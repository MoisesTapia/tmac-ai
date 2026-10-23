"""Delta data models for TMAC v1.1.0."""

from enum import Enum
from typing import Any

from pydantic import BaseModel

from tmac.models.finding import Finding, ScanResult


class ChangeAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    # Shadows str.replace (this enum subclasses str); kept for API/serialization compatibility.
    replace = "replace"  # type: ignore[assignment]


class PlannedChange(BaseModel):
    address: str
    resource_type: str
    resource_name: str
    action: ChangeAction
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class DeltaFinding(Finding):
    change_action: ChangeAction
    changed_attribute: str
    value_before: Any | None = None
    value_after: Any | None = None


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
