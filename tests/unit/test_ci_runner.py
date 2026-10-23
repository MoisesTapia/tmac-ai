"""Unit tests for CIRunner dispatch, token-absent, and no-token-option scenarios.

Task 8.5:
  1. --no-delta-only delegates to the full Scanner path, NOT changed_tf_files (R1.9)
  2. --plan-file dispatches to DeltaScanner (R1.5)
  3. Token absent/empty → publish skipped, findings-based exit, warning emitted (R3.6, R4.3)
  4. tmac ci --help exposes no --token option (R4.2)

Feature: tmac-v1-6-pr-agent
Validates: Requirements 1.5, 1.9, 3.6, 4.2, 4.3
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tmac.cli import cli
from tmac.ci.publisher import CIContext
from tmac.models.finding import ScanMetadata, ScanResult, ScanStatistics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_scan_result(findings: Optional[list] = None) -> ScanResult:
    """Build a minimal valid ScanResult with zero findings."""
    return ScanResult(
        metadata=ScanMetadata(scanned_directory=".", execution_time_seconds=0.0),
        statistics=ScanStatistics(total_resources=0, total_findings=0),
        findings=findings or [],
        files_scanned=0,
        rules_loaded=0,
        files_failed=0,
    )


def _minimal_delta_result():
    """Build a minimal valid DeltaScanResult with zero findings."""
    from tmac.delta.models import DeltaScanResult

    return DeltaScanResult(
        metadata=ScanMetadata(scanned_directory="plan.json", execution_time_seconds=0.0),
        statistics=ScanStatistics(total_resources=0, total_findings=0),
        findings=[],
        files_scanned=1,
        rules_loaded=0,
        files_failed=0,
        findings_introduced=0,
        findings_resolved=0,
        resources_created=0,
        resources_updated=0,
        resources_deleted=0,
        plan_file="plan.json",
    )


def _minimal_ci_context(directory: str) -> CIContext:
    return CIContext(
        platform="github",
        repo="owner/repo",
        pr_number=None,  # no PR — avoids publish attempt
        base_ref="main",
        head_ref="HEAD",
        api_base="https://api.github.com",
        artifact_path="tmac-report.md",
    )


# ---------------------------------------------------------------------------
# Test 1: --no-delta-only delegates to Scanner, NOT changed_tf_files (R1.9)
# ---------------------------------------------------------------------------

def test_no_delta_only_uses_scanner(tmp_path):
    """--no-delta-only must delegate to Scanner.run_scan, not changed_tf_files (R1.9)."""
    # Create a minimal .tf file so Scanner can scan the directory
    tf_file = tmp_path / "main.tf"
    tf_file.write_text('resource "aws_s3_bucket" "test" { bucket = "test" }\n')

    scan_result = _minimal_scan_result()

    # Scanner and changed_tf_files are lazy-imported inside CIRunner.run(), so we
    # patch at their canonical module locations (the module where they live), not
    # at tmac.ci.runner which doesn't hold them at import time.
    with patch("tmac.scanner.Scanner") as MockScanner, \
         patch("tmac.ci.git_diff.changed_tf_files") as mock_changed_tf:

        mock_scanner_instance = MagicMock()
        mock_scanner_instance.run_scan.return_value = scan_result
        MockScanner.return_value = mock_scanner_instance

        from tmac.ci.runner import CIRunner

        ctx = _minimal_ci_context(str(tmp_path))
        runner = CIRunner()
        # Patch comment formatting so it doesn't fail
        with patch("tmac.ci.comment.CommentFormatter.format", return_value="<!-- tmac:pr-comment:v1 -->"):
            exit_code = runner.run(
                directory=str(tmp_path),
                plan_file=None,
                fail_on="high",
                report_fmt="md",
                output=str(tmp_path / "report.md"),
                delta_only=False,  # <-- --no-delta-only
                comment=False,     # disable comment publishing
                exclude=[],
                ctx=ctx,
            )

    # Scanner.run_scan MUST be called with include_paths=None (full scan)
    mock_scanner_instance.run_scan.assert_called_once()
    call_kwargs = mock_scanner_instance.run_scan.call_args
    # include_paths should be None (not restricted to a changed set)
    actual_include_paths = call_kwargs.kwargs.get("include_paths")
    assert actual_include_paths is None, (
        f"Expected include_paths=None for --no-delta-only, got {actual_include_paths!r}"
    )

    # changed_tf_files must NOT be called (we skip the diff entirely)
    mock_changed_tf.assert_not_called()

    # Exit code should be findings-based (0 since no findings)
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Test 2: --plan-file dispatches to DeltaScanner (R1.5)
# ---------------------------------------------------------------------------

def test_plan_file_uses_delta_scanner(tmp_path):
    """--plan-file must dispatch to DeltaScanner.run, not Scanner or changed_tf_files (R1.5)."""
    # Create a minimal valid plan file
    plan_data = {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": "aws_s3_bucket.test",
                "type": "aws_s3_bucket",
                "name": "test",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {"acl": "private"},
                },
            }
        ],
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan_data))

    delta_result = _minimal_delta_result()

    # DeltaScanner and Scanner are lazy-imported inside CIRunner.run(); patch at canonical locations.
    with patch("tmac.delta.scanner.DeltaScanner") as MockDeltaScanner, \
         patch("tmac.scanner.Scanner") as MockScanner, \
         patch("tmac.ci.git_diff.changed_tf_files") as mock_changed_tf:

        mock_delta_instance = MagicMock()
        mock_delta_instance.run.return_value = delta_result
        MockDeltaScanner.return_value = mock_delta_instance

        from tmac.ci.runner import CIRunner

        ctx = _minimal_ci_context(str(tmp_path))
        runner = CIRunner()

        with patch("tmac.ci.comment.CommentFormatter.format", return_value="<!-- tmac:pr-comment:v1 -->"):
            exit_code = runner.run(
                directory=str(tmp_path),
                plan_file=str(plan_file),  # <-- plan file mode
                fail_on="high",
                report_fmt="md",
                output=str(tmp_path / "report.md"),
                delta_only=True,
                comment=False,
                exclude=[],
                ctx=ctx,
            )

    # DeltaScanner.run MUST be called
    mock_delta_instance.run.assert_called_once()
    call_kwargs = mock_delta_instance.run.call_args
    # The plan_file argument must match
    passed_plan_file = call_kwargs.kwargs.get("plan_file") or (
        call_kwargs.args[0] if call_kwargs.args else None
    )
    assert passed_plan_file == str(plan_file), (
        f"DeltaScanner.run called with plan_file={passed_plan_file!r}, "
        f"expected {str(plan_file)!r}"
    )

    # Scanner and changed_tf_files must NOT be called
    MockScanner.return_value.run_scan.assert_not_called()
    mock_changed_tf.assert_not_called()

    # Exit code findings-based (0 — no findings)
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Test 3: Token absent/empty → publish skipped, findings-based exit (R3.6, R4.3)
# ---------------------------------------------------------------------------

def test_token_absent_skips_publish(tmp_path, monkeypatch):
    """Token absent → publish and upload skipped, findings-based exit, warning emitted (R3.6, R4.3)."""
    # Clear all token env vars
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
    monkeypatch.delenv("TMAC_TOKEN", raising=False)

    # Create a minimal .tf file
    tf_file = tmp_path / "main.tf"
    tf_file.write_text('resource "aws_s3_bucket" "test" { bucket = "test" }\n')

    scan_result = _minimal_scan_result()

    with patch("tmac.scanner.Scanner") as MockScanner, \
         patch("tmac.ci.publisher.GitHubCommentPublisher.publish") as mock_publish, \
         patch("tmac.ci.publisher.GitLabCommentPublisher.publish") as mock_gl_publish:

        mock_scanner_instance = MagicMock()
        mock_scanner_instance.run_scan.return_value = scan_result
        MockScanner.return_value = mock_scanner_instance

        from tmac.ci.runner import CIRunner

        ctx = CIContext(
            platform="github",
            repo="owner/repo",
            pr_number="42",   # PR context is set — publish would be attempted if token existed
            base_ref="main",
            head_ref="HEAD",
            api_base="https://api.github.com",
            artifact_path="tmac-report.md",
        )
        runner = CIRunner()

        import io
        import sys as _sys

        stderr_capture = io.StringIO()
        with patch("tmac.ci.comment.CommentFormatter.format", return_value="<!-- tmac:pr-comment:v1 -->"):
            # Capture stderr to check for warning message
            old_stderr = _sys.stderr
            _sys.stderr = stderr_capture
            try:
                exit_code = runner.run(
                    directory=str(tmp_path),
                    plan_file=None,
                    fail_on="high",
                    report_fmt="md",
                    output=str(tmp_path / "report.md"),
                    delta_only=False,  # skip git diff, go straight to scanner
                    comment=True,      # publishing is desired, but token is absent
                    exclude=[],
                    ctx=ctx,
                )
            finally:
                _sys.stderr = old_stderr

    warning_output = stderr_capture.getvalue()

    # No publish attempt was made (neither GitHub nor GitLab)
    mock_publish.assert_not_called()
    mock_gl_publish.assert_not_called()

    # The warning message must mention the missing token
    assert "token" in warning_output.lower(), (
        f"Expected a warning about missing token in stderr, got: {warning_output!r}"
    )

    # Exit code must be findings-based (not 3) — 0 since no findings
    assert exit_code != 3, (
        "Exit code must be findings-based, not 3 (which signals a hard error like bad refs)"
    )
    assert exit_code == 0, (
        f"Expected exit 0 (no findings above threshold), got {exit_code}"
    )


def test_token_absent_via_cli_skips_publish_no_exit_3(tmp_path, monkeypatch):
    """Via CliRunner: token absent → findings-based exit code, not exit 3 (R3.6, R4.3)."""
    # Clear token env vars
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
    monkeypatch.delenv("TMAC_TOKEN", raising=False)

    # Create a minimal scan directory with a .tf file
    tf_file = tmp_path / "main.tf"
    tf_file.write_text('resource "aws_s3_bucket" "clean" { bucket = "clean" }\n')

    scan_result = _minimal_scan_result()

    runner_cli = CliRunner()

    with patch("tmac.scanner.Scanner") as MockScanner, \
         patch("tmac.ci.comment.CommentFormatter.format", return_value="<!-- tmac:pr-comment:v1 -->"):

        mock_scanner_instance = MagicMock()
        mock_scanner_instance.run_scan.return_value = scan_result
        MockScanner.return_value = mock_scanner_instance

        result = runner_cli.invoke(
            cli,
            [
                "ci",
                "--dir", str(tmp_path),
                "--no-delta-only",
                "--no-comment",
                "--fail-on", "high",
                "--report", "md",
                "--output", str(tmp_path / "report.md"),
            ],
            catch_exceptions=False,
        )

    # Must NOT exit with 3 (which would indicate a hard error like bad refs)
    assert result.exit_code != 3, (
        f"Exit code 3 indicates a hard error — should be findings-based. "
        f"Output: {result.output!r}"
    )
    # Findings-based exit: 0 (no findings)
    assert result.exit_code == 0, (
        f"Expected exit 0 for clean scan, got {result.exit_code}. Output: {result.output!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: tmac ci --help exposes no --token option (R4.2)
# ---------------------------------------------------------------------------

def test_ci_help_no_token_option():
    """tmac ci --help must not expose --token (R4.2).

    The token is read exclusively from environment variables (GITHUB_TOKEN /
    CI_JOB_TOKEN / TMAC_TOKEN) and must never appear as a CLI option.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ["ci", "--help"])

    assert result.exit_code == 0, (
        f"tmac ci --help failed with exit code {result.exit_code}. "
        f"Output: {result.output!r}"
    )

    # --token must NOT appear as a CLI option
    assert "--token" not in result.output, (
        f"Found '--token' in `tmac ci --help` output — token must not be a CLI option (R4.2). "
        f"Full output:\n{result.output}"
    )

    # Confirm expected options ARE present to validate --help works correctly
    assert "--dir" in result.output or "-d" in result.output, (
        "Expected --dir in help output"
    )
    assert "--plan-file" in result.output or "-p" in result.output, (
        "Expected --plan-file in help output"
    )
    assert "--fail-on" in result.output, (
        "Expected --fail-on in help output"
    )


