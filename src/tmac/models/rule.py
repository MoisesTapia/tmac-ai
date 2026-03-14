from typing import Any, List, Optional
from pydantic import BaseModel, Field

class CheckCondition(BaseModel):
    attribute: str
    condition: str
    values: List[Any] = Field(default_factory=list)
    and_check: Optional["CheckCondition"] = None

class ThreatRule(BaseModel):
    id: str
    name: str
    resource_type: str
    check: CheckCondition
    severity: str
    stride: str
    description: str
    mitigation: str
    references: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
