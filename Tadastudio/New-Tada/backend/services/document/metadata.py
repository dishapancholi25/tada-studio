"""File metadata extraction utilities."""

import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path

from .config import ALLOWED_FILE_DIRS, get_file_type_from_extension
from .models import FileMetadata


logger = logging.getLogger(__name__)


def _validate_file_path(file_path: Path) -> Path:
    """Validate and resolve a file path to prevent path traversal attacks.

    Args:
        file_path: Path to validate

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path contains traversal sequences or is outside allowed directories
    """
    resolved = os.path.realpath(file_path)

    for base_dir in ALLOWED_FILE_DIRS:
        base_prefix = str(base_dir) + os.sep
        if resolved == str(base_dir) or resolved.startswith(base_prefix):
            return Path(resolved)

    raise ValueError("File path is outside allowed directories")


def extract_file_metadata(file_path: Path) -> FileMetadata:
    """
    Extract metadata from a file.

    Args:
        file_path: Path to the file

    Returns:
        FileMetadata object with file information

    Raises:
        FileNotFoundError: If file does not exist
        OSError: If file cannot be accessed
        ValueError: If file path contains traversal sequences
    """
    file_path = _validate_file_path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path.name}")

    try:
        stat = file_path.stat()
        file_type = detect_file_type(file_path)

        logger.debug(
            f"[DOC-METADATA] Extracted metadata for {file_path.name}",
            extra={
                "file_type": file_type,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
            },
        )

        return FileMetadata(
            filename=file_path.name,
            file_path=str(file_path),
            file_type=file_type,
            file_size=stat.st_size,
            file_size_mb=round(stat.st_size / (1024 * 1024), 2),
            created_time=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            extension=file_path.suffix,
        )

    except OSError as e:
        logger.error(f"[DOC-METADATA] Failed to extract metadata: {e}")
        raise


def detect_file_type(file_path: Path) -> str:
    """
    Detect file type from extension and MIME type.

    Args:
        file_path: Path to the file

    Returns:
        File type string
    """
    # Try extension first
    ext = file_path.suffix.lower()
    file_type = get_file_type_from_extension(ext)

    # If unknown, try MIME type
    if file_type == "unknown":
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            logger.debug(f"[DOC-METADATA] Detected MIME type: {mime_type}")
            # Could add MIME type mapping here if needed

    return file_type
