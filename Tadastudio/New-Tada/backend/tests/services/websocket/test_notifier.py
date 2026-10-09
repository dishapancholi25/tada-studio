"""Tests for WebSocket execution notifier.

Tests the WebSocketExecutionNotifier class which handles execution lifecycle
events and WebSocket notifications, including cleanup task deduplication.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.websocket.notifier import (
    WebSocketExecutionNotifier,
    BUFFER_CLEANUP_DELAY,
)
from backend.services.websocket.connection_manager import ConnectionManager


class TestWebSocketExecutionNotifier:
    """Test suite for WebSocketExecutionNotifier class."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        manager = MagicMock(spec=ConnectionManager)
        manager.send_execution_status = AsyncMock()
        manager.send_node_update = AsyncMock()
        manager.send_execution_update = AsyncMock()
        manager.cleanup_execution = MagicMock()
        return manager

    @pytest.fixture
    def notifier(self, mock_connection_manager):
        """Create a notifier with mock connection manager."""
        return WebSocketExecutionNotifier(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_on_execution_start(self, notifier, mock_connection_manager):
        """Test on_execution_start sends correct status."""
        await notifier.on_execution_start("exec-123", "TestGraph")

        mock_connection_manager.send_execution_status.assert_called_once_with(
            "exec-123", "started", {"graph_name": "TestGraph"}
        )

    @pytest.mark.asyncio
    async def test_on_execution_complete(self, notifier, mock_connection_manager):
        """Test on_execution_complete sends status and schedules cleanup."""
        with patch.object(notifier, "_schedule_cleanup") as mock_schedule:
            await notifier.on_execution_complete("exec-123", {"result": "success"})

            mock_connection_manager.send_execution_status.assert_called_once_with(
                "exec-123", "completed", {"result": "success"}
            )
            mock_schedule.assert_called_once_with("exec-123")

    @pytest.mark.asyncio
    async def test_on_execution_error(self, notifier, mock_connection_manager):
        """Test on_execution_error sends status and schedules cleanup."""
        with patch.object(notifier, "_schedule_cleanup") as mock_schedule:
            await notifier.on_execution_error("exec-123", "Something went wrong")

            mock_connection_manager.send_execution_status.assert_called_once_with(
                "exec-123", "failed", None, "Something went wrong"
            )
            mock_schedule.assert_called_once_with("exec-123")

    @pytest.mark.asyncio
    async def test_on_execution_stopped(self, notifier, mock_connection_manager):
        """Test on_execution_stopped sends status and schedules cleanup."""
        with patch.object(notifier, "_schedule_cleanup") as mock_schedule:
            await notifier.on_execution_stopped("exec-123", {"reason": "user"})

            mock_connection_manager.send_execution_status.assert_called_once_with(
                "exec-123", "stopped", {"reason": "user"}
            )
            mock_schedule.assert_called_once_with("exec-123")

    @pytest.mark.asyncio
    async def test_on_node_start(self, notifier, mock_connection_manager):
        """Test on_node_start sends node update."""
        await notifier.on_node_start(
            execution_id="exec-123",
            node_id="node-1",
            node_name="Agent 1",
            node_type="AGENT",
        )

        mock_connection_manager.send_node_update.assert_called_once()
        call_args = mock_connection_manager.send_node_update.call_args
        assert call_args[0][0] == "exec-123"
        assert call_args[0][1] == "node-1"
        assert call_args[0][2] == "Agent 1"
        assert call_args[0][3] == "running"

    @pytest.mark.asyncio
    async def test_on_node_complete(self, notifier, mock_connection_manager):
        """Test on_node_complete sends node update with output."""
        await notifier.on_node_complete(
            execution_id="exec-123",
            node_id="node-1",
            node_name="Agent 1",
            output={"response": "Hello"},
            node_type="AGENT",
            duration_seconds=1.5,
        )

        mock_connection_manager.send_node_update.assert_called_once()
        call_args = mock_connection_manager.send_node_update.call_args
        assert call_args[0][0] == "exec-123"
        assert call_args[0][3] == "completed"
        assert call_args[0][4] == {"response": "Hello"}

    @pytest.mark.asyncio
    async def test_on_node_error(self, notifier, mock_connection_manager):
        """Test on_node_error sends failed node update."""
        await notifier.on_node_error(
            execution_id="exec-123",
            node_id="node-1",
            node_name="Agent 1",
            error="Node failed",
            node_type="AGENT",
        )

        mock_connection_manager.send_node_update.assert_called_once()
        call_args = mock_connection_manager.send_node_update.call_args
        assert call_args[0][3] == "failed"
        assert call_args[0][5] == "Node failed"


class TestCleanupDeduplication:
    """Tests for cleanup task deduplication functionality."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        manager = MagicMock(spec=ConnectionManager)
        manager.send_execution_status = AsyncMock()
        manager.cleanup_execution = MagicMock()
        return manager

    @pytest.fixture
    def notifier(self, mock_connection_manager):
        """Create a notifier with mock connection manager."""
        return WebSocketExecutionNotifier(mock_connection_manager)

    def test_schedule_cleanup_adds_to_pending(self, notifier):
        """Test _schedule_cleanup adds execution to pending set."""
        with patch("asyncio.create_task") as mock_create_task:
            notifier._schedule_cleanup("exec-123")

            assert "exec-123" in notifier._pending_cleanups
            mock_create_task.assert_called_once()

    def test_schedule_cleanup_skips_if_already_pending(self, notifier):
        """Test _schedule_cleanup skips if already scheduled."""
        notifier._pending_cleanups.add("exec-123")

        with patch("asyncio.create_task") as mock_create_task:
            notifier._schedule_cleanup("exec-123")

            # Should not create another task
            mock_create_task.assert_not_called()

    def test_multiple_cleanups_deduplicated(self, notifier):
        """Test that multiple cleanup requests are deduplicated."""
        with patch("asyncio.create_task") as mock_create_task:
            # Simulate complete, error, and stopped all happening
            notifier._schedule_cleanup("exec-123")
            notifier._schedule_cleanup("exec-123")
            notifier._schedule_cleanup("exec-123")

            # Only one task should be created
            assert mock_create_task.call_count == 1

    @pytest.mark.asyncio
    async def test_delayed_cleanup_removes_from_pending(
        self, notifier, mock_connection_manager
    ):
        """Test that _delayed_buffer_cleanup removes from pending after completion."""
        notifier._pending_cleanups.add("exec-123")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await notifier._delayed_buffer_cleanup("exec-123")

            mock_sleep.assert_called_once_with(BUFFER_CLEANUP_DELAY)
            mock_connection_manager.cleanup_execution.assert_called_once_with(
                "exec-123"
            )
            assert "exec-123" not in notifier._pending_cleanups

    @pytest.mark.asyncio
    async def test_delayed_cleanup_removes_from_pending_on_error(
        self, notifier, mock_connection_manager
    ):
        """Test cleanup is removed from pending even if cleanup_execution fails."""
        notifier._pending_cleanups.add("exec-123")
        mock_connection_manager.cleanup_execution.side_effect = Exception("DB error")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            try:
                await notifier._delayed_buffer_cleanup("exec-123")
            except Exception:
                pass

            # Should still be removed from pending
            assert "exec-123" not in notifier._pending_cleanups

    @pytest.mark.asyncio
    async def test_cleanup_integration(self, notifier, mock_connection_manager):
        """Integration test: verify cleanup flows correctly through the system."""
        execution_id = "exec-123"

        # Simulate the execution lifecycle
        await notifier.on_execution_start(execution_id, "TestGraph")

        # Complete the execution - this should schedule cleanup
        with patch("asyncio.create_task") as mock_create_task:
            await notifier.on_execution_complete(execution_id, {"result": "done"})

            # Verify cleanup was scheduled
            assert execution_id in notifier._pending_cleanups
            mock_create_task.assert_called_once()

        # Simulate error also coming in (shouldn't schedule another cleanup)
        with patch("asyncio.create_task") as mock_create_task:
            await notifier.on_execution_error(execution_id, "Late error")

            # Should not create another task
            mock_create_task.assert_not_called()

    def test_independent_executions_have_separate_cleanup(self, notifier):
        """Test that different executions have independent cleanup scheduling."""
        with patch("asyncio.create_task"):
            notifier._schedule_cleanup("exec-1")
            notifier._schedule_cleanup("exec-2")
            notifier._schedule_cleanup("exec-3")

            assert "exec-1" in notifier._pending_cleanups
            assert "exec-2" in notifier._pending_cleanups
            assert "exec-3" in notifier._pending_cleanups


class TestCleanupDelayConfiguration:
    """Tests for cleanup delay configuration."""

    def test_cleanup_delay_is_60_seconds(self):
        """Verify cleanup delay is 60 seconds."""
        assert BUFFER_CLEANUP_DELAY == 60.0

    @pytest.mark.asyncio
    async def test_cleanup_waits_correct_duration(self):
        """Test that cleanup waits for the configured delay."""
        manager = MagicMock(spec=ConnectionManager)
        manager.send_execution_status = AsyncMock()
        manager.cleanup_execution = MagicMock()

        notifier = WebSocketExecutionNotifier(manager)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await notifier._delayed_buffer_cleanup("exec-123")

            mock_sleep.assert_called_once_with(60.0)


class TestStreamEvents:
    """Tests for stream event handling."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        manager = MagicMock(spec=ConnectionManager)
        manager.send_execution_update = AsyncMock()
        return manager

    @pytest.fixture
    def notifier(self, mock_connection_manager):
        """Create a notifier with mock connection manager."""
        return WebSocketExecutionNotifier(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_on_stream_event_token(self, notifier, mock_connection_manager):
        """Test streaming token events."""
        await notifier.on_stream_event(
            execution_id="exec-123",
            event_type="token",
            payload={"content": "Hello"},
        )

        mock_connection_manager.send_execution_update.assert_called_once()
        call_args = mock_connection_manager.send_execution_update.call_args
        assert call_args[0][0] == "exec-123"
        assert call_args[0][1] == "token"

    @pytest.mark.asyncio
    async def test_on_stream_event_structured(self, notifier, mock_connection_manager):
        """Test structured streaming events with event_type in payload."""
        await notifier.on_stream_event(
            execution_id="exec-123",
            event_type="custom",
            payload={"event_type": "tool_call_start", "tool_name": "search"},
        )

        mock_connection_manager.send_execution_update.assert_called_once()
        call_args = mock_connection_manager.send_execution_update.call_args
        assert call_args[0][0] == "exec-123"
        # Should use the event_type from payload
        assert call_args[0][1] == "tool_call_start"

    @pytest.mark.asyncio
    async def test_on_stream_event_with_node_attribution(
        self, notifier, mock_connection_manager
    ):
        """Test stream events include node attribution."""
        await notifier.on_stream_event(
            execution_id="exec-123",
            event_type="token",
            payload={"content": "test", "node_id": "agent-1", "step": 2},
        )

        mock_connection_manager.send_execution_update.assert_called_once()
        call_args = mock_connection_manager.send_execution_update.call_args
        data = call_args[0][2]
        assert data.get("nodeId") == "agent-1"
        assert data.get("step") == 2


class TestPauseResumeEvents:
    """Tests for pause/resume event handling."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        manager = MagicMock(spec=ConnectionManager)
        manager.send_execution_status = AsyncMock()
        manager.send_node_update = AsyncMock()
        return manager

    @pytest.fixture
    def notifier(self, mock_connection_manager):
        """Create a notifier with mock connection manager."""
        return WebSocketExecutionNotifier(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_on_execution_paused(self, notifier, mock_connection_manager):
        """Test execution paused notification."""
        payload = {"checkpoint_id": "cp-123", "prompt": "Please confirm"}

        await notifier.on_execution_paused("exec-123", payload)

        mock_connection_manager.send_execution_status.assert_called_once_with(
            "exec-123", "paused", payload
        )

    @pytest.mark.asyncio
    async def test_on_execution_resumed(self, notifier, mock_connection_manager):
        """Test execution resumed notification."""
        await notifier.on_execution_resumed("exec-123", {"resumed_by": "user"})

        mock_connection_manager.send_execution_status.assert_called_once_with(
            "exec-123", "running", {"resumed_by": "user"}
        )

    @pytest.mark.asyncio
    async def test_on_node_paused(self, notifier, mock_connection_manager):
        """Test node paused notification."""
        await notifier.on_node_paused(
            execution_id="exec-123",
            node_id="checkpoint-1",
            node_name="Approval",
            node_type="CHECKPOINT",
        )

        mock_connection_manager.send_node_update.assert_called_once()
        call_args = mock_connection_manager.send_node_update.call_args
        assert call_args[0][3] == "paused"

    @pytest.mark.asyncio
    async def test_on_execution_pause_requested(
        self, notifier, mock_connection_manager
    ):
        """Test pause requested notification."""
        await notifier.on_execution_pause_requested(
            "exec-123", {"requested_by": "user"}
        )

        mock_connection_manager.send_execution_status.assert_called_once_with(
            "exec-123", "pause_pending", {"requested_by": "user"}
        )

    @pytest.mark.asyncio
    async def test_on_execution_stop_requested(self, notifier, mock_connection_manager):
        """Test stop requested notification."""
        await notifier.on_execution_stop_requested("exec-123", {"requested_by": "user"})

        mock_connection_manager.send_execution_status.assert_called_once_with(
            "exec-123", "stop_requested", {"requested_by": "user"}
        )
