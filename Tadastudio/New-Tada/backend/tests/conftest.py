"""Pytest fixtures for AgenticStudio backend tests.

This module provides fixtures for:
- Test database connection (Postgres via GitHub Actions service container)
- Test user creation and authentication override
- FastAPI TestClient with dependency injection
- Cleanup utilities for test isolation
- Mock data classes for unit testing
- Mock LLM and tool fixtures
"""

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


# ---------------------------------------------------------------------------
# Test User Configuration
# ---------------------------------------------------------------------------


# Test user claims - used to override authentication
TEST_USER_CLAIMS: Dict[str, Any] = {
    "sub": "test-user-pytest",
    "email": "pytest@agenticstudio.test",
    "name": "Pytest Test User",
    "given_name": "Pytest",
    "family_name": "User",
    "auth_source": "test",
}


# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------


def get_test_database_url() -> str:
    """Get the test database URL from environment variables.

    For GitHub Actions, these are set by the Postgres service container.
    For local testing, you can set them manually or use defaults.
    """
    host = os.getenv("KEY_POSTGRES_HOST", "localhost")
    port = os.getenv("KEY_POSTGRES_PORT", "5432")
    user = os.getenv("KEY_POSTGRES_USER", "postgres")
    password = os.getenv("KEY_POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("KEY_POSTGRES_DBNAME", "langgraph_test")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine.

    This fixture is session-scoped to reuse the connection across all tests.
    Creates the test database if it doesn't exist (for CI/CD environments).
    """
    # Get connection parameters
    host = os.getenv("KEY_POSTGRES_HOST", "localhost")
    port = os.getenv("KEY_POSTGRES_PORT", "5432")
    user = os.getenv("KEY_POSTGRES_USER", "postgres")
    password = os.getenv("KEY_POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("KEY_POSTGRES_DBNAME", "langgraph_test")

    # First connect to postgres database to create test database if needed
    postgres_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/postgres"
    temp_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")

    with temp_engine.connect() as conn:
        # Check if database exists
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": dbname},
        )
        exists = result.fetchone() is not None

        if not exists:
            # Create the test database
            conn.execute(text(f"CREATE DATABASE {dbname}"))

    temp_engine.dispose()

    # Now connect to the test database
    database_url = get_test_database_url()
    engine = create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    # Create pgvector extension if it doesn't exist
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    yield engine

    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_db_engine):
    """Create a session factory for the test database."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=test_db_engine,
    )


@pytest.fixture(scope="function")
def test_db_session(test_session_factory) -> Generator[Session, None, None]:
    """Provide a database session for each test.

    Each test gets its own session that is rolled back after the test.
    """
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def initialize_test_db(test_db_engine):
    """Initialize the test database with all tables.

    This runs once per test session and creates all necessary tables.
    """
    # Import all models to register them with SQLAlchemy
    from backend.services.database import Base

    # Import models to ensure they're registered
    from backend.models.auth.user import User  # noqa: F401
    from backend.models.auth.user_api_token import UserAPIToken  # noqa: F401
    from backend.models.workflows.membership import WorkflowMembership  # noqa: F401
    from backend.models import GraphDefinition  # noqa: F401
    from backend.models.execution.subagent_iteration_state import SubagentIterationState  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=test_db_engine)

    # Run migrations to add additional columns and indexes
    # Override get_engine to use test database
    from backend.services import database as db_module
    from sqlalchemy import text

    original_get_engine = db_module.get_engine

    def mock_get_engine():
        return test_db_engine

    db_module.get_engine = mock_get_engine

    try:
        from backend.services.database.migrations import run_migrations

        run_migrations()

        # Ensure the groups index is created (run migration again if needed)
        with test_db_engine.connect() as conn:
            # Check if idx_users_groups exists
            result = conn.execute(
                text(
                    "SELECT 1 FROM pg_indexes WHERE tablename='users' AND indexname='idx_users_groups'"
                )
            )
            if not result.fetchone():
                # Create the index if it doesn't exist
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_users_groups ON users USING GIN (groups)"
                    )
                )
                conn.commit()
    finally:
        db_module.get_engine = original_get_engine

    yield

    # Optionally drop tables after all tests (commented out to allow inspection)
    # Base.metadata.drop_all(bind=test_db_engine)


