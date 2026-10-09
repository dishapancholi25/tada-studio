"""Shared fixtures for agent review tests."""

import pytest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


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
# Review Config Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def review_config_human():
    """Human review configuration."""
    return MockReviewConfig(review_mode="human")


@pytest.fixture
def review_config_llm():
    """LLM review configuration."""
    return MockReviewConfig(
        review_mode="llm",
        reviewer_llm_config={"provider": "azure_openai", "model_name": "gpt-4"},
    )


# ---------------------------------------------------------------------------
# State Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_workflow_state():
    """Mock workflow state with all fields required for review architecture."""
    return {
        "execution_id": "exec-123",
        "db_execution_id": "db-exec-456",
        "graph_name": "TestGraph",
        "review_state": {},  # Required for review node architecture
        "pending_review": None,
        "custom_data": None,
    }


@pytest.fixture
def mock_node():
    """Mock agent node."""
    return MockEnhancedNodeData()


# ---------------------------------------------------------------------------
# History Fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def review_history_multi_iteration():
    """Review history with multiple iterations."""
    return [
        {
            "iteration": 1,
            "agent_output": "First attempt",
            "feedback": "Too brief",
            "reviewer_type": "human",
            "timestamp": "2025-01-01T00:00:00Z",
        },
        {
            "iteration": 2,
            "agent_output": "Second attempt with more detail",
            "feedback": "Missing conclusion",
            "reviewer_type": "human",
            "timestamp": "2025-01-01T00:01:00Z",
        },
    ]


# ---------------------------------------------------------------------------
# Mock Service Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ws_notifier():
    """Mock WebSocket notifier."""
    notifier = AsyncMock()
    notifier.on_execution_paused = AsyncMock()
    return notifier


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.fixture
def mock_review_state():
    """Mock AgentReviewState database record."""
    state = MagicMock()
    state.id = uuid4()
    state.graph_execution_id = "exec-123"
    state.node_execution_id = None
    state.agent_node_id = "node-456"
    state.checkpoint_id = None
    state.thread_id = "thread-789"
    state.status = "pending_review"
    state.current_iteration = 1
    state.max_iterations = 3
    state.review_mode = "human"
    state.review_prompt = "Review this output"
    state.current_agent_output = "Agent output text"
    state.review_history = []
    state.input_message = "Original input"
    state.resume_response = None
    state.review_config = {}
    state.created_at = datetime.now(timezone.utc)
    state.updated_at = datetime.now(timezone.utc)
    return state
