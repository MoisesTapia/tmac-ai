"""Unit tests for delta data models (Task 1.5).

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from tmac.delta.models import ChangeAction, DeltaFinding, DeltaScanResult, PlannedChange
from tmac.models.finding import Finding, ScanMetadata, ScanStatistics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(**kwargs) -> Finding:
    defaults = {
        "rule_id": "TMAC-AWS-S3-001",
        "rule_name": "S3 Public ACL",
        "severity": "Critical",
        "stride": "Information Disclosure",
        "resource_type": "aws_s3_bucket",
        "resource_name": "data",
        "file_path": "main.tf",
        "line_number": 1,
        "matched_attribute": "acl",
        "description": "Bucket is publicly accessible.",
        "mitigation": "Set acl to private.",
    }
    defaults.update(kwargs)
    return Finding(**defaults)


def _make_delta_finding(**kwargs) -> DeltaFinding:
    defaults = {
        "rule_id": "TMAC-AWS-S3-001",
        "rule_name": "S3 Public ACL",
        "severity": "Critical",
        "stride": "Information Disclosure",
        "resource_type": "aws_s3_bucket",
        "resource_name": "data",
        "file_path": "main.tf",
        "line_number": 1,
        "matched_attribute": "acl",
        "description": "Bucket is publicly accessible.",
        "mitigation": "Set acl to private.",
        "change_action": ChangeAction.update,
        "changed_attribute": "acl",
        "value_before": "private",
        "value_after": "public-read",
    }
    defaults.update(kwargs)
    return DeltaFinding(**defaults)


def _make_scan_metadata() -> ScanMetadata:
    return ScanMetadata(scanned_directory="/tmp")


def _make_scan_statistics() -> ScanStatistics:
    return ScanStatistics()


# ---------------------------------------------------------------------------
# PlannedChange tests
# ---------------------------------------------------------------------------


def test_planned_change_accepts_all_fields():
    """PlannedChange acepta todos los campos y los serializa correctamente."""
    pc = PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.update,
        before={"acl": "private"},
        after={"acl": "public-read"},
    )
    data = pc.model_dump()
    assert data["address"] == "aws_s3_bucket.data"
    assert data["resource_type"] == "aws_s3_bucket"
    assert data["resource_name"] == "data"
    assert data["action"] == ChangeAction.update
    assert data["before"] == {"acl": "private"}
    assert data["after"] == {"acl": "public-read"}


def test_planned_change_create_before_none():
    """PlannedChange con action=create acepta before=None."""
    pc = PlannedChange(
        address="aws_s3_bucket.new",
        resource_type="aws_s3_bucket",
        resource_name="new",
        action=ChangeAction.create,
        before=None,
        after={"acl": "public-read"},
    )
    assert pc.before is None
    assert pc.after == {"acl": "public-read"}


def test_planned_change_delete_after_none():
    """PlannedChange con action=delete acepta after=None."""
    pc = PlannedChange(
        address="aws_s3_bucket.old",
        resource_type="aws_s3_bucket",
        resource_name="old",
        action=ChangeAction.delete,
        before={"acl": "public-read"},
        after=None,
    )
    assert pc.before == {"acl": "public-read"}
    assert pc.after is None


# ---------------------------------------------------------------------------
# ChangeAction tests
# ---------------------------------------------------------------------------


def test_change_action_has_exactly_four_values():
    """ChangeAction tiene exactamente los valores create, update, delete, replace."""
    values = {a.value for a in ChangeAction}
    assert values == {"create", "update", "delete", "replace"}


def test_change_action_is_str_enum():
    """ChangeAction es un str Enum (comparación directa con strings)."""
    assert ChangeAction.create == "create"
    assert ChangeAction.update == "update"
    assert ChangeAction.delete == "delete"
    assert ChangeAction.replace == "replace"


# ---------------------------------------------------------------------------
# DeltaFinding tests
# ---------------------------------------------------------------------------


def test_delta_finding_inherits_finding_fields():
    """DeltaFinding hereda todos los campos de Finding."""
    df = _make_delta_finding()
    # Inherited Finding fields
    assert df.rule_id == "TMAC-AWS-S3-001"
    assert df.rule_name == "S3 Public ACL"
    assert df.severity == "Critical"
    assert df.stride == "Information Disclosure"
    assert df.resource_type == "aws_s3_bucket"
    assert df.resource_name == "data"
    assert df.file_path == "main.tf"
    assert df.line_number == 1
    assert df.matched_attribute == "acl"
    assert df.description == "Bucket is publicly accessible."
    assert df.mitigation == "Set acl to private."


def test_delta_finding_has_delta_fields():
    """DeltaFinding añade los campos de delta."""
    df = _make_delta_finding()
    assert df.change_action == ChangeAction.update
    assert df.changed_attribute == "acl"
    assert df.value_before == "private"
    assert df.value_after == "public-read"


def test_delta_finding_create_accepts_value_before_none():
    """DeltaFinding con change_action=create acepta value_before=None."""
    df = _make_delta_finding(
        change_action=ChangeAction.create,
        value_before=None,
        value_after="public-read",
    )
    assert df.change_action == ChangeAction.create
    assert df.value_before is None
    assert df.value_after == "public-read"


def test_delta_finding_update_accepts_both_values():
    """DeltaFinding con change_action=update acepta value_before y value_after poblados."""
    df = _make_delta_finding(
        change_action=ChangeAction.update,
        value_before="private",
        value_after="public-read",
    )
    assert df.value_before == "private"
    assert df.value_after == "public-read"


# ---------------------------------------------------------------------------
# DeltaScanResult tests
# ---------------------------------------------------------------------------


def test_delta_scan_result_inherits_scan_result_fields():
    """DeltaScanResult hereda todos los campos de ScanResult."""
    df = _make_delta_finding()
    result = DeltaScanResult(
        metadata=_make_scan_metadata(),
        statistics=_make_scan_statistics(),
        findings=[df],
        files_scanned=1,
        rules_loaded=5,
        findings_introduced=1,
        plan_file="plan.json",
    )
    assert result.files_scanned == 1
    assert result.rules_loaded == 5
    assert len(result.findings) == 1


def test_delta_scan_result_has_delta_fields():
    """DeltaScanResult añade los campos de delta con defaults correctos."""
    result = DeltaScanResult(
        metadata=_make_scan_metadata(),
        statistics=_make_scan_statistics(),
        findings=[],
    )
    assert result.findings_introduced == 0
    assert result.findings_resolved == 0
    assert result.resources_created == 0
    assert result.resources_updated == 0
    assert result.resources_deleted == 0
    assert result.plan_file == ""


def test_delta_scan_result_invariant():
    """findings_introduced == len(findings) invariant."""
    df = _make_delta_finding()
    result = DeltaScanResult(
        metadata=_make_scan_metadata(),
        statistics=_make_scan_statistics(),
        findings=[df],
        findings_introduced=1,
    )
    assert result.findings_introduced == len(result.findings)


# ---------------------------------------------------------------------------
# Property 6: Round-trip serialization of DeltaFinding
# Feature: tmac-v1-1-tfplan-delta, Property 6: Round-trip de serialización de DeltaFinding
# ---------------------------------------------------------------------------

_change_action_st = st.sampled_from(list(ChangeAction))
_optional_str = st.one_of(st.none(), st.text(max_size=50))


@settings(max_examples=100)
@given(
    change_action=_change_action_st,
    changed_attribute=st.text(min_size=1, max_size=30),
    value_before=_optional_str,
    value_after=_optional_str,
)
def test_delta_finding_round_trip(change_action, changed_attribute, value_before, value_after):
    """Property 6: serializar con model_dump() y reconstruir produce objeto equivalente."""
    df = _make_delta_finding(
        change_action=change_action,
        changed_attribute=changed_attribute,
        value_before=value_before,
        value_after=value_after,
    )
    data = df.model_dump()
    reconstructed = DeltaFinding(**data)
    assert reconstructed.change_action == df.change_action
    assert reconstructed.changed_attribute == df.changed_attribute
    assert reconstructed.value_before == df.value_before
    assert reconstructed.value_after == df.value_after
    assert reconstructed.rule_id == df.rule_id
    assert reconstructed.severity == df.severity


# ---------------------------------------------------------------------------
# CLI tests for `tmac plan` (Task 9.4)
# Validates: Requirements 4.1, 4.7
# ---------------------------------------------------------------------------

from click.testing import CliRunner

from tmac.cli import cli


def test_plan_help_shows_plan_file_flag():
    """tmac plan --help muestra el flag --plan-file como requerido."""
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--help"])
    assert result.exit_code == 0
    assert "--plan-file" in result.output


def test_plan_without_plan_file_returns_error():
    """tmac plan sin --plan-file retorna error de Click con mensaje descriptivo."""
    runner = CliRunner()
    result = runner.invoke(cli, ["plan"])
    assert result.exit_code != 0
    assert "plan-file" in result.output.lower() or "missing" in result.output.lower()


def test_plan_nonexistent_file_returns_exit_code_3():
    """tmac plan --plan-file /no/existe retorna exit code 3."""
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--plan-file", "/no/existe.json"])
    assert result.exit_code == 3
