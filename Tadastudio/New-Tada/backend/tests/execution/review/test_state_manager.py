"""Tests for AgentReviewStateManager.

These tests verify the persistence and retrieval of agent review state,
which is used to work around LangGraph's checkpoint limitations during
review interrupt/resume flows.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestAgentReviewStateManagerCreate:
    """Tests for creating and updating review state."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        return session

    @pytest.fixture
    def mock_review_state(self):
        """Create a mock AgentReviewState instance."""
        state = MagicMock()
        state.id = uuid4()
        state.graph_execution_id = "exec-123"
        state.agent_node_id = "node-456"
        state.thread_id = "thread-789"
        state.status = "pending_review"
        state.current_iteration = 1
        state.max_iterations = 3
        state.review_mode = "human"
        state.review_prompt = "Review this output"
        state.current_agent_output = "Agent output text"
        state.review_history = []
        state.checkpoint_id = None
        state.resume_response = None
        state.created_at = datetime.now(timezone.utc)
        state.updated_at = datetime.now(timezone.utc)
        return state

    def test_create_review_state_creates_new_record(
        self, mock_db_session, mock_review_state
    ):
        """Creating review state should persist all fields to database."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

            # Configure mock to return None for existing check (no existing record)
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            # Mock the add and commit to capture the created state
            mock_db_session.refresh = MagicMock(
                side_effect=lambda x: setattr(x, "id", uuid4())
            )

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            AgentReviewStateManager.create_or_update_review_state(
                graph_execution_id="exec-123",
                agent_node_id="node-456",
                thread_id="thread-789",
                agent_output="Test agent output",
                review_mode="human",
                review_prompt="Please review this",
                max_iterations=3,
                current_iteration=1,
            )

            # Verify add was called
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()

    def test_create_review_state_updates_existing_record(
        self, mock_db_session, mock_review_state
    ):
        """Updating existing review state should modify the record."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

            # Return existing record
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            AgentReviewStateManager.create_or_update_review_state(
                graph_execution_id="exec-123",
                agent_node_id="node-456",
                thread_id="thread-789",
                agent_output="Updated agent output",
                review_mode="human",
                current_iteration=2,
            )

            # Verify existing record was updated
            assert mock_review_state.current_agent_output == "Updated agent output"
            assert mock_review_state.current_iteration == 2
            mock_db_session.commit.assert_called_once()
            # Verify add was NOT called (update, not create)
            mock_db_session.add.assert_not_called()


class TestAgentReviewStateManagerRetrieve:
    """Tests for retrieving review state."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_review_state(self):
        """Create a mock AgentReviewState instance."""
        state = MagicMock()
        state.id = uuid4()
        state.graph_execution_id = "exec-123"
        state.node_execution_id = None
        state.agent_node_id = "node-456"
        state.checkpoint_id = "ck-001"
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

    def test_get_pending_review_returns_state(self, mock_db_session, mock_review_state):
        """Should retrieve pending review by execution_id and node_id."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.get_pending_review(
                graph_execution_id="exec-123",
                agent_node_id="node-456",
            )

            assert result is not None
            assert result["graph_execution_id"] == "exec-123"
            assert result["agent_node_id"] == "node-456"
            assert result["status"] == "pending_review"

    def test_get_pending_review_returns_none_when_not_found(self, mock_db_session):
        """Should return None when no pending review exists."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.get_pending_review(
                graph_execution_id="exec-123",
                agent_node_id="node-456",
            )

            assert result is None

    def test_get_by_checkpoint_id_returns_state(
        self, mock_db_session, mock_review_state
    ):
        """Should find review state by its linked checkpoint_id."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.get_by_checkpoint_id("ck-001")

            assert result is not None
            assert result["checkpoint_id"] == "ck-001"


class TestAgentReviewStateManagerUpdate:
    """Tests for updating review state fields."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_review_state(self):
        """Create a mock AgentReviewState instance."""
        state = MagicMock()
        state.id = uuid4()
        state.checkpoint_id = None
        state.resume_response = None
        state.review_history = []
        state.current_iteration = 1
        state.status = "pending_review"
        state.updated_at = None
        return state

    def test_update_checkpoint_id_sets_value(self, mock_db_session, mock_review_state):
        """Updating checkpoint_id should set the value and commit."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.update_checkpoint_id(
                review_state_id=str(mock_review_state.id),
                checkpoint_id="ck-new-001",
            )

            assert result is True
            assert mock_review_state.checkpoint_id == "ck-new-001"
            mock_db_session.commit.assert_called_once()

    def test_update_checkpoint_id_returns_false_when_not_found(self, mock_db_session):
        """Should return False when review state not found."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.update_checkpoint_id(
                review_state_id="nonexistent-id",
                checkpoint_id="ck-001",
            )

            assert result is False

    def test_set_resume_response_stores_response(
        self, mock_db_session, mock_review_state
    ):
        """Setting resume response should update the DB record."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            resume_data = {"approved": True}
            result = AgentReviewStateManager.set_resume_response(
                review_state_id=str(mock_review_state.id),
                resume_response=resume_data,
            )

            assert result is True
            assert mock_review_state.resume_response == resume_data
            mock_db_session.commit.assert_called_once()

    def test_add_feedback_to_history_appends_entry(
        self, mock_db_session, mock_review_state
    ):
        """Adding feedback should append to existing history array."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state
            mock_review_state.review_history = []  # Start with empty history

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.add_feedback_to_history(
                review_state_id=str(mock_review_state.id),
                feedback="Needs more detail",
                agent_output="Original output",
                reviewer_type="human",
            )

            assert result is True
            # Verify history was updated
            assert len(mock_review_state.review_history) == 1
            assert (
                mock_review_state.review_history[0]["feedback"] == "Needs more detail"
            )
            assert mock_review_state.review_history[0]["reviewer_type"] == "human"
            # Verify iteration was incremented
            assert mock_review_state.current_iteration == 2
            mock_db_session.commit.assert_called_once()

    def test_complete_review_sets_status(self, mock_db_session, mock_review_state):
        """Completing review should set status to approved/rejected."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.complete_review(
                review_state_id=str(mock_review_state.id),
                status="approved",
            )

            assert result is True
            assert mock_review_state.status == "approved"
            mock_db_session.commit.assert_called_once()

    def test_complete_review_with_max_iterations_status(
        self, mock_db_session, mock_review_state
    ):
        """Should support max_iterations as a completion status."""
        with patch(
            "backend.services.execution.review.state_manager.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review_state

            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            result = AgentReviewStateManager.complete_review(
                review_state_id=str(mock_review_state.id),
                status="max_iterations",
            )

            assert result is True
            assert mock_review_state.status == "max_iterations"
