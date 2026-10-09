"""Text processor for plain text files."""

import logging

from ..base import OCRProcessor
from ..config import SUPPORTED_TEXT_EXTENSIONS
from ..exceptions import InvalidInputError
from ..models import OCRRequest, OCRResponse
from ..utils import build_error_response, build_success_response


logger = logging.getLogger(__name__)


class TextProcessor(OCRProcessor):
    """Processor for plain text files (no OCR needed)."""

    def __init__(self):
        """Initialize text processor."""
        super().__init__(client=None)

    def supports_file_type(self, file_ext: str) -> bool:
        """Check if this processor supports the given file type."""
        return file_ext in SUPPORTED_TEXT_EXTENSIONS

    def process(self, request: OCRRequest) -> OCRResponse:
        """
        Process plain text file by reading directly.

        Args:
            request: OCR request with text file

        Returns:
            OCR response with file contents
        """
        try:
            text = self._read_text_file(request)

            logger.info(f"[OCR-TEXT] Processed text file: {len(text)} characters")

            return build_success_response(
                text=text,
                extraction_method="direct_text",
                tokens_used=0,
            )

        except Exception as e:
            logger.error(f"[OCR-TEXT] Error reading text file: {e}", exc_info=True)
            return build_error_response(str(e), "direct_text")

    def _read_text_file(self, request: OCRRequest) -> str:
        """Read text from file."""
        if request.file_path:
            return self._read_from_path(request.file_path)
        elif request.file_bytes:
            return self._read_from_bytes(request.file_bytes)
        else:
            raise InvalidInputError("Either file_path or file_bytes must be provided")

    def _read_from_path(self, file_path: str) -> str:
        """Read text from file path."""
        logger.debug(f"[OCR-TEXT] Reading from path: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_from_bytes(self, file_bytes: bytes) -> str:
        """Read text from bytes."""
        logger.debug(f"[OCR-TEXT] Reading from bytes: {len(file_bytes)} bytes")
        return file_bytes.decode("utf-8")
