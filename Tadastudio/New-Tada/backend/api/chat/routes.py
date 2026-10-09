"""Chat API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from ..auth.dependencies import require_active_user
from .dependencies import get_user_identifier
from .handlers import session_crud, message
from .models import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatWorkflowResponse,
    CreateChatSessionRequest,
    RenameChatSessionRequest,
    SendMessageRequest,
    SendMessageResponse,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    dependencies=[Depends(require_active_user)],
)


@router.get("/workflows", response_model=List[ChatWorkflowResponse])
async def list_chat_workflows(
    user_id: str = Depends(get_user_identifier),
):
    """List published workflows available for chat."""
    return session_crud.handle_list_chat_workflows(user_id)


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    user_id: str = Depends(get_user_identifier),
    workflow_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List chat sessions for the current user."""
    return session_crud.handle_list_sessions(user_id, workflow_id, limit, offset)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    request: CreateChatSessionRequest,
    user_id: str = Depends(get_user_identifier),
):
    """Create a new chat session."""
    return session_crud.handle_create_session(user_id, request.workflow_id)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_user_identifier),
):
    """Get a chat session by ID."""
    return session_crud.handle_get_session(session_id, user_id)


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def rename_session(
    session_id: str,
    request: RenameChatSessionRequest,
    user_id: str = Depends(get_user_identifier),
):
    """Rename a chat session."""
    return session_crud.handle_rename_session(session_id, user_id, request.title)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_user_identifier),
):
    """Delete (soft) a chat session."""
    session_crud.handle_delete_session(session_id, user_id)


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: str,
    user_id: str = Depends(get_user_identifier),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get message history for a chat session."""
    return await message.handle_get_messages(session_id, user_id, limit, offset)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_user_identifier),
):
    """Send a message to a chat session, triggering workflow execution."""
    return await message.handle_send_message(session_id, user_id, request.message)


@router.post("/sessions/{session_id}/messages-with-file", response_model=SendMessageResponse)
async def send_message_with_file(
    session_id: str,
    user_id: str = Depends(get_user_identifier),
    msg: str = Form(default=""),
    file: Optional[UploadFile] = File(default=None),
):
    """Send a message with an optional file attachment to a chat session."""
    return await message.handle_send_message_with_file(session_id, user_id, msg, file)
