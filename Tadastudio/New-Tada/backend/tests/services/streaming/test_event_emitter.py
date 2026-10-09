"""Tests for StreamingEventEmitter.

These tests verify the streaming event emitter functionality:
- Correct event structure for all event types
- Graceful handling when stream writer is unavailable
- Timestamp generation
- Result preview truncation
"""

from datetime import datetime

from backend.services.streaming import streaming_emitter
from backend.services.streaming.event_emitter import StreamingEventEmitter


# ---------------------------------------------------------------------------
# TestStreamingEventEmitter - Basic Functionality
# ---------------------------------------------------------------------------


class TestStreamingEventEmitter:
    """Tests for basic StreamingEventEmitter functionality."""

    def test_get_writer_returns_none_when_not_in_context(
        self, mock_stream_writer_unavailable
    ):
        """Should return None when not in LangGraph context."""
        writer = StreamingEventEmitter._get_writer()
        assert writer is None

    def test_get_writer_returns_writer_when_available(self, mock_stream_writer):
        """Should return stream writer when in LangGraph context."""
        writer = StreamingEventEmitter._get_writer()
        assert writer is not None

    def test_timestamp_returns_utc_iso_format(self):
        """Should return UTC timestamp in ISO format."""
        timestamp = StreamingEventEmitter._timestamp()
        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# TestToolCallStart - Tool Start Events
# ---------------------------------------------------------------------------


class TestToolCallStart:
    """Tests for tool_call_start event emission."""

    def test_emits_tool_start_event(
        self, mock_stream_writer, captured_events, sample_tool_call_start_event
    ):
        """Should emit tool_call_start event with correct structure."""
        streaming_emitter.emit_tool_start(**sample_tool_call_start_event)

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "tool_call_start"
        assert event["call_id"] == sample_tool_call_start_event["call_id"]
        assert event["tool_name"] == sample_tool_call_start_event["tool_name"]
        assert event["tool_args"] == sample_tool_call_start_event["tool_args"]
        assert event["agent_id"] == sample_tool_call_start_event["agent_id"]
        assert event["agent_name"] == sample_tool_call_start_event["agent_name"]
        assert "timestamp" in event

    def test_no_error_when_writer_unavailable(
        self, mock_stream_writer_unavailable, sample_tool_call_start_event
    ):
        """Should not raise when stream writer is unavailable."""
        # Should not raise any exception
        streaming_emitter.emit_tool_start(**sample_tool_call_start_event)

    def test_handles_empty_tool_args(self, mock_stream_writer, captured_events):
        """Should handle empty tool arguments."""
        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="simple_tool",
            tool_args={},
            agent_id="agent-001",
            agent_name="Test Agent",
        )

        assert len(captured_events) == 1
        assert captured_events[0]["tool_args"] == {}


# ---------------------------------------------------------------------------
# TestToolCallProgress - Tool Progress Events
# ---------------------------------------------------------------------------


class TestToolCallProgress:
    """Tests for tool_call_progress event emission."""

    def test_emits_progress_event(
        self, mock_stream_writer, captured_events, sample_tool_call_progress_event
    ):
        """Should emit tool_call_progress event with correct structure."""
        streaming_emitter.emit_tool_progress(**sample_tool_call_progress_event)

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "tool_call_progress"
        assert event["call_id"] == sample_tool_call_progress_event["call_id"]
        assert event["tool_name"] == sample_tool_call_progress_event["tool_name"]
        assert event["message"] == sample_tool_call_progress_event["message"]
        assert event["progress"] == sample_tool_call_progress_event["progress"]
        assert "timestamp" in event

    def test_handles_optional_progress_value(self, mock_stream_writer, captured_events):
        """Should handle when progress percentage is not provided."""
        streaming_emitter.emit_tool_progress(
            call_id="call_123",
            tool_name="search",
            message="Searching...",
        )

        assert len(captured_events) == 1
        assert captured_events[0]["progress"] is None

    def test_handles_optional_metadata(self, mock_stream_writer, captured_events):
        """Should include optional metadata when provided."""
        streaming_emitter.emit_tool_progress(
            call_id="call_123",
            tool_name="search",
            message="Searching...",
            progress=50,
            metadata={"collections_searched": 3},
        )

        assert len(captured_events) == 1
        assert captured_events[0]["metadata"] == {"collections_searched": 3}

    def test_no_error_when_writer_unavailable(
        self, mock_stream_writer_unavailable, sample_tool_call_progress_event
    ):
        """Should not raise when stream writer is unavailable."""
        streaming_emitter.emit_tool_progress(**sample_tool_call_progress_event)


