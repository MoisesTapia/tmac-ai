"""DeltaScanner — orchestrates the delta risk analysis pipeline.

TMAC v1.1.0 "Ixtla"
Validates: Requirements 3.1–3.8, 6.1–6.6
"""

import logging
import time
from typing import List, Optional, Tuple

from tmac.delta.models import ChangeAction, DeltaFinding, DeltaScanResult, PlannedChange
from tmac.engine.evaluator import Evaluator
from tmac.engine.matcher import group_rules_by_type
from tmac.engine.rule_loader import RuleLoader
from tmac.models.finding import ScanMetadata, ScanStatistics
from tmac.models.resource import IgnoreMap, ResourceIgnoreMap, ResourceModel
from tmac.models.rule import ThreatRule
from tmac.parsers.tfplan import TfplanParser

logger = logging.getLogger(__name__)


class DeltaScanError(Exception):
    """Raised when the delta scan pipeline cannot proceed."""
    pass


class DeltaScanner:
    """Orchestrates the delta risk analysis pipeline for tfplan.json files.

    Analogous to Scanner (v1.0.0) but oriented to PlannedChange[] instead of .tf files.
    Reuses RuleLoader and Evaluator without modifications.
    """

    def __init__(self) -> None:
        self._rule_loader = RuleLoader()
        self._evaluator = Evaluator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        plan_file: str,
        rules_dir: Optional[str] = None,
        ignore_map: Optional[IgnoreMap] = None,
        min_severity: str = "all",
        verbose: bool = False,
        resource_ignores: Optional[ResourceIgnoreMap] = None,
    ) -> DeltaScanResult:
        """Execute the full delta analysis pipeline.

        Suppressions: ``ignore_map`` is keyed by plan address
        (e.g. ``module.vpc.aws_subnet.private``); ``resource_ignores`` is keyed by
        ``(resource_type, resource_name)``, as collected from tmac:ignore comments in
        the .tf sources. Both accept ["*"] or a list of rule IDs.

        Raises:
            DeltaScanError: if the plan file is missing, invalid JSON, or lacks
                            the 'resource_changes' field.
        """
        start = time.time()
        ignore_map = ignore_map or {}
        resource_ignores = resource_ignores or {}

        parser = TfplanParser()
        changes = parser.parse_plan(plan_file)

        # parse_plan() returns [] on error — distinguish error from empty plan
        self._validate_plan_file(plan_file)

        rules = self._rule_loader.load_rules(rules_dir)
        logger.debug("Loaded %d rules", len(rules))
        rules_by_type = group_rules_by_type(rules)

        counts = {ChangeAction.create: 0, ChangeAction.update: 0,
                  ChangeAction.delete: 0, ChangeAction.replace: 0}
        all_findings: List[DeltaFinding] = []
        total_resolved = 0

        for change in changes:
            counts[change.action] = counts.get(change.action, 0) + 1

            ignored = ignore_map.get(change.address, []) + resource_ignores.get(
                (change.resource_type, change.resource_name), []
            )
            if "*" in ignored:
                logger.debug("Ignoring resource %s (tmac:ignore *)", change.address)
                continue

            applicable = [
                r for r in rules_by_type.get(change.resource_type, []) if r.id not in ignored
            ]
            logger.debug(
                "Evaluating %d rules against %s (%s)",
                len(applicable), change.address, change.action.value,
            )
            introduced, resolved = self._evaluate_change(change, applicable)
            all_findings.extend(introduced)
            total_resolved += resolved

        logger.debug(
            "Parsed %d planned changes from %s (create=%d, update=%d, delete=%d, replace=%d)",
            len(changes), plan_file,
            counts.get(ChangeAction.create, 0),
            counts.get(ChangeAction.update, 0),
            counts.get(ChangeAction.delete, 0),
            counts.get(ChangeAction.replace, 0),
        )

        stats = ScanStatistics.from_findings(all_findings, total_resources=len(changes))

        return DeltaScanResult(
            metadata=ScanMetadata(
                scanned_directory=plan_file,
                execution_time_seconds=time.time() - start,
            ),
            statistics=stats,
            findings=all_findings,
            files_scanned=1,
            rules_loaded=len(rules),
            findings_introduced=len(all_findings),
            findings_resolved=total_resolved,
            resources_created=counts.get(ChangeAction.create, 0),
            resources_updated=counts.get(ChangeAction.update, 0) + counts.get(ChangeAction.replace, 0),
            resources_deleted=counts.get(ChangeAction.delete, 0),
            plan_file=plan_file,
            issues=list(self._rule_loader.issues),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_plan_file(self, plan_file: str) -> None:
        """Raise DeltaScanError if the plan file is not a valid tfplan.json."""
        import json
        import os

        if not os.path.exists(plan_file):
            raise DeltaScanError(f"Plan file not found: {plan_file}")
        try:
            with open(plan_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise DeltaScanError(f"Invalid JSON in plan file {plan_file}: {exc}") from exc
        except Exception as exc:
            raise DeltaScanError(f"Cannot read plan file {plan_file}: {exc}") from exc

        if not isinstance(data, dict) or "resource_changes" not in data:
            raise DeltaScanError(
                f"Plan file {plan_file} does not contain 'resource_changes' field"
            )

    def _build_resource_model(
        self,
        change: PlannedChange,
        use_after: bool = True,
    ) -> ResourceModel:
        """Build a temporary ResourceModel from a PlannedChange's before or after attributes."""
        attributes = change.after if use_after else change.before
        return ResourceModel(
            resource_type=change.resource_type,
            name=change.resource_name,
            attributes=attributes or {},
            source_file=change.address,
            line_number=0,
        )

    def _evaluate_change(
        self,
        change: PlannedChange,
        rules: List[ThreatRule],
    ) -> Tuple[List[DeltaFinding], int]:
        """Evaluate a PlannedChange against all rules according to its action.

        Returns:
            (introduced_findings, resolved_count)

        Logic per action:
            create  → evaluate after  → matches are introduced
            delete  → evaluate before → matches are resolved
            update/replace → evaluate after and before:
                             in after but not before → introduced
                             in before but not after → resolved
        """
        introduced: List[DeltaFinding] = []
        resolved = 0

        # Filter rules applicable to this resource type
        applicable = [r for r in rules if r.resource_type == change.resource_type]

        if change.action == ChangeAction.create:
            for rule in applicable:
                if self._evaluator.evaluate(rule.check, change.after or {}):
                    introduced.append(self._make_delta_finding(rule, change, ChangeAction.create))

        elif change.action == ChangeAction.delete:
            for rule in applicable:
                if self._evaluator.evaluate(rule.check, change.before or {}):
                    resolved += 1

        else:  # update or replace
            after_attrs = change.after or {}
            before_attrs = change.before or {}
            for rule in applicable:
                in_after = self._evaluator.evaluate(rule.check, after_attrs)
                in_before = self._evaluator.evaluate(rule.check, before_attrs)
                if in_after and not in_before:
                    introduced.append(self._make_delta_finding(rule, change, change.action))
                elif in_before and not in_after:
                    resolved += 1

        return introduced, resolved

    def _make_delta_finding(
        self,
        rule: ThreatRule,
        change: PlannedChange,
        action: ChangeAction,
    ) -> DeltaFinding:
        """Construct a DeltaFinding from a matched rule and PlannedChange."""
        attribute = rule.check.attribute
        # Resolve dotted paths (e.g. "ingress.cidr_blocks") the same way the evaluator does.
        resolve = self._evaluator.resolve_attribute
        value_before = resolve(attribute, change.before) if change.before else None
        value_after = resolve(attribute, change.after) if change.after else None

        return DeltaFinding(
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            stride=rule.stride,
            resource_type=change.resource_type,
            resource_name=change.resource_name,
            file_path=change.address,
            line_number=0,
            matched_attribute=attribute,
            description=rule.description,
            mitigation=rule.mitigation,
            references=rule.references,
            tags=rule.tags,
            change_action=action,
            changed_attribute=attribute,
            value_before=value_before,
            value_after=value_after,
        )
