"""Output storage for delegated executions.

This module provides utilities for storing and retrieving outputs
from sub-agents and sub-workflows.
"""

from typing import Any, Dict, Optional

from backend.services.config import get_logger

logger = get_logger("delegation.storage")


def store_subagent_output(
    graph_manager,
    execution_id: str,
    agent_node_id: str,
    agent_node_name: str,
    response: Optional[str],
    structured_output: Optional[Dict[str, Any]] = None,
) -> None:
    """Store subagent output for later retrieval.

    Args:
        graph_manager: GraphManager instance for storage
        execution_id: Parent execution ID
        agent_node_id: Agent node ID
        agent_node_name: Agent node name
        response: Raw response text
        structured_output: Structured output dictionary
    """
    if not graph_manager or not execution_id:
        logger.debug("No graph_manager or execution_id, skipping storage")
        return

    # Initialize storage if needed
    if not hasattr(graph_manager, "_subagent_outputs"):
        graph_manager._subagent_outputs = {}
    if execution_id not in graph_manager._subagent_outputs:
        graph_manager._subagent_outputs[execution_id] = {}

    # Store the subagent's output with its node ID
    output_data = {
        "raw": response,
        "structured": structured_output,
        "fields": structured_output or {},
    }
    graph_manager._subagent_outputs[execution_id][agent_node_id] = output_data

    logger.info(
        f"[SUBAGENT_STORE] Stored output for {agent_node_name} (ID: {agent_node_id})"
    )
    logger.debug(
        f"[SUBAGENT_STORE] Execution ID: {execution_id}, "
        f"Output preview: {str(response)[:200] if response else 'None'}"
    )


def store_subworkflow_output(
    graph_manager,
    execution_id: str,
    workflow_node_id: str,
    workflow_name: str,
    response: Optional[str],
    structured_output: Optional[Dict[str, Any]] = None,
    nodes_executed: Optional[list] = None,
) -> None:
    """Store subworkflow output for later retrieval.

    Args:
        graph_manager: GraphManager instance for storage
        execution_id: Parent execution ID
        workflow_node_id: Workflow node ID
        workflow_name: Workflow name
        response: Raw response text
        structured_output: Structured output dictionary
        nodes_executed: List of nodes executed in the workflow
    """
    if not graph_manager or not execution_id:
        logger.debug("No graph_manager or execution_id, skipping storage")
        return

    # Initialize storage if needed
    if not hasattr(graph_manager, "_subworkflow_outputs"):
        graph_manager._subworkflow_outputs = {}
    if execution_id not in graph_manager._subworkflow_outputs:
        graph_manager._subworkflow_outputs[execution_id] = {}

    # Store the workflow's output with its node ID
    output_data = {
        "raw": response,
        "structured": structured_output,
        "fields": structured_output or {},
        "workflow_nodes_executed": nodes_executed or [],
    }
    graph_manager._subworkflow_outputs[execution_id][workflow_node_id] = output_data

    logger.info(
        f"[SUBWORKFLOW_STORE] Stored output for {workflow_name} "
        f"(ID: {workflow_node_id})"
    )
    logger.debug(
        f"[SUBWORKFLOW_STORE] Execution ID: {execution_id}, "
        f"Output preview: {str(response)[:200] if response else 'None'}"
    )


def retrieve_subagent_output(
    graph_manager,
    execution_id: str,
    agent_node_id: str,
) -> Optional[Dict[str, Any]]:
    """Retrieve stored subagent output.

    Args:
        graph_manager: GraphManager instance for storage
        execution_id: Parent execution ID
        agent_node_id: Agent node ID

    Returns:
        Output data dictionary or None if not found
    """
    if not hasattr(graph_manager, "_subagent_outputs"):
        return None

    outputs = graph_manager._subagent_outputs.get(execution_id, {})
    return outputs.get(agent_node_id)


def retrieve_subworkflow_output(
    graph_manager,
    execution_id: str,
    workflow_node_id: str,
) -> Optional[Dict[str, Any]]:
    """Retrieve stored subworkflow output.

    Args:
        graph_manager: GraphManager instance for storage
        execution_id: Parent execution ID
        workflow_node_id: Workflow node ID

    Returns:
        Output data dictionary or None if not found
    """
    if not hasattr(graph_manager, "_subworkflow_outputs"):
        return None

    outputs = graph_manager._subworkflow_outputs.get(execution_id, {})
    return outputs.get(workflow_node_id)
