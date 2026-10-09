"""Character-based text splitting strategy.

Best for documents with simple structure using a single separator.
"""

from typing import Any, Dict

from langchain_text_splitters import CharacterTextSplitter


class CharacterStrategy:
    """Character-based splitting strategy."""

    @staticmethod
    def create(
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Dict[str, Any],
    ) -> CharacterTextSplitter:
        """
        Create a character text splitter.

        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Additional parameters (separator, etc.)

        Returns:
            Configured CharacterTextSplitter instance
        """
        return CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=kwargs.get("separator", "\n"),
            length_function=len,
            is_separator_regex=False,
        )
