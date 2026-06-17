"""
Unit tests for Evaluator and Matcher.
Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 13.1, 13.2, 13.3, 13.4, 13.5
"""
import pytest
from hypothesis import given, settings, strategies as st

from tmac.engine.evaluator import Evaluator
from tmac.engine.matcher import Matcher
from tmac.models.rule import CheckCondition, ThreatRule
from tmac.models.resource import ResourceModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(rule_id="TMAC-TEST-001", resource_type="aws_security_group",
               attribute="ingress.from_port", condition="equals", values=None,
               and_check=None):
    return ThreatRule(
        id=rule_id,
        name=f"Rule {rule_id}",
        resource_type=resource_type,
        check=CheckCondition(attribute=attribute, condition=condition,
                             values=values or [], and_check=and_check),
        severity="High",
        stride="Denial of Service",
        description="desc",
        mitigation="mit",
    )


def _make_resource(resource_type="aws_security_group", name="my_sg", attributes=None):
    return ResourceModel(
        resource_type=resource_type,
        name=name,
        attributes=attributes or {},
        source_file="test.tf",
        line_number=1,
    )


evaluator = Evaluator()


# ---------------------------------------------------------------------------
# 4.1 — Parametrized tests per operator (Req 5.4, 13.1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("condition,values,actual,expected", [
    # equals
    ("equals",       ["public-read"],  "public-read",  True),
    ("equals",       ["public-read"],  "private",      False),
    # not_equals
    ("not_equals",   ["private"],      "public-read",  True),
    ("not_equals",   ["public-read"],  "public-read",  False),
    # in
    ("in",           ["a", "b", "c"], "b",             True),
    ("in",           ["a", "b", "c"], "d",             False),
    # not_in
    ("not_in",       ["a", "b"],      "c",             True),
    ("not_in",       ["a", "b"],      "a",             False),
    # contains (string)
    ("contains",     ["0.0.0.0"],     "0.0.0.0/0",    True),
    ("contains",     ["10.0.0.0"],    "0.0.0.0/0",    False),
    # contains (list)
    ("contains",     ["admin"],       ["admin", "user"], True),
    ("contains",     ["root"],        ["admin", "user"], False),
    # not_contains (string)
    ("not_contains", ["10.0.0.0"],    "0.0.0.0/0",    True),
    ("not_contains", ["0.0.0.0"],     "0.0.0.0/0",    False),
    # not_contains (list)
    ("not_contains", ["root"],        ["admin", "user"], True),
    ("not_contains", ["admin"],       ["admin", "user"], False),
    # regex
    ("regex",        ["^0\\.0\\.0\\.0"], "0.0.0.0/0", True),
    ("regex",        ["^10\\."],      "0.0.0.0/0",    False),
    # exists
    ("exists",       [],              "something",    True),
    ("exists",       [],              None,           False),
    # not_exists
    ("not_exists",   [],              None,           True),
    ("not_exists",   [],              "something",    False),
])
def test_all_operators(condition, values, actual, expected):
    """Req 5.4, 13.1: Evaluator is correct for all operators."""
    cond = CheckCondition(attribute="x", condition=condition, values=values)
    attrs = {"x": actual} if actual is not None else {}
    # For not_exists we need the key absent; for exists with None we also need it absent
    if actual is None and condition in ("exists", "not_exists"):
        attrs = {}
    result = evaluator.evaluate(cond, attrs)
    assert result == expected


# ---------------------------------------------------------------------------
# 4.1 — Composite and_check (Req 13.2)
# ---------------------------------------------------------------------------

def test_and_check_both_true():
    """Req 13.2: composite and_check evaluates correctly when both conditions are True."""
    inner = CheckCondition(attribute="cidr", condition="equals", values=["0.0.0.0/0"])
    outer = CheckCondition(attribute="port", condition="equals", values=[22], and_check=inner)
    attrs = {"port": 22, "cidr": "0.0.0.0/0"}
    assert evaluator.evaluate(outer, attrs) is True


def test_and_check_first_false():
    """and_check: if the first condition is False, the result is False."""
    inner = CheckCondition(attribute="cidr", condition="equals", values=["0.0.0.0/0"])
    outer = CheckCondition(attribute="port", condition="equals", values=[22], and_check=inner)
    attrs = {"port": 443, "cidr": "0.0.0.0/0"}
    assert evaluator.evaluate(outer, attrs) is False


