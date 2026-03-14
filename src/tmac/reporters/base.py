from abc import ABC, abstractmethod
from tmac.models.finding import ScanResult

class BaseReporter(ABC):
    """Abstract base class for reporters."""
    
    @abstractmethod
    def generate(self, result: ScanResult) -> str:
        """
        Generate a formatted report.
        
        Args:
            result: The scan result object containing findings and metadata
            
        Returns:
            String content of the rendered report
        """
        raise NotImplementedError()
