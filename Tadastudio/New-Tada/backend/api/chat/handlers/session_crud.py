"""Chat session CRUD handlers."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models import ChatSession, Workflow
from backend.models.workflows.publishing import PublishedWorkflow
from backend.services.database import get_db

from ..exceptions import (
    ChatAccessDeniedError,
    ChatSessionNotFoundError,
    WorkflowNotPublishedError,
)


logger = logging.getLogger("chat.session_crud")


def handle_list_sessions(
    user_id: str,
    workflow_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List chat sessions for a user.

    Args:
        user_id: User identifier
        workflow_id: Optional workflow filter
        limit: Maximum results
        offset: Pagination offset

    Returns:
        List of session dicts
    """
    with get_db() as db:
        query = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_deleted == False,  # noqa: E712
        )

        if workflow_id:
            query = query.filter(ChatSession.workflow_id == workflow_id)

        sessions = (
            query.order_by(ChatSession.last_message_at.desc().nullsfirst(), ChatSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [_session_to_dict(s) for s in sessions]


def handle_create_session(user_id: str, workflow_id: str) -> Dict[str, Any]:
    """Create a new chat session.

    Args:
        user_id: User identifier
        workflow_id: Workflow to chat with

    Returns:
        Created session dict

    Raises:
        WorkflowNotPublishedError: If workflow is not published
    """
    with get_db() as db:
        # Verify workflow is published
        published = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )

        if not published:
            raise WorkflowNotPublishedError(workflow_id)

        # Get workflow name
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        workflow_name = workflow.name if workflow else published.graph_name

        session = ChatSession(
            title="New Chat",
            workflow_id=workflow_id,
            user_id=user_id,
            workflow_name=workflow_name,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(f"Created chat session {session.id} for workflow {workflow_id}")
        return _session_to_dict(session)


def handle_get_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """Get a chat session by ID.

    Args:
        session_id: Session identifier
        user_id: User identifier for ownership check

    Returns:
        Session dict

    Raises:
        ChatSessionNotFoundError: If session not found
        ChatAccessDeniedError: If user doesn't own the session
    """
    session = _load_session(session_id, user_id)
    return _session_to_dict(session)


def handle_rename_session(session_id: str, user_id: str, title: str) -> Dict[str, Any]:
    """Rename a chat session.

    Args:
        session_id: Session identifier
        user_id: User identifier for ownership check
        title: New title

    Returns:
        Updated session dict
    """
    with get_db() as db:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.is_deleted == False,  # noqa: E712
            )
            .first()
        )

        if not session:
            raise ChatSessionNotFoundError(session_id)
        if session.user_id != user_id:
            raise ChatAccessDeniedError()

        session.title = title
        db.commit()
        db.refresh(session)

        return _session_to_dict(session)


def handle_delete_session(session_id: str, user_id: str) -> None:
    """Soft delete a chat session.

    Args:
        session_id: Session identifier
        user_id: User identifier for ownership check
    """
    with get_db() as db:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.is_deleted == False,  # noqa: E712
            )
            .first()
        )

        if not session:
            raise ChatSessionNotFoundError(session_id)
        if session.user_id != user_id:
            raise ChatAccessDeniedError()

        session.is_deleted = True
        db.commit()

        logger.info(f"Soft deleted chat session {session_id}")


def handle_list_chat_workflows(user_id: str) -> List[Dict[str, Any]]:
    """List published workflows available for chat.

    Args:
        user_id: User identifier

    Returns:
        List of published workflow dicts
    """
    with get_db() as db:
        published_workflows = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.is_published == True,  # noqa: E712
                PublishedWorkflow.user_id == user_id,
            )
            .all()
        )

        return [
            {
                "id": str(pw.id),
                "workflow_id": pw.workflow_id,
                "graph_name": pw.graph_name,
                "description": pw.description,
            }
            for pw in published_workflows
        ]


def update_session_after_message(session_id: str, message: str) -> None:
    """Update session metadata after a message is sent.

    Auto-titles from first message, updates last_message_at and count.

    Args:
        session_id: Session identifier
        message: The user's message text
    """
    with get_db() as db:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return

        # Auto-title from first message
        if session.message_count == 0:
            session.title = message[:60].strip() or "New Chat"

        session.last_message_at = datetime.now(timezone.utc)
        session.message_count += 1
        db.commit()


def _load_session(session_id: str, user_id: str) -> ChatSession:
    """Load and validate a chat session."""
    with get_db() as db:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.is_deleted == False,  # noqa: E712
            )
            .first()
        )

        if not session:
            raise ChatSessionNotFoundError(session_id)
        if session.user_id != user_id:
            raise ChatAccessDeniedError()

        # Detach from session for use outside context manager
        db.expunge(session)
        return session


def _session_to_dict(session: ChatSession) -> Dict[str, Any]:
    """Convert a ChatSession to a response dict."""
    return {
        "id": str(session.id),
        "title": session.title,
        "workflow_id": session.workflow_id,
        "workflow_name": session.workflow_name,
        "message_count": session.message_count,
        "last_message_at": session.last_message_at,
        "created_at": session.created_at,
    }