def test_and_check_second_false():
    """and_check: if the second condition is False, the result is False."""
    inner = CheckCondition(attribute="cidr", condition="equals", values=["0.0.0.0/0"])
    outer = CheckCondition(attribute="port", condition="equals", values=[22], and_check=inner)
    attrs = {"port": 22, "cidr": "10.0.0.0/8"}
    assert evaluator.evaluate(outer, attrs) is False


# ---------------------------------------------------------------------------
# 4.1 — SG with multiple ingress blocks (Req 5.1, 5.2, 13.3)
# ---------------------------------------------------------------------------

def test_multi_ingress_detects_when_any_block_matches():
    """Req 5.1, 5.2, 13.3: SG with multiple ingress blocks detects a rule when any block satisfies it."""
    # Only the second ingress block has port 22 open to 0.0.0.0/0
    attrs = {
        "ingress": [
            {"from_port": 443, "to_port": 443, "cidr_blocks": ["10.0.0.0/8"]},
            {"from_port": 22,  "to_port": 22,  "cidr_blocks": ["0.0.0.0/0"]},
        ]
    }
    cond = CheckCondition(attribute="ingress.from_port", condition="equals", values=[22])
    assert evaluator.evaluate(cond, attrs) is True


def test_multi_ingress_no_match_when_none_satisfy():
    """Req 5.1: no finding when no ingress block satisfies the condition."""
    attrs = {
        "ingress": [
            {"from_port": 443, "to_port": 443, "cidr_blocks": ["10.0.0.0/8"]},
            {"from_port": 80,  "to_port": 80,  "cidr_blocks": ["10.0.0.0/8"]},
        ]
    }
    cond = CheckCondition(attribute="ingress.from_port", condition="equals", values=[22])
    assert evaluator.evaluate(cond, attrs) is False


def test_multi_ingress_first_block_matches():
    """Req 5.1: detects when the first block (not just last) matches."""
    attrs = {
        "ingress": [
            {"from_port": 22,  "to_port": 22,  "cidr_blocks": ["0.0.0.0/0"]},
            {"from_port": 443, "to_port": 443, "cidr_blocks": ["10.0.0.0/8"]},
        ]
    }
    cond = CheckCondition(attribute="ingress.from_port", condition="equals", values=[22])
    assert evaluator.evaluate(cond, attrs) is True


# ---------------------------------------------------------------------------
# 4.2 — Matcher: global tmac:ignore (Req 13.4)
# ---------------------------------------------------------------------------

def test_matcher_global_ignore_suppresses_all_findings():
    """Req 13.4: Matcher skips resources with a global # tmac:ignore."""
    rule = _make_rule(attribute="acl", condition="equals", values=["public-read"],
                      resource_type="aws_s3_bucket")
    resource = _make_resource(resource_type="aws_s3_bucket", name="my_bucket",
                               attributes={"acl": "public-read"})
    ignore_map = {"my_bucket": ["*"]}

    matcher = Matcher()
    findings = matcher.match([resource], [rule], ignore_map=ignore_map)
    assert findings == []


def test_matcher_global_ignore_does_not_affect_other_resources():
    """Global ignore on one resource does not suppress findings on another."""
    rule = _make_rule(attribute="acl", condition="equals", values=["public-read"],
                      resource_type="aws_s3_bucket")
    r1 = _make_resource(resource_type="aws_s3_bucket", name="ignored_bucket",
                         attributes={"acl": "public-read"})
    r2 = _make_resource(resource_type="aws_s3_bucket", name="other_bucket",
                         attributes={"acl": "public-read"})
    ignore_map = {"ignored_bucket": ["*"]}

    matcher = Matcher()
    findings = matcher.match([r1, r2], [rule], ignore_map=ignore_map)
    assert len(findings) == 1
    assert findings[0].resource_name == "other_bucket"


# ---------------------------------------------------------------------------
# 4.2 — Matcher: tmac:ignore[RULE-ID] (Req 13.5)
# ---------------------------------------------------------------------------

def test_matcher_rule_ignore_suppresses_only_specified_rule():
    """Req 13.5: Matcher skips only the specified rule with # tmac:ignore[RULE-ID]."""
    rule1 = _make_rule(rule_id="TMAC-AWS-S3-001", attribute="acl",
                        condition="equals", values=["public-read"],
                        resource_type="aws_s3_bucket")
    rule2 = _make_rule(rule_id="TMAC-AWS-S3-002", attribute="encryption",
                        condition="not_exists", resource_type="aws_s3_bucket")
    resource = _make_resource(resource_type="aws_s3_bucket", name="my_bucket",
                               attributes={"acl": "public-read"})
    # Only ignore rule1; rule2 should still fire (encryption not_exists → True)
    ignore_map = {"my_bucket": ["TMAC-AWS-S3-001"]}

    matcher = Matcher()
    findings = matcher.match([resource], [rule1, rule2], ignore_map=ignore_map)
    rule_ids = [f.rule_id for f in findings]
    assert "TMAC-AWS-S3-001" not in rule_ids
    assert "TMAC-AWS-S3-002" in rule_ids


