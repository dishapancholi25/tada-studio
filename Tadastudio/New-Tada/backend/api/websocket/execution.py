"""WebSocket endpoint for real-time execution updates."""

import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.api.auth.dependencies import get_current_user_ws
from backend.services.authorization import require_execution_access
from backend.services.authorization.helpers import get_user_identifier

from ...models import GraphExecution
from ...services.config import get_logger
from ...services.database import get_db
from ...services.websocket import manager as ws_manager
from ...services.websocket import notifier as ws_notifier

logger = get_logger("websocket_execution")

execution_router = APIRouter(prefix="/api/ws", tags=["websocket"])


def _resolve_execution_for_websocket_id(execution_id: str):
    """Resolve a WebSocket execution ID to its persisted execution row."""
    with get_db() as db:
        execution = (
            db.query(GraphExecution)
            .filter(GraphExecution.websocket_execution_id == execution_id)
            .first()
        )
        if not execution:
            execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == execution_id)
                .first()
            )
        if not execution:
            return None
        return {"id": str(execution.id), "user_id": execution.user_id}


def _register_accepted_execution_websocket(websocket: WebSocket, execution_id: str):
    """Register an already accepted WebSocket with the execution manager."""
    connection_manager = ws_manager._connection_mgr
    connection_manager.all_connections.add(websocket)
    if execution_id not in connection_manager.active_connections:
        connection_manager.active_connections[execution_id] = set()
    connection_manager.active_connections[execution_id].add(websocket)


def _get_execution_status_with_nodes(execution_id: str):
    """Get execution status with node information from database."""
    from ...models import NodeExecution

    try:
        with get_db() as db:
            execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.websocket_execution_id == execution_id)
                .first()
            )

            if not execution:
                return None

            # Get node executions
            node_executions = (
                db.query(NodeExecution)
                .filter(NodeExecution.graph_execution_id == execution.id)
                .order_by(NodeExecution.execution_order)
                .all()
            )

            node_execution_payload = []
            for node in node_executions:
                node_execution_payload.append(
                    {
                        "id": node.id,
                        "node_id": node.node_id,
                        "node_name": node.node_name,
                        "node_type": node.node_type,
                        "status": node.status,
                        "execution_order": node.execution_order,
                        "start_time": node.start_time.isoformat()
                        if node.start_time
                        else None,
                        "end_time": node.end_time.isoformat()
                        if node.end_time
                        else None,
                        "duration_seconds": node.duration_seconds,
                        "input_data": node.input_data,
                        "output_data": node.output_data,
                        "error_message": node.error_message,
                        "node_metadata": node.node_metadata,
                        "is_sub_agent": node.is_sub_agent,
                        "parent_agent_id": node.parent_agent_id,
                        "input_tokens": node.input_tokens,
                        "output_tokens": node.output_tokens,
                        "total_tokens": node.total_tokens,
                        "token_metadata": node.token_metadata,
                        "llm_metadata": node.llm_metadata,
                        "message_structure": node.message_structure,
                        "tool_metadata": node.tool_metadata,
                        "orchestration_metadata": node.orchestration_metadata,
                        "memory_metadata": node.memory_metadata,
                        "environment_metadata": node.environment_metadata,
                        "prompt_cost": node.prompt_cost,
                        "completion_cost": node.completion_cost,
                        "total_cost": node.total_cost,
                        "time_to_first_token": node.time_to_first_token,
                        "tokens_per_second": node.tokens_per_second,
                        "created_at": node.created_at.isoformat()
                        if node.created_at
                        else None,
                        "updated_at": node.updated_at.isoformat()
                        if node.updated_at
                        else None,
                    }
                )

            status_payload = {
                "status": execution.status,
                "graph_name": execution.graph_name,
                "started_at": execution.start_time.isoformat()
                if execution.start_time
                else None,
                "completed_at": execution.end_time.isoformat()
                if execution.end_time
                else None,
                "db_execution_id": execution.id,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "node_name": n.node_name,
                        "status": n.status,
                        "node_type": n.node_type,
                    }
                    for n in node_executions
                ],
            }
            # Include rich node execution payload for frontends expecting detailed data
            status_payload["node_executions"] = {
                node_data["node_id"]: node_data for node_data in node_execution_payload
            }
            return status_payload
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting execution status: {e}")
        return None


