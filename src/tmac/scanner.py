import fnmatch
import logging
import time
from pathlib import Path
from typing import List, Optional

from tmac.config import ConfigError, load_config
from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader
from tmac.models.finding import ScanMetadata, ScanResult, ScanStatistics
from tmac.parsers.terraform import TerraformParser

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """Raised when the scan pipeline cannot proceed."""
    pass


class Scanner:
    """Orchestrates the full TMAC scan pipeline (SRP: no presentation logic)."""

    def run_scan(
        self,
        directory: str,
        rules_dir: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
        min_severity: str = "all",
        verbose: bool = False,
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

        # Discover .tf files, applying exclude patterns
        tf_files = [
            f for f in scan_path.rglob("*.tf")
            if not _is_excluded(f, all_excludes)
        ]
        logger.debug("Discovered %d .tf files in %s", len(tf_files), directory)

        # Parse resources
        parser = TerraformParser()
        all_resources = []
        combined_ignore_map: dict = {}

        for tf_file in tf_files:
            resources = parser.parse(str(tf_file))
            all_resources.extend(resources)
            for res_name, rules_list in parser.get_ignore_map(str(tf_file)).items():
                existing = combined_ignore_map.get(res_name, [])
                merged = list(existing)
                for rid in rules_list:
                    if rid not in merged:
                        merged.append(rid)
                combined_ignore_map[res_name] = ["*"] if "*" in merged else merged

        # Load rules
        extra_dir = rules_dir or cfg.get("scan", {}).get("rules_dir")
        loader = RuleLoader()
        rules = loader.load_rules(extra_dir)
        logger.debug("Loaded %d rules", len(rules))

        # Match
        matcher = Matcher()
        findings = matcher.match(all_resources, rules, ignore_map=combined_ignore_map)

        # Filter by min_severity
        severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        if min_severity != "all":
            min_level = severity_levels.get(min_severity.lower(), 0)
            findings = [f for f in findings if severity_levels.get(f.severity.lower(), 0) >= min_level]

        stats = ScanStatistics(
            total_resources=len(all_resources),
            total_findings=len(findings),
            critical=sum(1 for f in findings if f.severity.lower() == "critical"),
            high=sum(1 for f in findings if f.severity.lower() == "high"),
            medium=sum(1 for f in findings if f.severity.lower() == "medium"),
            low=sum(1 for f in findings if f.severity.lower() == "low"),
            info=sum(1 for f in findings if f.severity.lower() == "info"),
        )

        return ScanResult(
            metadata=ScanMetadata(
                scanned_directory=str(directory),
                execution_time_seconds=time.time() - start,
            ),
            statistics=stats,
            findings=findings,
            files_scanned=len(tf_files),
            rules_loaded=len(rules),
        )


def _is_excluded(file_path: Path, patterns: List[str]) -> bool:
    """Return True if any exclude pattern matches any part of the file path."""
    path_str = str(file_path)
    for pattern in patterns:
        if fnmatch.fnmatch(file_path.name, pattern):
            return True
        if fnmatch.fnmatch(path_str, f"*{pattern}*"):
            return True
    return False
