"""Whole page text splitting strategy.

Keeps PDF pages intact as single chunks without splitting.
Best for documents with page-based structure where page context is important.
"""

from typing import Any, Dict, List

from langchain_core.documents import Document


class WholePageSplitter:
    """A splitter that keeps documents intact without splitting.

    This is used for the whole_page strategy where each page
    should remain as a single chunk.
    """

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Return documents as-is without splitting.

        Args:
            documents: List of Document objects (typically one per page)

        Returns:
            The same documents unchanged
        """
        return documents

    def split_text(self, text: str) -> List[str]:
        """Return text as a single chunk.

        Args:
            text: The text to "split"

        Returns:
            List containing the entire text as one element
        """
        return [text] if text else []


class WholePageStrategy:
    """Whole page splitting strategy - keeps pages intact."""

    @staticmethod
    def create(
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Dict[str, Any],
    ) -> WholePageSplitter:
        """
        Create a whole page splitter.

        Note: chunk_size and chunk_overlap are ignored for this strategy
        as pages are kept intact without splitting.

        Args:
            chunk_size: Ignored for this strategy
            chunk_overlap: Ignored for this strategy
            **kwargs: Additional parameters (unused)

        Returns:
            Configured WholePageSplitter instance
        """
        return WholePageSplitter()
