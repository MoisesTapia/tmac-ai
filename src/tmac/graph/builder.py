"""Builds a directed dependency graph from ResourceModel.

The HCL parser preserves references between resources as interpolation
strings, for example ``"${aws_vpc.main.id}"``. This module walks the
attributes of each resource, extracts those references and builds a directed
graph where each edge represents "resource A references resource B".
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from tmac.models.resource import ResourceModel

# Captures references such as: aws_vpc.main  /  aws_subnet.web.id
# Group 1 = resource_type, Group 2 = resource_name
# The Terraform resource type always contains an underscore (provider_resource),
# which avoids false positives like "t3.micro" or "10.0".
_REFERENCE_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\.([A-Za-z_][A-Za-z0-9_-]*)")

# Prefixes that are not referenceable resources (variables, locals, data, etc.)
_NON_RESOURCE_PREFIXES = {"var", "local", "module", "data", "each", "count", "self", "path", "terraform"}


@dataclass(frozen=True)
class GraphNode:
    """A resource in the architecture graph."""

    resource_type: str
    name: str
    source_file: str = ""
    line_number: int = 0

    @property
    def id(self) -> str:
        return f"{self.resource_type}.{self.name}"


@dataclass(frozen=True)
class GraphEdge:
    """A directed dependency: source references target."""

    source: str
    target: str
    attribute: str = ""


@dataclass
class ResourceGraph:
    """Directed graph of resources and their dependencies."""

    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

    def node_ids(self) -> Set[str]:
        return {n.id for n in self.nodes}


class GraphBuilder:
    """Builds a ResourceGraph from a list of ResourceModel."""

    def build(self, resources: List[ResourceModel]) -> ResourceGraph:
        nodes = [
            GraphNode(
                resource_type=r.resource_type,
                name=r.name,
                source_file=r.source_file,
                line_number=r.line_number,
            )
            for r in resources
        ]
        valid_ids = {n.id for n in nodes}

        edges: List[GraphEdge] = []
        seen: Set[Tuple[str, str, str]] = set()

        for resource in resources:
            source_id = f"{resource.resource_type}.{resource.name}"
            for attr_name, value in resource.attributes.items():
                for ref_id in self._extract_references(value):
                    # Only create edges toward resources that exist in the graph
                    if ref_id in valid_ids and ref_id != source_id:
                        key = (source_id, ref_id, attr_name)
                        if key not in seen:
                            seen.add(key)
                            edges.append(GraphEdge(source=source_id, target=ref_id, attribute=attr_name))

        return ResourceGraph(nodes=nodes, edges=edges)

    def _extract_references(self, value: Any) -> Set[str]:
        """Recursively extract ``type.name`` references from an attribute value."""
        refs: Set[str] = set()
        if isinstance(value, str):
            for match in _REFERENCE_RE.finditer(value):
                res_type, res_name = match.group(1), match.group(2)
                if res_type in _NON_RESOURCE_PREFIXES:
                    continue
                refs.add(f"{res_type}.{res_name}")
        elif isinstance(value, dict):
            for v in value.values():
                refs |= self._extract_references(v)
        elif isinstance(value, (list, tuple)):
            for item in value:
                refs |= self._extract_references(item)
        return refs
