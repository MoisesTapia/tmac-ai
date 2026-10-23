"""Service for generating architecture diagrams from Terraform code."""

import logging
from pathlib import Path

from tmac.graph.builder import GraphBuilder, ResourceGraph
from tmac.graph.diagrams import render_graph
from tmac.graph.filters import DEFAULT_NOISE_TYPES, filter_graph
from tmac.graph.metadata import MetadataExtractor, ResourceMetadata
from tmac.models.resource import ResourceModel
from tmac.parsers.terraform import TerraformParser
from tmac.scanner import discover_files

logger = logging.getLogger(__name__)


class DiagramError(Exception):
    """Raised when the diagram cannot be generated."""


class DiagramService:
    """Reads a Terraform repo, builds the graph and renders it."""

    def parse_resources(
        self,
        directory: str,
        exclude_patterns: list[str] | None = None,
    ) -> list[ResourceModel]:
        scan_path = Path(directory)
        if not scan_path.exists() or not scan_path.is_dir():
            raise DiagramError(f"Directory not accessible: {directory}")

        parser = TerraformParser()
        tf_files = discover_files(scan_path, parser, exclude_patterns or [])
        logger.debug("Discovered %d .tf/.tofu files in %s", len(tf_files), directory)

        all_resources: list[ResourceModel] = []
        for tf_file in tf_files:
            all_resources.extend(parser.parse(str(tf_file)))
        return all_resources

    def build_graph(
        self,
        directory: str,
        exclude_patterns: list[str] | None = None,
        simplify: bool = False,
        exclude_types: list[str] | None = None,
    ) -> ResourceGraph:
        all_resources = self.parse_resources(directory, exclude_patterns)
        graph = GraphBuilder().build(all_resources)
        logger.debug("Built graph: %d nodes, %d edges", len(graph.nodes), len(graph.edges))

        types_to_hide: set[str] = set(exclude_types or [])
        if simplify:
            types_to_hide |= DEFAULT_NOISE_TYPES
        if types_to_hide:
            graph = filter_graph(graph, types_to_hide)
            logger.debug(
                "Filtered graph: %d nodes, %d edges (hidden types: %s)",
                len(graph.nodes),
                len(graph.edges),
                ", ".join(sorted(types_to_hide)),
            )
        return graph

    def extract_metadata(
        self,
        directory: str,
        exclude_patterns: list[str] | None = None,
    ) -> list[ResourceMetadata]:
        all_resources = self.parse_resources(directory, exclude_patterns)
        metadata = MetadataExtractor().extract(all_resources)
        logger.debug("Extracted metadata for %d resources", len(metadata))
        return metadata

    def generate(
        self,
        directory: str,
        fmt: str = "mermaid",
        exclude_patterns: list[str] | None = None,
    ) -> str:
        graph = self.build_graph(directory, exclude_patterns)
        return render_graph(graph, fmt)
