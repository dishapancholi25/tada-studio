"""Document processing service with support for multiple file types and processors."""

from .config import (
    DOCX_FILE_TYPES,
    EXCEL_FILE_TYPES,
    FILE_TYPE_MAP,
    IMAGE_FILE_TYPES,
    PDF_FILE_TYPES,
    TEXT_FILE_TYPES,
    determine_extraction_mode,
    get_file_type_from_extension,
    is_supported_file_type,
)
from .exceptions import (
    CacheError,
    DocumentConfigError,
    DocumentException,
    DocumentProcessingError,
    ProcessorNotAvailableError,
    UnsupportedFileTypeError,
)
from .models import (
    Element,
    FileMetadata,
    PageContent,
    ProcessingConfig,
    ProcessingRequest,
    ProcessingResult,
)
from .service import DocumentService


__all__ = [
    # Main service
    "DocumentService",
    # Models
    "ProcessingConfig",
    "ProcessingResult",
    "ProcessingRequest",
    "FileMetadata",
    "Element",
    "PageContent",
    # Exceptions
    "DocumentException",
    "DocumentConfigError",
    "DocumentProcessingError",
    "UnsupportedFileTypeError",
    "ProcessorNotAvailableError",
    "CacheError",
    # Config utilities
    "FILE_TYPE_MAP",
    "TEXT_FILE_TYPES",
    "PDF_FILE_TYPES",
    "DOCX_FILE_TYPES",
    "EXCEL_FILE_TYPES",
    "IMAGE_FILE_TYPES",
    "get_file_type_from_extension",
    "determine_extraction_mode",
    "is_supported_file_type",
]


def create_document_service(cache_dir=None) -> DocumentService:
    """
    Create document service.

    Args:
        cache_dir: Optional cache directory path

    Returns:
        Configured DocumentService instance
    """
    return DocumentService(cache_dir=cache_dir)
