"""Tests for the dependency graph and the diagram renderers."""

import xml.etree.ElementTree as ET

import pytest

from tmac.graph.builder import GraphBuilder
from tmac.graph.diagrams import render_graph
from tmac.models.resource import ResourceModel


def _resources():
    return [
        ResourceModel(
            resource_type="aws_vpc",
            name="main",
            attributes={"cidr_block": '"10.0.0.0/16"'},
            source_file="main.tf",
            line_number=1,
        ),
        ResourceModel(
            resource_type="aws_subnet",
            name="web",
            attributes={"vpc_id": "${aws_vpc.main.id}"},
            source_file="main.tf",
            line_number=5,
        ),
        ResourceModel(
            resource_type="aws_instance",
            name="app",
            attributes={
                "subnet_id": "${aws_subnet.web.id}",
                "vpc_security_group_ids": ["${aws_security_group.sg.id}"],
            },
            source_file="main.tf",
            line_number=10,
        ),
    ]


def test_build_creates_node_per_resource():
    graph = GraphBuilder().build(_resources())
    assert len(graph.nodes) == 3
    assert "aws_vpc.main" in graph.node_ids()


def test_build_extracts_edges_from_references():
    graph = GraphBuilder().build(_resources())
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("aws_subnet.web", "aws_vpc.main") in edges
    assert ("aws_instance.app", "aws_subnet.web") in edges


def test_edges_only_to_existing_nodes():
    # aws_security_group.sg does not exist as a node → it must not generate an edge
    graph = GraphBuilder().build(_resources())
    targets = {e.target for e in graph.edges}
    assert "aws_security_group.sg" not in targets


def test_ignores_var_and_local_references():
    resources = [
        ResourceModel(
            resource_type="aws_instance",
            name="app",
            attributes={"ami": "${var.ami_id}", "type": "${local.size}"},
            source_file="main.tf",
            line_number=1,
        )
    ]
    graph = GraphBuilder().build(resources)
    assert len(graph.edges) == 0


def test_mermaid_render_contains_nodes_and_edges():
    graph = GraphBuilder().build(_resources())
    out = render_graph(graph, "mermaid")
    assert out.startswith("graph TD")
    assert "aws_vpc_main" in out
    assert "-->" in out


def test_dot_render_is_valid_digraph():
    graph = GraphBuilder().build(_resources())
    out = render_graph(graph, "dot")
    assert out.startswith("digraph")
    assert "->" in out
    assert out.rstrip().endswith("}")


def test_drawio_render_is_valid_xml():
    graph = GraphBuilder().build(_resources())
    out = render_graph(graph, "drawio")
    root = ET.fromstring(out)
    assert root.tag == "mxfile"


def test_unsupported_format_raises():
    graph = GraphBuilder().build(_resources())
    with pytest.raises(ValueError):
        render_graph(graph, "svg")


def test_image_formats_constant():
    from tmac.graph.diagrams import IMAGE_FORMATS

    assert {"png", "svg", "pdf"} == IMAGE_FORMATS


def test_render_image_raises_when_graphviz_missing(monkeypatch):
    from tmac.graph import diagrams

    monkeypatch.setattr(diagrams, "graphviz_available", lambda: False)
    graph = GraphBuilder().build(_resources())
    with pytest.raises(RuntimeError):
        diagrams.render_image(graph, "out.png", "png")


def test_render_image_rejects_bad_format():
    from tmac.graph import diagrams

    graph = GraphBuilder().build(_resources())
    with pytest.raises(ValueError):
        diagrams.render_image(graph, "out.gif", "gif")
