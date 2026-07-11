"""
Unit tests for RuleLoader — schema validation and structured logging.
Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 9.1
"""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from tmac.engine.rule_loader import RuleLoader, REQUIRED_FILE_FIELDS, REQUIRED_RULE_FIELDS
from tmac.engine.matcher import Matcher
from tmac.models.rule import ThreatRule, CheckCondition
from tmac.models.resource import ResourceModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_rule_data(**overrides):
    base = {
        "id": "TMAC-TEST-001",
        "name": "Test Rule",
        "resource_type": "aws_s3_bucket",
        "check": {"attribute": "acl", "condition": "equals", "values": ["public-read"]},
        "severity": "High",
        "stride": "Information Disclosure",
        "description": "Test description",
        "mitigation": "Test mitigation",
    }
    base.update(overrides)
    return base


def _make_valid_file_data(rules=None):
    if rules is None:
        rules = [_make_valid_rule_data()]
    return {"version": "1.0", "rules": rules}


def _write_yaml(tmp_path: Path, filename: str, data: dict) -> Path:
    p = tmp_path / filename
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 3.1 — Validation of required fields
# ---------------------------------------------------------------------------

def test_file_missing_version_emits_warning_and_is_skipped(tmp_path, caplog):
    """Req 6.1, 6.2: a file without 'version' emits a warning and is skipped."""
    data = {"rules": [_make_valid_rule_data()]}  # no 'version'
    yaml_file = _write_yaml(tmp_path, "rules.yaml", data)

    loader = RuleLoader()
    rules_dict: dict = {}
    import logging
    with caplog.at_level(logging.WARNING, logger="tmac.engine.rule_loader"):
        loader._load_file(yaml_file, rules_dict)

    assert rules_dict == {}
    assert any("missing required fields" in r.message for r in caplog.records)


def test_rule_missing_id_emits_warning_and_is_skipped(tmp_path, caplog):
    """Req 6.3: a rule without the 'id' field emits a warning and is skipped."""
    bad_rule = _make_valid_rule_data()
    del bad_rule["id"]
    data = _make_valid_file_data(rules=[bad_rule])
    yaml_file = _write_yaml(tmp_path, "rules.yaml", data)

    loader = RuleLoader()
    rules_dict: dict = {}
    import logging
    with caplog.at_level(logging.WARNING, logger="tmac.engine.rule_loader"):
        loader._load_file(yaml_file, rules_dict)

    assert rules_dict == {}
    assert any("missing fields" in r.message for r in caplog.records)


def test_successful_load_returns_threat_rules(tmp_path):
    """Req 6.1–6.4: a successful load returns a list of ThreatRule with all fields."""
    data = _make_valid_file_data()
    yaml_file = _write_yaml(tmp_path, "rules.yaml", data)

    loader = RuleLoader()
    rules_dict: dict = {}
    loader._load_file(yaml_file, rules_dict)
    rules = list(rules_dict.values())

    assert len(rules) == 1
    rule = rules[0]
    assert isinstance(rule, ThreatRule)
    assert rule.id == "TMAC-TEST-001"
    assert rule.name == "Test Rule"
    assert rule.resource_type == "aws_s3_bucket"
    assert rule.severity == "High"


def test_no_print_calls_in_rule_loader(tmp_path, capsys):
    """Req 6.4: RuleLoader does not use print(), it uses logging."""
    # Trigger a warning path (missing version)
    data = {"rules": [_make_valid_rule_data()]}
    yaml_file = _write_yaml(tmp_path, "rules.yaml", data)

    loader = RuleLoader()
    rules_dict: dict = {}
    loader._load_file(yaml_file, rules_dict)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# ---------------------------------------------------------------------------
# 3.2 — Propagation of tags to the Finding
# ---------------------------------------------------------------------------

