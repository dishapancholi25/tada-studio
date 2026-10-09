"""WebSocket connection manager for real-time execution updates.

Manages active WebSocket connections and message broadcasting.
Includes message buffering for connection resilience during long workflows.
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

from ...services.config import get_logger
from .message_buffer import MessageBuffer


logger = get_logger("websocket_manager")


@dataclass(frozen=True)
class PendingRegistration:
    """Short-lived authorization marker for executions awaiting DB persistence."""

    user_identifier: str
    expires_at: float


class ConnectionManager:
    """Manages WebSocket connections for execution updates.

    Features:
    - Connection tracking by execution_id
    - Message buffering with sequence numbers for replay on reconnection
    - Automatic cleanup of disconnected clients
    - Ordered, error-logged cross-loop sends via a drain queue
    """

    _QUEUE_HIGH_WATER = 1000

    def __init__(self):
        """Initialize WebSocket connection manager."""
        # Track active connections by execution_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Track all connections
        self.all_connections: Set[WebSocket] = set()
        # Rate-limiting state for token update logs
        self._token_update_count: Dict[str, int] = {}
        self._last_token_log_time: Dict[str, float] = {}
        # Message buffering for connection resilience
        self.message_buffers: Dict[str, MessageBuffer] = {}
        self.sequence_counters: Dict[str, int] = {}
        self._buffer_lock = threading.Lock()
        self.pending_executions: Dict[str, PendingRegistration] = {}
        self._pending_lock = threading.Lock()
        # Cross-loop send support (initialized by set_main_loop)
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._send_queue: Optional[asyncio.Queue] = None
        self._drain_task: Optional[asyncio.Task] = None

    def register_pending(
        self, execution_id: str, user_identifier: str, ttl: int = 30
    ) -> None:
        """Register a short-lived execution owner before DB persistence completes."""
        expires_at = time.monotonic() + ttl
        with self._pending_lock:
            self._cleanup_expired_pending_locked()
            self.pending_executions[execution_id] = PendingRegistration(
                user_identifier=user_identifier,
                expires_at=expires_at,
            )

    def get_pending(self, execution_id: str) -> Optional[PendingRegistration]:
        """Return a pending execution registration if it exists and is unexpired."""
        with self._pending_lock:
            self._cleanup_expired_pending_locked()
            return self.pending_executions.get(execution_id)

    def consume_pending(self, execution_id: str) -> Optional[PendingRegistration]:
        """Remove and return a pending execution registration."""
        with self._pending_lock:
            self._cleanup_expired_pending_locked()
            return self.pending_executions.pop(execution_id, None)

    def _cleanup_expired_pending_locked(self) -> None:
        """Remove expired pending registrations while holding _pending_lock."""
        now = time.monotonic()
        expired = [
            execution_id
            for execution_id, registration in self.pending_executions.items()
            if registration.expires_at <= now
        ]
        for execution_id in expired:
            self.pending_executions.pop(execution_id, None)

    def set_main_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the main FastAPI event loop for cross-thread sends.

        Called once during application startup. Enables worker threads to
        route WebSocket sends through the main loop via an ordered queue.

        Args:
            loop: The main FastAPI event loop
        """
        self._main_loop = loop
        self._send_queue = asyncio.Queue()
        self._drain_task = loop.create_task(self._drain_cross_loop_sends())

    async def _drain_cross_loop_sends(self) -> None:
        """Process cross-loop sends sequentially on the main event loop.

        Guarantees message ordering and surfaces errors that would
        otherwise be silently swallowed by run_coroutine_threadsafe.
        """
        assert self._send_queue is not None
        queue = self._send_queue
        try:
            while True:
                item = await queue.get()
                try:
                    await self._do_send(*item)
                except Exception as e:
                    logger.error(f"[WS-DRAIN] Error processing queued send: {e}")
                finally:
                    queue.task_done()
        except asyncio.CancelledError:
            pass

    async def _do_send(
        self,
        connections: List[WebSocket],
        message_str: str,
        execution_id: str,
        event_type: str,
        seq: int,
    ) -> None:
        """Send a message to a list of WebSocket connections.

        Single send path used by both same-loop and cross-loop code paths.
        Handles errors per-connection and cleans up disconnected sockets.

        Args:
            connections: Snapshot of WebSocket connections to send to
            message_str: JSON-serialized message string
            execution_id: The execution identifier
            event_type: Type of event (for logging)
            seq: Sequence number (for logging)
        """
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message_str)
                await asyncio.sleep(0)
                if event_type != "token":
                    logger.debug(
                        f"[CHECKPOINT-DEBUG] Successfully sent {event_type} message "
                        f"to websocket for execution: {execution_id}"
                    )
            except Exception as e:
                logger.error(
                    f"[WS-ERROR] Failed to send {event_type} (seq={seq}) to {execution_id}: {e}"
                )
                disconnected.append(websocket)
        for ws in disconnected:
            self.disconnect(ws, execution_id)

    def shutdown(self) -> None:
        """Cancel the drain task during application shutdown."""
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()

    def _get_next_sequence(self, execution_id: str) -> int:
        """Get next monotonic sequence number for an execution.

        Args:
            execution_id: The execution identifier

        Returns:
            The next sequence number (starts at 1)
        """
        with self._buffer_lock:
            if execution_id not in self.sequence_counters:
                self.sequence_counters[execution_id] = 0
            self.sequence_counters[execution_id] += 1
            return self.sequence_counters[execution_id]

    def _get_buffer(self, execution_id: str) -> MessageBuffer:
        """Get or create message buffer for an execution.

        Args:
            execution_id: The execution identifier

        Returns:
            MessageBuffer instance for this execution
        """
        with self._buffer_lock:
            if execution_id not in self.message_buffers:
                self.message_buffers[execution_id] = MessageBuffer()
            return self.message_buffers[execution_id]

    async def connect(self, websocket: WebSocket, execution_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.all_connections.add(websocket)

        if execution_id:
            if execution_id not in self.active_connections:
                self.active_connections[execution_id] = set()
            self.active_connections[execution_id].add(websocket)

    def disconnect(self, websocket: WebSocket, execution_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        self.all_connections.discard(websocket)

        if execution_id and execution_id in self.active_connections:
            self.active_connections[execution_id].discard(websocket)
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]
                # Clean up rate-limiting state and log final count
                final_count = self._token_update_count.pop(execution_id, 0)
                self._last_token_log_time.pop(execution_id, None)
                if final_count > 0:
                    logger.info(
                        f"[CHECKPOINT-DEBUG] Execution {execution_id} completed: sent {final_count} total token updates"
                    )
        else:
            # Remove from all execution groups
            for exec_id in list(self.active_connections.keys()):
                connections = self.active_connections.get(exec_id)
                if connections:
                    connections.discard(websocket)
                    if not connections:
                        del self.active_connections[exec_id]
                    # Clean up rate-limiting state
                    final_count = self._token_update_count.pop(exec_id, 0)
                    self._last_token_log_time.pop(exec_id, None)
                    if final_count > 0:
                        logger.info(
                            f"[CHECKPOINT-DEBUG] Execution {exec_id} completed: sent {final_count} total token updates"
                        )

    async def send_execution_update(
        self, execution_id: str, event_type: str, data: Dict[str, Any]
    ):
        """Send an update to all connections watching an execution.

        Messages are assigned a sequence number and buffered for replay
        in case of client reconnection during long workflows.

        When called from a worker thread (different event loop), the send
        is routed through an ordered queue on the main loop, ensuring
        correct ordering and proper error reporting.

        Args:
            execution_id: The execution identifier
            event_type: Type of event (e.g., "token", "node_update")
            data: Event data payload
        """
        # Assign sequence number and buffer the message
        seq = self._get_next_sequence(execution_id)
        buffer = self._get_buffer(execution_id)
        buffer.add(seq, event_type, data)

        message = {
            "type": event_type,
            "execution_id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "seq": seq,
            "data": data,
        }

        # If no active connections, message is buffered for replay
        if execution_id not in self.active_connections:
            return

        # Snapshot connection set to avoid race condition during iteration
        connections = list(self.active_connections.get(execution_id, []))

        message_str = json.dumps(message)

        # Cross-loop detection: if we're on a different event loop than the
        # main FastAPI loop, route through the ordered drain queue so that
        # (a) sends execute on the correct loop, (b) ordering is preserved,
        # and (c) errors are logged instead of silently swallowed.
        if self._main_loop is not None and not self._main_loop.is_closed():
            current_loop = asyncio.get_running_loop()
            if current_loop is not self._main_loop:
                queue = self._send_queue
                assert queue is not None
                send_item = (connections, message_str, execution_id, event_type, seq)
                qsize = queue.qsize()
                if qsize > self._QUEUE_HIGH_WATER:
                    logger.warning(
                        f"[WS-BACKPRESSURE] Cross-loop send queue size: {qsize}"
                    )
                self._main_loop.call_soon_threadsafe(queue.put_nowait, send_item)
                return

        await self._do_send(connections, message_str, execution_id, event_type, seq)

    async def send_node_update(
        self,
        execution_id: str,
        node_id: str,
        node_name: str,
        status: str,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        node_type: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        input_data: Optional[Any] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        is_sub_agent: Optional[bool] = None,
        parent_agent_id: Optional[str] = None,
        database_node_id: Optional[str] = None,
        execution_order: Optional[int] = None,
        step: Optional[int] = None,
    ):
        """Send a node execution update with complete data."""
        data_payload = {
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "status": status,
            "output": output,
            "error": error,
            "duration_seconds": duration_seconds,
            "input_data": input_data,
            "start_time": start_time,
            "end_time": end_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "is_sub_agent": is_sub_agent,
            "parent_agent_id": parent_agent_id,
            "database_node_id": database_node_id,
            "execution_order": execution_order,
            "step": step,
        }

        await self.send_execution_update(execution_id, "node_update", data_payload)

    async def send_execution_status(
        self,
        execution_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        """Send execution status update."""
        await self.send_execution_update(
            execution_id,
            "execution_status",
            {"status": status, "result": result, "error": error},
        )

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        # Snapshot connection set to avoid race condition during iteration
        connections = list(self.all_connections)
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws)

    async def replay_from_sequence(
        self, websocket: WebSocket, execution_id: str, last_sequence: int
    ) -> int:
        """Replay buffered messages since last_sequence to a reconnecting client.

        This enables clients to catch up on missed messages after a connection
        drop during a long-running workflow.

        Args:
            websocket: The reconnecting WebSocket client
            execution_id: The execution identifier
            last_sequence: The last sequence number received by the client

        Returns:
            Number of messages replayed
        """
        buffer = self._get_buffer(execution_id)
        missed = buffer.get_since(last_sequence)

        if not missed:
            return 0

        for msg in missed:
            message = {
                "type": msg.event_type,
                "execution_id": execution_id,
                "timestamp": msg.timestamp.isoformat(),
                "seq": msg.sequence,
                "data": msg.data,
            }
            try:
                await websocket.send_json(message)
                await asyncio.sleep(0)  # Yield to ensure message is flushed
            except Exception as e:
                logger.error(
                    f"[WS-REPLAY] Failed to replay message seq={msg.sequence}: {e}"
                )
                break

        return len(missed)

    def cleanup_execution(self, execution_id: str) -> None:
        """Clean up buffers and counters when execution completes.

        Should be called after execution completes to prevent memory leaks.
        The cleanup is typically delayed to allow final messages to be sent.

        Args:
            execution_id: The execution identifier to clean up
        """
        with self._buffer_lock:
            self.message_buffers.pop(execution_id, None)
            self.sequence_counters.pop(execution_id, None)

    def get_buffer_stats(self, execution_id: str) -> Dict[str, Any]:
        """Get statistics about the message buffer for an execution.

        Useful for debugging and monitoring.

        Args:
            execution_id: The execution identifier

        Returns:
            Dictionary with buffer statistics
        """
        with self._buffer_lock:
            if execution_id not in self.message_buffers:
                return {"exists": False}
            buffer = self.message_buffers[execution_id]
            return {
                "exists": True,
                "size": buffer.size(),
                "latest_sequence": buffer.get_latest_sequence(),
                "max_size": buffer.max_size,
                "ttl_seconds": buffer.ttl_seconds,
            }
