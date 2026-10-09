"""
HTTP request tool creators.

Handles creation of HTTP/API request tools.
"""

from typing import Any, Dict

from langchain_core.tools import BaseTool

from ...config import get_logger
from .base import BaseToolCreator


logger = get_logger("tool-creators")


class HttpRequestCreator(BaseToolCreator):
    """Creator for HTTP request tools."""

    def get_tool_names(self) -> list[str]:
        """Get list of HTTP request tool names."""
        return ["http_request"]

    def create(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        """
        Create an HTTP request tool.

        Args:
            tool_name: Name of the HTTP tool
            config: Tool configuration

        Returns:
            Configured HTTP request tool

        Raises:
            ValueError: If tool_name is unknown
        """
        if tool_name == "http_request":
            return self._create_http_request_tool(config)
        else:
            raise ValueError(f"Unknown HTTP tool: {tool_name}")

    def _create_http_request_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create an HTTP request tool.

        Args:
            config: Tool configuration

        Returns:
            HTTP request tool instance
        """
        try:
            from ....tools.http_request import create_http_request_tool

            return create_http_request_tool(
                url_template=self.get_config_value(config, "url_template", ""),
                method=self.get_config_value(config, "method", "GET"),
                timeout_seconds=self.get_config_value(config, "timeout", 30),
                max_retries=self.get_config_value(config, "max_retries", 3),
                node_id=self.get_config_value(config, "node_id", ""),
                node_name=self.get_config_value(config, "node_name", "HTTP Request"),
            )
        except Exception as e:
            logger.error(f"[HTTP-CREATOR] Failed to create http_request: {e}")
            raise
