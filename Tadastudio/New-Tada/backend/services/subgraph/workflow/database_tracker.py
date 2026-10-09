"""
Database tracking for workflow subgraph execution.

This module handles creating and updating database execution records
for sub-workflows during subgraph execution.
"""

from typing import Any, Dict, List, Optional

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.execution.history import ExecutionHistoryService
from backend.services.common.utils.websocket_notifier import (
    send_node_complete_notification,
    send_node_start_notification,
)
from backend.services.config import get_logger


workflow_db_tracker_logger = get_logger("subgraph.workflow.db_tracker")


async def create_workflow_execution_record(
    workflow_node: EnhancedNodeData,
    workflow_name: str,
    parent_db_execution_id: Optional[str],
    parent_node_id: str,
    execution_order: int,
    task_description: str,
    workflow_input: Dict[str, Any],
) -> Optional[int]:
    """
    Create a database execution record for a sub-workflow.

    Args:
        workflow_node: The workflow node being executed
        workflow_name: Display name of the workflow
        parent_db_execution_id: Parent graph's database execution ID
        parent_node_id: Parent orchestrator's node ID
        execution_order: Current execution order
        task_description: The task being performed
        workflow_input: Additional workflow input parameters

    Returns:
        The database node execution ID, or None if creation failed
    """
    if not parent_db_execution_id:
        workflow_db_tracker_logger.debug(
            f"No parent DB execution ID, skipping record creation for {workflow_name}"
        )
        return None

    try:
        workflow_db_tracker_logger.info(
            f"[SUBWORKFLOW DB] Creating workflow execution for {workflow_name}"
        )

        # Look up the parent agent's node_execution_id so the subworkflow
        # is nested under its parent in the trace tree
        parent_node_exec_id = None
        if parent_db_execution_id and parent_node_id:
            try:
                parent_exec = ExecutionHistoryService.get_node_execution_by_node_id(
                    parent_db_execution_id, parent_node_id
                )
                if parent_exec:
                    parent_node_exec_id = parent_exec.get("id")
                    workflow_db_tracker_logger.info(
                        f"[SUBWORKFLOW DB] Found parent node_execution_id: {parent_node_exec_id}"
                    )
            except Exception as e:
                workflow_db_tracker_logger.debug(
                    f"Could not look up parent node execution: {e}"
                )

        node_exec = ExecutionHistoryService.create_node_execution(
            graph_execution_id=parent_db_execution_id,
            node_id=workflow_node.uniq_id,
            node_name=workflow_name,
            node_type=NodeType.SUBWORKFLOW.value,
            execution_order=execution_order,
            input_data={
                "task": task_description,
                "workflow_input": workflow_input,
                "parent_node_id": parent_node_id,
            },
            is_sub_agent=False,
            parent_agent_id=parent_node_exec_id,
        )

        node_exec_id = node_exec["id"]
        ExecutionHistoryService.start_node_execution(node_exec_id)

        workflow_db_tracker_logger.info(
            f"Created workflow execution record: {node_exec_id}"
        )
        return node_exec_id

    except Exception as e:
        workflow_db_tracker_logger.error(
            f"Failed to create workflow execution record: {e}"
        )
        return None


async def complete_workflow_execution_record(
    node_exec_id: Optional[int],
    workflow_name: str,
    workflow_output: str,
    nodes_executed: List[str],
) -> bool:
    """
    Complete a database execution record for a sub-workflow.

    Args:
        node_exec_id: The database node execution ID
        workflow_name: Display name of the workflow
        workflow_output: The workflow's output
        nodes_executed: List of node names executed

    Returns:
        True if update succeeded, False otherwise
    """
    if not node_exec_id:
        workflow_db_tracker_logger.debug(
            f"No node execution ID, skipping completion for {workflow_name}"
        )
        return False

    try:
        output_data = {
            "workflow_output": workflow_output,
            "nodes_executed": nodes_executed,
        }

        ExecutionHistoryService.complete_node_execution(
            node_execution_id=node_exec_id,
            status="completed",
            output_data=output_data,
        )

        workflow_db_tracker_logger.info(
            f"Completed workflow execution record: {node_exec_id}"
        )
        return True

    except Exception as e:
        workflow_db_tracker_logger.error(f"Failed to complete workflow execution: {e}")
        return False


async def fail_workflow_execution_record(
    node_exec_id: Optional[int],
    workflow_name: str,
    error: str,
) -> bool:
    """
    Mark a database execution record as failed for a sub-workflow.

    Args:
        node_exec_id: The database node execution ID
        workflow_name: Display name of the workflow
        error: The error message

    Returns:
        True if update succeeded, False otherwise
    """
    if not node_exec_id:
        workflow_db_tracker_logger.debug(
            f"No node execution ID, skipping failure for {workflow_name}"
        )
        return False

    try:
        ExecutionHistoryService.complete_node_execution(
            node_execution_id=node_exec_id,
            status="failed",
            output_data={"error": error},
        )

        workflow_db_tracker_logger.info(
            f"Marked workflow execution as failed: {node_exec_id}"
        )
        return True

    except Exception as e:
        workflow_db_tracker_logger.error(
            f"Failed to update error status for {workflow_name}: {e}"
        )
        return False


async def create_end_node_record(
    node: EnhancedNodeData,
    parent_db_execution_id: str,
    parent_node_id: str,
    parent_execution_id: str,
    workflow_output: str,
    parent_node_exec_id: Any = None,
) -> bool:
    """
    Create a database record for an END node in the workflow.

    Args:
        node: The END node
        parent_db_execution_id: Parent graph's database execution ID
        parent_node_id: Parent orchestrator's node ID
        parent_execution_id: Parent execution ID for WebSocket notifications
        workflow_output: The final workflow output

    Returns:
        True if creation succeeded, False otherwise
    """
    try:
        workflow_db_tracker_logger.info(
            f"[SUBWORKFLOW END] Creating DB record for END node {node.name}"
        )

        # Create the END node record
        node_exec = ExecutionHistoryService.create_node_execution(
            graph_execution_id=parent_db_execution_id,
            node_id=node.uniq_id,
            node_name=node.name,
            node_type=node.type.value,
            is_sub_agent=False,
            parent_agent_id=parent_node_exec_id,
            input_data={
                "workflow_output": workflow_output,
                "parent_node_id": parent_node_id,
            },
        )

        node_exec_id = node_exec["id"]

        # Send start notification
        await send_node_start_notification(
            execution_id=parent_execution_id,
            node_id=node.uniq_id,
            node_name=node.name,
            node_type=node.type.value,
            is_sub_agent=False,
            parent_agent_id=parent_node_id,
            database_node_id=node_exec_id,
        )

        # Start and immediately complete the END node (it executes instantly)
        ExecutionHistoryService.start_node_execution(node_exec_id)
        ExecutionHistoryService.complete_node_execution(
            node_execution_id=node_exec_id,
            status="completed",
            output_data={"workflow_output": workflow_output},
        )

        # Send complete notification
        await send_node_complete_notification(
            execution_id=parent_execution_id,
            node_id=node.uniq_id,
            node_name=node.name,
            output={"workflow_output": workflow_output},
            node_type=node.type.value,
            duration_seconds=0.0,  # END node executes instantly
            is_sub_agent=False,
            parent_agent_id=parent_node_id,
            database_node_id=node_exec_id,
        )

        workflow_db_tracker_logger.info(
            "[SUBWORKFLOW END] Created DB record for END node"
        )
        return True

    except Exception as e:
        workflow_db_tracker_logger.error(
            f"[SUBWORKFLOW END] Failed to create DB record for END node: {e}"
        )
        return False
