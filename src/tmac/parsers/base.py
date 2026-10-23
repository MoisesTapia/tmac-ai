from abc import ABC, abstractmethod
from typing import ClassVar, List, Tuple
from ..models.resource import ResourceModel

class BaseParser(ABC):
    """Abstract base class for Infrastructure as Code parsers.

    To plug a new IaC format into Scanner, subclass this and:
      - set ``file_patterns`` to the glob patterns the format uses (e.g. ``("*.tf",)``);
      - override ``can_parse`` when the extension alone is ambiguous
        (e.g. telling a CloudFormation template apart from any other YAML);
      - return ResourceModels from ``parse`` with ``ignored_rules`` already set
        from the format's inline suppression syntax.
    """

    file_patterns: ClassVar[Tuple[str, ...]] = ()

    def can_parse(self, file_path: str) -> bool:
        """Return False to skip a file that matched ``file_patterns`` but is not this format."""
        return True

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
