import hcl2
import logging
import re
from io import StringIO
from typing import Dict, List, Optional, Tuple
from tmac.parsers.base import BaseParser
from tmac.models.resource import ResourceModel

logger = logging.getLogger(__name__)

# IgnoreMap: resource_name → ["*"] (global ignore) or ["RULE-ID-1", ...] (per-rule)
IgnoreMap = Dict[str, List[str]]


class TerraformParser(BaseParser):
    """Parser for Terraform HCL format (.tf files)."""

    def parse(self, file_path: str) -> List[ResourceModel]:
        resources: List[ResourceModel] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            line_map, ignore_map = self._prescan(content)

            parsed = hcl2.load(StringIO(content))  # type: ignore

            if "resource" in parsed:
                for block in parsed["resource"]:
                    for res_type, res_dict in block.items():
                        for res_name, res_attrs in res_dict.items():
                            line_number = line_map.get((res_type, res_name), 0)
                            resources.append(
                                ResourceModel(
                                    resource_type=res_type,
                                    name=res_name,
                                    attributes=res_attrs,
                                    source_file=file_path,
                                    line_number=line_number,
                                )
                            )
            return resources
        except Exception as e:
            logger.warning("Failed to parse %s: %s", file_path, e)
            return []

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

    def _prescan(self, content: str) -> Tuple[Dict[Tuple[str, str], int], IgnoreMap]:
        """
        Single-pass pre-scan of raw .tf content.

        Returns:
            line_map:   {(resource_type, resource_name): line_number}  (1-indexed)
            ignore_map: {resource_name: ["*"] | ["RULE-ID-1", ...]}
        """
        line_map: Dict[Tuple[str, str], int] = {}
        ignore_map: IgnoreMap = {}

        lines = content.splitlines()

        # Accumulate consecutive tmac:ignore[RULE-ID] comments above a resource block.
        # pending_ignores holds the rule IDs (or ["*"] for global) collected so far.
        pending_ignores: Optional[List[str]] = None

        resource_re = re.compile(
            r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"'
        )
        # Matches:  # tmac:ignore           → global
        # Matches:  # tmac:ignore[RULE-ID]  → per-rule
        ignore_re = re.compile(
            r"#\s*tmac:ignore(?:\[([^\]]+)\])?"
        )

        for lineno, line in enumerate(lines, start=1):
            res_match = resource_re.match(line)
            inline_ignore = ignore_re.search(line)

            if res_match:
                res_type = res_match.group(1)
                res_name = res_match.group(2)
                line_map[(res_type, res_name)] = lineno

                # Collect ignores: inline on the resource line takes precedence,
                # then any accumulated pending_ignores from preceding lines.
                all_ignores: List[str] = []

                if inline_ignore:
                    rule_id = inline_ignore.group(1)
                    all_ignores.append("*" if rule_id is None else rule_id.strip())

                if pending_ignores:
                    for rid in pending_ignores:
                        if rid not in all_ignores:
                            all_ignores.append(rid)

                if all_ignores:
                    existing = ignore_map.get(res_name, [])
                    # Merge: if any entry is "*", collapse to global
                    merged = list(existing)
                    for rid in all_ignores:
                        if rid not in merged:
                            merged.append(rid)
                    if "*" in merged:
                        ignore_map[res_name] = ["*"]
                    else:
                        ignore_map[res_name] = merged

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
