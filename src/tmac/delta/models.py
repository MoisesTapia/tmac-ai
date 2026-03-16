"""Delta data models for TMAC v1.1.0."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from tmac.models.finding import Finding, ScanResult


class ChangeAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    replace = "replace"


class PlannedChange(BaseModel):
    address: str
    resource_type: str
    resource_name: str
    action: ChangeAction
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None


class DeltaFinding(Finding):
    change_action: ChangeAction
    changed_attribute: str
    value_before: Optional[Any] = None
    value_after: Optional[Any] = None


class DeltaScanResult(ScanResult):
    """Extends ScanResult with delta statistics.

    Invariant: findings_introduced == len(findings) always.
    """

    findings_introduced: int = 0
    findings_resolved: int = 0
    resources_created: int = 0
    resources_updated: int = 0
    resources_deleted: int = 0
    plan_file: str = ""
