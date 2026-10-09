"""Execution feedback model for thumbs up/down ratings on workflow runs."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class ExecutionFeedback(Base, UUIDPrimaryKeyMixin):
    """Model for storing user feedback (thumbs up/down) on execution runs.

    Each feedback record links a user rating to a specific graph execution,
    enabling use of positively-rated runs as evaluation test cases.

    Attributes:
        id: Unique feedback identifier (UUID).
        graph_execution_id: The execution being rated.
        rating: Feedback type - "positive" (thumbs up) or "negative" (thumbs down).
        comment: Optional user note explaining the rating.
        user_id: User who gave the feedback.
        created_at: Record creation timestamp.
    """

    __tablename__ = "execution_feedback"

    graph_execution_id = Column(
        String,
        ForeignKey("graph_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_execution_id = Column(
        String,
        ForeignKey("node_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rating = Column(String, nullable=False)  # "positive" or "negative"
    comment = Column(Text, nullable=True)
    user_id = Column(String, nullable=False, index=True)
    graph_definition_id = Column(
        String,
        ForeignKey("graph_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    graph_execution = relationship("GraphExecution", foreign_keys=[graph_execution_id])
    node_execution = relationship("NodeExecution", foreign_keys=[node_execution_id])
    graph_definition = relationship(
        "GraphDefinition", foreign_keys=[graph_definition_id]
    )
