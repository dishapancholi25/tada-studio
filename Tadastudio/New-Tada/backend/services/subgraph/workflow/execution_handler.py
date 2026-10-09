"""
Workflow execution handler for subgraph execution.

This module contains the core logic for executing workflows within subgraphs,
coordinating node execution, database tracking, and WebSocket notifications.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.common.utils.websocket_notifier import (
    send_node_complete_notification,
    send_node_start_notification,
)
from backend.services.config import get_logger

from ..models import SubWorkflowState
from .database_tracker import (
    complete_workflow_execution_record,
    create_workflow_execution_record,
    fail_workflow_execution_record,
)
from .node_executor import execute_agent_node, process_end_node


execution_handler_logger = get_logger("subgraph.workflow.execution_handler")


async def execute_workflow_in_subgraph(
    state: SubWorkflowState,
    subworkflow_node: EnhancedNodeData,
    workflow_name: str,
    graph_manager: Any,
) -> Dict[str, Any]:
    """
    Execute a sub-workflow within a subgraph.

    Args:
        state: The current sub-workflow state
        subworkflow_node: The subworkflow node configuration
        workflow_name: Display name of the workflow
        graph_manager: The graph manager instance

    Returns:
        Updated state dictionary with execution results
    """
    execution_handler_logger.info(f"Executing sub-workflow {workflow_name}")

    start_time = datetime.now(timezone.utc)
    execution_order = state["execution_order"]

    # Create database record
    node_exec_id = await create_workflow_execution_record(
        workflow_node=subworkflow_node,
        workflow_name=workflow_name,
        parent_db_execution_id=state.get("parent_db_execution_id"),
        parent_node_id=state.get("parent_node_id"),
        execution_order=execution_order,
        task_description=state["task_description"],
        workflow_input=state.get("workflow_input", {}),
    )

    # Send start notification
    await send_node_start_notification(
        execution_id=state.get("parent_execution_id"),
        node_id=subworkflow_node.uniq_id,
        node_name=workflow_name,
        node_type=NodeType.SUBWORKFLOW.value,
        is_sub_agent=False,
        parent_agent_id=state.get("parent_node_id"),
        database_node_id=node_exec_id,
    )

    try:
        # Get the workflow nodes
        workflow_nodes = _get_workflow_nodes(subworkflow_node, graph_manager, state)

        # Execute the workflow nodes
        workflow_output, nodes_executed, current_order = await _execute_workflow_nodes(
            workflow_nodes=workflow_nodes,
            state=state,
            execution_order=execution_order,
            graph_manager=graph_manager,
            parent_node_exec_id=node_exec_id,
        )

        end_time = datetime.now(timezone.utc)

        # Complete database record
        await complete_workflow_execution_record(
            node_exec_id=node_exec_id,
            workflow_name=workflow_name,
            workflow_output=workflow_output,
            nodes_executed=nodes_executed,
        )

        # Send completion notification
        await send_node_complete_notification(
            execution_id=state.get("parent_execution_id"),
            node_id=subworkflow_node.uniq_id,
            node_name=workflow_name,
            output={
                "workflow_output": workflow_output,
                "nodes_executed": nodes_executed,
            },
            node_type=NodeType.SUBWORKFLOW.value,
            duration_seconds=(end_time - start_time).total_seconds(),
            is_sub_agent=False,
            parent_agent_id=state.get("parent_node_id"),
            database_node_id=node_exec_id,
        )

        return {
            "workflow_output": workflow_output,
            "nodes_executed": nodes_executed,
            "execution_order": current_order,
            "end_time": end_time.isoformat(),
            "error": None,
            "response": workflow_output,
        }

    except Exception as e:
        execution_handler_logger.error(
            f"Workflow execution failed: {str(e)}", exc_info=True
        )

        await fail_workflow_execution_record(node_exec_id, workflow_name, str(e))

        return {
            "error": str(e),
            "execution_order": execution_order,
            "end_time": datetime.now(timezone.utc).isoformat(),
        }


def _get_workflow_nodes(
    subworkflow_node: EnhancedNodeData,
    graph_manager: Any,
    state: SubWorkflowState,
) -> List[EnhancedNodeData]:
    """Get all nodes in the workflow by traversing from the subworkflow node.

    If subworkflow_node.subworkflow_config.target_workflow_id is set, traverses
    that saved workflow's own nodes instead of the current graph.
    """
    target_workflow_id = getattr(
        subworkflow_node.subworkflow_config, "target_workflow_id", None
    )
    graph_name = target_workflow_id or getattr(
        graph_manager, "current_graph_name", None
    )

    execution_handler_logger.info(f"Resolving workflow graph: {graph_name}")

    if not graph_name:
        execution_handler_logger.warning("No graph name resolved for subworkflow")
        return []

    # load_graph_by_workflow_id enforces access control, including shared-workflow membership
    user_id = state.get("user_id") or None
    graph_data = (
        graph_manager.load_graph_by_workflow_id(target_workflow_id, user_id)
        if target_workflow_id
        else graph_manager.get_graph(graph_name)
    )
    if not graph_data:
        execution_handler_logger.warning(f"Could not load graph {graph_name}")
        return []

    execution_handler_logger.info(
        f"Loaded graph {graph_name} with {len(graph_data.nodes)} nodes"
    )

    # A target_workflow_id run starts at that workflow's own entry node(s),
    # not subworkflow_node.nexts (which belong to the caller's graph).
    if target_workflow_id:
        nodes_to_process = []
        for start_node in (n for n in graph_data.nodes if n.type == NodeType.START):
            nodes_to_process.extend(start_node.nexts or [])
        return _traverse_workflow_nodes(graph_data, nodes_to_process)

    # Traverse nodes starting from subworkflow's nexts
    return _traverse_workflow_nodes(graph_data, list(subworkflow_node.nexts or []))


def _traverse_workflow_nodes(
    graph_data: Any, nodes_to_process: List[str]
) -> List[EnhancedNodeData]:
    """BFS-walk node IDs to their END node, collecting each node visited."""
    workflow_nodes: List[EnhancedNodeData] = []
    processed = set()

    while nodes_to_process:
        node_id = nodes_to_process.pop(0)
        if node_id in processed:
            continue
        processed.add(node_id)

        node = next((n for n in graph_data.nodes if n.uniq_id == node_id), None)
        if not node:
            execution_handler_logger.warning(f"Node {node_id} not found in graph")
            continue

        workflow_nodes.append(node)

        # Add next nodes to process (unless it's an END node)
        if node.type != NodeType.END and node.nexts:
            nodes_to_process.extend(node.nexts)

    execution_handler_logger.info(f"Workflow contains {len(workflow_nodes)} nodes")
    return workflow_nodes


async def _execute_workflow_nodes(
    workflow_nodes: List[EnhancedNodeData],
    state: SubWorkflowState,
    execution_order: int,
    graph_manager: Any,
    parent_node_exec_id: Any = None,
) -> tuple:
    """Execute all workflow nodes in sequence.

    Agent nodes are chained so each subsequent agent is nested under
    the previous one in the trace tree (parent → child delegation).
    """
    workflow_output = ""
    nodes_executed = []
    current_output = state["task_description"]
    current_order = execution_order
    # Track the current agent's exec ID so the next agent nests under it
    current_agent_exec_id = parent_node_exec_id

    for node in workflow_nodes:
        execution_handler_logger.info(
            f"[SUBWORKFLOW NODE] Executing: {node.name} ({node.type})"
        )
        current_order += 1
        nodes_executed.append(node.name)

        if node.type == NodeType.END:
            workflow_output = await process_end_node(
                node=node,
                current_output=current_output,
                parent_db_execution_id=state.get("parent_db_execution_id"),
                parent_node_id=state.get("parent_node_id"),
                parent_execution_id=state.get("parent_execution_id"),
                parent_node_exec_id=current_agent_exec_id,
            )

        elif node.type == NodeType.AGENT:
            current_output, _, agent_exec_id = await execute_agent_node(
                node=node,
                current_output=current_output,
                parent_db_execution_id=state.get("parent_db_execution_id"),
                parent_node_id=state.get("parent_node_id"),
                parent_execution_id=state.get("parent_execution_id"),
                current_order=current_order,
                graph_manager=graph_manager,
                user_id=state.get("user_id"),
                parent_node_exec_id=current_agent_exec_id,
            )
            # Next agent in the chain nests under this one
            if agent_exec_id:
                current_agent_exec_id = agent_exec_id

    return workflow_output, nodes_executed, current_order
