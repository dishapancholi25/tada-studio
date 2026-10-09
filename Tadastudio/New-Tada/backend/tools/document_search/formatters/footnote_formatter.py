"""Footnote-style citation formatter for document search results."""

import logging
from typing import List, Tuple

from langchain_core.documents import Document

from .base import BaseFormatter
from .metadata_utils import extract_document_name, format_page_info_inline


logger = logging.getLogger(__name__)


class FootnoteFormatter(BaseFormatter):
    """Formats results with footnote-style citations."""

    def format(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        include_confidence: bool = True,
    ) -> str:
        """Format results with footnote citations.

        Args:
            results: List of (Document, score) tuples
            query: Original search query
            include_confidence: Whether to include confidence scores

        Returns:
            Formatted string with footnote citations
        """
        if self._check_empty_results(results):
            return self._get_empty_message()

        formatted_results = []
        citations = []

        for i, (doc, score) in enumerate(results):
            footnote_num = i + 1

            # Add content with footnote marker
            content = doc.page_content.strip()
            formatted_results.append(f"{content} [{footnote_num}]")

            # Build citation
            citation = self._build_citation(
                doc.metadata,
                footnote_num,
                include_confidence,
            )
            citations.append(citation)

        # Combine results and citations
        output = "\n\n".join(formatted_results)
        output += "\n\nReferences:\n" + "\n".join(citations)

        return output

    def _build_citation(
        self,
        metadata: dict,
        footnote_num: int,
        include_confidence: bool,
    ) -> str:
        """Build footnote citation.

        Args:
            metadata: Document metadata
            footnote_num: Footnote number
            include_confidence: Whether to include collection info

        Returns:
            Formatted citation string
        """
        source = extract_document_name(metadata)
        citation = f"[{footnote_num}] {source}"

        # Add page information
        page_info = format_page_info_inline(metadata)
        citation += page_info

        # Add collection if requested
        collection = metadata.get("collection_name", "")
        if collection and include_confidence:
            citation += f" (Collection: {collection})"

        return citation
