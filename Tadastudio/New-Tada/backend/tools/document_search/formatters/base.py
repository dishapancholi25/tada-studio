"""Base formatter interface for document search results."""

import logging
from abc import ABC, abstractmethod
from typing import List, Tuple

from langchain_core.documents import Document


logger = logging.getLogger(__name__)


class BaseFormatter(ABC):
    """Abstract base formatter for search results."""

    @abstractmethod
    def format(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        include_confidence: bool = True,
    ) -> str:
        """Format search results.

        Args:
            results: List of (Document, score) tuples
            query: Original search query
            include_confidence: Whether to include confidence scores

        Returns:
            Formatted string
        """
        pass

    def _check_empty_results(self, results: List[Tuple[Document, float]]) -> bool:
        """Check if results are empty.

        Args:
            results: List of search results

        Returns:
            True if results are empty
        """
        return not results

    def _get_empty_message(self) -> str:
        """Get message for empty results.

        Returns:
            Empty results message
        """
        return "No relevant documents found for the query."