# ---------------------------------------------------------------------------
# TestToolCallComplete - Tool Completion Events
# ---------------------------------------------------------------------------


class TestToolCallComplete:
    """Tests for tool_call_complete event emission."""

    def test_emits_complete_event(
        self, mock_stream_writer, captured_events, sample_tool_call_complete_event
    ):
        """Should emit tool_call_complete event with correct structure."""
        streaming_emitter.emit_tool_complete(**sample_tool_call_complete_event)

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "tool_call_complete"
        assert event["call_id"] == sample_tool_call_complete_event["call_id"]
        assert event["tool_name"] == sample_tool_call_complete_event["tool_name"]
        assert event["duration_ms"] == sample_tool_call_complete_event["duration_ms"]
        assert "timestamp" in event

    def test_truncates_long_result_preview(self, mock_stream_writer, captured_events):
        """Should truncate result_preview to 500 characters."""
        long_result = "A" * 1000  # 1000 characters

        streaming_emitter.emit_tool_complete(
            call_id="call_123",
            tool_name="search",
            result_preview=long_result,
            duration_ms=100,
        )

        assert len(captured_events) == 1
        assert len(captured_events[0]["result_preview"]) == 500

    def test_handles_none_result_preview(self, mock_stream_writer, captured_events):
        """Should handle None result_preview."""
        streaming_emitter.emit_tool_complete(
            call_id="call_123",
            tool_name="search",
            result_preview=None,
            duration_ms=100,
        )

        assert len(captured_events) == 1
        assert captured_events[0]["result_preview"] is None

    def test_no_error_when_writer_unavailable(
        self, mock_stream_writer_unavailable, sample_tool_call_complete_event
    ):
        """Should not raise when stream writer is unavailable."""
        streaming_emitter.emit_tool_complete(**sample_tool_call_complete_event)


# ---------------------------------------------------------------------------
# TestToolCallError - Tool Error Events
# ---------------------------------------------------------------------------


class TestToolCallError:
    """Tests for tool_call_error event emission."""

    def test_emits_error_event(
        self, mock_stream_writer, captured_events, sample_tool_call_error_event
    ):
        """Should emit tool_call_error event with correct structure."""
        streaming_emitter.emit_tool_error(**sample_tool_call_error_event)

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "tool_call_error"
        assert event["call_id"] == sample_tool_call_error_event["call_id"]
        assert event["tool_name"] == sample_tool_call_error_event["tool_name"]
        assert event["error"] == sample_tool_call_error_event["error"]
        assert event["duration_ms"] == sample_tool_call_error_event["duration_ms"]
        assert "timestamp" in event

    def test_no_error_when_writer_unavailable(
        self, mock_stream_writer_unavailable, sample_tool_call_error_event
    ):
        """Should not raise when stream writer is unavailable."""
        streaming_emitter.emit_tool_error(**sample_tool_call_error_event)


# ---------------------------------------------------------------------------
# TestSubAgentStart - Sub-Agent Start Events
# ---------------------------------------------------------------------------


class TestSubAgentStart:
    """Tests for subagent_start event emission."""

    def test_emits_subagent_start_event(
        self, mock_stream_writer, captured_events, sample_subagent_start_event
    ):
        """Should emit subagent_start event with correct structure."""
        streaming_emitter.emit_subagent_start(**sample_subagent_start_event)

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "subagent_start"
        assert event["subagent_id"] == sample_subagent_start_event["subagent_id"]
        assert event["subagent_name"] == sample_subagent_start_event["subagent_name"]
        assert (
            event["task_description"] == sample_subagent_start_event["task_description"]
        )
        assert (
            event["parent_agent_id"] == sample_subagent_start_event["parent_agent_id"]
        )
        assert (
            event["parent_agent_name"]
            == sample_subagent_start_event["parent_agent_name"]
        )
        assert "timestamp" in event

    def test_no_error_when_writer_unavailable(
        self, mock_stream_writer_unavailable, sample_subagent_start_event
    ):
        """Should not raise when stream writer is unavailable."""
        streaming_emitter.emit_subagent_start(**sample_subagent_start_event)


# ---------------------------------------------------------------------------
# TestSubAgentComplete - Sub-Agent Completion Events
# ---------------------------------------------------------------------------