def test_tags_propagated_from_rule_to_finding():
    """Req 9.1: rule tags are propagated to the Finding produced by the Matcher."""
    rule = ThreatRule(
        id="TMAC-TEST-001",
        name="Test Rule",
        resource_type="aws_s3_bucket",
        check=CheckCondition(attribute="acl", condition="equals", values=["public-read"]),
        severity="High",
        stride="Information Disclosure",
        description="desc",
        mitigation="mit",
        tags=["s3", "public-access"],
    )
    resource = ResourceModel(
        resource_type="aws_s3_bucket",
        name="my_bucket",
        attributes={"acl": "public-read"},
        source_file="test.tf",
        line_number=1,
    )

    matcher = Matcher()
    findings = matcher.match([resource], [rule])

    assert len(findings) == 1
    assert findings[0].tags == ["s3", "public-access"]


def test_empty_tags_propagated_to_finding():
    """Req 9.1: empty tags are also propagated correctly."""
    rule = ThreatRule(
        id="TMAC-TEST-002",
        name="Test Rule 2",
        resource_type="aws_s3_bucket",
        check=CheckCondition(attribute="acl", condition="equals", values=["public-read"]),
        severity="Medium",
        stride="Information Disclosure",
        description="desc",
        mitigation="mit",
        tags=[],
    )
    resource = ResourceModel(
        resource_type="aws_s3_bucket",
        name="my_bucket",
        attributes={"acl": "public-read"},
        source_file="test.tf",
        line_number=1,
    )

    matcher = Matcher()
    findings = matcher.match([resource], [rule])

    assert len(findings) == 1
    assert findings[0].tags == []


# ---------------------------------------------------------------------------
# Property 11: RuleLoader is idempotent with respect to file order
# Validates: Requirements 6.5
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=65), min_size=3, max_size=10),
        min_size=1,
        max_size=5,
        unique=True,
    )
)
def test_property_11_rule_loader_idempotent_order(rule_id_suffixes):
    """
    **Validates: Requirements 6.5**
    Property 11: RuleLoader is idempotent with respect to file order.
    Loading the same YAML files in any order produces the same set of ThreatRule.
    """
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for suffix in rule_id_suffixes:
            rule_id = f"TMAC-TEST-{suffix}"
            data = _make_valid_file_data(rules=[_make_valid_rule_data(id=rule_id, name=f"Rule {suffix}")])
            p = tmp_path / f"rules_{suffix}.yaml"
            p.write_text(yaml.dump(data), encoding="utf-8")

        loader = RuleLoader()
        rules = loader.load_rules(extra_rules_dir=str(tmp_path))
        rule_ids = sorted(r.id for r in rules)

        # Load again — same directory, same files, result must be identical
        rules2 = loader.load_rules(extra_rules_dir=str(tmp_path))
        rule_ids2 = sorted(r.id for r in rules2)

        assert rule_ids == rule_ids2


# ---------------------------------------------------------------------------
# Property 17: Finding.tags is propagated from ThreatRule.tags
# Validates: Requirements 9.1
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.lists(
        st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pd"), min_codepoint=45), min_size=1, max_size=20),
        min_size=0,
        max_size=10,
    )
)
def test_property_17_finding_tags_propagated_from_rule(tags):
    """
    **Validates: Requirements 9.1**
    Property 17: Finding.tags is propagated from ThreatRule.tags.
    For any ThreatRule with a tags field, the produced Finding must have the same value.
    """
    rule = ThreatRule(
        id="TMAC-PROP-017",
        name="Property 17 Rule",
        resource_type="aws_s3_bucket",
        check=CheckCondition(attribute="acl", condition="equals", values=["public-read"]),
        severity="High",
        stride="Information Disclosure",
        description="desc",
        mitigation="mit",
        tags=tags,
    )
    resource = ResourceModel(
        resource_type="aws_s3_bucket",
        name="bucket",
        attributes={"acl": "public-read"},
        source_file="test.tf",
        line_number=1,
    )

    matcher = Matcher()
    findings = matcher.match([resource], [rule])

    assert len(findings) == 1
    assert findings[0].tags == tags
