"""Main reconnection handler."""

from typing import Optional

from fastapi import WebSocket

from ...database import get_db
from ....services.config import get_logger
from .execution_loader import load_execution_from_db
from .node_state_sender import send_all_node_states
from .status_handler import (
    handle_completed_status,
    handle_paused_status,
    handle_running_status,
)


logger = get_logger("websocket_reconnection")


async def handle_reconnect_execution(
    manager,
    notifier,
    websocket: WebSocket,
    execution_id: str,
    thread_id: Optional[str] = None,
    db_execution_id: Optional[str] = None,
):
    """
    Handle reconnection to an existing execution.

    Args:
        manager: ConnectionManager instance
        notifier: WebSocketExecutionNotifier instance
        websocket: WebSocket connection
        execution_id: Execution ID
        thread_id: Optional thread ID
        db_execution_id: Optional database execution ID
    """
    logger.info(
        f"[RECONNECT] Handling reconnection for execution: {execution_id}, thread: {thread_id}, db_id: {db_execution_id}"
    )

    try:
        # Connect the websocket to this execution
        await manager.connect(websocket, execution_id)

        # Send current execution state if available
        if not db_execution_id:
            return

        # Get database session
        with get_db() as db:
            # Load execution from database
            result = load_execution_from_db(db, db_execution_id)
            if not result:
                return

            execution, node_executions = result

            # Send initial reconnection confirmation
            await manager.send_execution_update(
                execution_id,
                "reconnected",
                {
                    "status": execution.status,
                    "thread_id": thread_id,
                    "db_execution_id": db_execution_id,
                    "graph_name": execution.graph_name,
                },
            )

            # Send all node states
            await send_all_node_states(manager, execution_id, node_executions)

            # Handle current execution status
            if execution.status == "paused":
                await handle_paused_status(
                    notifier, execution_id, node_executions, thread_id, db_execution_id
                )
            elif execution.status == "running":
                await handle_running_status(manager, execution_id)
            elif execution.status == "completed":
                await handle_completed_status(manager, execution_id, execution)

            logger.info(
                f"[RECONNECT] Successfully sent execution state for: {execution_id} (status: {execution.status})"
            )

    except Exception as e:
        logger.error(f"[RECONNECT] Failed to handle reconnection: {e}")
        await manager.send_execution_update(
            execution_id, "reconnect_failed", {"error": str(e)}
        )
