"""Handoff tool creation for agent-to-agent transfers.

This module provides functionality for creating handoff tools that follow
the LangGraph pattern for agent handoff.
"""

from typing import Any, Dict, Optional

from langchain_core.tools import Tool

from backend.services.config import get_logger

logger = get_logger("delegation.factory.handoff")


def create_handoff_tool(
    agent_name: str, agent_id: str, description: Optional[str] = None
) -> Tool:
    """Create a handoff tool following LangGraph's pattern.

    This creates a tool that returns a Command object for proper
    agent handoff in LangGraph workflows.

    Args:
        agent_name: Name of the agent to hand off to
        agent_id: Unique ID of the agent node
        description: Optional tool description

    Returns:
        Tool that performs handoff
    """
    tool_name = f"transfer_to_{agent_name.lower().replace(' ', '_')}"

    if not description:
        description = f"Transfer control to {agent_name} agent"

    logger.info(
        f"Creating handoff tool: {tool_name} for agent {agent_name} ({agent_id})"
    )

    def handoff_func(
        task: str, state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform handoff to another agent.

        Args:
            task: Task description for the target agent
            state: Optional state to pass along

        Returns:
            Command-like dict for handoff
        """
        logger.info("=== HANDOFF ===")
        logger.info(f"Target agent: {agent_name} ({agent_id})")
        logger.info(f"Task: {task}")

        # Return a command-like structure
        # In actual LangGraph integration, this would return a Command object
        return {
            "type": "handoff",
            "goto": agent_id,
            "agent_name": agent_name,
            "task": task,
            "state": state or {},
        }

    tool = Tool(name=tool_name, description=description, func=handoff_func)

    logger.info(f"Created handoff tool: {tool_name}")
    return tool
