"""OCR services for document processing using configurable AI models and traditional OCR engines."""

from .config import (
    ALL_SUPPORTED_EXTENSIONS,
    DEFAULT_OCR_PROMPTS,
    auto_detect_doc_type,
    get_default_prompt,
)
from .exceptions import (
    FileSizeExceededError,
    InvalidInputError,
    OCRConfigError,
    OCRException,
    OCRProcessingError,
    UnsupportedFileTypeError,
)
from .models import (
    AzureOpenAIConfig,
    LegacyOCRResponse,
    OCRRequest,
    OCRResponse,
    PageResult,
)
from .service import GPT4oOCRService


# Legacy OCR service import
try:
    from .legacy_ocr_service import OCRService
except ImportError:
    # Legacy service not yet moved
    OCRService = None

__all__ = [
    # Main service
    "GPT4oOCRService",
    # Legacy service
    "OCRService",
    # Models
    "OCRRequest",
    "OCRResponse",
    "PageResult",
    "AzureOpenAIConfig",
    "LegacyOCRResponse",
    # Exceptions
    "OCRException",
    "OCRConfigError",
    "OCRProcessingError",
    "UnsupportedFileTypeError",
    "FileSizeExceededError",
    "InvalidInputError",
    # Config utilities
    "get_default_prompt",
    "auto_detect_doc_type",
    "DEFAULT_OCR_PROMPTS",
    "ALL_SUPPORTED_EXTENSIONS",
]


def create_gpt4o_ocr_service(azure_config=None) -> GPT4oOCRService:
    """
    Create GPT-4o OCR service.

    Args:
        azure_config: Optional Azure OpenAI configuration dict

    Returns:
        Configured GPT4oOCRService instance
    """
    return GPT4oOCRService(azure_config=azure_config)


def create_legacy_ocr_service(library: str = "easyocr", language: str = "en"):
    """
    Create legacy OCR service.

    Args:
        library: OCR library to use (easyocr, paddleocr, tesseract, etc.)
        language: Language code for OCR

    Returns:
        Configured OCRService instance

    Raises:
        ImportError: If legacy OCR service is not available
    """
    if OCRService is None:
        raise ImportError(
            "Legacy OCR service not available. "
            "Ensure legacy_ocr_service.py is in the ocr module."
        )
    return OCRService(library=library, language=language)
