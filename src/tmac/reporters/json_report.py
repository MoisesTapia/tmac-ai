import json
from tmac.reporters.base import BaseReporter
from tmac.models.finding import ScanResult
from tmac.delta.models import DeltaFinding

SARIF_SEVERITY_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "none",
}


class JSONReporter(BaseReporter):
    """Generates a SARIF 2.1.0 compliant JSON report of scan results."""

    def generate(self, result: ScanResult) -> str:
        # Build unique rules from findings
        seen_rule_ids: set = set()
        rules = []
        for finding in result.findings:
            if finding.rule_id not in seen_rule_ids:
                seen_rule_ids.add(finding.rule_id)
                rule_entry = {
                    "id": finding.rule_id,
                    "name": finding.rule_name,
                    "shortDescription": {"text": finding.description},
                }
                if finding.references:
                    rule_entry["helpUri"] = finding.references[0]
                rules.append(rule_entry)

        # Build results array
        results = []
        for finding in result.findings:
            level = SARIF_SEVERITY_MAP.get(finding.severity.lower(), "warning")
            result_entry: dict = {
                "ruleId": finding.rule_id,
                "level": level,
                "message": {"text": finding.description},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file_path},
                        "region": {"startLine": finding.line_number},
                    }
                }],
            }
            if isinstance(finding, DeltaFinding):
                result_entry["properties"] = {
                    "changeAction": finding.change_action.value,
                    "valueBefore": finding.value_before,
                    "valueAfter": finding.value_after,
                }
            results.append(result_entry)

        sarif = {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": result.metadata.tool_name,
                        "version": result.metadata.version,
                        "informationUri": "https://github.com/tmac-security/tmac",
                        "rules": rules,
                    }
                },
                "results": results,
                # Unparseable files / invalid rules: SARIF consumers (e.g. GitHub code
                # scanning) see the run as unsuccessful instead of trusting a clean result.
                "invocations": [{
                    "executionSuccessful": not result.issues,
                    "toolExecutionNotifications": [
                        {
                            "level": "error",
                            "descriptor": {"id": f"tmac/{issue.kind}-error"},
                            "message": {"text": issue.message},
                            "locations": [{
                                "physicalLocation": {"artifactLocation": {"uri": issue.file_path}}
                            }],
                        }
                        for issue in result.issues
                    ],
                }],
            }],
        }

        return json.dumps(sarif, indent=2)
