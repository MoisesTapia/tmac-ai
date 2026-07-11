from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from tmac.reporters.base import BaseReporter
from tmac.models.finding import ScanResult
from tmac.delta.models import DeltaScanResult

class HTMLReporter(BaseReporter):
    """Generates a self-contained HTML report of findings."""

    def generate(self, result: ScanResult, diagram: str | None = None) -> str:
        templates_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(templates_dir))

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
