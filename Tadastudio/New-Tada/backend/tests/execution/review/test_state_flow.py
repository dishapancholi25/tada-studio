"""Integration tests for review_state flowing through the execution pipeline.

These tests verify the actual code paths work together, using minimal mocking.
The goal is to catch bugs like factory.py dropping review_state.

Key principle: Only mock external dependencies (LLM calls, database), never mock
the internal state flow between components.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.execution.nodes.factory import NodeFunctionFactory
from backend.models.workflow import EnhancedNodeData, NodeType, GraphData


class TestFactoryPassesReviewState:
    """Tests that factory.py correctly passes review_state from executors."""

    @pytest.fixture
    def mock_agent_node(self):
        """Create a minimal agent node with review enabled."""
        node = MagicMock(spec=EnhancedNodeData)
        node.uniq_id = "agent-123"
        node.name = "Test Agent"
        node.type = NodeType.AGENT
        node.nexts = []

        # Review config
        review_config = MagicMock()
        review_config.review_enabled = True
        review_config.review_mode = "human"
        review_config.review_prompt = "Review the output"
        review_config.max_iterations = 3

        agent_config = MagicMock()
        agent_config.review_config = review_config
        node.agent_config = agent_config

        return node

    @pytest.fixture
    def mock_graph(self):
        """Create a minimal graph."""
        graph = MagicMock(spec=GraphData)
        graph.nodes = []
        graph.connections = []
        return graph

    @pytest.fixture
    def initial_state(self):
        """Create initial workflow state with review_state initialized."""
        return {
            "execution_id": "exec-test",
            "db_execution_id": 1,
            "graph_name": "TestGraph",
            "node_outputs": {},
            "results": [],
            "current_node": None,
            "metadata": {},
            "review_state": {},  # Must be initialized
            "pending_review": None,
            "custom_data": None,
            "execution_order": 0,
            "messages": [],
            "original_message": "test input",
        }

    @pytest.mark.asyncio
    async def test_factory_process_node_result_includes_review_state(self):
        """Verify _process_node_result passes through review_state."""
        # This tests the actual factory code, not mocks
        factory = NodeFunctionFactory(checkpoint_executors={})

        node = MagicMock()
        node.name = "TestNode"
        node.uniq_id = "node-123"
        node.type = NodeType.AGENT

        state = {"node_outputs": {}, "results": []}

        # Simulate agent executor returning review_state
        result = {
            "node_output": {"raw": "test output", "structured": None, "fields": {}},
            "review_state": {
                "node-123": {
                    "output": "test output",
                    "config": {"review_mode": "human"},
                    "iteration": 1,
                }
            },
            "execution_order": 1,
        }

        updates = {"current_node": "node-123", "metadata": {}}

        # Call the actual factory method
        processed = factory._process_node_result(node, state, result, updates, None)

        # CRITICAL: review_state must be in the processed updates
        assert "review_state" in processed, (
            "factory._process_node_result must pass through review_state. "
            "This is required for the review node architecture."
        )
        assert "node-123" in processed["review_state"]
        assert processed["review_state"]["node-123"]["output"] == "test output"

    @pytest.mark.asyncio
    async def test_factory_preserves_review_state_with_other_fields(self):
        """Verify review_state is preserved alongside other state fields."""
        factory = NodeFunctionFactory(checkpoint_executors={})

        node = MagicMock()
        node.name = "TestNode"
        node.uniq_id = "node-123"
        node.type = NodeType.AGENT

        state = {"node_outputs": {}, "results": []}

        result = {
            "node_output": {"raw": "output", "structured": None, "fields": {}},
            "review_state": {"node-123": {"output": "output", "iteration": 1}},
            "messages": [{"role": "assistant", "content": "test"}],
            "execution_order": 5,
        }

        updates = {"current_node": "node-123", "metadata": {}}

        processed = factory._process_node_result(node, state, result, updates, None)

        # All fields should be present
        assert "review_state" in processed
        assert "node_outputs" in processed
        assert "execution_order" in processed
        assert processed["execution_order"] == 5

    @pytest.mark.asyncio
    async def test_factory_handles_missing_review_state(self):
        """Verify factory works correctly when no review_state in result."""
        factory = NodeFunctionFactory(checkpoint_executors={})

        node = MagicMock()
        node.name = "TestNode"
        node.uniq_id = "node-123"
        node.type = NodeType.AGENT

        state = {"node_outputs": {}, "results": []}

        # No review_state in result (non-review agent)
        result = {
            "node_output": {"raw": "output", "structured": None, "fields": {}},
            "execution_order": 1,
        }

        updates = {"current_node": "node-123", "metadata": {}}

        processed = factory._process_node_result(node, state, result, updates, None)

        # Should not have review_state
        assert "review_state" not in processed
        # But should still have other fields
        assert "node_outputs" in processed


class TestReviewNodeReceivesState:
    """Tests that review node correctly receives state from agent."""

    @pytest.mark.asyncio
    async def test_review_node_function_reads_review_state(self):
        """Verify review node reads review_state from state dict."""
        from backend.services.nodes.executors.review import ReviewNodeFunctionFactory

        # Create a mock agent node
        agent_node = MagicMock()
        agent_node.uniq_id = "agent-123"
        agent_node.name = "Test Agent"

        # Create review node function
        factory = ReviewNodeFunctionFactory()
        review_func = factory.create_review_function(agent_node)

        # State with review_state populated (as it would be after agent execution)
        state = {
            "execution_id": "exec-test",
            "review_state": {
                "agent-123": {
                    "output": "Agent output to review",
                    "config": {
                        "review_mode": "human",
                        "review_prompt": "Review this",
                        "max_iterations": 3,
                    },
                    "iteration": 1,
                    "history": [],
                }
            },
        }

        # The review node should see the review_state
        # We can't fully execute (it calls interrupt), but we can verify the logic
        # by checking logs or by mocking interrupt

        # Mock interrupt to verify it gets called with correct data
        # interrupt is imported inside the function from langgraph.types
        with patch("langgraph.types.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"approved": True}

            # Also mock WebSocket notifier
            with patch(
                "backend.services.nodes.executors.review.ws_notifier"
            ) as mock_ws:
                mock_ws.on_execution_paused = AsyncMock()

                await review_func(state)

                # Verify interrupt was called (meaning review_state was found)
                assert mock_interrupt.called, (
                    "interrupt() should be called when review_state contains data"
                )

                # Verify the payload contains agent output
                call_args = mock_interrupt.call_args[0][0]
                assert call_args["agent_output"] == "Agent output to review"
                assert call_args["node_id"] == "agent-123"

    @pytest.mark.asyncio
    async def test_review_node_passes_through_without_review_state(self):
        """Verify review node passes through when no review_state for agent."""
        from backend.services.nodes.executors.review import ReviewNodeFunctionFactory

        agent_node = MagicMock()
        agent_node.uniq_id = "agent-123"
        agent_node.name = "Test Agent"

        factory = ReviewNodeFunctionFactory()
        review_func = factory.create_review_function(agent_node)

        # State with empty review_state
        state = {
            "execution_id": "exec-test",
            "review_state": {},  # Empty - no review needed
        }

        result = await review_func(state)

        # Should pass through without calling interrupt
        assert result.get("custom_data", {}).get("__review_route") == "continue"


class TestEndToEndStateFlow:
    """End-to-end tests for state flow from agent to review node.

    These tests verify the complete flow with minimal mocking.
    """

    @pytest.mark.asyncio
    async def test_agent_output_reaches_review_node_via_factory(self):
        """Integration test: agent → factory → state → review node."""
        # This test uses real factory code to process agent result
        factory = NodeFunctionFactory(checkpoint_executors={})

        # 1. Simulate agent executor returning review_state
        agent_node = MagicMock()
        agent_node.name = "Agent"
        agent_node.uniq_id = "agent-001"
        agent_node.type = NodeType.AGENT

        agent_result = {
            "node_output": {"raw": "Agent response", "structured": None, "fields": {}},
            "review_state": {
                "agent-001": {
                    "output": "Agent response",
                    "config": {"review_mode": "human", "max_iterations": 3},
                    "iteration": 1,
                    "history": [],
                }
            },
        }

        state = {"node_outputs": {}, "results": []}
        updates = {"current_node": "agent-001", "metadata": {}}

        # 2. Factory processes the result
        processed = factory._process_node_result(
            agent_node, state, agent_result, updates, None
        )

        # 3. Verify review_state survives factory processing
        assert "review_state" in processed, "Factory must preserve review_state"

        # 4. Simulate state after LangGraph merges (what review node would see)
        merged_state = {
            **state,
            **processed,
        }

        # 5. Verify review node can read the state
        from backend.services.nodes.executors.review import ReviewNodeFunctionFactory

        review_agent_node = MagicMock()
        review_agent_node.uniq_id = "agent-001"
        review_agent_node.name = "Agent"

        review_factory = ReviewNodeFunctionFactory()
        review_func = review_factory.create_review_function(review_agent_node)

        # Mock interrupt since we're testing state flow, not interrupt behavior
        # interrupt is imported inside the function from langgraph.types
        with patch("langgraph.types.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"approved": True}
            with patch("backend.services.nodes.executors.review.ws_notifier"):
                await review_func(merged_state)

        # Verify the review node found the data and processed it
        assert mock_interrupt.called, (
            "Review node should call interrupt when it has data"
        )
        interrupt_payload = mock_interrupt.call_args[0][0]
        assert interrupt_payload["agent_output"] == "Agent response"
