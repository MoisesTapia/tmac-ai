"""Renderers for the ResourceGraph to different diagram formats.

Supported formats:
- mermaid: Mermaid text (graph TD), native rendering in GitHub/GitLab/Markdown.
- dot:     Graphviz DOT format (text), convertible to SVG/PNG with `dot`.
- drawio:  mxGraphModel XML, editable in draw.io / diagrams.net.
"""

import html
import re
import shutil
import subprocess

from tmac.graph.builder import GraphNode, ResourceGraph


def _sanitize_id(node_id: str) -> str:
    """Convert 'aws_vpc.main' into an id that is safe for Mermaid/DOT."""
    return re.sub(r"[^A-Za-z0-9_]", "_", node_id)


def _short_label(node_id: str) -> str:
    """Readable label: 'aws_vpc.main' → 'aws_vpc\\nmain'."""
    if "." in node_id:
        rtype, name = node_id.split(".", 1)
        return f"{rtype}\\n{name}"
    return node_id


Groups = dict[str, list[str]] | None


class MermaidRenderer:
    """Renders the graph as a Mermaid diagram (flowchart)."""

    def render(self, graph: ResourceGraph, groups: Groups = None) -> str:
        lines: list[str] = ["graph TD"]

        if groups:
            grouped_ids = {nid for ids in groups.values() for nid in ids}
            for label, node_ids in groups.items():
                lines.append(f'    subgraph {_sanitize_id(label)}["{label}"]')
                for nid in sorted(node_ids):
                    node = next((n for n in graph.nodes if n.id == nid), None)
                    if node is None:
                        continue
                    lines.append(
                        f'        {_sanitize_id(nid)}["{node.resource_type}<br/>{node.name}"]'
                    )
                lines.append("    end")
            # Nodes without a group (just in case)
            for node in sorted(graph.nodes, key=lambda n: n.id):
                if node.id not in grouped_ids:
                    lines.append(
                        f'    {_sanitize_id(node.id)}["{node.resource_type}<br/>{node.name}"]'
                    )
        else:
            for node in sorted(graph.nodes, key=lambda n: n.id):
                nid = _sanitize_id(node.id)
                lines.append(f'    {nid}["{node.resource_type}<br/>{node.name}"]')

        for edge in graph.edges:
            src = _sanitize_id(edge.source)
            tgt = _sanitize_id(edge.target)
            if edge.attribute:
                lines.append(f"    {src} -->|{edge.attribute}| {tgt}")
            else:
                lines.append(f"    {src} --> {tgt}")

        return "\n".join(lines) + "\n"


class DotRenderer:
    """Renders the graph as Graphviz DOT."""

    def render(self, graph: ResourceGraph, groups: Groups = None) -> str:
        lines: list[str] = [
            "digraph tmac_architecture {",
            "    rankdir=LR;",
            '    node [shape=box, style="rounded,filled", fillcolor="#e8f0fe", fontname="Helvetica"];',
            '    edge [fontname="Helvetica", fontsize=10, color="#5f6368"];',
        ]

        def node_stmt(node: GraphNode) -> str:
            return f'{_sanitize_id(node.id)} [label="{node.resource_type}\\n{node.name}"];'

        if groups:
            grouped_ids = {nid for ids in groups.values() for nid in ids}
            for idx, (label, node_ids) in enumerate(groups.items()):
                lines.append(f"    subgraph cluster_{idx} {{")
                lines.append(f'        label="{label}";')
                lines.append('        style="rounded";')
                lines.append('        color="#9aa0a6";')
                for nid in sorted(node_ids):
                    node = next((n for n in graph.nodes if n.id == nid), None)
                    if node is not None:
                        lines.append(f"        {node_stmt(node)}")
                lines.append("    }")
            for node in sorted(graph.nodes, key=lambda n: n.id):
                if node.id not in grouped_ids:
                    lines.append(f"    {node_stmt(node)}")
        else:
            for node in sorted(graph.nodes, key=lambda n: n.id):
                lines.append(f"    {node_stmt(node)}")

        for edge in graph.edges:
            src = _sanitize_id(edge.source)
            tgt = _sanitize_id(edge.target)
            attr = f' [label="{edge.attribute}"]' if edge.attribute else ""
            lines.append(f"    {src} -> {tgt}{attr};")

        lines.append("}")
        return "\n".join(lines) + "\n"


