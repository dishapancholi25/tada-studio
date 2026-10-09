"""Tests for SubgraphDelegationExecutor.

These tests verify the subgraph delegation executor behavior, particularly
the CRITICAL pause propagation from sub-agent subgraphs back to the parent workflow.

The key fix being tested:
- SubAgentState must include paused_for_review, paused, and review_data fields
- When subgraph returns paused_for_review=True, executor must raise GraphInterrupt
- GraphInterrupt must contain review_data with sub_agent info
"""

import pytest
from unittest.mock import MagicMock, patch

from langgraph.errors import GraphInterrupt
from langgraph.types import Interrupt


# ---------------------------------------------------------------------------
# TestSubgraphDelegationExecutor - Basic Functionality
# ---------------------------------------------------------------------------


class TestSubgraphDelegationExecutor:
    """Tests for basic SubgraphDelegationExecutor functionality."""

    def test_prepares_initial_state_with_pause_fields(self, delegation_request):
        """CRITICAL: Initial state MUST include pause fields for LangGraph filtering."""
        # Import the module to make it available for patching
        from backend.services.delegation.executors import subgraph_executor

        # Patch get_executor at the location where it's imported (inside execute method)
        with patch("backend.services.execution.get_executor") as mock_get_exec:
            mock_executor = MagicMock()
            mock_executor.subgraph_builder = MagicMock()
            mock_get_exec.return_value = mock_executor

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )
            initial_state = executor._prepare_subagent_state(delegation_request)

            # These fields MUST be present for LangGraph state schema
            assert "paused" in initial_state
            assert "paused_for_review" in initial_state
            assert "review_data" in initial_state

            # Default values should be None
            assert initial_state["paused"] is None
            assert initial_state["paused_for_review"] is None
            assert initial_state["review_data"] is None

    def test_prepares_initial_state_with_required_fields(self, delegation_request):
        """Should prepare initial state with all required fields."""
        from backend.services.delegation.executors import subgraph_executor

        with patch("backend.services.execution.get_executor") as mock_get_exec:
            mock_executor = MagicMock()
            mock_executor.subgraph_builder = MagicMock()
            mock_get_exec.return_value = mock_executor

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )
            initial_state = executor._prepare_subagent_state(delegation_request)

            # Required fields from context
            assert initial_state["task_description"] == "Calculate 2+2"
            assert initial_state["parent_execution_id"] == "exec-123"
            assert initial_state["parent_db_execution_id"] == "db-exec-456"
            assert initial_state["parent_node_id"] == "orchestrator-001"
            assert initial_state["execution_order"] == 2  # current_order + 1

    def test_returns_success_result_on_completion(
        self, delegation_request, mock_subgraph
    ):
        """Should return success result when subgraph completes normally."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = mock_subgraph
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            # Simulate successful completion
            mock_run.return_value = {
                "response": "The answer is 4",
                "execution_order": 2,
                "paused_for_review": None,
                "error": None,
            }

            graph_manager = MagicMock()
            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=graph_manager
            )
            result = executor.execute(delegation_request)

            assert result.success is True
            assert result.response == "The answer is 4"
            assert result.error is None

    def test_returns_error_result_on_failure(self, delegation_request):
        """Should return error result when subgraph has an error."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            # Simulate error in result state
            mock_run.return_value = {
                "error": "LLM call failed",
                "execution_order": 1,
            }

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )
            result = executor.execute(delegation_request)

            assert result.success is False
            assert result.error == "LLM call failed"


# ---------------------------------------------------------------------------
# TestPausePropagation - CRITICAL FIX VERIFICATION
# ---------------------------------------------------------------------------


