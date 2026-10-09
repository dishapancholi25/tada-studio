"""
Content type handlers for token counting.

This module provides strategies for counting tokens in different content types.
"""

import json
import logging
from typing import Any, Callable


logger = logging.getLogger(__name__)


class ContentTokenCounter:
    """Handles token counting for different content types."""

    def __init__(self, string_counter: Callable[[str], int]):
        """
        Initialize content counter with a string counting function.

        Args:
            string_counter: Function to count tokens in a string
        """
        self.count_string = string_counter

    def count_content(self, content: Any) -> int:
        """
        Count tokens in content of various types.

        Args:
            content: Content to count (str, dict, list, or other)

        Returns:
            Number of tokens
        """
        if isinstance(content, str):
            return self._count_string_content(content)
        elif isinstance(content, dict):
            return self._count_dict_content(content)
        elif isinstance(content, list):
            return self._count_list_content(content)
        else:
            return 0

    def _count_string_content(self, content: str) -> int:
        """
        Count tokens in string content.

        Args:
            content: String content

        Returns:
            Number of tokens
        """
        return self.count_string(content)

    def _count_dict_content(self, content: dict) -> int:
        """
        Count tokens in structured dictionary content.

        Args:
            content: Dictionary content

        Returns:
            Number of tokens
        """
        # For structured content, serialize to JSON
        return self.count_string(json.dumps(content))

    def _count_list_content(self, content: list) -> int:
        """
        Count tokens in multi-part list content.

        Args:
            content: List content

        Returns:
            Number of tokens
        """
        # For multi-part content, count each part
        total = 0
        for part in content:
            if isinstance(part, str):
                total += self.count_string(part)
            else:
                # Non-string parts are serialized to JSON
                total += self.count_string(json.dumps(part))
        return total
