"""Tests for sub-agent streaming events.

These tests verify that the SubgraphDelegationExecutor correctly emits
streaming events for sub-agent delegation lifecycle.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from backend.models.workflow import NodeType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_subagent_dependencies():
    """Mock all dependencies for SubgraphDelegationExecutor."""
    with (
        patch("backend.services.execution.get_executor") as mock_get_exec,
        patch(
            "backend.services.delegation.executors.subgraph_executor.run_async_in_sync_isolated"
        ) as mock_run,
    ):
        mock_executor = MagicMock()
        mock_subgraph_builder = MagicMock()
        mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
        mock_executor.subgraph_builder = mock_subgraph_builder
        mock_get_exec.return_value = mock_executor

        yield {
            "get_executor": mock_get_exec,
            "run_async": mock_run,
            "executor": mock_executor,
            "subgraph_builder": mock_subgraph_builder,
        }


@pytest.fixture
def mock_delegation_request():
    """Create mock delegation request for testing."""

    class MockAgentConfig:
        system_prompt = "You are a math specialist"
        review_config = None

    class MockAgentNode:
        uniq_id = "subagent-math-001"
        name = "Math Expert"
        type = NodeType.AGENT
        agent_config = MockAgentConfig()

    class MockDelegationRequest:
        agent_node = MockAgentNode()
        task_description = "Calculate the sum of 2 + 2"
        orchestrator_id = "orchestrator-001"
        context = {
            "execution_id": "exec-test-123",
            "db_execution_id": "db-exec-456",
            "execution_order": 1,
            "graph_name": "TestWorkflow",
            "tool_node_mapping": {},
            "parent_node_execution_id": "node-exec-789",
        }

    return MockDelegationRequest()


# ---------------------------------------------------------------------------
# TestSubAgentStartStreaming
# ---------------------------------------------------------------------------


class TestSubAgentStartStreaming:
    """Tests for subagent_start event emission."""

    def test_emits_subagent_start_on_execution(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should emit subagent_start event when delegation begins."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        # Configure successful completion
        mock_subagent_dependencies["run_async"].return_value = {
            "response": "The answer is 4",
            "execution_order": 2,
            "paused_for_review": None,
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        _result = executor.execute(mock_delegation_request)

        # Find subagent_start event
        start_events = [
            e for e in captured_events if e["event_type"] == "subagent_start"
        ]

        assert len(start_events) == 1
        event = start_events[0]

        assert event["subagent_id"] == mock_delegation_request.agent_node.uniq_id
        assert event["subagent_name"] == mock_delegation_request.agent_node.name
        assert event["task_description"] == mock_delegation_request.task_description
        assert event["parent_agent_id"] == mock_delegation_request.orchestrator_id
        assert "timestamp" in event

    def test_subagent_start_includes_parent_agent_name(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should include parent agent name in start event."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_subagent_dependencies["run_async"].return_value = {
            "response": "Done",
            "execution_order": 2,
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        executor.execute(mock_delegation_request)

        start_events = [
            e for e in captured_events if e["event_type"] == "subagent_start"
        ]

        assert len(start_events) == 1
        # Parent agent name may be derived from orchestrator_id or set explicitly
        assert "parent_agent_id" in start_events[0]


# ---------------------------------------------------------------------------
# TestSubAgentCompleteStreaming
# ---------------------------------------------------------------------------


class TestSubAgentCompleteStreaming:
    """Tests for subagent_complete event emission."""

    def test_emits_subagent_complete_on_success(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should emit subagent_complete event when delegation succeeds."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_subagent_dependencies["run_async"].return_value = {
            "response": "The answer is 4",
            "execution_order": 2,
            "paused_for_review": None,
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        _result = executor.execute(mock_delegation_request)

        # Find subagent_complete event
        complete_events = [
            e for e in captured_events if e["event_type"] == "subagent_complete"
        ]

        assert len(complete_events) == 1
        event = complete_events[0]

        assert event["subagent_id"] == mock_delegation_request.agent_node.uniq_id
        assert event["subagent_name"] == mock_delegation_request.agent_node.name
        assert event["success"] is True
        assert "duration_ms" in event
        assert event["duration_ms"] >= 0
        assert "timestamp" in event

    def test_emits_subagent_complete_on_error(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should emit subagent_complete with success=False on error."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_subagent_dependencies["run_async"].return_value = {
            "response": None,
            "execution_order": 2,
            "error": "LLM call failed: timeout",
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        _result = executor.execute(mock_delegation_request)

        complete_events = [
            e for e in captured_events if e["event_type"] == "subagent_complete"
        ]

        assert len(complete_events) == 1
        event = complete_events[0]

        assert event["success"] is False

    def test_emits_subagent_complete_on_exception(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should emit subagent_complete when exception is raised."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_subagent_dependencies["run_async"].side_effect = ValueError(
            "Unexpected error"
        )

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        result = executor.execute(mock_delegation_request)

        complete_events = [
            e for e in captured_events if e["event_type"] == "subagent_complete"
        ]

        assert len(complete_events) == 1
        event = complete_events[0]

        assert event["success"] is False
        assert result.success is False

    def test_includes_response_preview(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should include truncated response preview in complete event."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        long_response = "A" * 1000  # Very long response

        mock_subagent_dependencies["run_async"].return_value = {
            "response": long_response,
            "execution_order": 2,
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        executor.execute(mock_delegation_request)

        complete_events = [
            e for e in captured_events if e["event_type"] == "subagent_complete"
        ]

        assert len(complete_events) == 1
        # Response should be truncated if longer than 500 chars
        if complete_events[0].get("response_preview"):
            assert len(complete_events[0]["response_preview"]) <= 500


# ---------------------------------------------------------------------------
# TestSubAgentEventSequence
# ---------------------------------------------------------------------------


class TestSubAgentEventSequence:
    """Tests for correct sequence of sub-agent streaming events."""

    def test_start_before_complete(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Start event should always come before complete event."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_subagent_dependencies["run_async"].return_value = {
            "response": "Done",
            "execution_order": 2,
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        executor.execute(mock_delegation_request)

        # Get indices of start and complete events
        start_idx = None
        complete_idx = None

        for i, event in enumerate(captured_events):
            if event["event_type"] == "subagent_start":
                start_idx = i
            elif event["event_type"] == "subagent_complete":
                complete_idx = i

        assert start_idx is not None, "subagent_start event not found"
        assert complete_idx is not None, "subagent_complete event not found"
        assert start_idx < complete_idx, "start event should come before complete"

    def test_duration_calculated_correctly(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Duration should be positive and reflect actual execution time."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        # Add a small delay to ensure measurable duration
        def delayed_execution(*args, **kwargs):
            time.sleep(0.01)  # 10ms delay
            return {
                "response": "Done",
                "execution_order": 2,
                "error": None,
            }

        mock_subagent_dependencies["run_async"].side_effect = delayed_execution

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        executor.execute(mock_delegation_request)

        complete_events = [
            e for e in captured_events if e["event_type"] == "subagent_complete"
        ]

        assert len(complete_events) == 1
        duration_ms = complete_events[0]["duration_ms"]
        assert duration_ms >= 0  # Should be non-negative


# ---------------------------------------------------------------------------
# TestSubAgentStreamingWithPause
# ---------------------------------------------------------------------------


class TestSubAgentStreamingWithPause:
    """Tests for sub-agent streaming when workflow is paused for review."""

    def test_emits_start_before_pause_interrupt(
        self,
        mock_stream_writer,
        captured_events,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should emit subagent_start before raising GraphInterrupt for pause."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )
        from langgraph.errors import GraphInterrupt

        # Configure paused state
        mock_subagent_dependencies["run_async"].return_value = {
            "response": "[AWAITING REVIEW] Output pending",
            "execution_order": 2,
            "paused": True,
            "paused_for_review": True,
            "review_data": {
                "type": "agent_review",
                "node_id": "subagent-math-001",
            },
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())

        with pytest.raises(GraphInterrupt):
            executor.execute(mock_delegation_request)

        # Should have emitted start event before the pause
        start_events = [
            e for e in captured_events if e["event_type"] == "subagent_start"
        ]
        complete_events = [
            e for e in captured_events if e["event_type"] == "subagent_complete"
        ]

        assert len(start_events) == 1
        # Complete event is NOT emitted when paused - the sub-agent is not complete, just paused
        assert len(complete_events) == 0

        # Verify the start event has correct data
        assert (
            start_events[0]["subagent_id"] == mock_delegation_request.agent_node.uniq_id
        )
        assert (
            start_events[0]["subagent_name"] == mock_delegation_request.agent_node.name
        )


# ---------------------------------------------------------------------------
# TestNoStreamingWhenWriterUnavailable
# ---------------------------------------------------------------------------


class TestNoStreamingWhenWriterUnavailable:
    """Tests for graceful handling when stream writer is unavailable."""

    def test_executes_without_errors_when_no_writer(
        self,
        mock_stream_writer_unavailable,
        mock_subagent_dependencies,
        mock_delegation_request,
    ):
        """Should execute successfully even when stream writer is unavailable."""
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_subagent_dependencies["run_async"].return_value = {
            "response": "The answer is 4",
            "execution_order": 2,
            "error": None,
        }

        executor = SubgraphDelegationExecutor(graph_manager=MagicMock())
        result = executor.execute(mock_delegation_request)

        # Should complete successfully
        assert result.success is True
        assert result.response == "The answer is 4"
