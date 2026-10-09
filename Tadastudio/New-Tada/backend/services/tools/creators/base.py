"""
Base protocol and utilities for tool creators.

This module defines the interface that all tool creators must implement,
providing a consistent API for tool creation across different tool types.
"""

from typing import Any, Dict, Optional, Protocol

from langchain_core.tools import BaseTool


class ToolCreator(Protocol):
    """
    Protocol for tool creator implementations.

    All tool creators must implement this protocol to ensure consistent
    behavior and enable dynamic registration.

    Methods:
        create: Create a tool instance from configuration
        get_tool_names: Get list of tool names this creator can handle
    """

    def create(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a tool instance from configuration.

        Args:
            config: Configuration dictionary for the tool

        Returns:
            Configured tool instance

        Raises:
            ValueError: If configuration is invalid
            ImportError: If required dependencies are missing
        """
        ...

    def get_tool_names(self) -> list[str]:
        """
        Get list of tool names this creator can handle.

        Returns:
            List of tool name strings
        """
        ...


class BaseToolCreator:
    """
    Base class for tool creators with common utilities.

    Provides helper methods for configuration validation and error handling.
    """

    def validate_config(self, config: Dict[str, Any], required_keys: list[str]) -> None:
        """
        Validate that required configuration keys are present.

        Args:
            config: Configuration dictionary to validate
            required_keys: List of required key names

        Raises:
            ValueError: If any required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValueError(
                f"Missing required configuration keys: {', '.join(missing_keys)}"
            )

    def get_config_value(
        self, config: Dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """
        Safely get a configuration value with default fallback.

        Args:
            config: Configuration dictionary
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return config.get(key, default)

    def handle_creation_error(
        self, tool_name: str, error: Exception
    ) -> Optional[BaseTool]:
        """
        Handle tool creation errors consistently.

        Args:
            tool_name: Name of the tool being created
            error: Exception that occurred

        Returns:
            None (logs error and returns None)
        """
        from ...config import get_logger

        logger = get_logger("tool-creators")
        logger.error(f"[TOOL-CREATOR] Failed to create tool '{tool_name}': {error}")
        return None
