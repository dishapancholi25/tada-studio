"""Tests for StructuredOutputHandler.

These tests verify:
1. The should_use_structured_output decision logic
2. The execute_with_tools_then_format two-phase execution
3. The _build_format_messages helper
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class TestShouldUseStructuredOutput:
    """Test the should_use_structured_output decision logic."""

    @pytest.fixture
    def handler(self):
        """Create a StructuredOutputHandler instance."""
        from backend.services.execution.async_agent.structured_output_handler import (
            StructuredOutputHandler,
        )

        return StructuredOutputHandler()

    def test_returns_true_when_format_output_and_structured_outputs(
        self, handler, agent_config_with_tools_and_structured
    ):
        """Should return True when both format_output=True and structured_outputs exist."""
        result = handler.should_use_structured_output(
            agent_config=agent_config_with_tools_and_structured,
            format_output=True,
        )
        assert result is True

    def test_returns_false_when_format_output_false(
        self, handler, agent_config_with_tools_and_structured
    ):
        """Should return False when format_output=False."""
        result = handler.should_use_structured_output(
            agent_config=agent_config_with_tools_and_structured,
            format_output=False,
        )
        assert result is False

    def test_returns_false_when_no_structured_outputs(
        self, handler, agent_config_no_tools_no_structured
    ):
        """Should return False when structured_outputs is empty."""
        result = handler.should_use_structured_output(
            agent_config=agent_config_no_tools_no_structured,
            format_output=True,
        )
        assert result is False

    def test_returns_false_when_structured_outputs_none(self, handler):
        """Should return False when structured_outputs is None."""

        # Create a config without structured_outputs attribute
        class ConfigWithoutStructured:
            pass

        config = ConfigWithoutStructured()

        result = handler.should_use_structured_output(
            agent_config=config,
            format_output=True,
        )
        assert result is False

    def test_returns_false_when_structured_outputs_empty_list(self, handler):
        """Should return False when structured_outputs is an empty list."""

        class ConfigWithEmptyStructured:
            structured_outputs = []

        config = ConfigWithEmptyStructured()

        result = handler.should_use_structured_output(
            agent_config=config,
            format_output=True,
        )
        assert result is False


class TestBuildFormatMessages:
    """Test the _build_format_messages helper method."""

    @pytest.fixture
    def handler(self):
        """Create a StructuredOutputHandler instance."""
        from backend.services.execution.async_agent.structured_output_handler import (
            StructuredOutputHandler,
        )

        return StructuredOutputHandler()

    def test_builds_messages_from_ai_message(self, handler):
        """Should build formatting messages from an AIMessage."""
        tool_response = AIMessage(content="The calculation result is 4.")

        messages = handler._build_format_messages(tool_response)

        assert len(messages) == 2
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert "formatting assistant" in messages[0].content.lower()
        assert "The calculation result is 4." in messages[1].content

    def test_builds_messages_from_string(self, handler):
        """Should handle non-AIMessage responses."""
        # Test with a simple object that doesn't have .content
        tool_response = "Plain string response"

        messages = handler._build_format_messages(tool_response)

        assert len(messages) == 2
        assert "Plain string response" in messages[1].content

    def test_builds_messages_from_object_with_content(self, handler):
        """Should extract content from objects with content attribute."""

        class ResponseWithContent:
            content = "Response from tool"

        tool_response = ResponseWithContent()

        messages = handler._build_format_messages(tool_response)

        assert len(messages) == 2
        assert "Response from tool" in messages[1].content


class TestExecuteWithToolsThenFormat:
    """Test the two-phase execution method."""

    @pytest.fixture
    def handler(self):
        """Create a StructuredOutputHandler instance."""
        from backend.services.execution.async_agent.structured_output_handler import (
            StructuredOutputHandler,
        )

        return StructuredOutputHandler()

    @pytest.fixture
    def mock_tool_executor(self):
        """Create a mock tool executor."""
        executor = AsyncMock()
        executor.execute_with_tools = AsyncMock(
            return_value=AIMessage(content="Tool execution result: 2+2=4")
        )
        return executor

    @pytest.fixture
    def mock_structured_result(self):
        """Create a mock structured output result."""
        result = MagicMock()
        result.model_dump_json.return_value = '{"answer": "4", "explanation": "2+2=4"}'
        return result

    @pytest.mark.asyncio
    async def test_calls_tool_executor_first(
        self,
        handler,
        mock_llm,
        mock_tool_executor,
        mock_tools,
        agent_config_with_tools_and_structured,
        mock_structured_result,
    ):
        """Phase 1: Should call tool_executor.execute_with_tools."""
        # Setup mock LLM to return structured result
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_structured_result
        )

        messages = [HumanMessage(content="What is 2+2?")]

        # Patch _create_schema to avoid actual schema creation
        with patch.object(handler, "_create_schema", return_value=MagicMock()):
            await handler.execute_with_tools_then_format(
                llm=mock_llm,
                messages=messages,
                tools=mock_tools,
                agent_config=agent_config_with_tools_and_structured,
                tool_executor=mock_tool_executor,
                agent_name="Test Agent",
            )

        # Verify tool executor was called
        mock_tool_executor.execute_with_tools.assert_called_once()

        # Verify it was called with the correct LLM and messages
        call_args = mock_tool_executor.execute_with_tools.call_args
        assert call_args[0][0] == mock_llm  # First positional arg is llm
        assert call_args[0][1] == messages  # Second is messages

    @pytest.mark.asyncio
    async def test_formats_with_structured_output_second(
        self,
        handler,
        mock_llm,
        mock_tool_executor,
        mock_tools,
        agent_config_with_tools_and_structured,
        mock_structured_result,
    ):
        """Phase 2: Should format response with structured output."""
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_structured_result
        )

        messages = [HumanMessage(content="What is 2+2?")]

        with patch.object(handler, "_create_schema", return_value=MagicMock()):
            await handler.execute_with_tools_then_format(
                llm=mock_llm,
                messages=messages,
                tools=mock_tools,
                agent_config=agent_config_with_tools_and_structured,
                tool_executor=mock_tool_executor,
                agent_name="Test Agent",
            )

        # Verify with_structured_output was called (Phase 2)
        mock_llm.with_structured_output.assert_called_once()

        # Verify the structured LLM was invoked
        mock_llm.with_structured_output.return_value.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_ai_message_with_json(
        self,
        handler,
        mock_llm,
        mock_tool_executor,
        mock_tools,
        agent_config_with_tools_and_structured,
        mock_structured_result,
    ):
        """Should return AIMessage with JSON content."""
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_structured_result
        )

        messages = [HumanMessage(content="What is 2+2?")]

        with patch.object(handler, "_create_schema", return_value=MagicMock()):
            result = await handler.execute_with_tools_then_format(
                llm=mock_llm,
                messages=messages,
                tools=mock_tools,
                agent_config=agent_config_with_tools_and_structured,
                tool_executor=mock_tool_executor,
                agent_name="Test Agent",
            )

        # Verify result is an AIMessage
        assert isinstance(result, AIMessage)

        # Verify content is JSON
        assert '"answer"' in result.content
        assert '"4"' in result.content

        # Verify structured flag is set
        assert result.additional_kwargs.get("structured") is True

    @pytest.mark.asyncio
    async def test_passes_kwargs_to_tool_executor(
        self,
        handler,
        mock_llm,
        mock_tool_executor,
        mock_tools,
        agent_config_with_tools_and_structured,
        mock_structured_result,
    ):
        """Should pass additional kwargs (ws_notifier, execution_id) to tool_executor."""
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_structured_result
        )

        messages = [HumanMessage(content="test")]
        mock_ws_notifier = MagicMock()

        with patch.object(handler, "_create_schema", return_value=MagicMock()):
            await handler.execute_with_tools_then_format(
                llm=mock_llm,
                messages=messages,
                tools=mock_tools,
                agent_config=agent_config_with_tools_and_structured,
                tool_executor=mock_tool_executor,
                agent_name="Test Agent",
                ws_notifier=mock_ws_notifier,
                execution_id="exec-123",
                node_id="node-456",
            )

        # Verify kwargs were passed through
        call_kwargs = mock_tool_executor.execute_with_tools.call_args[1]
        assert call_kwargs["ws_notifier"] == mock_ws_notifier
        assert call_kwargs["execution_id"] == "exec-123"
        assert call_kwargs["node_id"] == "node-456"


class TestExecuteWithStructuredOutput:
    """Test the direct structured output execution (no tools)."""

    @pytest.fixture
    def handler(self):
        """Create a StructuredOutputHandler instance."""
        from backend.services.execution.async_agent.structured_output_handler import (
            StructuredOutputHandler,
        )

        return StructuredOutputHandler()

    @pytest.fixture
    def mock_structured_result(self):
        """Create a mock structured output result."""
        result = MagicMock()
        result.model_dump_json.return_value = '{"answer": "4"}'
        return result

    @pytest.mark.asyncio
    async def test_creates_schema_from_config(
        self,
        handler,
        mock_llm,
        agent_config_no_tools_with_structured,
        mock_structured_result,
    ):
        """Should create schema from agent_config.structured_outputs."""
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_structured_result
        )

        messages = [HumanMessage(content="What is 2+2?")]

        with patch.object(handler, "_create_schema") as mock_create_schema:
            mock_create_schema.return_value = MagicMock()

            await handler.execute_with_structured_output(
                llm=mock_llm,
                messages=messages,
                agent_config=agent_config_no_tools_with_structured,
            )

            # Verify _create_schema was called with the structured output config
            mock_create_schema.assert_called_once()
            call_args = mock_create_schema.call_args[0][0]
            assert call_args["model_name"] == "MathResult"

    @pytest.mark.asyncio
    async def test_returns_ai_message(
        self,
        handler,
        mock_llm,
        agent_config_no_tools_with_structured,
        mock_structured_result,
    ):
        """Should return AIMessage with JSON content."""
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_structured_result
        )

        messages = [HumanMessage(content="test")]

        with patch.object(handler, "_create_schema", return_value=MagicMock()):
            result = await handler.execute_with_structured_output(
                llm=mock_llm,
                messages=messages,
                agent_config=agent_config_no_tools_with_structured,
            )

        assert isinstance(result, AIMessage)
        assert result.additional_kwargs.get("structured") is True
