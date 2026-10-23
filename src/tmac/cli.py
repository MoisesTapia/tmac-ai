import logging
import os
import sys

import click

from tmac.delta.scanner import DeltaScanError, DeltaScanner
from tmac.graph.service import DiagramError, DiagramService
from tmac.graph.diagrams import IMAGE_FORMATS, render_graph, render_image
from tmac.graph.grouping import group_by_name
from tmac.graph.metadata import render_metadata
from tmac.engine.severity import SEVERITY_LEVELS
from tmac.reporters import get_reporter
from tmac.scanner import ScanError, Scanner


@click.group()
@click.version_option(version="1.6.0", prog_name="TMAC")
def cli() -> None:
    """TMAC (Threat Modeling as Code) - Static Analysis for IaC."""
    pass


@cli.command()
@click.option("--dir", "-d", "directory", default=".", type=click.Path(exists=True), help="Directory to scan.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Output format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Additional rules directory.")
@click.option("--config", type=click.Path(), default=".tmac.yaml", help="Configuration file path.")
@click.option("--fail-on", type=click.Choice(["critical", "high", "medium", "low", "info"]), help="Severity threshold for exit 1.")
@click.option("--severity", type=click.Choice(["all", "critical", "high", "medium", "low", "info"]), help="Minimum severity to show.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--exclude", "-e", "exclude", multiple=True, type=click.STRING, help="Glob patterns to exclude (repeatable).")
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--diagram", "with_diagram", is_flag=True, help="Embed an architecture diagram (Mermaid) in HTML/MD reports.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def scan(
    directory: str,
    report: str,
    output: str,
    rules_dir: str,
    config: str,
    fail_on: str,
    severity: str,
    quiet: bool,
    exclude: tuple,
    no_color: bool,
    with_diagram: bool,
    verbose: bool,
) -> None:
    """Scan infrastructure code for security threats."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    if no_color:
        os.environ["NO_COLOR"] = "1"

    fmt = report or "html"
    out_file = output or f"tmac-report.{fmt}"
    threshold = (fail_on or "critical").lower()
    min_sev = severity or "all"

    try:
        result = Scanner().run_scan(
            directory=directory,
            rules_dir=rules_dir,
            exclude_patterns=list(exclude),
            min_severity=min_sev,
            verbose=verbose,
        )
    except ScanError as exc:
        click.echo(str(exc), err=True)
        sys.exit(3)

    # Build the architecture diagram only when requested and for HTML/MD reports.
    diagram_src: str | None = None
    if with_diagram and fmt in ("html", "md"):
        try:
            graph = DiagramService().build_graph(directory, exclude_patterns=list(exclude), simplify=True)
            diagram_src = render_graph(graph, "mermaid")
        except DiagramError as exc:
            click.echo(f"Warning: could not generate the diagram: {exc}", err=True)

    report_content = get_reporter(fmt).generate(result, diagram=diagram_src)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    if not quiet:
        click.echo(f"Scan complete: {result.statistics.total_findings} findings. Report saved to {out_file}")

    _exit_with_code(result.findings, threshold)


@cli.command()
@click.option("--plan-file", "-p", required=True, type=click.Path(), help="Path to the tfplan.json.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Output format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Additional rules directory.")
@click.option("--fail-on", type=click.Choice(["critical", "high", "medium", "low", "info"]), help="Severity threshold for exit 1.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def plan(
    plan_file: str,
    report: str,
    output: str,
    rules_dir: str,
    fail_on: str,
    quiet: bool,
    no_color: bool,
    verbose: bool,
) -> None:
    """Analyze a tfplan.json to detect the STRIDE risk delta."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    if no_color:
        os.environ["NO_COLOR"] = "1"

    fmt = report or "html"
    out_file = output or f"tmac-delta-report.{fmt}"
    threshold = (fail_on or "critical").lower()

    try:
        result = DeltaScanner().run(plan_file=plan_file, rules_dir=rules_dir, verbose=verbose)
    except DeltaScanError as exc:
        click.echo(str(exc), err=True)
        sys.exit(3)

    report_content = get_reporter(fmt).generate(result)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    if not quiet:
        click.echo(
            f"Delta scan complete: {result.findings_introduced} threats introduced, "
            f"{result.findings_resolved} resolved. Report saved to {out_file}"
        )

    _exit_with_code(result.findings, threshold)


