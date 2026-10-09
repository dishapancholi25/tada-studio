"""HTTP listener WebSocket management.

Manages WebSocket connections that listen for HTTP-triggered workflow executions.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from ...services.config import get_logger


logger = get_logger("websocket_manager")


class HTTPListenerManager:
    """Manages WebSocket connections for HTTP execution notifications."""

    def __init__(self):
        """Initialize HTTP listener manager."""
        # Track HTTP listener connections (UI clients listening for HTTP executions)
        self.http_listeners: Dict[str, Set[WebSocket]] = {}  # graph_name -> websockets
        # Track all HTTP listeners (for broadcast to all)
        self.all_http_listeners: Set[WebSocket] = set()

    async def connect_http_listener(
        self, websocket: WebSocket, graph_name: Optional[str] = None
    ):
        """Connect a WebSocket as an HTTP execution listener."""
        await websocket.accept()
        self.all_http_listeners.add(websocket)

        if graph_name:
            if graph_name not in self.http_listeners:
                self.http_listeners[graph_name] = set()
            self.http_listeners[graph_name].add(websocket)
            logger.info(f"HTTP listener connected for graph: {graph_name}")
        else:
            logger.info("HTTP listener connected for all graphs")

    def disconnect_http_listener(
        self, websocket: WebSocket, graph_name: Optional[str] = None
    ):
        """Disconnect an HTTP listener."""
        self.all_http_listeners.discard(websocket)

        if graph_name and graph_name in self.http_listeners:
            self.http_listeners[graph_name].discard(websocket)
            if not self.http_listeners[graph_name]:
                del self.http_listeners[graph_name]
        else:
            # Remove from all graph listeners
            for g_name in list(self.http_listeners.keys()):
                self.http_listeners[g_name].discard(websocket)
                if not self.http_listeners[g_name]:
                    del self.http_listeners[g_name]

    async def broadcast_http_execution_start(
        self, execution_id: str, graph_name: str, input_data: Dict[str, Any]
    ):
        """Broadcast HTTP execution start to all relevant listeners."""
        message = {
            "type": "http_execution_started",
            "execution_id": execution_id,
            "graph_name": graph_name,
            "timestamp": datetime.now().isoformat(),
            "data": {"input": input_data, "source": "http"},
        }

        message_str = json.dumps(message)
        disconnected = []

        # Send only to graph-specific listeners (no cross-workflow leaking)
        if graph_name in self.http_listeners:
            for websocket in self.http_listeners[graph_name]:
                try:
                    await websocket.send_text(message_str)
                    logger.info(
                        f"Sent HTTP execution start to listener for graph: {graph_name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send to HTTP listener: {e}")
                    disconnected.append((websocket, graph_name))
        else:
            logger.debug(f"No HTTP listeners registered for graph: {graph_name}")

        # Clean up disconnected
        for ws, g_name in disconnected:
            self.disconnect_http_listener(ws, g_name)
