"""
Tests unitarios para RuleLoader — validación de schema y logging estructurado.
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
# 3.1 — Validación de campos obligatorios
# ---------------------------------------------------------------------------

def test_file_missing_version_emits_warning_and_is_skipped(tmp_path, caplog):
    """Req 6.1, 6.2: archivo sin 'version' emite warning y es omitido."""
    data = {"rules": [_make_valid_rule_data()]}  # sin 'version'
    yaml_file = _write_yaml(tmp_path, "rules.yaml", data)

    loader = RuleLoader()
    rules_dict: dict = {}
    import logging
    with caplog.at_level(logging.WARNING, logger="tmac.engine.rule_loader"):
        loader._load_file(yaml_file, rules_dict)

    assert rules_dict == {}
    assert any("missing required fields" in r.message for r in caplog.records)


def test_rule_missing_id_emits_warning_and_is_skipped(tmp_path, caplog):
    """Req 6.3: regla sin campo 'id' emite warning y es omitida."""
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
    """Req 6.1–6.4: carga exitosa retorna lista de ThreatRule con todos los campos."""
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
    """Req 6.4: RuleLoader no usa print(), usa logging."""
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
# 3.2 — Propagación de tags al Finding
# ---------------------------------------------------------------------------

def test_tags_propagated_from_rule_to_finding():
    """Req 9.1: tags de la regla se propagan al Finding producido por el Matcher."""
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
    """Req 9.1: tags vacíos también se propagan correctamente."""
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
# Property 11: RuleLoader es idempotente respecto al orden de archivos
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
    Property 11: RuleLoader es idempotente respecto al orden de archivos.
    Cargar los mismos archivos YAML en cualquier orden produce el mismo conjunto de ThreatRule.
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
# Property 17: Finding.tags se propaga desde ThreatRule.tags
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
    Property 17: Finding.tags se propaga desde ThreatRule.tags.
    Para cualquier ThreatRule con campo tags, el Finding producido debe tener el mismo valor.
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


# ---------------------------------------------------------------------------
# Rule value validation (severity / stride / condition / regex)
# ---------------------------------------------------------------------------

class TestRuleValidation:
    def test_values_are_normalized_case_insensitively(self):
        rule = ThreatRule(**_make_valid_rule_data(
            severity="critical",
            stride="information disclosure",
            check={"attribute": "acl", "condition": "EQUALS", "values": ["public-read"]},
        ))
        assert rule.severity == "Critical"
        assert rule.stride == "Information Disclosure"
        assert rule.check.condition == "equals"

    @pytest.mark.parametrize("field, value", [
        ("severity", "Critcal"),
        ("stride", "Infomation Disclosure"),
    ])
    def test_typo_in_severity_or_stride_is_rejected(self, field, value):
        with pytest.raises(ValueError, match=f"invalid {field}"):
            ThreatRule(**_make_valid_rule_data(**{field: value}))

    def test_unknown_condition_is_rejected(self):
        with pytest.raises(ValueError, match="invalid condition"):
            CheckCondition(attribute="acl", condition="equal", values=["x"])

    def test_condition_without_values_is_rejected(self):
        with pytest.raises(ValueError, match="requires at least one value"):
            CheckCondition(attribute="acl", condition="equals", values=[])

    def test_exists_conditions_need_no_values(self):
        assert CheckCondition(attribute="acl", condition="not_exists").values == []

    def test_invalid_regex_is_rejected(self):
        with pytest.raises(ValueError, match="invalid regex"):
            CheckCondition(attribute="name", condition="regex", values=["(unclosed"])

    def test_invalid_nested_and_check_is_rejected(self):
        with pytest.raises(ValueError, match="invalid condition"):
            CheckCondition(
                attribute="acl", condition="equals", values=["x"],
                and_check={"attribute": "b", "condition": "nope", "values": ["y"]},
            )

    def test_invalid_rule_is_skipped_without_dropping_the_rest_of_the_file(self, tmp_path, caplog):
        import logging
        data = _make_valid_file_data(rules=[
            _make_valid_rule_data(id="TMAC-TEST-BAD", severity="Critcal"),
            _make_valid_rule_data(id="TMAC-TEST-GOOD"),
        ])
        _write_yaml(tmp_path, "custom.yaml", data)
        with caplog.at_level(logging.WARNING):
            rules = RuleLoader().load_rules(str(tmp_path))
        ids = {r.id for r in rules}
        assert "TMAC-TEST-GOOD" in ids
        assert "TMAC-TEST-BAD" not in ids
        assert "TMAC-TEST-BAD" in caplog.text

    def test_all_built_in_rules_are_valid(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            rules = RuleLoader().load_rules()
        assert len(rules) == 101
        assert "invalid" not in caplog.text
