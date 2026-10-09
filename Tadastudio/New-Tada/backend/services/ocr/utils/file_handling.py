"""File handling utilities for OCR services."""

import logging
import os
from pathlib import Path

from ..config import DEFAULT_MAX_FILE_SIZE_MB
from ..exceptions import FileNotFoundError, FileSizeExceededError


logger = logging.getLogger(__name__)


def load_file_bytes(file_path: str) -> bytes:
    """
    Load file contents as bytes.

    Args:
        file_path: Path to file

    Returns:
        File contents as bytes

    Raises:
        FileNotFoundError: If file does not exist
        OSError: If file cannot be read
    """
    if not os.path.exists(file_path):
        logger.error(f"[OCR-FILE] File not found: {file_path}")
        raise FileNotFoundError(file_path)

    logger.debug(f"[OCR-FILE] Loading file: {file_path}")
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except OSError as e:
        logger.error(f"[OCR-FILE] Failed to read file: {e}")
        raise


def validate_file_size(
    file_path: str, max_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB
) -> float:
    """
    Validate file size is within limits.

    Args:
        file_path: Path to file
        max_size_mb: Maximum allowed file size in MB

    Returns:
        File size in MB

    Raises:
        FileNotFoundError: If file does not exist
        FileSizeExceededError: If file exceeds maximum size
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    logger.debug(f"[OCR-FILE] File size: {file_size_mb:.2f} MB (max: {max_size_mb} MB)")

    if file_size_mb > max_size_mb:
        logger.error(
            f"[OCR-FILE] File size ({file_size_mb:.2f} MB) exceeds "
            f"maximum ({max_size_mb} MB)"
        )
        raise FileSizeExceededError(file_size_mb, max_size_mb)

    return file_size_mb


def get_file_extension(file_path: str) -> str:
    """
    Get file extension from path.

    Args:
        file_path: Path to file

    Returns:
        File extension (lowercase, with leading dot)
    """
    return Path(file_path).suffix.lower()
