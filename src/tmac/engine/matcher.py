from tmac.engine.evaluator import Evaluator
from tmac.models.finding import Finding
from tmac.models.resource import IgnoreMap, ResourceModel
from tmac.models.rule import ThreatRule


def group_rules_by_type(rules: list[ThreatRule]) -> dict[str, list[ThreatRule]]:
    """Index rules by resource_type so each resource only sees applicable rules."""
    rules_by_type: dict[str, list[ThreatRule]] = {}
    for rule in rules:
        rules_by_type.setdefault(rule.resource_type, []).append(rule)
    return rules_by_type


class Matcher:
    """Matches resources against threat rules."""

    def __init__(self) -> None:
        self.evaluator = Evaluator()

    def match(
        self,
        resources: list[ResourceModel],
        rules: list[ThreatRule],
        ignore_map: IgnoreMap | None = None,
    ) -> list[Finding]:
        findings: list[Finding] = []
        ignore_map = ignore_map or {}
        rules_by_type = group_rules_by_type(rules)

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
