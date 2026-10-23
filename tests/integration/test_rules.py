"""
Parametrized integration tests for TMAC rules.

Each rule is tested with a positive fixture (should produce a Finding)
and a negative fixture (should produce zero Findings).

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5
"""

import re
from pathlib import Path

import pytest
import yaml

from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader
from tmac.parsers.terraform import TerraformParser

RULE_FIXTURES = [
    ("TMAC-AWS-S3-001", "s3_public_acl.tf", True),
    ("TMAC-AWS-S3-001", "s3_private.tf", False),
    ("TMAC-AWS-S3-002", "s3_no_encryption.tf", True),
    ("TMAC-AWS-S3-002", "s3_encrypted.tf", False),
    ("TMAC-AWS-S3-003", "s3_no_logging.tf", True),
    ("TMAC-AWS-S3-003", "s3_with_logging.tf", False),
    ("TMAC-AWS-IAM-001", "iam_wildcard_resource.tf", True),
    ("TMAC-AWS-IAM-001", "iam_scoped_resource.tf", False),
    ("TMAC-AWS-IAM-002", "iam_inline_policy.tf", True),
    ("TMAC-AWS-IAM-002", "iam_managed_policy.tf", False),
    ("TMAC-AWS-SG-001", "sg_ssh_open.tf", True),
    ("TMAC-AWS-SG-001", "sg_ssh_restricted.tf", False),
    ("TMAC-AWS-SG-002", "sg_rdp_open.tf", True),
    ("TMAC-AWS-SG-002", "sg_rdp_restricted.tf", False),
    ("TMAC-AWS-RDS-001", "rds_no_encryption.tf", True),
    ("TMAC-AWS-RDS-001", "rds_encrypted.tf", False),
    ("TMAC-AWS-RDS-002", "rds_public.tf", True),
    ("TMAC-AWS-RDS-002", "rds_private.tf", False),
    ("TMAC-AWS-CW-001", "cloudtrail_disabled.tf", True),
    ("TMAC-AWS-CW-001", "cloudtrail_enabled.tf", False),
]

# Separate positive and negative cases for clearer parametrize IDs
POSITIVE_FIXTURES = [(r, f) for r, f, e in RULE_FIXTURES if e]
NEGATIVE_FIXTURES = [(r, f) for r, f, e in RULE_FIXTURES if not e]


@pytest.mark.parametrize("rule_id,fixture", POSITIVE_FIXTURES)
def test_positive_fixture_produces_finding(rule_id: str, fixture: str, fixtures_path: Path) -> None:
    """Positive fixture must produce exactly one Finding with the correct rule_id."""
    parser = TerraformParser()
    loader = RuleLoader()
    matcher = Matcher()

    resources = parser.parse(str(fixtures_path / fixture))
    rules = [r for r in loader.load_rules() if r.id == rule_id]
    findings = matcher.match(resources, rules)
    rule_findings = [f for f in findings if f.rule_id == rule_id]

    assert (
        len(rule_findings) >= 1
    ), f"Expected at least one Finding for {rule_id} in {fixture}, got 0"
    assert all(f.rule_id == rule_id for f in rule_findings)


@pytest.mark.parametrize("rule_id,fixture", NEGATIVE_FIXTURES)
def test_negative_fixture_produces_no_finding(
    rule_id: str, fixture: str, fixtures_path: Path
) -> None:
    """Negative fixture must produce zero Findings for the given rule_id."""
    parser = TerraformParser()
    loader = RuleLoader()
    matcher = Matcher()

    resources = parser.parse(str(fixtures_path / fixture))
    rules = [r for r in loader.load_rules() if r.id == rule_id]
    findings = matcher.match(resources, rules)
    rule_findings = [f for f in findings if f.rule_id == rule_id]

    assert (
        len(rule_findings) == 0
    ), f"Expected zero Findings for {rule_id} in {fixture}, got {len(rule_findings)}"


def test_all_rule_ids_follow_pattern() -> None:
    """All rule_id values in threats.yaml must follow TMAC-{CLOUD}-{SERVICE}-{NNN}."""
    threats_path = (
        Path(__file__).parent.parent.parent / "src" / "tmac" / "rules" / "aws" / "threats.yaml"
    )
    with open(threats_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    pattern = re.compile(r"^TMAC-[A-Z0-9]+-[A-Z0-9]+-\d{3}$")
    for rule in data["rules"]:
        rule_id = rule["id"]
        assert pattern.match(
            rule_id
        ), f"Rule ID '{rule_id}' does not match pattern TMAC-{{CLOUD}}-{{SERVICE}}-{{NNN}}"
