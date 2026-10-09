"""Subworkflow tool creation for delegation.

This module provides functionality for creating tools that execute sub-workflows.
"""

from typing import Optional

from langchain_core.tools import Tool

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.config import get_logger
from backend.services.delegation.storage import store_subworkflow_output
from backend.services.delegation.utils import run_async_in_sync_isolated
from backend.services.execution.context import (
    get_current_db_execution_id,
    get_current_execution_id,
)

logger = get_logger("delegation.factory.subworkflow")


def create_subworkflow_tool(
    subworkflow_node: EnhancedNodeData,
    orchestrator_id: str,
    graph_manager,
    description: Optional[str] = None,
    parent_execution_id: Optional[str] = None,
    parent_db_execution_id: Optional[str] = None,
    parent_user_id: Optional[str] = None,
) -> Tool:
    """Create a tool that executes a sub-workflow.

    Args:
        subworkflow_node: The SUBWORKFLOW node to wrap as a tool
        orchestrator_id: ID of the orchestrator agent
        graph_manager: GraphManager instance
        description: Optional custom description for the tool
        parent_execution_id: Parent execution ID for tracking
        parent_db_execution_id: Parent database execution ID

    Returns:
        Tool instance that can execute the sub-workflow

    Raises:
        ValueError: If subworkflow_node is not a SUBWORKFLOW type
    """
    if subworkflow_node.type != NodeType.SUBWORKFLOW:
        raise ValueError(f"Node {subworkflow_node.name} is not a SUBWORKFLOW node")

    # Get subworkflow configuration
    config = subworkflow_node.subworkflow_config

    # Generate tool name
    workflow_name = config.workflow_name if config else subworkflow_node.name
    tool_name = f"execute_{workflow_name.lower().replace(' ', '_')}_workflow"

    # Generate description if not provided
    if not description:
        if config and config.delegation_description:
            description = config.delegation_description
        else:
            description = (
                f"Execute {workflow_name} workflow - "
                f"{subworkflow_node.description or 'specialized workflow'}"
            )

    logger.info(f"Creating subworkflow tool: {tool_name} for workflow {workflow_name}")

    # Create the subworkflow execution function
    def execute_subworkflow(task_description: str, **kwargs) -> str:
        """Execute a sub-workflow with the given task and parameters.

        Args:
            task_description: Description of the task for the workflow
            **kwargs: Additional parameters to pass to the workflow

        Returns:
            Response from the workflow END node
        """
        logger.info("=== SUBWORKFLOW EXECUTION START ===")
        logger.info(f"Orchestrator: {orchestrator_id}")
        logger.info(f"Executing workflow: {workflow_name} ({subworkflow_node.uniq_id})")
        logger.info(f"Task: {task_description}")
        logger.info(f"Additional params: {kwargs}")

        try:
            # Get execution context — read before run_async_in_sync_isolated wipes contextvars
            exec_id = parent_execution_id or get_current_execution_id()
            db_exec_id = parent_db_execution_id or get_current_db_execution_id()

            logger.info(f"Execution context - ID: {exec_id}, DB ID: {db_exec_id}")

            # Build and execute subworkflow
            from backend.services.subgraph import SubgraphBuilder

            builder = SubgraphBuilder(graph_manager)

            # Get current graph name
            current_graph_name = getattr(graph_manager, "current_graph_name", None)

            # Create the subworkflow graph
            logger.info(f"Building subworkflow graph for {workflow_name}")
            subgraph = builder.create_subworkflow_graph(
                subworkflow_node=subworkflow_node, graph_name=current_graph_name
            )

            if not subgraph:
                error_msg = f"Could not build workflow graph for {workflow_name}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Prepare initial state
            initial_state = {
                "task_description": task_description,
                "workflow_input": kwargs,
                "parent_execution_id": exec_id,
                "parent_db_execution_id": db_exec_id,
                "parent_node_id": orchestrator_id,
                "parent_node_name": "orchestrator",
                "execution_order": 1,  # TODO: Get from context
                "workflow_node_id": subworkflow_node.uniq_id,
                "workflow_node_name": workflow_name,
                "user_id": parent_user_id,
                "messages": [],
            }

            logger.info(f"Executing subworkflow graph for {workflow_name}")

            # Execute the workflow with complete context isolation.
            # Uses run_async_in_sync_isolated with a lambda to defer coroutine creation
            # until inside a fresh contextvars.Context(), preventing LangChain's
            # context variables (including parent's checkpointer) from being inherited.
            result_state = run_async_in_sync_isolated(
                lambda: subgraph.ainvoke(initial_state, config={"configurable": {}})
            )

            # Check for errors
            if result_state.get("error"):
                error_msg = result_state["error"]
                logger.error(f"Subworkflow execution failed: {error_msg}")
                return f"Error executing {workflow_name}: {error_msg}"

            # Get the workflow output
            workflow_output = result_state.get("workflow_output", "")
            if not workflow_output:
                workflow_output = result_state.get("response", "")

            # Update execution order
            new_order = result_state.get("execution_order", 1)
            logger.info(f"Subworkflow completed with execution order: {new_order}")

            # Store workflow output
            if exec_id:
                store_subworkflow_output(
                    graph_manager=graph_manager,
                    execution_id=exec_id,
                    workflow_node_id=subworkflow_node.uniq_id,
                    workflow_name=workflow_name,
                    response=workflow_output,
                    structured_output=result_state.get("structured_output"),
                    nodes_executed=result_state.get("nodes_executed", []),
                )

            logger.info(f"Subworkflow {workflow_name} completed successfully")
            return (
                f"{workflow_name} workflow completed with the following result:\n\n"
                f"{workflow_output}"
            )

        except Exception as e:
            logger.error(f"Subworkflow execution error: {e}", exc_info=True)
            return f"Error in {workflow_name}: {str(e)}"

        finally:
            logger.info("=== SUBWORKFLOW EXECUTION END ===")

    # Create tool with appropriate description
    tool = Tool(name=tool_name, description=description, func=execute_subworkflow)

    logger.info(f"Created subworkflow tool: {tool_name}")
    return tool
