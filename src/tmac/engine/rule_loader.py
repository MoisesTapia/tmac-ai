import logging
import yaml  # type: ignore
from pathlib import Path
from typing import List, Dict, Optional
from tmac.models.rule import ThreatRule

logger = logging.getLogger(__name__)

REQUIRED_FILE_FIELDS = {"version", "rules"}
REQUIRED_RULE_FIELDS = {"id", "name", "resource_type", "check", "severity", "stride"}


class RuleLoader:
    """Loads and parses the threat rules from YAML."""

    def load_rules(self, extra_rules_dir: Optional[str] = None) -> List[ThreatRule]:
        rules: Dict[str, ThreatRule] = {}

        # Load built-in rules
        base_dir = Path(__file__).parent.parent / "rules" / "aws"
        threats_file = base_dir / "threats.yaml"

        if threats_file.exists():
            self._load_file(threats_file, rules)

        # Optional custom rules
        if extra_rules_dir:
            extra_path = Path(extra_rules_dir)
            if extra_path.exists() and extra_path.is_dir():
                for yaml_file in sorted(extra_path.glob("*.yaml")):
                    self._load_file(yaml_file, rules)

        return list(rules.values())

    def _validate_file(self, data: dict, file_path: Path) -> bool:
        missing = REQUIRED_FILE_FIELDS - set(data.keys())
        if missing:
            logger.warning(
                "File %s missing required fields: %s — skipping", file_path, missing
            )
            return False
        return True

    def _validate_rule(self, rule_data: dict, file_path: Path) -> bool:
        missing = REQUIRED_RULE_FIELDS - set(rule_data.keys())
        if missing:
            rule_id = rule_data.get("id", "<unknown>")
            logger.warning(
                "Rule %s in %s missing fields: %s — skipping", rule_id, file_path, missing
            )
            return False
        return True

    def _load_file(self, file_path: Path, rules_dict: Dict[str, ThreatRule]) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning("File %s is empty or invalid — skipping", file_path)
                return

            if not self._validate_file(data, file_path):
                return

            for rule_data in data["rules"]:
                if not self._validate_rule(rule_data, file_path):
                    continue
                rule = ThreatRule(**rule_data)
                # Overwrite if rule ID already exists
                rules_dict[rule.id] = rule
        except Exception as e:
            logger.warning("Failed to load rules from %s: %s", file_path, e)
