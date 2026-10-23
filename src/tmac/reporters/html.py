from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tmac.delta.models import DeltaScanResult
from tmac.models.finding import ScanResult
from tmac.reporters.base import BaseReporter

SAFE_URL_SCHEMES = {"http", "https"}


def safe_url(value: object) -> str:
    """Return the URL only if it uses http(s); otherwise '#' (blocks javascript:, data:, ...)."""
    url = str(value).strip()
    if urlparse(url).scheme.lower() in SAFE_URL_SCHEMES:
        return url
    return "#"


class HTMLReporter(BaseReporter):
    """Generates a self-contained HTML report of findings."""

    def generate(self, result: ScanResult, diagram: str | None = None) -> str:
        templates_dir = Path(__file__).parent.parent / "templates"
        # Findings carry attacker-controllable text (resource names, file paths,
        # custom rule fields), so every value must be HTML-escaped.
        env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(enabled_extensions=("html", "html.j2")),
        )
        env.filters["safe_url"] = safe_url

        if isinstance(result, DeltaScanResult):
            template = env.get_template("report_delta.html.j2")
            risk_delta = result.findings_introduced - result.findings_resolved
            return template.render(
                result=result,
                findings_introduced=result.findings_introduced,
                findings_resolved=result.findings_resolved,
                risk_delta=risk_delta,
                diagram=diagram,
            )

        template = env.get_template("report.html.j2")
        return template.render(result=result, diagram=diagram)
