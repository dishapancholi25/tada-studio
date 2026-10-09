"""Recursive character text splitting strategy.

Best for general-purpose document chunking with hierarchical separators.
"""

from typing import Any, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter


class RecursiveStrategy:
    """Recursive character splitting strategy."""

    @staticmethod
    def create(
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Dict[str, Any],
    ) -> RecursiveCharacterTextSplitter:
        """
        Create a recursive character text splitter.

        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Additional parameters (separators, etc.)

        Returns:
            Configured RecursiveCharacterTextSplitter instance
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=kwargs.get(
                "separators", ["\n\n", "\n", ".", "!", "?", ";", ",", " ", ""]
            ),
            is_separator_regex=False,
        )
