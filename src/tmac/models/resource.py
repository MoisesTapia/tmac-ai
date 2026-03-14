from typing import Any, Dict
from pydantic import BaseModel

class ResourceModel(BaseModel):
    resource_type: str
    name: str
    attributes: Dict[str, Any]
    source_file: str
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
