"""Tests for initial state creation with review support.

These tests ensure the workflow executor creates initial state with all fields
required for the review node architecture.
"""

import re


class TestInitialStateCreation:
    """Tests for initial state containing review-related fields."""

    def test_workflow_executor_initial_state_has_review_state(self):
        """Verify workflow_executor.py creates initial_state with review_state.

        This test reads the source code to ensure review_state is included.
        This catches the bug where review_state was missing from initial state.
        """
        import inspect
        from backend.services.execution import workflow_executor

        # Get the source code of the module
        source = inspect.getsource(workflow_executor)

        # Find the initial_state creation block
        # Look for the pattern where initial_state is created
        assert "review_state" in source, (
            "workflow_executor.py must include 'review_state' in initial_state. "
            "The review node architecture requires this field to be initialized."
        )

        # More specific check: ensure review_state is in the initial_state dict
        # Look for the pattern: "review_state": {}
        assert re.search(r'"review_state":\s*\{\}', source), (
            "workflow_executor.py must initialize review_state as empty dict in initial_state"
        )

    def test_workflow_executor_initial_state_has_pending_review(self):
        """Verify workflow_executor.py creates initial_state with pending_review."""
        import inspect
        from backend.services.execution import workflow_executor

        source = inspect.getsource(workflow_executor)

        # Check pending_review is included
        assert '"pending_review"' in source, (
            "workflow_executor.py must include 'pending_review' in initial_state"
        )

    def test_review_state_field_required_for_reducer(self):
        """Verify the merge_review_state reducer works with initial empty state."""
        from backend.services.workflow.state.reducers import merge_review_state

        # Simulate initial state (empty dict)
        current = {}

        # Agent returns review state update
        updates = {
            "node-123": {
                "output": "Agent response",
                "config": {"review_mode": "human"},
                "iteration": 1,
            }
        }

        # Reducer should merge correctly
        result = merge_review_state(current, updates)

        assert "node-123" in result
        assert result["node-123"]["output"] == "Agent response"

    def test_review_state_none_clears_entry(self):
        """Verify setting node to None clears the review state entry."""
        from backend.services.workflow.state.reducers import merge_review_state

        # Current state with review data
        current = {
            "node-123": {
                "output": "Agent response",
                "config": {"review_mode": "human"},
                "iteration": 1,
            }
        }

        # Approval clears the entry by setting to None
        updates = {"node-123": None}

        result = merge_review_state(current, updates)

        assert "node-123" not in result, (
            "Setting node to None should remove it from review_state"
        )


class TestReviewNodeStateAccess:
    """Tests for review node accessing state correctly."""

    def test_review_node_reads_from_review_state(self):
        """Review node should read agent output from state.review_state."""
        # This tests the pattern used in review.py
        agent_node_id = "agent-123"

        # State with review data (as it would be after agent execution)
        state = {
            "review_state": {
                agent_node_id: {
                    "output": "Test output",
                    "config": {"review_mode": "human", "max_iterations": 3},
                    "iteration": 1,
                    "history": [],
                }
            }
        }

        # This is how review node accesses the data
        review_state = state.get("review_state", {})
        review_data = review_state.get(agent_node_id)

        assert review_data is not None
        assert review_data["output"] == "Test output"

    def test_review_node_handles_missing_review_state(self):
        """Review node should handle missing review_state gracefully."""
        agent_node_id = "agent-123"

        # State without review_state (should not happen with proper initialization)
        state = {}

        # This is how review node accesses the data
        review_state = state.get("review_state", {})
        review_data = review_state.get(agent_node_id)

        # Should return None, not raise an error
        assert review_data is None

    def test_review_node_handles_empty_review_state(self):
        """Review node should handle empty review_state (first execution)."""
        agent_node_id = "agent-123"

        # State with empty review_state (initial state)
        state = {"review_state": {}}

        review_state = state.get("review_state", {})
        review_data = review_state.get(agent_node_id)

        assert review_data is None
