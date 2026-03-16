"""Hypothesis strategies for TMAC v1.1.0 delta models.

Provides reusable strategies for generating valid instances of:
- PlannedChange
- DeltaFinding
- ThreatRule / CheckCondition
- Resource attribute dicts

Feature: tmac-v1-1-tfplan-delta
Validates: Requirements 7.6
"""

from hypothesis import strategies as st

from tmac.delta.models import ChangeAction, DeltaFinding, PlannedChange
from tmac.models.rule import CheckCondition, ThreatRule

# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

_RESOURCE_TYPES = ["aws_s3_bucket", "aws_security_group", "aws_iam_role"]
_SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]
_STRIDES = [
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
]
_CONDITIONS = ["equals", "not_equals", "in", "not_in", "exists", "not_exists"]
_ACL_VALUES = ["private", "public-read", "public-read-write", "authenticated-read"]

# Simple non-empty identifier text (letters + underscores)
_identifier = st.from_regex(r"[a-z][a-z_]{0,15}", fullmatch=True)


# ---------------------------------------------------------------------------
# attributes_strategy — generates AWS-like resource attribute dicts
# ---------------------------------------------------------------------------

def attributes_strategy() -> st.SearchStrategy:
    """Generate dicts of AWS resource attributes suitable for rule evaluation."""
    return st.fixed_dictionaries(
        {},
        optional={
            "acl": st.sampled_from(_ACL_VALUES),
            "bucket": _identifier,
            "versioning_enabled": st.booleans(),
            "logging": st.one_of(st.none(), st.just({"target_bucket": "logs"})),
            "server_side_encryption": st.one_of(st.none(), st.just("AES256")),
            "publicly_accessible": st.booleans(),
            "multi_az": st.booleans(),
            "encrypted": st.booleans(),
        },
    )


# ---------------------------------------------------------------------------
# planned_change_strategy — generates valid PlannedChange instances
# ---------------------------------------------------------------------------

def _before_after_for_action(action: ChangeAction):
    """Return (before_strategy, after_strategy) consistent with the given action."""
    attrs = attributes_strategy()
    if action == ChangeAction.create:
        return st.just(None), attrs
    elif action == ChangeAction.delete:
        return attrs, st.just(None)
    else:  # update or replace
        return attrs, attrs


@st.composite
def planned_change_strategy(draw) -> PlannedChange:
    """Generate a PlannedChange with semantically consistent before/after values."""
    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    resource_name = draw(_identifier)
    action = draw(st.sampled_from(list(ChangeAction)))

    before_st, after_st = _before_after_for_action(action)
    before = draw(before_st)
    after = draw(after_st)

    address = f"{resource_type}.{resource_name}"

    return PlannedChange(
        address=address,
        resource_type=resource_type,
        resource_name=resource_name,
        action=action,
        before=before,
        after=after,
    )


# ---------------------------------------------------------------------------
# delta_finding_strategy — generates valid DeltaFinding instances
# ---------------------------------------------------------------------------

@st.composite
def delta_finding_strategy(draw) -> DeltaFinding:
    """Generate a DeltaFinding with all required fields populated."""
    change_action = draw(st.sampled_from(list(ChangeAction)))

    # value_before is None for create; value_after is None for delete
    if change_action == ChangeAction.create:
        value_before = None
        value_after = draw(st.one_of(st.none(), st.text(max_size=50)))
    elif change_action == ChangeAction.delete:
        value_before = draw(st.one_of(st.none(), st.text(max_size=50)))
        value_after = None
    else:
        value_before = draw(st.one_of(st.none(), st.text(max_size=50)))
        value_after = draw(st.one_of(st.none(), st.text(max_size=50)))

    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    resource_name = draw(_identifier)

    return DeltaFinding(
        rule_id=draw(st.from_regex(r"TMAC-[A-Z]+-[A-Z0-9]+-\d{3}", fullmatch=True)),
        rule_name=draw(st.text(min_size=1, max_size=60)),
        severity=draw(st.sampled_from(_SEVERITIES)),
        stride=draw(st.sampled_from(_STRIDES)),
        resource_type=resource_type,
        resource_name=resource_name,
        file_path=f"{resource_type}.{resource_name}",
        line_number=draw(st.integers(min_value=0, max_value=9999)),
        matched_attribute=draw(_identifier),
        description=draw(st.text(max_size=200)),
        mitigation=draw(st.text(max_size=200)),
        references=draw(st.lists(st.text(max_size=100), max_size=3)),
        tags=draw(st.lists(_identifier, max_size=5)),
        change_action=change_action,
        changed_attribute=draw(_identifier),
        value_before=value_before,
        value_after=value_after,
    )


# ---------------------------------------------------------------------------
# rule_strategy — generates ThreatRule with valid CheckCondition
# ---------------------------------------------------------------------------

@st.composite
def rule_strategy(draw) -> ThreatRule:
    """Generate a ThreatRule with a valid CheckCondition."""
    condition = draw(st.sampled_from(_CONDITIONS))
    attribute = draw(_identifier)

    if condition in ("exists", "not_exists"):
        values = []
    else:
        values = draw(st.lists(st.sampled_from(_ACL_VALUES), min_size=1, max_size=3))

    check = CheckCondition(attribute=attribute, condition=condition, values=values)

    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    rule_id = draw(st.from_regex(r"TMAC-[A-Z]+-[A-Z0-9]+-\d{3}", fullmatch=True))

    return ThreatRule(
        id=rule_id,
        name=draw(st.text(min_size=1, max_size=60)),
        resource_type=resource_type,
        check=check,
        severity=draw(st.sampled_from(_SEVERITIES)),
        stride=draw(st.sampled_from(_STRIDES)),
        description=draw(st.text(max_size=200)),
        mitigation=draw(st.text(max_size=200)),
        references=draw(st.lists(st.text(max_size=100), max_size=3)),
        tags=draw(st.lists(_identifier, max_size=5)),
    )
