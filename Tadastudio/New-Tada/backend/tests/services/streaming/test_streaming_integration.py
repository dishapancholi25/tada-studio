"""Integration tests for streaming functionality.

These tests verify end-to-end streaming behavior using realistic
workflow configurations like the DocTest workflow with an agent
and document search tool.
"""

import pytest
from unittest.mock import patch, AsyncMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def doctest_workflow_json():
    """Load the DocTest workflow JSON for integration testing.

    This workflow contains:
    - Start node
    - Agent 1 (with document search tool connected)
    - Document Search node (as tool)
    - End node
    """
    return {
        "name": "DocTest",
        "description": "",
        "nodes": [
            {
                "uniq_id": "15a332f9-c0c3-4d28-98fb-9ff6cb983371",
                "name": "Start",
                "type": "START",
                "nexts": ["9a7299e4-f7de-45d5-8fde-0cc74d95d6d7"],
                "inputs": [],
            },
            {
                "uniq_id": "9a7299e4-f7de-45d5-8fde-0cc74d95d6d7",
                "name": "Agent 1",
                "type": "AGENT",
                "nexts": [
                    "1724b903-9555-49b9-97ea-aa1af8403bec",
                    "9f36c074-bfbd-4163-8cc0-6594a2111988",
                ],
                "inputs": ["15a332f9-c0c3-4d28-98fb-9ff6cb983371"],
                "agent_config": {
                    "agent_type": "conversational",
                    "system_prompt": "Use your document search tool containing resolved tickets to find information",
                    "max_iterations": 10,
                    "temperature": 0,
                    "tools": [],
                    "llm_config": {
                        "provider": "azure_openai",
                        "model_name": "gpt-4o-mini",
                    },
                },
            },
            {
                "uniq_id": "1724b903-9555-49b9-97ea-aa1af8403bec",
                "name": "End 2",
                "type": "END",
                "nexts": [],
                "inputs": ["9a7299e4-f7de-45d5-8fde-0cc74d95d6d7"],
            },
            {
                "uniq_id": "9f36c074-bfbd-4163-8cc0-6594a2111988",
                "name": "Document Search",
                "type": "DOCUMENT_SEARCH",
                "nexts": [],
                "inputs": ["9a7299e4-f7de-45d5-8fde-0cc74d95d6d7"],
                "document_search_config": {
                    "document_collections": ["25237095-fd60-4b33-b679-fb98f2350bc2"],
                    "document_ids": [],
                    "search_k": 3,
                    "search_type": "similarity",
                    "similarity_threshold": 0.7,
                    "hybrid_search_enabled": True,
                    "search_mode": "hybrid",
                    "keyword_weight": 0.5,
                    "include_confidence_scores": True,
                },
            },
        ],
        "connections": [
            {
                "source_id": "15a332f9-c0c3-4d28-98fb-9ff6cb983371",
                "target_id": "9a7299e4-f7de-45d5-8fde-0cc74d95d6d7",
                "connection_type": "workflow",
            },
            {
                "source_id": "9a7299e4-f7de-45d5-8fde-0cc74d95d6d7",
                "target_id": "1724b903-9555-49b9-97ea-aa1af8403bec",
                "connection_type": "workflow",
            },
            {
                "source_id": "9a7299e4-f7de-45d5-8fde-0cc74d95d6d7",
                "target_id": "9f36c074-bfbd-4163-8cc0-6594a2111988",
                "source_handle": "tools",
                "target_handle": "top",
                "connection_type": "tool",
            },
        ],
    }


# ---------------------------------------------------------------------------
# TestStreamingEventTypes
# ---------------------------------------------------------------------------


class TestStreamingEventTypes:
    """Tests to verify all expected event types are defined and used correctly."""

    def test_all_event_types_supported(self):
        """Verify all streaming event types are supported."""
        from backend.services.streaming import streaming_emitter

        # These methods should exist
        assert hasattr(streaming_emitter, "emit_tool_start")
        assert hasattr(streaming_emitter, "emit_tool_progress")
        assert hasattr(streaming_emitter, "emit_tool_complete")
        assert hasattr(streaming_emitter, "emit_tool_error")
        assert hasattr(streaming_emitter, "emit_subagent_start")
        assert hasattr(streaming_emitter, "emit_subagent_complete")

    def test_event_type_values(self, mock_stream_writer, captured_events):
        """Verify event types have correct string values."""
        from backend.services.streaming import streaming_emitter

        streaming_emitter.emit_tool_start("call_1", "tool", {}, "agent_1", "Agent")
        streaming_emitter.emit_tool_progress("call_1", "tool", "msg")
        streaming_emitter.emit_tool_complete("call_1", "tool")
        streaming_emitter.emit_tool_error("call_2", "tool", "error")
        streaming_emitter.emit_subagent_start(
            "sub_1", "SubAgent", "task", "parent", "Parent"
        )
        streaming_emitter.emit_subagent_complete("sub_1", "SubAgent", True)

        event_types = [e["event_type"] for e in captured_events]

        assert "tool_call_start" in event_types
        assert "tool_call_progress" in event_types
        assert "tool_call_complete" in event_types
        assert "tool_call_error" in event_types
        assert "subagent_start" in event_types
        assert "subagent_complete" in event_types


