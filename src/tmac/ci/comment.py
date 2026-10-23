"""PR/MR comment formatter for TMAC v1.6.0 CI layer.

Renders a deterministic, idempotent Markdown comment body from a ScanResult
or DeltaScanResult.  Always begins with MARKER (R3.1).

Feature: tmac-v1-6-pr-agent
Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
           2.10, 2.11, 2.12, 2.13, 2.14, 3.1, 7.3, 7.4
"""

from __future__ import annotations

from dataclasses import dataclass

from tmac.delta.models import ChangeAction, DeltaFinding
from tmac.engine.severity import SEVERITY_LEVELS
from tmac.models.finding import Finding, ScanResult

# ---------------------------------------------------------------------------
# Idempotency marker — must appear at the very top of every rendered comment
# ---------------------------------------------------------------------------

MARKER = "<!-- tmac:pr-comment:v1 -->"

# ---------------------------------------------------------------------------
# Severity display helpers
# ---------------------------------------------------------------------------

_SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    "info": "🔵",
}

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

_STATUS_EMOJI = {
    "APPROVED": "✅",
    "WARNING": "⚠️",
    "BLOCKED": "🚫",
}


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommentContext:
    """Inputs the formatter needs that are not on the scan result."""

    fail_on: str  # Fail_On_Threshold (e.g. "high")
    artifact_ref: str  # URL / path of the full Report_Artifact (R2.12)
    max_length: int  # Platform maximum comment length (R2.13)
    introduced: int  # Newly introduced threat count (R2.1)
    resolved: int  # Resolved threat count (R2.1)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------


