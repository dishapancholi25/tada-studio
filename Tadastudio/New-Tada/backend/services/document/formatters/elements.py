"""Elements output formatter."""

import logging
from typing import Any, Dict, List

from .base import OutputFormatter


logger = logging.getLogger(__name__)


class ElementsFormatter(OutputFormatter):
    """Formatter for structured elements output."""

    def format(self, raw_result: Dict[str, Any], config: Dict[str, Any]) -> List[Dict]:
        """
        Format result as structured elements.

        Args:
            raw_result: Raw processing result
            config: Processing configuration

        Returns:
            List of element dictionaries
        """
        # If documents from Unstructured, format as elements
        if "documents" in raw_result:
            return self._format_documents(raw_result)

        # If OCR blocks, format as elements
        if "blocks" in raw_result:
            return self._format_ocr_blocks(raw_result)

        # Default: single element
        return [
            {
                "type": "text",
                "text": str(raw_result.get("content", "")),
                "metadata": {},
            }
        ]

    def _format_documents(self, raw_result: Dict[str, Any]) -> List[Dict]:
        """Format Unstructured documents as elements."""
        documents = raw_result.get("documents", [])
        elements = []

        for doc in documents:
            elements.append(
                {
                    "type": doc.metadata.get("category", "text"),
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                }
            )

        return elements

    def _format_ocr_blocks(self, raw_result: Dict[str, Any]) -> List[Dict]:
        """Format OCR blocks as elements."""
        blocks = raw_result.get("blocks", [])
        elements = []

        for block in blocks:
            elements.append(
                {
                    "type": "text",
                    "text": block.get("text", ""),
                    "metadata": {
                        "confidence": block.get("confidence", 0.0),
                        "bbox": block.get("bbox", []),
                    },
                }
            )

        return elements
