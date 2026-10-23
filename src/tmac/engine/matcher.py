from typing import Dict, List, Optional
from tmac.models.resource import ResourceModel
from tmac.models.rule import ThreatRule
from tmac.models.finding import Finding
from tmac.engine.evaluator import Evaluator

# IgnoreMap: resource_name → ["*"] (global) or ["RULE-ID-1", ...] (per-rule)
IgnoreMap = Dict[str, List[str]]


class Matcher:
    """Matches resources against threat rules."""

    def __init__(self) -> None:
        self.evaluator = Evaluator()

    def match(
        self,
        resources: List[ResourceModel],
        rules: List[ThreatRule],
        ignore_map: Optional[IgnoreMap] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []
        ignore_map = ignore_map or {}

        # Group rules by resource type for optimization
        rules_by_type: dict[str, List[ThreatRule]] = {}
        for rule in rules:
            if rule.resource_type not in rules_by_type:
                rules_by_type[rule.resource_type] = []
            rules_by_type[rule.resource_type].append(rule)

        for resource in resources:
            # Suppressions bound to the resource itself, plus any caller-supplied
            # name-based ignore_map (legacy API).
            ignored_rules = resource.ignored_rules + ignore_map.get(resource.name, [])
            # Global ignore — skip all rules for this resource
            if "*" in ignored_rules:
                continue

            applicable_rules = rules_by_type.get(resource.resource_type, [])
            for rule in applicable_rules:
                # Per-rule ignore
                if rule.id in ignored_rules:
                    continue

                if self.evaluator.evaluate(rule.check, resource.attributes):
                    findings.append(
                        Finding(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            stride=rule.stride,
                            resource_type=resource.resource_type,
                            resource_name=resource.name,
                            file_path=resource.source_file,
                            line_number=resource.line_number,
                            matched_attribute=rule.check.attribute,
                            description=rule.description,
                            mitigation=rule.mitigation,
                            references=rule.references,
                            tags=rule.tags,
                        )
                    )
        return findings
