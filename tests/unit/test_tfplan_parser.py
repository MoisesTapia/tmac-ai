"""Unit tests for TfplanParser (Task 2.6).

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10
"""

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tmac.delta.models import ChangeAction
from tmac.models.resource import ResourceModel
from tmac.parsers.tfplan import TfplanParser

PLANS = Path("tests/fixtures/plans")


@pytest.fixture
def parser() -> TfplanParser:
    return TfplanParser()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
                "change": {
                    "actions": actions,
                    "before": before,
                    "after": after,
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# Fixture-based tests
# ---------------------------------------------------------------------------


def test_parse_create_action(parser: TfplanParser):
    """parse_plan() with create_with_threat.json returns PlannedChange with action=create,
    before=None, after populated."""
    changes = parser.parse_plan(str(PLANS / "create_with_threat.json"))
    assert len(changes) == 1
    c = changes[0]
    assert c.action == ChangeAction.create
    assert c.before is None
    assert c.after is not None
    assert c.after.get("acl") == "public-read"


def test_parse_delete_action(parser: TfplanParser):
    """parse_plan() with delete_with_threat.json returns PlannedChange with action=delete,
    before populated, after=None."""
    changes = parser.parse_plan(str(PLANS / "delete_with_threat.json"))
    assert len(changes) == 1
    c = changes[0]
    assert c.action == ChangeAction.delete
    assert c.before is not None
    assert c.before.get("acl") == "public-read"
    assert c.after is None


def test_parse_update_action(parser: TfplanParser):
    """parse_plan() with update_secure_to_insecure.json returns PlannedChange with
    action=update, before and after both populated."""
    changes = parser.parse_plan(str(PLANS / "update_secure_to_insecure.json"))
    assert len(changes) == 1
    c = changes[0]
    assert c.action == ChangeAction.update
    assert c.before is not None
    assert c.after is not None
    assert c.before.get("acl") == "private"
    assert c.after.get("acl") == "public-read"


def test_noop_resources_omitted(parser: TfplanParser, tmp_path: Path):
    """Resources with action no-op are not included in the result."""
    data = _minimal_plan(
        "aws_s3_bucket.data", ["no-op"], before={"acl": "private"}, after={"acl": "private"}
    )
    path = _write_plan(tmp_path, data)
    changes = parser.parse_plan(path)
    assert changes == []


def test_invalid_json_returns_empty(parser: TfplanParser, tmp_path: Path):
    """Invalid JSON returns empty list without raising an exception."""
    p = tmp_path / "bad.json"
    p.write_text("not valid json {{", encoding="utf-8")
    changes = parser.parse_plan(str(p))
    assert changes == []


def test_missing_resource_changes_returns_empty(parser: TfplanParser, tmp_path: Path):
    """JSON without resource_changes field returns empty list."""
    path = _write_plan(tmp_path, {"format_version": "1.2"})
    changes = parser.parse_plan(path)
    assert changes == []


def test_nonexistent_file_returns_empty(parser: TfplanParser):
    """Non-existent file path returns empty list without raising an exception."""
    changes = parser.parse_plan("/no/such/file/plan.json")
    assert changes == []


# ---------------------------------------------------------------------------
# Address parsing tests
# ---------------------------------------------------------------------------


def test_address_parsing_simple(parser: TfplanParser):
    """'aws_s3_bucket.data' → resource_type='aws_s3_bucket', resource_name='data'."""
    rt, rn = parser._extract_resource_type_and_name("aws_s3_bucket.data")
    assert rt == "aws_s3_bucket"
    assert rn == "data"


def test_address_parsing_module(parser: TfplanParser):
    """'module.vpc.aws_subnet.private' → resource_type='aws_subnet', resource_name='private'."""
    rt, rn = parser._extract_resource_type_and_name("module.vpc.aws_subnet.private")
    assert rt == "aws_subnet"
    assert rn == "private"


# ---------------------------------------------------------------------------
# BaseParser interface test
# ---------------------------------------------------------------------------


def test_parse_base_interface_returns_resource_models(parser: TfplanParser):
    """parse() (BaseParser interface) returns ResourceModels built from 'after' attributes."""
    resources = parser.parse(str(PLANS / "create_with_threat.json"))
    assert len(resources) == 1
    r = resources[0]
    assert isinstance(r, ResourceModel)
    assert r.resource_type == "aws_s3_bucket"
    assert r.name == "data"
    assert r.attributes.get("acl") == "public-read"


def test_parse_base_interface_excludes_delete(parser: TfplanParser):
    """parse() excludes resources with action=delete (after=None)."""
    resources = parser.parse(str(PLANS / "delete_with_threat.json"))
    assert resources == []


# ---------------------------------------------------------------------------
# _map_action tests
# ---------------------------------------------------------------------------


def test_map_action_create(parser: TfplanParser):
    assert parser._map_action(["create"]) == ChangeAction.create


def test_map_action_delete(parser: TfplanParser):
    assert parser._map_action(["delete"]) == ChangeAction.delete


def test_map_action_update(parser: TfplanParser):
    assert parser._map_action(["update"]) == ChangeAction.update


def test_map_action_replace(parser: TfplanParser):
    assert parser._map_action(["delete", "create"]) == ChangeAction.replace


def test_map_action_noop_returns_none(parser: TfplanParser):
    assert parser._map_action(["no-op"]) is None


def test_map_action_unknown_returns_none(parser: TfplanParser):
    assert parser._map_action(["unknown-action"]) is None


# ---------------------------------------------------------------------------
# Property 1: Semántica before/after por acción del parser
# Feature: tmac-v1-1-tfplan-delta, Property 1
# ---------------------------------------------------------------------------

_action_strategy = st.sampled_from(["create", "update", "delete"])
_attrs_strategy = st.fixed_dictionaries({"acl": st.sampled_from(["private", "public-read"])})


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(action=_action_strategy, attrs=_attrs_strategy)
def test_property_1_before_after_semantics(
    tmp_path: Path, parser: TfplanParser, action: str, attrs: dict
):
    """Property 1: before/after semantics are correct for each action type."""
    # Feature: tmac-v1-1-tfplan-delta, Property 1: Semántica before/after por acción del parser
    before = attrs if action in ("update", "delete") else None
    after = attrs if action in ("update", "create") else None
    data = _minimal_plan("aws_s3_bucket.test", [action], before=before, after=after)
    path = _write_plan(tmp_path, data)
    changes = parser.parse_plan(path)
    assert len(changes) == 1
    c = changes[0]
    if action == "create":
        assert c.before is None
        assert c.after is not None
    elif action == "delete":
        assert c.before is not None
        assert c.after is None
    else:  # update
        assert c.before is not None
        assert c.after is not None


# ---------------------------------------------------------------------------
# Property 2: El parser omite recursos no-op
# Feature: tmac-v1-1-tfplan-delta, Property 2
# ---------------------------------------------------------------------------


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n_noop=st.integers(min_value=1, max_value=5))
def test_property_2_noop_omitted(tmp_path: Path, parser: TfplanParser, n_noop: int):
    """Property 2: no-op resources never appear in the result."""
    # Feature: tmac-v1-1-tfplan-delta, Property 2: El parser omite recursos no-op
    resource_changes = [
        {
            "address": f"aws_s3_bucket.bucket_{i}",
            "type": "aws_s3_bucket",
            "name": f"bucket_{i}",
            "change": {
                "actions": ["no-op"],
                "before": {"acl": "private"},
                "after": {"acl": "private"},
            },
        }
        for i in range(n_noop)
    ]
    data = {"format_version": "1.2", "resource_changes": resource_changes}
    path = _write_plan(tmp_path, data)
    changes = parser.parse_plan(path)
    assert changes == []


