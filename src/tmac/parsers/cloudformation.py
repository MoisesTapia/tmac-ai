"""CloudFormationParser — parses AWS CloudFormation templates (YAML or JSON)."""

import json
import logging
import os
import re
from typing import Any

import yaml  # type: ignore

from tmac.models.resource import IgnoreMap, ResourceModel, is_unresolved_reference
from tmac.parsers.base import BaseParser, ParseError
from tmac.parsers.terraform import merge_ignores

logger = logging.getLogger(__name__)

# AWS caps template bodies at 1 MB; anything far larger is refused rather than loaded.
MAX_TEMPLATE_BYTES = 5 * 1024 * 1024
# Bytes read by can_parse() to decide whether a .yaml/.json file is a CFN template.
DETECTION_BYTES = 1024 * 1024
# Upper bound on values visited while normalizing (guards against YAML alias bombs).
MAX_NODES = 1_000_000

_CFN_MARKER_RE = re.compile(r"AWSTemplateFormatVersion|[\"']?Type[\"']?\s*:\s*[\"']?AWS::")
_IGNORE_RE = re.compile(r"#\s*tmac:ignore(?:\[([^\]]+)\])?")


class _CfnLoader(yaml.SafeLoader):  # type: ignore[misc]  # PyYAML ships no type stubs
    """SafeLoader that accepts CloudFormation short-form tags (!Ref, !Sub, !GetAtt, ...).

    A subclass, so the global yaml.SafeLoader is left untouched.
    """


def _construct_intrinsic(loader: _CfnLoader, tag_suffix: str, node: yaml.Node) -> dict[str, Any]:
    """`!Ref X` -> {"Ref": X}; `!Name v` -> {"Fn::Name": v} (the long form CFN itself uses)."""
    value: Any
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    return {"Ref" if tag_suffix == "Ref" else f"Fn::{tag_suffix}": value}


_CfnLoader.add_multi_constructor("!", _construct_intrinsic)
# CloudFormation treats unquoted dates as strings; keep them as str (YAML/JSON parity).
_CfnLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


