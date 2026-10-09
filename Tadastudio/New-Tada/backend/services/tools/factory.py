"""
Tool factory for creating tool instances.

This module provides the ToolFactory class which manages tool creation
using registered creators, with caching and validation.
"""

from typing import Any, Callable, Dict, Optional

from langchain_core.tools import BaseTool

from ..config import get_logger
from .cache import ToolCache
from .creators import (
    CalculationCreator,
    CustomToolCreator,
    DatabaseCreator,
    FileSystemCreator,
    HttpRequestCreator,
    WebSearchCreator,
)
from .validation import ConfigValidator


logger = get_logger("tool-factory")


class ToolFactory:
    """
    Factory for creating tool instances with caching.

    The factory uses registered creators to instantiate tools from
    configuration dictionaries, with automatic caching and validation.
    """

    def __init__(self, enable_cache: bool = True, cache_ttl: int = 300):
        """
        Initialize the tool factory.

        Args:
            enable_cache: Whether to enable tool instance caching
            cache_ttl: Cache time-to-live in seconds
        """
        self._cache = (
            ToolCache(max_size=128, default_ttl=cache_ttl) if enable_cache else None
        )
        self._creators: Dict[str, Any] = {}
        self._custom_creation_functions: Dict[str, Callable] = {}
        self._register_default_creators()
        logger.info(
            f"[TOOL-FACTORY] Initialized (caching={'enabled' if enable_cache else 'disabled'})"
        )

    def _register_default_creators(self) -> None:
        """Register default tool creators."""
        # Instantiate creators
        web_search_creator = WebSearchCreator()
        database_creator = DatabaseCreator()
        file_system_creator = FileSystemCreator()
        calculation_creator = CalculationCreator()
        http_creator = HttpRequestCreator()
        custom_creator = CustomToolCreator()

        # Register by tool names
        for tool_name in web_search_creator.get_tool_names():
            self._creators[tool_name] = web_search_creator

        for tool_name in database_creator.get_tool_names():
            self._creators[tool_name] = database_creator

        for tool_name in file_system_creator.get_tool_names():
            self._creators[tool_name] = file_system_creator

        for tool_name in calculation_creator.get_tool_names():
            self._creators[tool_name] = calculation_creator

        for tool_name in http_creator.get_tool_names():
            self._creators[tool_name] = http_creator

        for tool_name in custom_creator.get_tool_names():
            self._creators[tool_name] = custom_creator

        logger.info(
            f"[TOOL-FACTORY] Registered {len(self._creators)} default tool creators"
        )

    def create_tool(
        self, tool_name: str, config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseTool]:
        """
        Create a tool instance with caching and validation.

        Args:
            tool_name: Name of the tool to create
            config: Optional configuration for the tool

        Returns:
            Tool instance or None if creation fails
        """
        config = config or {}

        # Check cache first
        if self._cache:
            cache_key = self._cache.generate_key(tool_name, config)
            cached_tool = self._cache.get(cache_key)
            if cached_tool:
                logger.debug(f"[TOOL-FACTORY] Using cached tool: {tool_name}")
                return cached_tool

        # Validate configuration
        try:
            ConfigValidator.validate_config(tool_name, config)
        except Exception as e:
            logger.error(
                f"[TOOL-FACTORY] Configuration validation failed for '{tool_name}': {e}"
            )
            return None

        # Try to create with registered creator
        tool = self._create_with_creator(tool_name, config)

        # If creator failed, try custom creation function
        if tool is None and tool_name in self._custom_creation_functions:
            tool = self._create_with_custom_function(tool_name, config)

        # If still failed, try custom creator with connected_node_id
        if tool is None and "connected_node_id" in config:
            tool = self._create_custom_tool(tool_name, config)

        # Cache if successful
        if tool and self._cache:
            cache_key = self._cache.generate_key(tool_name, config)
            self._cache.set(cache_key, tool)
            logger.info(f"[TOOL-FACTORY] Created and cached tool: {tool_name}")
        elif tool:
            logger.info(f"[TOOL-FACTORY] Created tool: {tool_name}")
        else:
            logger.warning(f"[TOOL-FACTORY] Failed to create tool: {tool_name}")

        return tool

    def _create_with_creator(
        self, tool_name: str, config: Dict[str, Any]
    ) -> Optional[BaseTool]:
        """
        Create tool using registered creator.

        Args:
            tool_name: Name of the tool
            config: Tool configuration

        Returns:
            Tool instance or None if failed
        """
        if tool_name not in self._creators:
            return None

        try:
            creator = self._creators[tool_name]
            tool = creator.create(tool_name, config)
            return tool
        except Exception as e:
            logger.error(f"[TOOL-FACTORY] Creator failed for '{tool_name}': {e}")
            return None

    def _create_with_custom_function(
        self, tool_name: str, config: Dict[str, Any]
    ) -> Optional[BaseTool]:
        """
        Create tool using custom creation function.

        Args:
            tool_name: Name of the tool
            config: Tool configuration

        Returns:
            Tool instance or None if failed
        """
        try:
            creation_func = self._custom_creation_functions[tool_name]
            tool = creation_func(config)
            return tool
        except Exception as e:
            logger.error(
                f"[TOOL-FACTORY] Custom creation function failed for '{tool_name}': {e}"
            )
            return None

    def _create_custom_tool(
        self, tool_name: str, config: Dict[str, Any]
    ) -> Optional[BaseTool]:
        """
        Create a custom/connected tool.

        Args:
            tool_name: Name of the custom tool
            config: Tool configuration

        Returns:
            Tool instance or None if failed
        """
        try:
            custom_creator = CustomToolCreator()
            tool = custom_creator.create(tool_name, config)
            return tool
        except Exception as e:
            logger.error(
                f"[TOOL-FACTORY] Custom tool creation failed for '{tool_name}': {e}"
            )
            return None

    def register_custom_tool(self, name: str, creation_func: Callable) -> None:
        """
        Register a custom tool creation function.

        Args:
            name: Tool name
            creation_func: Function that creates the tool from config
        """
        self._custom_creation_functions[name] = creation_func
        logger.info(f"[TOOL-FACTORY] Registered custom tool creation function: {name}")

    def clear_cache(self) -> None:
        """Clear the tool cache."""
        if self._cache:
            self._cache.clear()
            logger.info("[TOOL-FACTORY] Tool cache cleared")

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get cache statistics.

        Returns:
            Cache statistics or None if caching disabled
        """
        if self._cache:
            return self._cache.get_stats()
        return None

    def get_supported_tools(self) -> list[str]:
        """
        Get list of all supported tool names.

        Returns:
            List of tool name strings
        """
        supported = list(self._creators.keys())
        supported.extend(self._custom_creation_functions.keys())
        return sorted(set(supported))
