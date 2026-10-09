"""File upload and processing handlers.

This module provides handler functions for file upload and processing operations.
"""

import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException, UploadFile

from backend.services.authorization import require_workflow_access
from backend.services.authorization.helpers import get_user_identifier
from backend.services.config import get_logger
from backend.services.document import DocumentService
from backend.services.document.config import ALLOWED_FILE_DIRS

from ..constants import LOG_PREFIX
from ..exceptions import FileProcessingError
from ..services.file_processor import FileProcessorService, get_file_owner

logger = get_logger(__name__)


def _validate_file_path(file_path: str) -> Path:
    """Validate a file path to prevent path traversal attacks.

    Args:
        file_path: Path string to validate

    Returns:
        Resolved Path object

    Raises:
        FileProcessingError: If path is invalid or outside allowed directories
    """
    if "\0" in file_path:
        raise FileProcessingError(file_path, "Path traversal is not allowed")

    resolved = os.path.realpath(file_path)

    for base_dir in ALLOWED_FILE_DIRS:
        base_prefix = str(base_dir) + os.sep
        if resolved == str(base_dir) or resolved.startswith(base_prefix):
            return Path(resolved)

    raise FileProcessingError(file_path, "File path is outside allowed directories")


def _require_file_owner(file_path: Path, current_user: Dict[str, Any]) -> None:
    """Require the caller to own a validated upload path.

    Legacy files without registry entries are intentionally admin-only so a
    leaked path cannot grant cross-user access.
    """
    if current_user.get("is_admin", False):
        return

    caller_identifier = get_user_identifier(current_user)
    owner_identifier = get_file_owner(str(file_path))
    if owner_identifier != caller_identifier:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this file",
        )


async def handle_upload_file(
    file: UploadFile, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Upload a file for processing by FILE_READ nodes.

    Args:
        file: Uploaded file
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and file info

    Raises:
        FileUploadError: If upload validation fails
    """
    logger.info(f"{LOG_PREFIX} Uploading file: {file.filename}")

    # Read file contents
    contents = await file.read()
    user_identifier = get_user_identifier(current_user)

    # Process upload
    file_info = await FileProcessorService.process_upload(
        file.filename, contents, owner_identifier=user_identifier
    )

    logger.info(f"{LOG_PREFIX} File uploaded successfully: {file.filename}")
    return {
        "success": True,
        "file_info": file_info,
    }


async def handle_get_file_metadata(
    file_path: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Get metadata about a file without processing it.

    Args:
        file_path: Path to file
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and metadata

    Raises:
        FileProcessingError: If file not found
    """
    logger.info(f"{LOG_PREFIX} Getting file metadata")

    file_path_obj = _validate_file_path(file_path)
    _require_file_owner(file_path_obj, current_user)
    if not file_path_obj.exists():
        raise FileProcessingError(file_path, "File not found")

    stat = file_path_obj.stat()
    mime_type, _ = mimetypes.guess_type(str(file_path_obj))

    return {
        "success": True,
        "metadata": {
            "filename": file_path_obj.name,
            "file_path": str(file_path_obj),
            "file_size": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "mime_type": mime_type,
            "extension": file_path_obj.suffix,
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
        },
    }


async def handle_process_file(
    file_path: str,
    current_user: Dict[str, Any],
    extraction_mode: str = "auto",
    output_format: str = "markdown",
    ocr_library: str = "easyocr",
    language: str = "en",
) -> Dict[str, Any]:
    """Process a file using document service directly.

    Args:
        file_path: Path to file
        current_user: Current user from JWT token
        extraction_mode: Extraction mode (auto, text, ocr, etc.)
        output_format: Output format (markdown, text, etc.)
        ocr_library: OCR library to use
        language: Language for OCR

    Returns:
        Dictionary with success status, content, metadata, and extraction method

    Raises:
        FileProcessingError: If file processing fails
    """
    logger.info(f"{LOG_PREFIX} Processing file")

    file_path_obj = _validate_file_path(file_path)
    _require_file_owner(file_path_obj, current_user)

    try:
        # Initialize document service
        doc_service = DocumentService()

        # Process configuration
        config = {
            "extraction_mode": extraction_mode,
            "output_format": output_format,
            "ocr_library": ocr_library,
            "language": language,
        }

        # Process document
        result = doc_service.process_document(
            file_path=str(file_path_obj), config=config, use_cache=True
        )

        return {
            "success": result.get("success", False),
            "content": result.get("content", ""),
            "metadata": result.get("metadata", {}),
            "extraction_method": result.get("extraction_method", "unknown"),
        }
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error processing file: {e}")
        raise FileProcessingError(file_path, str(e))


async def handle_execute_with_file(
    graph_name: str,
    username: str,
    async_execution: bool,
    message: Optional[str],
    file: Optional[UploadFile],
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a graph with optional file input.

    If no file is provided, checks for a persistent file stored with the workflow.

    Args:
        graph_name: Name of the graph
        username: Username
        async_execution: Whether to execute asynchronously
        message: Optional message
        file: Optional uploaded file
        current_user: Current user from JWT token

    Returns:
        Dictionary with execution result

    Raises:
        FileUploadError: If file validation fails
    """

    require_workflow_access(current_user, graph_name)
    logger.info(f"{LOG_PREFIX} Executing graph '{graph_name}' with file")

    from ..models import GraphExecutionRequest

    # Prepare initial input
    initial_input = {}
    file_info = None

    # Handle file if provided
    if file:
        # Read file contents
        contents = await file.read()

        # Process upload
        file_info = await FileProcessorService.process_upload(
            file.filename,
            contents,
            owner_identifier=get_user_identifier(current_user),
        )

        # Add to initial input
        initial_input["file_info"] = file_info

        # Also store file persistently for MCP tools to access
        # This allows RAG MCP servers to query the file using workflow_id
        from . import workflow_file
        try:
            # Reset file position for re-reading
            await file.seek(0)
            await workflow_file.handle_upload_workflow_file(
                graph_name, file, current_user
            )
            logger.info(f"{LOG_PREFIX} File also stored persistently for MCP tools")
        except Exception as e:
            # Log but don't fail execution if persistent storage fails
            logger.warning(f"{LOG_PREFIX} Could not store file persistently for MCP: {e}")

    else:
        # No file provided - always check for persistent workflow file
        from . import workflow_file

        logger.info(f"{LOG_PREFIX} No file provided, checking for persistent file for '{graph_name}'")

        try:
            # Always try to load persistent file when no file is provided
            persistent_file = await workflow_file.handle_get_workflow_file_content(
                graph_name, current_user
            )
            if persistent_file.get("success") and persistent_file.get("has_file"):
                # Use the persistent file
                logger.info(f"{LOG_PREFIX} Using persistent file for '{graph_name}': {persistent_file.get('filename')}")
                file_info = {
                    "path": None,  # Not a filesystem path
                    "content": persistent_file["content"],
                    "filename": persistent_file["filename"],
                    "extension": persistent_file["file_extension"],
                    "content_type": persistent_file["content_type"],
                }
                initial_input["file_info"] = file_info
            else:
                logger.info(f"{LOG_PREFIX} No persistent file found for '{graph_name}'")
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} Could not load persistent file: {e}")

    # Add message if provided
    if message:
        initial_input["message"] = message

    # Create execution request
    request = GraphExecutionRequest(
        graph_name=graph_name,
        initial_input=initial_input,
        username=username,
        async_execution=async_execution,
        file_info=file_info,
    )

    # Use the execution handler
    from .execution import handle_execute_graph

    return await handle_execute_graph(request, current_user)
