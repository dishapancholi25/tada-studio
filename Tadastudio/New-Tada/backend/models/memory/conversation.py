"""Conversation memory model for agents."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ConversationMemory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing conversation memory for agents.

    Tracks conversation history and memory for individual agents,
    supporting importance scoring and access tracking.

    Attributes:
        id: Unique memory identifier (UUID).
        graph_execution_id: Associated graph execution ID.
        node_execution_id: Associated node execution ID.
        agent_id: Agent identifier (node.uniq_id).
        agent_name: Human-readable agent name.
        memory_type: Type of memory (conversation, summary, fact, instruction).
        content: Memory content text.
        importance_score: Memory importance (0-1 scale).
        access_count: How often this memory has been accessed.
        last_accessed: Timestamp of last access.
        is_active: Whether memory is active (soft delete).
        expires_at: Optional expiration timestamp.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "conversation_memories"

    # Linking to execution context
    graph_execution_id = Column(
        String, ForeignKey("graph_executions.id"), nullable=True, index=True
    )
    node_execution_id = Column(
        String, ForeignKey("node_executions.id"), nullable=True, index=True
    )

    # Agent identification
    agent_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=False)

    # Memory content
    memory_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    # Metadata
    importance_score = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True), nullable=True)

    # Chat session link for chat-scoped memory
    chat_session_id = Column(
        String,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Memory management
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    graph_execution = relationship("GraphExecution", backref="memories")
    node_execution = relationship("NodeExecution", backref="memories")
