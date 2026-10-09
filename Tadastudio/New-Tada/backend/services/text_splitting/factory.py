"""Factory for creating text splitters based on strategy."""

import logging
from typing import Any, Dict

from .strategies import (
    CharacterStrategy,
    RecursiveStrategy,
    SemanticStrategy,
    TokenStrategy,
    WholePageStrategy,
)


logger = logging.getLogger(__name__)


class TextSplitterFactory:
    """Factory class for creating different text splitters based on strategy."""

    # Strategy registry
    _strategies = {
        "recursive": RecursiveStrategy,
        "character": CharacterStrategy,
        "token": TokenStrategy,
        "semantic": SemanticStrategy,
        "whole_page": WholePageStrategy,
    }

    @staticmethod
    def create_splitter(
        strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs: Dict[str, Any],
    ):
        """
        Create a text splitter based on the specified strategy.

        Args:
            strategy: The splitting strategy to use
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Additional strategy-specific parameters

        Returns:
            A configured text splitter instance
        """
        strategy_class = TextSplitterFactory._strategies.get(strategy)

        if strategy_class is None:
            logger.warning(
                f"Unknown strategy '{strategy}', using default recursive splitter"
            )
            strategy_class = RecursiveStrategy

        return strategy_class.create(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs,
        )
