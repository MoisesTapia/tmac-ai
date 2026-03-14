import logging
import os
import sys

import click

from tmac.reporters.base import BaseReporter
from tmac.reporters.html import HTMLReporter
from tmac.reporters.json_report import JSONReporter
from tmac.reporters.markdown import MarkdownReporter
from tmac.scanner import ScanError, Scanner

SEVERITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


@click.group()
@click.version_option(version="1.0.0", prog_name="TMAC")
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

    reporter: BaseReporter
    if fmt == "html":
        reporter = HTMLReporter()
    elif fmt == "md":
        reporter = MarkdownReporter()
    else:
        reporter = JSONReporter()

    report_content = reporter.generate(result)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    if not quiet:
        click.echo(f"Scan complete: {result.statistics.total_findings} findings. Report saved to {out_file}")

    _exit_with_code(result.findings, threshold)


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
