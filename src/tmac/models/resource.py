from typing import Any, Dict, List
from pydantic import BaseModel, Field

class ResourceModel(BaseModel):
    resource_type: str
    name: str
    attributes: Dict[str, Any]
    source_file: str
    line_number: int = 0
    # tmac:ignore suppressions bound to this exact resource: ["*"] or ["RULE-ID", ...]
    ignored_rules: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