class TestSubAgentComplete:
    """Tests for subagent_complete event emission."""

    def test_emits_subagent_complete_event_success(
        self, mock_stream_writer, captured_events, sample_subagent_complete_event
    ):
        """Should emit subagent_complete event for successful completion."""
        streaming_emitter.emit_subagent_complete(**sample_subagent_complete_event)

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "subagent_complete"
        assert event["subagent_id"] == sample_subagent_complete_event["subagent_id"]
        assert event["subagent_name"] == sample_subagent_complete_event["subagent_name"]
        assert event["success"] is True
        assert event["duration_ms"] == sample_subagent_complete_event["duration_ms"]
        assert event["tools_used"] == sample_subagent_complete_event["tools_used"]
        assert "timestamp" in event

    def test_emits_subagent_complete_event_failure(
        self, mock_stream_writer, captured_events
    ):
        """Should emit subagent_complete event for failed completion."""
        streaming_emitter.emit_subagent_complete(
            subagent_id="subagent-001",
            subagent_name="Research Specialist",
            success=False,
            response_preview="Error: LLM call failed",
            duration_ms=1000,
        )

        assert len(captured_events) == 1
        event = captured_events[0]

        assert event["event_type"] == "subagent_complete"
        assert event["success"] is False

    def test_truncates_long_response_preview(self, mock_stream_writer, captured_events):
        """Should truncate response_preview to 500 characters."""
        long_response = "B" * 1000

        streaming_emitter.emit_subagent_complete(
            subagent_id="subagent-001",
            subagent_name="Agent",
            success=True,
            response_preview=long_response,
            duration_ms=100,
        )

        assert len(captured_events) == 1
        assert len(captured_events[0]["response_preview"]) == 500

    def test_handles_empty_tools_used(self, mock_stream_writer, captured_events):
        """Should handle empty tools_used list."""
        streaming_emitter.emit_subagent_complete(
            subagent_id="subagent-001",
            subagent_name="Agent",
            success=True,
            duration_ms=100,
        )

        assert len(captured_events) == 1
        assert captured_events[0]["tools_used"] == []

    def test_no_error_when_writer_unavailable(
        self, mock_stream_writer_unavailable, sample_subagent_complete_event
    ):
        """Should not raise when stream writer is unavailable."""
        streaming_emitter.emit_subagent_complete(**sample_subagent_complete_event)


# ---------------------------------------------------------------------------
# TestEventSequence - Multiple Events
# ---------------------------------------------------------------------------


class TestEventSequence:
    """Tests for sequences of streaming events."""

    def test_complete_tool_call_sequence(self, mock_stream_writer, captured_events):
        """Should emit complete tool call sequence: start -> progress -> complete."""
        call_id = "call_xyz789"
        tool_name = "document_search"

        # Start
        streaming_emitter.emit_tool_start(
            call_id=call_id,
            tool_name=tool_name,
            tool_args={"query": "test"},
            agent_id="agent-001",
            agent_name="Test Agent",
        )

        # Progress updates
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=tool_name,
            message="Searching collections...",
            progress=30,
        )

        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=tool_name,
            message="Found 5 results, ranking...",
            progress=70,
        )

        # Complete
        streaming_emitter.emit_tool_complete(
            call_id=call_id,
            tool_name=tool_name,
            result_preview="Document 1: ...",
            duration_ms=1500,
        )

        assert len(captured_events) == 4
        assert captured_events[0]["event_type"] == "tool_call_start"
        assert captured_events[1]["event_type"] == "tool_call_progress"
        assert captured_events[2]["event_type"] == "tool_call_progress"
        assert captured_events[3]["event_type"] == "tool_call_complete"

        # All should have same call_id
        for event in captured_events:
            assert event["call_id"] == call_id

    def test_subagent_with_nested_tool_calls(self, mock_stream_writer, captured_events):
        """Should emit subagent events with nested tool calls."""
        subagent_id = "subagent-research-001"

        # Sub-agent starts
        streaming_emitter.emit_subagent_start(
            subagent_id=subagent_id,
            subagent_name="Research Agent",
            task_description="Find documents",
            parent_agent_id="orchestrator-001",
            parent_agent_name="Orchestrator",
        )

        # Tool call within sub-agent
        streaming_emitter.emit_tool_start(
            call_id="call_nested_1",
            tool_name="document_search",
            tool_args={"query": "test"},
            agent_id=subagent_id,
            agent_name="Research Agent",
        )

        streaming_emitter.emit_tool_complete(
            call_id="call_nested_1",
            tool_name="document_search",
            result_preview="Found 3 documents",
            duration_ms=500,
        )

        # Sub-agent completes
        streaming_emitter.emit_subagent_complete(
            subagent_id=subagent_id,
            subagent_name="Research Agent",
            success=True,
            response_preview="Task completed successfully",
            duration_ms=2000,
            tools_used=["document_search"],
        )

        assert len(captured_events) == 4
        assert captured_events[0]["event_type"] == "subagent_start"
        assert captured_events[1]["event_type"] == "tool_call_start"
        assert captured_events[2]["event_type"] == "tool_call_complete"
        assert captured_events[3]["event_type"] == "subagent_complete"

    def test_parallel_tool_calls(self, mock_stream_writer, captured_events):
        """Should handle parallel tool calls with different call_ids."""
        # Start two tools in parallel
        streaming_emitter.emit_tool_start(
            call_id="call_1",
            tool_name="document_search",
            tool_args={"query": "topic A"},
            agent_id="agent-001",
            agent_name="Agent",
        )

        streaming_emitter.emit_tool_start(
            call_id="call_2",
            tool_name="web_search",
            tool_args={"query": "topic B"},
            agent_id="agent-001",
            agent_name="Agent",
        )

        # Progress for both
        streaming_emitter.emit_tool_progress(
            call_id="call_1",
            tool_name="document_search",
            message="Searching...",
            progress=50,
        )

        streaming_emitter.emit_tool_progress(
            call_id="call_2",
            tool_name="web_search",
            message="Searching...",
            progress=30,
        )

        # Complete in different order
        streaming_emitter.emit_tool_complete(
            call_id="call_2", tool_name="web_search", duration_ms=800
        )

        streaming_emitter.emit_tool_complete(
            call_id="call_1", tool_name="document_search", duration_ms=1200
        )

        assert len(captured_events) == 6

        # Verify call_ids are distinct and trackable
        call_1_events = [e for e in captured_events if e["call_id"] == "call_1"]
        call_2_events = [e for e in captured_events if e["call_id"] == "call_2"]

        assert len(call_1_events) == 3  # start, progress, complete
        assert len(call_2_events) == 3  # start, progress, complete


