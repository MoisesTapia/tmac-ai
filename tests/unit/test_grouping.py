"""Tests for grouping resources by microservice."""

from tmac.graph.builder import GraphNode, ResourceGraph
from tmac.graph.diagrams import render_graph
from tmac.graph.grouping import SHARED_GROUP, group_by_name


def _graph():
    nodes = [
        GraphNode("aws_lambda_function", "product"),
        GraphNode("aws_dynamodb_table", "product"),
        GraphNode("aws_lambda_function", "basket"),
        GraphNode("aws_dynamodb_table", "basket"),
        GraphNode("aws_apigatewayv2_api", "main"),
    ]
    return ResourceGraph(nodes=nodes, edges=[])


def test_groups_by_name_token():
    groups = group_by_name(_graph())
    assert set(groups["product"]) == {"aws_lambda_function.product", "aws_dynamodb_table.product"}
    assert set(groups["basket"]) == {"aws_lambda_function.basket", "aws_dynamodb_table.basket"}


def test_singletons_go_to_shared():
    groups = group_by_name(_graph())
    assert "aws_apigatewayv2_api.main" in groups[SHARED_GROUP]
    assert "main" not in groups


def test_min_size_respected():
    # With min_size=3, no token forms a group → everything goes to shared
    groups = group_by_name(_graph(), min_size=3)
    assert set(groups.keys()) == {SHARED_GROUP}


def test_mermaid_renders_subgraphs():
    groups = group_by_name(_graph())
    out = render_graph(_graph(), "mermaid", groups)
    assert "subgraph" in out
    assert 'product["product"]' in out
    assert out.count("end") >= 2


def test_dot_renders_clusters():
    groups = group_by_name(_graph())
    out = render_graph(_graph(), "dot", groups)
    assert "cluster_" in out
    assert 'label="product"' in out
