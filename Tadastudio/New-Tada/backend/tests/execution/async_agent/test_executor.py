"""Tests for AsyncAgentExecutor.

These tests verify the four execution paths in _execute_llm():
1. Both tools AND structured output → Two-phase execution
2. Only structured output → Direct structured output
3. Only tools → Tool execution with ReAct
4. Neither → Regular execution

They also verify that tools are NOT blocked when structured output is configured.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage


class TestExecuteLLMDecisionLogic:
    """Test the _execute_llm method's four execution paths.

    These tests ensure the correct execution path is chosen based on
    the combination of tools and structured output configuration.
    """

    @pytest.fixture
    def mock_executor(self):
        """Create a mock AsyncAgentExecutor with mocked handlers."""
        # We'll patch the imports and create a minimal executor for testing
        with patch(
            "backend.services.execution.async_agent.executor.ExecutionConfig"
        ) as mock_exec_config:
            mock_exec_config.enable_streaming.return_value = False

            from backend.services.execution.async_agent.executor import (
                AsyncAgentExecutor,
            )

            # Create executor with mocked dependencies
            mock_llm_factory = MagicMock()
            mock_model_service = MagicMock()

            executor = AsyncAgentExecutor(
                llm_factory=mock_llm_factory,
                model_service=mock_model_service,
            )

            # Mock the handlers
            executor.structured_output_handler = MagicMock()
            executor.tool_executor = AsyncMock()

            return executor

    @pytest.mark.asyncio
    async def test_case1_tools_and_structured_output_uses_two_phase(
        self,
        mock_executor,
        agent_config_with_tools_and_structured,
        mock_llm,
        execution_config_default,
    ):
        """CASE 1: Both tools AND structured output → calls execute_with_tools_then_format."""
        # Setup
        mock_executor.structured_output_handler.should_use_structured_output.return_value = True
        mock_executor.structured_output_handler.execute_with_tools_then_format = (
            AsyncMock(
                return_value=AIMessage(
                    content='{"answer": "4", "explanation": "2+2=4"}'
                )
            )
        )

        tools = [MagicMock(name="calculator")]
        messages = [HumanMessage(content="What is 2+2?")]

        # Execute
        await mock_executor._execute_llm(
            llm=mock_llm,
            messages=messages,
            agent_config=agent_config_with_tools_and_structured,
            tools=tools,
            config=execution_config_default,
            agent_name="Test Agent",
        )

        # Verify two-phase execution was called
        mock_executor.structured_output_handler.execute_with_tools_then_format.assert_called_once()

        # Verify other paths were NOT called
        mock_executor.structured_output_handler.execute_with_structured_output.assert_not_called()
        mock_executor.tool_executor.execute_with_tools.assert_not_called()
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_case2_structured_output_only_uses_direct_structured(
        self,
        mock_executor,
        agent_config_no_tools_with_structured,
        mock_llm,
        execution_config_default,
    ):
        """CASE 2: Only structured output (no tools) → calls execute_with_structured_output."""
        # Setup
        mock_executor.structured_output_handler.should_use_structured_output.return_value = True
        mock_executor.structured_output_handler.execute_with_structured_output = (
            AsyncMock(return_value=AIMessage(content='{"answer": "4"}'))
        )

        tools = None  # No tools
        messages = [HumanMessage(content="What is 2+2?")]

        # Execute
        await mock_executor._execute_llm(
            llm=mock_llm,
            messages=messages,
            agent_config=agent_config_no_tools_with_structured,
            tools=tools,
            config=execution_config_default,
            agent_name="Test Agent",
        )

        # Verify direct structured output was called
        mock_executor.structured_output_handler.execute_with_structured_output.assert_called_once()

        # Verify other paths were NOT called
        mock_executor.structured_output_handler.execute_with_tools_then_format.assert_not_called()
        mock_executor.tool_executor.execute_with_tools.assert_not_called()
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_case3_tools_only_uses_tool_executor(
        self,
        mock_executor,
        agent_config_with_tools_no_structured,
        mock_llm,
        execution_config_default,
    ):
        """CASE 3: Only tools (no structured output) → calls tool_executor.execute_with_tools."""
        # Setup
        mock_executor.structured_output_handler.should_use_structured_output.return_value = False
        mock_executor.tool_executor.execute_with_tools = AsyncMock(
            return_value=AIMessage(content="Calculator result: 4")
        )

        tools = [MagicMock(name="calculator")]
        messages = [HumanMessage(content="What is 2+2?")]

        # Execute
        await mock_executor._execute_llm(
            llm=mock_llm,
            messages=messages,
            agent_config=agent_config_with_tools_no_structured,
            tools=tools,
            config=execution_config_default,
            agent_name="Test Agent",
        )

        # Verify tool executor was called
        mock_executor.tool_executor.execute_with_tools.assert_called_once()

        # Verify other paths were NOT called
        mock_executor.structured_output_handler.execute_with_tools_then_format.assert_not_called()
        mock_executor.structured_output_handler.execute_with_structured_output.assert_not_called()
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_case4_neither_uses_regular_execution(
        self,
        mock_executor,
        agent_config_no_tools_no_structured,
        mock_llm,
        execution_config_default,
    ):
        """CASE 4: Neither tools nor structured output → calls llm.ainvoke directly."""
        # Setup
        mock_executor.structured_output_handler.should_use_structured_output.return_value = False
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="The answer is 4"))

        tools = None  # No tools
        messages = [HumanMessage(content="What is 2+2?")]

        # Execute
        await mock_executor._execute_llm(
            llm=mock_llm,
            messages=messages,
            agent_config=agent_config_no_tools_no_structured,
            tools=tools,
            config=execution_config_default,
            agent_name="Test Agent",
        )

        # Verify regular LLM invocation was called
        mock_llm.ainvoke.assert_called_once_with(messages)

        # Verify other paths were NOT called
        mock_executor.structured_output_handler.execute_with_tools_then_format.assert_not_called()
        mock_executor.structured_output_handler.execute_with_structured_output.assert_not_called()
        mock_executor.tool_executor.execute_with_tools.assert_not_called()


class TestGetToolsIfNeeded:
    """Test that tools are always loaded when available.

    This is the key regression test - ensuring that tools are NOT blocked
    when structured output is configured (the bug that was fixed).
    """

    @pytest.fixture
    def executor_with_tools_callback(self):
        """Create executor with a tools callback that returns mock tools."""
        with patch("backend.services.execution.async_agent.executor.ExecutionConfig"):
            from backend.services.execution.async_agent.executor import (
                AsyncAgentExecutor,
            )

            mock_llm_factory = MagicMock()
            mock_model_service = MagicMock()

            # Create a callback that returns tools
            mock_tools = [MagicMock(name="tool1"), MagicMock(name="tool2")]

            def get_tools_callback(**kwargs):
                return mock_tools

            executor = AsyncAgentExecutor(
                llm_factory=mock_llm_factory,
                model_service=mock_model_service,
                get_tools_callback=get_tools_callback,
            )

            executor._mock_tools = mock_tools
            return executor

    def test_tools_loaded_even_with_structured_output(
        self,
        executor_with_tools_callback,
        agent_config_with_tools_and_structured,
        execution_config_default,
    ):
        """REGRESSION TEST: Verify tools are NOT blocked when structured output is configured.

        This is the key test for the fix. Previously, _get_tools_if_needed() would
        return None when structured_outputs was configured, blocking tool/sub-agent
        execution. After the fix, tools should always be loaded.
        """
        # Create a mock agent node
        from backend.tests.conftest import MockEnhancedNodeData

        agent_node = MockEnhancedNodeData(
            uniq_id="test-agent",
            name="Test Agent",
            agent_config=agent_config_with_tools_and_structured,
        )

        # Get tools - this should NOT return None even with structured output
        tools = executor_with_tools_callback._get_tools_if_needed(
            agent_node=agent_node,
            agent_config=agent_config_with_tools_and_structured,
            config=execution_config_default,
            graph_name="TestGraph",
        )

        # CRITICAL ASSERTION: Tools should be returned, not None
        assert tools is not None, (
            "Tools should NOT be blocked when structured output is configured. "
            "This was the bug that was fixed."
        )
        assert len(tools) == 2, "Should return the mock tools from callback"

    def test_tools_loaded_without_structured_output(
        self,
        executor_with_tools_callback,
        agent_config_with_tools_no_structured,
        execution_config_default,
    ):
        """Verify tools work normally without structured output."""
        from backend.tests.conftest import MockEnhancedNodeData

        agent_node = MockEnhancedNodeData(
            uniq_id="test-agent",
            name="Test Agent",
            agent_config=agent_config_with_tools_no_structured,
        )

        tools = executor_with_tools_callback._get_tools_if_needed(
            agent_node=agent_node,
            agent_config=agent_config_with_tools_no_structured,
            config=execution_config_default,
            graph_name="TestGraph",
        )

        assert tools is not None, "Tools should be returned when no structured output"
        assert len(tools) == 2

    def test_no_tools_returned_when_no_callback(
        self,
        agent_config_with_tools_and_structured,
        execution_config_default,
    ):
        """Verify None is returned when there's no tools callback."""
        with patch("backend.services.execution.async_agent.executor.ExecutionConfig"):
            from backend.services.execution.async_agent.executor import (
                AsyncAgentExecutor,
            )
            from backend.tests.conftest import MockEnhancedNodeData

            # Executor WITHOUT tools callback
            executor = AsyncAgentExecutor(
                llm_factory=MagicMock(),
                model_service=MagicMock(),
                get_tools_callback=None,  # No callback
            )

            agent_node = MockEnhancedNodeData(
                uniq_id="test-agent",
                name="Test Agent",
                agent_config=agent_config_with_tools_and_structured,
            )

            tools = executor._get_tools_if_needed(
                agent_node=agent_node,
                agent_config=agent_config_with_tools_and_structured,
                config=execution_config_default,
                graph_name="TestGraph",
            )

            # Without a callback, should return None (no way to get tools)
            assert tools is None


