"""Grouping of resources into clusters (microservices) for the diagram.

Generic heuristic: most Terraform repos name the resources of the same
microservice with a common token (``product``, ``basket``, ``order``).
This module groups nodes by the leading token of their name when that token
appears in 2+ resources; the rest is left as shared infrastructure.
"""

from collections import defaultdict
from typing import Dict, List

from tmac.graph.builder import ResourceGraph

SHARED_GROUP = "shared"


def _leading_token(name: str) -> str:
    """Leading token separated by underscore: 'order_queue' → 'order'."""
    return name.split("_", 1)[0]


def group_by_name(graph: ResourceGraph, min_size: int = 2) -> Dict[str, List[str]]:
    """Group node ids by name token.

    Args:
        graph: graph to group.
        min_size: minimum number of resources to consider a token as a group.

    Returns:
        Map ``group_label -> [node_id, ...]``. Resources whose token does not
        form a group are placed under ``SHARED_GROUP``.
    """
    token_to_nodes: Dict[str, List[str]] = defaultdict(list)
    for node in graph.nodes:
        token_to_nodes[_leading_token(node.name)].append(node.id)

    groups: Dict[str, List[str]] = {}
    shared: List[str] = []
    for token, node_ids in token_to_nodes.items():
        if len(node_ids) >= min_size:
            groups[token] = sorted(node_ids)
        else:
            shared.extend(node_ids)

    if shared:
        groups[SHARED_GROUP] = sorted(shared)
    return groups