class TestPausePropagation:
    """CRITICAL tests for pause propagation from subgraph to parent workflow.

    These tests verify the fix for the bug where paused_for_review was being
    silently dropped by LangGraph's state filtering because it wasn't in
    the SubAgentState TypedDict schema.
    """

    def test_detects_paused_for_review_in_result_state(
        self, delegation_request_with_review
    ):
        """CRITICAL: Should detect paused_for_review=True in result state."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            # Simulate paused state from subgraph
            mock_run.return_value = {
                "response": "[AWAITING REVIEW] Output pending review",
                "execution_order": 2,
                "paused": True,
                "paused_for_review": True,  # This MUST be detected
                "review_data": {
                    "type": "agent_review",
                    "node_id": "subagent-review-001",
                    "agent_output": "The answer is 4",
                },
            }

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )

            # Should raise GraphInterrupt when paused_for_review is True
            with pytest.raises(GraphInterrupt):
                executor.execute(delegation_request_with_review)

    def test_raises_graph_interrupt_when_paused(self, delegation_request_with_review):
        """CRITICAL: Should raise GraphInterrupt to pause parent workflow."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            mock_run.return_value = {
                "response": "[AWAITING REVIEW]",
                "paused_for_review": True,
                "review_data": {"type": "agent_review"},
            }

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )

            with pytest.raises(GraphInterrupt) as exc_info:
                executor.execute(delegation_request_with_review)

            # Verify it's a proper GraphInterrupt
            assert isinstance(exc_info.value, GraphInterrupt)

    def test_interrupt_contains_review_data(self, delegation_request_with_review):
        """CRITICAL: GraphInterrupt should contain review_data for UI."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            review_data = {
                "type": "agent_review",
                "node_id": "subagent-review-001",
                "agent_output": "The answer is 4",
                "review_prompt": "Check the math",
            }
            mock_run.return_value = {
                "response": "[AWAITING REVIEW]",
                "paused_for_review": True,
                "review_data": review_data,
            }

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )

            with pytest.raises(GraphInterrupt) as exc_info:
                executor.execute(delegation_request_with_review)

            # Extract interrupt payload
            gi = exc_info.value
            assert hasattr(gi, "args") and gi.args

            # Find Interrupt object in args (may be nested in tuples)
            def find_interrupt(obj):
                """Recursively find Interrupt object in nested structure."""
                if hasattr(obj, "value"):
                    return obj
                if isinstance(obj, (list, tuple)):
                    for item in obj:
                        result = find_interrupt(item)
                        if result is not None:
                            return result
                return None

            interrupt_obj = find_interrupt(gi.args)
            assert interrupt_obj is not None, (
                f"No Interrupt object found in args: {gi.args}"
            )
            # Review data should be in the interrupt value
            assert "type" in interrupt_obj.value or interrupt_obj.value.get("type")

    def test_interrupt_includes_sub_agent_info(self, delegation_request_with_review):
        """CRITICAL: Interrupt should include sub_agent_name and sub_agent_id."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            mock_run.return_value = {
                "response": "[AWAITING REVIEW]",
                "paused_for_review": True,
                "review_data": {"type": "agent_review"},
            }

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )

            with pytest.raises(GraphInterrupt) as exc_info:
                executor.execute(delegation_request_with_review)

            gi = exc_info.value

            # Find Interrupt object in args (may be nested in tuples)
            def find_interrupt(obj):
                """Recursively find Interrupt object in nested structure."""
                if hasattr(obj, "value"):
                    return obj
                if isinstance(obj, (list, tuple)):
                    for item in obj:
                        result = find_interrupt(item)
                        if result is not None:
                            return result
                return None

            interrupt_obj = find_interrupt(gi.args)
            assert interrupt_obj is not None, (
                f"No Interrupt object found in args: {gi.args}"
            )
            interrupt_value = interrupt_obj.value

            # Sub-agent info should be added by executor
            assert interrupt_value.get("sub_agent_name") == "Math Expert"
            assert (
                interrupt_value.get("sub_agent_id")
                == delegation_request_with_review.agent_node.uniq_id
            )


# ---------------------------------------------------------------------------
# TestGraphInterruptPropagation
# ---------------------------------------------------------------------------


class TestGraphInterruptPropagation:
    """Tests for GraphInterrupt propagation scenarios."""

    def test_propagates_graph_interrupt_from_subgraph(self, delegation_request):
        """Should propagate GraphInterrupt raised during subgraph execution."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            # Simulate GraphInterrupt from subgraph
            interrupt_data = Interrupt(value={"type": "agent_review"})
            mock_run.side_effect = GraphInterrupt((interrupt_data,))

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )

            with pytest.raises(GraphInterrupt):
                executor.execute(delegation_request)

    def test_detects_wrapped_interrupt_in_exception(self, delegation_request):
        """Should detect wrapped GraphInterrupt in exception message."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            # Simulate wrapped interrupt (from run_async_in_sync thread pool)
            class WrappedInterruptError(Exception):
                pass

            WrappedInterruptError.__name__ = "GraphInterrupt"
            mock_run.side_effect = WrappedInterruptError("Interrupt value")

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )

            with pytest.raises(GraphInterrupt):
                executor.execute(delegation_request)

    def test_returns_error_for_non_interrupt_exception(self, delegation_request):
        """Should return error result for non-interrupt exceptions."""
        from backend.services.delegation.executors import subgraph_executor

        with (
            patch("backend.services.execution.get_executor") as mock_get_exec,
            patch.object(subgraph_executor, "run_async_in_sync_isolated") as mock_run,
        ):
            mock_executor = MagicMock()
            mock_subgraph_builder = MagicMock()
            mock_subgraph_builder.create_subagent_graph.return_value = MagicMock()
            mock_executor.subgraph_builder = mock_subgraph_builder
            mock_get_exec.return_value = mock_executor

            # Simulate regular exception
            mock_run.side_effect = ValueError("Something went wrong")

            executor = subgraph_executor.SubgraphDelegationExecutor(
                graph_manager=MagicMock()
            )
            result = executor.execute(delegation_request)

            assert result.success is False
            assert "Something went wrong" in result.error


# ---------------------------------------------------------------------------
# TestSubAgentStateSchema - Schema Verification
# ---------------------------------------------------------------------------


class TestSubAgentStateSchema:
    """Tests to verify SubAgentState schema includes required fields.

    This is a documentation test to ensure the schema fix is in place.
    """

    def test_subagent_state_includes_pause_fields(self):
        """Verify SubAgentState TypedDict includes pause fields."""
        from backend.services.subgraph.models import SubAgentState

        # Get the annotations (TypedDict fields)
        annotations = SubAgentState.__annotations__

        # These fields MUST be present for LangGraph to include them in state
        assert "paused" in annotations, "SubAgentState must include 'paused' field"
        assert "paused_for_review" in annotations, (
            "SubAgentState must include 'paused_for_review' field"
        )
        assert "review_data" in annotations, (
            "SubAgentState must include 'review_data' field"
        )

    def test_subagent_state_pause_fields_are_optional(self):
        """Verify pause fields are Optional types."""
        from typing import get_origin

        from backend.services.subgraph.models import SubAgentState

        annotations = SubAgentState.__annotations__

        # Check paused field
        paused_type = annotations.get("paused")
        assert get_origin(paused_type) is not None or "Optional" in str(paused_type)

        # Check paused_for_review field
        paused_for_review_type = annotations.get("paused_for_review")
        assert get_origin(paused_for_review_type) is not None or "Optional" in str(
            paused_for_review_type
        )