class CommentFormatter:
    """Renders a deterministic Markdown PR/MR comment from a scan result."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, result: ScanResult, ctx: CommentContext) -> str:
        """Produce the full Markdown comment body, always starting with MARKER.

        Deterministic: identical (result, ctx) input → identical string.
        """
        findings: list[Finding] = list(result.findings)

        badge = self._status_badge(findings, ctx.fail_on)
        badge_emoji = _STATUS_EMOJI[badge]
        breakdown = self._severity_breakdown(findings)
        ordered = self._ordered_rows(findings)
        ordered, omitted = self._truncate(ordered, ctx)

        lines: list[str] = [MARKER, ""]
        lines.append("## 🛡️ TMAC Threat Model Analysis")
        lines.append("")
        lines.append(f"**Status:** {badge_emoji} {badge}")
        lines.append("")
        lines.append(
            f"**Summary:** {ctx.introduced} threat{'s' if ctx.introduced != 1 else ''} introduced, "
            f"{ctx.resolved} resolved"
        )
        lines.append("")

        # Severity breakdown table
        lines.append("### Severity Breakdown")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in _SEVERITY_ORDER:
            emoji = _SEVERITY_EMOJI[sev]
            lines.append(f"| {emoji} {sev.capitalize()} | {breakdown[sev]} |")
        lines.append("")

        # Truncation notice (when applicable)
        if omitted > 0:
            lines.append(
                f"⚠️ {omitted} finding{'s' if omitted != 1 else ''} omitted due to comment length limit. "
                "See full report for complete results."
            )
            lines.append("")

        # Findings section
        lines.append("### Findings")
        if not ordered:
            lines.append("")
            lines.append("✅ No findings")
        else:
            lines.append("| Severity | Resource | Rule | Action |")
            lines.append("|----------|----------|------|--------|")
            for finding in ordered:
                sev_lower = finding.severity.lower()
                sev_emoji = _SEVERITY_EMOJI.get(sev_lower, "")
                resource = f"`{finding.resource_type}.{finding.resource_name}`"
                rule = f"`{finding.rule_id}`"
                action = self._action_label(finding)
                lines.append(f"| {sev_emoji} {finding.severity} | {resource} | {rule} | {action} |")

        lines.append("")
        lines.append(f"📎 Full report: {ctx.artifact_ref}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers (unit-tested directly)
    # ------------------------------------------------------------------

    def _status_badge(self, findings: list[Finding], fail_on: str) -> str:
        """Return one of BLOCKED, WARNING, APPROVED.

        - empty findings → APPROVED  (R2.7)
        - any finding severity >= fail_on → BLOCKED  (R2.8)
        - findings present but none meet threshold → WARNING  (R2.9)
        """
        if not findings:
            return "APPROVED"

        threshold = SEVERITY_LEVELS.get(fail_on.lower(), SEVERITY_LEVELS["critical"])
        for f in findings:
            if SEVERITY_LEVELS.get(f.severity.lower(), -1) >= threshold:
                return "BLOCKED"

        return "WARNING"

    def _severity_breakdown(self, findings: list[Finding]) -> dict[str, int]:
        """Return all five severity levels, zero-filled. (R2.2)"""
        breakdown: dict[str, int] = {sev: 0 for sev in _SEVERITY_ORDER}
        for f in findings:
            key = f.severity.lower()
            if key in breakdown:
                breakdown[key] += 1
        return breakdown

    def _ordered_rows(self, findings: list[Finding]) -> list[Finding]:
        """Sort by severity desc, then resource address asc. (R2.4, R7.3)"""

        def sort_key(f: Finding) -> tuple[int, str]:
            sev_val = SEVERITY_LEVELS.get(f.severity.lower(), -1)
            address = f"{f.resource_type}.{f.resource_name}"
            return (-sev_val, address)

        return sorted(findings, key=sort_key)

    def _action_label(self, finding: Finding) -> str:
        """Map change_action to label: create→NEW, update|replace→MODIFIED, delete→REMOVED. (R2.10)

        For plain Finding objects (no change_action), returns empty string.
        """
        if not isinstance(finding, DeltaFinding):
            return ""
        action = finding.change_action
        if action == ChangeAction.create:
            return "NEW"
        elif action in (ChangeAction.update, ChangeAction.replace):
            return "MODIFIED"
        elif action == ChangeAction.delete:
            return "REMOVED"
        return ""

    def _truncate(
        self,
        rows: list[Finding],
        ctx: CommentContext,
    ) -> tuple[list[Finding], int]:
        """Drop rows from the END of ordered list until rendered body fits max_length. (R2.13, R7.4)

        Returns (kept_rows, omitted_count).  The caller prepends the truncation
        notice; this method just determines the right subset.
        """
        total = len(rows)

        # Fast path: no truncation needed
        if not rows:
            return rows, 0

        # Check if full set already fits by rendering a probe
        if len(self._render_body(rows, ctx, omitted=0)) <= ctx.max_length:
            return rows, 0

        # Binary-search style: drop from the end one at a time
        kept = list(rows)
        while kept:
            kept = kept[:-1]
            omitted = total - len(kept)
            rendered = self._render_body(kept, ctx, omitted=omitted)
            if len(rendered) <= ctx.max_length:
                return kept, omitted

        # Even 0 rows still exceeds the budget — return empty with all omitted
        return [], total

    def _render_body(
        self,
        rows: list[Finding],
        ctx: CommentContext,
        omitted: int,
    ) -> str:
        """Render the full body with a specific row subset and omitted count.

        Used internally by _truncate to probe lengths.
        """
        badge = self._status_badge(rows, ctx.fail_on)
        badge_emoji = _STATUS_EMOJI[badge]
        breakdown = self._severity_breakdown(rows)

        lines: list[str] = [MARKER, ""]
        lines.append("## 🛡️ TMAC Threat Model Analysis")
        lines.append("")
        lines.append(f"**Status:** {badge_emoji} {badge}")
        lines.append("")
        lines.append(
            f"**Summary:** {ctx.introduced} threat{'s' if ctx.introduced != 1 else ''} introduced, "
            f"{ctx.resolved} resolved"
        )
        lines.append("")

        lines.append("### Severity Breakdown")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in _SEVERITY_ORDER:
            emoji = _SEVERITY_EMOJI[sev]
            lines.append(f"| {emoji} {sev.capitalize()} | {breakdown[sev]} |")
        lines.append("")

        if omitted > 0:
            lines.append(
                f"⚠️ {omitted} finding{'s' if omitted != 1 else ''} omitted due to comment length limit. "
                "See full report for complete results."
            )
            lines.append("")

        lines.append("### Findings")
        if not rows:
            lines.append("")
            lines.append("✅ No findings")
        else:
            lines.append("| Severity | Resource | Rule | Action |")
            lines.append("|----------|----------|------|--------|")
            for finding in rows:
                sev_lower = finding.severity.lower()
                sev_emoji = _SEVERITY_EMOJI.get(sev_lower, "")
                resource = f"`{finding.resource_type}.{finding.resource_name}`"
                rule = f"`{finding.rule_id}`"
                action = self._action_label(finding)
                lines.append(f"| {sev_emoji} {finding.severity} | {resource} | {rule} | {action} |")

        lines.append("")
        lines.append(f"📎 Full report: {ctx.artifact_ref}")

        return "\n".join(lines)
