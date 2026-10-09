"""Service-layer schemas for memory operations.

This module defines Pydantic models for internal service operations,
providing type safety and validation for memory-related data structures.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MemoryCreate(BaseModel):
    """Schema for creating a new memory entry."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    memory_type: str = Field(
        ..., description="Type of memory (conversation, summary, fact, instruction)"
    )
    content: str = Field(..., description="Memory content")
    graph_execution_id: Optional[str] = Field(
        None, description="Associated graph execution ID"
    )
    node_execution_id: Optional[str] = Field(
        None, description="Associated node execution ID"
    )
    importance_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Memory importance (0-1)"
    )
    chat_session_id: Optional[str] = Field(
        None, description="Associated chat session ID for chat-scoped memory"
    )
    redacted: bool = Field(
        False,
        description=(
            "Transport-only marker set by the manager after PII redaction. "
            "Not persisted; asserted by the repository to guarantee no "
            "un-redacted content is written."
        ),
    )

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        """Validate memory type."""
        valid_types = {"conversation", "summary", "fact", "instruction", "chat_conversation"}
        if v not in valid_types:
            raise ValueError(f"Invalid memory type. Must be one of: {valid_types}")
        return v


class MemoryData(BaseModel):
    """Schema for memory data returned from service layer."""

    id: str
    agent_id: str
    agent_name: str
    memory_type: str
    content: str
    importance_score: float
    access_count: int
    is_active: bool
    created_at: datetime
    last_accessed: Optional[datetime] = None
    graph_execution_id: Optional[str] = None
    node_execution_id: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class AgentProfileData(BaseModel):
    """Schema for agent profile data."""

    id: str
    agent_id: str
    agent_name: str
    graph_id: str
    memory_window_size: int
    summarization_threshold: int
    memory_retention_days: int
    total_conversations: int
    total_messages: int
    last_interaction: Optional[datetime] = None
    personality_traits: Optional[dict] = None
    knowledge_base: Optional[dict] = None
    interaction_patterns: Optional[dict] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ConversationTurn(BaseModel):
    """Schema for a conversation turn (user message + agent response)."""

    user_message: str
    agent_response: str


class ConversationHistoryEntry(BaseModel):
    """Schema for a conversation history entry."""

    timestamp: datetime
    type: str
    content: str
    role: str


class MemoryQuery(BaseModel):
    """Schema for querying memories."""

    agent_id: str
    memory_types: Optional[list[str]] = None
    limit: int = Field(10, gt=0, le=100)
    only_active: bool = True
    graph_execution_id: Optional[str] = None
    chat_session_id: Optional[str] = None

    @field_validator("memory_types")
    @classmethod
    def validate_memory_types(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate memory types."""
        if v is not None:
            valid_types = {"conversation", "summary", "fact", "instruction", "chat_conversation"}
            invalid = set(v) - valid_types
            if invalid:
                raise ValueError(f"Invalid memory types: {invalid}")
        return v


class MemoryStatistics(BaseModel):
    """Schema for memory statistics."""

    total_memories: int
    active_memories: int
    memory_by_type: dict[str, int]
    average_importance: float
    most_accessed: Optional[MemoryData] = None