# ---------------------------------------------------------------------------
# TestToolNodeStreaming
# ---------------------------------------------------------------------------


class TestToolNodeStreaming:
    """Tests for tool node streaming in workflow context."""

    def test_document_search_tool_emits_events(
        self,
        mock_stream_writer,
        captured_events,
    ):
        """Document search tool should emit progress events."""
        from backend.tools.document_search.handlers import execute_search
        from backend.tools.document_search.schemas import DocumentSearchConfig

        with patch(
            "backend.tools.document_search.handlers.document_search_service"
        ) as mock_service:
            mock_service.search_multiple_collections.return_value = [
                {
                    "content": "Document content about tickets",
                    "score": 0.85,
                    "metadata": {"doc_id": "doc-1", "title": "Ticket Resolution"},
                }
            ]

            config = DocumentSearchConfig(
                collection_names=["25237095-fd60-4b33-b679-fb98f2350bc2"],
                search_k=3,
                search_type="similarity",
                similarity_threshold=0.7,
                include_metadata=True,
                hybrid_search_enabled=True,
                search_mode="hybrid",
            )

            _result = execute_search(
                query="Find resolved tickets",
                config=config,
                call_id="call_doc_001",
            )

            # Verify progress events were emitted
            progress_events = [
                e for e in captured_events if e["event_type"] == "tool_call_progress"
            ]

            assert len(progress_events) >= 2

            # Verify all events have correct call_id
            for event in progress_events:
                assert event["call_id"] == "call_doc_001"
                assert event["tool_name"] == "document_search"


# ---------------------------------------------------------------------------
# TestWebSocketEventRouting
# ---------------------------------------------------------------------------


class TestWebSocketEventRouting:
    """Tests for WebSocket event routing of streaming events."""

    @pytest.fixture
    def mock_ws_manager(self):
        """Mock WebSocket manager for testing event routing."""
        manager = AsyncMock()
        manager.send_execution_update = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_custom_events_routed_by_type(self, mock_ws_manager):
        """Custom streaming events should be routed by their event_type."""
        from backend.services.websocket.notifier import WebSocketExecutionNotifier

        notifier = WebSocketExecutionNotifier(mock_ws_manager)

        # Simulate a streaming event with event_type
        event_payload = {
            "event_type": "tool_call_start",
            "call_id": "call_123",
            "tool_name": "document_search",
            "timestamp": "2025-01-01T00:00:00Z",
        }

        # on_stream_event takes (execution_id, event_type, payload)
        # For structured events, the event_type param is ignored and payload's event_type is used
        await notifier.on_stream_event("exec-123", "custom", event_payload)

        # Should have called send_execution_update with specific event type from payload
        mock_ws_manager.send_execution_update.assert_called_once()
        call_args = mock_ws_manager.send_execution_update.call_args

        assert call_args[0][0] == "exec-123"  # execution_id
        assert call_args[0][1] == "tool_call_start"  # event_type from payload
        assert call_args[0][2] == event_payload  # payload

    @pytest.mark.asyncio
    async def test_regular_events_use_provided_type(self, mock_ws_manager):
        """Non-structured events should use provided event_type."""
        from backend.services.websocket.notifier import WebSocketExecutionNotifier

        notifier = WebSocketExecutionNotifier(mock_ws_manager)

        # Simulate a non-structured event (string payload)
        event_payload = "Simple string payload"

        await notifier.on_stream_event("exec-123", "token", event_payload)

        mock_ws_manager.send_execution_update.assert_called_once()
        call_args = mock_ws_manager.send_execution_update.call_args

        assert call_args[0][0] == "exec-123"  # execution_id
        assert call_args[0][1] == "token"  # event_type as provided


# ---------------------------------------------------------------------------
# TestStreamingWithWorkflowExecution
# ---------------------------------------------------------------------------