class TestExecutionModeLogging:
    """Test that the correct execution mode is logged."""

    @pytest.fixture
    def executor_with_logger(self):
        """Create executor with accessible logger."""
        with patch(
            "backend.services.execution.async_agent.executor.ExecutionConfig"
        ) as mock_config:
            mock_config.enable_streaming.return_value = False

            from backend.services.execution.async_agent.executor import (
                AsyncAgentExecutor,
            )

            executor = AsyncAgentExecutor(
                llm_factory=MagicMock(),
                model_service=MagicMock(),
            )

            executor.structured_output_handler = MagicMock()
            executor.tool_executor = AsyncMock()

            return executor

    @pytest.mark.asyncio
    async def test_logs_two_phase_execution(
        self,
        executor_with_logger,
        agent_config_with_tools_and_structured,
        mock_llm,
        execution_config_default,
    ):
        """Verify logging for two-phase execution path."""
        executor_with_logger.structured_output_handler.should_use_structured_output.return_value = True
        executor_with_logger.structured_output_handler.execute_with_tools_then_format = AsyncMock(
            return_value=AIMessage(content="{}")
        )

        with patch.object(executor_with_logger, "logger") as mock_logger:
            await executor_with_logger._execute_llm(
                llm=mock_llm,
                messages=[HumanMessage(content="test")],
                agent_config=agent_config_with_tools_and_structured,
                tools=[MagicMock()],
                config=execution_config_default,
                agent_name="Test Agent",
            )

            # Check that two-phase execution was logged
            mock_logger.info.assert_called()
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any(
                "Two-phase" in str(call) or "two-phase" in str(call)
                for call in log_calls
            ), "Should log two-phase execution"
