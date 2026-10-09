"""Plain text formatter for document search results without citations."""

import logging
from typing import List, Tuple

from langchain_core.documents import Document

from .base import BaseFormatter
from .metadata_utils import format_confidence_score


logger = logging.getLogger(__name__)


class PlainFormatter(BaseFormatter):
    """Formats results without citations."""

    def format(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        include_confidence: bool = True,
    ) -> str:
        """Format results without citations.

        Args:
            results: List of (Document, score) tuples
            query: Original search query
            include_confidence: Whether to include confidence scores

        Returns:
            Formatted plain text string
        """
        if self._check_empty_results(results):
            return self._get_empty_message()

        formatted_results = []

        for doc, score in results:
            content = doc.page_content.strip()
            formatted_results.append(content)

            # Optionally add metadata
            if include_confidence:
                metadata_line = self._build_metadata_line(doc.metadata, score)
                if metadata_line:
                    formatted_results.append(metadata_line)

        return "\n\n".join(formatted_results)

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

        # Add page information
        if "page_label" in metadata:
            metadata_items.append(f"Page: {metadata['page_label']}")
        elif "page" in metadata and metadata["page"] is not None:
            metadata_items.append(f"Page: {metadata['page'] + 1}")

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
