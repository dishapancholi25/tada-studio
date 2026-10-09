"""
File system tool creators.

Handles creation of file reading and writing tools.
"""

from typing import Any, Dict

from langchain_core.tools import BaseTool

from ...config import get_logger
from .base import BaseToolCreator


logger = get_logger("tool-creators")


class FileSystemCreator(BaseToolCreator):
    """Creator for file system tools."""

    def get_tool_names(self) -> list[str]:
        """Get list of file system tool names."""
        return ["file_read", "file_write"]

    def create(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        """
        Create a file system tool.

        Args:
            tool_name: Name of the file system tool
            config: Tool configuration

        Returns:
            Configured file system tool

        Raises:
            ValueError: If tool_name is unknown
        """
        if tool_name == "file_read":
            return self._create_file_read_tool(config)
        elif tool_name == "file_write":
            return self._create_file_write_tool(config)
        else:
            raise ValueError(f"Unknown file system tool: {tool_name}")

    def _create_file_read_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a file read tool.

        Args:
            config: Tool configuration

        Returns:
            File read tool instance
        """
        try:
            from ....tools.file_tools import FileReadTool

            return FileReadTool(
                base_path=self.get_config_value(config, "base_path", "."),
                allowed_extensions=self.get_config_value(
                    config, "allowed_extensions", [".txt", ".json", ".yaml", ".md"]
                ),
            )
        except Exception as e:
            logger.error(f"[FILE-SYSTEM-CREATOR] Failed to create file_read: {e}")
            raise

    def _create_file_write_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a file write tool.

        Args:
            config: Tool configuration

        Returns:
            File write tool instance
        """
        try:
            from ....tools.file_tools import FileWriteTool

            return FileWriteTool(
                base_path=self.get_config_value(config, "base_path", "."),
                allowed_extensions=self.get_config_value(
                    config, "allowed_extensions", [".txt", ".json", ".yaml", ".md"]
                ),
            )
        except Exception as e:
            logger.error(f"[FILE-SYSTEM-CREATOR] Failed to create file_write: {e}")
            raise
