import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore
from pydantic import ValidationError

from tmac.models.finding import ScanIssue
from tmac.models.rule import ThreatRule

logger = logging.getLogger(__name__)

REQUIRED_FILE_FIELDS = {"version", "rules"}
REQUIRED_RULE_FIELDS = {"id", "name", "resource_type", "check", "severity", "stride"}

RULES_DIR = Path(__file__).parent.parent / "rules"
BUILTIN_RULE_DIRS = (RULES_DIR / "aws", RULES_DIR / "cfn")


class RuleLoader:
    """Loads and parses the threat rules from YAML.

    Problems (unreadable files, invalid rules) are logged, skipped, and recorded
    in ``self.issues`` so callers can fail closed instead of scanning with fewer rules.
    """

    def __init__(self) -> None:
        self.issues: list[ScanIssue] = []

    def load_rules(self, extra_rules_dir: str | None = None) -> list[ThreatRule]:
        self.issues = []
        rules: dict[str, ThreatRule] = {}

        # Built-in rules: Terraform (aws/threats*.yaml, incl. threats_extended.yaml) and
        # CloudFormation (cfn/threats*.yaml). Rules only apply to their own resource_type,
        # so loading both never mixes frameworks.
        for builtin_dir in BUILTIN_RULE_DIRS:
            builtin_files = sorted(builtin_dir.glob("threats*.yaml"))
            if not builtin_files:
                self._issue(builtin_dir, "Built-in rules files not found")
            for threats_file in builtin_files:
                self._load_file(threats_file, rules)

        # Optional custom rules
        if extra_rules_dir:
            extra_path = Path(extra_rules_dir)
            if extra_path.exists() and extra_path.is_dir():
                for yaml_file in sorted(extra_path.glob("*.yaml")):
                    self._load_file(yaml_file, rules)
            else:
                self._issue(extra_path, "Rules directory not found")

        return list(rules.values())

    def _issue(self, file_path: Path, message: str) -> None:
        logger.warning("%s: %s", file_path, message)
        self.issues.append(ScanIssue(kind="rules", file_path=str(file_path), message=message))

    def _validate_file(self, data: dict[str, Any], file_path: Path) -> bool:
        missing = REQUIRED_FILE_FIELDS - set(data.keys())
        if missing:
            self._issue(file_path, f"File missing required fields: {sorted(missing)} — skipped")
            return False
        return True

    def _validate_rule(self, rule_data: dict[str, Any], file_path: Path) -> bool:
        missing = REQUIRED_RULE_FIELDS - set(rule_data.keys())
        if missing:
            rule_id = rule_data.get("id", "<unknown>")
            self._issue(file_path, f"Rule {rule_id} missing fields: {sorted(missing)} — skipped")
            return False
        return True

    def _load_file(self, file_path: Path, rules_dict: dict[str, ThreatRule]) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                self._issue(file_path, "File is empty or invalid — skipped")
                return

            if not self._validate_file(data, file_path):
                return

            for rule_data in data["rules"]:
                if not self._validate_rule(rule_data, file_path):
                    continue
                # Validate per rule so one bad rule doesn't drop the rest of the file.
                try:
                    rule = ThreatRule(**rule_data)
                except ValidationError as e:
                    self._issue(
                        file_path,
                        f"Rule {rule_data.get('id', '<unknown>')} is invalid — skipped: "
                        + "; ".join(err["msg"] for err in e.errors()),
                    )
                    continue
                # Overwrite if rule ID already exists
                rules_dict[rule.id] = rule
        # Any malformed rules file (bad YAML, wrong types, ...) must become a recorded
        # issue rather than crash the scan, so the catch-all is intentional.
        except Exception as e:  # noqa: BLE001
            self._issue(file_path, f"Failed to load rules: {e}")
