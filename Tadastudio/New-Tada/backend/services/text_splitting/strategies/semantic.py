"""Semantic text splitting strategy.

Best for preserving context using NLP-based sentence/paragraph detection.
"""

import logging
from typing import Any, Dict

from langchain_text_splitters import (
    NLTKTextSplitter,
    RecursiveCharacterTextSplitter,
    SpacyTextSplitter,
)


logger = logging.getLogger(__name__)


class SemanticStrategy:
    """Semantic splitting strategy with multiple fallbacks."""

    @staticmethod
    def create(
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Dict[str, Any],
    ):
        """
        Create a semantic text splitter.

        Tries SpaCy first, falls back to NLTK, then to recursive splitter.

        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Additional parameters (pipeline, etc.)

        Returns:
            Configured semantic splitter or fallback instance
        """
        # Try SpaCy first (better performance)
        try:
            pipeline = kwargs.get("pipeline", "en_core_web_sm")
            return SpacyTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                pipeline=pipeline,
            )
        except (ImportError, OSError):
            pass

        # Fall back to NLTK
        try:
            import nltk

            # Download punkt tokenizer if not available
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)

            return NLTKTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        except ImportError:
            pass

        # Final fallback to recursive splitter with sentence-aware separators
        logger.warning(
            "Neither SpaCy nor NLTK available, falling back to recursive splitter"
        )
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",
                "\n",
                ". ",
                "! ",
                "? ",
                "; ",
                ", ",
                " ",
                "",
            ],
            is_separator_regex=False,
        )
