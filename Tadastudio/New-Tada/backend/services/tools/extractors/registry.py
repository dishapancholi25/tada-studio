"""
Extractor registry for mapping tool names to extractors.

This module provides the central registry that matches tool names
to their appropriate extractors based on patterns.
"""

import logging
from typing import Dict, Optional

from .base import BaseExtractor
from .fallback import FallbackExtractor
from .http_request import HttpRequestExtractor
from .query_based import QueryBasedExtractor
from .structured import StructuredToolExtractor


logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """
    Registry for managing tool extractors.

    The registry maps tool name patterns to extractor instances
    and provides methods to look up the appropriate extractor
    for a given tool name.

    Attributes:
        _pattern_to_extractor: Mapping of tool name patterns to extractors
        _fallback_extractor: Default extractor for unmatched tools
    """

    def __init__(self):
        """Initialize the extractor registry with default mappings."""
        # Create extractor instances
        self._structured_extractor = StructuredToolExtractor()
        self._query_extractor = QueryBasedExtractor()
        self._http_extractor = HttpRequestExtractor()
        self._fallback_extractor = FallbackExtractor()

        # Pattern to extractor mapping
        # Order matters - more specific patterns should come first
        self._pattern_to_extractor: Dict[str, BaseExtractor] = {
            # HTTP/API tools
            "http_request": self._http_extractor,
            # Query-based tools
            "query_database": self._query_extractor,
            "search_web": self._query_extractor,
            "web_search": self._query_extractor,
            # Structured tools
            "search_documents": self._structured_extractor,
            "delegate": self._structured_extractor,
            "create_sub_agent": self._structured_extractor,
        }

        logger.info(
            f"[TOOL-EXTRACTOR] Initialized registry with {len(self._pattern_to_extractor)} patterns"
        )

    def get_extractor(self, tool_name: str) -> BaseExtractor:
        """
        Get the appropriate extractor for a tool name.

        Matches the tool name against registered patterns and returns
        the corresponding extractor. Falls back to FallbackExtractor
        if no pattern matches.

        Args:
            tool_name: Name of the tool to extract data for

        Returns:
            Appropriate extractor instance
        """
        if not tool_name:
            logger.warning("[TOOL-EXTRACTOR] Empty tool name, using fallback extractor")
            return self._fallback_extractor

        # Normalize tool name for matching
        normalized_name = tool_name.lower().strip()

        # Try to match patterns
        for pattern, extractor in self._pattern_to_extractor.items():
            if pattern in normalized_name:
                logger.debug(
                    f"[TOOL-EXTRACTOR] Matched tool '{tool_name}' to pattern '{pattern}' -> {extractor.name}"
                )
                return extractor

        # No match found, use fallback
        logger.debug(
            f"[TOOL-EXTRACTOR] No pattern matched for tool '{tool_name}', using {self._fallback_extractor.name}"
        )
        return self._fallback_extractor

    def register_pattern(self, pattern: str, extractor: BaseExtractor) -> None:
        """
        Register a custom pattern and extractor.

        This allows dynamic registration of new extractors at runtime.

        Args:
            pattern: Tool name pattern to match (case-insensitive substring)
            extractor: Extractor instance to use for this pattern

        Example:
            registry.register_pattern("custom_tool", CustomExtractor())
        """
        if not pattern:
            raise ValueError("Pattern cannot be empty")

        if not isinstance(extractor, BaseExtractor):
            raise TypeError("Extractor must inherit from BaseExtractor")

        self._pattern_to_extractor[pattern] = extractor
        logger.info(
            f"[TOOL-EXTRACTOR] Registered custom pattern '{pattern}' -> {extractor.name}"
        )

    def unregister_pattern(self, pattern: str) -> bool:
        """
        Unregister a pattern from the registry.

        Args:
            pattern: Pattern to remove

        Returns:
            True if pattern was removed, False if not found
        """
        if pattern in self._pattern_to_extractor:
            del self._pattern_to_extractor[pattern]
            logger.info(f"[TOOL-EXTRACTOR] Unregistered pattern '{pattern}'")
            return True
        return False

    def get_registered_patterns(self) -> Dict[str, str]:
        """
        Get all registered patterns and their extractor names.

        Returns:
            Dictionary mapping patterns to extractor names
        """
        return {
            pattern: extractor.name
            for pattern, extractor in self._pattern_to_extractor.items()
        }


# Global registry instance
_global_registry: Optional[ExtractorRegistry] = None


def get_registry() -> ExtractorRegistry:
    """
    Get the global extractor registry instance.

    Creates the registry on first call (singleton pattern).

    Returns:
        Global ExtractorRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ExtractorRegistry()
    return _global_registry


def reset_registry() -> None:
    """
    Reset the global registry.

    Useful for testing or when you want to reinitialize with different defaults.
    """
    global _global_registry
    _global_registry = None
    logger.info("[TOOL-EXTRACTOR] Registry reset")
