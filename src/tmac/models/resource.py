from typing import Any

from pydantic import BaseModel, Field

# IgnoreMap: resource key (name, or address for tfplan) → ["*"] (global) or ["RULE-ID-1", ...]
IgnoreMap = dict[str, list[str]]
# Same, keyed by (resource_type, resource_name).
ResourceIgnoreMap = dict[tuple[str, str], list[str]]

# CloudFormation intrinsic functions, as normalized by CloudFormationParser:
# `!Ref X` / {"Ref": X} -> {"Ref": X}; `!Sub s` / {"Fn::Sub": s} -> {"Sub": s}; etc.
INTRINSIC_FUNCTIONS = frozenset(
    {
        "Ref", "Base64", "Cidr", "FindInMap", "GetAtt", "GetAZs", "ImportValue", "Join",
        "Length", "Select", "Split", "Sub", "ToJsonString", "Transform",
        "And", "Equals", "If", "Not", "Or", "Condition",
    }
)  # fmt: skip


def is_unresolved_reference(value: Any) -> bool:
    """True for a normalized intrinsic-function value ({"Ref": ...}, {"Sub": ...}, ...).

    Such a value is present but only known at deploy time, so rules can tell that it
    exists but cannot compare it.
    """
    return isinstance(value, dict) and len(value) == 1 and next(iter(value)) in INTRINSIC_FUNCTIONS


class ResourceModel(BaseModel):
    resource_type: str
    name: str
    attributes: dict[str, Any]
    source_file: str
    line_number: int = 0
    # tmac:ignore suppressions bound to this exact resource: ["*"] or ["RULE-ID", ...]
    ignored_rules: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
