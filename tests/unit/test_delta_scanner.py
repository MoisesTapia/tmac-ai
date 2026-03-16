"""Unit tests for DeltaScanner (Task 3.5).

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8,
           6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tmac.delta.models import ChangeAction, DeltaFinding, DeltaScanResult, PlannedChange
from tmac.delta.scanner import DeltaScanError, DeltaScanner
from tmac.engine.evaluator import Evaluator
from tmac.models.resource import ResourceModel
from tmac.models.rule import CheckCondition, ThreatRule

PLANS = Path("tests/fixtures/plans")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(
    rule_id: str = "TMAC-AWS-S3-001",
    resource_type: str = "aws_s3_bucket",
    attribute: str = "acl",
    condition: str = "in",
    values: Optional[List[Any]] = None,
    severity: str = "Critical",
) -> ThreatRule:
    return ThreatRule(
        id=rule_id,
        name="Test Rule",
        resource_type=resource_type,
        check=CheckCondition(
            attribute=attribute,
            condition=condition,
            values=values if values is not None else ["public-read", "public-read-write"],
        ),
        severity=severity,
        stride="Information Disclosure",
        description="Test description.",
        mitigation="Test mitigation.",
    )


def _write_plan(tmp_path: Path, data: dict) -> str:
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def _minimal_plan(address: str, actions: list, before=None, after=None) -> dict:
    return {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": address,
                "type": address.split(".")[-2] if address.count(".") >= 1 else address,
                "name": address.split(".")[-1],
                "change": {"actions": actions, "before": before, "after": after},
            }
        ],
    }


@pytest.fixture
def scanner() -> DeltaScanner:
    return DeltaScanner()


# ---------------------------------------------------------------------------
# 3.5 — Core classification tests
# ---------------------------------------------------------------------------

def test_create_produces_delta_finding(scanner: DeltaScanner):
    """PlannedChange create with insecure attribute produces DeltaFinding with change_action=create."""
    result = scanner.run(str(PLANS / "create_with_threat.json"))
    assert result.findings_introduced >= 1
    finding = next(f for f in result.findings if f.rule_id == "TMAC-AWS-S3-001")
    assert isinstance(finding, DeltaFinding)
    assert finding.change_action == ChangeAction.create
    assert finding.value_before is None
    assert finding.value_after == "public-read"


def test_update_secure_to_insecure_produces_finding(scanner: DeltaScanner):
    """PlannedChange update from secure to insecure produces exactly one DeltaFinding."""
    result = scanner.run(str(PLANS / "update_secure_to_insecure.json"))
    s3_findings = [f for f in result.findings if f.rule_id == "TMAC-AWS-S3-001"]
    assert len(s3_findings) == 1
    assert result.findings_introduced >= 1
    assert result.findings_resolved == 0
    f = s3_findings[0]
    assert isinstance(f, DeltaFinding)
    assert f.change_action == ChangeAction.update


def test_update_insecure_to_secure_increments_resolved(scanner: DeltaScanner):
    """PlannedChange update from insecure to secure increments findings_resolved, no DeltaFinding."""
    result = scanner.run(str(PLANS / "update_insecure_to_secure.json"))
    assert result.findings_introduced == 0
    assert len(result.findings) == 0
    assert result.findings_resolved >= 1


def test_delete_with_threat_increments_resolved(scanner: DeltaScanner):
    """PlannedChange delete with threat in before increments findings_resolved."""
    result = scanner.run(str(PLANS / "delete_with_threat.json"))
    assert result.findings_introduced == 0
    assert len(result.findings) == 0
    assert result.findings_resolved >= 1


def test_clean_plan_returns_zero_findings(scanner: DeltaScanner):
    """Plan without threats returns findings_introduced=0 and empty findings list."""
    result = scanner.run(str(PLANS / "clean_plan.json"))
    assert result.findings_introduced == 0
    assert result.findings == []


def test_resource_counts_correct(scanner: DeltaScanner):
    """resources_created, resources_updated, resources_deleted are correct for mixed plan."""
    result = scanner.run(str(PLANS / "mixed_plan.json"))
    assert result.resources_created == 1
    assert result.resources_updated == 1
    assert result.resources_deleted == 1


def test_findings_introduced_equals_len_findings(scanner: DeltaScanner):
    """findings_introduced == len(result.findings) invariant holds."""
    for fixture in ["create_with_threat.json", "update_secure_to_insecure.json",
                    "update_insecure_to_secure.json", "delete_with_threat.json",
                    "clean_plan.json", "mixed_plan.json"]:
        result = scanner.run(str(PLANS / fixture))
        assert result.findings_introduced == len(result.findings), (
            f"Invariant violated for {fixture}: "
            f"findings_introduced={result.findings_introduced}, len={len(result.findings)}"
        )


def test_ignore_map_suppresses_resource(scanner: DeltaScanner):
    """Resource in ignore_map with ['*'] produces no DeltaFinding."""
    result = scanner.run(
        str(PLANS / "create_with_threat.json"),
        ignore_map={"aws_s3_bucket.data": ["*"]},
    )
    assert result.findings_introduced == 0
    assert result.findings == []


def test_delta_scan_error_on_nonexistent_file(scanner: DeltaScanner):
    """DeltaScanError is raised for a non-existent file."""
    with pytest.raises(DeltaScanError):
        scanner.run("/no/such/file/plan.json")


def test_delta_scan_error_on_invalid_json(scanner: DeltaScanner, tmp_path: Path):
    """DeltaScanError is raised for invalid JSON."""
    p = tmp_path / "bad.json"
    p.write_text("not valid json {{", encoding="utf-8")
    with pytest.raises(DeltaScanError):
        scanner.run(str(p))


def test_delta_scan_error_on_missing_resource_changes(scanner: DeltaScanner, tmp_path: Path):
    """DeltaScanError is raised when resource_changes field is absent."""
    path = _write_plan(tmp_path, {"format_version": "1.2"})
    with pytest.raises(DeltaScanError):
        scanner.run(path)


def test_delta_finding_fields_populated(scanner: DeltaScanner):
    """DeltaFinding has changed_attribute, value_before, value_after correctly set."""
    result = scanner.run(str(PLANS / "update_secure_to_insecure.json"))
    f = next(f for f in result.findings if f.rule_id == "TMAC-AWS-S3-001")
    assert isinstance(f, DeltaFinding)
    assert f.changed_attribute == "acl"
    assert f.value_before == "private"
    assert f.value_after == "public-read"


def test_replace_action_counted_as_updated(scanner: DeltaScanner, tmp_path: Path):
    """PlannedChange with replace action is counted in resources_updated."""
    data = _minimal_plan(
        "aws_s3_bucket.data", ["delete", "create"],
        before={"acl": "private"}, after={"acl": "public-read"},
    )
    path = _write_plan(tmp_path, data)
    result = scanner.run(path)
    assert result.resources_updated == 1
    assert result.resources_created == 0


# ---------------------------------------------------------------------------
# _build_resource_model tests
# ---------------------------------------------------------------------------

def test_build_resource_model_use_after():
    """_build_resource_model with use_after=True uses 'after' attributes."""
    scanner = DeltaScanner()
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.update,
        before={"acl": "private"},
        after={"acl": "public-read"},
    )
    model = scanner._build_resource_model(change, use_after=True)
    assert isinstance(model, ResourceModel)
    assert model.attributes == {"acl": "public-read"}
    assert model.source_file == "aws_s3_bucket.data"
    assert model.line_number == 0


def test_build_resource_model_use_before():
    """_build_resource_model with use_after=False uses 'before' attributes."""
    scanner = DeltaScanner()
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.update,
        before={"acl": "private"},
        after={"acl": "public-read"},
    )
    model = scanner._build_resource_model(change, use_after=False)
    assert model.attributes == {"acl": "private"}


# ---------------------------------------------------------------------------
# _evaluate_change unit tests
# ---------------------------------------------------------------------------

def test_evaluate_change_create_introduces_finding():
    """_evaluate_change for create action returns introduced findings."""
    scanner = DeltaScanner()
    rule = _make_rule()
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.create,
        before=None,
        after={"acl": "public-read"},
    )
    introduced, resolved = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 1
    assert resolved == 0
    assert introduced[0].change_action == ChangeAction.create


def test_evaluate_change_delete_resolves_finding():
    """_evaluate_change for delete action returns resolved count."""
    scanner = DeltaScanner()
    rule = _make_rule()
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.delete,
        before={"acl": "public-read"},
        after=None,
    )
    introduced, resolved = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 0
    assert resolved == 1


def test_evaluate_change_update_secure_to_insecure():
    """_evaluate_change for update secure→insecure introduces finding."""
    scanner = DeltaScanner()
    rule = _make_rule()
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.update,
        before={"acl": "private"},
        after={"acl": "public-read"},
    )
    introduced, resolved = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 1
    assert resolved == 0


def test_evaluate_change_update_insecure_to_secure():
    """_evaluate_change for update insecure→secure resolves finding."""
    scanner = DeltaScanner()
    rule = _make_rule()
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.update,
        before={"acl": "public-read"},
        after={"acl": "private"},
    )
    introduced, resolved = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 0
    assert resolved == 1


def test_evaluate_change_skips_wrong_resource_type():
    """_evaluate_change ignores rules for different resource types."""
    scanner = DeltaScanner()
    rule = _make_rule(resource_type="aws_security_group")
    change = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.create,
        before=None,
        after={"acl": "public-read"},
    )
    introduced, resolved = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 0
    assert resolved == 0


# ---------------------------------------------------------------------------
# Property 7: Semántica de DeltaFinding por tipo de cambio
# Feature: tmac-v1-1-tfplan-delta, Property 7
# ---------------------------------------------------------------------------

_acl_strategy = st.sampled_from(["public-read", "public-read-write"])


@settings(max_examples=100)
@given(acl=_acl_strategy)
def test_property_7_delta_finding_semantics_create(acl: str):
    """Property 7: DeltaFinding for create has change_action=create and value_before=None."""
    # Feature: tmac-v1-1-tfplan-delta, Property 7: Semántica de DeltaFinding por tipo de cambio
    scanner = DeltaScanner()
    rule = _make_rule()
    change = PlannedChange(
        address="aws_s3_bucket.test",
        resource_type="aws_s3_bucket",
        resource_name="test",
        action=ChangeAction.create,
        before=None,
        after={"acl": acl},
    )
    introduced, _ = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 1
    f = introduced[0]
    assert f.change_action == ChangeAction.create
    assert f.value_before is None
    assert f.value_after == acl


@settings(max_examples=100)
@given(acl_after=_acl_strategy)
def test_property_7_delta_finding_semantics_update(acl_after: str):
    """Property 7: DeltaFinding for update has value_before and value_after set."""
    # Feature: tmac-v1-1-tfplan-delta, Property 7: Semántica de DeltaFinding por tipo de cambio
    scanner = DeltaScanner()
    rule = _make_rule()
    change = PlannedChange(
        address="aws_s3_bucket.test",
        resource_type="aws_s3_bucket",
        resource_name="test",
        action=ChangeAction.update,
        before={"acl": "private"},
        after={"acl": acl_after},
    )
    introduced, _ = scanner._evaluate_change(change, [rule])
    assert len(introduced) == 1
    f = introduced[0]
    assert f.change_action == ChangeAction.update
    assert f.value_before == "private"
    assert f.value_after == acl_after


# ---------------------------------------------------------------------------
# Property 8: DeltaScanner produces exactly the correct DeltaFindings for updates
# Feature: tmac-v1-1-tfplan-delta, Property 8
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(n_rules=st.integers(min_value=1, max_value=5))
def test_property_8_exact_findings_for_update(n_rules: int):
    """Property 8: update secure→insecure produces exactly N findings for N violated rules."""
    # Feature: tmac-v1-1-tfplan-delta, Property 8: DeltaScanner produce exactamente los DeltaFinding correctos para updates
    scanner = DeltaScanner()
    rules = [
        _make_rule(
            rule_id=f"RULE-{i:03d}",
            attribute=f"attr_{i}",
            condition="equals",
            values=["bad"],
        )
        for i in range(n_rules)
    ]
    after_attrs = {f"attr_{i}": "bad" for i in range(n_rules)}
    before_attrs = {f"attr_{i}": "good" for i in range(n_rules)}
    change = PlannedChange(
        address="aws_s3_bucket.test",
        resource_type="aws_s3_bucket",
        resource_name="test",
        action=ChangeAction.update,
        before=before_attrs,
        after=after_attrs,
    )
    introduced, resolved = scanner._evaluate_change(change, rules)
    assert len(introduced) == n_rules
    assert resolved == 0


# ---------------------------------------------------------------------------
# Property 9: DeltaScanner correctly records resolved threats
# Feature: tmac-v1-1-tfplan-delta, Property 9
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    action=st.sampled_from([ChangeAction.update, ChangeAction.delete]),
    n_rules=st.integers(min_value=1, max_value=5),
)
def test_property_9_resolved_threats(action: ChangeAction, n_rules: int):
    """Property 9: update/delete insecure→secure resolves exactly M findings."""
    # Feature: tmac-v1-1-tfplan-delta, Property 9: DeltaScanner registra correctamente amenazas resueltas
    scanner = DeltaScanner()
    rules = [
        _make_rule(
            rule_id=f"RULE-{i:03d}",
            attribute=f"attr_{i}",
            condition="equals",
            values=["bad"],
        )
        for i in range(n_rules)
    ]
    insecure_attrs = {f"attr_{i}": "bad" for i in range(n_rules)}
    secure_attrs = {f"attr_{i}": "good" for i in range(n_rules)}

    if action == ChangeAction.update:
        change = PlannedChange(
            address="aws_s3_bucket.test",
            resource_type="aws_s3_bucket",
            resource_name="test",
            action=action,
            before=insecure_attrs,
            after=secure_attrs,
        )
    else:  # delete
        change = PlannedChange(
            address="aws_s3_bucket.test",
            resource_type="aws_s3_bucket",
            resource_name="test",
            action=action,
            before=insecure_attrs,
            after=None,
        )

    introduced, resolved = scanner._evaluate_change(change, rules)
    assert len(introduced) == 0
    assert resolved == n_rules


# ---------------------------------------------------------------------------
# Property 10: DeltaScanResult count invariants
# Feature: tmac-v1-1-tfplan-delta, Property 10
# ---------------------------------------------------------------------------

@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n_create=st.integers(min_value=0, max_value=3),
    n_update=st.integers(min_value=0, max_value=3),
    n_delete=st.integers(min_value=0, max_value=3),
)
def test_property_10_count_invariants(
    tmp_path: Path, n_create: int, n_update: int, n_delete: int
):
    """Property 10: resource count fields match actual PlannedChange counts."""
    # Feature: tmac-v1-1-tfplan-delta, Property 10: Invariantes de conteo del DeltaScanResult
    resource_changes = []
    for i in range(n_create):
        resource_changes.append({
            "address": f"aws_s3_bucket.create_{i}",
            "type": "aws_s3_bucket",
            "name": f"create_{i}",
            "change": {"actions": ["create"], "before": None, "after": {"acl": "private"}},
        })
    for i in range(n_update):
        resource_changes.append({
            "address": f"aws_s3_bucket.update_{i}",
            "type": "aws_s3_bucket",
            "name": f"update_{i}",
            "change": {
                "actions": ["update"],
                "before": {"acl": "private"},
                "after": {"acl": "private"},
            },
        })
    for i in range(n_delete):
        resource_changes.append({
            "address": f"aws_s3_bucket.delete_{i}",
            "type": "aws_s3_bucket",
            "name": f"delete_{i}",
            "change": {"actions": ["delete"], "before": {"acl": "private"}, "after": None},
        })

    data = {"format_version": "1.2", "resource_changes": resource_changes}
    path = _write_plan(tmp_path, data)
    scanner = DeltaScanner()
    result = scanner.run(path)

    assert result.resources_created == n_create
    assert result.resources_updated == n_update
    assert result.resources_deleted == n_delete
    assert result.findings_introduced == len(result.findings)


# ---------------------------------------------------------------------------
# Property 12: Equivalence between DeltaScanner and Scanner evaluation
# Feature: tmac-v1-1-tfplan-delta, Property 12
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(acl=st.sampled_from(["private", "public-read", "public-read-write"]))
def test_property_12_evaluation_equivalence(acl: str):
    """Property 12: evaluating rule against PlannedChange.after == evaluating against ResourceModel."""
    # Feature: tmac-v1-1-tfplan-delta, Property 12: Equivalencia de evaluación entre DeltaScanner y Scanner
    scanner = DeltaScanner()
    evaluator = Evaluator()
    rule = _make_rule()

    attrs = {"acl": acl}
    change = PlannedChange(
        address="aws_s3_bucket.test",
        resource_type="aws_s3_bucket",
        resource_name="test",
        action=ChangeAction.create,
        before=None,
        after=attrs,
    )

    # Evaluate via DeltaScanner._evaluate_change
    introduced, _ = scanner._evaluate_change(change, [rule])
    delta_result = len(introduced) > 0

    # Evaluate directly via Evaluator (same as Scanner would)
    direct_result = evaluator.evaluate(rule.check, attrs)

    assert delta_result == direct_result


# ---------------------------------------------------------------------------
# Property 13: tmac:ignore suppresses resources from delta analysis
# Feature: tmac-v1-1-tfplan-delta, Property 13
# ---------------------------------------------------------------------------

@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(acl=_acl_strategy)
def test_property_13_ignore_suppresses_resource(tmp_path: Path, acl: str):
    """Property 13: resource in ignore_map with ['*'] produces no DeltaFinding."""
    # Feature: tmac-v1-1-tfplan-delta, Property 13: tmac:ignore suprime recursos del análisis de delta
    data = _minimal_plan("aws_s3_bucket.data", ["create"], before=None, after={"acl": acl})
    path = _write_plan(tmp_path, data)
    scanner = DeltaScanner()
    result = scanner.run(path, ignore_map={"aws_s3_bucket.data": ["*"]})
    assert result.findings_introduced == 0
    assert result.findings == []
