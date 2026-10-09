"""
Base classes and protocols for token counting.

This module defines abstract interfaces for token counters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage


class BaseTokenCounter(ABC):
    """Abstract base class for token counters."""

    @abstractmethod
    def count_string(self, text: str) -> int:
        """
        Count tokens in a string.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def count_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        Count tokens in a list of messages.

        Args:
            messages: List of LangChain messages

        Returns:
            Dictionary with token counts and breakdown
        """
        pass