class DrawioRenderer:
    """Renders the graph as mxGraphModel XML (draw.io / diagrams.net)."""

    def render(self, graph: ResourceGraph, groups: Groups = None) -> str:
        cells: list[str] = []
        node_cell_ids: dict[str, str] = {}

        # Simple grid layout
        cols = max(1, int(len(graph.nodes) ** 0.5))
        x_step, y_step = 200, 120
        cell_counter = 2  # 0 and 1 are reserved by draw.io

        for idx, node in enumerate(sorted(graph.nodes, key=lambda n: n.id)):
            cell_id = str(cell_counter)
            node_cell_ids[node.id] = cell_id
            cell_counter += 1
            col, row = idx % cols, idx // cols
            x, y = col * x_step, row * y_step
            label = html.escape(f"{node.resource_type}\n{node.name}")
            cells.append(
                f'        <mxCell id="{cell_id}" value="{label}" '
                f'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" '
                f'vertex="1" parent="1">\n'
                f'          <mxGeometry x="{x}" y="{y}" width="160" height="60" as="geometry"/>\n'
                f"        </mxCell>"
            )

        for edge in graph.edges:
            src_cell = node_cell_ids.get(edge.source)
            tgt_cell = node_cell_ids.get(edge.target)
            if not src_cell or not tgt_cell:
                continue
            cell_id = str(cell_counter)
            cell_counter += 1
            label = html.escape(edge.attribute)
            cells.append(
                f'        <mxCell id="{cell_id}" value="{label}" '
                f'style="endArrow=classic;html=1;" edge="1" parent="1" '
                f'source="{src_cell}" target="{tgt_cell}">\n'
                f'          <mxGeometry relative="1" as="geometry"/>\n'
                f"        </mxCell>"
            )

        body = "\n".join(cells)
        return (
            '<mxfile host="tmac">\n'
            '  <diagram name="TMAC Architecture">\n'
            '    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" '
            'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            'pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">\n'
            "      <root>\n"
            '        <mxCell id="0"/>\n'
            '        <mxCell id="1" parent="0"/>\n'
            f"{body}\n"
            "      </root>\n"
            "    </mxGraphModel>\n"
            "  </diagram>\n"
            "</mxfile>\n"
        )


_RENDERERS: dict[str, type[MermaidRenderer | DotRenderer | DrawioRenderer]] = {
    "mermaid": MermaidRenderer,
    "dot": DotRenderer,
    "drawio": DrawioRenderer,
}

# Image formats that require Graphviz (`dot`) installed on the system.
IMAGE_FORMATS = {"png", "svg", "pdf"}


def render_graph(graph: ResourceGraph, fmt: str, groups: Groups = None) -> str:
    """Render the graph in the given format."""
    fmt = fmt.lower()
    renderer_cls = _RENDERERS.get(fmt)
    if renderer_cls is None:
        raise ValueError(f"Unsupported diagram format: {fmt}. Use: {', '.join(_RENDERERS)}")
    return renderer_cls().render(graph, groups)


def graphviz_available() -> bool:
    """True if the Graphviz `dot` binary is available on the PATH."""
    return shutil.which("dot") is not None


def render_image(
    graph: ResourceGraph, output_path: str, image_format: str, groups: Groups = None
) -> None:
    """Render the graph to an image (png/svg/pdf) using Graphviz.

    Requires the `dot` binary installed. Raises RuntimeError if it is not available.
    """
    image_format = image_format.lower()
    if image_format not in IMAGE_FORMATS:
        raise ValueError(
            f"Unsupported image format: {image_format}. Use: {', '.join(IMAGE_FORMATS)}"
        )
    if not graphviz_available():
        raise RuntimeError(
            "Graphviz is not installed (`dot` binary not found). "
            "Install it with `brew install graphviz` (macOS) or `apt-get install graphviz` (Linux), "
            "or generate the diagram in mermaid/dot/drawio format."
        )

    dot_source = DotRenderer().render(graph, groups)
    try:
        subprocess.run(
            ["dot", f"-T{image_format}", "-o", output_path],
            input=dot_source.encode("utf-8"),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise RuntimeError(f"Graphviz failed to render the image: {stderr}") from exc
