"""
Custom tool creators.

Handles creation of custom and connected tools (tools that reference
other nodes in the graph).
"""

from typing import Any, Dict

from langchain_core.tools import BaseTool

from ...config import get_logger
from .base import BaseToolCreator


logger = get_logger("tool-creators")


class CustomToolCreator(BaseToolCreator):
    """Creator for custom and connected tools."""

    def get_tool_names(self) -> list[str]:
        """Get list of custom tool names."""
        return ["custom", "connected_node"]

    def create(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        """
        Create a custom tool.

        Args:
            tool_name: Name of the custom tool
            config: Tool configuration

        Returns:
            Configured custom tool

        Raises:
            ValueError: If tool_name is unknown or config is invalid
        """
        # Check if it's a connected tool node
        if "connected_node_id" in config:
            return self._create_connected_tool(tool_name, config)

        raise ValueError(f"Unable to create custom tool: {tool_name}")

    def _create_connected_tool(
        self, tool_name: str, config: Dict[str, Any]
    ) -> BaseTool:
        """
        Create a tool for a connected node in the graph.

        Args:
            tool_name: Name of the connected tool
            config: Tool configuration (must contain 'connected_node_id')

        Returns:
            Connected node tool instance

        Raises:
            ValueError: If connected_node_id is missing
        """
        try:
            if "connected_node_id" not in config:
                raise ValueError(
                    "Connected tool requires 'connected_node_id' in config"
                )

            from ....tools.connected_node_tool import ConnectedNodeTool

            return ConnectedNodeTool(
                name=tool_name,
                node_id=config["connected_node_id"],
                node_type=self.get_config_value(config, "node_type", "TOOL"),
                description=self.get_config_value(
                    config, "description", f"Execute {tool_name}"
                ),
            )
        except Exception as e:
            logger.error(
                f"[CUSTOM-CREATOR] Failed to create connected tool '{tool_name}': {e}"
            )
            raise
