"""Chat session model for conversational workflow interaction."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Model for storing chat sessions.

    A chat session represents a conversation between a user and a published workflow.
    Messages are derived from GraphExecution records linked via chat_session_id.

    Attributes:
        id: Unique session identifier (UUID).
        title: Session title (auto-generated from first message, user-editable).
        workflow_id: Associated workflow ID.
        user_id: User who owns this session.
        workflow_name: Denormalized workflow name for display.
        last_message_at: Timestamp of the most recent message.
        message_count: Total number of messages in the session.
        is_deleted: Soft delete flag.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "chat_sessions"

    # Core
    title = Column(String, nullable=False)
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String, nullable=False, index=True)

    # Denormalized for display
    workflow_name = Column(String, nullable=False)

    # Metadata
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, default=0, nullable=False)

    # Relationships
    workflow = relationship("Workflow")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_chat_sessions_user_workflow", "user_id", "workflow_id"),
    )
