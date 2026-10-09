"""Workflow file storage handlers.

This module provides handler functions for persistent file storage per workflow.
Files are stored with the workflow and persist across executions.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import UploadFile

from backend.services.authorization import require_workflow_access
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager

from ..constants import LOG_PREFIX
from ..exceptions import FileProcessingError


logger = get_logger(__name__)

# Base directory for workflow files
WORKFLOW_FILES_DIR = Path(__file__).parent.parent.parent.parent.parent / "workspace" / "workflow_files"


def _get_workflow_file_dir(workflow_id: str) -> Path:
    """Get the directory for a workflow's files."""
    return WORKFLOW_FILES_DIR / workflow_id


def _get_workflow_file_path(workflow_id: str) -> Path:
    """Get the path to the workflow's stored file."""
    return _get_workflow_file_dir(workflow_id) / "file_data.json"


def _ensure_workflow_dir(workflow_id: str) -> Path:
    """Ensure the workflow file directory exists."""
    dir_path = _get_workflow_file_dir(workflow_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


async def handle_upload_workflow_file(
    graph_name: str,
    file: UploadFile,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Upload and store a file for a workflow.

    The file is stored persistently and associated with the workflow.
    If a file already exists, it will be replaced.

    Args:
        graph_name: Name of the workflow
        file: Uploaded file
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and file info
    """
    require_workflow_access(current_user, graph_name)
    logger.info(f"{LOG_PREFIX} Uploading file for workflow '{graph_name}'")

    # Get workflow to verify it exists and get workflow_id
    graph_manager = get_graph_manager()
    user_id = current_user.get("email") or current_user.get("sub") or "anonymous"

    graph_data = graph_manager.get_graph(graph_name) or graph_manager.load_graph(graph_name, user_id)
    if not graph_data:
        raise FileProcessingError(graph_name, "Workflow not found")

    workflow_id = getattr(graph_data, "workflow_id", None) or graph_name

    # Read file contents
    contents = await file.read()
    file_size = len(contents)

    # Validate file size (max 50MB)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise FileProcessingError(
            file.filename or "unknown",
            f"File too large. Maximum size is 50MB, got {file_size / (1024*1024):.2f}MB"
        )

    # Get file extension
    filename = file.filename or "uploaded_file"
    file_ext = Path(filename).suffix.lower()

    # Validate file type
    allowed_extensions = [".txt", ".csv", ".pdf", ".json", ".md", ".xml", ".html"]
    if file_ext not in allowed_extensions:
        raise FileProcessingError(
            filename,
            f"File type '{file_ext}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Ensure directory exists
    workflow_dir = _ensure_workflow_dir(workflow_id)

    # Store the actual file content
    content_file_path = workflow_dir / f"content{file_ext}"
    with open(content_file_path, "wb") as f:
        f.write(contents)

    # Determine content type
    text_extensions = [".txt", ".csv", ".json", ".md", ".xml", ".html"]
    if file_ext in text_extensions:
        try:
            contents.decode("utf-8")
            content_type = "text"
        except UnicodeDecodeError:
            content_type = "binary"
    else:
        content_type = "binary"

    # Store metadata
    file_data = {
        "workflow_id": workflow_id,
        "graph_name": graph_name,
        "filename": filename,
        "file_extension": file_ext,
        "file_size": file_size,
        "content_type": content_type,
        "content_file": str(content_file_path),
        "uploaded_at": datetime.utcnow().isoformat(),
        "uploaded_by": user_id,
    }

    metadata_path = _get_workflow_file_path(workflow_id)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(file_data, f, indent=2)

    logger.info(f"{LOG_PREFIX} File stored for workflow '{graph_name}': {filename}")

    return {
        "success": True,
        "message": f"File '{filename}' uploaded successfully",
        "file_info": {
            "filename": filename,
            "file_size": file_size,
            "file_size_kb": round(file_size / 1024, 2),
            "file_extension": file_ext,
            "content_type": content_type,
            "uploaded_at": file_data["uploaded_at"],
        },
    }


async def handle_get_workflow_file(
    graph_name: str,
    current_user: Dict[str, Any],
    include_content: bool = False,
) -> Dict[str, Any]:
    """Get file info for a workflow.

    Args:
        graph_name: Name of the workflow
        current_user: Current user from JWT token
        include_content: Whether to include file content in response

    Returns:
        Dictionary with file info or not_found status
    """
    require_workflow_access(current_user, graph_name)
    logger.info(f"{LOG_PREFIX} Getting file info for workflow '{graph_name}'")

    # Get workflow to verify it exists and get workflow_id
    graph_manager = get_graph_manager()
    user_id = current_user.get("email") or current_user.get("sub") or "anonymous"

    graph_data = graph_manager.get_graph(graph_name) or graph_manager.load_graph(graph_name, user_id)
    if not graph_data:
        raise FileProcessingError(graph_name, "Workflow not found")

    workflow_id = getattr(graph_data, "workflow_id", None) or graph_name

    # Check if file exists
    metadata_path = _get_workflow_file_path(workflow_id)
    if not metadata_path.exists():
        return {
            "success": True,
            "has_file": False,
            "message": "No file uploaded for this workflow",
        }

    # Load metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        file_data = json.load(f)

    response = {
        "success": True,
        "has_file": True,
        "file_info": {
            "filename": file_data["filename"],
            "file_size": file_data["file_size"],
            "file_size_kb": round(file_data["file_size"] / 1024, 2),
            "file_extension": file_data["file_extension"],
            "content_type": file_data["content_type"],
            "uploaded_at": file_data["uploaded_at"],
            "uploaded_by": file_data.get("uploaded_by", "unknown"),
        },
    }

    # Include content if requested and it's a text file
    if include_content and file_data["content_type"] == "text":
        content_file = Path(file_data["content_file"])
        if content_file.exists():
            with open(content_file, "r", encoding="utf-8") as f:
                response["file_content"] = f.read()

    return response


async def handle_delete_workflow_file(
    graph_name: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Delete the stored file for a workflow.

    Args:
        graph_name: Name of the workflow
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status
    """
    require_workflow_access(current_user, graph_name)
    logger.info(f"{LOG_PREFIX} Deleting file for workflow '{graph_name}'")

    # Get workflow to verify it exists and get workflow_id
    graph_manager = get_graph_manager()
    user_id = current_user.get("email") or current_user.get("sub") or "anonymous"

    graph_data = graph_manager.get_graph(graph_name) or graph_manager.load_graph(graph_name, user_id)
    if not graph_data:
        raise FileProcessingError(graph_name, "Workflow not found")

    workflow_id = getattr(graph_data, "workflow_id", None) or graph_name

    # Check if file exists
    workflow_dir = _get_workflow_file_dir(workflow_id)
    if not workflow_dir.exists():
        return {
            "success": True,
            "message": "No file to delete",
        }

    # Get filename before deleting
    metadata_path = _get_workflow_file_path(workflow_id)
    filename = "unknown"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
            filename = file_data.get("filename", "unknown")

    # Delete the entire workflow file directory
    shutil.rmtree(workflow_dir)

    logger.info(f"{LOG_PREFIX} File deleted for workflow '{graph_name}': {filename}")

    return {
        "success": True,
        "message": f"File '{filename}' deleted successfully",
        "deleted_file": filename,
    }


async def handle_get_workflow_file_content(
    graph_name: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Get the full file content for a workflow.

    This is used by the RAG MCP server to get file content for processing.

    Args:
        graph_name: Name of the workflow
        current_user: Current user from JWT token

    Returns:
        Dictionary with file content
    """
    require_workflow_access(current_user, graph_name)
    logger.info(f"{LOG_PREFIX} Getting file content for workflow '{graph_name}'")

    # Get workflow to verify it exists and get workflow_id
    graph_manager = get_graph_manager()
    user_id = current_user.get("email") or current_user.get("sub") or "anonymous"

    graph_data = graph_manager.get_graph(graph_name) or graph_manager.load_graph(graph_name, user_id)
    if not graph_data:
        raise FileProcessingError(graph_name, "Workflow not found")

    workflow_id = getattr(graph_data, "workflow_id", None) or graph_name

    # Check if file exists
    metadata_path = _get_workflow_file_path(workflow_id)
    if not metadata_path.exists():
        return {
            "success": False,
            "has_file": False,
            "message": "No file uploaded for this workflow",
        }

    # Load metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        file_data = json.load(f)

    # Read content
    content_file = Path(file_data["content_file"])
    if not content_file.exists():
        return {
            "success": False,
            "message": "File content not found",
        }

    # Read based on content type
    if file_data["content_type"] == "text":
        with open(content_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        import base64
        with open(content_file, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

    return {
        "success": True,
        "has_file": True,
        "workflow_id": workflow_id,
        "filename": file_data["filename"],
        "file_extension": file_data["file_extension"],
        "content_type": file_data["content_type"],
        "content": content,
    }
