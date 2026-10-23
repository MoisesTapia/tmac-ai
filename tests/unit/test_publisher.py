"""Unit and integration tests for the CommentPublisher abstraction.

Tasks 7.4 and 7.5:
  - 7.4: auth header, 403 handling, fork-token pre-check
  - 7.5: GitHub vs GitLab equivalence against FakeHttpTransport

Feature: tmac-v1-6-pr-agent
Validates: Requirements 3.5, 3.7, 4.4, 6.2
"""

from __future__ import annotations

import json

import pytest

from tests.property.strategies import FakeHttpTransport
from tmac.ci.comment import MARKER
from tmac.ci.publisher import (
    CIContext,
    GitHubCommentPublisher,
    GitLabCommentPublisher,
    NoPullRequestContext,
    PublishPermissionError,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _github_ctx(pr_number: str = "42") -> CIContext:
    return CIContext(
        platform="github",
        repo="owner/repo",
        pr_number=pr_number,
        base_ref="main",
        head_ref="feature",
        api_base="https://api.github.com",
        artifact_path="report.md",
    )


def _gitlab_ctx(pr_number: str = "7") -> CIContext:
    return CIContext(
        platform="gitlab",
        repo="123",
        pr_number=pr_number,
        base_ref="main",
        head_ref="feature",
        api_base="https://gitlab.example.com/api/v4",
        artifact_path="report.md",
    )


def _comment_with_marker() -> dict:
    return {"id": 1, "body": f"old analysis\n{MARKER}\nfooter"}


def _comment_without_marker() -> dict:
    return {"id": 2, "body": "some unrelated comment"}


# ===========================================================================
# Task 7.4 — auth header, 403, and fork-token pre-check
# ===========================================================================


class TestAuthHeader:
    """Assert every request carries the auth header (R3.5)."""

    def test_github_get_carries_bearer_token(self):
        transport = FakeHttpTransport()
        transport.set_list_response([])
        transport.set_write_response(201)

        publisher = GitHubCommentPublisher(transport, "my-secret-token")
        publisher.publish(_github_ctx(), f"body {MARKER}")

        # Every call must include the Authorization header
        for method, url, headers, body in transport.calls:
            assert "Authorization" in headers, f"Authorization header missing on {method} {url}"
            assert (
                "my-secret-token" in headers["Authorization"]
            ), f"Token not present in Authorization header for {method} {url}"
            # Token must not be logged — we verify it's only in the header
            assert (
                "my-secret-token" not in url
            ), f"Token found in URL (should only be in headers): {url}"

    def test_gitlab_get_carries_private_token(self):
        transport = FakeHttpTransport()
        transport.set_list_response([])
        transport.set_write_response(201)

        publisher = GitLabCommentPublisher(transport, "glpat-secret", use_job_token=False)
        publisher.publish(_gitlab_ctx(), f"body {MARKER}")

        for method, url, headers, body in transport.calls:
            assert "PRIVATE-TOKEN" in headers, f"PRIVATE-TOKEN header missing on {method} {url}"
            assert (
                "glpat-secret" in headers["PRIVATE-TOKEN"]
            ), f"Token not present in PRIVATE-TOKEN header for {method} {url}"

    def test_gitlab_job_token_uses_job_token_header(self):
        transport = FakeHttpTransport()
        transport.set_list_response([])
        transport.set_write_response(201)

        publisher = GitLabCommentPublisher(transport, "ci-job-token", use_job_token=True)
        publisher.publish(_gitlab_ctx(), f"body {MARKER}")

        for method, url, headers, body in transport.calls:
            assert "JOB-TOKEN" in headers, f"JOB-TOKEN header missing on {method} {url}"
            # Should NOT use PRIVATE-TOKEN when use_job_token=True
            assert (
                "PRIVATE-TOKEN" not in headers
            ), "PRIVATE-TOKEN should not be sent when use_job_token=True"


class TestPermissionError:
    """Assert 403 response → PublishPermissionError, existing comment unmodified (R3.7)."""

    def test_github_403_on_get_raises_permission_error(self):
        """A 403 on GET (listing comments) should raise PublishPermissionError."""
        transport = FakeHttpTransport()
        transport.set_get_403(True)  # force GET to return 403

        publisher = GitHubCommentPublisher(transport, "bad-token")
        ctx = _github_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.find_existing(ctx)

    def test_github_403_on_post_raises_permission_error(self):
        """A 403 on POST (create) should raise PublishPermissionError.

        Existing comments must remain unchanged (no writes before the failure).
        """
        transport = FakeHttpTransport()
        transport.set_list_response([])  # no existing marker comments
        transport.set_write_response(403)  # write returns 403

        publisher = GitHubCommentPublisher(transport, "bad-token")
        ctx = _github_ctx()

        # The pre-check GET will succeed (not 403), so we get to POST
        with pytest.raises(PublishPermissionError):
            publisher.publish(ctx, f"new body {MARKER}")

        # No successful writes occurred
        successful_writes = [c for c in transport.written_calls if c[0] in ("POST", "PATCH", "PUT")]
        # The only write attempt should be the failed POST
        assert len(successful_writes) == 1
        assert successful_writes[0][0] == "POST"

    def test_github_403_on_patch_raises_permission_error_existing_unchanged(self):
        """A 403 on PATCH (update) should raise PublishPermissionError.

        The existing comment body is unchanged (we never succeed at writing).
        """
        existing = _comment_with_marker()
        transport = FakeHttpTransport()
        transport.set_list_response([existing])
        transport.set_write_response(403)  # update returns 403

        publisher = GitHubCommentPublisher(transport, "bad-token")
        ctx = _github_ctx()

        original_body = existing["body"]

        with pytest.raises(PublishPermissionError):
            publisher.publish(ctx, f"new body {MARKER}")

        # The original comment body is unchanged (we tracked it before publish)
        assert (
            existing["body"] == original_body
        ), "Existing comment body was mutated despite publish failure"

    def test_gitlab_403_on_get_raises_permission_error(self):
        transport = FakeHttpTransport()
        transport.set_get_403(True)

        publisher = GitLabCommentPublisher(transport, "bad-token")
        ctx = _gitlab_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.find_existing(ctx)

    def test_gitlab_403_on_post_raises_permission_error(self):
        transport = FakeHttpTransport()
        transport.set_list_response([])
        transport.set_write_response(403)

        publisher = GitLabCommentPublisher(transport, "bad-token")
        ctx = _gitlab_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.publish(ctx, f"new body {MARKER}")


class TestForkTokenPreCheck:
    """Assert read-only/fork token causes pre-publish skip without write attempt (R4.4)."""

    def test_github_fork_token_raises_before_create(self):
        """When GET returns 403 (read-only token), create() raises PublishPermissionError
        WITHOUT making a POST write attempt."""
        transport = FakeHttpTransport()
        transport.set_get_403(True)  # simulate read-only / fork token

        publisher = GitHubCommentPublisher(transport, "fork-token")
        ctx = _github_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.create(ctx, f"body {MARKER}")

        # No write calls should have been made
        assert (
            len(transport.written_calls) == 0
        ), f"Expected 0 write calls but got: {[c[0] for c in transport.written_calls]}"

    def test_github_fork_token_raises_before_update(self):
        """When GET returns 403 (read-only token), update() raises PublishPermissionError
        WITHOUT making a PATCH write attempt."""
        transport = FakeHttpTransport()
        transport.set_get_403(True)

        publisher = GitHubCommentPublisher(transport, "fork-token")
        ctx = _github_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.update(ctx, "1", f"body {MARKER}")

        assert (
            len(transport.written_calls) == 0
        ), f"Expected 0 write calls but got: {[c[0] for c in transport.written_calls]}"

    def test_gitlab_fork_token_raises_before_create(self):
        """When GET returns 403 (read-only token), GitLab create() raises PublishPermissionError
        WITHOUT making a POST write attempt."""
        transport = FakeHttpTransport()
        transport.set_get_403(True)

        publisher = GitLabCommentPublisher(transport, "fork-token")
        ctx = _gitlab_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.create(ctx, f"body {MARKER}")

        assert (
            len(transport.written_calls) == 0
        ), f"Expected 0 write calls but got: {[c[0] for c in transport.written_calls]}"

    def test_gitlab_fork_token_raises_before_update(self):
        transport = FakeHttpTransport()
        transport.set_get_403(True)

        publisher = GitLabCommentPublisher(transport, "fork-token")
        ctx = _gitlab_ctx()

        with pytest.raises(PublishPermissionError):
            publisher.update(ctx, "1", f"body {MARKER}")

        assert len(transport.written_calls) == 0

    def test_no_pr_context_raises_no_pull_request_context(self):
        """When pr_number is None, publish() raises NoPullRequestContext (R3.8)."""
        transport = FakeHttpTransport()
        publisher = GitHubCommentPublisher(transport, "token")
        ctx = CIContext(
            platform="github",
            repo="owner/repo",
            pr_number=None,  # <-- no PR
            base_ref="main",
            head_ref="feature",
            api_base="https://api.github.com",
            artifact_path="report.md",
        )

        with pytest.raises(NoPullRequestContext):
            publisher.publish(ctx, f"body {MARKER}")

        # No HTTP requests should have been made
        assert len(transport.calls) == 0, "No HTTP calls should be made when there is no PR context"


# ===========================================================================
# Task 7.5 — GitHub vs GitLab equivalence (integration tests)
# ===========================================================================


class TestGitHubGitLabEquivalence:
    """Assert both publishers produce equivalent find-or-update behavior
    with platform-specific URL/JSON shapes (R6.2)."""

    def test_both_create_when_no_existing_comment(self):
        """When there are no existing marked comments, both platforms create one."""
        gh_transport = FakeHttpTransport()
        gh_transport.set_list_response([])
        gh_transport.set_write_response(201, '{"id": 100}')

        gl_transport = FakeHttpTransport()
        gl_transport.set_list_response([])
        gl_transport.set_write_response(201, '{"id": 200}')

        gh_publisher = GitHubCommentPublisher(gh_transport, "gh-token")
        gl_publisher = GitLabCommentPublisher(gl_transport, "gl-token")

        body = f"analysis\n{MARKER}\nfooter"
        gh_publisher.publish(_github_ctx(), body)
        gl_publisher.publish(_gitlab_ctx(), body)

        # Both should have made exactly one write call
        gh_writes = [c[0] for c in gh_transport.written_calls]
        gl_writes = [c[0] for c in gl_transport.written_calls]

        assert gh_writes == ["POST"], f"GitHub expected [POST], got {gh_writes}"
        assert gl_writes == ["POST"], f"GitLab expected [POST], got {gl_writes}"

        # GitHub uses /repos/ path
        gh_post_url = gh_transport.written_calls[0][1]
        assert "/repos/" in gh_post_url, f"GitHub POST URL should contain /repos/: {gh_post_url}"
        assert "/issues/" in gh_post_url, f"GitHub POST URL should contain /issues/: {gh_post_url}"

        # GitLab uses /projects/ path
        gl_post_url = gl_transport.written_calls[0][1]
        assert (
            "/projects/" in gl_post_url
        ), f"GitLab POST URL should contain /projects/: {gl_post_url}"
        assert (
            "/merge_requests/" in gl_post_url
        ), f"GitLab POST URL should contain /merge_requests/: {gl_post_url}"

    def test_both_update_when_existing_comment_present(self):
        """When an existing marked comment exists, both platforms update it."""
        existing_gh = {"id": 50, "body": f"old text {MARKER}"}
        existing_gl = {"id": 60, "body": f"old text {MARKER}"}

        gh_transport = FakeHttpTransport()
        gh_transport.set_list_response([existing_gh])
        gh_transport.set_write_response(200, '{"id": 50}')

        gl_transport = FakeHttpTransport()
        gl_transport.set_list_response([existing_gl])
        gl_transport.set_write_response(200, '{"id": 60}')

        gh_publisher = GitHubCommentPublisher(gh_transport, "gh-token")
        gl_publisher = GitLabCommentPublisher(gl_transport, "gl-token")

        body = f"new analysis {MARKER}"
        gh_publisher.publish(_github_ctx(), body)
        gl_publisher.publish(_gitlab_ctx(), body)

        # GitHub uses PATCH, GitLab uses PUT
        gh_writes = [c[0] for c in gh_transport.written_calls]
        gl_writes = [c[0] for c in gl_transport.written_calls]

        assert gh_writes == ["PATCH"], f"GitHub expected [PATCH] for update, got {gh_writes}"
        assert gl_writes == ["PUT"], f"GitLab expected [PUT] for update, got {gl_writes}"

        # No additional POSTs (creates)
        assert "POST" not in gh_writes, "GitHub should not POST when updating"
        assert "POST" not in gl_writes, "GitLab should not POST when updating"

    def test_both_update_most_recent_of_multiple_marked_comments(self):
        """When multiple marked comments exist, both update the most recently created one."""
        # Comments in ascending order (last = most recent)
        existing_gh = [
            {"id": 10, "body": f"older {MARKER}"},  # older
            {"id": 20, "body": f"newer {MARKER}"},  # most recent
        ]
        existing_gl = [
            {"id": 30, "body": f"older {MARKER}"},
            {"id": 40, "body": f"newer {MARKER}"},
        ]

        gh_transport = FakeHttpTransport()
        gh_transport.set_list_response(existing_gh)
        gh_transport.set_write_response(200, '{"id": 20}')

        gl_transport = FakeHttpTransport()
        gl_transport.set_list_response(existing_gl)
        gl_transport.set_write_response(200, '{"id": 40}')

        gh_publisher = GitHubCommentPublisher(gh_transport, "gh-token")
        gl_publisher = GitLabCommentPublisher(gl_transport, "gl-token")

        body = f"latest analysis {MARKER}"
        gh_publisher.publish(_github_ctx(), body)
        gl_publisher.publish(_gitlab_ctx(), body)

        # GitHub PATCH must target id=20 (most recent)
        gh_patch_url = gh_transport.written_calls[0][1]
        assert "20" in gh_patch_url, f"GitHub PATCH should target id=20, got URL: {gh_patch_url}"
        assert "10" not in gh_patch_url.split("/")[-1], "GitHub PATCH should NOT target id=10"

        # GitLab PUT must target id=40 (most recent)
        gl_put_url = gl_transport.written_calls[0][1]
        assert "40" in gl_put_url, f"GitLab PUT should target id=40, got URL: {gl_put_url}"
        assert "30" not in gl_put_url.split("/")[-1], "GitLab PUT should NOT target id=30"

    def test_both_produce_json_body_with_comment_text(self):
        """Both publishers send the comment body as JSON."""
        gh_transport = FakeHttpTransport()
        gh_transport.set_list_response([])
        gh_transport.set_write_response(201, '{"id": 1}')

        gl_transport = FakeHttpTransport()
        gl_transport.set_list_response([])
        gl_transport.set_write_response(201, '{"id": 2}')

        body = f"my comment {MARKER}"

        GitHubCommentPublisher(gh_transport, "gh-tok").publish(_github_ctx(), body)
        GitLabCommentPublisher(gl_transport, "gl-tok").publish(_gitlab_ctx(), body)

        # Check GitHub write
        gh_write_body = gh_transport.written_calls[0][3]
        assert gh_write_body is not None
        gh_payload = json.loads(gh_write_body.decode("utf-8"))
        assert gh_payload.get("body") == body, f"GitHub JSON body mismatch: {gh_payload}"

        # Check GitLab write
        gl_write_body = gl_transport.written_calls[0][3]
        assert gl_write_body is not None
        gl_payload = json.loads(gl_write_body.decode("utf-8"))
        assert gl_payload.get("body") == body, f"GitLab JSON body mismatch: {gl_payload}"

    def test_both_include_marker_in_written_body(self):
        """Both publishers write a body that contains MARKER (idempotency anchor)."""
        for transport_cls, publisher_cls, ctx_fn in [
            (FakeHttpTransport, GitHubCommentPublisher, _github_ctx),
            (FakeHttpTransport, GitLabCommentPublisher, _gitlab_ctx),
        ]:
            transport = transport_cls()
            transport.set_list_response([])
            transport.set_write_response(201, '{"id": 1}')

            publisher = publisher_cls(transport, "token")
            body = f"analysis\n{MARKER}\nrest of comment"
            publisher.publish(ctx_fn(), body)

            write_body = transport.written_calls[0][3]
            assert write_body is not None
            payload = json.loads(write_body.decode("utf-8"))
            assert MARKER in payload.get(
                "body", ""
            ), f"{publisher_cls.__name__} did not include MARKER in written body"
