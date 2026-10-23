"""Unit tests for the CommentFormatter (task 5.12).

Validates:
- Headings Severity, Resource, Rule, Action are present in rendered output (R2.11)
- Empty finding set renders "✅ No findings" block instead of a table (R2.5)

Feature: tmac-v1-6-pr-agent
Validates: Requirements 2.5, 2.11
"""

from __future__ import annotations

from tmac.ci.comment import MARKER, CommentContext, CommentFormatter
from tmac.delta.models import ChangeAction, DeltaFinding
from tmac.models.finding import Finding, ScanMetadata, ScanResult, ScanStatistics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scan_result(findings) -> ScanResult:
    return ScanResult(
        metadata=ScanMetadata(scanned_directory="test"),
        statistics=ScanStatistics(total_findings=len(findings)),
        findings=findings,
    )


def _default_ctx(**kwargs) -> CommentContext:
    defaults = {
        "fail_on": "high",
        "artifact_ref": "https://example.com/report",
        "max_length": 65536,
        "introduced": 0,
        "resolved": 0,
    }
    defaults.update(kwargs)
    return CommentContext(**defaults)


def _make_finding(
    *,
    rule_id: str = "TMAC-AWS-S3-001",
    severity: str = "High",
    resource_type: str = "aws_s3_bucket",
    resource_name: str = "example",
    change_action: ChangeAction | None = None,
) -> Finding:
    base = {
        "rule_id": rule_id,
        "rule_name": "Test Rule",
        "severity": severity,
        "stride": "Tampering",
        "resource_type": resource_type,
        "resource_name": resource_name,
        "file_path": f"{resource_type}.{resource_name}",
        "line_number": 1,
        "matched_attribute": "acl",
        "description": "A test finding.",
        "mitigation": "Fix it.",
    }
    if change_action is not None:
        return DeltaFinding(
            **base,
            change_action=change_action,
            changed_attribute="acl",
            value_before="private",
            value_after="public-read",
        )
    return Finding(**base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHeadingsPresent:
    """Assert required column headings appear in the rendered output (R2.11)."""

    def test_headings_present_with_findings(self):
        """All four column headings must appear when findings are present."""
        finding = _make_finding(change_action=ChangeAction.create)
        result = _make_scan_result([finding])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)

        assert "Severity" in rendered, "Heading 'Severity' missing"
        assert "Resource" in rendered, "Heading 'Resource' missing"
        assert "Rule" in rendered, "Heading 'Rule' missing"
        assert "Action" in rendered, "Heading 'Action' missing"

    def test_headings_present_in_severity_breakdown(self):
        """The Severity heading must appear in the breakdown table even with no findings."""
        result = _make_scan_result([])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)

        assert "Severity" in rendered, "Heading 'Severity' missing for empty result"

    def test_headings_present_with_plain_finding(self):
        """Headings must appear for a plain Finding (not DeltaFinding)."""
        finding = _make_finding()
        result = _make_scan_result([finding])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)

        assert "Severity" in rendered
        assert "Resource" in rendered
        assert "Rule" in rendered
        assert "Action" in rendered


class TestEmptyFindingSet:
    """Assert empty finding set renders 'No findings' block, not a findings table (R2.5)."""

    def test_empty_findings_renders_no_findings_block(self):
        """Empty result must contain the explicit no-findings indicator."""
        result = _make_scan_result([])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)

        assert "✅ No findings" in rendered, "Expected '✅ No findings' block for empty finding set"

    def test_empty_findings_does_not_render_table_rows(self):
        """Empty result must not contain finding table rows (pipe-separated data rows)."""
        result = _make_scan_result([])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)

        # The findings table header row pattern: | Severity | Resource | Rule | Action |
        # should not appear when there are no findings
        lines = rendered.splitlines()
        finding_table_header = "| Severity | Resource | Rule | Action |"
        assert (
            finding_table_header not in lines
        ), "Finding table header must not appear when no findings exist"

    def test_empty_findings_approved_badge(self):
        """Empty result should yield APPROVED badge."""
        result = _make_scan_result([])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)
        assert "APPROVED" in rendered

    def test_marker_present_even_for_empty(self):
        """MARKER must be present and at start even for empty findings."""
        result = _make_scan_result([])
        ctx = _default_ctx()
        rendered = CommentFormatter().format(result, ctx)
        assert rendered.startswith(MARKER)


