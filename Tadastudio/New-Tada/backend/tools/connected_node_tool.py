"""
Connected Node Tool - Execute graph nodes as tools.

This module provides a tool that allows one node in the graph to invoke
another node as if it were a tool, enabling node composition and reuse.
"""

import logging
from typing import Any, Dict, Optional

from langchain_core.tools import BaseTool
from pydantic import Field


logger = logging.getLogger(__name__)


class ConnectedNodeTool(BaseTool):
    """Tool for executing a connected node in the graph.

    This tool wraps a graph node, allowing it to be called as a tool
    by other agents or nodes in the workflow.
    """

    name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of what the tool does")
    node_id: str = Field(description="Unique ID of the connected node to execute")
    node_type: str = Field(
        default="TOOL", description="Type of the connected node (TOOL, AGENT, etc.)"
    )

    def _run(
        self,
        query: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Execute the connected node synchronously.

        Args:
            query: Optional query string input
            input_data: Optional structured input data
            **kwargs: Additional arguments passed to the node

        Returns:
            Result from the connected node execution
        """
        logger.info(
            f"[CONNECTED-NODE-TOOL] Executing connected node {self.node_id} ({self.name})"
        )

        try:
            # Prepare input for the connected node
            node_input = {}
            if query:
                node_input["query"] = query
            if input_data:
                node_input.update(input_data)
            node_input.update(kwargs)

            # TODO: This is a placeholder implementation
            # The actual execution should integrate with the graph executor
            # and properly execute the connected node within the workflow context
            #
            # For now, we return a message indicating the tool needs proper integration
            # with the graph execution system.

            logger.warning(
                f"[CONNECTED-NODE-TOOL] Connected node tool {self.name} "
                f"requires integration with graph executor for node {self.node_id}"
            )

            return (
                f"Connected node tool '{self.name}' (node_id: {self.node_id}) "
                f"invoked with input: {node_input}. "
                f"Note: Full execution requires graph executor integration."
            )

        except Exception as e:
            error_msg = f"Failed to execute connected node {self.node_id}: {str(e)}"
            logger.error(f"[CONNECTED-NODE-TOOL] {error_msg}", exc_info=True)
            return f"Error: {error_msg}"

    async def _arun(
        self,
        query: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Execute the connected node asynchronously.

        Args:
            query: Optional query string input
            input_data: Optional structured input data
            **kwargs: Additional arguments passed to the node

        Returns:
            Result from the connected node execution
        """
        logger.info(
            f"[CONNECTED-NODE-TOOL] Async executing connected node {self.node_id} ({self.name})"
        )

        try:
            # Prepare input for the connected node
            node_input = {}
            if query:
                node_input["query"] = query
            if input_data:
                node_input.update(input_data)
            node_input.update(kwargs)

            # TODO: This is a placeholder implementation
            # The actual execution should integrate with the graph executor
            # and properly execute the connected node within the workflow context

            logger.warning(
                f"[CONNECTED-NODE-TOOL] Connected node tool {self.name} "
                f"requires integration with graph executor for node {self.node_id}"
            )

            return (
                f"Connected node tool '{self.name}' (node_id: {self.node_id}) "
                f"invoked with input: {node_input}. "
                f"Note: Full execution requires graph executor integration."
            )

        except Exception as e:
            error_msg = f"Failed to execute connected node {self.node_id}: {str(e)}"
            logger.error(f"[CONNECTED-NODE-TOOL] {error_msg}", exc_info=True)
            return f"Error: {error_msg}"


def create_connected_node_tool(
    name: str,
    node_id: str,
    node_type: str = "TOOL",
    description: Optional[str] = None,
) -> ConnectedNodeTool:
    """Factory function to create a connected node tool.

    Args:
        name: Name of the tool
        node_id: Unique ID of the node to connect
        node_type: Type of the node (TOOL, AGENT, etc.)
        description: Optional description of what the tool does

    Returns:
        Configured ConnectedNodeTool instance
    """
    if description is None:
        description = f"Execute {name}"

    return ConnectedNodeTool(
        name=name,
        node_id=node_id,
        node_type=node_type,
        description=description,
    )


__all__ = [
    "ConnectedNodeTool",
    "create_connected_node_tool",
]