def test_matcher_no_ignore_map_produces_findings():
    """Without ignore_map, all matching rules produce findings."""
    rule = _make_rule(attribute="acl", condition="equals", values=["public-read"],
                      resource_type="aws_s3_bucket")
    resource = _make_resource(resource_type="aws_s3_bucket", name="my_bucket",
                               attributes={"acl": "public-read"})

    matcher = Matcher()
    findings = matcher.match([resource], [rule])
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# Property 9: Evaluator detects a condition in any element of a list of blocks
# Validates: Requirements 5.1, 5.2, 5.5
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.lists(
        st.integers(min_value=1, max_value=65535),
        min_size=1,
        max_size=10,
    )
)
def test_property_9_evaluator_list_any_match(ports):
    """
    **Validates: Requirements 5.1, 5.2, 5.5**
    Property 9: Evaluator detects a condition in any element of a list of blocks.
    If any ingress block has from_port == 22, the evaluator must return True.
    Reordering the blocks does not change the result.
    """
    target_port = 22
    ingress_blocks = [{"from_port": p, "to_port": p, "cidr_blocks": ["0.0.0.0/0"]} for p in ports]
    attrs = {"ingress": ingress_blocks}
    cond = CheckCondition(attribute="ingress.from_port", condition="equals", values=[target_port])

    result = evaluator.evaluate(cond, attrs)
    expected = any(p == target_port for p in ports)
    assert result == expected

    # Reordering must not change the result (invariance of order)
    reversed_attrs = {"ingress": list(reversed(ingress_blocks))}
    assert evaluator.evaluate(cond, reversed_attrs) == expected


# ---------------------------------------------------------------------------
# Property 10: Evaluator is correct for all operators
# Validates: Requirements 5.4
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.one_of(
        st.text(min_size=0, max_size=20),
        st.integers(),
        st.none(),
    )
)
def test_property_10_equals_operator_correctness(value):
    """
    **Validates: Requirements 5.4**
    Property 10 (partial): equals operator is logically correct for any value.
    """
    sentinel = "SENTINEL_VALUE_XYZ"
    cond_match = CheckCondition(attribute="x", condition="equals", values=[sentinel])
    cond_no_match = CheckCondition(attribute="x", condition="equals", values=["OTHER_VALUE_ABC"])

    if value is None:
        attrs: dict = {}
    else:
        attrs = {"x": value}

    # equals sentinel → True only when value IS sentinel
    assert evaluator.evaluate(cond_match, attrs) == (value == sentinel)
    # equals other → True only when value IS other (never, since value is arbitrary)
    assert evaluator.evaluate(cond_no_match, attrs) == (value == "OTHER_VALUE_ABC")


@settings(max_examples=100)
@given(st.text(min_size=1, max_size=30))
def test_property_10_not_equals_is_complement_of_equals(value):
    """
    **Validates: Requirements 5.4**
    Property 10: not_equals is the logical complement of equals for non-None values.
    """
    target = "target_value"
    attrs = {"x": value}
    cond_eq = CheckCondition(attribute="x", condition="equals", values=[target])
    cond_ne = CheckCondition(attribute="x", condition="not_equals", values=[target])
    assert evaluator.evaluate(cond_eq, attrs) != evaluator.evaluate(cond_ne, attrs)


@settings(max_examples=100)
@given(st.text(min_size=1, max_size=30))
def test_property_10_exists_not_exists_complement(value):
    """
    **Validates: Requirements 5.4**
    Property 10: exists and not_exists are always complements.
    """
    attrs_with = {"x": value}
    attrs_without: dict = {}
    cond_exists = CheckCondition(attribute="x", condition="exists", values=[])
    cond_not_exists = CheckCondition(attribute="x", condition="not_exists", values=[])

    assert evaluator.evaluate(cond_exists, attrs_with) is True
    assert evaluator.evaluate(cond_not_exists, attrs_with) is False
    assert evaluator.evaluate(cond_exists, attrs_without) is False
    assert evaluator.evaluate(cond_not_exists, attrs_without) is True
