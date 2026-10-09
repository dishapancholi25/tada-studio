"""Configuration and constants for delegation service.

This module contains constants, configuration values, and utility functions
for the delegation service.
"""

from backend.models.workflow import EnhancedNodeData

# Execution configuration
DELEGATION_TIMEOUT_SECONDS = 300  # 5 minutes
DEFAULT_EXECUTION_ORDER = 0

# Logging prefixes
LOG_PREFIX_DELEGATION = "[DELEGATION]"
LOG_PREFIX_SUBAGENT_STORE = "[SUBAGENT_STORE]"
LOG_PREFIX_SUBWORKFLOW = "[SUBWORKFLOW]"
LOG_PREFIX_SUBWORKFLOW_STORE = "[SUBWORKFLOW_STORE]"
LOG_PREFIX_HANDOFF = "[HANDOFF]"


def generate_tool_name(
    agent_node: EnhancedNodeData, prefix: str = "delegate_to"
) -> str:
    """Generate a standardized tool name for an agent.

    Args:
        agent_node: The agent node
        prefix: Prefix for the tool name (default: "delegate_to")

    Returns:
        Standardized tool name
    """
    return f"{prefix}_{agent_node.name.lower().replace(' ', '_')}"


def generate_tool_description(agent_node: EnhancedNodeData) -> str:
    """Generate a description for a delegation tool.

    Args:
        agent_node: The agent node

    Returns:
        Tool description
    """
    # Use delegation_description if this is a sub-agent
    if agent_node.is_sub_agent and agent_node.delegation_description:
        return agent_node.delegation_description

    # Otherwise, generate from node description
    agent_desc = agent_node.description or "specialized agent"
    return f"Delegate task to {agent_node.name} - {agent_desc}"


def generate_task_id(execution_id: str, agent_id: str) -> str:
    """Generate a task ID for delegation tracking.

    Args:
        execution_id: Parent execution ID
        agent_id: Agent node ID

    Returns:
        Task ID string
    """
    return f"task_{execution_id}_{agent_id}"
