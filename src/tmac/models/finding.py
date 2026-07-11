from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

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
    references: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class ScanMetadata(BaseModel):
    tool_name: str = "TMAC"
    version: str = "1.6.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
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

class ScanResult(BaseModel):
    metadata: ScanMetadata
    statistics: ScanStatistics
    findings: List[Finding]
    files_scanned: int = 0
    rules_loaded: int = 0
    files_failed: int = 0  # count of .tf files that could not be parsed (returned [] for non-empty content)
