import fnmatch
import logging
import time
from pathlib import Path
from typing import List, Optional, Set

from tmac.config import ConfigError, load_config
from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader
from tmac.engine.severity import filter_by_min_severity
from tmac.models.finding import ScanMetadata, ScanResult, ScanStatistics
from tmac.parsers.base import BaseParser
from tmac.parsers.terraform import TerraformParser

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """Raised when the scan pipeline cannot proceed."""
    pass


class Scanner:
    """Orchestrates the full TMAC scan pipeline (SRP: no presentation logic).

    Format-agnostic: file discovery and parsing are delegated to ``parser``
    (Terraform by default). Supporting a new IaC format means writing a
    BaseParser subclass, not a new scanner.
    """

    def __init__(self, parser: Optional[BaseParser] = None) -> None:
        self.parser = parser or TerraformParser()
        if not self.parser.file_patterns:
            raise ValueError(f"{type(self.parser).__name__} declares no file_patterns")

    def run_scan(
        self,
        directory: str,
        rules_dir: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
        min_severity: str = "all",
        verbose: bool = False,
        include_paths: Optional[List[str]] = None,
    ) -> ScanResult:
        start = time.time()
        exclude_patterns = exclude_patterns or []

        # Validate directory
        scan_path = Path(directory)
        if not scan_path.exists() or not scan_path.is_dir():
            raise ScanError(f"Directory not accessible: {directory}")

        # Load config (may raise ConfigError → caller converts to ScanError)
        try:
            cfg = load_config()
        except ConfigError as e:
            raise ScanError(str(e)) from e

        cfg_exclude = cfg.get("scan", {}).get("exclude", [])
        all_excludes = list(exclude_patterns) + cfg_exclude

        # Restrict to include_paths (resolved absolute paths) when provided (CI delta mode)
        include_set = (
            {str(Path(p).resolve()) for p in include_paths} if include_paths is not None else None
        )

        files = self._discover_files(scan_path, all_excludes, include_set)
        logger.debug(
            "Discovered %d files (%s) in %s",
            len(files), ", ".join(self.parser.file_patterns), directory,
        )

        # Parse resources (tmac:ignore suppressions travel on each ResourceModel)
        all_resources = []
        files_failed = 0

        for file in files:
            resources = self.parser.parse(str(file))
            # Detect parse failure: non-empty file that returned no resources
            # (parser.parse returns [] on error per its implementation)
            if not resources:
                try:
                    file_size = file.stat().st_size
                except OSError:
                    file_size = 0
                if file_size > 0:
                    # Non-empty file that yielded nothing — treat as parse failure
                    files_failed += 1
            all_resources.extend(resources)

        # Load rules
        extra_dir = rules_dir or cfg.get("scan", {}).get("rules_dir")
        loader = RuleLoader()
        rules = loader.load_rules(extra_dir)
        logger.debug("Loaded %d rules", len(rules))

        # Match
        matcher = Matcher()
        findings = filter_by_min_severity(matcher.match(all_resources, rules), min_severity)

        return ScanResult(
            metadata=ScanMetadata(
                scanned_directory=str(directory),
                execution_time_seconds=time.time() - start,
            ),
            statistics=ScanStatistics.from_findings(findings, total_resources=len(all_resources)),
            findings=findings,
            files_scanned=len(files),
            rules_loaded=len(rules),
            files_failed=files_failed,
        )

    def _discover_files(
        self, scan_path: Path, excludes: List[str], include_set: Optional[Set[str]] = None
    ) -> List[Path]:
        """Files matching the parser's patterns, minus excludes, deduplicated and sorted.

        When ``include_set`` is given, only those (resolved, absolute) paths are kept.
        """
        found = {
            f
            for pattern in self.parser.file_patterns
            for f in scan_path.rglob(pattern)
            if f.is_file()
            and (include_set is None or str(f.resolve()) in include_set)
            and not _is_excluded(f, excludes)
        }
        return sorted(f for f in found if self.parser.can_parse(str(f)))


def _is_excluded(file_path: Path, patterns: List[str]) -> bool:
    """Return True if any exclude pattern matches any part of the file path."""
    path_str = str(file_path)
    for pattern in patterns:
        if fnmatch.fnmatch(file_path.name, pattern):
            return True
        if fnmatch.fnmatch(path_str, f"*{pattern}*"):
            return True
    return False
