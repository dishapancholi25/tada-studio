"""WebSocket endpoint for real-time trace updates."""

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.api.auth.dependencies import get_current_user_ws
from backend.services.authorization import require_execution_access

from ...services.config import get_logger
from ...services.execution.history import ExecutionHistoryService
from ...services.trace import TraceTreeBuilder

logger = get_logger("websocket_trace")

websocket_router = APIRouter(prefix="/api/trace", tags=["trace"])


@websocket_router.websocket("/{execution_id}/stream")
async def stream_trace_updates(websocket: WebSocket, execution_id: str):
    """Stream real-time trace updates via WebSocket."""
    await websocket.accept()

    user = await get_current_user_ws(websocket)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        require_execution_access(user, execution_id)
    except HTTPException:
        await websocket.close(code=4003, reason="Forbidden")
        return

    try:
        # Subscribe to updates for this execution
        async def send_updates():
            while True:
                try:
                    # Get latest execution state
                    execution_data = ExecutionHistoryService.get_graph_execution_dict(
                        execution_id
                    )
                    if execution_data:
                        trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
                        await websocket.send_json(
                            {"type": "trace_update", "data": trace_tree}
                        )

                    # Wait before next update
                    await asyncio.sleep(1)  # Send updates every second

                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error sending trace update: {e}")
                    break

        # Start sending updates
        await send_updates()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for execution {execution_id}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
