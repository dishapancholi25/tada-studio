"""Token-based text splitting strategy.

Best for optimal LLM compatibility with token-aware chunking.
"""

import logging
from typing import Any, Dict

from langchain_text_splitters import CharacterTextSplitter, TokenTextSplitter


logger = logging.getLogger(__name__)


class TokenStrategy:
    """Token-based splitting strategy with fallback."""

    @staticmethod
    def create(
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Dict[str, Any],
    ):
        """
        Create a token-based text splitter.

        Falls back to CharacterTextSplitter if tiktoken is not available.

        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Additional parameters (encoding_name, etc.)

        Returns:
            Configured TokenTextSplitter or CharacterTextSplitter instance
        """
        try:
            encoding_name = kwargs.get("encoding_name", "cl100k_base")
            return TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                encoding_name=encoding_name,
            )
        except ImportError:
            logger.warning("tiktoken not available, falling back to character splitter")
            return CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
