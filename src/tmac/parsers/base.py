from abc import ABC, abstractmethod
from typing import List
from ..models.resource import ResourceModel

class BaseParser(ABC):
    """Abstract base class for Infrastructure as Code parsers."""
    
    @abstractmethod
    def parse(self, file_path: str) -> List[ResourceModel]:
        """
        Parse an IaC file and return a list of ResourceModels.
        
        Args:
            file_path: Path to the IaC file
            
        Returns:
            List of normalized ResourceModels extracted from the file
        """
        pass
