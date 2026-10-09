"""JSON output formatter."""

import logging
from typing import Any, Dict

from .base import OutputFormatter


logger = logging.getLogger(__name__)


class JSONFormatter(OutputFormatter):
    """Formatter for JSON output."""

    def format(self, raw_result: Dict[str, Any], config: Dict[str, Any]) -> Dict:
        """
        Format result as JSON.

        Args:
            raw_result: Raw processing result
            config: Processing configuration

        Returns:
            JSON-compatible dictionary
        """
        # If content has documents (from Unstructured), format them
        if "documents" in raw_result:
            return self._format_documents(raw_result)

        # If OCR result with blocks
        if "blocks" in raw_result:
            return self._format_ocr_result(raw_result)

        # Default: simple JSON structure
        content = raw_result.get("content", "")
        if isinstance(content, dict):
            return content

        return {
            "text": str(content),
            "extraction_method": raw_result.get("extraction_method", "unknown"),
        }

    def _format_documents(self, raw_result: Dict[str, Any]) -> Dict:
        """Format Unstructured documents as JSON."""
        documents = raw_result.get("documents", [])

        pages = []
        full_text = []
        current_page = None

        for doc in documents:
            page_num = doc.metadata.get("page_number", 1)

            if current_page != page_num:
                current_page = page_num
                pages.append(
                    {
                        "page_number": page_num,
                        "content": doc.page_content,
                    }
                )
            else:
                # Append to last page
                pages[-1]["content"] += "\n" + doc.page_content

            full_text.append(doc.page_content)

        return {
            "pages": pages,
            "text": "\n".join(full_text),
        }

    def _format_ocr_result(self, raw_result: Dict[str, Any]) -> Dict:
        """Format OCR result with blocks."""
        return {
            "text": raw_result.get("content", ""),
            "blocks": raw_result.get("blocks", []),
            "confidence": raw_result.get("ocr_confidence", 0.0),
        }
