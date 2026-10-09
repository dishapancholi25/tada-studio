"""Pydantic models for HTTP execution API.

This module defines request and response models for HTTP-triggered workflow execution,
providing data validation and serialization.
"""

from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


class HttpExecutionRequest(BaseModel):
    """Request model for HTTP-triggered execution.

    Supports multiple file input formats:
    - ``file_info``: Standard format (matches Graph API) with base64, extension, name, type, size.
    - ``file``: TADA Chat format with base64, file_name, file_type fields.
    - ``chat_files``: TADA Chat array format (first file is used).
    """

    message: str = Field(..., description="Message to pass to the workflow")
    async_mode: bool = Field(
        False,
        description="If true, return immediately with execution ID. If false, wait for completion and return results.",
    )
    timeout: int = Field(
        300, description="Timeout in seconds for sync mode (default: 5 minutes)"
    )
    clear_memory: bool = Field(
        False,
        description=(
            "If true, clear stored conversation memory for every agent (and "
            "sub-agent) in the workflow before executing. Use this to start a "
            "fresh chat (e.g. TADA Chat 'New Chat') so cross-execution memory "
            "does not carry over."
        ),
    )
    file_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Standard file data for FILE_READ nodes (base64, extension, name, type, size)",
    )
    file: Optional[Dict[str, Any]] = Field(
        None,
        description="TADA Chat single file object (base64, file_name, file_type)",
    )
    chat_files: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="TADA Chat file array (first file is used for FILE_READ nodes)",
    )

    class Config:
        extra = "allow"

    def resolve_file_data(self) -> Optional[Dict[str, Any]]:
        """Resolve file data from any supported format into standard file_info format.

        Priority: file_info > file > chat_files[0]

        Returns:
            Normalized file data dict or None if no file provided.
        """
        if self.file_info:
            return self.file_info

        source = self.file or (self.chat_files[0] if self.chat_files else None)
        if not source:
            return None

        base64_content = source.get("base64")
        if not base64_content:
            return None

        file_type = source.get("file_type", "pdf")
        file_name = source.get("file_name") or source.get("original_file_name") or "unknown"
        extension = f".{file_type}" if not file_type.startswith(".") else file_type

        return {
            "base64": base64_content,
            "extension": extension,
            "name": file_name,
            "type": source.get("type") or f"application/{file_type}",
            "size": len(base64_content) * 3 // 4,
        }


class CheckpointPausedResponse(BaseModel):
    """Response when execution pauses at checkpoint."""

    status: str = "paused"
    execution_id: str
    thread_id: str
    checkpoint_id: str
    checkpoint_node: str  # Name of checkpoint node
    checkpoint_input: Any  # The input to the checkpoint (from previous node)
    resume_endpoint: str
    resume_instructions: str


class HttpExecutionResponse(BaseModel):
    """Response model for HTTP-triggered execution."""

    success: bool
    execution_id: str
    status: str  # "completed", "paused", "failed", "running"
    # For completed executions
    output: Optional[Any] = None
    # For paused executions
    checkpoint_data: Optional[CheckpointPausedResponse] = None
    # For async executions
    status_endpoint: Optional[str] = None
    message: Optional[str] = None
    # Number of nodes that have reached a terminal state — used by MCP for stuck detection
    nodes_completed: Optional[int] = None


class HttpResumeRequest(BaseModel):
    """Resume a paused HTTP execution."""

    thread_id: str
    checkpoint_id: str
    user_input: Any  # User's response to checkpoint
    async_mode: bool = Field(
        False, description="If true, return immediately. If false, wait for completion."
    )
    timeout: int = Field(
        300, description="Timeout in seconds for sync mode (default: 5 minutes)"
    )


class FileUploadData(TypedDict):
    """Structured type for uploaded file data."""

    base64: str  # Base64-encoded file content
    extension: str  # File extension (e.g., '.txt')
    name: str  # Original filename
    type: str  # MIME type
    size: int  # File size in bytes


class ExecutionState(TypedDict):
    """Type-safe structure for active execution state."""

    execution_id: str
    status: str  # "pending", "running", "completed", "failed", "paused"
    start_time: str
    graph_name: str
    current_node: Optional[str]
    node_execution_map: dict[str, Any]
    db_execution_id: Optional[int]
    source: str  # "http", "http-sse", "ui"
    paused: Optional[dict[str, Any]]  # Checkpoint pause data
    error: Optional[str]  # Error message if failed


class CheckpointStateData(TypedDict):
    """Type-safe structure for stored checkpoint state."""

    graph_name: str
    checkpoint_id: str
    execution_id: str
    db_execution_id: Optional[int]
    paused_at: str  # ISO format datetime
    checkpoint_node: str
    checkpoint_input: Any


class CheckpointNodeData(TypedDict):
    """Type-safe structure for checkpoint node information."""

    node_name: str
    checkpoint_input: Any
    node_id: str


class LatestExecutionResponse(BaseModel):
    """Response for latest execution query."""

    success: bool
    has_active_execution: bool
    execution_id: Optional[str] = None
    status: Optional[str] = None
    start_time: Optional[str] = None
    db_execution_id: Optional[int] = None


class ExecutionInfoResponse(BaseModel):
    """Response for execution info endpoint."""

    success: bool
    graph_name: str
    endpoint: str
    method: str
    headers: dict[str, str]
    body_format: dict[str, str]
    has_token: bool
    example_curl: str
    example_body: dict[str, str]


class SSEEvent(TypedDict):
    """Type-safe structure for SSE events."""

    event: str  # Event type: 'acknowledged', 'started', 'node_executing', 'completed', 'failed', 'error', 'done'
    message: Optional[str]
    graph: Optional[str]
    execution_id: Optional[str]
    node: Optional[str]
    status: Optional[str]
    output: Optional[Any]
    error: Optional[str]


class ClientContext(TypedDict, total=False):
    """Type-safe structure for client request context."""

    client_ip: Optional[str]
    user_agent: Optional[str]
    token: Optional[str]
    graph_name: str
    execution_id: str
