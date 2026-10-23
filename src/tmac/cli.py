import logging
import os
import sys
from typing import Any, Dict, List, NoReturn, Optional

import click
from click.core import ParameterSource

from tmac import __version__
from tmac.config import ConfigError, load_config
from tmac.delta.scanner import DeltaScanError, DeltaScanner
from tmac.graph.service import DiagramError, DiagramService
from tmac.graph.diagrams import IMAGE_FORMATS, render_graph, render_image
from tmac.graph.grouping import group_by_name
from tmac.graph.metadata import render_metadata
from tmac.engine.severity import SEVERITY_LEVELS
from tmac.models.finding import Finding, ScanResult
from tmac.parsers.terraform import TerraformParser
from tmac.reporters import get_reporter
from tmac.scanner import ScanError, Scanner

SEVERITY_CHOICES = ["critical", "high", "medium", "low", "info"]
MAX_ISSUES_SHOWN = 10


@click.group()
@click.version_option(version=__version__, prog_name="TMAC")
def cli() -> None:
    """TMAC (Threat Modeling as Code) - Static Analysis for IaC."""
    pass


@cli.command()
@click.option("--dir", "-d", "directory", type=click.Path(), help="Directory to scan (default: scan.dir from config, else '.').")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Output format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Additional rules directory.")
@click.option("--config", type=click.Path(), default=".tmac.yaml", help="Configuration file path.")
@click.option("--fail-on", type=click.Choice(SEVERITY_CHOICES), help="Severity threshold for exit 1.")
@click.option("--severity", type=click.Choice(["all"] + SEVERITY_CHOICES), help="Minimum severity to show.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--exclude", "-e", "exclude", multiple=True, type=click.STRING, help="Glob patterns to exclude (repeatable).")
@click.option("--lenient", is_flag=True, help="Don't exit 3 when files can't be parsed or rules are invalid.")
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--diagram", "with_diagram", is_flag=True, help="Embed an architecture diagram (Mermaid) in HTML/MD reports.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def scan(
    ctx: click.Context,
    directory: Optional[str],
    report: Optional[str],
    output: Optional[str],
    rules_dir: Optional[str],
    config: str,
    fail_on: Optional[str],
    severity: Optional[str],
    quiet: bool,
    exclude: tuple,
    lenient: bool,
    no_color: bool,
    with_diagram: bool,
    verbose: bool,
) -> None:
    """Scan infrastructure code for security threats."""
    _setup(verbose, no_color)
    cfg = _load_cli_config(ctx, config)
    scan_cfg, report_cfg = cfg.get("scan", {}), cfg.get("report", {})

    # Precedence: CLI flag > .tmac.yaml > built-in default
    fmt = report or report_cfg.get("format", "html")
    out_file = output or f"tmac-report.{fmt}"
    threshold = fail_on or report_cfg.get("fail_on", "critical")
    min_sev = severity or report_cfg.get("severity", "all")
    target_dir = directory or scan_cfg.get("dir") or "."

    try:
        result = Scanner().run_scan(
            directory=target_dir,
            rules_dir=rules_dir,
            exclude_patterns=list(exclude),
            min_severity=min_sev,
            verbose=verbose,
            config=cfg,
        )
    except ScanError as exc:
        _fail(str(exc))

    # Build the architecture diagram only when requested and for HTML/MD reports.
    diagram_src: str | None = None
    if with_diagram and fmt in ("html", "md"):
        try:
            graph = DiagramService().build_graph(
                target_dir, exclude_patterns=list(exclude), simplify=True
            )
            diagram_src = render_graph(graph, "mermaid")
        except DiagramError as exc:
            click.echo(f"Warning: could not generate the diagram: {exc}", err=True)

    _write_report(result, fmt, out_file, diagram=diagram_src)
    if not quiet:
        click.echo(f"Scan complete: {result.statistics.total_findings} findings. Report saved to {out_file}")

    _check_issues(result, lenient)
    _exit_with_code(result.findings, threshold)


