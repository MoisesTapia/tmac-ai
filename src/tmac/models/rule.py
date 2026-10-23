import re
from typing import Any, Literal, Optional, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

Severity = Literal["Critical", "High", "Medium", "Low", "Info"]
Stride = Literal[
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
]
# Must stay in sync with Evaluator._evaluate_condition.
ConditionOp = Literal[
    "equals",
    "not_equals",
    "in",
    "not_in",
    "contains",
    "not_contains",
    "regex",
    "exists",
    "not_exists",
]
VALUELESS_CONDITIONS = {"exists", "not_exists"}


def _canonical(value: Any, allowed: Any, field: str) -> Any:
    """Map a case-insensitive input onto its canonical Literal spelling."""
    if not isinstance(value, str):
        return value
    lookup: dict[str, str] = {opt.lower(): opt for opt in get_args(allowed)}
    canonical = lookup.get(value.strip().lower())
    if canonical is None:
        raise ValueError(f"invalid {field} {value!r}; allowed: {', '.join(get_args(allowed))}")
    return canonical


class CheckCondition(BaseModel):
    attribute: str
    condition: ConditionOp
    values: list[Any] = Field(default_factory=list)
    and_check: Optional["CheckCondition"] = None

    @field_validator("condition", mode="before")
    @classmethod
    def _normalize_condition(cls, v: Any) -> Any:
        return _canonical(v, ConditionOp, "condition")

    @model_validator(mode="after")
    def _check_values(self) -> "CheckCondition":
        # Without values these conditions can never match, so the rule would never fire.
        if self.condition not in VALUELESS_CONDITIONS and not self.values:
            raise ValueError(f"condition '{self.condition}' requires at least one value")
        if self.condition == "regex":
            for pattern in self.values:
                try:
                    re.compile(str(pattern))
                except re.error as e:
                    raise ValueError(f"invalid regex {pattern!r}: {e}") from e
        return self


class ThreatRule(BaseModel):
    id: str
    name: str
    resource_type: str
    check: CheckCondition
    severity: Severity
    stride: Stride
    description: str
    mitigation: str
    references: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v: Any) -> Any:
        return _canonical(v, Severity, "severity")

    @field_validator("stride", mode="before")
    @classmethod
    def _normalize_stride(cls, v: Any) -> Any:
        return _canonical(v, Stride, "stride")
