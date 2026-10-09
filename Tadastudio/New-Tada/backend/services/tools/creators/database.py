"""
Database tool creators.

Handles creation of database query tools with proper configuration
and validation.
"""

from typing import Any, Dict

from langchain_core.tools import BaseTool

from ...config import get_logger
from .base import BaseToolCreator


logger = get_logger("tool-creators")


class DatabaseCreator(BaseToolCreator):
    """Creator for database query tools."""

    def get_tool_names(self) -> list[str]:
        """Get list of database tool names."""
        return ["database_query"]

    def create(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        """
        Create a database query tool.

        Args:
            tool_name: Name of the database tool
            config: Tool configuration

        Returns:
            Configured database tool

        Raises:
            ValueError: If tool_name is unknown
        """
        if tool_name == "database_query":
            return self._create_database_query_tool(config)
        else:
            raise ValueError(f"Unknown database tool: {tool_name}")

    def _create_database_query_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a database query tool.

        Args:
            config: Tool configuration

        Returns:
            Database query tool instance
        """
        try:
            from ....tools.database_query import create_database_query_tool

            return create_database_query_tool(
                connection_id=self.get_config_value(config, "connection_id", ""),
                table_names=self.get_config_value(config, "table_names", []),
                allowed_operations=self.get_config_value(
                    config, "allowed_operations", ["SELECT"]
                ),
                max_rows=self.get_config_value(config, "max_rows", 100),
                timeout_seconds=self.get_config_value(config, "timeout_seconds", 30),
                enable_read_only=self.get_config_value(
                    config, "enable_read_only", False
                ),
                return_format=self.get_config_value(config, "return_format", "json"),
                include_schema=self.get_config_value(config, "include_schema", True),
                tool_name=self.get_config_value(config, "tool_name", None),
            )
        except Exception as e:
            logger.error(f"[DATABASE-CREATOR] Failed to create database_query: {e}")
            raise