class CloudFormationParser(BaseParser):
    """Parser for AWS CloudFormation templates (YAML or JSON).

    - LogicalId -> ResourceModel.name, Type -> resource_type, Properties -> attributes.
    - Intrinsic functions are normalized to single-key dicts ({"Ref": X}, {"Sub": s},
      {"GetAtt": "Res.Attr"}, ...), never resolved (see is_unresolved_reference).
    - Suppressions: `# tmac:ignore` / `# tmac:ignore[RULE-ID]` comments right above the
      LogicalId (YAML), or resource Metadata `tmac: {ignore: [...]}` (YAML and JSON).
    """

    file_patterns = ("*.yaml", "*.yml", "*.json", "*.template")

    def can_parse(self, file_path: str) -> bool:
        """Cheap content check so other YAML/JSON (k8s, CI, package.json...) is skipped."""
        try:
            with open(file_path, "rb") as f:
                head = f.read(DETECTION_BYTES)
        except OSError:
            return False
        return bool(_CFN_MARKER_RE.search(head.decode("utf-8", "ignore")))

    def parse(self, file_path: str) -> list[ResourceModel]:
        """Lenient parse: logs a warning and returns [] if the file cannot be parsed."""
        try:
            return self.parse_strict(file_path)
        except ParseError as e:
            logger.warning("%s", e)
            return []

    def parse_strict(self, file_path: str) -> list[ResourceModel]:
        try:
            if os.path.getsize(file_path) > MAX_TEMPLATE_BYTES:
                raise ParseError(
                    f"Failed to parse {file_path}: larger than {MAX_TEMPLATE_BYTES} bytes"
                )
            with open(file_path, encoding="utf-8-sig") as f:
                content = f.read()
        except (OSError, ValueError) as e:
            raise ParseError(f"Failed to parse {file_path}: {e}") from e

        is_json = content.lstrip().startswith("{")
        try:
            data = json.loads(content) if is_json else yaml.load(content, Loader=_CfnLoader)
        except (yaml.YAMLError, ValueError, RecursionError) as e:
            raise ParseError(f"Failed to parse {file_path}: {e}") from e

        if not isinstance(data, dict):
            raise ParseError(f"Failed to parse {file_path}: template is not a mapping")
        if "Resources" not in data:
            logger.warning("No 'Resources' section in %s — no resources to analyze", file_path)
            return []

        line_numbers = self._line_numbers(content, data, is_json)
        comment_ignores = {} if is_json else self._comment_ignores(content, line_numbers)
        try:
            return self._build_resources(data, file_path, line_numbers, comment_ignores)
        except RecursionError as e:
            raise ParseError(f"Failed to parse {file_path}: nesting too deep") from e

    def parse_template(self, data: dict[str, Any], source_file: str = "") -> list[ResourceModel]:
        """Build ResourceModels from an already-loaded template dict (no line numbers)."""
        return self._build_resources(data, source_file, {}, {})

    def get_ignore_map(self, file_path: str) -> IgnoreMap:
        """Suppressions per LogicalId: {LogicalId: ["*"] | ["RULE-ID-1", ...]}."""
        try:
            resources = self.parse_strict(file_path)
        except ParseError as e:
            logger.warning("Failed to read ignore map from %s: %s", file_path, e)
            return {}
        return {r.name: r.ignored_rules for r in resources if r.ignored_rules}

    # ------------------------------------------------------------------
    # Serialization (pretty printer, used for round-trip checks)
    # ------------------------------------------------------------------

    def serialize(self, resources: list[ResourceModel]) -> dict[str, Any]:
        """{"Resources": {name: {"Type": ..., "Properties": ...}}}, intrinsics in long form."""
        return {
            "Resources": {
                r.name: {"Type": r.resource_type, "Properties": _to_long_form(r.attributes)}
                for r in resources
            }
        }

    def serialize_to_yaml(self, resources: list[ResourceModel]) -> str:
        return str(yaml.safe_dump(self.serialize(resources), sort_keys=False, allow_unicode=True))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_resources(
        self,
        data: dict[str, Any],
        file_path: str,
        line_numbers: dict[str, int],
        comment_ignores: IgnoreMap,
    ) -> list[ResourceModel]:
        resources = data.get("Resources")
        if resources is None:
            return []
        if not isinstance(resources, dict):
            raise ParseError(f"Failed to parse {file_path}: 'Resources' is not a mapping")

        budget = [MAX_NODES]
        models: list[ResourceModel] = []
        for logical_id, body in resources.items():
            name = str(logical_id)
            if not isinstance(body, dict) or not isinstance(body.get("Type"), str):
                raise ParseError(f"Failed to parse {file_path}: resource {name} has no 'Type'")
            properties = body.get("Properties") or {}
            if not isinstance(properties, dict):
                raise ParseError(
                    f"Failed to parse {file_path}: 'Properties' of {name} is not a mapping"
                )
            models.append(
                ResourceModel(
                    resource_type=body["Type"],
                    name=name,
                    attributes=_normalize(properties, budget, file_path),
                    source_file=file_path,
                    line_number=line_numbers.get(name, 0),
                    ignored_rules=merge_ignores(
                        comment_ignores.get(name, []), _metadata_ignores(body)
                    ),
                )
            )
        return models

    def _line_numbers(self, content: str, data: dict[str, Any], is_json: bool) -> dict[str, int]:
        """1-indexed line of each LogicalId key under Resources."""
        resources = data.get("Resources")
        if not isinstance(resources, dict):
            return {}
        if is_json:
            start = content.find('"Resources"')
            numbers = {}
            for logical_id in resources:
                match = re.compile(rf'"{re.escape(str(logical_id))}"\s*:').search(content, start)
                if match:
                    numbers[str(logical_id)] = content.count("\n", 0, match.start()) + 1
            return numbers
        # YAML: positions come from the node tree (compose builds nodes only, no values).
        root = yaml.compose(content, Loader=_CfnLoader)
        if not isinstance(root, yaml.MappingNode):
            return {}
        for key, value in root.value:
            if key.value == "Resources" and isinstance(value, yaml.MappingNode):
                return {str(k.value): k.start_mark.line + 1 for k, _ in value.value}
        return {}

    def _comment_ignores(self, content: str, line_numbers: dict[str, int]) -> IgnoreMap:
        """tmac:ignore comments inline on, or directly above, each LogicalId line."""
        lines = content.splitlines()
        ignores: IgnoreMap = {}
        for logical_id, lineno in line_numbers.items():
            found: list[str] = []
            inline = _IGNORE_RE.search(lines[lineno - 1]) if 0 < lineno <= len(lines) else None
            if inline:
                found.append(_ignore_entry(inline))
            # Walk up through the comment/blank block preceding the key.
            i = lineno - 2
            while i >= 0 and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
                match = _IGNORE_RE.search(lines[i])
                if match:
                    found.append(_ignore_entry(match))
                i -= 1
            if found:
                ignores[logical_id] = merge_ignores([], found)
        return ignores


def _ignore_entry(match: re.Match[str]) -> str:
    rule_id = match.group(1)
    return "*" if rule_id is None else rule_id.strip()


def _metadata_ignores(body: dict[str, Any]) -> list[str]:
    """Resource-level `Metadata: {tmac: {ignore: ["*" | "RULE-ID", ...]}}`."""
    metadata = body.get("Metadata")
    tmac = metadata.get("tmac") if isinstance(metadata, dict) else None
    ignore = tmac.get("ignore") if isinstance(tmac, dict) else None
    if isinstance(ignore, str):
        ignore = [ignore]
    if not isinstance(ignore, list):
        return []
    return merge_ignores([], [str(i).strip() for i in ignore])


def _normalize(value: Any, budget: list[int], file_path: str) -> Any:
    """Normalize intrinsic functions to {"Ref": X} / {"Sub": s} / {"GetAtt": "R.A"} ..."""
    budget[0] -= 1
    if budget[0] < 0:
        raise ParseError(f"Failed to parse {file_path}: template too large after alias expansion")
    if isinstance(value, dict):
        if len(value) == 1:
            key, inner = next(iter(value.items()))
            if key == "Ref" or (isinstance(key, str) and key.startswith("Fn::")):
                name = key.removeprefix("Fn::")
                inner = _normalize(inner, budget, file_path)
                if name == "GetAtt" and isinstance(inner, list):
                    inner = ".".join(str(part) for part in inner)
                return {name: inner}
        return {str(k): _normalize(v, budget, file_path) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v, budget, file_path) for v in value]
    return value


def _to_long_form(value: Any) -> Any:
    """Inverse of _normalize for serialization: {"Sub": s} -> {"Fn::Sub": s}."""
    if is_unresolved_reference(value):
        name, inner = next(iter(value.items()))
        return {name if name == "Ref" else f"Fn::{name}": _to_long_form(inner)}
    if isinstance(value, dict):
        return {k: _to_long_form(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_long_form(v) for v in value]
    return value
