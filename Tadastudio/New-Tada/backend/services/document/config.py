"""Configuration and constants for document processing."""

import tempfile
from pathlib import Path
from typing import Dict, List


# File type mappings
FILE_TYPE_MAP: Dict[str, str] = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
    ".docx": "docx",
    ".doc": "doc",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".csv": "csv",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpeg",
    ".html": "html",
    ".htm": "html",
    ".pptx": "pptx",
    ".ppt": "ppt",
}

# Supported file types by processor
TEXT_FILE_TYPES: List[str] = ["text", "markdown", "csv"]
PDF_FILE_TYPES: List[str] = ["pdf"]
DOCX_FILE_TYPES: List[str] = ["docx", "doc"]
EXCEL_FILE_TYPES: List[str] = ["xlsx", "xls"]
IMAGE_FILE_TYPES: List[str] = ["png", "jpg", "jpeg"]
HTML_FILE_TYPES: List[str] = ["html"]
PRESENTATION_FILE_TYPES: List[str] = ["pptx", "ppt"]

# File types that work well with Unstructured
UNSTRUCTURED_SUPPORTED_TYPES: List[str] = (
    PDF_FILE_TYPES + DOCX_FILE_TYPES + HTML_FILE_TYPES + PRESENTATION_FILE_TYPES
)

# File types that require OCR
OCR_FILE_TYPES: List[str] = IMAGE_FILE_TYPES

# Default cache directory
DEFAULT_CACHE_DIR: Path = Path("./document_cache")

# Allowed base directories for file operations (used for path traversal prevention)
ALLOWED_FILE_DIRS: list[Path] = [
    Path("./workspace").resolve(),
    DEFAULT_CACHE_DIR.resolve(),
    Path(tempfile.gettempdir()).resolve(),
]

# Default processing configuration
DEFAULT_EXTRACTION_MODE: str = "auto"
DEFAULT_OUTPUT_FORMAT: str = "markdown"
DEFAULT_MAX_PARTITION_SIZE: int = 1500
DEFAULT_COMBINE_UNDER_N_CHARS: int = 500


def get_file_type_from_extension(extension: str) -> str:
    """
    Get file type from extension.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        File type string, or "unknown" if not recognized
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    return FILE_TYPE_MAP.get(extension.lower(), "unknown")


def determine_extraction_mode(file_type: str) -> str:
    """
    Determine best extraction mode for a file type.

    Args:
        file_type: Detected file type

    Returns:
        Recommended extraction mode
    """
    if file_type in UNSTRUCTURED_SUPPORTED_TYPES:
        return "unstructured"
    elif file_type in OCR_FILE_TYPES:
        return "ocr"
    elif file_type in TEXT_FILE_TYPES:
        return "text"
    else:
        return "text"  # Default fallback


def is_supported_file_type(file_type: str) -> bool:
    """
    Check if file type is supported.

    Args:
        file_type: File type to check

    Returns:
        True if supported, False otherwise
    """
    return file_type in FILE_TYPE_MAP.values()
