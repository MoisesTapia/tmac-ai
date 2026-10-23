"""CI orchestrator for TMAC v1.6.0 "Ixtla" (CI/CD Native).

This module houses the `CIContext` dataclass, the `ci_context_from_env()`
detection helper, and the `CIRunner` orchestration class.

Feature: tmac-v1-6-pr-agent
Validates: Requirements 1.5, 1.6, 3.6, 3.7, 3.8, 4.1, 4.3, 6.6
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys

# CIContext is defined (and already imported by publisher + tests) in publisher.py.
# Re-export it here so the design's "place CIContext in runner.py" is honoured while
# maintaining backward compatibility for existing imports.
from tmac.ci.publisher import CIContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CI environment variable constants
# ---------------------------------------------------------------------------

# GitHub Actions standard env vars
_GH_REPO = "GITHUB_REPOSITORY"  # "owner/repo"
_GH_EVENT_NAME = "GITHUB_EVENT_NAME"  # "pull_request", "push", ...
_GH_HEAD_REF = "GITHUB_HEAD_REF"  # branch name of the PR head
_GH_BASE_REF = "GITHUB_BASE_REF"  # branch name of the PR base
_GH_REF = "GITHUB_REF"  # full ref: "refs/pull/{n}/merge" or "refs/heads/..."
_GH_API_URL = "GITHUB_API_URL"  # "https://api.github.com"
_GH_SERVER_URL = "GITHUB_SERVER_URL"  # "https://github.com"
_GH_EVENT_PATH = "GITHUB_EVENT_PATH"  # path to the event payload JSON file

# GitLab CI standard env vars
_GL_PROJECT_PATH = "CI_PROJECT_PATH"  # "namespace/project"
_GL_MR_IID = "CI_MERGE_REQUEST_IID"  # MR internal ID
_GL_MR_SOURCE_BRANCH = "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"
_GL_MR_TARGET_BRANCH = "CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
_GL_SERVER_URL = "CI_SERVER_URL"  # "https://gitlab.com"
_GL_API_V4_URL = "CI_API_V4_URL"  # "https://gitlab.com/api/v4"

# Regex to extract PR number from "refs/pull/{number}/merge"
_GH_PR_REF_RE = re.compile(r"^refs/pull/(\d+)/merge$")


# ---------------------------------------------------------------------------
# Public helper: ci_context_from_env
# ---------------------------------------------------------------------------


def ci_context_from_env(
    *,
    platform: str | None = None,
    repo: str | None = None,
    pr_number: str | None = None,
    base_ref: str | None = None,
    head_ref: str | None = None,
    api_base: str | None = None,
    artifact_path: str = "tmac-report.md",
) -> CIContext:
    """Build a `CIContext` from explicit arguments, falling back to CI env vars.

    Auto-detection priority:
    1. Explicit keyword arguments (caller-supplied values always win).
    2. GitHub Actions env vars (detected when ``GITHUB_REPOSITORY`` is set).
    3. GitLab CI env vars (detected when ``CI_PROJECT_PATH`` is set).

    ``pr_number`` is ``None`` when no PR/MR context can be determined; this
    signals to the publisher and runner to skip comment publishing
    (R3.8, R5.9, R6.9).

    Args:
        platform: ``"github"`` or ``"gitlab"``.  Auto-detected when ``None``.
        repo: ``"owner/repo"`` (GitHub) or project path/id (GitLab).  Auto-detected.
        pr_number: PR/MR number as a string, or ``None`` for no PR context.
        base_ref: Base branch/ref of the PR.  Auto-detected.
        head_ref: Head branch/ref of the PR.  Auto-detected.
        api_base: Platform API root URL.  Auto-detected.
        artifact_path: Path / URL of the Report_Artifact.  Defaults to ``tmac-report.md``.

    Returns:
        A fully populated ``CIContext``.  Fields that cannot be determined from
        the environment remain ``None``.
    """
    # Detect the running platform if not provided
    detected_platform = platform or _detect_platform()

    if detected_platform == "github":
        return _build_github_context(
            platform=detected_platform,
            repo=repo,
            pr_number=pr_number,
            base_ref=base_ref,
            head_ref=head_ref,
            api_base=api_base,
            artifact_path=artifact_path,
        )
    elif detected_platform == "gitlab":
        return _build_gitlab_context(
            platform=detected_platform,
            repo=repo,
            pr_number=pr_number,
            base_ref=base_ref,
            head_ref=head_ref,
            api_base=api_base,
            artifact_path=artifact_path,
        )
    else:
        # Unknown / local environment — return a minimal context with Nones
        logger.debug(
            "ci_context_from_env: no known CI platform detected; "
            "returning minimal context with pr_number=None"
        )
        return CIContext(
            platform=detected_platform or "unknown",
            repo=repo or "",
            pr_number=pr_number,  # None → no PR context (R3.8)
            base_ref=base_ref,
            head_ref=head_ref,
            api_base=api_base or "",
            artifact_path=artifact_path,
        )


# ---------------------------------------------------------------------------
# Internal: platform detection
# ---------------------------------------------------------------------------


def _detect_platform() -> str | None:
    """Detect the running CI platform from env vars.

    Returns ``"github"``, ``"gitlab"``, or ``None`` when not in a known CI env.
    """
    if os.environ.get(_GH_REPO):
        return "github"
    if os.environ.get(_GL_PROJECT_PATH):
        return "gitlab"
    return None


# ---------------------------------------------------------------------------
# Internal: GitHub context builder
# ---------------------------------------------------------------------------


def _build_github_context(
    *,
    platform: str,
    repo: str | None,
    pr_number: str | None,
    base_ref: str | None,
    head_ref: str | None,
    api_base: str | None,
    artifact_path: str,
) -> CIContext:
    """Populate a CIContext for GitHub Actions from env vars."""
    resolved_repo = repo or os.environ.get(_GH_REPO) or ""
    resolved_api_base = api_base or os.environ.get(_GH_API_URL) or "https://api.github.com"
    resolved_base_ref = base_ref or os.environ.get(_GH_BASE_REF) or None
    resolved_head_ref = head_ref or os.environ.get(_GH_HEAD_REF) or None

    # Determine PR number
    resolved_pr_number = pr_number
    if resolved_pr_number is None:
        resolved_pr_number = _extract_github_pr_number()

    return CIContext(
        platform=platform,
        repo=resolved_repo,
        pr_number=resolved_pr_number,
        base_ref=resolved_base_ref,
        head_ref=resolved_head_ref,
        api_base=resolved_api_base,
        artifact_path=artifact_path,
    )


def _extract_github_pr_number() -> str | None:
    """Extract the PR number from GitHub env vars.

    Tries three sources in order:
    1. ``GITHUB_REF`` — format ``refs/pull/{number}/merge`` (pull_request events).
    2. ``GITHUB_EVENT_PATH`` — parses the event JSON for ``pull_request.number``.
    3. Returns ``None`` when neither source yields a PR number (push events, etc.).
    """
    # Source 1: GITHUB_REF
    gh_ref = os.environ.get(_GH_REF, "")
    match = _GH_PR_REF_RE.match(gh_ref)
    if match:
        return match.group(1)

    # Source 2: GITHUB_EVENT_PATH (event payload JSON)
    event_path = os.environ.get(_GH_EVENT_PATH, "")
    if event_path:
        try:
            with open(event_path, "r", encoding="utf-8") as fh:
                event = json.load(fh)
            pr_number = event.get("pull_request", {}).get("number") or event.get("number")
            if pr_number is not None:
                return str(pr_number)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.debug("Could not parse GITHUB_EVENT_PATH %s: %s", event_path, exc)

    # Check if we are on a pull_request event at all
    event_name = os.environ.get(_GH_EVENT_NAME, "")
    if event_name and event_name != "pull_request":
        # Push or other non-PR event: no PR context (R5.9)
        logger.debug(
            "GitHub event '%s' is not a pull_request; pr_number=None (no PR context).",
            event_name,
        )

    return None  # No PR context


# ---------------------------------------------------------------------------
# Internal: GitLab context builder
# ---------------------------------------------------------------------------


def _build_gitlab_context(
    *,
    platform: str,
    repo: str | None,
    pr_number: str | None,
    base_ref: str | None,
    head_ref: str | None,
    api_base: str | None,
    artifact_path: str,
) -> CIContext:
    """Populate a CIContext for GitLab CI from env vars."""
    resolved_repo = repo or os.environ.get(_GL_PROJECT_PATH) or ""
    resolved_api_base = api_base or os.environ.get(_GL_API_V4_URL) or "https://gitlab.com/api/v4"

    # MR IID → pr_number (None when not in an MR pipeline, R6.9)
    resolved_pr_number = pr_number or os.environ.get(_GL_MR_IID) or None

    resolved_base_ref = base_ref or os.environ.get(_GL_MR_TARGET_BRANCH) or None
    resolved_head_ref = head_ref or os.environ.get(_GL_MR_SOURCE_BRANCH) or None

    if resolved_pr_number is None:
        logger.debug("GitLab: CI_MERGE_REQUEST_IID not set; pr_number=None (no MR context, R6.9).")

    return CIContext(
        platform=platform,
        repo=resolved_repo,
        pr_number=resolved_pr_number,
        base_ref=resolved_base_ref,
        head_ref=resolved_head_ref,
        api_base=resolved_api_base,
        artifact_path=artifact_path,
    )


# ---------------------------------------------------------------------------
# CIRunner — main orchestration class (task 8.2)
# ---------------------------------------------------------------------------


class CIRunner:
    """Orchestrates the full CI analysis pipeline.

    Orchestration flow:
    1. Compute the Changed_File_Set via ``changed_tf_files`` (or skip to
       ``DeltaScanner`` when a plan file is given, R1.5).
    2. Scan restricted to the changed paths via ``Scanner(include_paths=...)``,
       or ``DeltaScanner.run(plan_file)`` for plan-file mode.
    3. Write the Report_Artifact via the appropriate reporter.
    4. Format the PR/MR comment via ``CommentFormatter.format(result, ctx)``.
    5. Publish via ``CommentPublisher.publish(ci_ctx, body)`` when a token is
       present and comment publishing is enabled.
    6. Return the findings-based exit code using the same logic as
       ``_exit_with_code`` in ``cli.py`` (replicated inline to avoid circular
       imports — cli imports runner transitively through the ci subcommand).

    Validates: Requirements 1.5, 1.6, 3.6, 3.7, 3.8, 4.1, 4.3, 6.6
    """

    # -----------------------------------------------------------------
    # Exit-code logic (replicated from cli._exit_with_code to avoid the
    # circular import cli → runner → cli)
    # -----------------------------------------------------------------
    _SEVERITY_LEVELS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "info": 0,
    }

    def _compute_exit_code(self, findings: list, threshold: str) -> int:
        """Return the findings-based exit code (does NOT call sys.exit)."""
        threshold_val = self._SEVERITY_LEVELS.get(
            threshold.lower(), self._SEVERITY_LEVELS["critical"]
        )
        max_sev = max(
            (self._SEVERITY_LEVELS.get(f.severity.lower(), -1) for f in findings),
            default=-1,
        )
        if max_sev < threshold_val:
            return 0

        has_critical = any(f.severity.lower() == "critical" for f in findings)
        has_high = any(f.severity.lower() == "high" for f in findings)
        if has_critical:
            return 1
        elif has_high:
            return 2
        return 1

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def run(
        self,
        *,
        directory: str,
        plan_file: str | None,
        fail_on: str,
        report_fmt: str,
        output: str | None,
        delta_only: bool,
        comment: bool,
        exclude: list[str],
        ctx: CIContext,
        lenient: bool = False,
    ) -> int:
        """Run the CI pipeline and return the findings-based exit code.

        Never raises tokens.  Redacts all user-facing strings via
        ``secrets.redact()``.  A publish failure never changes the
        findings-based exit code (R3.7, R3.8, R6.6).

        Args:
            directory:  The Terraform root to scan.
            plan_file:  When provided, use ``DeltaScanner`` instead of the
                        diff + ``Scanner`` path (R1.5).
            fail_on:    Severity threshold for the exit code.
            report_fmt: ``"html"``, ``"md"``, or ``"json"``.
            output:     Explicit output path for the Report_Artifact; defaults
                        to ``"tmac-report.<fmt>"``.
            delta_only: When *True* (default), compute the changed set and
                        restrict scanning to it.  When *False*, scan the whole
                        directory (R1.9).
            comment:    Whether to publish a PR/MR comment.
            exclude:    Glob patterns to exclude from scanning.
            ctx:        The populated ``CIContext``.
            lenient:    When *False* (default), an incomplete scan (unparseable
                        files, invalid rules) exits 3 even if no findings were
                        produced; the report and comment are still published.

        Returns:
            Integer exit code (0, 1, 2, or 3).
        """
        from tmac.ci import secrets as _secrets
        from tmac.ci.comment import CommentContext, CommentFormatter
        from tmac.ci.git_diff import GitRefError, changed_tf_files
        from tmac.ci.publisher import (
            NoPullRequestContext,
            PublishError,
            PublishPermissionError,
        )
        from tmac.delta.models import DeltaScanResult
        from tmac.delta.scanner import DeltaScanError, DeltaScanner
        from tmac.scanner import ScanError, Scanner

        token = _secrets.read_token()

        # ------------------------------------------------------------------
        # Step 1: Determine scan mode and produce result
        # ------------------------------------------------------------------
        result = None
        include_paths: list[str] | None = None

        if plan_file:
            # Plan-file mode → DeltaScanner (R1.5)
            logger.debug("CIRunner: plan_file mode → DeltaScanner('%s')", plan_file)
            try:
                result = DeltaScanner().run(plan_file=plan_file)
            except DeltaScanError as exc:
                msg = _secrets.redact(str(exc), token)
                logger.error("CIRunner: DeltaScanner error: %s", msg)
                print(msg, file=sys.stderr)
                return 3
        else:
            if delta_only:
                # Delta-only: compute Changed_File_Set first (R1.2)
                base_ref = ctx.base_ref
                head_ref = ctx.head_ref

                if not base_ref or not head_ref:
                    missing = "base_ref" if not base_ref else "head_ref"
                    msg = _secrets.redact(
                        f"Missing required ref: {missing} is not set. "
                        "Provide --base-ref and --head-ref.",
                        token,
                    )
                    print(msg, file=sys.stderr)
                    return 3

                try:
                    changed = changed_tf_files(
                        base_ref=base_ref,
                        head_ref=head_ref,
                        repo_dir=directory,
                    )
                except GitRefError as exc:
                    msg = _secrets.redact(str(exc), token)
                    print(msg, file=sys.stderr)
                    return 3

                if not changed:
                    # Empty Changed_File_Set → zero findings, exit 0 (R1.6)
                    logger.debug("CIRunner: empty changed set → exit 0")
                    return 0

                # Resolve to absolute paths for include_paths filtering
                import os as _os

                include_paths = [
                    str(_os.path.join(_os.path.abspath(directory), p)) for p in changed
                ]
            else:
                # Full scan mode (--no-delta-only, R1.9)
                include_paths = None

            # Run the Scanner (restricted or full)
            try:
                result = Scanner().run_scan(
                    directory=directory,
                    exclude_patterns=exclude,
                    include_paths=include_paths,
                )
            except ScanError as exc:
                msg = _secrets.redact(str(exc), token)
                print(msg, file=sys.stderr)
                return 3

        # ------------------------------------------------------------------
        # Step 2: Determine output path
        # ------------------------------------------------------------------
        fmt = report_fmt or "md"
        out_file = output or f"tmac-report.{fmt}"

        # ------------------------------------------------------------------
        # Step 3: Write the Report_Artifact (only when token is present OR
        # publish is disabled — skip upload when token is missing per R4.3)
        # ------------------------------------------------------------------
        if token:
            reporter = self._build_reporter(fmt)
            report_content = reporter.generate(result)
            try:
                with open(out_file, "w", encoding="utf-8") as fh:
                    fh.write(report_content)
                logger.debug("CIRunner: report written to '%s'", out_file)
            except OSError as exc:
                msg = _secrets.redact(f"Could not write report to '{out_file}': {exc}", token)
                print(msg, file=sys.stderr)
                # Don't abort — proceed with findings-based exit
        else:
            # Token missing: skip artifact upload, report missing token (R4.3)
            print(
                "Warning: No CI token found (GITHUB_TOKEN / CI_JOB_TOKEN / TMAC_TOKEN). "
                "Skipping artifact upload and comment publishing.",
                file=sys.stderr,
            )

        # ------------------------------------------------------------------
        # Step 4: Format the comment
        # ------------------------------------------------------------------
        formatter = CommentFormatter()
        max_length = 65536 if ctx.platform == "github" else 1_000_000

        introduced = 0
        resolved = 0
        if isinstance(result, DeltaScanResult):
            introduced = result.findings_introduced
            resolved = result.findings_resolved

        comment_ctx = CommentContext(
            fail_on=fail_on,
            artifact_ref=out_file,
            max_length=max_length,
            introduced=introduced,
            resolved=resolved,
        )
        body = formatter.format(result, comment_ctx)
        if result.issues:
            body += (
                f"\n\n> ⚠️ **Incomplete scan:** {len(result.issues)} file(s)/rule(s) could not be "
                "processed, so this result may be missing findings. See the job log.\n"
            )
        body = _secrets.redact(body, token)

        # ------------------------------------------------------------------
        # Step 5: Publish (only when token present, comment enabled, R3.6, R4.3)
        # ------------------------------------------------------------------
        if comment and token:
            publisher = self._build_publisher(ctx, token)
            if publisher is not None:
                try:
                    publisher.publish(ctx, body)
                    logger.debug("CIRunner: comment published successfully.")
                except NoPullRequestContext as exc:
                    msg = _secrets.redact(str(exc), token)
                    logger.debug("CIRunner: no PR context — skipping publish: %s", msg)
                except PublishPermissionError as exc:
                    msg = _secrets.redact(str(exc), token)
                    print(
                        f"Warning: Comment publish failed (permission error): {msg}",
                        file=sys.stderr,
                    )
                    # Artifact retained; do not change exit code (R3.7, R6.6)
                except PublishError as exc:
                    msg = _secrets.redact(str(exc), token)
                    print(
                        f"Warning: Comment publish failed: {msg}",
                        file=sys.stderr,
                    )
                    # Artifact retained; do not change exit code (R3.7, R6.6)
        elif comment and not token:
            # Already reported above; just log for debugging
            logger.debug("CIRunner: comment skipped — no token.")

        # ------------------------------------------------------------------
        # Step 6: Fail closed on an incomplete scan, else findings-based exit code
        # ------------------------------------------------------------------
        if result.issues:
            print(
                f"Warning: the scan is incomplete ({len(result.issues)} issue(s)):",
                file=sys.stderr,
            )
            for issue in result.issues:
                print(f"  [{issue.kind}] {_secrets.redact(issue.message, token)}", file=sys.stderr)
            if not lenient:
                return 3
        return self._compute_exit_code(result.findings, fail_on)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _build_reporter(fmt: str):
        """Return the reporter matching the requested format."""
        from tmac.reporters.html import HTMLReporter
        from tmac.reporters.json_report import JSONReporter
        from tmac.reporters.markdown import MarkdownReporter

        fmt = fmt.lower()
        if fmt == "html":
            return HTMLReporter()
        elif fmt == "json":
            return JSONReporter()
        return MarkdownReporter()

    @staticmethod
    def _build_publisher(ctx: CIContext, token: str):
        """Instantiate the appropriate publisher for the platform.

        Returns None when the platform is not recognized.
        """
        from tmac.ci.publisher import (
            GitHubCommentPublisher,
            GitLabCommentPublisher,
        )

        class _StdlibHttpTransport:
            """Minimal stdlib urllib-based HttpTransport."""

            def request(self, method, url, headers, body):
                import urllib.request as _req

                from tmac.ci.publisher import HttpResponse

                req = _req.Request(url, data=body, headers=headers or {}, method=method)
                try:
                    with _req.urlopen(req) as resp:
                        return HttpResponse(
                            status=resp.status,
                            body=resp.read().decode("utf-8", errors="replace"),
                        )
                except Exception as exc:
                    # Re-raise so publisher error handling can map HTTP codes
                    raise exc

        transport = _StdlibHttpTransport()

        platform = (ctx.platform or "").lower()
        if platform == "github":
            return GitHubCommentPublisher(transport, token)
        elif platform == "gitlab":
            return GitLabCommentPublisher(transport, token)
        else:
            logger.debug("CIRunner: unknown platform '%s' — skipping publish.", platform)
            return None
