from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from tmac.reporters.base import BaseReporter
from tmac.models.finding import ScanResult

class MarkdownReporter(BaseReporter):
    """Generates a Markdown report intended for Pull Request comments."""
    
    def generate(self, result: ScanResult) -> str:
        templates_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("report.md.j2")
        return template.render(result=result)