@pytest.fixture(scope="function")
def test_user(test_db_session, initialize_test_db) -> Dict[str, Any]:
    """Create a test user in the database.

    Returns the user claims dictionary that will be used for authentication.
    """
    from backend.models.auth.user import User

    # Check if user already exists
    existing_user = (
        test_db_session.query(User).filter(User.id == TEST_USER_CLAIMS["sub"]).first()
    )

    if not existing_user:
        user = User(
            id=TEST_USER_CLAIMS["sub"],
            email=TEST_USER_CLAIMS["email"],
            name=TEST_USER_CLAIMS["name"],
            given_name=TEST_USER_CLAIMS.get("given_name"),
            family_name=TEST_USER_CLAIMS.get("family_name"),
        )
        test_db_session.add(user)
        test_db_session.commit()

    return TEST_USER_CLAIMS


@pytest.fixture(scope="function")
def test_client(
    test_db_engine, test_session_factory, test_user, initialize_test_db
) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with authentication override.

    This client:
    - Overrides authentication to use the test user
    - Overrides database session to use the test database
    - Initializes application dependencies
    """
    # Override database engine and session factory before importing app
    from backend.services import database as db_module

    # Store original values
    original_get_engine = db_module.get_engine

    def mock_get_engine():
        return test_db_engine

    # Apply database overrides
    db_module.get_engine = mock_get_engine
    db_module.reset_session_factory()

    # Now import app (after database is configured)
    from backend.app import app
    from backend.api.auth.dependencies import get_current_user

    # Override authentication
    async def override_get_current_user() -> Dict[str, Any]:
        return TEST_USER_CLAIMS

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create test client
    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
    db_module.get_engine = original_get_engine
    db_module.reset_session_factory()


@pytest.fixture(scope="function")
def unique_workflow_name() -> str:
    """Generate a unique workflow name for test isolation."""
    return f"test-workflow-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def cleanup_workflows(test_client):
    """Track and clean up workflows created during tests.

    Usage:
        def test_example(test_client, cleanup_workflows):
            # Create workflow
            response = test_client.post("/api/graph/create", json={"name": "my-test"})
            cleanup_workflows.append("my-test")  # Will be deleted after test
    """
    workflows_to_delete = []

    yield workflows_to_delete

    # Clean up after test
    for workflow_name in workflows_to_delete:
        try:
            test_client.delete(f"/api/graph/{workflow_name}")
        except Exception:
            pass  # Ignore cleanup errors


# ---------------------------------------------------------------------------
# Mock Data Classes (mimicking real models without importing them)
# ---------------------------------------------------------------------------


@dataclass
class MockAgentConfig:
    """Mock AgentConfig for testing."""

    system_prompt: str = "You are a helpful assistant"
    tools: List[str] = field(default_factory=list)
    structured_outputs: List[Dict[str, Any]] = field(default_factory=list)
    memory_enabled: bool = False
    is_orchestrator: bool = False
    delegated_agents: List[str] = field(default_factory=list)
    max_iterations: int = 50
    llm_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "provider": "azure_openai",
            "model_name": "gpt-4",
        }
    )


@dataclass
class MockEnhancedNodeData:
    """Mock EnhancedNodeData for testing."""

    uniq_id: str = "test-node-123"
    name: str = "Test Agent"
    type: str = "AGENT"
    agent_config: Optional[MockAgentConfig] = None

    def __post_init__(self):
        if self.agent_config is None:
            self.agent_config = MockAgentConfig()


# ---------------------------------------------------------------------------
# Sample Structured Output Configurations
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_structured_output_config():
    """Sample structured output configuration for testing."""
    return {
        "model_name": "MathResult",
        "fields": [
            {"name": "answer", "type": "str", "description": "The computed answer"},
            {
                "name": "explanation",
                "type": "str",
                "description": "Step-by-step explanation",
            },
        ],
    }


@pytest.fixture
def sample_structured_outputs(sample_structured_output_config):
    """List of structured outputs (as stored in agent_config)."""
    return [sample_structured_output_config]


# ---------------------------------------------------------------------------
# Agent Config Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent_config_no_tools_no_structured():
    """Agent config with neither tools nor structured outputs."""
    return MockAgentConfig(
        system_prompt="Basic assistant",
        tools=[],
        structured_outputs=[],
    )


@pytest.fixture
def agent_config_with_tools_no_structured():
    """Agent config with tools but no structured outputs."""
    return MockAgentConfig(
        system_prompt="Tool-using assistant",
        tools=["calculator", "web_search"],
        structured_outputs=[],
    )


@pytest.fixture
def agent_config_no_tools_with_structured(sample_structured_outputs):
    """Agent config with structured outputs but no tools."""
    return MockAgentConfig(
        system_prompt="Structured output assistant",
        tools=[],
        structured_outputs=sample_structured_outputs,
    )


@pytest.fixture
def agent_config_with_tools_and_structured(sample_structured_outputs):
    """Agent config with BOTH tools AND structured outputs."""
    return MockAgentConfig(
        system_prompt="Full-featured assistant",
        tools=["calculator"],
        structured_outputs=sample_structured_outputs,
        is_orchestrator=True,
    )


# ---------------------------------------------------------------------------
# Node Data Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent_node_basic(agent_config_no_tools_no_structured):
    """Basic agent node with no tools or structured outputs."""
    return MockEnhancedNodeData(
        uniq_id="basic-agent-001",
        name="Basic Agent",
        agent_config=agent_config_no_tools_no_structured,
    )


@pytest.fixture
def agent_node_with_tools(agent_config_with_tools_no_structured):
    """Agent node with tools."""
    return MockEnhancedNodeData(
        uniq_id="tool-agent-001",
        name="Tool Agent",
        agent_config=agent_config_with_tools_no_structured,
    )


@pytest.fixture
def agent_node_with_structured(agent_config_no_tools_with_structured):
    """Agent node with structured outputs."""
    return MockEnhancedNodeData(
        uniq_id="structured-agent-001",
        name="Structured Agent",
        agent_config=agent_config_no_tools_with_structured,
    )


@pytest.fixture
def agent_node_with_both(agent_config_with_tools_and_structured):
    """Agent node with BOTH tools AND structured outputs."""
    return MockEnhancedNodeData(
        uniq_id="full-agent-001",
        name="Full Agent",
        agent_config=agent_config_with_tools_and_structured,
    )


# ---------------------------------------------------------------------------
# Mock LLM Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm():
    """Mock LLM instance."""
    llm = AsyncMock()
    llm.model_name = "gpt-4"
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="Mock response"))
    llm.with_structured_output = MagicMock(return_value=llm)
    llm.bind_tools = MagicMock(return_value=llm)
    return llm


@pytest.fixture
def mock_llm_factory(mock_llm):
    """Mock LLM factory."""
    mock_instance = MagicMock()
    mock_instance.llm = mock_llm
    mock_instance.supports_tool_calling = True

    factory = MagicMock()
    factory.create_llm_instance = MagicMock(return_value=mock_instance)
    return factory


@pytest.fixture
def mock_model_service():
    """Mock model deployment service."""
    service = MagicMock()
    service.enrich_llm_config = MagicMock(side_effect=lambda config: config)
    return service


# ---------------------------------------------------------------------------
# Mock Tool Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tools():
    """List of mock tools."""
    tool1 = MagicMock()
    tool1.name = "calculator"
    tool1.description = "Performs calculations"

    tool2 = MagicMock()
    tool2.name = "delegate_to_math_expert"
    tool2.description = "Delegates to math expert sub-agent"

    return [tool1, tool2]


@pytest.fixture
def mock_tool_executor():
    """Mock AsyncToolExecutor."""
    executor = AsyncMock()
    executor.execute_with_tools = AsyncMock(
        return_value=AIMessage(content="Tool execution result")
    )
    return executor


# ---------------------------------------------------------------------------
# Execution Config Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def execution_config_default():
    """Default execution config with format_output=True."""

    # Return a simple object that mimics ExecutionConfig
    class Config:
        format_output = True
        db_execution_id = "test-exec-123"
        tool_execution_tracker = []
        return_token_counts = False
        enable_memory = False
        execution_id = "exec-001"
        graph_name = "TestGraph"
        node_id = "node-001"
        user_id = "user-001"
        tool_node_mapping = None
        review_iteration = None
        node_execution_id = None
        is_subagent = False
        invocation_index = None
        parent_subagent_id = None
        workflow_id = "workflow-001"
        execution_order = None
        db_node_id = None

    return Config()


@pytest.fixture
def execution_config_no_format():
    """Execution config with format_output=False."""

    class Config:
        format_output = False
        db_execution_id = "test-exec-123"
        tool_execution_tracker = []
        return_token_counts = False
        enable_memory = False
        execution_id = "exec-001"
        graph_name = "TestGraph"
        node_id = "node-001"
        user_id = "user-001"
        tool_node_mapping = None
        review_iteration = None
        node_execution_id = None
        is_subagent = False
        invocation_index = None
        parent_subagent_id = None
        workflow_id = "workflow-001"
        execution_order = None
        db_node_id = None

    return Config()
