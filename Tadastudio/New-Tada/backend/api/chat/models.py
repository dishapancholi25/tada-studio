"""Pydantic models for chat API requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateChatSessionRequest(BaseModel):
    """Request to create a new chat session."""

    workflow_id: str = Field(..., description="ID of the workflow to chat with")


class RenameChatSessionRequest(BaseModel):
    """Request to rename a chat session."""

    title: str = Field(..., min_length=1, max_length=200, description="New title")


class SendMessageRequest(BaseModel):
    """Request to send a message in a chat session."""

    message: str = Field(..., min_length=1, description="Message text")


class ChatSessionResponse(BaseModel):
    """Response representing a chat session."""

    id: str
    title: str
    workflow_id: str
    workflow_name: str
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """Response representing a chat message."""

    role: str
    content: str
    execution_id: Optional[str] = None
    created_at: Optional[datetime] = None


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    success: bool = True
    execution_id: str
    chat_session_id: str
    status: str = "running"
    message: str = "Execution started"


class ChatWorkflowResponse(BaseModel):
    """Response representing a published workflow available for chat."""

    id: str
    workflow_id: str
    graph_name: str
    description: Optional[str] = None