@cli.command()
@click.option("--plan-file", "-p", required=True, type=click.Path(), help="Path to the tfplan.json.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Output format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Additional rules directory.")
@click.option("--config", type=click.Path(), default=".tmac.yaml", help="Configuration file path.")
@click.option("--source-dir", type=click.Path(exists=True, file_okay=False), help="Directory with the plan's .tf sources, to apply their tmac:ignore comments.")
@click.option("--fail-on", type=click.Choice(SEVERITY_CHOICES), help="Severity threshold for exit 1.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--lenient", is_flag=True, help="Don't exit 3 when rules are invalid.")
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def plan(
    ctx: click.Context,
    plan_file: str,
    report: Optional[str],
    output: Optional[str],
    rules_dir: Optional[str],
    config: str,
    source_dir: Optional[str],
    fail_on: Optional[str],
    quiet: bool,
    lenient: bool,
    no_color: bool,
    verbose: bool,
) -> None:
    """Analyze a tfplan.json to detect the STRIDE risk delta."""
    _setup(verbose, no_color)
    cfg = _load_cli_config(ctx, config)
    report_cfg = cfg.get("report", {})

    fmt = report or report_cfg.get("format", "html")
    out_file = output or f"tmac-delta-report.{fmt}"
    threshold = fail_on or report_cfg.get("fail_on", "critical")
    resource_ignores = TerraformParser().collect_resource_ignores(source_dir) if source_dir else None

    try:
        result = DeltaScanner().run(
            plan_file=plan_file,
            rules_dir=rules_dir or cfg.get("scan", {}).get("rules_dir"),
            verbose=verbose,
            resource_ignores=resource_ignores,
        )
    except DeltaScanError as exc:
        _fail(str(exc))

    _write_report(result, fmt, out_file)
    if not quiet:
        click.echo(
            f"Delta scan complete: {result.findings_introduced} threats introduced, "
            f"{result.findings_resolved} resolved. Report saved to {out_file}"
        )

    _check_issues(result, lenient)
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
@click.option("--lenient", is_flag=True, help="Don't exit 3 when files can't be parsed or rules are invalid.")
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
    lenient: bool,
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
        lenient=lenient,
    )
    sys.exit(exit_code)


def _setup(verbose: bool, no_color: bool) -> None:
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    if no_color:
        os.environ["NO_COLOR"] = "1"

def _fail(message: str) -> NoReturn:
    """Exit 3: the scan could not run, or its results cannot be trusted."""
    click.echo(message, err=True)
    sys.exit(3)


def _load_cli_config(ctx: click.Context, config_path: str) -> Dict[str, Any]:
    """Load .tmac.yaml. A missing default file is fine; a missing explicit --config is an error."""
    explicit = ctx.get_parameter_source("config") == ParameterSource.COMMANDLINE
    if explicit and not os.path.isfile(config_path):
        _fail(f"Config file not found: {config_path}")
    try:
        return load_config(config_path)
    except ConfigError as exc:
        _fail(str(exc))


def _write_report(
    result: ScanResult, fmt: str, out_file: str, diagram: Optional[str] = None
) -> None:
    report_content = get_reporter(fmt).generate(result, diagram=diagram)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_content)


def _check_issues(result: ScanResult, lenient: bool) -> None:
    """Report scan issues on stderr; unless lenient, an incomplete scan exits 3 (fail closed)."""
    if not result.issues:
        return
    click.echo(f"Warning: the scan is incomplete ({len(result.issues)} issue(s)):", err=True)
    for issue in result.issues[:MAX_ISSUES_SHOWN]:
        click.echo(f"  [{issue.kind}] {issue.message}", err=True)
    if len(result.issues) > MAX_ISSUES_SHOWN:
        click.echo(f"  ... and {len(result.issues) - MAX_ISSUES_SHOWN} more (see the report)", err=True)
    if not lenient:
        _fail("Failing with exit code 3 because results may be missing findings (use --lenient to ignore).")


def _exit_with_code(findings: List[Finding], threshold: str) -> NoReturn:
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