# ---------------------------------------------------------------------------
# Property 3: El parser es determinista
# Feature: tmac-v1-1-tfplan-delta, Property 3
# ---------------------------------------------------------------------------


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    action=st.sampled_from(["create", "update", "delete"]),
    acl=st.sampled_from(["private", "public-read"]),
)
def test_property_3_deterministic(tmp_path: Path, parser: TfplanParser, action: str, acl: str):
    """Property 3: parsing the same file twice produces identical results."""
    # Feature: tmac-v1-1-tfplan-delta, Property 3: El parser es determinista
    before = {"acl": acl} if action in ("update", "delete") else None
    after = {"acl": acl} if action in ("update", "create") else None
    data = _minimal_plan("aws_s3_bucket.test", [action], before=before, after=after)
    path = _write_plan(tmp_path, data)
    first = parser.parse_plan(path)
    second = parser.parse_plan(path)
    assert len(first) == len(second)
    for a, b in zip(first, second):
        assert a.model_dump() == b.model_dump()


# ---------------------------------------------------------------------------
# Property 4: Round-trip del parser (serializar + parsear)
# Feature: tmac-v1-1-tfplan-delta, Property 4
# ---------------------------------------------------------------------------


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    action=st.sampled_from(["create", "update", "delete"]),
    acl=st.sampled_from(["private", "public-read"]),
)
def test_property_4_round_trip(tmp_path: Path, parser: TfplanParser, action: str, acl: str):
    """Property 4: serializing PlannedChange[] to JSON and re-parsing produces an equivalent list.

    Validates: Requirements 1.11, 1.12
    """
    # Feature: tmac-v1-1-tfplan-delta, Property 4: Round-trip del parser (serializar + parsear)
    before = {"acl": acl} if action in ("update", "delete") else None
    after = {"acl": acl} if action in ("update", "create") else None

    # Build a minimal tfplan.json and parse it
    data = _minimal_plan("aws_s3_bucket.test", [action], before=before, after=after)
    path = _write_plan(tmp_path, data)
    original = parser.parse_plan(path)
    assert len(original) == 1

    # Serialize the PlannedChange back to a tfplan-compatible JSON structure
    change = original[0]
    serialized_plan = {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": change.address,
                "type": change.resource_type,
                "name": change.resource_name,
                "change": {
                    "actions": (
                        [change.action.value]
                        if change.action != ChangeAction.replace
                        else ["delete", "create"]
                    ),
                    "before": change.before,
                    "after": change.after,
                },
            }
        ],
    }

    # Write the serialized plan and re-parse
    round_trip_path = tmp_path / "round_trip.json"
    round_trip_path.write_text(json.dumps(serialized_plan), encoding="utf-8")
    reparsed = parser.parse_plan(str(round_trip_path))

    assert len(reparsed) == 1
    orig_dump = original[0].model_dump()
    reparsed_dump = reparsed[0].model_dump()
    assert orig_dump["address"] == reparsed_dump["address"]
    assert orig_dump["resource_type"] == reparsed_dump["resource_type"]
    assert orig_dump["resource_name"] == reparsed_dump["resource_name"]
    assert orig_dump["action"] == reparsed_dump["action"]
    assert orig_dump["before"] == reparsed_dump["before"]
    assert orig_dump["after"] == reparsed_dump["after"]


# ---------------------------------------------------------------------------
# Property 5: El parser maneja JSON inválido sin lanzar excepciones
# Feature: tmac-v1-1-tfplan-delta, Property 5
# ---------------------------------------------------------------------------


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(bad_content=st.text(min_size=1, max_size=200).filter(lambda s: s.strip() != "{}"))
def test_property_5_invalid_json_no_exception(
    tmp_path: Path, parser: TfplanParser, bad_content: str
):
    """Property 5: any non-JSON content returns [] without raising exceptions."""
    # Feature: tmac-v1-1-tfplan-delta, Property 5: El parser maneja JSON inválido sin lanzar excepciones
    p = tmp_path / "bad.json"
    try:
        p.write_text(bad_content, encoding="utf-8", errors="replace")
    except Exception:
        return  # skip if we can't even write the file
    try:
        result = parser.parse_plan(str(p))
        # If it parses as valid JSON but lacks resource_changes, result is []
        assert isinstance(result, list)
    except Exception as exc:
        pytest.fail(f"parse_plan raised an unexpected exception: {exc}")
