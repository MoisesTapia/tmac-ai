"""PR/MR comment formatter for TMAC v1.6.0 CI layer.

Renders a deterministic, idempotent Markdown comment body from a ScanResult
or DeltaScanResult.  Always begins with MARKER (R3.1).

Feature: tmac-v1-6-pr-agent
Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
           2.10, 2.11, 2.12, 2.13, 2.14, 3.1, 7.3, 7.4
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import PurePath
from urllib.parse import quote

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
    repo_url: str = ""  # Base GitHub repo URL for generating file links (optional)
    ref: str = "HEAD"  # Git ref the file links point at (the PR head, not the default branch)
    source_root: str = ""  # Scanned directory; finding paths are made relative to it


def _md_cell(text: str) -> str:
    """Make text safe inside a Markdown table cell / code span of the PR comment.

    Resource names and file paths come from the code under review, so they must not be
    able to break the table or inject Markdown/HTML into the comment.
    """
    return str(text).replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("`", "'")


def _repo_relative(file_path: str, source_root: str) -> str:
    """POSIX path relative to the scanned directory (or as given, minus a leading ./)."""
    if not file_path:
        return ""
    path = file_path
    if source_root and os.path.isabs(path):
        try:
            path = os.path.relpath(path, source_root)
        except ValueError:  # different drive on Windows
            pass
    posix = PurePath(path).as_posix()
    return posix.removeprefix("./")


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

        # Findings section — grouped by severity, each group collapsible
        lines.append("### Findings")
        if not ordered:
            lines.append("")
            lines.append("✅ No findings")
        else:
            lines.extend(self._render_collapsible_groups(ordered, ctx))

        lines.append("")
        lines.append(f"📎 Full report: {ctx.artifact_ref}")

        return "\n".join(lines)

    def _render_collapsible_groups(
        self, rows: list[Finding], ctx: CommentContext | None = None
    ) -> list[str]:
        """Render findings grouped by severity, each group in a <details> block."""
        groups: dict[str, list[Finding]] = {sev: [] for sev in _SEVERITY_ORDER}
        for f in rows:
            key = f.severity.lower()
            if key in groups:
                groups[key].append(f)

        lines: list[str] = []
        for sev in _SEVERITY_ORDER:
            group = groups[sev]
            if not group:
                continue
            emoji = _SEVERITY_EMOJI[sev]
            count = len(group)
            label = f"{emoji} {sev.capitalize()} — {count} finding{'s' if count != 1 else ''}"
            lines.append("")
            lines.append("<details>")
            lines.append(f"<summary>{label}</summary>")
            lines.append("")
            # Plan (delta) findings keep the NEW / MODIFIED / REMOVED action column.
            with_action = any(isinstance(f, DeltaFinding) for f in group)
            if with_action:
                lines.append("| Resource | Rule | Action | File | STRIDE | Mitigation |")
                lines.append("|----------|------|--------|------|--------|------------|")
            else:
                lines.append("| Resource | Rule | File | STRIDE | Mitigation |")
                lines.append("|----------|------|------|--------|------------|")
            for f in group:
                # Resource names and paths come from the scanned (possibly untrusted) code.
                resource = f"`{_md_cell(f.resource_type)}.{_md_cell(f.resource_name)}`"
                rule = f"`{_md_cell(f.rule_id)}`"
                stride = _md_cell(f.stride if isinstance(f.stride, str) else ", ".join(f.stride))
                mitigation = _md_cell(f.mitigation)[:120]
                # File + line: link to GitHub if repo_url available, otherwise plain text
                file_ref = self._file_ref(f, ctx)
                if with_action:
                    action = self._action_label(f)
                    lines.append(
                        f"| {resource} | {rule} | {action} | {file_ref} | {stride} | {mitigation} |"
                    )
                else:
                    lines.append(f"| {resource} | {rule} | {file_ref} | {stride} | {mitigation} |")
            lines.append("")
            lines.append("</details>")

        return lines

    def _file_ref(self, finding: Finding, ctx: CommentContext | None) -> str:
        """Return a file:line reference, linked to GitHub when repo_url is set."""
        if isinstance(finding, DeltaFinding):
            # Plan findings carry the resource address, not a source file.
            return f"`{_md_cell(finding.file_path)}`" if finding.file_path else ""

        rel_path = _repo_relative(finding.file_path or "", ctx.source_root if ctx else "")
        if not rel_path:
            return ""
        line = finding.line_number
        label = f"{rel_path}:{line}" if line > 0 else rel_path
        if ctx and ctx.repo_url:
            # e.g. https://github.com/owner/repo/blob/<pr-head>/examples/file.tf#L31
            anchor = f"#L{line}" if line > 0 else ""
            url = (
                f"{ctx.repo_url.rstrip('/')}/blob/{quote(ctx.ref or 'HEAD', safe='')}/"
                f"{quote(rel_path)}{anchor}"
            )
            return f"[`{_md_cell(label)}`]({url})"
        return f"`{_md_cell(label)}`"

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
            lines.extend(self._render_collapsible_groups(rows, ctx))

        lines.append("")
        lines.append(f"📎 Full report: {ctx.artifact_ref}")

        return "\n".join(lines)
