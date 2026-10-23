"""Single source of truth for severity ordering and filtering."""
from typing import Dict, List, Sequence, TypeVar

from tmac.models.finding import Finding

SEVERITY_LEVELS: Dict[str, int] = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

F = TypeVar("F", bound=Finding)


def severity_level(severity: str, default: int = 0) -> int:
    """Numeric level for a severity name (case-insensitive)."""
    return SEVERITY_LEVELS.get(severity.lower(), default)


def filter_by_min_severity(findings: Sequence[F], min_severity: str) -> List[F]:
    """Keep findings at or above min_severity; "all" keeps everything."""
    if min_severity == "all":
        return list(findings)
    min_level = severity_level(min_severity)
    return [f for f in findings if severity_level(f.severity) >= min_level]
