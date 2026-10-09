"""Tests for WorkflowExecutor streaming event handling.

These tests verify that the workflow executor correctly forwards
streaming events to WebSocket clients via on_stream_event.

NOTE: Bridging code (tool_call_* -> on_node_*) was removed.
The frontend now handles tool_call_start/complete/error events directly
via streaming callbacks to update tool status in real-time.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestStreamEventForwarding:
    """Tests for forwarding streaming events via on_stream_event.

    NOTE: Bridging (tool_call_* -> on_node_*) was removed.
    The frontend handles tool status updates directly via streaming callbacks.
    """

    @pytest.fixture
    def mock_ws_notifier(self):
        """Create a mock WebSocket notifier with async methods."""
        notifier = MagicMock()
        notifier.on_node_start = AsyncMock()
        notifier.on_node_complete = AsyncMock()
        notifier.on_node_error = AsyncMock()
        notifier.on_stream_event = AsyncMock()
        return notifier

    @pytest.fixture
    def workflow_executor(self):
        """Create a minimal WorkflowExecutor for testing."""
        from backend.services.execution.workflow_executor import WorkflowExecutor

        mock_engine = MagicMock()
        return WorkflowExecutor(engine=mock_engine)

    @pytest.mark.asyncio
    async def test_tool_call_start_forwarded_to_stream_event(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool_call_start is forwarded via on_stream_event (no bridging)."""
        payload = {
            "event_type": "tool_call_start",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "tool_node_id": "node_doc_456",
            "tool_node_name": "Document Search",
            "tool_node_type": "DOCUMENT_SEARCH",
            "agent_id": "agent_1",
            "agent_name": "Research Agent",
            "tool_args": {"query": "test"},
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No bridging - on_node_start should NOT be called
        mock_ws_notifier.on_node_start.assert_not_called()

        # Stream event should be forwarded
        mock_ws_notifier.on_stream_event.assert_called_once()
        call_args = mock_ws_notifier.on_stream_event.call_args
        assert call_args[0][0] == "exec-123"  # execution_id
        assert call_args[0][1] == "custom"  # event_type
        assert call_args[0][2]["event_type"] == "tool_call_start"

    @pytest.mark.asyncio
    async def test_tool_call_complete_forwarded_to_stream_event(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool_call_complete is forwarded via on_stream_event (no bridging)."""
        payload = {
            "event_type": "tool_call_complete",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "tool_node_id": "node_doc_456",
            "tool_node_name": "Document Search",
            "tool_node_type": "DOCUMENT_SEARCH",
            "duration_ms": 1500.0,
            "result_preview": "Found 5 documents about the topic",
            "agent_id": "agent_1",
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No bridging - on_node_complete should NOT be called
        mock_ws_notifier.on_node_complete.assert_not_called()

        # Stream event should be forwarded
        mock_ws_notifier.on_stream_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_call_error_forwarded_to_stream_event(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool_call_error is forwarded via on_stream_event (no bridging)."""
        payload = {
            "event_type": "tool_call_error",
            "call_id": "call_123",
            "tool_name": "http_request_abc",
            "tool_node_id": "node_http_789",
            "tool_node_name": "API Request",
            "tool_node_type": "HTTP_REQUEST",
            "error": "Connection refused: timeout after 30s",
            "duration_ms": 30000.0,
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No bridging - on_node_error should NOT be called
        mock_ws_notifier.on_node_error.assert_not_called()

        # Stream event should be forwarded
        mock_ws_notifier.on_stream_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_event_without_node_id_still_forwarded(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool events without tool_node_id are still forwarded."""
        payload = {
            "event_type": "tool_call_start",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            # No tool_node_id - old-style event without node info
            "agent_id": "agent_1",
            "agent_name": "Research Agent",
            "tool_args": {"query": "test"},
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No bridging
        mock_ws_notifier.on_node_start.assert_not_called()

        # Stream event should still be forwarded
        mock_ws_notifier.on_stream_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_event_includes_tool_node_info(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify stream event includes tool_node_id, name, type for frontend."""
        payload = {
            "event_type": "tool_call_start",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "tool_node_id": "node_doc_456",
            "tool_node_name": "Document Search",
            "tool_node_type": "DOCUMENT_SEARCH",
            "agent_id": "agent_1",
            "tool_args": {"query": "test"},
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # Verify stream event includes tool node info
        mock_ws_notifier.on_stream_event.assert_called_once()
        call_args = mock_ws_notifier.on_stream_event.call_args
        forwarded_payload = call_args[0][2]

        assert forwarded_payload.get("tool_node_id") == "node_doc_456"
        assert forwarded_payload.get("tool_node_name") == "Document Search"
        assert forwarded_payload.get("tool_node_type") == "DOCUMENT_SEARCH"

    @pytest.mark.asyncio
    async def test_no_crash_on_stream_event_failure(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify graceful handling when on_stream_event fails."""
        payload = {
            "event_type": "tool_call_start",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "tool_node_id": "node_doc_456",
            "agent_id": "agent_1",
        }

        # Make on_stream_event raise an exception
        mock_ws_notifier.on_stream_event = AsyncMock(
            side_effect=Exception("WebSocket disconnected")
        )

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            # Should not raise - failures are caught and logged
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)


class TestNonToolStreamEvents:
    """Tests for non-tool streaming events (should pass through unchanged)."""

    @pytest.fixture
    def mock_ws_notifier(self):
        """Create a mock WebSocket notifier."""
        notifier = MagicMock()
        notifier.on_node_start = AsyncMock()
        notifier.on_node_complete = AsyncMock()
        notifier.on_node_error = AsyncMock()
        notifier.on_stream_event = AsyncMock()
        return notifier

    @pytest.fixture
    def workflow_executor(self):
        """Create a minimal WorkflowExecutor."""
        from backend.services.execution.workflow_executor import WorkflowExecutor

        mock_engine = MagicMock()
        return WorkflowExecutor(engine=mock_engine)

    @pytest.mark.asyncio
    async def test_subagent_events_pass_through(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify subagent_start events pass through without bridging."""
        payload = {
            "event_type": "subagent_start",
            "subagent_id": "sub_123",
            "subagent_name": "Data Analyst",
            "task_description": "Analyze the data",
            "parent_agent_id": "orchestrator_1",
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No node bridging for subagent events
        mock_ws_notifier.on_node_start.assert_not_called()
        mock_ws_notifier.on_node_complete.assert_not_called()

        # Stream event should still be sent
        mock_ws_notifier.on_stream_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_progress_events_pass_through(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool_call_progress events pass through without bridging."""
        payload = {
            "event_type": "tool_call_progress",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "message": "Searching collection 2/3...",
            "progress": 66,
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No node bridging for progress events
        mock_ws_notifier.on_node_start.assert_not_called()
        mock_ws_notifier.on_node_complete.assert_not_called()

        # Stream event should still be sent
        mock_ws_notifier.on_stream_event.assert_called_once()


class TestEdgeCases:
    """Edge case tests for _handle_stream_event."""

    @pytest.fixture
    def mock_ws_notifier(self):
        """Create a mock WebSocket notifier."""
        notifier = MagicMock()
        notifier.on_node_start = AsyncMock()
        notifier.on_node_complete = AsyncMock()
        notifier.on_node_error = AsyncMock()
        notifier.on_stream_event = AsyncMock()
        return notifier

    @pytest.fixture
    def workflow_executor(self):
        """Create a minimal WorkflowExecutor."""
        from backend.services.execution.workflow_executor import WorkflowExecutor

        mock_engine = MagicMock()
        return WorkflowExecutor(engine=mock_engine)

    @pytest.mark.asyncio
    async def test_no_notifier_skips_processing(self, workflow_executor):
        """Verify early return when ws_notifier is None."""
        payload = {
            "event_type": "tool_call_start",
            "tool_node_id": "node_123",
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            None,
        ):
            # Should return early without error
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

    @pytest.mark.asyncio
    async def test_no_execution_id_skips_processing(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify early return when execution_id is empty."""
        payload = {
            "event_type": "tool_call_start",
            "tool_node_id": "node_123",
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            # Should return early without processing
            await workflow_executor._handle_stream_event("", "custom", payload)

        mock_ws_notifier.on_node_start.assert_not_called()
        mock_ws_notifier.on_stream_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_event_with_missing_node_name_still_forwarded(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool event without tool_node_name still forwarded to stream_event."""
        payload = {
            "event_type": "tool_call_start",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "tool_node_id": "node_doc_456",
            # No tool_node_name - frontend will use tool_name as fallback
            "tool_node_type": "DOCUMENT_SEARCH",
            "agent_id": "agent_1",
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No bridging
        mock_ws_notifier.on_node_start.assert_not_called()

        # Stream event should still be forwarded with full payload
        mock_ws_notifier.on_stream_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_complete_without_duration_still_forwarded(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify tool_call_complete without duration_ms still forwarded."""
        payload = {
            "event_type": "tool_call_complete",
            "call_id": "call_123",
            "tool_name": "search_documents_abc",
            "tool_node_id": "node_doc_456",
            "tool_node_name": "Document Search",
            "tool_node_type": "DOCUMENT_SEARCH",
            # No duration_ms - frontend will handle default
            "result_preview": "Complete",
        }

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "custom", payload)

        # No bridging
        mock_ws_notifier.on_node_complete.assert_not_called()

        # Stream event forwarded
        mock_ws_notifier.on_stream_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_string_payload_passes_through(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify string payloads pass through unchanged (not dict)."""
        payload = "Simple text message"

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_stream_event("exec-123", "token", payload)

        # No node bridging for non-dict payloads
        mock_ws_notifier.on_node_start.assert_not_called()

        # But stream event should still be sent
        mock_ws_notifier.on_stream_event.assert_called_once()


class TestHandleExecutionError:
    """Tests for _handle_execution_error method."""

    @pytest.fixture
    def mock_ws_notifier(self):
        """Create a mock WebSocket notifier with async methods."""
        notifier = MagicMock()
        notifier.on_node_start = AsyncMock()
        notifier.on_node_complete = AsyncMock()
        notifier.on_node_error = AsyncMock()
        notifier.on_stream_event = AsyncMock()
        notifier.on_execution_error = AsyncMock()
        return notifier

    @pytest.fixture
    def workflow_executor(self):
        """Create a minimal WorkflowExecutor for testing."""
        from backend.services.execution.workflow_executor import WorkflowExecutor

        mock_engine = MagicMock()
        mock_engine.active_executions = {}
        return WorkflowExecutor(engine=mock_engine)

    @pytest.mark.asyncio
    async def test_handle_execution_error_updates_database_with_error_message(
        self, workflow_executor
    ):
        """Verify update_graph_execution is called with error_message parameter."""
        error = Exception("Test error message")

        with patch(
            "backend.services.execution.workflow_executor.ExecutionHistoryService"
        ) as mock_service:
            await workflow_executor._handle_execution_error(
                execution_id="exec-123",
                db_execution_id=456,
                error=error,
            )

            mock_service.update_graph_execution.assert_called_once()
            call_kwargs = mock_service.update_graph_execution.call_args.kwargs
            assert call_kwargs["status"] == "failed"
            assert call_kwargs["error_message"] == "Test error message"
            assert "error" not in call_kwargs  # Wrong param name should not be used

    @pytest.mark.asyncio
    async def test_handle_execution_error_sends_websocket_notification(
        self, workflow_executor, mock_ws_notifier
    ):
        """Verify on_execution_error is called (not on_execution_failed)."""
        error = Exception("WebSocket test error")

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            await workflow_executor._handle_execution_error(
                execution_id="exec-789",
                db_execution_id=None,
                error=error,
            )

        mock_ws_notifier.on_execution_error.assert_called_once_with(
            "exec-789", "WebSocket test error"
        )

    @pytest.mark.asyncio
    async def test_handle_execution_error_updates_in_memory_state(
        self, workflow_executor
    ):
        """Verify in-memory active_executions is updated on error."""
        workflow_executor.engine.active_executions["exec-abc"] = {"status": "running"}
        error = Exception("State test error")

        await workflow_executor._handle_execution_error(
            execution_id="exec-abc",
            db_execution_id=None,
            error=error,
        )

        state = workflow_executor.engine.active_executions["exec-abc"]
        assert state["status"] == "failed"
        assert state["error"] == "State test error"
        assert "end_time" in state

    @pytest.mark.asyncio
    async def test_handle_execution_error_graceful_on_db_failure(
        self, workflow_executor, caplog
    ):
        """Verify DB errors are logged but don't crash execution."""
        with patch(
            "backend.services.execution.workflow_executor.ExecutionHistoryService"
        ) as mock_service:
            mock_service.update_graph_execution.side_effect = Exception("DB down")

            # Should not raise
            await workflow_executor._handle_execution_error(
                execution_id="exec-123",
                db_execution_id=456,
                error=Exception("Original error"),
            )

        assert "Failed to update DB on error" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_execution_error_graceful_on_websocket_failure(
        self, workflow_executor, mock_ws_notifier, caplog
    ):
        """Verify WebSocket errors are logged but don't crash execution."""
        mock_ws_notifier.on_execution_error.side_effect = Exception("WS disconnected")

        with patch(
            "backend.services.execution.workflow_executor.ws_notifier",
            mock_ws_notifier,
        ):
            # Should not raise
            await workflow_executor._handle_execution_error(
                execution_id="exec-123",
                db_execution_id=None,
                error=Exception("Original error"),
            )

        assert "Failed to send error notification" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_execution_error_skips_db_update_when_no_db_id(
        self, workflow_executor
    ):
        """Verify DB update is skipped when db_execution_id is None."""
        error = Exception("Test error")

        with patch(
            "backend.services.execution.workflow_executor.ExecutionHistoryService"
        ) as mock_service:
            await workflow_executor._handle_execution_error(
                execution_id="exec-123",
                db_execution_id=None,
                error=error,
            )

            mock_service.update_graph_execution.assert_not_called()
