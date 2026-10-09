"""PDF file processor using PyPDF2."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from ..config import PDF_FILE_TYPES
from ..exceptions import DocumentProcessingError, ProcessorNotAvailableError
from .base import DocumentProcessor


logger = logging.getLogger(__name__)


class PDFProcessor(DocumentProcessor):
    """Processor for PDF files using PyPDF2."""

    def __init__(self):
        """Initialize PDF processor."""
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if PyPDF2 is available."""
        try:
            import PyPDF2  # noqa: F401

            logger.debug("[DOC-PDF] PyPDF2 available")
        except ImportError:
            raise ProcessorNotAvailableError("pdf", "PyPDF2 library not installed")

    def supports(self, file_type: str) -> bool:
        """Check if this processor supports the file type."""
        return file_type in PDF_FILE_TYPES

    def process(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a PDF file.

        Args:
            file_path: Path to PDF file
            config: Processing configuration

        Returns:
            Dictionary with extracted content and page count
        """
        logger.info(f"[DOC-PDF] Processing PDF file: {file_path.name}")

        try:
            pages = self._extract_pages(file_path, config)
            content = "\n\n".join(pages)
            page_count = len(pages)

            logger.debug(f"[DOC-PDF] Extracted {page_count} pages")

            return {
                "content": content,
                "extraction_method": "pypdf2",
                "page_count": page_count,
            }

        except Exception as e:
            logger.error(f"[DOC-PDF] PDF extraction failed: {e}")
            raise DocumentProcessingError(
                f"Failed to process PDF: {e}",
                file_path=str(file_path),
                processor="pdf",
            )

    def _extract_pages(self, file_path: Path, config: Dict[str, Any]) -> List[str]:
        """Extract text from PDF pages."""
        import PyPDF2

        pages = []

        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_range = self._get_page_range(config, len(pdf_reader.pages))

            for page_num in page_range:
                if page_num < len(pdf_reader.pages):
                    page = pdf_reader.pages[page_num]
                    pages.append(page.extract_text())

        return pages

    def _get_page_range(self, config: Dict[str, Any], total_pages: int) -> range:
        """Get range of pages to extract."""
        page_numbers = config.get("page_numbers")
        if page_numbers:
            return page_numbers
        return range(total_pages)