class TestStatusBadge:
    """Unit tests for _status_badge."""

    def test_empty_is_approved(self):
        assert CommentFormatter()._status_badge([], "high") == "APPROVED"

    def test_blocked_when_finding_at_threshold(self):
        finding = _make_finding(severity="High")
        assert CommentFormatter()._status_badge([finding], "high") == "BLOCKED"

    def test_blocked_when_finding_above_threshold(self):
        finding = _make_finding(severity="Critical")
        assert CommentFormatter()._status_badge([finding], "high") == "BLOCKED"

    def test_warning_when_finding_below_threshold(self):
        finding = _make_finding(severity="Low")
        assert CommentFormatter()._status_badge([finding], "high") == "WARNING"

    def test_warning_when_only_info_and_threshold_high(self):
        finding = _make_finding(severity="Info")
        assert CommentFormatter()._status_badge([finding], "high") == "WARNING"


class TestActionLabel:
    """Unit tests for _action_label."""

    def test_create_maps_to_new(self):
        f = _make_finding(change_action=ChangeAction.create)
        assert CommentFormatter()._action_label(f) == "NEW"

    def test_update_maps_to_modified(self):
        f = _make_finding(change_action=ChangeAction.update)
        assert CommentFormatter()._action_label(f) == "MODIFIED"

    def test_replace_maps_to_modified(self):
        f = _make_finding(change_action=ChangeAction.replace)
        assert CommentFormatter()._action_label(f) == "MODIFIED"

    def test_delete_maps_to_removed(self):
        f = _make_finding(change_action=ChangeAction.delete)
        assert CommentFormatter()._action_label(f) == "REMOVED"

    def test_plain_finding_returns_empty(self):
        f = _make_finding()
        assert CommentFormatter()._action_label(f) == ""


class TestSeverityBreakdown:
    """Unit tests for _severity_breakdown."""

    def test_all_levels_zero_when_empty(self):
        bd = CommentFormatter()._severity_breakdown([])
        assert bd == {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

    def test_counts_correct_for_mixed_findings(self):
        findings = [
            _make_finding(severity="Critical"),
            _make_finding(severity="Critical"),
            _make_finding(severity="High"),
            _make_finding(severity="Low"),
        ]
        bd = CommentFormatter()._severity_breakdown(findings)
        assert bd["critical"] == 2
        assert bd["high"] == 1
        assert bd["medium"] == 0
        assert bd["low"] == 1
        assert bd["info"] == 0


class TestTruncation:
    """Unit tests for _truncate."""

    def test_no_truncation_when_fits(self):
        findings = [_make_finding() for _ in range(3)]
        ctx = _default_ctx(max_length=65536)
        formatter = CommentFormatter()
        ordered = formatter._ordered_rows(findings)
        kept, omitted = formatter._truncate(ordered, ctx)
        assert len(kept) == 3
        assert omitted == 0

    def test_truncates_when_over_budget(self):
        # Make many findings; max_length is skeleton + tiny buffer so rows get dropped
        findings = [_make_finding(rule_id=f"TMAC-TST-X01-{i:03d}") for i in range(20)]
        formatter = CommentFormatter()
        ctx_probe = _default_ctx(max_length=65536)
        min_body = formatter._render_body([], ctx_probe, omitted=20)
        max_length = len(min_body) + 30  # enough for 0 rows, not for 20
        ctx = _default_ctx(max_length=max_length)
        ordered = formatter._ordered_rows(findings)
        kept, omitted = formatter._truncate(ordered, ctx)
        assert omitted > 0
        assert len(kept) + omitted == 20

    def test_truncation_notice_in_rendered_output(self):
        # Use enough findings to force truncation; max_length just over the
        # zero-row skeleton so some rows are dropped but the body still fits.
        findings = [_make_finding(rule_id=f"TMAC-TST-X01-{i:03d}") for i in range(30)]
        # Compute the minimum body size (0 rows) to pick a max_length that is
        # at least that large so the budget constraint can be satisfied.
        formatter = CommentFormatter()
        ctx_probe = _default_ctx(max_length=65536)
        min_body = formatter._render_body([], ctx_probe, omitted=30)
        # Add a small buffer so 0 rows fits but full 30 rows does not
        max_length = len(min_body) + 50
        ctx = _default_ctx(max_length=max_length)
        result = _make_scan_result(findings)
        rendered = formatter.format(result, ctx)
        assert "omitted" in rendered.lower()
        assert len(rendered) <= ctx.max_length

    def test_empty_findings_no_truncation(self):
        ctx = _default_ctx(max_length=100)
        formatter = CommentFormatter()
        kept, omitted = formatter._truncate([], ctx)
        assert kept == []
        assert omitted == 0
