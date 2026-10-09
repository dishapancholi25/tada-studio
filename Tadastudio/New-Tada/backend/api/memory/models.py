"""Pydantic models for memory API endpoints.

This module defines request and response models for the memory management API,
providing validation and documentation for all memory-related endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    """Request model for creating a new memory entry."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    memory_type: str = Field(
        ..., description="Type of memory (conversation, summary, fact, instruction)"
    )
    content: str = Field(..., description="Memory content")
    importance_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Memory importance score (0-1)"
    )
    graph_execution_id: Optional[str] = Field(
        None, description="Associated graph execution ID"
    )
    node_execution_id: Optional[str] = Field(
        None, description="Associated node execution ID"
    )


class MemoryResponse(BaseModel):
    """Response model for memory entries."""

    id: str = Field(..., description="Unique memory identifier")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Agent name")
    memory_type: str = Field(..., description="Memory type")
    content: str = Field(..., description="Memory content")
    importance_score: float = Field(..., description="Importance score (0-1)")
    access_count: int = Field(..., description="Number of times accessed")
    is_active: bool = Field(..., description="Whether memory is active")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    last_accessed: Optional[str] = Field(
        None, description="Last access timestamp (ISO format)"
    )


class AgentProfileResponse(BaseModel):
    """Response model for agent memory profiles."""

    id: str = Field(..., description="Unique profile identifier")
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Agent name")
    graph_id: str = Field(..., description="Graph identifier")
    memory_window_size: int = Field(..., description="Memory window size")
    summarization_threshold: int = Field(..., description="Summarization threshold")
    memory_retention_days: int = Field(..., description="Retention period in days")
    total_conversations: int = Field(..., description="Total conversation count")
    total_messages: int = Field(..., description="Total message count")
    last_interaction: Optional[str] = Field(
        None, description="Last interaction timestamp (ISO format)"
    )


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    agent_id: str = Field(..., description="Agent identifier")
    history: list[dict] = Field(..., description="List of conversation entries")


class MemoryPruneResponse(BaseModel):
    """Response model for memory pruning operations."""

    message: str = Field(..., description="Success message")
    count: int = Field(..., description="Number of memories affected")


class MemoryClearResponse(BaseModel):
    """Response model for memory clearing operations."""

    message: str = Field(..., description="Success message")
    count: int = Field(..., description="Number of memories cleared")
