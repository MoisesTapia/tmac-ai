from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from tmac import __version__


class Finding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    stride: str
    resource_type: str
    resource_name: str
    file_path: str
    line_number: int
    matched_attribute: str
    description: str
    mitigation: str
    references: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ScanMetadata(BaseModel):
    tool_name: str = "TMAC"
    version: str = __version__
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    )
    scanned_directory: str
    execution_time_seconds: float = 0.0


class ScanStatistics(BaseModel):
    total_resources: int = 0
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0

    @classmethod
    def from_findings(cls, findings: Sequence[Finding], total_resources: int) -> "ScanStatistics":
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = f.severity.lower()
            if sev in counts:
                counts[sev] += 1
        return cls(total_resources=total_resources, total_findings=len(findings), **counts)


class ScanIssue(BaseModel):
    """Something that made the scan incomplete: an unparseable IaC file or an invalid rule."""

    kind: Literal["parse", "rules"]
    file_path: str
    message: str


class ScanResult(BaseModel):
    metadata: ScanMetadata
    statistics: ScanStatistics
    findings: list[Finding]
    files_scanned: int = 0
    rules_loaded: int = 0
    # Number of IaC files that could not be parsed (== parse issues below).
    files_failed: int = 0
    # Non-empty means the results may be missing findings (the scan is not trustworthy).
    issues: list[ScanIssue] = Field(default_factory=list)
