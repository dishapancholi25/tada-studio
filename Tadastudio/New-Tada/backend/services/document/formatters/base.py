"""Base formatter interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def format(self, raw_result: Dict[str, Any], config: Dict[str, Any]) -> Any:
        """
        Format raw processing result.

        Args:
            raw_result: Raw processing result from processor
            config: Processing configuration

        Returns:
            Formatted output
        """
        pass
