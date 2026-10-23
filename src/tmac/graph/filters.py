"""Noise filtering in the architecture graph.

A Terraform repo contains many "plumbing" resources (IAM roles, policies,
Lambda permissions, API Gateway stages, queue policies) that are necessary to
deploy but that clutter an architecture diagram. This module allows hiding
them while preserving the real connectivity between the important resources.

When a node is removed, each predecessor is reconnected to each successor
(pass-through), so that ``A -> noise -> B`` becomes ``A -> B``.
"""

from collections.abc import Iterable

from tmac.graph.builder import GraphEdge, GraphNode, ResourceGraph

# Resource types considered "noise" for an architecture diagram.
# These are security/permission/wiring resources that do not contribute to the
# view of components and flows. Editable as needed.
DEFAULT_NOISE_TYPES: set[str] = {
    "aws_iam_role",
    "aws_iam_role_policy",
    "aws_iam_policy",
    "aws_iam_role_policy_attachment",
    "aws_iam_policy_attachment",
    "aws_lambda_permission",
    "aws_sqs_queue_policy",
    "aws_s3_bucket_policy",
    "aws_sns_topic_policy",
    "aws_apigatewayv2_stage",
    "aws_api_gateway_deployment",
    "aws_api_gateway_method_settings",
}


def filter_graph(
    graph: ResourceGraph,
    exclude_types: Iterable[str],
    collapse: bool = True,
) -> ResourceGraph:
    """Return a new graph without the nodes whose type is in ``exclude_types``.

    Args:
        graph: original graph.
        exclude_types: resource types to hide.
        collapse: if True, reconnect predecessors with successors of each
            removed node to preserve transitive connectivity.
    """
    exclude = set(exclude_types)
    if not exclude:
        return graph

    removed_ids = {n.id for n in graph.nodes if n.resource_type in exclude}
    kept_nodes: list[GraphNode] = [n for n in graph.nodes if n.resource_type not in exclude]

    edges: list[GraphEdge] = list(graph.edges)

    if collapse:
        edges = _collapse_nodes(edges, removed_ids)

    kept_ids = {n.id for n in kept_nodes}
    final_edges: list[GraphEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for e in edges:
        if e.source in kept_ids and e.target in kept_ids and e.source != e.target:
            key = (e.source, e.target, e.attribute)
            if key not in seen:
                seen.add(key)
                final_edges.append(e)

    return ResourceGraph(nodes=kept_nodes, edges=final_edges)


def _collapse_nodes(edges: list[GraphEdge], removed_ids: set[str]) -> list[GraphEdge]:
    """Reconnect predecessors with successors for each removed node."""
    result = list(edges)
    for node_id in removed_ids:
        incoming = [e for e in result if e.target == node_id]
        outgoing = [e for e in result if e.source == node_id]
        bridged: list[GraphEdge] = []
        for inc in incoming:
            for out in outgoing:
                if inc.source != out.target:
                    label = out.attribute or inc.attribute
                    bridged.append(GraphEdge(source=inc.source, target=out.target, attribute=label))
        # Remove the edges that touch the removed node and add the bridge edges
        result = [e for e in result if e.source != node_id and e.target != node_id]
        result.extend(bridged)
    return result
