import logging
import yaml  # type: ignore
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

ALLOWED_TOP_KEYS = {"scan", "report"}
ALLOWED_SCAN_KEYS = {"dir", "exclude", "rules_dir"}
ALLOWED_REPORT_KEYS = {"format", "fail_on", "severity"}
ALLOWED_FORMATS = {"html", "json", "md"}


class ConfigError(Exception):
    """Raised when the config file has syntax errors or is unreadable."""
    pass


def load_config(config_path: str = ".tmac.yaml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        raise ConfigError(f"Cannot read config file {config_path}: {e}") from e

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML syntax error in {config_path}: {e}") from e

    if not data:
        return {}

    if not isinstance(data, dict):
        raise ConfigError(f"Config file {config_path} must be a YAML mapping at the top level.")

    # Warn about unknown top-level keys and keep only valid ones
    unknown_top = set(data.keys()) - ALLOWED_TOP_KEYS
    if unknown_top:
        logger.warning(
            "Unknown top-level keys in %s: %s — ignoring them",
            config_path,
            sorted(unknown_top),
        )
    result: Dict[str, Any] = {k: v for k, v in data.items() if k in ALLOWED_TOP_KEYS}

    # Validate scan section
    if "scan" in result and isinstance(result["scan"], dict):
        scan = result["scan"]
        unknown_scan = set(scan.keys()) - ALLOWED_SCAN_KEYS
        if unknown_scan:
            logger.warning(
                "Unknown keys in scan section of %s: %s — ignoring them",
                config_path,
                sorted(unknown_scan),
            )
            result["scan"] = {k: v for k, v in scan.items() if k in ALLOWED_SCAN_KEYS}

        # Validate scan.exclude is a list of strings
        if "exclude" in result["scan"]:
            exclude_val = result["scan"]["exclude"]
            if not isinstance(exclude_val, list) or not all(
                isinstance(item, str) for item in exclude_val
            ):
                logger.warning(
                    "scan.exclude in %s must be a list of strings — ignoring it",
                    config_path,
                )
                del result["scan"]["exclude"]

    # Validate report section
    if "report" in result and isinstance(result["report"], dict):
        report = result["report"]
        unknown_report = set(report.keys()) - ALLOWED_REPORT_KEYS
        if unknown_report:
            logger.warning(
                "Unknown keys in report section of %s: %s — ignoring them",
                config_path,
                sorted(unknown_report),
            )
            result["report"] = {k: v for k, v in report.items() if k in ALLOWED_REPORT_KEYS}

        # Validate report.format is a permitted value
        if "format" in result["report"]:
            fmt = result["report"]["format"]
            if fmt not in ALLOWED_FORMATS:
                logger.warning(
                    "report.format '%s' in %s is not valid (allowed: %s) — ignoring it",
                    fmt,
                    config_path,
                    sorted(ALLOWED_FORMATS),
                )
                del result["report"]["format"]

    return result
