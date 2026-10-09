"""Base formatter interface for search results."""

from abc import ABC, abstractmethod
from typing import Any


class ResultFormatter(ABC):
    """Base class for result formatters."""

    @abstractmethod
    def format(self, results: Any, **kwargs) -> str:
        """
        Format search results into a string representation.

        Args:
            results: Search results (can be list or dict depending on provider)
            **kwargs: Formatter-specific options

        Returns:
            Formatted string
        """
        pass

    def _extract_result_list(self, results: Any) -> list:
        """
        Extract result list from different result formats.

        Args:
            results: Either a list or dict with 'results' key

        Returns:
            List of results
        """
        if isinstance(results, dict):
            return results.get("results", [])
        elif isinstance(results, list):
            return results
        else:
            return []