# ---------------------------------------------------------------------------
# Fail closed: an incomplete scan exits 3 in `tmac ci` too (unless lenient)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lenient, expected_exit", [(False, 3), (True, 0)])
def test_incomplete_scan_exits_3_unless_lenient(tmp_path, capsys, lenient, expected_exit):
    from tmac.ci.runner import CIRunner
    from tmac.models.finding import ScanIssue

    (tmp_path / "broken.tf").write_text('resource "aws_s3_bucket" "b" {\n  acl = \n', encoding="utf-8")
    with patch.dict(os.environ, {"GITHUB_TOKEN": "t0ken-value"}), patch(
        "tmac.ci.comment.CommentFormatter.format", return_value="<!-- tmac:pr-comment:v1 -->"
    ) as fmt:
        exit_code = CIRunner().run(
            directory=str(tmp_path),
            plan_file=None,
            fail_on="high",
            report_fmt="md",
            output=str(tmp_path / "report.md"),
            delta_only=False,
            comment=False,
            exclude=[],
            ctx=_minimal_ci_context(str(tmp_path)),
            lenient=lenient,
        )
    assert exit_code == expected_exit
    assert fmt.called  # the comment body is still built
    assert (tmp_path / "report.md").exists()  # and the report still written
    err = capsys.readouterr().err
    assert "the scan is incomplete" in err and "broken.tf" in err


def test_complete_scan_keeps_findings_based_exit(tmp_path):
    from tmac.ci.runner import CIRunner

    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "b" {\n  acl = "private"\n}\n')
    exit_code = CIRunner().run(
        directory=str(tmp_path),
        plan_file=None,
        fail_on="critical",
        report_fmt="md",
        output=str(tmp_path / "report.md"),
        delta_only=False,
        comment=False,
        exclude=[],
        ctx=_minimal_ci_context(str(tmp_path)),
    )
    assert exit_code == 0


def test_ci_command_exposes_lenient():
    assert "--lenient" in CliRunner().invoke(cli, ["ci", "--help"]).output