@cli.command()
@click.option("--dir", "-d", "directory", default=".", type=click.Path(exists=True), help="Terraform directory to analyze.")
@click.option("--format", "-f", "diagram_format", type=click.Choice(["mermaid", "dot", "drawio", "png", "svg", "pdf"]), default="mermaid", help="Diagram format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--metadata", "metadata_flag", is_flag=True, help="Also generate a document with the configuration of each resource.")
@click.option("--metadata-format", type=click.Choice(["md", "json"]), default="md", help="Metadata document format.")
@click.option("--simplify", "-s", is_flag=True, help="Hide plumbing resources (IAM, permissions, policies) for a more readable diagram.")
@click.option("--group", "-g", "group_flag", is_flag=True, help="Group resources by microservice (subgraphs).")
@click.option("--exclude-type", "exclude_types", multiple=True, type=click.STRING, help="Resource type to hide from the diagram (repeatable).")
@click.option("--exclude", "-e", "exclude", multiple=True, type=click.STRING, help="Glob patterns to exclude (repeatable).")
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def diagram(
    directory: str,
    diagram_format: str,
    output: str,
    metadata_flag: bool,
    metadata_format: str,
    simplify: bool,
    group_flag: bool,
    exclude_types: tuple,
    exclude: tuple,
    quiet: bool,
    verbose: bool,
) -> None:
    """Generate an architecture diagram from the Terraform dependency graph."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    ext = {"mermaid": "mmd", "dot": "dot", "drawio": "drawio", "png": "png", "svg": "svg", "pdf": "pdf"}[diagram_format]
    out_file = output or f"tmac-diagram.{ext}"
    exclude_patterns = list(exclude)
    service = DiagramService()

    try:
        graph = service.build_graph(
            directory,
            exclude_patterns=exclude_patterns,
            simplify=simplify,
            exclude_types=list(exclude_types),
        )
        groups = group_by_name(graph) if group_flag else None
        if diagram_format in IMAGE_FORMATS:
            render_image(graph, out_file, diagram_format, groups)
        else:
            content = render_graph(graph, diagram_format, groups)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(content)
    except DiagramError as exc:
        click.echo(str(exc), err=True)
        sys.exit(3)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(3)

    if not quiet:
        click.echo(
            f"Diagram generated: {len(graph.nodes)} resources, {len(graph.edges)} connections. "
            f"Saved to {out_file}"
        )

    if metadata_flag:
        try:
            metadata = service.extract_metadata(directory, exclude_patterns=exclude_patterns)
        except DiagramError as exc:
            click.echo(str(exc), err=True)
            sys.exit(3)
        meta_ext = "json" if metadata_format == "json" else "md"
        meta_file = f"tmac-metadata.{meta_ext}"
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(render_metadata(metadata, metadata_format))
        if not quiet:
            click.echo(f"Metadata for {len(metadata)} resources saved to {meta_file}")


@cli.command()
@click.option("--dir", "-d", "directory", default=".", type=click.Path(exists=True), help="Terraform directory to scan.")
@click.option("--plan-file", "-p", type=click.Path(), default=None, help="Path to tfplan.json (uses DeltaScanner).")
@click.option("--base-ref", default=None, help="Base git ref for delta comparison.")
@click.option("--head-ref", default=None, help="Head git ref for delta comparison.")
@click.option("--delta-only/--no-delta-only", default=True, help="Restrict scan to changed .tf files (default: on).")
@click.option("--comment/--no-comment", default=True, help="Publish a PR/MR comment (default: on).")
@click.option("--fail-on", type=click.Choice(["critical", "high", "medium", "low", "info"]), default="high", help="Severity threshold for non-zero exit.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), default="md", help="Report format.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path for the report.")
@click.option("--platform", type=click.Choice(["github", "gitlab"]), default=None, help="CI platform (auto-detected when not provided).")
@click.option("--exclude", "-e", multiple=True, help="Glob patterns to exclude (repeatable).")
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def ci(
    directory: str,
    plan_file: str,
    base_ref: str,
    head_ref: str,
    delta_only: bool,
    comment: bool,
    fail_on: str,
    report: str,
    output: str,
    platform: str,
    exclude: tuple,
    quiet: bool,
    no_color: bool,
    verbose: bool,
) -> None:
    """Run a CI-native delta scan, write the report, and publish a PR/MR comment."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    if no_color:
        os.environ["NO_COLOR"] = "1"

    # Validate refs when delta_only is active and no plan_file supplied (R1.7, R1.8)
    if delta_only and not plan_file:
        if base_ref is None:
            click.echo("Error: --base-ref is required for delta-only mode", err=True)
            sys.exit(3)
        if head_ref is None:
            click.echo("Error: --head-ref is required for delta-only mode", err=True)
            sys.exit(3)

    from tmac.ci.runner import CIRunner, ci_context_from_env

    # Build CIContext from env with explicit CLI overrides
    ctx = ci_context_from_env(
        platform=platform,
        base_ref=base_ref,
        head_ref=head_ref,
    )

    runner = CIRunner()
    exit_code = runner.run(
        directory=directory,
        plan_file=plan_file,
        fail_on=fail_on,
        report_fmt=report,
        output=output,
        delta_only=delta_only,
        comment=comment,
        exclude=list(exclude),
        ctx=ctx,
    )
    sys.exit(exit_code)


def _exit_with_code(findings: list, threshold: str) -> None:
    """Determine and apply exit code based on findings and threshold."""
    threshold_val = SEVERITY_LEVELS.get(threshold, SEVERITY_LEVELS["critical"])
    max_sev = max((SEVERITY_LEVELS.get(f.severity.lower(), -1) for f in findings), default=-1)

    if max_sev < threshold_val:
        sys.exit(0)

    has_critical = any(f.severity.lower() == "critical" for f in findings)
    has_high = any(f.severity.lower() == "high" for f in findings)

    if has_critical:
        sys.exit(1)
    elif has_high:
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    cli()
