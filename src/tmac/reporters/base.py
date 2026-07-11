from abc import ABC, abstractmethod
from tmac.models.finding import ScanResult

class BaseReporter(ABC):
    """Abstract base class for reporters."""
    
    @abstractmethod
    def generate(self, result: ScanResult, diagram: str | None = None) -> str:
        """
        Generate a formatted report.

        Args:
            result: The scan result object containing findings and metadata
            diagram: Optional Mermaid diagram source to embed in the report

        Returns:
            String content of the rendered report
        """
        raise NotImplementedError()
