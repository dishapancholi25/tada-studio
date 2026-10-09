"""Handle different execution statuses during reconnection."""

from typing import List, Optional

from ....models import GraphExecution, NodeExecution
from ....services.config import get_logger


logger = get_logger("websocket_reconnection")


async def handle_paused_status(
    notifier,
    execution_id: str,
    node_executions: List[NodeExecution],
    thread_id: Optional[str],
    db_execution_id: str,
):
    """
    Handle reconnection for paused execution.

    Args:
        notifier: WebSocketExecutionNotifier instance
        execution_id: Execution ID
        node_executions: List of node executions
        thread_id: Thread ID
        db_execution_id: Database execution ID
    """
    # Find paused checkpoint or review node
    checkpoint_node = next(
        (
            n
            for n in node_executions
            if n.node_type in ("CHECKPOINT", "REVIEW") and n.status == "paused"
        ),
        None,
    )

    if checkpoint_node and checkpoint_node.node_metadata:
        await notifier.on_execution_paused(
            execution_id,
            {
                "checkpoint_id": checkpoint_node.node_metadata.get("checkpoint_id"),
                "thread_id": thread_id,
                "node_id": checkpoint_node.node_id,
                "prompt": checkpoint_node.node_metadata.get("prompt"),
                "db_execution_id": db_execution_id,
            },
        )


async def handle_running_status(manager, execution_id: str):
    """
    Handle reconnection for running execution.

    Args:
        manager: ConnectionManager instance
        execution_id: Execution ID
    """
    logger.info(
        f"[RECONNECT] Execution is running, sending status update for: {execution_id}"
    )
    await manager.send_execution_status(
        execution_id, "running", {"message": "Execution resumed and running"}
    )


async def handle_completed_status(
    manager, execution_id: str, execution: GraphExecution
):
    """
    Handle reconnection for completed execution.

    Args:
        manager: ConnectionManager instance
        execution_id: Execution ID
        execution: GraphExecution object
    """
    logger.info(
        f"[RECONNECT] Execution is completed, sending status update for: {execution_id}"
    )
    await manager.send_execution_status(
        execution_id, "completed", execution.output_data
    )
