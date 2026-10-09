"""WebSocket execution notifier for real-time updates.

Provides callback methods for the execution engine to send real-time updates.
"""

import asyncio
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from ...services.config import get_logger
from .connection_manager import ConnectionManager
from .reconnection import handle_reconnect_execution


logger = get_logger("websocket_notifier")

# Delay before cleaning up message buffers after execution completes
# Extended to 60s to allow reconnecting clients more time to catch up
BUFFER_CLEANUP_DELAY = 60.0  # seconds


class WebSocketExecutionNotifier:
    """Provides callback methods for the execution engine to send real-time updates.

    This replaces the adapter layer's update functionality.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize WebSocket execution notifier."""
        self.manager = connection_manager
        # Track pending cleanup tasks to avoid scheduling duplicates
        self._pending_cleanups: Set[str] = set()
        # Track cleanup task references for cancellation on shutdown
        self._cleanup_tasks: Dict[str, asyncio.Task] = {}

    async def on_execution_start(self, execution_id: str, graph_name: str):
        """Handle execution start event."""
        await self.manager.send_execution_status(
            execution_id, "started", {"graph_name": graph_name}
        )

    async def on_node_start(
        self,
        execution_id: str,
        node_id: str,
        node_name: str,
        node_type: str,
        is_sub_agent: Optional[bool] = None,
        parent_agent_id: Optional[str] = None,
        database_node_id: Optional[str] = None,
        execution_order: Optional[int] = None,
        step: Optional[int] = None,
    ):
        """Handle node start event."""
        await self.manager.send_node_update(
            execution_id,
            node_id,
            node_name,
            "running",
            None,  # output
            None,  # error
            node_type,  # node_type
            None,  # duration_seconds
            None,  # input_data
            None,  # start_time
            None,  # end_time
            None,  # input_tokens
            None,  # output_tokens
            None,  # total_tokens
            is_sub_agent,
            parent_agent_id,
            database_node_id,
            execution_order,
            step,
        )

    async def on_node_complete(
        self,
        execution_id: str,
        node_id: str,
        node_name: str,
        output: Any,
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
        """Handle node completion event."""
        await self.manager.send_node_update(
            execution_id,
            node_id,
            node_name,
            "completed",
            output,
            None,  # error
            node_type,
            duration_seconds,
            input_data,
            start_time,
            end_time,
            input_tokens,
            output_tokens,
            total_tokens,
            is_sub_agent,
            parent_agent_id,
            database_node_id,
            execution_order,
            step,
        )

    async def on_node_error(
        self,
        execution_id: str,
        node_id: str,
        node_name: str,
        error: str,
        node_type: Optional[str] = None,
        database_node_id: Optional[str] = None,
    ):
        """Handle node error event."""
        await self.manager.send_node_update(
            execution_id,
            node_id,
            node_name,
            "failed",
            None,
            error,
            node_type,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            database_node_id,
        )

    async def on_execution_complete(self, execution_id: str, result: Any):
        """Handle execution completion event."""
        await self.manager.send_execution_status(execution_id, "completed", result)
        # Schedule buffer cleanup after delay to allow reconnecting clients
        self._schedule_cleanup(execution_id)

    def _schedule_cleanup(self, execution_id: str) -> None:
        """Schedule buffer cleanup if not already pending.

        Prevents duplicate cleanup tasks from being scheduled when
        multiple terminal events occur (complete, error, stopped).
        """
        if execution_id in self._pending_cleanups:
            logger.debug(
                f"[WS-CLEANUP] Cleanup already scheduled for {execution_id}, skipping"
            )
            return

        self._pending_cleanups.add(execution_id)
        task = asyncio.create_task(self._delayed_buffer_cleanup(execution_id))
        self._cleanup_tasks[execution_id] = task

    async def _delayed_buffer_cleanup(self, execution_id: str) -> None:
        """Clean up message buffer after a delay.

        This allows time for:
        - Final messages to be sent
        - Reconnecting clients to receive buffered messages
        """
        try:
            await asyncio.sleep(BUFFER_CLEANUP_DELAY)
            self.manager.cleanup_execution(execution_id)
            logger.debug(f"[WS-CLEANUP] Scheduled cleanup completed for {execution_id}")
        finally:
            # Always remove from tracking, even if cleanup fails or is cancelled
            self._pending_cleanups.discard(execution_id)
            self._cleanup_tasks.pop(execution_id, None)

    async def shutdown(self) -> None:
        """Cancel all pending cleanup tasks during application shutdown.

        This prevents 'Task was destroyed but it is pending!' warnings when
        the application shuts down while cleanup tasks are still waiting.
        """
        if not self._cleanup_tasks:
            return

        logger.info(
            f"[WS-CLEANUP] Cancelling {len(self._cleanup_tasks)} pending cleanup tasks"
        )

        for execution_id, task in list(self._cleanup_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            # Perform immediate cleanup instead of waiting
            self.manager.cleanup_execution(execution_id)

        self._cleanup_tasks.clear()
        self._pending_cleanups.clear()
        logger.info("[WS-CLEANUP] All pending cleanup tasks cancelled")

    async def on_stream_event(
        self,
        execution_id: str,
        event_type: str,
        payload: Any,
    ):
        """
        Send a generic streaming event (tokens, custom tool progress, etc.).
        Args:
            execution_id: The execution identifier
            event_type: A short type label (e.g., "token", "custom")
            payload: JSON-serializable payload (may include node_id and step for attribution)
        """
        # Check if this is a structured streaming event from our event emitter
        # These events have an "event_type" field that should be used as the message type
        if isinstance(payload, dict) and "event_type" in payload:
            custom_event_type = payload.get("event_type")
            logger.debug(
                f"Routing structured streaming event: {custom_event_type} for {execution_id}"
            )
            await self.manager.send_execution_update(
                execution_id,
                custom_event_type,  # Use specific event type (tool_call_start, etc.)
                payload,
            )
            return

        # Extract node_id and step from payload if present for token attribution
        # This allows the frontend to display tokens under the correct node iteration
        data = {"payload": payload}
        if isinstance(payload, dict):
            if "node_id" in payload:
                data["nodeId"] = payload.get("node_id")
            if "step" in payload:
                data["step"] = payload.get("step")
            # Send content directly instead of nested dict
            data["payload"] = payload.get("content", payload)

        await self.manager.send_execution_update(
            execution_id,
            event_type,
            data,
        )

    async def on_node_paused(
        self,
        execution_id: str,
        node_id: str,
        node_name: str,
        node_type: Optional[str] = None,
        database_node_id: Optional[str] = None,
        is_sub_agent: Optional[bool] = None,
        parent_agent_id: Optional[str] = None,
    ):
        """Handle node pause event (e.g., checkpoint)."""
        logger.info(
            f"[CHECKPOINT-DEBUG] Node paused - execution_id: {execution_id}, node_id: {node_id}, node_name: {node_name}, node_type: {node_type}"
        )
        await self.manager.send_node_update(
            execution_id,
            node_id,
            node_name,
            "paused",
            None,  # output
            None,  # error
            node_type,
            None,  # duration
            None,  # input_data
            None,  # start_time
            None,  # end_time
            None,  # input_tokens
            None,  # output_tokens
            None,  # total_tokens
            is_sub_agent,
            parent_agent_id,
            database_node_id,
        )

    async def on_execution_paused(self, execution_id: str, payload: Any):
        """Handle execution pause event for human-in-the-loop."""
        logger.info(
            f"[CHECKPOINT-DEBUG] Execution paused - execution_id: {execution_id}, payload: {payload}"
        )
        await self.manager.send_execution_status(execution_id, "paused", payload)

    async def on_execution_resumed(self, execution_id: str, payload: Any | None = None):
        """Handle execution resumption after pause."""
        logger.info(
            f"[CHECKPOINT-DEBUG] Execution resumed - execution_id: {execution_id}, payload: {payload}"
        )
        await self.manager.send_execution_status(execution_id, "running", payload)

    async def on_execution_pause_requested(self, execution_id: str, payload: Any):
        """Notify clients that a pause has been requested."""
        logger.info(
            f"[EXEC-CONTROL] Pause requested - execution_id: {execution_id}, payload: {payload}"
        )
        await self.manager.send_execution_status(
            execution_id,
            "pause_pending",
            payload,
        )

    async def on_execution_stop_requested(self, execution_id: str, payload: Any):
        """Notify clients that a stop has been requested."""
        logger.info(
            f"[EXEC-CONTROL] Stop requested - execution_id: {execution_id}, payload: {payload}"
        )
        await self.manager.send_execution_status(
            execution_id,
            "stop_requested",
            payload,
        )

    async def on_execution_stopped(self, execution_id: str, payload: Any):
        """Notify clients that an execution has stopped."""
        logger.info(
            f"[EXEC-CONTROL] Execution stopped - execution_id: {execution_id}, payload: {payload}"
        )
        await self.manager.send_execution_status(
            execution_id,
            "stopped",
            payload,
        )
        # Schedule buffer cleanup after delay (deduplicated)
        self._schedule_cleanup(execution_id)

    async def on_execution_error(self, execution_id: str, error: str):
        """Handle execution error event."""
        await self.manager.send_execution_status(execution_id, "failed", None, error)
        # Schedule buffer cleanup after delay (deduplicated)
        self._schedule_cleanup(execution_id)

    async def handle_reconnect_execution(
        self,
        websocket: WebSocket,
        execution_id: str,
        thread_id: Optional[str] = None,
        db_execution_id: Optional[str] = None,
    ):
        """Handle reconnection to an existing execution."""
        await handle_reconnect_execution(
            self.manager, self, websocket, execution_id, thread_id, db_execution_id
        )
