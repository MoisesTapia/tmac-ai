from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from tmac.reporters.base import BaseReporter
from tmac.models.finding import ScanResult

class HTMLReporter(BaseReporter):
    """Generates a self-contained HTML report of findings."""
    
    def generate(self, result: ScanResult) -> str:
        templates_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("report.html.j2")
        return template.render(result=result)
