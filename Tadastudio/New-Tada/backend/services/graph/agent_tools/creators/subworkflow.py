"""Subworkflow tool creator for agents.

This module creates subworkflow tool instances that agents can use
to delegate tasks to other workflows.
"""

from typing import Any, Optional

from backend.models.workflow import EnhancedNodeData, NodeType, SubWorkflowConfig
from backend.services.config import get_logger


logger = get_logger(__name__)


def create_subworkflow_tool_from_node(
    target_node: EnhancedNodeData,
    orchestrator_id: str,
    delegation_factory: Any,
    user_id: Optional[str] = None,
) -> Optional[Any]:
    """
    Create a subworkflow delegation tool from a SUBWORKFLOW node.

    Args:
        target_node: The SUBWORKFLOW node configuration
        orchestrator_id: ID of the orchestrating agent
        delegation_factory: AgentDelegationToolFactory instance

    Returns:
        Subworkflow tool instance, or None if configuration is invalid
    """
    if target_node.type != NodeType.SUBWORKFLOW:
        logger.warning(f"Node {target_node.name} is not a SUBWORKFLOW node")
        return None

    logger.info(f"Creating subworkflow tool from node: {target_node.name}")

    # Get or create the subworkflow configuration
    if not target_node.subworkflow_config:
        # Create a default configuration if none exists
        target_node.subworkflow_config = SubWorkflowConfig(
            workflow_name=target_node.name or "Subworkflow",
            delegation_description=target_node.description
            or f"Execute {target_node.name} workflow",
        )
        logger.info(f"Created default subworkflow_config for {target_node.name}")

    # Create the subworkflow tool using the delegation factory
    subworkflow_tool = delegation_factory.create_subworkflow_tool(
        subworkflow_node=target_node,
        orchestrator_id=orchestrator_id,
        parent_user_id=user_id,
    )

    if subworkflow_tool:
        logger.info(f"Created subworkflow tool: {target_node.name}")
    else:
        logger.warning(f"Failed to create tool for subworkflow: {target_node.name}")

    return subworkflow_tool
