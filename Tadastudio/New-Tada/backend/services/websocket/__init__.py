"""WebSocket services for real-time execution updates."""

from .connection_manager import ConnectionManager
from .http_listener_manager import HTTPListenerManager
from .notifier import WebSocketExecutionNotifier


# Create global instances
connection_manager = ConnectionManager()
http_listener_manager = HTTPListenerManager()
notifier = WebSocketExecutionNotifier(connection_manager)


# Create combined manager for backward compatibility
class CombinedManager:
    """Combined manager that delegates to specialized managers."""

    def __init__(
        self, connection_mgr: ConnectionManager, http_mgr: HTTPListenerManager
    ):
        self._connection_mgr = connection_mgr
        self._http_mgr = http_mgr

    # Delegate connection methods
    async def connect(self, websocket, execution_id=None):
        return await self._connection_mgr.connect(websocket, execution_id)

    def disconnect(self, websocket, execution_id=None):
        return self._connection_mgr.disconnect(websocket, execution_id)

    async def send_execution_update(self, execution_id, event_type, data):
        return await self._connection_mgr.send_execution_update(
            execution_id, event_type, data
        )

    async def send_node_update(self, *args, **kwargs):
        return await self._connection_mgr.send_node_update(*args, **kwargs)

    async def send_execution_status(self, *args, **kwargs):
        return await self._connection_mgr.send_execution_status(*args, **kwargs)

    async def broadcast(self, message):
        return await self._connection_mgr.broadcast(message)

    async def replay_from_sequence(self, websocket, execution_id, last_sequence):
        return await self._connection_mgr.replay_from_sequence(
            websocket, execution_id, last_sequence
        )

    def register_pending(self, execution_id, user_identifier, ttl=30):
        return self._connection_mgr.register_pending(
            execution_id, user_identifier, ttl
        )

    def get_pending(self, execution_id):
        return self._connection_mgr.get_pending(execution_id)

    def consume_pending(self, execution_id):
        return self._connection_mgr.consume_pending(execution_id)

    def cleanup_execution(self, execution_id):
        return self._connection_mgr.cleanup_execution(execution_id)

    def get_buffer_stats(self, execution_id):
        return self._connection_mgr.get_buffer_stats(execution_id)

    # Delegate HTTP listener methods
    async def connect_http_listener(self, websocket, graph_name=None):
        return await self._http_mgr.connect_http_listener(websocket, graph_name)

    def disconnect_http_listener(self, websocket, graph_name=None):
        return self._http_mgr.disconnect_http_listener(websocket, graph_name)

    async def broadcast_http_execution_start(
        self, execution_id, graph_name, input_data
    ):
        return await self._http_mgr.broadcast_http_execution_start(
            execution_id, graph_name, input_data
        )


# Create combined manager instance
manager = CombinedManager(connection_manager, http_listener_manager)

__all__ = [
    "ConnectionManager",
    "HTTPListenerManager",
    "WebSocketExecutionNotifier",
    "manager",
    "notifier",
]
