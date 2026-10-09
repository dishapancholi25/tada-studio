"""Markdown output formatter."""

import logging
from typing import Any, Dict

from .base import OutputFormatter


logger = logging.getLogger(__name__)


class MarkdownFormatter(OutputFormatter):
    """Formatter for markdown output."""

    def format(self, raw_result: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Format result as markdown.

        Args:
            raw_result: Raw processing result
            config: Processing configuration

        Returns:
            Markdown formatted string
        """
        # If content is already a string, return it
        if isinstance(raw_result.get("content"), str):
            return self._add_metadata_if_needed(raw_result, config)

        # If content has documents (from Unstructured), combine them
        if "documents" in raw_result:
            return self._format_documents(raw_result, config)

        # Default: convert to string
        return str(raw_result.get("content", ""))

    def _add_metadata_if_needed(
        self, raw_result: Dict[str, Any], config: Dict[str, Any]
    ) -> str:
        """Add metadata header if configured."""
        content = raw_result.get("content", "")

        if not config.get("include_metadata", True):
            return content

        # Add OCR metadata if present
        if "ocr_confidence" in raw_result:
            confidence = raw_result["ocr_confidence"]
            method = raw_result.get("ocr_method", "unknown")
            header = (
                f"# OCR Extracted Content\n\n"
                f"**Confidence**: {confidence:.2%}\n"
                f"**Method**: {method}\n\n"
            )
            return header + content

        return content

    def _format_documents(
        self, raw_result: Dict[str, Any], config: Dict[str, Any]
    ) -> str:
        """Format documents from Unstructured."""
        documents = raw_result.get("documents", [])

        if config.get("include_page_breaks", False):
            return self._format_with_page_breaks(documents)

        # Simple concatenation
        return "\n\n".join([doc.page_content for doc in documents])

    def _format_with_page_breaks(self, documents) -> str:
        """Format documents with page break markers."""
        content_parts = []
        current_page = None

        for doc in documents:
            page_num = doc.metadata.get("page_number", 1)

            if current_page != page_num:
                if current_page is not None:
                    content_parts.append("\n---\n")
                content_parts.append(f"## Page {page_num}\n")
                current_page = page_num

            content_parts.append(doc.page_content)

        return "\n".join(content_parts)
