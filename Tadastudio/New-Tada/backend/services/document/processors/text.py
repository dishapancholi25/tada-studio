"""Text file processor."""

import logging
from pathlib import Path
from typing import Any, Dict

from ..config import TEXT_FILE_TYPES
from ..exceptions import DocumentProcessingError
from .base import DocumentProcessor


logger = logging.getLogger(__name__)


class TextProcessor(DocumentProcessor):
    """Processor for plain text files."""

    def supports(self, file_type: str) -> bool:
        """Check if this processor supports the file type."""
        return file_type in TEXT_FILE_TYPES

    def process(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a text file.

        Args:
            file_path: Path to text file
            config: Processing configuration

        Returns:
            Dictionary with extracted content
        """
        logger.info(f"[DOC-TEXT] Processing text file: {file_path.name}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            logger.debug(f"[DOC-TEXT] Extracted {len(content)} characters")

            return {
                "content": content,
                "extraction_method": "text",
            }

        except OSError as e:
            logger.error(f"[DOC-TEXT] Failed to read file: {e}")
            raise DocumentProcessingError(
                f"Failed to read text file: {e}",
                file_path=str(file_path),
                processor="text",
            )
