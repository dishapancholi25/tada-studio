"""OCR processor that delegates to OCR service."""

import logging
from pathlib import Path
from typing import Any, Dict

from ..config import OCR_FILE_TYPES
from ..exceptions import DocumentProcessingError, ProcessorNotAvailableError
from .base import DocumentProcessor


logger = logging.getLogger(__name__)


class OCRProcessor(DocumentProcessor):
    """Processor for images using OCR service."""

    def __init__(self):
        """Initialize OCR processor."""
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if OCR service is available."""
        try:
            from backend.services.ocr.legacy_ocr_service import OCRService  # noqa: F401

            logger.debug("[DOC-OCR] OCR service available")
        except ImportError:
            raise ProcessorNotAvailableError("ocr", "OCR service not available")

    def supports(self, file_type: str) -> bool:
        """Check if this processor supports the file type."""
        return file_type in OCR_FILE_TYPES

    def process(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image using OCR.

        Args:
            file_path: Path to image file
            config: Processing configuration

        Returns:
            Dictionary with extracted content
        """
        logger.info(f"[DOC-OCR] Processing image: {file_path.name}")

        try:
            from backend.services.ocr.legacy_ocr_service import OCRService

            # Initialize OCR service
            ocr_library = config.get("ocr_library", "easyocr")
            language = config.get("language", "en")
            ocr_service = OCRService(library=ocr_library, language=language)

            # Perform OCR
            confidence_threshold = config.get("ocr_confidence_threshold", 0.5)
            result = ocr_service.extract_text_from_image(
                image_path=str(file_path),
                confidence_threshold=confidence_threshold,
            )

            logger.debug(
                f"[DOC-OCR] Extracted text with confidence: "
                f"{result['average_confidence']:.2%}"
            )

            return {
                "content": result["text"],
                "extraction_method": "ocr",
                "ocr_confidence": result["average_confidence"],
                "ocr_method": result["extraction_method"],
                "blocks": result.get("blocks", []),
            }

        except Exception as e:
            logger.error(f"[DOC-OCR] OCR processing failed: {e}")
            raise DocumentProcessingError(
                f"OCR processing failed: {e}",
                file_path=str(file_path),
                processor="ocr",
            )
