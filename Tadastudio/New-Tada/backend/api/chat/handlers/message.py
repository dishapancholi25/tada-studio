"""Chat message handlers — send messages and get history."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from backend.api.graph.services.execution_manager import execution_manager
from backend.models.workflows.publishing import PublishedWorkflow
from backend.services.chat.memory import ChatMemoryService
from backend.services.database import get_db
from backend.services.dependency_injection import get_execution_engine, get_graph_manager

from ..exceptions import (
    ChatAccessDeniedError,
    ChatExecutionError,
    ChatSessionNotFoundError,
    WorkflowNotPublishedError,
)
from .session_crud import update_session_after_message


logger = logging.getLogger("chat.message")

EXECUTION_ID_PREFIX = "exec_"
EXECUTION_ID_DATE_FORMAT = "%Y%m%d_%H%M%S"


async def handle_get_messages(
    session_id: str,
    user_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get message history for a chat session.

    Args:
        session_id: Chat session identifier
        user_id: User identifier for ownership check
        limit: Maximum messages to return
        offset: Pagination offset

    Returns:
        List of message dicts with role, content, execution_id, created_at
    """
    _verify_session_access(session_id, user_id)

    chat_memory = ChatMemoryService()
    messages = chat_memory.load_chat_history_sync(
        chat_session_id=session_id,
        limit=limit,
    )

    # Apply offset
    if offset > 0:
        messages = messages[offset:]

    return messages


async def handle_send_message(
    session_id: str,
    user_id: str,
    message: str,
) -> Dict[str, Any]:
    """Send a message to a chat session, triggering workflow execution.

    Args:
        session_id: Chat session identifier
        user_id: User identifier
        message: User's message text

    Returns:
        Dict with execution_id, chat_session_id, status

    Raises:
        ChatSessionNotFoundError: If session not found
        ChatAccessDeniedError: If user doesn't own the session
        WorkflowNotPublishedError: If workflow is not published
        ChatExecutionError: If execution fails to start
    """
    from backend.models import ChatSession

    return await _execute_chat_session(session_id, user_id, {"message": message}, message)


async def handle_send_message_with_file(
    session_id: str,
    user_id: str,
    message: str,
    file: Optional[UploadFile] = None,
) -> Dict[str, Any]:
    """Send a message with an optional file attachment, triggering workflow execution.

    The file is processed and its content is passed as file_info in initial_input
    so FILE_READ nodes can consume it directly without needing filesystem access.
    """
    from backend.api.graph.services.file_processor import FileProcessorService

    initial_input: Dict[str, Any] = {}

    # Process file if provided
    if file and file.filename:
        contents = await file.read()
        file_info = await FileProcessorService.process_upload(file.filename, contents)

        # Extract readable text using the same LangChain-based pipeline as document collection ingestion
        # (supports PDF via PyPDFLoader→PyMuPDF→PDFMiner fallbacks, DOCX, Excel, TXT, CSV, Markdown)
        try:
            from backend.services.document_storage.service import DocumentStorageService
            chunks, _ = DocumentStorageService().process_document(file_info["path"])
            if chunks:
                file_info["extracted_text"] = "\n\n".join(c.page_content for c in chunks)
                logger.info(
                    f"Chat file text extracted: {file.filename} "
                    f"({len(file_info['extracted_text'])} chars)"
                )
            else:
                logger.warning(
                    f"Chat file extraction returned no content for {file.filename}"
                )
        except Exception as e:
            logger.warning(f"Could not extract text from uploaded file {file.filename}: {e}")

        initial_input["file_info"] = file_info
        logger.info(f"Chat file upload: {file.filename} ({len(contents)} bytes) for session {session_id}")

    # Compose the message to include file name and extracted content when available
    composed_message = message or ""
    if file and file.filename and initial_input.get("file_info", {}).get("extracted_text"):
        file_info = initial_input["file_info"]
        parts = []
        if composed_message:
            parts.append(f"Question: {composed_message}")
        parts.append(f"File Name: {file_info['filename']}")
        parts.append(f"File Content:\n{file_info['extracted_text']}")
        composed_message = "\n\n".join(parts)
        logger.info(f"Composed message with file content for session {session_id}")

    if composed_message:
        initial_input["message"] = composed_message

    # Delegate to core send logic with composed initial_input
    return await _execute_chat_session(session_id, user_id, initial_input, message or file.filename or "")


async def _execute_chat_session(
    session_id: str,
    user_id: str,
    initial_input: Dict[str, Any],
    display_message: str,
) -> Dict[str, Any]:
    """Core execution logic shared by text and file message handlers."""
    from backend.models import ChatSession

    with get_db() as db:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.is_deleted == False)  # noqa: E712
            .first()
        )
        if not session:
            raise ChatSessionNotFoundError(session_id)
        if session.user_id != user_id:
            raise ChatAccessDeniedError()
        workflow_id = session.workflow_id
        workflow_name = session.workflow_name

    with get_db() as db:
        published = (
            db.query(PublishedWorkflow)
            .filter(PublishedWorkflow.workflow_id == workflow_id, PublishedWorkflow.is_published == True)  # noqa: E712
            .first()
        )
        if not published:
            raise WorkflowNotPublishedError(workflow_id)
        published_user_id = published.user_id

    try:
        graph = get_graph_manager().load_graph_by_workflow_id(
            workflow_id=workflow_id, username=published_user_id
        )
        if not graph:
            raise WorkflowNotPublishedError(workflow_id)
    except Exception as e:
        logger.error(f"Failed to load graph for workflow {workflow_id}: {e}")
        raise ChatExecutionError(f"Failed to load workflow: {e}")

    timestamp = datetime.now().strftime(EXECUTION_ID_DATE_FORMAT)
    safe_name = workflow_name.replace(" ", "_").replace("-", "_")[:30]
    execution_id = f"{EXECUTION_ID_PREFIX}{timestamp}_{safe_name}"

    get_execution_engine().active_executions[execution_id] = {
        "execution_id": execution_id,
        "status": "pending",
        "start_time": str(datetime.now()),
        "graph_name": workflow_name,
        "current_node": None,
        "node_execution_map": {},
        "db_execution_id": None,
        "source": "chat",
    }

    try:
        execution_manager.submit_execution(
            graph=graph,
            initial_input=initial_input,
            execution_id=execution_id,
            user_id=user_id,
            workflow_id=workflow_id,
            trigger_type="chat",
            chat_session_id=session_id,
        )
    except Exception as e:
        logger.error(f"Failed to submit chat execution: {e}")
        get_execution_engine().active_executions.pop(execution_id, None)
        raise ChatExecutionError(str(e))

    try:
        update_session_after_message(session_id, display_message)
    except Exception as e:
        logger.warning(f"Failed to update session metadata: {e}")

    logger.info(f"Chat execution started: session={session_id}, execution={execution_id}, workflow={workflow_name}")

    return {
        "success": True,
        "execution_id": execution_id,
        "chat_session_id": session_id,
        "status": "running",
        "message": "Execution started",
    }


def _verify_session_access(session_id: str, user_id: str) -> None:
    """Verify user has access to the session."""
    from backend.models import ChatSession

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
