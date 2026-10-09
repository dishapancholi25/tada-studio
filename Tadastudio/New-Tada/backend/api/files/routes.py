"""API endpoints for serving execution files from PostgreSQL."""

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ...services.execution.files import ExecutionFileService
from ..auth.dependencies import get_current_user, require_active_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/files", tags=["files"], dependencies=[Depends(require_active_user)]
)


@router.get("/{file_id}")
async def get_file(
    file_id: str,
    download: bool = Query(
        default=False,
        description="If true, force download with Content-Disposition: attachment",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Serve a file from PostgreSQL by ID.

    Requires authentication. Users can only access files from their own executions.

    Args:
        file_id: UUID of the file to retrieve.
        download: If true, sets Content-Disposition to attachment for download.
        current_user: Authenticated user from JWT token.

    Returns:
        Response with the file content and appropriate headers.

    Raises:
        HTTPException: 400 if file_id is not a valid UUID.
        HTTPException: 404 if file not found.
        HTTPException: 403 if user doesn't own the file.
    """
    # Validate UUID format to prevent injection attacks
    try:
        uuid.UUID(file_id)
    except ValueError:
        logger.warning(f"[Files API] Invalid UUID format: {file_id}")
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    logger.info(
        f"[Files API] Request for file: {file_id} (download={download}, user={current_user.get('email')})"
    )

    file_service = ExecutionFileService()
    result = file_service.get_file_content(file_id)

    if not result:
        logger.warning(f"[Files API] File not found: {file_id}")
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    # Verify ownership: check if user owns the execution that created this file
    user_id = current_user.get("sub")
    if not file_service.verify_file_ownership(file_id, user_id):
        logger.warning(
            f"[Files API] Access denied: user {current_user.get('email')} "
            f"attempted to access file {file_id} they don't own"
        )
        raise HTTPException(
            status_code=403, detail="Access denied: You do not own this file"
        )

    content, mime_type, filename = result

    logger.info(
        f"[Files API] Serving file: {filename} "
        f"(mime={mime_type}, size={len(content)}, download={download})"
    )

    # Set appropriate headers
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    return Response(
        content=content,
        media_type=mime_type,
        headers=headers,
    )


@router.get("/{file_id}/metadata")
async def get_file_metadata(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    """Get file metadata without content.

    Requires authentication. Users can only access metadata from their own executions.

    Args:
        file_id: UUID of the file.
        current_user: Authenticated user from JWT token.

    Returns:
        File metadata dictionary.

    Raises:
        HTTPException: 400 if file_id is not a valid UUID.
        HTTPException: 404 if file not found.
        HTTPException: 403 if user doesn't own the file.
    """
    # Validate UUID format to prevent injection attacks
    try:
        uuid.UUID(file_id)
    except ValueError:
        logger.warning(f"[Files API] Invalid UUID format: {file_id}")
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    file_service = ExecutionFileService()
    metadata = file_service.get_file_metadata(file_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    # Verify ownership
    user_id = current_user.get("sub")
    if not file_service.verify_file_ownership(file_id, user_id):
        logger.warning(
            f"[Files API] Access denied: user {current_user.get('email')} "
            f"attempted to access metadata for file {file_id} they don't own"
        )
        raise HTTPException(
            status_code=403, detail="Access denied: You do not own this file"
        )

    return metadata
