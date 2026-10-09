"""Agent memory profile model."""

from sqlalchemy import JSON, Column, DateTime, Integer, String

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class AgentMemoryProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing agent-specific memory configuration and long-term memory.

    Manages memory configuration and long-term learning for individual agents,
    including personality traits, knowledge base, and interaction patterns.

    Attributes:
        id: Unique profile identifier (UUID).
        agent_id: Unique agent identifier.
        agent_name: Human-readable agent name.
        graph_id: Graph that this agent belongs to.
        memory_window_size: Number of conversation pairs to keep.
        summarization_threshold: When to trigger summarization.
        memory_retention_days: How long to keep memories.
        personality_traits: Extracted personality/behavior patterns (JSON).
        knowledge_base: Facts and information the agent has learned (JSON).
        interaction_patterns: Common interaction patterns (JSON).
        total_conversations: Total number of conversations.
        total_messages: Total number of messages.
        last_interaction: Timestamp of last interaction.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "agent_memory_profiles"

    # Agent identification
    agent_id = Column(String, nullable=False, unique=True, index=True)
    agent_name = Column(String, nullable=False)
    graph_id = Column(String, nullable=False)

    # Memory configuration
    memory_window_size = Column(Integer, default=10)
    summarization_threshold = Column(Integer, default=20)
    memory_retention_days = Column(Integer, default=30)

    # Long-term memory summary
    personality_traits = Column(JSON, nullable=True)
    knowledge_base = Column(JSON, nullable=True)
    interaction_patterns = Column(JSON, nullable=True)

    # Statistics
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    last_interaction = Column(DateTime(timezone=True), nullable=True)
