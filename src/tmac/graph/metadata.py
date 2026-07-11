"""Extraction of per-resource configuration metadata for threat modeling.

Each ResourceModel already contains the complete dictionary of attributes as
they were declared in the `.tf`. This module classifies those attributes into:

- connections: attributes whose value references another resource (graph edges).
- config:      scalar configuration attributes (cidr_block, engine, etc.).
- blocks:      nested blocks (ingress, egress, ebs_block_device, ...).

Additionally, an optional curated layer (security_attrs) allows highlighting
attributes relevant to security per resource type and detecting absences.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from tmac.graph.builder import _NON_RESOURCE_PREFIXES, _REFERENCE_RE
from tmac.models.resource import ResourceModel

logger = logging.getLogger(__name__)

# Defaults used if the external YAML is unavailable or invalid.
_DEFAULT_SECURITY_ATTRS: Dict[str, List[str]] = {
    "aws_s3_bucket": ["acl", "versioning", "server_side_encryption_configuration"],
    "aws_db_instance": ["storage_encrypted", "publicly_accessible", "kms_key_id", "iam_database_authentication_enabled"],
    "aws_instance": ["associate_public_ip_address", "metadata_options", "ebs_optimized"],
    "aws_security_group": ["ingress", "egress"],
    "aws_vpc": ["cidr_block", "enable_dns_support"],
    "aws_subnet": ["map_public_ip_on_launch", "cidr_block"],
    "aws_ebs_volume": ["encrypted", "kms_key_id"],
    "aws_efs_file_system": ["encrypted", "kms_key_id"],
    "aws_sqs_queue": ["kms_master_key_id"],
    "aws_sns_topic": ["kms_master_key_id"],
}

_DEFAULT_SATELLITES: Dict[str, str] = {
    "aws_flow_log": "VPC Flow Logs",
    "aws_s3_bucket_server_side_encryption_configuration": "S3 Encryption",
    "aws_s3_bucket_logging": "S3 Access Logging",
    "aws_s3_bucket_versioning": "S3 Versioning",
    "aws_s3_bucket_public_access_block": "S3 Public Access Block",
    "aws_cloudtrail": "CloudTrail Logging",
}

# Path to the curated YAML, editable without touching code.
_SECURITY_ATTRS_YAML = Path(__file__).parent.parent / "rules" / "aws" / "security_attrs.yaml"


def _load_security_config() -> tuple[Dict[str, List[str]], Dict[str, str]]:
    """Load security_attrs and satellites from the external YAML, with fallback."""
    try:
        with open(_SECURITY_ATTRS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        sec = data.get("security_attrs") or {}
        sat = data.get("satellites") or {}
        if not isinstance(sec, dict) or not isinstance(sat, dict):
            raise ValueError("invalid format in security_attrs.yaml")
        return sec, sat
    except (OSError, ValueError, yaml.YAMLError) as exc:
        logger.warning("Could not load %s (%s); using defaults.", _SECURITY_ATTRS_YAML, exc)
        return dict(_DEFAULT_SECURITY_ATTRS), dict(_DEFAULT_SATELLITES)


# Attributes relevant to security per resource type (curated layer, editable).
# "Satellite" resources that contribute security configuration to another resource.
SECURITY_ATTRS, SATELLITE_RESOURCES = _load_security_config()


def _is_reference(value: Any) -> bool:
    """True if the value contains a reference to another Terraform resource."""
    if isinstance(value, str):
        for m in _REFERENCE_RE.finditer(value):
            if m.group(1) not in _NON_RESOURCE_PREFIXES:
                return True
    elif isinstance(value, (list, tuple)):
        return any(_is_reference(v) for v in value)
    return False


@dataclass
class ResourceMetadata:
    """Configuration metadata of a resource."""

    resource_type: str
    name: str
    source_file: str
    line_number: int
    config: Dict[str, Any] = field(default_factory=dict)
    connections: Dict[str, Any] = field(default_factory=dict)
    blocks: Dict[str, Any] = field(default_factory=dict)
    security_attrs: Dict[str, Any] = field(default_factory=dict)
    enrichments: List[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.resource_type}.{self.name}"


class MetadataExtractor:
    """Extracts ResourceMetadata from a list of ResourceModel."""

    def extract(self, resources: List[ResourceModel]) -> List[ResourceMetadata]:
        # Maps satellite resources to the target resources they enrich.
        enrichment_map: Dict[str, List[str]] = {}
        for res in resources:
            label = SATELLITE_RESOURCES.get(res.resource_type)
            if not label:
                continue
            for target_id in self._referenced_ids(res.attributes):
                enrichment_map.setdefault(target_id, []).append(label)

        metadata: List[ResourceMetadata] = []
        for res in resources:
            config: Dict[str, Any] = {}
            connections: Dict[str, Any] = {}
            blocks: Dict[str, Any] = {}

            for attr, value in res.attributes.items():
                if attr == "__is_block__":
                    continue
                if self._is_block(value):
                    blocks[attr] = value
                elif _is_reference(value):
                    connections[attr] = value
                else:
                    config[attr] = value

            sec_keys = SECURITY_ATTRS.get(res.resource_type, [])
            security_attrs = {
                k: res.attributes.get(k, "<not defined>") for k in sec_keys
            }

            metadata.append(
                ResourceMetadata(
                    resource_type=res.resource_type,
                    name=res.name,
                    source_file=res.source_file,
                    line_number=res.line_number,
                    config=config,
                    connections=connections,
                    blocks=blocks,
                    security_attrs=security_attrs,
                    enrichments=enrichment_map.get(f"{res.resource_type}.{res.name}", []),
                )
            )
        return metadata

    def _is_block(self, value: Any) -> bool:
        """A nested block is a list of dicts or a dict (not a reference)."""
        if isinstance(value, dict):
            return True
        if isinstance(value, (list, tuple)):
            return any(isinstance(v, dict) for v in value)
        return False

    def _referenced_ids(self, attributes: Dict[str, Any]) -> List[str]:
        ids: List[str] = []
        self._collect(attributes, ids)
        return ids

    def _collect(self, value: Any, acc: List[str]) -> None:
        if isinstance(value, str):
            for m in _REFERENCE_RE.finditer(value):
                if m.group(1) not in _NON_RESOURCE_PREFIXES:
                    acc.append(f"{m.group(1)}.{m.group(2)}")
        elif isinstance(value, dict):
            for v in value.values():
                self._collect(v, acc)
        elif isinstance(value, (list, tuple)):
            for v in value:
                self._collect(v, acc)


def _fmt_value(value: Any) -> str:
    """Format a value for a Markdown table cell."""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    text = text.replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= 120 else text[:117] + "..."


def render_metadata_markdown(metadata: List[ResourceMetadata]) -> str:
    """Render the metadata as a readable Markdown document."""
    lines: List[str] = [
        "# TMAC — Resource Configuration Metadata",
        "",
        f"Total resources analyzed: **{len(metadata)}**",
        "",
        "This document details the configuration of each resource to support "
        "threat modeling.",
        "",
    ]

    for md in sorted(metadata, key=lambda m: m.id):
        lines.append(f"## `{md.id}`")
        lines.append("")
        lines.append(f"- File: `{md.source_file}` (line {md.line_number})")
        if md.enrichments:
            lines.append(f"- Related configuration: {', '.join(md.enrichments)}")
        lines.append("")

        if md.security_attrs:
            lines.append("### Attributes relevant to security")
            lines.append("")
            lines.append("| Attribute | Value |")
            lines.append("| :--- | :--- |")
            for k, v in md.security_attrs.items():
                lines.append(f"| `{k}` | {_fmt_value(v)} |")
            lines.append("")

        if md.config:
            lines.append("### Configuration")
            lines.append("")
            lines.append("| Attribute | Value |")
            lines.append("| :--- | :--- |")
            for k, v in sorted(md.config.items()):
                lines.append(f"| `{k}` | {_fmt_value(v)} |")
            lines.append("")

        if md.connections:
            lines.append("### Connections (references to other resources)")
            lines.append("")
            lines.append("| Attribute | Reference |")
            lines.append("| :--- | :--- |")
            for k, v in sorted(md.connections.items()):
                lines.append(f"| `{k}` | {_fmt_value(v)} |")
            lines.append("")

        if md.blocks:
            lines.append("### Nested blocks")
            lines.append("")
            for k, v in sorted(md.blocks.items()):
                lines.append(f"- `{k}`: {_fmt_value(v)}")
            lines.append("")

    return "\n".join(lines) + "\n"


def render_metadata_json(metadata: List[ResourceMetadata]) -> str:
    """Render the metadata as JSON (consumable by agents/threat modelers)."""
    payload = {
        "tool": "TMAC",
        "document": "resource-metadata",
        "total_resources": len(metadata),
        "resources": [
            {
                "id": m.id,
                "resource_type": m.resource_type,
                "name": m.name,
                "source_file": m.source_file,
                "line_number": m.line_number,
                "config": m.config,
                "connections": m.connections,
                "blocks": m.blocks,
                "security_attrs": m.security_attrs,
                "enrichments": m.enrichments,
            }
            for m in sorted(metadata, key=lambda m: m.id)
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_metadata(metadata: List[ResourceMetadata], fmt: str = "md") -> str:
    fmt = fmt.lower()
    if fmt in ("md", "markdown"):
        return render_metadata_markdown(metadata)
    if fmt == "json":
        return render_metadata_json(metadata)
    raise ValueError(f"Unsupported metadata format: {fmt}. Use: md, json")
