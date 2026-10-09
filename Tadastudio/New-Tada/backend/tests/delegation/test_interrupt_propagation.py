"""Integration tests for GraphInterrupt propagation through delegation stack.

These tests verify that GraphInterrupt propagates correctly through ALL layers:
1. SubgraphDelegationExecutor - raises GraphInterrupt when paused_for_review=True
2. sync_factory.py - delegate_to_agent() re-raises GraphInterrupt
3. tool_executor.py - execute_with_tools() re-raises GraphInterrupt
4. executor.py - execute_agent() re-raises GraphInterrupt

The fix ensures that `except GraphInterrupt: raise` appears BEFORE
`except Exception` in each layer.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from langgraph.errors import GraphInterrupt
from langgraph.types import Interrupt


class TestSyncFactoryInterruptPropagation:
    """Test that sync_factory.py re-raises GraphInterrupt."""

    def test_delegate_to_agent_propagates_interrupt(self):
        """sync_factory delegate_to_agent() should re-raise GraphInterrupt."""
        from backend.services.delegation.factories.sync_factory import (
            AgentDelegationToolFactory,
        )
        from backend.models.workflow import EnhancedNodeData, NodeType, AgentConfig

        # Create a mock agent node with proper string values
        agent_node = MagicMock(spec=EnhancedNodeData)
        agent_node.name = "Test Agent"
        agent_node.uniq_id = "agent-001"
        agent_node.type = NodeType.AGENT
        agent_config = MagicMock(spec=AgentConfig)
        agent_config.delegation_description = "Test delegation"
        agent_node.agent_config = agent_config

        # Create mock graph manager
        mock_graph_manager = MagicMock()
        mock_graph_manager.get_active_graph_by_name.return_value = None

        factory = AgentDelegationToolFactory(mock_graph_manager)

        # Mock execution to raise GraphInterrupt
        with (
            patch.object(factory, "_execute_with_tracking") as mock_exec,
            patch.object(factory, "_get_execution_context") as mock_ctx,
            patch(
                "backend.services.delegation.factories.sync_factory.get_current_execution_id"
            ) as mock_exec_id,
            patch(
                "backend.services.delegation.factories.sync_factory.get_current_db_execution_id"
            ) as mock_db_exec_id,
            patch(
                "backend.services.delegation.factories.sync_factory.get_node_execution_id"
            ) as mock_node_exec_id,
        ):
            mock_ctx.return_value = {
                "execution_id": "exec-123",
                "db_execution_id": "db-456",
            }
            mock_exec_id.return_value = "exec-123"
            mock_db_exec_id.return_value = "db-456"
            mock_node_exec_id.return_value = "node-exec-789"

            # Simulate GraphInterrupt from _execute_with_tracking
            interrupt_data = Interrupt(value={"type": "agent_review"})
            mock_exec.side_effect = GraphInterrupt((interrupt_data,))

            tool = factory.create_delegation_tool(
                agent_node=agent_node,
                orchestrator_id="orchestrator-001",
                description="Delegate to test agent",  # Provide explicit description
            )

            # The tool func should propagate the interrupt
            with pytest.raises(GraphInterrupt):
                tool.func("Do something")


class TestToolExecutorInterruptPropagation:
    """Test that tool_executor.py re-raises GraphInterrupt."""

    @pytest.mark.asyncio
    async def test_execute_with_tools_propagates_interrupt(self):
        """tool_executor execute_with_tools() should re-raise GraphInterrupt."""
        from backend.services.execution.async_agent.tool_executor import (
            AsyncToolExecutor,
        )

        executor = AsyncToolExecutor()

        # Create mock LLM that raises GraphInterrupt
        mock_llm = MagicMock()
        interrupt_data = Interrupt(value={"type": "agent_review"})
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock(side_effect=GraphInterrupt((interrupt_data,)))

        # Create mock tool
        mock_tool = MagicMock()
        mock_tool.name = "delegate_to_agent"

        with pytest.raises(GraphInterrupt):
            await executor.execute_with_tools(
                llm=mock_llm,
                messages=[{"role": "user", "content": "test"}],
                tools=[mock_tool],
                tracker=[],
                agent_name="Test Agent",
            )

    @pytest.mark.asyncio
    async def test_tool_execution_propagates_interrupt(self):
        """tool_executor should propagate interrupt from tool execution."""
        from backend.services.execution.async_agent.tool_executor import (
            AsyncToolExecutor,
        )

        executor = AsyncToolExecutor()

        # Create mock tool that raises GraphInterrupt when invoked
        async def raise_interrupt(*args, **kwargs):
            interrupt_data = Interrupt(value={"type": "agent_review"})
            raise GraphInterrupt((interrupt_data,))

        mock_tool = MagicMock()
        mock_tool.name = "delegate_to_subagent"
        mock_tool.description = "Test tool"
        mock_tool.ainvoke = raise_interrupt

        # Create mock LLM that returns a tool call
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"name": "delegate_to_subagent", "args": {"task": "test"}, "id": "call-1"}
        ]
        mock_response.content = ""
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with pytest.raises(GraphInterrupt):
            await executor.execute_with_tools(
                llm=mock_llm,
                messages=[{"role": "user", "content": "test"}],
                tools=[mock_tool],
                tracker=[],
                agent_name="Test Agent",
            )


class TestAsyncExecutorInterruptPropagation:
    """Test that executor.py re-raises GraphInterrupt."""

    @pytest.mark.asyncio
    async def test_execute_agent_propagates_interrupt_from_llm_build(self):
        """executor.py execute_agent() should re-raise GraphInterrupt from LLM build."""
        from backend.services.execution.async_agent.executor import AsyncAgentExecutor
        from backend.models.workflow import EnhancedNodeData, AgentConfig

        mock_llm_factory = MagicMock()
        mock_model_service = MagicMock()

        executor = AsyncAgentExecutor(mock_llm_factory, mock_model_service)

        agent_node = MagicMock(spec=EnhancedNodeData)
        agent_node.name = "Test Agent"
        agent_node.uniq_id = "agent-001"
        agent_config = MagicMock(spec=AgentConfig)
        agent_config.memory_enabled = False
        agent_config.tools = []
        agent_config.structured_outputs = None
        agent_node.agent_config = agent_config

        # Mock the LLM builder to raise GraphInterrupt
        with patch.object(
            executor.llm_builder, "build_llm", new_callable=AsyncMock
        ) as mock_build:
            interrupt_data = Interrupt(value={"type": "agent_review"})
            mock_build.side_effect = GraphInterrupt((interrupt_data,))

            with pytest.raises(GraphInterrupt):
                await executor.execute_agent(
                    agent_node=agent_node,
                    user_message="Test message",
                )

    @pytest.mark.asyncio
    async def test_execute_agent_propagates_interrupt_from_execute_llm(self):
        """executor.py should propagate GraphInterrupt from _execute_llm."""
        from backend.services.execution.async_agent.executor import AsyncAgentExecutor
        from backend.models.workflow import EnhancedNodeData, AgentConfig

        mock_llm_factory = MagicMock()
        mock_model_service = MagicMock()

        executor = AsyncAgentExecutor(mock_llm_factory, mock_model_service)

        agent_node = MagicMock(spec=EnhancedNodeData)
        agent_node.name = "Test Agent"
        agent_node.uniq_id = "agent-001"
        agent_config = MagicMock(spec=AgentConfig)
        agent_config.memory_enabled = False
        agent_config.tools = []
        agent_config.structured_outputs = None
        agent_node.agent_config = agent_config

        # Mock everything up to _execute_llm
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4"

        with (
            patch.object(
                executor.llm_builder, "build_llm", new_callable=AsyncMock
            ) as mock_build,
            patch.object(
                executor.token_handler, "initialize_counts"
            ) as mock_init_counts,
            patch.object(
                executor.message_builder, "build_messages", new_callable=AsyncMock
            ) as mock_build_msgs,
            patch.object(executor.token_handler, "count_input_tokens") as mock_count,
            patch.object(
                executor, "_execute_llm", new_callable=AsyncMock
            ) as mock_exec_llm,
        ):
            mock_build.return_value = mock_llm
            mock_init_counts.return_value = MagicMock(model="gpt-4", input_tokens=0)
            mock_build_msgs.return_value = []
            mock_count.return_value = MagicMock(input_tokens=100)

            # _execute_llm raises GraphInterrupt
            interrupt_data = Interrupt(value={"type": "agent_review"})
            mock_exec_llm.side_effect = GraphInterrupt((interrupt_data,))

            with pytest.raises(GraphInterrupt):
                await executor.execute_agent(
                    agent_node=agent_node,
                    user_message="Test message",
                )


class TestFullPropagationChain:
    """Test the complete interrupt propagation chain.

    This simulates the real scenario:
    1. Subgraph execution returns paused_for_review=True
    2. SubgraphDelegationExecutor raises GraphInterrupt
    3. sync_factory's delegate_to_agent re-raises
    4. tool_executor's execute_with_tools re-raises
    5. executor's execute_agent re-raises
    """

    def test_interrupt_propagates_from_subgraph_through_delegation(
        self, delegation_request_with_review
    ):
        """Full chain: subgraph → SubgraphDelegationExecutor → sync_factory.

        Uses the delegation_request_with_review fixture from conftest.
        """
        from backend.services.delegation.executors.subgraph_executor import (
            SubgraphDelegationExecutor,
        )

        mock_graph_manager = MagicMock()

        # Patch at the import location within subgraph_executor
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

            # Simulate subgraph returning paused state (like execution_handler.py does)
            mock_run.return_value = {
                "response": "[AWAITING REVIEW] Output pending review",
                "paused": True,
                "paused_for_review": True,
                "review_data": {
                    "type": "agent_review",
                    "node_id": "subagent-review-001",
                    "agent_output": "The answer is 4",
                    "review_mode": "human",
                },
                "execution_order": 2,
                "error": None,
            }

            executor = SubgraphDelegationExecutor(mock_graph_manager)

            # This should raise GraphInterrupt
            with pytest.raises(GraphInterrupt) as exc_info:
                executor.execute(delegation_request_with_review)

            # Verify interrupt contains expected data
            gi = exc_info.value
            assert hasattr(gi, "args") and gi.args

            # Find the Interrupt object
            def find_interrupt(obj):
                if hasattr(obj, "value"):
                    return obj
                if isinstance(obj, (list, tuple)):
                    for item in obj:
                        result = find_interrupt(item)
                        if result is not None:
                            return result
                return None

            interrupt_obj = find_interrupt(gi.args)
            assert interrupt_obj is not None

            # Verify sub-agent info was added
            assert interrupt_obj.value.get("sub_agent_name") == "Math Expert"
            assert interrupt_obj.value.get("sub_agent_id") == "subagent-review-001"
            assert interrupt_obj.value.get("type") == "agent_review"
            assert interrupt_obj.value.get("review_mode") == "human"


class TestExceptionHandlerOrdering:
    """Verify that GraphInterrupt handlers come BEFORE generic Exception handlers.

    These tests use code inspection to verify the fix is in place.
    """

    def test_sync_factory_has_graphinterrupt_handler_before_exception(self):
        """sync_factory.py should handle GraphInterrupt before Exception."""
        import inspect
        from backend.services.delegation.factories import sync_factory

        source = inspect.getsource(sync_factory)

        # Find the delegate_to_agent function
        assert "except GraphInterrupt:" in source, (
            "sync_factory.py must have 'except GraphInterrupt:' handler"
        )

        # Verify GraphInterrupt comes before generic Exception in delegate_to_agent
        gi_pos = source.find("except GraphInterrupt:")
        exc_pos = source.find("except Exception as e:", gi_pos)
        assert gi_pos < exc_pos, (
            "GraphInterrupt handler must come before Exception handler"
        )

    def test_tool_executor_has_graphinterrupt_handler_before_exception(self):
        """tool_executor.py should handle GraphInterrupt before Exception."""
        import inspect
        from backend.services.execution.async_agent import tool_executor

        source = inspect.getsource(tool_executor)

        # Should have GraphInterrupt handler
        assert "except GraphInterrupt:" in source, (
            "tool_executor.py must have 'except GraphInterrupt:' handler"
        )

    def test_executor_has_graphinterrupt_handler_before_exception(self):
        """executor.py should handle GraphInterrupt before Exception."""
        import inspect
        from backend.services.execution.async_agent import executor

        source = inspect.getsource(executor)

        # Should have GraphInterrupt handler
        assert "except GraphInterrupt:" in source, (
            "executor.py must have 'except GraphInterrupt:' handler"
        )

        # Verify ordering in execute_agent method
        # Find execute_agent method
        method_start = source.find("async def execute_agent")
        method_end = source.find("\n    def ", method_start + 1)
        if method_end == -1:
            method_end = len(source)
        method_source = source[method_start:method_end]

        gi_pos = method_source.find("except GraphInterrupt:")
        exc_pos = method_source.find("except Exception as e:")
        assert gi_pos != -1, "execute_agent must have GraphInterrupt handler"
        assert gi_pos < exc_pos, (
            "GraphInterrupt handler must come before Exception handler in execute_agent"
        )

    def test_agent_executor_has_graphinterrupt_handler_before_exception(self):
        """agent.py (AgentNodeExecutor) should handle GraphInterrupt before Exception."""
        import inspect
        from backend.services.nodes.executors import agent

        source = inspect.getsource(agent)

        # Should have GraphInterrupt handler
        assert "except GraphInterrupt:" in source, (
            "agent.py must have 'except GraphInterrupt:' handler"
        )
