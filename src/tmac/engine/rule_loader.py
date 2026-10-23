import logging
import yaml  # type: ignore
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import ValidationError
from tmac.models.finding import ScanIssue
from tmac.models.rule import ThreatRule

logger = logging.getLogger(__name__)

REQUIRED_FILE_FIELDS = {"version", "rules"}
REQUIRED_RULE_FIELDS = {"id", "name", "resource_type", "check", "severity", "stride"}


class RuleLoader:
    """Loads and parses the threat rules from YAML.

    Problems (unreadable files, invalid rules) are logged, skipped, and recorded
    in ``self.issues`` so callers can fail closed instead of scanning with fewer rules.
    """

    def __init__(self) -> None:
        self.issues: List[ScanIssue] = []

    def load_rules(self, extra_rules_dir: Optional[str] = None) -> List[ThreatRule]:
        self.issues = []
        rules: Dict[str, ThreatRule] = {}

        # Load built-in rules
        base_dir = Path(__file__).parent.parent / "rules" / "aws"
        threats_file = base_dir / "threats.yaml"

        if threats_file.exists():
            self._load_file(threats_file, rules)
        else:
            self._issue(threats_file, "Built-in rules file not found")

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

    def _validate_file(self, data: dict, file_path: Path) -> bool:
        missing = REQUIRED_FILE_FIELDS - set(data.keys())
        if missing:
            self._issue(file_path, f"File missing required fields: {sorted(missing)} — skipped")
            return False
        return True

    def _validate_rule(self, rule_data: dict, file_path: Path) -> bool:
        missing = REQUIRED_RULE_FIELDS - set(rule_data.keys())
        if missing:
            rule_id = rule_data.get("id", "<unknown>")
            self._issue(file_path, f"Rule {rule_id} missing fields: {sorted(missing)} — skipped")
            return False
        return True

    def _load_file(self, file_path: Path, rules_dict: Dict[str, ThreatRule]) -> None:
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
        except Exception as e:
            self._issue(file_path, f"Failed to load rules: {e}")
