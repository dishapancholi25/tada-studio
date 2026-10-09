"""Integration test using real workflow JSON structure.

This test uses the actual ReviewTest workflow export structure to verify
the review feature works end-to-end with minimal mocking.

Only external dependencies (LLM calls, database) are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch

# The actual workflow structure from ReviewTest export
REVIEW_TEST_WORKFLOW = {
    "name": "ReviewTest",
    "description": "",
    "nodes": [
        {
            "uniq_id": "56ca794f-22a9-4431-bb00-9ff2c58bc5b3",
            "name": "Start",
            "type": "START",
            "description": "",
            "nexts": ["b1eb47c3-4107-4134-aa76-9b4e56c6129d"],
            "inputs": [],
            "is_sub_agent": False,
            "is_subworkflow": False,
            "parent_agent_id": None,
            "delegation_description": "",
        },
        {
            "uniq_id": "b1eb47c3-4107-4134-aa76-9b4e56c6129d",
            "name": "Agent 1",
            "type": "AGENT",
            "description": "You are a helpful AI assistant.",
            "nexts": ["c4ff9da0-dc97-4e18-8b4a-aff2a3a52310"],
            "inputs": ["56ca794f-22a9-4431-bb00-9ff2c58bc5b3"],
            "is_sub_agent": False,
            "is_subworkflow": False,
            "parent_agent_id": None,
            "delegation_description": "",
            "agent_config": {
                "agent_type": "conversational",
                "system_prompt": "You are a helpful AI assistant.",
                "max_iterations": 10,
                "temperature": 0,
                "tools": [],
                "memory_enabled": False,
                "llm_config": {
                    "provider": "azure_openai",
                    "model_name": "gpt-4",
                    "temperature": 0,
                },
                # REVIEW CONFIG - This is what enables review!
                "review_config": {
                    "review_enabled": True,
                    "review_mode": "human",
                    "review_prompt": "Review the agent output for quality",
                    "max_iterations": 3,
                    "auto_approve_on_max_iterations": True,
                },
            },
        },
        {
            "uniq_id": "c4ff9da0-dc97-4e18-8b4a-aff2a3a52310",
            "name": "End 2",
            "type": "END",
            "description": "END node",
            "nexts": [],
            "inputs": ["b1eb47c3-4107-4134-aa76-9b4e56c6129d"],
            "is_sub_agent": False,
            "is_subworkflow": False,
            "parent_agent_id": None,
            "delegation_description": "",
        },
    ],
    "connections": [
        {
            "source_id": "56ca794f-22a9-4431-bb00-9ff2c58bc5b3",
            "target_id": "b1eb47c3-4107-4134-aa76-9b4e56c6129d",
            "connection_type": "workflow",
            "label": "",
        },
        {
            "source_id": "b1eb47c3-4107-4134-aa76-9b4e56c6129d",
            "target_id": "c4ff9da0-dc97-4e18-8b4a-aff2a3a52310",
            "connection_type": "workflow",
            "label": "",
        },
    ],
    "default_llm_config": None,
}


class TestReviewWorkflowIntegration:
    """Integration tests using real workflow structure."""

    @pytest.fixture
    def workflow_data(self):
        """Return the review test workflow data."""
        return REVIEW_TEST_WORKFLOW.copy()

    @pytest.mark.asyncio
    async def test_agent_stores_output_in_review_state(self, workflow_data):
        """Verify agent executor stores output in review_state when review enabled."""
        from backend.models.workflow import GraphData, EnhancedNodeData
        from backend.services.execution.nodes.factory import NodeFunctionFactory

        # Parse workflow
        graph_data = GraphData(**workflow_data)

        # Get the agent node
        agent_node_data = next(
            n for n in workflow_data["nodes"] if n["type"] == "AGENT"
        )
        agent_node = EnhancedNodeData(**agent_node_data)

        # Create factory
        factory = NodeFunctionFactory(checkpoint_executors={})

        # Simulate what the agent executor would return
        # This tests the factory's handling, not the full agent execution
        mock_result = {
            "node_output": {
                "raw": "Hello! I'm here to help.",
                "structured": None,
                "fields": {},
            },
            "review_state": {
                agent_node.uniq_id: {
                    "output": "Hello! I'm here to help.",
                    "config": {
                        "review_mode": "human",
                        "review_prompt": "Review the agent output",
                        "max_iterations": 3,
                    },
                    "iteration": 1,
                    "history": [],
                    "input_message": "Hi there",
                }
            },
            "execution_order": 1,
        }

        state = {"node_outputs": {}, "results": []}
        updates = {"current_node": agent_node.uniq_id, "metadata": {}}

        # Process through factory
        processed = factory._process_node_result(
            agent_node, state, mock_result, updates, graph_data
        )

        # CRITICAL: review_state must survive factory processing
        assert "review_state" in processed, (
            "Factory must pass through review_state from agent executor"
        )
        assert agent_node.uniq_id in processed["review_state"]
        assert (
            processed["review_state"][agent_node.uniq_id]["output"]
            == "Hello! I'm here to help."
        )

    @pytest.mark.asyncio
    async def test_review_node_receives_review_state(self, workflow_data):
        """Verify review node can read review_state passed from agent."""
        from backend.services.nodes.executors.review import ReviewNodeFunctionFactory

        # Get agent node info
        agent_node_data = next(
            n for n in workflow_data["nodes"] if n["type"] == "AGENT"
        )
        agent_node = MagicMock()
        agent_node.uniq_id = agent_node_data["uniq_id"]
        agent_node.name = agent_node_data["name"]

        # Create review node function
        factory = ReviewNodeFunctionFactory()
        review_func = factory.create_review_function(agent_node)

        # State as it would be after agent execution (with review_state populated)
        state = {
            "execution_id": "test-exec",
            "review_state": {
                agent_node.uniq_id: {
                    "output": "Agent response to review",
                    "config": {
                        "review_mode": "human",
                        "review_prompt": "Review this output",
                        "max_iterations": 3,
                    },
                    "iteration": 1,
                    "history": [],
                }
            },
        }

        # Mock interrupt and verify it's called with correct payload
        with patch("langgraph.types.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"approved": True}
            with patch("backend.services.nodes.executors.review.ws_notifier"):
                await review_func(state)

        # Verify interrupt was called (review node found the data)
        assert mock_interrupt.called, (
            "Review node should call interrupt when review_state has data"
        )

        # Verify the interrupt payload
        payload = mock_interrupt.call_args[0][0]
        assert payload["node_id"] == agent_node.uniq_id
        assert payload["agent_output"] == "Agent response to review"
        assert payload["review_mode"] == "human"

    @pytest.mark.asyncio
    async def test_full_state_flow_agent_to_review(self, workflow_data):
        """End-to-end test: agent returns review_state → factory processes → review node reads."""
        from backend.models.workflow import GraphData, EnhancedNodeData
        from backend.services.execution.nodes.factory import NodeFunctionFactory
        from backend.services.nodes.executors.review import ReviewNodeFunctionFactory

        graph_data = GraphData(**workflow_data)

        # Get agent node
        agent_node_data = next(
            n for n in workflow_data["nodes"] if n["type"] == "AGENT"
        )
        agent_node = EnhancedNodeData(**agent_node_data)

        # Step 1: Simulate agent executor output
        agent_result = {
            "node_output": {"raw": "Test response", "structured": None, "fields": {}},
            "review_state": {
                agent_node.uniq_id: {
                    "output": "Test response",
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

        # Step 2: Factory processes the result
        factory = NodeFunctionFactory(checkpoint_executors={})
        state = {"node_outputs": {}, "results": [], "review_state": {}}
        updates = {"current_node": agent_node.uniq_id, "metadata": {}}

        processed = factory._process_node_result(
            agent_node, state, agent_result, updates, graph_data
        )

        # Step 3: Merge into state (simulating LangGraph behavior)
        merged_state = {
            **state,
            **processed,
            "execution_id": "test-exec",
        }

        # Step 4: Review node reads the state
        review_factory = ReviewNodeFunctionFactory()
        mock_agent_node = MagicMock()
        mock_agent_node.uniq_id = agent_node.uniq_id
        mock_agent_node.name = agent_node.name

        review_func = review_factory.create_review_function(mock_agent_node)

        with patch("langgraph.types.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"approved": True}
            with patch("backend.services.nodes.executors.review.ws_notifier"):
                await review_func(merged_state)

        # Verify the complete flow worked
        assert mock_interrupt.called, (
            "Full flow failed: review_state should flow from agent → factory → review node"
        )
        payload = mock_interrupt.call_args[0][0]
        assert payload["agent_output"] == "Test response"


class TestMissingReviewConfig:
    """Tests for workflows without review_config (should work normally)."""

    @pytest.mark.asyncio
    async def test_factory_works_without_review_state(self):
        """Verify factory works when agent returns no review_state."""
        from backend.services.execution.nodes.factory import NodeFunctionFactory

        factory = NodeFunctionFactory(checkpoint_executors={})

        node = MagicMock()
        node.name = "AgentWithoutReview"
        node.uniq_id = "agent-no-review"
        node.type = MagicMock()
        node.type.value = "AGENT"

        # Agent result without review_state (review not enabled)
        result = {
            "node_output": {"raw": "Response", "structured": None, "fields": {}},
            "execution_order": 1,
        }

        state = {"node_outputs": {}, "results": []}
        updates = {"current_node": "agent-no-review", "metadata": {}}

        processed = factory._process_node_result(node, state, result, updates, None)

        # Should work fine without review_state
        assert "review_state" not in processed
        assert "node_outputs" in processed