@execution_router.websocket("/execution/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    """Stream real-time execution updates via WebSocket.

    Clients can connect to receive live updates for a specific execution.
    """
    logger.info(
        f"[CHECKPOINT-DEBUG] WebSocket connection attempt for execution: {execution_id}"
    )
    await websocket.accept()

    user = await get_current_user_ws(websocket)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        caller_identifier = get_user_identifier(user)
    except HTTPException:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    is_admin = bool(user.get("is_admin"))
    execution_record = await asyncio.to_thread(
        _resolve_execution_for_websocket_id, execution_id
    )
    if execution_record:
        execution_owner = execution_record.get("user_id")
        if execution_owner and execution_owner != caller_identifier and not is_admin:
            await websocket.close(code=4003, reason="Forbidden")
            return

        try:
            require_execution_access(user, execution_record["id"])
        except HTTPException:
            await websocket.close(code=4003, reason="Forbidden")
            return
    elif not is_admin:
        pending = ws_manager.get_pending(execution_id)
        if not pending:
            await websocket.close(code=4004, reason="Execution not found")
            return
        if pending.user_identifier != caller_identifier:
            await websocket.close(code=4003, reason="Forbidden")
            return

    _register_accepted_execution_websocket(websocket, execution_id)

    receive_task = None

    try:
        # Send initial status
        status = await asyncio.to_thread(_get_execution_status_with_nodes, execution_id)
        if status:
            logger.info(
                f"[CHECKPOINT-DEBUG] Sending initial status for execution: {execution_id}"
            )
            await websocket.send_json(
                {"type": "initial_status", "execution_id": execution_id, "data": status}
            )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for any message from client with timeout
                receive_task = asyncio.create_task(websocket.receive_text())
                data = await asyncio.wait_for(receive_task, timeout=30.0)

                # Try to parse as JSON first
                try:
                    message = json.loads(data)

                    # Handle JSON commands
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("type") == "pong":
                        pass  # Ignore pong responses from client
                    elif message.get("type") == "close":
                        logger.info(
                            f"[CHECKPOINT-DEBUG] Client requested close for execution: {execution_id}"
                        )
                        break
                    elif message.get("type") == "reconnect":
                        # Handle reconnection to existing execution
                        logger.info(
                            f"[RECONNECT] Received reconnect request for execution: {execution_id}"
                        )
                        thread_id = message.get("thread_id")
                        db_execution_id = message.get("db_execution_id")
                        last_seq = message.get("last_seq", 0)

                        # First replay any missed messages from the buffer
                        replayed_count = 0
                        if last_seq > 0:
                            replayed_count = await ws_manager.replay_from_sequence(
                                websocket, execution_id, last_seq
                            )
                            logger.info(
                                f"[RECONNECT] Replayed {replayed_count} missed messages for {execution_id}"
                            )

                        # Send replay_complete marker so client knows buffered replay is done
                        # This helps client distinguish between replayed and new messages
                        await websocket.send_json(
                            {
                                "type": "replay_complete",
                                "execution_id": execution_id,
                                "replayed_count": replayed_count,
                                "last_replayed_seq": last_seq + replayed_count
                                if replayed_count > 0
                                else last_seq,
                            }
                        )

                        # Then handle full reconnection for state recovery from database
                        await ws_notifier.handle_reconnect_execution(
                            websocket, execution_id, thread_id, db_execution_id
                        )
                except json.JSONDecodeError:
                    # Handle legacy plain text commands for backwards compatibility
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif data == "pong":
                        pass  # Ignore
                    elif data == "close":
                        logger.info(
                            f"[CHECKPOINT-DEBUG] Client requested close for execution: {execution_id}"
                        )
                        break
                    else:
                        logger.debug(f"Received non-JSON message: {data}")

            except asyncio.TimeoutError:
                # Send periodic ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:  # noqa: BLE001
                    logger.info(
                        f"[CHECKPOINT-DEBUG] Failed to send ping, connection likely closed for execution: {execution_id}"
                    )
                    break

    except WebSocketDisconnect:
        logger.info(
            f"[CHECKPOINT-DEBUG] WebSocket disconnected normally for execution: {execution_id}"
        )
    except asyncio.CancelledError:
        logger.warning(
            f"[CHECKPOINT-DEBUG] WebSocket task cancelled for execution: {execution_id}"
        )
        if receive_task and not receive_task.done():
            receive_task.cancel()
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(
            f"[CHECKPOINT-DEBUG] WebSocket error for execution {execution_id}: {e}"
        )
    finally:
        # Ensure proper cleanup
        ws_manager.disconnect(websocket, execution_id)
        logger.info(
            f"[CHECKPOINT-DEBUG] WebSocket cleanup completed for execution: {execution_id}"
        )
