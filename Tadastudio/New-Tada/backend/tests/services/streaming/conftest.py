"""Fixtures for streaming tests.

Provides mock stream writers and event capture utilities for testing
the StreamingEventEmitter and related streaming functionality.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Auto-use Fixtures (applied to all tests in this directory)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_iteration_manager():
    """Auto-mock SubagentIterationManager to avoid database dependency in unit tests.

    The SubgraphDelegationExecutor.execute() method calls
    SubagentIterationManager.get_current_iteration() which queries the database.
    Since these are unit tests with mocks, we mock this call to avoid requiring
    the actual database connection.
    """
    with patch(
        "backend.services.execution.subagent.SubagentIterationManager.get_current_iteration"
    ) as mock_get_iteration:
        mock_get_iteration.return_value = 1
        yield mock_get_iteration


# ---------------------------------------------------------------------------
# Event Capture Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_events() -> List[Dict[str, Any]]:
    """List to capture emitted streaming events."""
    return []


@pytest.fixture
def mock_stream_writer(captured_events):
    """Mock stream writer that captures events to a list.

    Usage:
        def test_example(mock_stream_writer, captured_events):
            # Events emitted via streaming_emitter will be captured
            streaming_emitter.emit_tool_start(...)
            assert len(captured_events) == 1
            assert captured_events[0]["event_type"] == "tool_call_start"
    """

    def capture_event(event: Dict[str, Any]):
        captured_events.append(event)

    with patch(
        "backend.services.streaming.event_emitter.get_stream_writer",
        return_value=capture_event,
    ):
        yield capture_event


@pytest.fixture
def mock_stream_writer_unavailable():
    """Mock scenario where stream writer is not available (not in LangGraph context)."""
    with patch(
        "backend.services.streaming.event_emitter.get_stream_writer",
        side_effect=RuntimeError("Not in LangGraph context"),
    ):
        yield


@pytest.fixture
def sample_tool_call_start_event():
    """Sample tool_call_start event data."""
    return {
        "call_id": "call_abc123",
        "tool_name": "document_search",
        "tool_args": {"query": "test query", "collection_id": "col-1"},
        "agent_id": "agent-001",
        "agent_name": "Research Agent",
    }


@pytest.fixture
def sample_tool_call_progress_event():
    """Sample tool_call_progress event data."""
    return {
        "call_id": "call_abc123",
        "tool_name": "document_search",
        "message": "Searching 3 collections...",
        "progress": 45,
    }


@pytest.fixture
def sample_tool_call_complete_event():
    """Sample tool_call_complete event data."""
    return {
        "call_id": "call_abc123",
        "tool_name": "document_search",
        "result_preview": "Found 5 relevant documents...",
        "duration_ms": 1234.5,
    }


@pytest.fixture
def sample_tool_call_error_event():
    """Sample tool_call_error event data."""
    return {
        "call_id": "call_abc123",
        "tool_name": "document_search",
        "error": "Connection timeout after 30s",
        "duration_ms": 30000.0,
    }


@pytest.fixture
def sample_subagent_start_event():
    """Sample subagent_start event data."""
    return {
        "subagent_id": "subagent-001",
        "subagent_name": "Research Specialist",
        "task_description": "Find relevant documents about machine learning",
        "parent_agent_id": "orchestrator-001",
        "parent_agent_name": "Orchestrator",
    }


@pytest.fixture
def sample_subagent_complete_event():
    """Sample subagent_complete event data."""
    return {
        "subagent_id": "subagent-001",
        "subagent_name": "Research Specialist",
        "success": True,
        "response_preview": "I found 3 relevant documents about machine learning...",
        "duration_ms": 5432.1,
        "tools_used": ["document_search", "web_search"],
    }


@pytest.fixture
def sample_workflow_json():
    """Sample workflow JSON with agent and document search tool (DocTest workflow)."""
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
                    "system_prompt": "Use your document search tool to find information",
                    "tools": [],
                    "llm_config": {
                        "provider": "azure_openai",
                        "model_name": "gpt-4",
                    },
                },
            },
            {
                "uniq_id": "1724b903-9555-49b9-97ea-aa1af8403bec",
                "name": "End",
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
                    "search_k": 3,
                    "search_type": "similarity",
                    "hybrid_search_enabled": True,
                    "search_mode": "hybrid",
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
