import logging
import os
import sys
from typing import Any, NoReturn

import click
from click.core import ParameterSource

from tmac import __version__
from tmac.config import ConfigError, load_config
from tmac.delta.scanner import DeltaScanError, DeltaScanner
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


@cli.command()
@click.option(
    "--dir",
    "-d",
    "directory",
    type=click.Path(),
    help="Directory to scan (default: scan.dir from config, else '.').",
)
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Output format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Additional rules directory.")
@click.option("--config", type=click.Path(), default=".tmac.yaml", help="Configuration file path.")
@click.option(
    "--fail-on", type=click.Choice(SEVERITY_CHOICES), help="Severity threshold for exit 1."
)
@click.option(
    "--severity", type=click.Choice(["all"] + SEVERITY_CHOICES), help="Minimum severity to show."
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option(
    "--exclude",
    "-e",
    "exclude",
    multiple=True,
    type=click.STRING,
    help="Glob patterns to exclude (repeatable).",
)
@click.option(
    "--lenient", is_flag=True, help="Don't exit 3 when files can't be parsed or rules are invalid."
)
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def scan(
    ctx: click.Context,
    directory: str | None,
    report: str | None,
    output: str | None,
    rules_dir: str | None,
    config: str,
    fail_on: str | None,
    severity: str | None,
    quiet: bool,
    exclude: tuple[str, ...],
    lenient: bool,
    no_color: bool,
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

    _write_report(result, fmt, out_file)
    if not quiet:
        click.echo(
            f"Scan complete: {result.statistics.total_findings} findings. Report saved to {out_file}"
        )

    _check_issues(result, lenient)
    _exit_with_code(result.findings, threshold)


@cli.command()
@click.option("--plan-file", "-p", required=True, type=click.Path(), help="Ruta al tfplan.json.")
@click.option("--report", "-r", type=click.Choice(["html", "json", "md"]), help="Output format.")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option("--rules-dir", type=click.Path(exists=True), help="Additional rules directory.")
@click.option("--config", type=click.Path(), default=".tmac.yaml", help="Configuration file path.")
@click.option(
    "--source-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Directorio con los .tf del plan, para aplicar sus comentarios tmac:ignore.",
)
@click.option(
    "--fail-on", type=click.Choice(SEVERITY_CHOICES), help="Severity threshold for exit 1."
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress stdout output.")
@click.option("--lenient", is_flag=True, help="Don't exit 3 when rules are invalid.")
@click.option("--no-color", "no_color", is_flag=True, help="Disable ANSI color output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def plan(
    ctx: click.Context,
    plan_file: str,
    report: str | None,
    output: str | None,
    rules_dir: str | None,
    config: str,
    source_dir: str | None,
    fail_on: str | None,
    quiet: bool,
    lenient: bool,
    no_color: bool,
    verbose: bool,
) -> None:
    """Analiza un tfplan.json para detectar el delta de riesgo STRIDE."""
    _setup(verbose, no_color)
    cfg = _load_cli_config(ctx, config)
    report_cfg = cfg.get("report", {})

    fmt = report or report_cfg.get("format", "html")
    out_file = output or f"tmac-delta-report.{fmt}"
    threshold = fail_on or report_cfg.get("fail_on", "critical")
    resource_ignores = (
        TerraformParser().collect_resource_ignores(source_dir) if source_dir else None
    )

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
            f"Delta scan complete: {result.findings_introduced} amenazas introducidas, "
            f"{result.findings_resolved} resueltas. Reporte guardado en {out_file}"
        )

    _check_issues(result, lenient)
    _exit_with_code(result.findings, threshold)


def _setup(verbose: bool, no_color: bool) -> None:
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    if no_color:
        os.environ["NO_COLOR"] = "1"


def _fail(message: str) -> NoReturn:
    """Exit 3: the scan could not run, or its results cannot be trusted."""
    click.echo(message, err=True)
    sys.exit(3)


def _load_cli_config(ctx: click.Context, config_path: str) -> dict[str, Any]:
    """Load .tmac.yaml. A missing default file is fine; a missing explicit --config is an error."""
    explicit = ctx.get_parameter_source("config") == ParameterSource.COMMANDLINE
    if explicit and not os.path.isfile(config_path):
        _fail(f"Config file not found: {config_path}")
    try:
        return load_config(config_path)
    except ConfigError as exc:
        _fail(str(exc))


def _write_report(result: ScanResult, fmt: str, out_file: str) -> None:
    report_content = get_reporter(fmt).generate(result)
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
        click.echo(
            f"  ... and {len(result.issues) - MAX_ISSUES_SHOWN} more (see the report)", err=True
        )
    if not lenient:
        _fail(
            "Failing with exit code 3 because results may be missing findings (use --lenient to ignore)."
        )


def _exit_with_code(findings: list[Finding], threshold: str) -> NoReturn:
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
