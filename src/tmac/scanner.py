import fnmatch
import logging
import os
import time
from pathlib import Path
from typing import Any

from tmac.config import ConfigError, load_config
from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader
from tmac.engine.severity import filter_by_min_severity
from tmac.models.finding import ScanIssue, ScanMetadata, ScanResult, ScanStatistics
from tmac.parsers.base import BaseParser, ParseError
from tmac.parsers.terraform import TerraformParser

logger = logging.getLogger(__name__)

# Never descended into: VCS metadata, downloaded dependencies/modules and tool caches.
# (.terraform holds third-party module copies; scanning them reports findings the
# project doesn't own.)
DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".git", ".hg", ".svn", ".terraform", ".terragrunt-cache", "node_modules",
        ".venv", "venv", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", ".aws-sam",
    }
)  # fmt: skip


class ScanError(Exception):
    """Raised when the scan pipeline cannot proceed."""


class Scanner:
    """Orchestrates the full TMAC scan pipeline (SRP: no presentation logic).

    Format-agnostic: file discovery and parsing are delegated to ``parser``
    (Terraform by default). Supporting a new IaC format means writing a
    BaseParser subclass, not a new scanner.
    """

    def __init__(self, parser: BaseParser | None = None) -> None:
        self.parser = parser or TerraformParser()
        if not self.parser.file_patterns:
            raise ValueError(f"{type(self.parser).__name__} declares no file_patterns")

    def run_scan(
        self,
        directory: str,
        rules_dir: str | None = None,
        exclude_patterns: list[str] | None = None,
        min_severity: str = "all",
        verbose: bool = False,
        config: dict[str, Any] | None = None,
    ) -> ScanResult:
        """Run the scan. ``config`` is an already-loaded .tmac.yaml; when None, the
        default ./.tmac.yaml is loaded."""
        start = time.time()
        exclude_patterns = exclude_patterns or []

        # Validate directory
        scan_path = Path(directory)
        if not scan_path.exists() or not scan_path.is_dir():
            raise ScanError(f"Directory not accessible: {directory}")

        # Load config (may raise ConfigError → caller converts to ScanError)
        if config is not None:
            cfg = config
        else:
            try:
                cfg = load_config()
            except ConfigError as e:
                raise ScanError(str(e)) from e

        cfg_exclude = cfg.get("scan", {}).get("exclude", [])
        all_excludes = list(exclude_patterns) + cfg_exclude

        files = self._discover_files(scan_path, all_excludes)
        logger.debug(
            "Discovered %d files (%s) in %s",
            len(files),
            ", ".join(self.parser.file_patterns),
            directory,
        )

        # Parse resources (tmac:ignore suppressions travel on each ResourceModel).
        # Unparseable files are recorded, not silently treated as empty.
        all_resources = []
        issues: list[ScanIssue] = []
        for file in files:
            try:
                all_resources.extend(self.parser.parse_strict(str(file)))
            except ParseError as e:
                logger.warning("%s", e)
                issues.append(ScanIssue(kind="parse", file_path=str(file), message=str(e)))

        # Load rules
        extra_dir = rules_dir or cfg.get("scan", {}).get("rules_dir")
        loader = RuleLoader()
        rules = loader.load_rules(extra_dir)
        issues.extend(loader.issues)
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
            issues=issues,
        )

    def _discover_files(self, scan_path: Path, excludes: list[str]) -> list[Path]:
        """Files matching the parser's patterns, minus excludes, sorted.

        Directories in DEFAULT_EXCLUDED_DIRS are pruned while walking, so vendored
        trees (node_modules, .terraform, virtualenvs) are never read.
        """
        found: list[Path] = []
        for root, dirs, files in os.walk(scan_path):
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDED_DIRS]
            for name in files:
                if not any(fnmatch.fnmatch(name, p) for p in self.parser.file_patterns):
                    continue
                path = Path(root) / name
                if not _is_excluded(path, excludes) and self.parser.can_parse(str(path)):
                    found.append(path)
        return sorted(found)


def _is_excluded(file_path: Path, patterns: list[str]) -> bool:
    """Return True if any exclude pattern matches any part of the file path."""
    path_str = str(file_path)
    for pattern in patterns:
        if fnmatch.fnmatch(file_path.name, pattern):
            return True
        if fnmatch.fnmatch(path_str, f"*{pattern}*"):
            return True
    return False
