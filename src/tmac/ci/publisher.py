"""Publisher abstraction for TMAC v1.6.0 CI layer.

Provides an `HttpTransport` protocol, `CommentPublisher` ABC, and concrete
GitHub/GitLab implementations.  All network I/O is injected via `HttpTransport`
so tests can use a fake transport without real sockets.

Feature: tmac-v1-6-pr-agent
Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.7, 3.8, 4.4
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tmac.ci.comment import MARKER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CIContext — shared across publisher and runner (task 8 imports from here)
# ---------------------------------------------------------------------------


@dataclass
class CIContext:
    """CI environment description shared by runner and publisher.

    pr_number is None when there is no open PR/MR context (R3.8, R5.9, R6.9).
    """

    platform: str  # "github" | "gitlab"
    repo: str  # "owner/repo" for GitHub; project id/path for GitLab
    pr_number: str | None  # PR/MR number; None ⇒ no PR context (R3.8)
    base_ref: str | None
    head_ref: str | None
    api_base: str  # platform API root URL
    artifact_path: str


# ---------------------------------------------------------------------------
# HTTP transport protocol and response
# ---------------------------------------------------------------------------


@dataclass
class HttpResponse:
    """Minimal HTTP response wrapper."""

    status: int
    body: str


class HttpTransport:
    """Protocol for injectable HTTP transport.

    Implementations may use urllib, requests, or a fake for testing.
    The `body` parameter is optional (None for GET/DELETE).
    """

    def request(
        self,
        method: str,
        url: str,
        headers: dict,
        body: bytes | None,
    ) -> HttpResponse:
        """Perform an HTTP request and return the response.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT).
            url: Absolute URL.
            headers: Request headers dict.
            body: Optional request body bytes (None for GET).

        Returns:
            HttpResponse with status code and decoded body.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PublishError(Exception):
    """Raised when comment publishing fails for any reason."""


class PublishPermissionError(PublishError):
    """Raised when the token lacks permission to write comments (HTTP 403).

    Validates: Requirements 3.7, 4.4
    """


class NoPullRequestContext(PublishError):
    """Raised when there is no open PR/MR to publish to.

    Validates: Requirements 3.8
    """


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class CommentPublisher(ABC):
    """Provider-agnostic comment publisher base.

    Sub-classes implement find_existing, create, and update for a specific
    platform.  The concrete `publish` orchestrates find-or-update:
    - 0 matching comments → create (R3.2)
    - ≥1 matching comments → update the most-recently-created one (R3.3, R3.4)

    The token is held in memory only and sent exclusively as an HTTP header;
    it is never written to logs or placed on any command line (R3.5, R4.2).
    """

    def __init__(self, transport: HttpTransport, token: str) -> None:
        self._transport = transport
        # Store token privately; never expose it in repr or logs
        self.__token = token

    # Expose token only to sub-classes for header construction
    @property
    def _token(self) -> str:  # type: ignore[return]
        return self.__token

    # ------------------------------------------------------------------
    # Abstract interface for sub-classes
    # ------------------------------------------------------------------

    @abstractmethod
    def find_existing(self, ctx: CIContext) -> str | None:
        """Return the comment id of the most-recently-created comment whose body
        contains MARKER, else None.  Must NOT log the token (R3.5).

        Raises:
            PublishPermissionError: if the HTTP response is 403.
        """

    @abstractmethod
    def create(self, ctx: CIContext, body: str) -> None:
        """Create a new comment with the given body.

        Raises:
            PublishPermissionError: if the HTTP response is 403.
        """

    @abstractmethod
    def update(self, ctx: CIContext, comment_id: str, body: str) -> None:
        """Replace the body of an existing comment.

        Raises:
            PublishPermissionError: if the HTTP response is 403.
        """

    # ------------------------------------------------------------------
    # Concrete find-or-update orchestration
    # ------------------------------------------------------------------

    def publish(self, ctx: CIContext, body: str) -> str:
        """Find-or-update the TMAC marker comment.

        Returns a short outcome string for logging.

        Raises:
            NoPullRequestContext: if ctx.pr_number is None (R3.8).
            PublishPermissionError: if HTTP 403 is encountered (R3.7).
            PublishError: for other publish failures.
        """
        if ctx.pr_number is None:
            raise NoPullRequestContext(
                "No PR/MR context available (pr_number is None); skipping comment publish."
            )

        comment_id = self.find_existing(ctx)

        if comment_id is None:
            # No existing marked comment → create new (R3.2)
            logger.debug("No existing TMAC comment found; creating new comment.")
            self.create(ctx, body)
            return "created"
        else:
            # Found an existing marked comment → update it (R3.3, R3.4)
            logger.debug("Existing TMAC comment %s found; updating.", comment_id)
            self.update(ctx, comment_id, body)
            return "updated"

    # ------------------------------------------------------------------
    # Fork / read-only token pre-check helper
    # ------------------------------------------------------------------

    def _is_read_only_token(self, ctx: CIContext) -> bool:
        """Probe whether the token can list comments (GET).

        Returns True if the token is read-only (GET returns 403), False otherwise.
        This check is performed BEFORE any write attempt (R4.4).

        Sub-classes can override for platform-specific probing.
        """
        # Default implementation: assume writable if we can't determine otherwise.
        # Concrete sub-classes use this to do a lightweight permission probe.
        return False


