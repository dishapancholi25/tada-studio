"""Base interface for text splitting strategies."""

from typing import Any, Dict, Protocol


class TextSplitterStrategy(Protocol):
    """Protocol defining the interface for text splitting strategies."""

    def create(
        self,
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Dict[str, Any],
    ):
        """
        Create a text splitter instance.

        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Strategy-specific parameters

        Returns:
            A configured text splitter instance
        """
        ...
