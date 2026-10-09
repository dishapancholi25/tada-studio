"""Tests for AsyncToolExecutor tool_node_mapping integration and stuck-loop detection.

These tests verify that the tool executor correctly:
1. Passes tool_node_mapping through execute_with_tools
2. Looks up node info from mapping in _execute_single_tool
3. Includes node info in streaming events for timeline updates
4. Handles missing mappings gracefully (backward compatibility)
5. Detects stuck tool-calling loops via _detect_stuck_loop
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from backend.services.execution.async_agent.tool_executor import (
    _detect_stuck_loop,
    _hash_tool_call,
)


class TestToolNodeMappingIntegration:
    """Tests for tool_node_mapping parameter in tool executor."""

    @pytest.fixture
    def tool_node_mapping(self):
        """Sample tool-to-node mapping for testing."""
        return {
            "search_documents_abc123": {
                "node_id": "node_doc_456",
                "node_name": "Document Search",
                "node_type": "DOCUMENT_SEARCH",
            },
            "http_request_xyz789": {
                "node_id": "node_http_101",
                "node_name": "API Call",
                "node_type": "HTTP_REQUEST",
            },
        }

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        tool = MagicMock()
        tool.name = "search_documents_abc123"
        tool.ainvoke = AsyncMock(return_value="Search results: found 5 documents")
        return tool

    @pytest.fixture
    def mock_http_tool(self):
        """Create a mock HTTP tool."""
        tool = MagicMock()
        tool.name = "http_request_xyz789"
        tool.ainvoke = AsyncMock(return_value='{"status": "ok"}')
        return tool

    @pytest.fixture
    def tool_executor(self):
        """Create an AsyncToolExecutor instance."""
        from backend.services.execution.async_agent.tool_executor import (
            AsyncToolExecutor,
        )

        return AsyncToolExecutor()

    @pytest.fixture
    def captured_events(self):
        """List to capture emitted streaming events."""
        return []

    @pytest.fixture
    def mock_stream_writer(self, captured_events):
        """Mock the streaming emitter to capture events."""
        with patch(
            "backend.services.execution.async_agent.tool_executor.streaming_emitter"
        ) as mock_emitter:
            # Capture emit_tool_start calls
            def capture_start(**kwargs):
                captured_events.append({"event_type": "tool_call_start", **kwargs})

            def capture_complete(**kwargs):
                captured_events.append({"event_type": "tool_call_complete", **kwargs})

            def capture_error(**kwargs):
                captured_events.append({"event_type": "tool_call_error", **kwargs})

            mock_emitter.emit_tool_start = MagicMock(side_effect=capture_start)
            mock_emitter.emit_tool_complete = MagicMock(side_effect=capture_complete)
            mock_emitter.emit_tool_error = MagicMock(side_effect=capture_error)

            yield mock_emitter

    @pytest.mark.asyncio
    async def test_execute_with_tools_passes_mapping_to_process(
        self, tool_executor, tool_node_mapping, mock_llm
    ):
        """Verify tool_node_mapping is passed through to process_tool_calls."""
        tool_call = {
            "id": "call_123",
            "name": "search_documents_abc123",
            "args": {"query": "test"},
        }

        # Mock the LLM responses
        tool_response = AIMessage(content="", tool_calls=[tool_call])
        final_response = AIMessage(content="Here are the results.")

        # Mock _invoke_with_streaming to return tool call first, then final response
        with patch.object(
            tool_executor,
            "_invoke_with_streaming",
            new=AsyncMock(side_effect=[tool_response, final_response]),
        ):
            # Mock process_tool_calls to verify mapping is passed
            with patch.object(tool_executor, "process_tool_calls") as mock_process:
                mock_process.return_value = [
                    MagicMock(content="Results", tool_call_id="call_123")
                ]

                # Create mock tools
                mock_tool = MagicMock(name="search_documents_abc123")
                mock_llm.bind_tools = MagicMock(return_value=mock_llm)

                await tool_executor.execute_with_tools(
                    llm=mock_llm,
                    messages=[],
                    tools=[mock_tool],
                    tool_node_mapping=tool_node_mapping,
                )

                # Verify process_tool_calls was called with mapping
                mock_process.assert_called()
                _, kwargs = mock_process.call_args
                assert kwargs.get("tool_node_mapping") == tool_node_mapping

    @pytest.mark.asyncio
    async def test_execute_single_tool_uses_mapping(
        self,
        tool_executor,
        tool_node_mapping,
        mock_tool,
        mock_stream_writer,
        captured_events,
    ):
        """Verify _execute_single_tool looks up node info from mapping."""
        tool_call = {
            "id": "call_123",
            "name": "search_documents_abc123",
            "args": {"query": "test query"},
        }

        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[mock_tool],
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping=tool_node_mapping,
        )

        # Find the start event
        start_events = [
            e for e in captured_events if e["event_type"] == "tool_call_start"
        ]
        assert len(start_events) == 1

        start_event = start_events[0]
        assert start_event["tool_node_id"] == "node_doc_456"
        assert start_event["tool_node_name"] == "Document Search"
        assert start_event["tool_node_type"] == "DOCUMENT_SEARCH"

        # Verify complete event also has node info
        complete_events = [
            e for e in captured_events if e["event_type"] == "tool_call_complete"
        ]
        assert len(complete_events) == 1

        complete_event = complete_events[0]
        assert complete_event["tool_node_id"] == "node_doc_456"
        assert complete_event["tool_node_name"] == "Document Search"
        assert complete_event["tool_node_type"] == "DOCUMENT_SEARCH"

    @pytest.mark.asyncio
    async def test_execute_single_tool_handles_missing_mapping(
        self,
        tool_executor,
        mock_stream_writer,
        captured_events,
    ):
        """Verify graceful handling when tool not in mapping."""
        # Create a tool that's NOT in the mapping
        unknown_tool = MagicMock()
        unknown_tool.name = "unknown_tool_xyz"
        unknown_tool.ainvoke = AsyncMock(return_value="Unknown result")

        tool_call = {
            "id": "call_456",
            "name": "unknown_tool_xyz",
            "args": {},
        }

        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[unknown_tool],
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping={},  # Empty mapping
        )

        # Should still emit event with None node_id and tool_name as fallback
        start_events = [
            e for e in captured_events if e["event_type"] == "tool_call_start"
        ]
        assert len(start_events) == 1

        start_event = start_events[0]
        assert start_event["tool_node_id"] is None
        assert (
            start_event["tool_node_name"] == "unknown_tool_xyz"
        )  # Falls back to tool_name
        assert start_event["tool_node_type"] is None

    @pytest.mark.asyncio
    async def test_execute_single_tool_handles_no_mapping_param(
        self,
        tool_executor,
        mock_tool,
        mock_stream_writer,
        captured_events,
    ):
        """Verify backward compatibility when tool_node_mapping is None."""
        tool_call = {
            "id": "call_789",
            "name": "search_documents_abc123",
            "args": {"query": "test"},
        }

        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[mock_tool],
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping=None,  # No mapping provided (backward compat)
        )

        # Should still emit events without node info
        start_events = [
            e for e in captured_events if e["event_type"] == "tool_call_start"
        ]
        assert len(start_events) == 1

        start_event = start_events[0]
        assert start_event["tool_node_id"] is None
        assert start_event["tool_node_name"] == "search_documents_abc123"
        assert start_event["tool_node_type"] is None

    @pytest.mark.asyncio
    async def test_tool_error_includes_node_info(
        self,
        tool_executor,
        tool_node_mapping,
        mock_stream_writer,
        captured_events,
    ):
        """Verify node info is included in error events."""
        # Create a tool that raises an error
        failing_tool = MagicMock()
        failing_tool.name = "http_request_xyz789"
        failing_tool.ainvoke = AsyncMock(side_effect=Exception("Connection timeout"))

        tool_call = {
            "id": "call_error",
            "name": "http_request_xyz789",
            "args": {"url": "https://example.com"},
        }

        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[failing_tool],
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping=tool_node_mapping,
        )

        # Should have start event with node info
        start_events = [
            e for e in captured_events if e["event_type"] == "tool_call_start"
        ]
        assert len(start_events) == 1
        assert start_events[0]["tool_node_id"] == "node_http_101"

        # Should have error event with node info
        error_events = [
            e for e in captured_events if e["event_type"] == "tool_call_error"
        ]
        assert len(error_events) == 1

        error_event = error_events[0]
        assert error_event["tool_node_id"] == "node_http_101"
        assert error_event["tool_node_name"] == "API Call"
        assert error_event["tool_node_type"] == "HTTP_REQUEST"
        assert "Connection timeout" in error_event["error"]

    @pytest.mark.asyncio
    async def test_tool_not_found_includes_node_info(
        self,
        tool_executor,
        tool_node_mapping,
        mock_stream_writer,
        captured_events,
    ):
        """Verify node info is included even when tool is not found."""
        tool_call = {
            "id": "call_notfound",
            "name": "search_documents_abc123",
            "args": {"query": "test"},
        }

        # Pass empty tools list - tool won't be found
        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[],  # No tools available
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping=tool_node_mapping,
        )

        # Should have error event with node info
        error_events = [
            e for e in captured_events if e["event_type"] == "tool_call_error"
        ]
        assert len(error_events) == 1

        error_event = error_events[0]
        assert error_event["tool_node_id"] == "node_doc_456"
        assert error_event["tool_node_name"] == "Document Search"
        assert "not found" in error_event["error"].lower()


class TestProcessToolCallsWithMapping:
    """Tests for process_tool_calls with tool_node_mapping."""

    @pytest.fixture
    def tool_executor(self):
        """Create an AsyncToolExecutor instance."""
        from backend.services.execution.async_agent.tool_executor import (
            AsyncToolExecutor,
        )

        return AsyncToolExecutor()

    @pytest.fixture
    def tool_node_mapping(self):
        """Sample mapping."""
        return {
            "tool_a": {
                "node_id": "node_a",
                "node_name": "Tool A",
                "node_type": "CUSTOM",
            },
            "tool_b": {
                "node_id": "node_b",
                "node_name": "Tool B",
                "node_type": "CUSTOM",
            },
        }

    @pytest.mark.asyncio
    async def test_process_tool_calls_passes_mapping(
        self, tool_executor, tool_node_mapping
    ):
        """Verify process_tool_calls passes mapping to _execute_single_tool."""
        tool_calls = [
            {"id": "call_1", "name": "tool_a", "args": {}},
            {"id": "call_2", "name": "tool_b", "args": {}},
        ]

        # Create mock tools
        tool_a = MagicMock()
        tool_a.name = "tool_a"
        tool_a.ainvoke = AsyncMock(return_value="Result A")

        tool_b = MagicMock()
        tool_b.name = "tool_b"
        tool_b.ainvoke = AsyncMock(return_value="Result B")

        with patch.object(tool_executor, "_execute_single_tool") as mock_execute:
            mock_execute.return_value = ("Result", MagicMock())

            await tool_executor.process_tool_calls(
                tool_calls=tool_calls,
                tools=[tool_a, tool_b],
                agent_name="Test Agent",
                agent_id="agent_1",
                tool_node_mapping=tool_node_mapping,
            )

            # Verify _execute_single_tool was called with mapping for each tool
            assert mock_execute.call_count == 2

            for call in mock_execute.call_args_list:
                _, kwargs = call
                # Mapping is passed as positional arg in asyncio.gather call
                # Check it was included in the call
                assert (
                    tool_node_mapping == kwargs.get("tool_node_mapping")
                    or tool_node_mapping in call[0]
                )


class TestMappingLookupEdgeCases:
    """Edge case tests for tool_node_mapping lookup."""

    @pytest.fixture
    def tool_executor(self):
        """Create an AsyncToolExecutor instance."""
        from backend.services.execution.async_agent.tool_executor import (
            AsyncToolExecutor,
        )

        return AsyncToolExecutor()

    @pytest.fixture
    def captured_events(self):
        """List to capture emitted streaming events."""
        return []

    @pytest.fixture
    def mock_stream_writer(self, captured_events):
        """Mock the streaming emitter to capture events."""
        with patch(
            "backend.services.execution.async_agent.tool_executor.streaming_emitter"
        ) as mock_emitter:

            def capture_start(**kwargs):
                captured_events.append({"event_type": "tool_call_start", **kwargs})

            def capture_complete(**kwargs):
                captured_events.append({"event_type": "tool_call_complete", **kwargs})

            mock_emitter.emit_tool_start = MagicMock(side_effect=capture_start)
            mock_emitter.emit_tool_complete = MagicMock(side_effect=capture_complete)
            mock_emitter.emit_tool_error = MagicMock()

            yield mock_emitter

    @pytest.mark.asyncio
    async def test_partial_mapping_info(
        self,
        tool_executor,
        mock_stream_writer,
        captured_events,
    ):
        """Verify handling when mapping has partial node info."""
        # Mapping with only node_id (missing node_name and node_type)
        partial_mapping = {
            "partial_tool": {
                "node_id": "node_partial",
                # Missing node_name and node_type
            }
        }

        mock_tool = MagicMock()
        mock_tool.name = "partial_tool"
        mock_tool.ainvoke = AsyncMock(return_value="Result")

        tool_call = {
            "id": "call_partial",
            "name": "partial_tool",
            "args": {},
        }

        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[mock_tool],
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping=partial_mapping,
        )

        start_events = [
            e for e in captured_events if e["event_type"] == "tool_call_start"
        ]
        assert len(start_events) == 1

        start_event = start_events[0]
        assert start_event["tool_node_id"] == "node_partial"
        # Should fall back to tool_name when node_name not in mapping
        assert start_event["tool_node_name"] == "partial_tool"
        assert start_event["tool_node_type"] is None

    @pytest.mark.asyncio
    async def test_empty_mapping_dict_for_tool(
        self,
        tool_executor,
        mock_stream_writer,
        captured_events,
    ):
        """Verify handling when mapping has empty dict for tool."""
        empty_mapping = {
            "empty_tool": {}  # Empty dict
        }

        mock_tool = MagicMock()
        mock_tool.name = "empty_tool"
        mock_tool.ainvoke = AsyncMock(return_value="Result")

        tool_call = {
            "id": "call_empty",
            "name": "empty_tool",
            "args": {},
        }

        await tool_executor._execute_single_tool(
            tool_call=tool_call,
            tools=[mock_tool],
            agent_name="Test Agent",
            agent_id="agent_1",
            tool_node_mapping=empty_mapping,
        )

        start_events = [
            e for e in captured_events if e["event_type"] == "tool_call_start"
        ]
        assert len(start_events) == 1

        start_event = start_events[0]
        assert start_event["tool_node_id"] is None
        assert start_event["tool_node_name"] == "empty_tool"
        assert start_event["tool_node_type"] is None


class TestStuckLoopDetection:
    """Tests for _detect_stuck_loop and _hash_tool_call helpers."""

    def test_hash_tool_call_deterministic(self):
        """Same name and args always produce the same hash."""
        a = _hash_tool_call("search", {"query": "hello"})
        b = _hash_tool_call("search", {"query": "hello"})
        assert a == b

    def test_hash_tool_call_differs_on_args(self):
        """Different args produce different hashes."""
        a = _hash_tool_call("search", {"query": "hello"})
        b = _hash_tool_call("search", {"query": "world"})
        assert a != b

    def test_hash_tool_call_differs_on_name(self):
        """Different tool names produce different tuples."""
        a = _hash_tool_call("search", {"query": "hello"})
        b = _hash_tool_call("fetch", {"query": "hello"})
        assert a[0] != b[0]

    def test_no_detection_below_threshold(self):
        """No stuck loop detected with fewer iterations than threshold."""
        call = _hash_tool_call("search", {"query": "hello"})
        history = [[call], [call]]  # Only 2 consecutive
        assert _detect_stuck_loop(history, threshold=3) is None

    def test_detection_at_threshold(self):
        """Stuck loop detected at exactly the threshold."""
        call = _hash_tool_call("search", {"query": "hello"})
        history = [[call], [call], [call]]  # Exactly 3
        result = _detect_stuck_loop(history, threshold=3)
        assert result is not None
        assert result[0] == "search"
        assert result[1] == 3

    def test_detection_above_threshold(self):
        """Stuck loop detected above the threshold with correct count."""
        call = _hash_tool_call("search", {"query": "hello"})
        history = [[call], [call], [call], [call], [call]]  # 5 consecutive
        result = _detect_stuck_loop(history, threshold=3)
        assert result is not None
        assert result[0] == "search"
        assert result[1] == 5

    def test_no_detection_with_different_args(self):
        """Same tool with different args across iterations is not a stuck loop."""
        history = [
            [_hash_tool_call("search", {"query": "cats"})],
            [_hash_tool_call("search", {"query": "dogs"})],
            [_hash_tool_call("search", {"query": "birds"})],
        ]
        assert _detect_stuck_loop(history, threshold=3) is None

    def test_no_detection_with_mixed_tools(self):
        """Different tools across iterations is not a stuck loop."""
        history = [
            [_hash_tool_call("search", {"query": "hello"})],
            [_hash_tool_call("fetch", {"url": "http://example.com"})],
            [_hash_tool_call("search", {"query": "hello"})],
        ]
        assert _detect_stuck_loop(history, threshold=3) is None

    def test_detection_with_multiple_calls_per_iteration(self):
        """Detects stuck loop even when iterations have multiple tool calls."""
        stuck_call = _hash_tool_call("search", {"query": "hello"})
        other_call_1 = _hash_tool_call("fetch", {"url": "http://a.com"})
        other_call_2 = _hash_tool_call("fetch", {"url": "http://b.com"})
        history = [
            [stuck_call, other_call_1],
            [stuck_call, other_call_2],
            [stuck_call],  # stuck_call appears in all 3
        ]
        result = _detect_stuck_loop(history, threshold=3)
        assert result is not None
        assert result[0] == "search"

    def test_broken_streak_resets(self):
        """A non-matching iteration in the middle breaks the consecutive count."""
        call = _hash_tool_call("search", {"query": "hello"})
        other = _hash_tool_call("search", {"query": "different"})
        history = [
            [call],
            [call],
            [other],  # Breaks the streak
            [call],
            [call],
        ]
        assert _detect_stuck_loop(history, threshold=3) is None

    def test_empty_history(self):
        """Empty call history returns None."""
        assert _detect_stuck_loop([], threshold=3) is None
