from typing import Any

from pydantic import BaseModel, Field

# IgnoreMap: resource key (name, or address for tfplan) → ["*"] (global) or ["RULE-ID-1", ...]
IgnoreMap = dict[str, list[str]]
# Same, keyed by (resource_type, resource_name).
ResourceIgnoreMap = dict[tuple[str, str], list[str]]


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
