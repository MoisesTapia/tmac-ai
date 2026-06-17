"""Tests for noise filtering of the architecture graph."""

from tmac.graph.builder import GraphEdge, GraphNode, ResourceGraph
from tmac.graph.filters import DEFAULT_NOISE_TYPES, filter_graph


def _graph():
    nodes = [
        GraphNode("aws_lambda_function", "app"),
        GraphNode("aws_iam_role", "app_role"),
        GraphNode("aws_iam_role_policy", "app_policy"),
        GraphNode("aws_dynamodb_table", "data"),
    ]
    edges = [
        GraphEdge("aws_lambda_function.app", "aws_iam_role.app_role", "role"),
        GraphEdge("aws_iam_role_policy.app_policy", "aws_iam_role.app_role", "role"),
        GraphEdge("aws_iam_role_policy.app_policy", "aws_dynamodb_table.data", "policy"),
        GraphEdge("aws_lambda_function.app", "aws_dynamodb_table.data", "environment"),
    ]
    return ResourceGraph(nodes=nodes, edges=edges)


def test_no_exclude_returns_same_graph():
    g = _graph()
    assert filter_graph(g, []) is g


def test_removes_excluded_node_types():
    g = filter_graph(_graph(), {"aws_iam_role", "aws_iam_role_policy"})
    types = {n.resource_type for n in g.nodes}
    assert "aws_iam_role" not in types
    assert "aws_iam_role_policy" not in types
    assert "aws_lambda_function" in types
    assert "aws_dynamodb_table" in types


def test_removes_dangling_edges():
    g = filter_graph(_graph(), {"aws_iam_role", "aws_iam_role_policy"})
    # The lambda->dynamodb edge survives; edges touching removed nodes do not
    pairs = {(e.source, e.target) for e in g.edges}
    assert ("aws_lambda_function.app", "aws_dynamodb_table.data") in pairs
    for s, t in pairs:
        assert "iam_role" not in s and "iam_role" not in t


def test_collapse_reconnects_through_removed_node():
    # A -> B(noise) -> C  should become A -> C
    nodes = [
        GraphNode("aws_a", "a"),
        GraphNode("aws_glue_thing", "b"),
        GraphNode("aws_c", "c"),
    ]
    edges = [
        GraphEdge("aws_a.a", "aws_glue_thing.b", "x"),
        GraphEdge("aws_glue_thing.b", "aws_c.c", "y"),
    ]
    g = filter_graph(ResourceGraph(nodes=nodes, edges=edges), {"aws_glue_thing"})
    pairs = {(e.source, e.target) for e in g.edges}
    assert ("aws_a.a", "aws_c.c") in pairs


def test_default_noise_types_includes_iam():
    assert "aws_iam_role_policy" in DEFAULT_NOISE_TYPES
    assert "aws_lambda_permission" in DEFAULT_NOISE_TYPES
