"""Inline citation formatter for document search results."""

import logging
from typing import List, Tuple

from langchain_core.documents import Document

from .base import BaseFormatter
from .metadata_utils import (
    extract_document_name,
    format_confidence_score,
    format_page_info_inline,
)


logger = logging.getLogger(__name__)


class InlineFormatter(BaseFormatter):
    """Formats results with inline citations."""

    def format(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        include_confidence: bool = True,
    ) -> str:
        """Format results with inline citations.

        Args:
            results: List of (Document, score) tuples
            query: Original search query
            include_confidence: Whether to include confidence scores

        Returns:
            Formatted string with inline citations
        """
        if self._check_empty_results(results):
            return self._get_empty_message()

        formatted_results = []

        for doc, score in results:
            # Build result with inline citation
            result_text = self._build_result_with_citation(doc, score)
            formatted_results.append(result_text)

            # Add metadata if requested
            if include_confidence:
                metadata_line = self._build_metadata_line(doc.metadata, score)
                if metadata_line:
                    formatted_results.append(metadata_line)

        return "\n\n".join(formatted_results)

    def _build_result_with_citation(
        self,
        doc: Document,
        score: float,
    ) -> str:
        """Build result text with inline citation.

        Args:
            doc: Document object
            score: Relevance score

        Returns:
            Formatted result string
        """
        content = doc.page_content.strip()
        source = extract_document_name(doc.metadata)
        page_info = format_page_info_inline(doc.metadata)

        return f"{content} [{source}{page_info}]"

    def _build_metadata_line(
        self,
        metadata: dict,
        score: float,
    ) -> str:
        """Build metadata line for result.

        Args:
            metadata: Document metadata
            score: Relevance score

        Returns:
            Formatted metadata string or empty string
        """
        metadata_items = []

        # Add collection name
        if "collection_name" in metadata:
            metadata_items.append(f"Collection: {metadata['collection_name']}")

        # Add relevance score
        if score < 1.0:
            metadata_items.append(
                f"Relevance: {format_confidence_score(score, as_percentage=False)}"
            )

        if metadata_items:
            return f"   Metadata: {', '.join(metadata_items)}"
        return ""
