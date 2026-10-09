"""Shared fixtures for subgraph tests.

These fixtures support testing of sub-agent execution, review handling,
and pause propagation in subgraph contexts.
"""

import pytest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from langchain_core.messages import AIMessage

from backend.models.workflow import NodeType


# ---------------------------------------------------------------------------
# Auto-use Fixtures (applied to all tests in this directory)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_iteration_manager():
    """Auto-mock SubagentIterationManager to avoid database dependency in unit tests.

    The SubgraphDelegationExecutor.execute() method calls
    SubagentIterationManager.get_current_iteration() which queries the database.
    Since these are unit tests with mocks, we mock this call to avoid requiring
    the actual database connection.
    """
    with patch(
        "backend.services.execution.subagent.SubagentIterationManager.get_current_iteration"
    ) as mock_get_iteration:
        mock_get_iteration.return_value = 1
        yield mock_get_iteration


# ---------------------------------------------------------------------------
# Mock Data Classes
# ---------------------------------------------------------------------------


@dataclass
class MockReviewConfig:
    """Mock ReviewConfig for sub-agent review testing."""

    review_enabled: bool = True
    review_mode: str = "human"
    review_prompt: str = "Review the sub-agent output"
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
class MockAgentConfig:
    """Mock AgentConfig for sub-agent testing."""

    system_prompt: str = "You are a helpful assistant"
    agent_type: str = "conversational"
    max_iterations: int = 50
    temperature: float = 0
    tools: List[str] = field(default_factory=list)
    memory_enabled: bool = False
    is_orchestrator: bool = False
    delegated_agents: List[str] = field(default_factory=list)
    review_config: Optional[MockReviewConfig] = None
    llm_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "provider": "azure_openai",
            "model_name": "gpt-4",
        }
    )


@dataclass
class MockEnhancedNodeData:
    """Mock EnhancedNodeData for sub-agent testing."""

    uniq_id: str = "subagent-001"
    name: str = "Math Expert"
    type: NodeType = NodeType.AGENT
    description: str = "Math specialist sub-agent"
    is_sub_agent: bool = True
    parent_agent_id: Optional[str] = "orchestrator-001"
    agent_config: Optional[MockAgentConfig] = None

    def __post_init__(self):
        if self.agent_config is None:
            self.agent_config = MockAgentConfig()


# ---------------------------------------------------------------------------
# SubAgentState Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sub_agent_state():
    """Base SubAgentState for testing with all required fields."""
    return {
        "task_description": "Calculate 2+2",
        "task_id": "task-001",
        "parent_execution_id": "exec-123",
        "parent_db_execution_id": "db-exec-456",
        "parent_node_id": "orchestrator-001",
        "parent_node_execution_id": "node-exec-789",
        "parent_node_name": "Orchestrator",
        "execution_order": 1,
        "start_time": None,
        "end_time": None,
        "agent_node_id": "subagent-001",
        "agent_node_name": "Math Expert",
        "agent_config": None,
        "graph_name": "TestWorkflow",
        "tool_node_mapping": {},
        "tool_execution_tracker": [],
        "response": None,
        "structured_output": None,
        "tool_executions": [],
        "error": None,
        "paused": None,
        "paused_for_review": None,
        "review_data": None,
        "messages": [],
        "metadata": {},
    }


