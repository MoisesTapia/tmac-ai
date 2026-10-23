from abc import ABC, abstractmethod
from typing import ClassVar, List, Tuple
from ..models.resource import ResourceModel


class ParseError(Exception):
    """Raised by parse_strict() when a file cannot be parsed."""


class BaseParser(ABC):
    """Abstract base class for Infrastructure as Code parsers.

    To plug a new IaC format into Scanner, subclass this and:
      - set ``file_patterns`` to the glob patterns the format uses (e.g. ``("*.tf",)``);
      - override ``can_parse`` when the extension alone is ambiguous
        (e.g. telling a CloudFormation template apart from any other YAML);
      - return ResourceModels from ``parse`` with ``ignored_rules`` already set
        from the format's inline suppression syntax;
      - override ``parse_strict`` to raise ParseError on unparseable input, so
        Scanner can report the file instead of treating it as having no resources.
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

    def parse_strict(self, file_path: str) -> List[ResourceModel]:
        """Like parse(), but raises ParseError when the file cannot be parsed.

        The default cannot tell a failure from an empty file; parsers should override it.
        """
        return self.parse(file_path)
