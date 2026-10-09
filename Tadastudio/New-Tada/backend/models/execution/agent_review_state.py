"""Agent review state tracking model.

This module contains the model for tracking agent review state across
checkpoint boundaries, supporting both human and LLM review modes.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class AgentReviewState(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for persisting agent review state across checkpoint boundaries.

    This model solves the LangGraph limitation where interrupt() returns stale
    values during resume operations. By persisting review state to the database,
    we ensure review context survives across checkpoint boundaries.

    Attributes:
        id: Unique review state identifier (UUID).
        graph_execution_id: Parent graph execution ID.
        node_execution_id: Associated node execution ID.
        agent_node_id: Node identifier within the graph (for lookup).
        checkpoint_id: LangGraph checkpoint ID (links to pause point).
        thread_id: LangGraph thread ID.
        status: Review status (pending_review, approved, rejected, max_iterations).
        current_iteration: Current review iteration number (1-indexed).
        max_iterations: Maximum allowed iterations before auto-action.
        review_mode: Review type - "human" or "llm".
        review_prompt: Guidance for reviewers or prompt for LLM reviewer.
        current_agent_output: The agent's output being reviewed.
        review_history: JSON array of previous review iterations.
        input_message: Original input for agent re-execution after rejection.
        resume_response: User's response on resume (approved/feedback).
        review_config: Full review configuration as JSON.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "agent_review_states"

    # Foreign keys to execution tables
    graph_execution_id = Column(
        String,
        ForeignKey("graph_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_execution_id = Column(
        String,
        ForeignKey("node_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Node and checkpoint identifiers for lookup
    agent_node_id = Column(String, nullable=False, index=True)
    agent_node_name = Column(
        String, nullable=True
    )  # Human-readable agent name for display
    checkpoint_id = Column(String, nullable=True, index=True)
    thread_id = Column(String, nullable=False, index=True)

    # Review status tracking
    status = Column(String, nullable=False, default="pending_review")
    current_iteration = Column(Integer, nullable=False, default=1)
    max_iterations = Column(Integer, nullable=False, default=3)
    review_mode = Column(String, nullable=False, default="human")
    review_prompt = Column(Text, nullable=True)

    # Agent output and review context
    current_agent_output = Column(Text, nullable=True)
    review_history = Column(JSON, nullable=True, default=list)
    input_message = Column(Text, nullable=True)
    resume_response = Column(JSON, nullable=True)
    review_config = Column(JSON, nullable=True)

    # Relationships
    graph_execution = relationship("GraphExecution")
    node_execution = relationship("NodeExecution")