# ---------------------------------------------------------------------------
# TestToolCallStartWithNodeInfo - Tool Start Events with Node Info
# ---------------------------------------------------------------------------


class TestToolCallStartWithNodeInfo:
    """Tests for emit_tool_start with new tool_node_* parameters (Phase 9)."""

    def test_emit_tool_start_includes_node_info(
        self, mock_stream_writer, captured_events
    ):
        """Should include tool_node_id, tool_node_name, tool_node_type in event."""
        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="search_documents_abc123",
            tool_args={"query": "test"},
            agent_id="agent_1",
            agent_name="Research Agent",
            tool_node_id="node_doc_search_456",
            tool_node_name="Document Search",
            tool_node_type="DOCUMENT_SEARCH",
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["event_type"] == "tool_call_start"
        assert event["tool_node_id"] == "node_doc_search_456"
        assert event["tool_node_name"] == "Document Search"
        assert event["tool_node_type"] == "DOCUMENT_SEARCH"

    def test_emit_tool_start_node_info_optional(
        self, mock_stream_writer, captured_events
    ):
        """Should work without node info (backward compatible)."""
        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="search_documents_abc123",
            tool_args={"query": "test"},
            agent_id="agent_1",
            agent_name="Research Agent",
            # No tool_node_* params
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["tool_node_id"] is None
        assert event["tool_node_name"] is None
        assert event["tool_node_type"] is None

    def test_emit_tool_start_partial_node_info(
        self, mock_stream_writer, captured_events
    ):
        """Should handle partial node info (only some fields provided)."""
        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="http_request_xyz",
            tool_args={"url": "https://api.example.com"},
            agent_id="agent_1",
            agent_name="API Agent",
            tool_node_id="node_http_789",
            # tool_node_name and tool_node_type not provided
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["tool_node_id"] == "node_http_789"
        assert event["tool_node_name"] is None
        assert event["tool_node_type"] is None


# ---------------------------------------------------------------------------
# TestToolCallCompleteWithNodeInfo - Tool Complete Events with Node Info
# ---------------------------------------------------------------------------


