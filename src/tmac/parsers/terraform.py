import logging
import re
from io import StringIO
from pathlib import Path

import hcl2

from tmac.models.resource import IgnoreMap, ResourceIgnoreMap, ResourceModel
from tmac.parsers.base import BaseParser, ParseError

logger = logging.getLogger(__name__)

LineMap = dict[tuple[str, str], int]


def merge_ignores(existing: list[str], new: list[str]) -> list[str]:
    """Merge rule-ID lists without duplicates; any "*" collapses the result to global."""
    merged = list(existing)
    for rid in new:
        if rid not in merged:
            merged.append(rid)
    return ["*"] if "*" in merged else merged


class TerraformParser(BaseParser):
    """Parser for Terraform HCL format (.tf files)."""

    file_patterns = ("*.tf",)

    def parse(self, file_path: str) -> list[ResourceModel]:
        """Lenient parse: logs a warning and returns [] if the file cannot be parsed."""
        try:
            return self.parse_strict(file_path)
        except ParseError as e:
            logger.warning("%s", e)
            return []

    def parse_strict(self, file_path: str) -> list[ResourceModel]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            line_map, ignores = self._prescan_resources(content)
            parsed = hcl2.load(StringIO(content))  # type: ignore
        except Exception as e:
            raise ParseError(f"Failed to parse {file_path}: {e}") from e

        resources: list[ResourceModel] = []
        if "resource" in parsed:
            for block in parsed["resource"]:
                for res_type, res_dict in block.items():
                    for res_name, res_attrs in res_dict.items():
                        key = (res_type, res_name)
                        resources.append(
                            ResourceModel(
                                resource_type=res_type,
                                name=res_name,
                                attributes=res_attrs,
                                source_file=file_path,
                                line_number=line_map.get(key, 0),
                                ignored_rules=ignores.get(key, []),
                            )
                        )
        return resources

    def get_resource_ignores(self, file_path: str) -> ResourceIgnoreMap:
        """Return tmac:ignore suppressions keyed by (resource_type, resource_name)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            _, ignores = self._prescan_resources(content)
            return ignores
        except Exception as e:
            logger.warning("Failed to read ignore map from %s: %s", file_path, e)
            return {}

    def collect_resource_ignores(self, directory: str) -> ResourceIgnoreMap:
        """Merge tmac:ignore suppressions from every .tf file under ``directory``.

        Used by ``tmac plan --source-dir``: plan JSON carries no comments, so
        suppressions are matched to planned changes by (resource_type, resource_name).
        """
        merged: ResourceIgnoreMap = {}
        for tf_file in sorted(Path(directory).rglob("*.tf")):
            for key, rule_ids in self.get_resource_ignores(str(tf_file)).items():
                merged[key] = merge_ignores(merged.get(key, []), rule_ids)
        return merged

    def get_ignore_map(self, file_path: str) -> IgnoreMap:
        """Return the ignore_map for a file without full parsing."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            _, ignore_map = self._prescan(content)
            return ignore_map
        except Exception as e:
            logger.warning("Failed to read ignore map from %s: %s", file_path, e)
            return {}

    def _prescan(self, content: str) -> tuple[LineMap, IgnoreMap]:
        """
        Pre-scan of raw .tf content with the ignore map keyed by resource name only.

        Kept for backwards compatibility; resources of different types sharing a name
        are merged here. parse() uses _prescan_resources() instead.

        Returns:
            line_map:   {(resource_type, resource_name): line_number}  (1-indexed)
            ignore_map: {resource_name: ["*"] | ["RULE-ID-1", ...]}
        """
        line_map, ignores = self._prescan_resources(content)
        ignore_map: IgnoreMap = {}
        for (_, res_name), rule_ids in ignores.items():
            ignore_map[res_name] = merge_ignores(ignore_map.get(res_name, []), rule_ids)
        return line_map, ignore_map

    def _prescan_resources(self, content: str) -> tuple[LineMap, ResourceIgnoreMap]:
        """
        Single-pass pre-scan of raw .tf content.

        Returns:
            line_map: {(resource_type, resource_name): line_number}  (1-indexed)
            ignores:  {(resource_type, resource_name): ["*"] | ["RULE-ID-1", ...]}
        """
        line_map: LineMap = {}
        ignore_map: ResourceIgnoreMap = {}

        lines = content.splitlines()

        # Accumulate consecutive tmac:ignore[RULE-ID] comments above a resource block.
        # pending_ignores holds the rule IDs (or ["*"] for global) collected so far.
        pending_ignores: list[str] | None = None

        resource_re = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"')
        # Matches:  # tmac:ignore           → global
        # Matches:  # tmac:ignore[RULE-ID]  → per-rule
        ignore_re = re.compile(r"#\s*tmac:ignore(?:\[([^\]]+)\])?")

        for lineno, line in enumerate(lines, start=1):
            res_match = resource_re.match(line)
            inline_ignore = ignore_re.search(line)

            if res_match:
                res_type = res_match.group(1)
                res_name = res_match.group(2)
                line_map[(res_type, res_name)] = lineno

                # Collect ignores: inline on the resource line takes precedence,
                # then any accumulated pending_ignores from preceding lines.
                all_ignores: list[str] = []

                if inline_ignore:
                    rule_id = inline_ignore.group(1)
                    all_ignores.append("*" if rule_id is None else rule_id.strip())

                if pending_ignores:
                    for rid in pending_ignores:
                        if rid not in all_ignores:
                            all_ignores.append(rid)

                if all_ignores:
                    key = (res_type, res_name)
                    ignore_map[key] = merge_ignores(ignore_map.get(key, []), all_ignores)

                # Reset pending after consuming (whether used or not)
                pending_ignores = None

            elif inline_ignore and not res_match:
                # This is a standalone comment line — accumulate for the next resource block
                rule_id = inline_ignore.group(1)
                entry = "*" if rule_id is None else rule_id.strip()

                if pending_ignores is None:
                    pending_ignores = [entry]
                else:
                    if entry not in pending_ignores:
                        pending_ignores.append(entry)
            else:
                # Any non-ignore, non-resource line resets the pending accumulator
                # (only blank lines and comments should be between ignore and resource)
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    pending_ignores = None

        return line_map, ignore_map