@pytest.fixture
def sub_agent_state_with_response(sub_agent_state):
    """SubAgentState with a completed response."""
    return {
        **sub_agent_state,
        "response": "The answer is 4",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sub_agent_state_paused(sub_agent_state):
    """SubAgentState in paused-for-review state."""
    return {
        **sub_agent_state,
        "response": "[AWAITING REVIEW] Math Expert output is pending human review.",
        "paused": True,
        "paused_for_review": True,
        "review_data": {
            "type": "agent_review",
            "node_id": "subagent-001",
            "node_name": "Math Expert",
            "agent_output": "The answer is 4",
            "review_prompt": "Review the math calculation",
            "is_sub_agent": True,
        },
        "metadata": {
            "paused_for_review": True,
            "review_node_id": "subagent-001",
            "review_node_name": "Math Expert",
        },
    }


# ---------------------------------------------------------------------------
# Node Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sub_agent_node():
    """Basic sub-agent node without review config."""
    return MockEnhancedNodeData(
        uniq_id="subagent-001",
        name="Math Expert",
        is_sub_agent=True,
        parent_agent_id="orchestrator-001",
        agent_config=MockAgentConfig(
            system_prompt="You are a math specialist",
        ),
    )


@pytest.fixture
def sub_agent_node_with_human_review():
    """Sub-agent node with human review enabled."""
    return MockEnhancedNodeData(
        uniq_id="subagent-review-001",
        name="Math Expert",
        is_sub_agent=True,
        parent_agent_id="orchestrator-001",
        agent_config=MockAgentConfig(
            system_prompt="You are a math specialist",
            review_config=MockReviewConfig(
                review_enabled=True,
                review_mode="human",
                review_prompt="Review the math calculation for accuracy",
                max_iterations=3,
            ),
        ),
    )


@pytest.fixture
def sub_agent_node_with_llm_review():
    """Sub-agent node with LLM review enabled."""
    return MockEnhancedNodeData(
        uniq_id="subagent-llm-review-001",
        name="Math Expert",
        is_sub_agent=True,
        parent_agent_id="orchestrator-001",
        agent_config=MockAgentConfig(
            system_prompt="You are a math specialist",
            review_config=MockReviewConfig(
                review_enabled=True,
                review_mode="llm",
                review_prompt="Verify the mathematical correctness",
                max_iterations=2,
                reviewer_llm_config={
                    "provider": "azure_openai",
                    "model_name": "gpt-4",
                },
            ),
        ),
    )


@pytest.fixture
def sub_agent_node_review_disabled():
    """Sub-agent node with review explicitly disabled."""
    return MockEnhancedNodeData(
        uniq_id="subagent-no-review-001",
        name="Math Expert",
        is_sub_agent=True,
        parent_agent_id="orchestrator-001",
        agent_config=MockAgentConfig(
            system_prompt="You are a math specialist",
            review_config=MockReviewConfig(review_enabled=False),
        ),
    )


@pytest.fixture
def orchestrator_node():
    """Orchestrator agent node that delegates to sub-agents."""
    return MockEnhancedNodeData(
        uniq_id="orchestrator-001",
        name="Orchestrator",
        is_sub_agent=False,
        parent_agent_id=None,
        agent_config=MockAgentConfig(
            system_prompt="You coordinate tasks between specialists",
            is_orchestrator=True,
            delegated_agents=["subagent-001"],
        ),
    )


# ---------------------------------------------------------------------------
# Mock Service Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_graph_manager():
    """Mock GraphManager for subgraph testing."""
    manager = MagicMock()
    manager.execute_agent_async = AsyncMock(
        return_value=(
            AIMessage(content="The answer is 4"),  # response
            {"input_tokens": 100, "output_tokens": 50},  # token_counts
            [],  # tool_executions
        )
    )
    manager.subgraph_builder = MagicMock()
    manager._subagent_outputs = {}
    return manager


@pytest.fixture
def mock_subgraph():
    """Mock LangGraph StateGraph for testing."""
    subgraph = AsyncMock()
    subgraph.ainvoke = AsyncMock(
        return_value={
            "response": "The answer is 4",
            "tool_executions": [],
            "execution_order": 2,
            "paused": None,
            "paused_for_review": None,
            "review_data": None,
        }
    )
    return subgraph


@pytest.fixture
def mock_subgraph_paused():
    """Mock subgraph that returns paused state."""
    subgraph = AsyncMock()
    subgraph.ainvoke = AsyncMock(
        return_value={
            "response": "[AWAITING REVIEW] Math Expert output is pending human review.",
            "tool_executions": [],
            "execution_order": 2,
            "paused": True,
            "paused_for_review": True,
            "review_data": {
                "type": "agent_review",
                "node_id": "subagent-001",
                "node_name": "Math Expert",
                "agent_output": "The answer is 4",
            },
        }
    )
    return subgraph


@pytest.fixture
def mock_ws_notifier():
    """Mock WebSocket notifier."""
    notifier = AsyncMock()
    notifier.on_execution_paused = AsyncMock()
    return notifier


@pytest.fixture
def mock_db_session():
    """Mock database session for AgentReviewState persistence."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.fixture
def mock_review_state_record():
    """Mock AgentReviewState database record."""
    state = MagicMock()
    state.id = uuid4()
    state.graph_execution_id = "db-exec-456"
    state.agent_node_id = "subagent-001"
    state.checkpoint_id = None
    state.thread_id = "exec-123"
    state.status = "pending_review"
    state.current_iteration = 1
    state.max_iterations = 3
    state.review_mode = "human"
    state.review_prompt = "Review the math calculation"
    state.current_agent_output = "The answer is 4"
    state.review_history = []
    state.input_message = "Calculate 2+2"
    state.resume_response = None
    state.review_config = {"review_enabled": True, "review_mode": "human"}
    state.created_at = datetime.now(timezone.utc)
    state.updated_at = datetime.now(timezone.utc)
    return state


@pytest.fixture
def mock_review_state_with_response(mock_review_state_record):
    """Mock AgentReviewState with a pending resume response."""
    mock_review_state_record.resume_response = {"approved": True}
    return mock_review_state_record


# ---------------------------------------------------------------------------
# Delegation Request Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def delegation_request(sub_agent_node):
    """Mock DelegationRequest for testing."""

    class MockDelegationRequest:
        agent_node = sub_agent_node
        task_description = "Calculate 2+2"
        orchestrator_id = "orchestrator-001"
        context = {
            "execution_id": "exec-123",
            "db_execution_id": "db-exec-456",
            "execution_order": 1,
            "graph_name": "TestWorkflow",
            "tool_node_mapping": {},
            "parent_node_execution_id": "node-exec-789",
        }

    return MockDelegationRequest()


@pytest.fixture
def delegation_request_with_review(sub_agent_node_with_human_review):
    """Mock DelegationRequest for sub-agent with review enabled."""

    class MockDelegationRequest:
        agent_node = sub_agent_node_with_human_review
        task_description = "Calculate 2+2"
        orchestrator_id = "orchestrator-001"
        context = {
            "execution_id": "exec-123",
            "db_execution_id": "db-exec-456",
            "execution_order": 1,
            "graph_name": "TestWorkflow",
            "tool_node_mapping": {},
            "parent_node_execution_id": "node-exec-789",
        }

    return MockDelegationRequest()


# ---------------------------------------------------------------------------
# Review History Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def review_history_empty():
    """Empty review history."""
    return []


@pytest.fixture
def review_history_with_rejection():
    """Review history with one rejection."""
    return [
        {
            "iteration": 1,
            "agent_output": "The answer is 5",
            "feedback": "Incorrect calculation. 2+2=4, not 5.",
            "reviewer_type": "human",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]


@pytest.fixture
def review_history_max_iterations():
    """Review history at max iterations."""
    return [
        {
            "iteration": 1,
            "agent_output": "First attempt",
            "feedback": "Incorrect",
            "reviewer_type": "human",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "iteration": 2,
            "agent_output": "Second attempt",
            "feedback": "Still wrong",
            "reviewer_type": "human",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "iteration": 3,
            "agent_output": "Third attempt",
            "feedback": "Max iterations reached",
            "reviewer_type": "human",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ]


# ---------------------------------------------------------------------------
# Workflow JSON Fixture (Real workflow structure)
# ---------------------------------------------------------------------------


@pytest.fixture
def sub_review_workflow_json():
    """Real workflow JSON with orchestrator and sub-agent with review."""
    return {
        "name": "SubReviewTest",
        "description": "Test workflow for sub-agent review",
        "nodes": [
            {
                "uniq_id": "start-001",
                "name": "Start",
                "type": "START",
                "description": "",
                "nexts": ["orchestrator-001"],
                "inputs": [],
                "is_sub_agent": False,
            },
            {
                "uniq_id": "orchestrator-001",
                "name": "Orchestrator",
                "type": "AGENT",
                "description": "Coordinates with specialists",
                "nexts": ["end-001", "subagent-001"],
                "inputs": ["start-001"],
                "is_sub_agent": False,
                "agent_config": {
                    "agent_type": "conversational",
                    "system_prompt": "Delegate math queries to Math Expert",
                    "is_orchestrator": True,
                    "delegated_agents": ["subagent-001"],
                    "llm_config": {
                        "provider": "azure_openai",
                        "model_name": "gpt-4",
                    },
                },
            },
            {
                "uniq_id": "subagent-001",
                "name": "Math Expert",
                "type": "AGENT",
                "description": "Math specialist",
                "nexts": [],
                "inputs": ["orchestrator-001"],
                "is_sub_agent": True,
                "parent_agent_id": "orchestrator-001",
                "agent_config": {
                    "agent_type": "conversational",
                    "system_prompt": "You are a math specialist",
                    "is_orchestrator": False,
                    "review_config": {
                        "review_enabled": True,
                        "review_mode": "human",
                        "review_prompt": "Review the math calculation",
                        "max_iterations": 3,
                    },
                    "llm_config": {
                        "provider": "azure_openai",
                        "model_name": "gpt-4",
                    },
                },
            },
            {
                "uniq_id": "end-001",
                "name": "End",
                "type": "END",
                "description": "",
                "nexts": [],
                "inputs": ["orchestrator-001"],
                "is_sub_agent": False,
            },
        ],
        "connections": [
            {
                "source_id": "start-001",
                "target_id": "orchestrator-001",
                "connection_type": "workflow",
            },
            {
                "source_id": "orchestrator-001",
                "target_id": "end-001",
                "connection_type": "workflow",
            },
            {
                "source_id": "orchestrator-001",
                "target_id": "subagent-001",
                "connection_type": "delegation",
            },
        ],
    }
