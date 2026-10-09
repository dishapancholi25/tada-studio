"""
Factory for creating workflow subgraphs.

This module provides the factory function that creates complete workflow subgraphs
with proper state management and execution logic.
"""

from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.config import get_logger

from ..models import SubWorkflowState
from .execution_handler import execute_workflow_in_subgraph


factory_logger = get_logger("subgraph.workflow.factory")


def create_workflow_subgraph(
    subworkflow_node: EnhancedNodeData,
    graph_manager: Any,
    graph_name: Optional[str] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> StateGraph:
    """
    Create a LangGraph subgraph for sub-workflow execution.

    This subgraph will:
    1. Start from the SUBWORKFLOW node (acts as START)
    2. Execute all connected workflow nodes
    3. Collect output from END node
    4. Track execution in the database
    5. Send WebSocket notifications
    6. Return results to parent agent

    Args:
        subworkflow_node: The SUBWORKFLOW node that starts the workflow
        graph_manager: The GraphManager instance
        graph_name: Name of the parent graph for context
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled StateGraph ready for execution

    Raises:
        ValueError: If the provided node is not a SUBWORKFLOW node
    """
    if subworkflow_node.type != NodeType.SUBWORKFLOW:
        raise ValueError(f"Node {subworkflow_node.name} is not a SUBWORKFLOW node")

    factory_logger.info(
        f"Creating subworkflow graph for: {subworkflow_node.name} "
        f"({subworkflow_node.uniq_id})"
    )

    # Get the workflow configuration
    config = subworkflow_node.subworkflow_config
    workflow_name = config.workflow_name if config else subworkflow_node.name

    # Create the state graph for the workflow
    workflow = StateGraph(SubWorkflowState)

    # Define the workflow execution node
    async def execute_workflow(state: SubWorkflowState):
        """Execute the entire sub-workflow and return results."""
        return await execute_workflow_in_subgraph(
            state=state,
            subworkflow_node=subworkflow_node,
            workflow_name=workflow_name,
            graph_manager=graph_manager,
        )

    # Add the workflow execution node to the graph
    workflow.add_node("execute_workflow", execute_workflow)

    # Set entry point and finish point
    workflow.set_entry_point("execute_workflow")
    workflow.add_edge("execute_workflow", END)

    # Compile the workflow without checkpointer
    # Subworkflows don't need checkpointers - they complete in a single invocation
    # and their state is returned to the parent graph which handles persistence.
    # Using checkpointers here causes event loop mismatch errors when subworkflows
    # are invoked via asyncio.run() in delegation contexts.
    compiled = workflow.compile(checkpointer=None)

    factory_logger.info(f"Created subworkflow graph for {workflow_name}")

    return compiled