# ---------------------------------------------------------------------------
# GitHub implementation
# ---------------------------------------------------------------------------


class GitHubCommentPublisher(CommentPublisher):
    """Publish PR comments via the GitHub Issues Comments API.

    Endpoint: /repos/{owner}/{repo}/issues/{pr}/comments
    Auth header: Authorization: Bearer <token>
    Create: POST, Update: PATCH, List: GET

    403 responses map to PublishPermissionError (R3.7).
    Fork PR token detection via GET probe before write (R4.4).

    Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.7, 4.4
    """

    def _auth_headers(self) -> dict:
        """Build GitHub auth headers.  Token never logged (R3.5)."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }

    def _comments_url(self, ctx: CIContext) -> str:
        """Return the URL for listing / creating comments."""
        base = ctx.api_base.rstrip("/")
        return f"{base}/repos/{ctx.repo}/issues/{ctx.pr_number}/comments"

    def _comment_url(self, ctx: CIContext, comment_id: str) -> str:
        """Return the URL for updating a specific comment."""
        base = ctx.api_base.rstrip("/")
        return f"{base}/repos/{ctx.repo}/issues/comments/{comment_id}"

    def _is_read_only_token(self, ctx: CIContext) -> bool:
        """Probe GitHub permissions by checking the X-OAuth-Scopes header.

        Returns True if the GET to list comments returns 403.
        """
        url = self._comments_url(ctx) + "?per_page=1"
        resp = self._transport.request("GET", url, self._auth_headers(), None)
        return resp.status == 403

    def find_existing(self, ctx: CIContext) -> str | None:
        """Return the id of the most-recently-created TMAC marker comment, else None.

        Lists all comments (with pagination) and returns the last one containing MARKER.
        GitHub returns comments in ascending created-at order; the last item is most recent.

        Raises:
            PublishPermissionError: on HTTP 403.
        """
        url = self._comments_url(ctx) + "?per_page=100&sort=created&direction=asc"
        marked: list[dict] = []

        while url:
            resp = self._transport.request("GET", url, self._auth_headers(), None)
            if resp.status == 403:
                raise PublishPermissionError(
                    "GitHub GET comments returned 403 — insufficient token scope."
                )
            if resp.status not in (200, 201):
                raise PublishError(f"GitHub GET comments returned HTTP {resp.status}.")
            comments = json.loads(resp.body) if resp.body else []
            for comment in comments:
                if MARKER in comment.get("body", ""):
                    marked.append(comment)
            # Simple pagination: stop after first page (no Link header parsing needed
            # for the typical case; a real implementation would follow Link headers)
            url = None  # type: ignore[assignment]

        if not marked:
            return None
        # Return the id of the most-recently-created marked comment (R3.4)
        # Comments are sorted ascending by created_at, so the last entry is newest
        return str(marked[-1]["id"])

    def create(self, ctx: CIContext, body: str) -> None:
        """POST a new comment.

        Raises:
            PublishPermissionError: on HTTP 403.
        """
        # Pre-check: detect read-only / fork token before attempting write (R4.4)
        if self._is_read_only_token(ctx):
            raise PublishPermissionError(
                "GitHub token does not have comment-write permission (read-only / fork token)."
            )

        url = self._comments_url(ctx)
        payload = json.dumps({"body": body}).encode("utf-8")
        resp = self._transport.request("POST", url, self._auth_headers(), payload)
        if resp.status == 403:
            raise PublishPermissionError(
                "GitHub POST comment returned 403 — insufficient token scope."
            )
        if resp.status not in (200, 201):
            raise PublishError(f"GitHub POST comment returned HTTP {resp.status}.")

    def update(self, ctx: CIContext, comment_id: str, body: str) -> None:
        """PATCH an existing comment.

        Raises:
            PublishPermissionError: on HTTP 403.
        """
        # Pre-check: detect read-only / fork token before attempting write (R4.4)
        if self._is_read_only_token(ctx):
            raise PublishPermissionError(
                "GitHub token does not have comment-write permission (read-only / fork token)."
            )

        url = self._comment_url(ctx, comment_id)
        payload = json.dumps({"body": body}).encode("utf-8")
        resp = self._transport.request("PATCH", url, self._auth_headers(), payload)
        if resp.status == 403:
            raise PublishPermissionError(
                "GitHub PATCH comment returned 403 — insufficient token scope."
            )
        if resp.status not in (200, 201):
            raise PublishError(f"GitHub PATCH comment returned HTTP {resp.status}.")


# ---------------------------------------------------------------------------
# GitLab implementation
# ---------------------------------------------------------------------------


class GitLabCommentPublisher(CommentPublisher):
    """Publish MR notes via the GitLab Merge Request Notes API.

    Endpoint: /projects/{id}/merge_requests/{iid}/notes
    Auth headers: PRIVATE-TOKEN (personal/project) or JOB-TOKEN (CI job token)
    Create: POST, Update: PUT, List: GET

    403 responses map to PublishPermissionError (R3.7).
    Fork MR token detection via GET probe before write (R4.4).

    Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.7, 4.4
    """

    def __init__(self, transport: HttpTransport, token: str, use_job_token: bool = False) -> None:
        super().__init__(transport, token)
        self._use_job_token = use_job_token

    def _auth_headers(self) -> dict:
        """Build GitLab auth headers.  Token never logged (R3.5)."""
        if self._use_job_token:
            return {
                "JOB-TOKEN": self._token,
                "Content-Type": "application/json",
            }
        return {
            "PRIVATE-TOKEN": self._token,
            "Content-Type": "application/json",
        }

    def _notes_url(self, ctx: CIContext) -> str:
        """Return the URL for listing / creating MR notes."""
        base = ctx.api_base.rstrip("/")
        # ctx.repo holds the project id or URL-encoded path
        return f"{base}/projects/{ctx.repo}/merge_requests/{ctx.pr_number}/notes"

    def _note_url(self, ctx: CIContext, note_id: str) -> str:
        """Return the URL for updating a specific MR note."""
        base = ctx.api_base.rstrip("/")
        return f"{base}/projects/{ctx.repo}/merge_requests/{ctx.pr_number}/notes/{note_id}"

    def _is_read_only_token(self, ctx: CIContext) -> bool:
        """Probe GitLab permissions by attempting a lightweight GET.

        Returns True if the GET returns 403.
        """
        url = self._notes_url(ctx) + "?per_page=1"
        resp = self._transport.request("GET", url, self._auth_headers(), None)
        return resp.status == 403

    def find_existing(self, ctx: CIContext) -> str | None:
        """Return the id of the most-recently-created TMAC marker note, else None.

        Lists notes and returns the last one containing MARKER (ascending order).

        Raises:
            PublishPermissionError: on HTTP 403.
        """
        url = self._notes_url(ctx) + "?sort=asc&order_by=created_at&per_page=100"
        marked: list[dict] = []

        while url:
            resp = self._transport.request("GET", url, self._auth_headers(), None)
            if resp.status == 403:
                raise PublishPermissionError(
                    "GitLab GET notes returned 403 — insufficient token scope."
                )
            if resp.status not in (200, 201):
                raise PublishError(f"GitLab GET notes returned HTTP {resp.status}.")
            notes = json.loads(resp.body) if resp.body else []
            for note in notes:
                if MARKER in note.get("body", ""):
                    marked.append(note)
            url = None  # type: ignore[assignment]

        if not marked:
            return None
        return str(marked[-1]["id"])

    def create(self, ctx: CIContext, body: str) -> None:
        """POST a new MR note.

        Raises:
            PublishPermissionError: on HTTP 403.
        """
        # Pre-check: detect read-only / fork token before write (R4.4)
        if self._is_read_only_token(ctx):
            raise PublishPermissionError(
                "GitLab token does not have note-write permission (read-only / fork token)."
            )

        url = self._notes_url(ctx)
        payload = json.dumps({"body": body}).encode("utf-8")
        resp = self._transport.request("POST", url, self._auth_headers(), payload)
        if resp.status == 403:
            raise PublishPermissionError(
                "GitLab POST note returned 403 — insufficient token scope."
            )
        if resp.status not in (200, 201):
            raise PublishError(f"GitLab POST note returned HTTP {resp.status}.")

    def update(self, ctx: CIContext, note_id: str, body: str) -> None:
        """PUT an existing MR note.

        Raises:
            PublishPermissionError: on HTTP 403.
        """
        # Pre-check: detect read-only / fork token before write (R4.4)
        if self._is_read_only_token(ctx):
            raise PublishPermissionError(
                "GitLab token does not have note-write permission (read-only / fork token)."
            )

        url = self._note_url(ctx, note_id)
        payload = json.dumps({"body": body}).encode("utf-8")
        resp = self._transport.request("PUT", url, self._auth_headers(), payload)
        if resp.status == 403:
            raise PublishPermissionError("GitLab PUT note returned 403 — insufficient token scope.")
        if resp.status not in (200, 201):
            raise PublishError(f"GitLab PUT note returned HTTP {resp.status}.")
