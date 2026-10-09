"""Chat API exceptions."""

from fastapi import HTTPException


class ChatSessionNotFoundError(HTTPException):
    """Raised when a chat session is not found."""

    def __init__(self, session_id: str):
        super().__init__(status_code=404, detail=f"Chat session '{session_id}' not found")


class ChatAccessDeniedError(HTTPException):
    """Raised when a user doesn't own the chat session."""

    def __init__(self):
        super().__init__(status_code=403, detail="Access denied to this chat session")


class WorkflowNotPublishedError(HTTPException):
    """Raised when the workflow is not published or not found."""

    def __init__(self, workflow_id: str):
        super().__init__(
            status_code=404,
            detail=f"Published workflow '{workflow_id}' not found or not published",
        )


class ChatExecutionError(HTTPException):
    """Raised when execution fails to start."""

    def __init__(self, message: str):
        super().__init__(status_code=500, detail=f"Chat execution error: {message}")