class TestStreamingWithWorkflowExecution:
    """Integration tests for streaming during workflow execution."""

    @pytest.fixture
    def mock_workflow_dependencies(self):
        """Mock all dependencies for workflow execution."""
        mocks = {}

        with (
            patch(
                "backend.services.execution.async_agent.tool_executor.streaming_emitter"
            ) as mock_tool_emitter,
            patch(
                "backend.services.delegation.executors.subgraph_executor.streaming_emitter"
            ) as mock_subagent_emitter,
        ):
            mocks["tool_emitter"] = mock_tool_emitter
            mocks["subagent_emitter"] = mock_subagent_emitter
            yield mocks

    def test_tool_executor_has_streaming_emitter_import(
        self, mock_workflow_dependencies
    ):
        """Tool executor module should import streaming_emitter."""
        from backend.services.execution.async_agent import tool_executor

        # Verify the module imports streaming_emitter
        assert hasattr(tool_executor, "streaming_emitter")

    def test_tool_executor_has_execute_single_tool_method(self):
        """Tool executor should have _execute_single_tool method."""
        from backend.services.execution.async_agent.tool_executor import (
            AsyncToolExecutor,
        )

        executor = AsyncToolExecutor()

        # The executor should have methods for tool execution
        assert hasattr(executor, "_execute_single_tool")


# ---------------------------------------------------------------------------
# TestStreamingEventStructure
# ---------------------------------------------------------------------------


class TestStreamingEventStructure:
    """Tests for streaming event data structure validation."""

    def test_tool_call_start_structure(self, mock_stream_writer, captured_events):
        """tool_call_start events should have required fields."""
        from backend.services.streaming import streaming_emitter

        streaming_emitter.emit_tool_start(
            call_id="call_123",
            tool_name="test_tool",
            tool_args={"query": "test"},
            agent_id="agent_001",
            agent_name="Test Agent",
        )

        event = captured_events[0]
        required_fields = [
            "event_type",
            "call_id",
            "tool_name",
            "tool_args",
            "agent_id",
            "agent_name",
            "timestamp",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"

    def test_tool_call_progress_structure(self, mock_stream_writer, captured_events):
        """tool_call_progress events should have required fields."""
        from backend.services.streaming import streaming_emitter

        streaming_emitter.emit_tool_progress(
            call_id="call_123",
            tool_name="test_tool",
            message="Processing...",
            progress=50,
        )

        event = captured_events[0]
        required_fields = [
            "event_type",
            "call_id",
            "tool_name",
            "message",
            "progress",
            "timestamp",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"

    def test_subagent_start_structure(self, mock_stream_writer, captured_events):
        """subagent_start events should have required fields."""
        from backend.services.streaming import streaming_emitter

        streaming_emitter.emit_subagent_start(
            subagent_id="subagent_001",
            subagent_name="Research Agent",
            task_description="Find documents",
            parent_agent_id="orchestrator_001",
            parent_agent_name="Orchestrator",
        )

        event = captured_events[0]
        required_fields = [
            "event_type",
            "subagent_id",
            "subagent_name",
            "task_description",
            "parent_agent_id",
            "parent_agent_name",
            "timestamp",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"

    def test_subagent_complete_structure(self, mock_stream_writer, captured_events):
        """subagent_complete events should have required fields."""
        from backend.services.streaming import streaming_emitter

        streaming_emitter.emit_subagent_complete(
            subagent_id="subagent_001",
            subagent_name="Research Agent",
            success=True,
            response_preview="Found 3 documents",
            duration_ms=1500.5,
            tools_used=["document_search"],
        )

        event = captured_events[0]
        required_fields = [
            "event_type",
            "subagent_id",
            "subagent_name",
            "success",
            "duration_ms",
            "tools_used",
            "timestamp",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# TestDocTestWorkflowStreaming
# ---------------------------------------------------------------------------


class TestDocTestWorkflowStreaming:
    """Integration tests specific to the DocTest workflow configuration."""

    def test_workflow_has_tool_connection(self, doctest_workflow_json):
        """DocTest workflow should have tool connection from Agent to Document Search."""
        connections = doctest_workflow_json["connections"]
        tool_connections = [
            c for c in connections if c.get("connection_type") == "tool"
        ]

        assert len(tool_connections) == 1
        conn = tool_connections[0]

        assert conn["source_id"] == "9a7299e4-f7de-45d5-8fde-0cc74d95d6d7"  # Agent 1
        assert conn["target_id"] == "9f36c074-bfbd-4163-8cc0-6594a2111988"  # Doc Search
        assert conn["source_handle"] == "tools"

    def test_document_search_has_collections(self, doctest_workflow_json):
        """Document Search node should have collections configured."""
        doc_search_node = next(
            n for n in doctest_workflow_json["nodes"] if n["type"] == "DOCUMENT_SEARCH"
        )

        config = doc_search_node["document_search_config"]
        assert len(config["document_collections"]) == 1
        assert config["hybrid_search_enabled"] is True
        assert config["search_mode"] == "hybrid"

    def test_agent_has_llm_config(self, doctest_workflow_json):
        """Agent node should have LLM configuration."""
        agent_node = next(
            n for n in doctest_workflow_json["nodes"] if n["type"] == "AGENT"
        )

        assert "agent_config" in agent_node
        assert "llm_config" in agent_node["agent_config"]
        assert agent_node["agent_config"]["llm_config"]["provider"] == "azure_openai"
