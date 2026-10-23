"""TfplanParser — parses tfplan.json into PlannedChange objects.

TMAC v1.1.0 "Ixtla"
Validates: Requirements 1.1–1.12, 6.5
"""

import json
import logging
from typing import Any

from tmac.delta.models import ChangeAction, PlannedChange
from tmac.models.resource import IgnoreMap, ResourceModel
from tmac.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class TfplanParser(BaseParser):
    """Parser for Terraform plan JSON files (tfplan.json).

    Implements BaseParser for ecosystem consistency.
    Primary method is parse_plan() which returns List[PlannedChange].
    The parse() method returns List[ResourceModel] built from 'after' attributes
    for BaseParser compatibility.
    """

    # ------------------------------------------------------------------
    # BaseParser interface
    # ------------------------------------------------------------------

    def parse(self, file_path: str) -> list[ResourceModel]:
        """Implements BaseParser. Returns ResourceModels built from 'after' attributes."""
        changes = self.parse_plan(file_path)
        resources: list[ResourceModel] = []
        for change in changes:
            if change.after is not None:
                resources.append(
                    ResourceModel(
                        resource_type=change.resource_type,
                        name=change.resource_name,
                        attributes=change.after,
                        source_file=file_path,
                        line_number=0,
                    )
                )
        return resources

    # ------------------------------------------------------------------
    # Primary method
    # ------------------------------------------------------------------

    def parse_plan(self, file_path: str) -> list[PlannedChange]:
        """Parse a tfplan.json and return a list of PlannedChange objects.

        Returns an empty list (with a warning) if the file does not exist,
        is not valid JSON, or lacks the 'resource_changes' field.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            logger.warning("Plan file not found: %s", file_path)
            return []
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse JSON in %s: %s", file_path, exc)
            return []
        except (OSError, ValueError) as exc:
            logger.warning("Failed to read plan file %s: %s", file_path, exc)
            return []

        if not isinstance(data, dict) or "resource_changes" not in data:
            logger.warning("No 'resource_changes' field in %s — returning empty result", file_path)
            return []

        changes: list[PlannedChange] = []
        counts: dict[str, int] = {"create": 0, "update": 0, "delete": 0, "replace": 0}

        for rc in data["resource_changes"]:
            address = rc.get("address", "")
            change_block = rc.get("change", {})
            actions = change_block.get("actions", [])

            action = self._map_action(actions)
            if action is None:
                continue  # no-op or unknown — skip

            resource_type, resource_name = self._extract_resource_type_and_name(address)

            raw_before = change_block.get("before")
            raw_after = change_block.get("after")

            # Enforce before/after semantics per action
            if action == ChangeAction.create:
                before: dict[str, Any] | None = None
                after: dict[str, Any] | None = raw_after if isinstance(raw_after, dict) else {}
            elif action == ChangeAction.delete:
                before = raw_before if isinstance(raw_before, dict) else {}
                after = None
            else:  # update or replace
                before = raw_before if isinstance(raw_before, dict) else {}
                after = raw_after if isinstance(raw_after, dict) else {}

            changes.append(
                PlannedChange(
                    address=address,
                    resource_type=resource_type,
                    resource_name=resource_name,
                    action=action,
                    before=before,
                    after=after,
                )
            )
            counts[action.value] += 1

        logger.debug(
            "Parsed %d planned changes from %s (create=%d, update=%d, delete=%d, replace=%d)",
            len(changes),
            file_path,
            counts["create"],
            counts["update"],
            counts["delete"],
            counts["replace"],
        )
        return changes

    # ------------------------------------------------------------------
    # ignore_map extraction
    # ------------------------------------------------------------------

    def _prescan(self, file_path: str) -> IgnoreMap:
        """Build an ignore_map from the resource addresses in the plan.

        For tfplan.json the ignore mechanism is address-based (not HCL comments).
        Returns a dict mapping resource address → ["*"] for global suppression.

        In v1.1.0 the ignore_map is populated by the DeltaScanner caller; this
        method provides the address list so callers can build their own maps.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to read ignore map from %s: %s", file_path, exc)
            return {}

        ignore_map: IgnoreMap = {}
        for rc in data.get("resource_changes", []):
            address = rc.get("address", "")
            if address:
                # Default: no ignores — callers add entries as needed
                ignore_map.setdefault(address, [])
        return ignore_map

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_resource_type_and_name(self, address: str) -> tuple[str, str]:
        """Extract resource_type and resource_name from a tfplan address.

        Simple:  'aws_s3_bucket.data'              → ('aws_s3_bucket', 'data')
        Module:  'module.vpc.aws_subnet.private'   → ('aws_subnet', 'private')
        """
        parts = address.split(".")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
        # Fallback for malformed addresses
        return address, address

    def _map_action(self, actions: list[str]) -> ChangeAction | None:
        """Map a tfplan actions list to a ChangeAction enum value.

        ['create']          → ChangeAction.create
        ['delete']          → ChangeAction.delete
        ['update']          → ChangeAction.update
        ['delete', 'create'] → ChangeAction.replace
        ['no-op']           → None  (caller should skip)
        unknown             → None  + logger.warning
        """
        if actions == ["create"]:
            return ChangeAction.create
        if actions == ["delete"]:
            return ChangeAction.delete
        if actions == ["update"]:
            return ChangeAction.update
        if set(actions) == {"delete", "create"}:
            return ChangeAction.replace
        if actions == ["no-op"]:
            return None
        logger.warning("Unknown action list %s — skipping resource", actions)
        return None