class TestToolCallCompleteWithNodeInfo:
    """Tests for emit_tool_complete with new tool_node_* parameters (Phase 9)."""

    def test_emit_tool_complete_includes_node_info(
        self, mock_stream_writer, captured_events
    ):
        """Should include node info in completion event."""
        streaming_emitter.emit_tool_complete(
            call_id="call_123",
            tool_name="search_documents_abc123",
            result_preview="Found 5 documents...",
            duration_ms=1500.0,
            tool_node_id="node_doc_search_456",
            tool_node_name="Document Search",
            tool_node_type="DOCUMENT_SEARCH",
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["event_type"] == "tool_call_complete"
        assert event["tool_node_id"] == "node_doc_search_456"
        assert event["tool_node_name"] == "Document Search"
        assert event["tool_node_type"] == "DOCUMENT_SEARCH"

    def test_emit_tool_complete_node_info_optional(
        self, mock_stream_writer, captured_events
    ):
        """Should work without node info (backward compatible)."""
        streaming_emitter.emit_tool_complete(
            call_id="call_123",
            tool_name="search_documents_abc123",
            result_preview="Found results",
            duration_ms=1000.0,
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["tool_node_id"] is None
        assert event["tool_node_name"] is None
        assert event["tool_node_type"] is None


# ---------------------------------------------------------------------------
# TestToolCallErrorWithNodeInfo - Tool Error Events with Node Info
# ---------------------------------------------------------------------------


class TestToolCallErrorWithNodeInfo:
    """Tests for emit_tool_error with new tool_node_* parameters (Phase 9)."""

    def test_emit_tool_error_includes_node_info(
        self, mock_stream_writer, captured_events
    ):
        """Should include node info in error event."""
        streaming_emitter.emit_tool_error(
            call_id="call_123",
            tool_name="http_request_abc123",
            error="Connection timeout",
            duration_ms=5000.0,
            tool_node_id="node_http_789",
            tool_node_name="API Request",
            tool_node_type="HTTP_REQUEST",
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["event_type"] == "tool_call_error"
        assert event["tool_node_id"] == "node_http_789"
        assert event["tool_node_name"] == "API Request"
        assert event["tool_node_type"] == "HTTP_REQUEST"

    def test_emit_tool_error_node_info_optional(
        self, mock_stream_writer, captured_events
    ):
        """Should work without node info (backward compatible)."""
        streaming_emitter.emit_tool_error(
            call_id="call_123",
            tool_name="database_query_xyz",
            error="Query failed",
            duration_ms=1000.0,
        )

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event["tool_node_id"] is None
        assert event["tool_node_name"] is None
        assert event["tool_node_type"] is None


# ---------------------------------------------------------------------------
# TestToolNodeInfoInSequence - Node Info in Complete Sequences
# ---------------------------------------------------------------------------


class TestToolNodeInfoInSequence:
    """Tests for node info consistency across tool call sequences (Phase 9)."""

    def test_node_info_consistent_across_start_and_complete(
        self, mock_stream_writer, captured_events
    ):
        """Should have consistent node info in start and complete events."""
        node_id = "node_doc_456"
        node_name = "Document Search"
        node_type = "DOCUMENT_SEARCH"

        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="search_documents_abc",
            tool_args={"query": "test"},
            agent_id="agent_1",
            agent_name="Agent",
            tool_node_id=node_id,
            tool_node_name=node_name,
            tool_node_type=node_type,
        )

        streaming_emitter.emit_tool_complete(
            call_id="call_123",
            tool_name="search_documents_abc",
            result_preview="Results",
            duration_ms=1000.0,
            tool_node_id=node_id,
            tool_node_name=node_name,
            tool_node_type=node_type,
        )

        assert len(captured_events) == 2

        start_event = captured_events[0]
        complete_event = captured_events[1]

        # Both should have same node info
        assert start_event["tool_node_id"] == complete_event["tool_node_id"] == node_id
        assert (
            start_event["tool_node_name"]
            == complete_event["tool_node_name"]
            == node_name
        )
        assert (
            start_event["tool_node_type"]
            == complete_event["tool_node_type"]
            == node_type
        )

    def test_node_info_in_error_sequence(self, mock_stream_writer, captured_events):
        """Should have consistent node info in start and error events."""
        node_id = "node_http_789"
        node_name = "API Request"
        node_type = "HTTP_REQUEST"

        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="http_request_xyz",
            tool_args={"url": "https://example.com"},
            agent_id="agent_1",
            agent_name="Agent",
            tool_node_id=node_id,
            tool_node_name=node_name,
            tool_node_type=node_type,
        )

        streaming_emitter.emit_tool_error(
            call_id="call_123",
            tool_name="http_request_xyz",
            error="Connection refused",
            duration_ms=5000.0,
            tool_node_id=node_id,
            tool_node_name=node_name,
            tool_node_type=node_type,
        )

        assert len(captured_events) == 2

        start_event = captured_events[0]
        error_event = captured_events[1]

        # Both should have same node info
        assert start_event["tool_node_id"] == error_event["tool_node_id"] == node_id
        assert (
            start_event["tool_node_name"] == error_event["tool_node_name"] == node_name
        )
        assert (
            start_event["tool_node_type"] == error_event["tool_node_type"] == node_type
        )
