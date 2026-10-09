"""Tests for ReviewExecutor.

These tests verify the review execution logic including:
- Human review interrupt/response processing
- LLM review invocation and response parsing
- Review response format handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# Mock Data Classes
# ---------------------------------------------------------------------------


@dataclass
class MockReviewConfig:
    """Mock ReviewConfig for testing."""

    review_enabled: bool = True
    review_mode: str = "human"
    review_prompt: str = "Review the output"
    max_iterations: int = 3
    timeout_seconds: Optional[int] = None
    auto_approve_on_timeout: bool = False
    auto_approve_on_max_iterations: bool = True
    reviewer_llm_config: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_enabled": self.review_enabled,
            "review_mode": self.review_mode,
            "review_prompt": self.review_prompt,
            "max_iterations": self.max_iterations,
        }


@dataclass
class MockEnhancedNodeData:
    """Mock EnhancedNodeData for testing."""

    uniq_id: str = "test-agent-001"
    name: str = "Test Agent"
    type: str = "AGENT"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def review_config_human():
    """Human review config."""
    return MockReviewConfig(review_mode="human")


@pytest.fixture
def review_config_llm():
    """LLM review config."""
    return MockReviewConfig(
        review_mode="llm",
        reviewer_llm_config={"provider": "azure_openai", "model_name": "gpt-4"},
    )


@pytest.fixture
def mock_workflow_state():
    """Mock workflow state."""
    return {
        "execution_id": "exec-123",
        "db_execution_id": "db-exec-456",
        "graph_name": "TestGraph",
    }


@pytest.fixture
def mock_node():
    """Mock agent node."""
    return MockEnhancedNodeData()


@pytest.fixture
def review_history_empty():
    """Empty review history."""
    return []


@pytest.fixture
def review_history_with_feedback():
    """Review history with prior feedback."""
    return [
        {
            "iteration": 1,
            "agent_output": "First attempt output",
            "feedback": "Missing required details",
            "reviewer_type": "human",
            "timestamp": "2025-01-01T00:00:00Z",
        }
    ]


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestReviewExecutorHumanReview:
    """Tests for human review execution."""

    @pytest.fixture
    def review_executor(self):
        """Create a ReviewExecutor instance."""
        from backend.services.execution.review.executor import ReviewExecutor

        return ReviewExecutor()

    @pytest.mark.asyncio
    async def test_human_review_calls_interrupt(
        self,
        review_executor,
        mock_node,
        mock_workflow_state,
        review_config_human,
        review_history_empty,
    ):
        """Should call interrupt() with correct payload for human review."""
        with (
            patch("langgraph.types.interrupt") as mock_interrupt,
            patch("backend.services.execution.review.executor.ws_notifier") as mock_ws,
        ):
            # Configure interrupt to return an approval
            mock_interrupt.return_value = {"approved": True}
            mock_ws.on_execution_paused = AsyncMock()

            await review_executor.execute_review(
                node=mock_node,
                state=mock_workflow_state,
                agent_output="Test output",
                review_config=review_config_human,
                review_history=review_history_empty,
            )

            # Verify interrupt was called with correct payload
            mock_interrupt.assert_called_once()
            call_args = mock_interrupt.call_args[0][0]
            assert call_args["type"] == "agent_review"
            assert call_args["node_id"] == mock_node.uniq_id
            assert call_args["agent_output"] == "Test output"
            assert call_args["review_mode"] == "human"

    @pytest.mark.asyncio
    async def test_human_review_sends_websocket_notification(
        self,
        review_executor,
        mock_node,
        mock_workflow_state,
        review_config_human,
        review_history_empty,
    ):
        """Should send pause notification via WebSocket."""
        with (
            patch("langgraph.types.interrupt") as mock_interrupt,
            patch("backend.services.execution.review.executor.ws_notifier") as mock_ws,
        ):
            mock_interrupt.return_value = {"approved": True}
            mock_ws.on_execution_paused = AsyncMock()

            await review_executor.execute_review(
                node=mock_node,
                state=mock_workflow_state,
                agent_output="Test output",
                review_config=review_config_human,
                review_history=review_history_empty,
            )

            # Verify WebSocket notification was sent
            mock_ws.on_execution_paused.assert_called_once()


class TestReviewExecutorLLMReview:
    """Tests for LLM-based review execution."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"proceed": true, "feedback": "Looks good", "confidence_score": 0.95}'
            )
        )
        return llm

    @pytest.fixture
    def review_executor_with_llm(self, mock_llm):
        """Create a ReviewExecutor with mocked LLM factory."""
        mock_factory = MagicMock()
        mock_llm_instance = MagicMock()
        mock_llm_instance.llm = mock_llm
        mock_factory.create_llm_instance = MagicMock(return_value=mock_llm_instance)

        mock_model_service = MagicMock()
        mock_model_service.enrich_llm_config = MagicMock(side_effect=lambda x: x)

        from backend.services.execution.review.executor import ReviewExecutor

        return ReviewExecutor(
            llm_factory=mock_factory,
            model_service=mock_model_service,
        )

    @pytest.mark.asyncio
    async def test_llm_review_calls_reviewer_llm(
        self,
        review_executor_with_llm,
        mock_node,
        mock_workflow_state,
        review_config_llm,
        review_history_empty,
        mock_llm,
    ):
        """Should invoke reviewer LLM with correct prompt."""
        result = await review_executor_with_llm.execute_review(
            node=mock_node,
            state=mock_workflow_state,
            agent_output="Test output for LLM review",
            review_config=review_config_llm,
            review_history=review_history_empty,
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result
        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_llm_review_auto_approves_on_missing_config(
        self,
        mock_node,
        mock_workflow_state,
        review_history_empty,
    ):
        """Should auto-approve when reviewer LLM config is missing."""
        from backend.services.execution.review.executor import ReviewExecutor

        review_config = MockReviewConfig(
            review_mode="llm",
            reviewer_llm_config=None,  # No LLM config
        )

        executor = ReviewExecutor()

        result = await executor.execute_review(
            node=mock_node,
            state=mock_workflow_state,
            agent_output="Test output",
            review_config=review_config,
            review_history=review_history_empty,
        )

        # Should auto-approve
        assert result["approved"] is True


class TestReviewResponseProcessing:
    """Tests for response parsing and processing."""

    @pytest.fixture
    def review_executor(self):
        """Create a ReviewExecutor instance."""
        from backend.services.execution.review.executor import ReviewExecutor

        return ReviewExecutor()

    def test_parse_approved_response(self, review_executor):
        """Should correctly parse approval response."""
        response = {"approved": True}
        result = review_executor._process_human_review_response(
            response, "test output", 1
        )
        assert result["approved"] is True
        assert result["final_output"] == "test output"

    def test_parse_rejected_with_feedback(self, review_executor):
        """Should extract feedback from rejection response."""
        response = {"approved": False, "feedback": "Needs improvement"}
        result = review_executor._process_human_review_response(
            response, "test output", 1
        )
        assert result["approved"] is False
        assert result["feedback"] == "Needs improvement"

    def test_parse_wrapped_json_format(self, review_executor):
        """Should handle wrapped format from checkpoint resume."""
        response = {"value": '{"approved": true}'}
        result = review_executor._process_human_review_response(
            response, "test output", 1
        )
        assert result["approved"] is True

    def test_parse_string_approval_keywords(self, review_executor):
        """Should recognize approval keywords in string responses."""
        for keyword in ["approved", "approve", "proceed", "yes", "ok", "pass"]:
            result = review_executor._process_human_review_response(
                keyword, "test output", 1
            )
            assert result["approved"] is True, f"Failed for keyword: {keyword}"

    def test_parse_string_rejection(self, review_executor):
        """Should treat non-approval strings as feedback."""
        response = "The output is incorrect, please fix X"
        result = review_executor._process_human_review_response(
            response, "test output", 1
        )
        assert result["approved"] is False
        assert result["feedback"] == "The output is incorrect, please fix X"


class TestLLMResponseParsing:
    """Tests for LLM review response parsing."""

    @pytest.fixture
    def review_executor(self):
        """Create a ReviewExecutor instance."""
        from backend.services.execution.review.executor import ReviewExecutor

        return ReviewExecutor()

    def test_parse_valid_json_response(self, review_executor):
        """Should parse valid JSON response."""
        content = '{"proceed": true, "feedback": "Good", "confidence_score": 0.9}'
        result = review_executor._parse_llm_review_response(content)

        assert result["proceed"] is True
        assert result["feedback"] == "Good"
        assert result["confidence_score"] == 0.9

    def test_parse_json_in_markdown_block(self, review_executor):
        """Should extract JSON from markdown code block."""
        content = """```json
{"proceed": false, "feedback": "Needs work", "confidence_score": 0.3}
```"""
        result = review_executor._parse_llm_review_response(content)

        assert result["proceed"] is False
        assert result["feedback"] == "Needs work"

    def test_parse_malformed_json_defaults_to_reject(self, review_executor):
        """Should handle malformed LLM response gracefully."""
        content = "This is not valid JSON at all"
        result = review_executor._parse_llm_review_response(content)

        # Should default to not proceeding
        assert result["proceed"] is False
        assert "parse_error" in result["issue_categories"]


class TestReviewHistoryBuilding:
    """Tests for review history and feedback context building."""

    def test_build_feedback_context_empty_history(self):
        """Should return empty string for empty history."""
        from backend.services.execution.review.executor import ReviewExecutor

        result = ReviewExecutor.build_feedback_context([])
        assert result == ""

    def test_build_feedback_context_with_entries(self):
        """Should format feedback context from history."""
        from backend.services.execution.review.executor import ReviewExecutor

        history = [
            {
                "iteration": 1,
                "agent_output": "First output",
                "feedback": "Add more detail",
                "reviewer_type": "human",
            }
        ]
        result = ReviewExecutor.build_feedback_context(history)

        assert "Previous Review Feedback" in result
        assert "Add more detail" in result
        assert "human" in result

    def test_create_history_entry_includes_all_fields(self):
        """Should create complete history entry."""
        from backend.services.execution.review.executor import ReviewExecutor

        entry = ReviewExecutor.create_history_entry(
            iteration=2,
            agent_output="Output text",
            feedback="Needs revision",
            reviewer_type="llm",
            llm_metadata={"confidence_score": 0.7},
        )

        assert entry["iteration"] == 2
        assert entry["agent_output"] == "Output text"
        assert entry["feedback"] == "Needs revision"
        assert entry["reviewer_type"] == "llm"
        assert entry["llm_metadata"]["confidence_score"] == 0.7
        assert "timestamp" in entry
