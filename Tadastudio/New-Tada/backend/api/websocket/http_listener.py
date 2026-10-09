"""WebSocket endpoint for HTTP execution notifications."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.api.auth.dependencies import get_current_user_ws
from backend.services.authorization import require_workflow_access

from ...services.config import get_logger
from ...services.websocket import manager as ws_manager

logger = get_logger("websocket_http_listener")

http_listener_router = APIRouter(prefix="/api/ws", tags=["websocket"])


def _register_accepted_http_listener(websocket: WebSocket, graph_name: str):
    """Register an already accepted WebSocket with the HTTP listener manager."""
    http_manager = ws_manager._http_mgr
    http_manager.all_http_listeners.add(websocket)
    if graph_name not in http_manager.http_listeners:
        http_manager.http_listeners[graph_name] = set()
    http_manager.http_listeners[graph_name].add(websocket)
    logger.info(f"HTTP listener connected for graph: {graph_name}")


@http_listener_router.websocket("/http-listener/{graph_name}")
async def websocket_http_listener(websocket: WebSocket, graph_name: str):
    """Listen for HTTP-triggered execution notifications via WebSocket.

    UI clients can connect to receive notifications when HTTP executions start.
    """
    logger.info(f"HTTP listener WebSocket connection for graph: {graph_name}")
    await websocket.accept()

    user = await get_current_user_ws(websocket)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        require_workflow_access(user, graph_name)
    except HTTPException:
        await websocket.close(code=4003, reason="Forbidden")
        return

    _register_accepted_http_listener(websocket, graph_name)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"HTTP listener disconnected for graph: {graph_name}")
        ws_manager.disconnect_http_listener(websocket, graph_name)
    except Exception as e:  # noqa: BLE001
        logger.error(f"HTTP listener error: {e}")
        ws_manager.disconnect_http_listener(websocket, graph_name)
