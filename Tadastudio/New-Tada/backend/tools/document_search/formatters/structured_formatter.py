"""Structured markdown formatter for document search results."""

import logging
from typing import List, Tuple

from langchain_core.documents import Document

from .base import BaseFormatter
from .metadata_utils import (
    calculate_search_statistics,
    extract_document_name,
    format_confidence_score,
    format_page_info_structured,
)


logger = logging.getLogger(__name__)


class StructuredFormatter(BaseFormatter):
    """Formats results in structured markdown format."""

    def format(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        include_confidence: bool = True,
    ) -> str:
        """Format search results in structured way for better agent understanding.

        Args:
            results: List of (Document, score) tuples
            query: Original search query
            include_confidence: Whether to include confidence scores

        Returns:
            Formatted markdown string
        """
        if self._check_empty_results(results):
            return "No relevant documents found."

        output_parts = []

        # Build header section
        output_parts.extend(self._build_header(query, results))

        # Build context section
        output_parts.extend(self._build_context_section(results, include_confidence))

        # Build references section
        references = self._build_references(results, include_confidence)
        output_parts.append("## References")
        output_parts.extend(references)

        # Build quality summary
        if include_confidence:
            output_parts.extend(self._build_quality_summary(results))

        return "\n".join(output_parts)

    def _build_header(
        self, query: str, results: List[Tuple[Document, float]]
    ) -> List[str]:
        """Build header section.

        Args:
            query: Search query
            results: Search results

        Returns:
            List of header lines
        """
        return [
            "## Document Search Results",
            f"**Query:** {query}",
            f"**Results Found:** {len(results)}",
            "",
        ]

    def _build_context_section(
        self,
        results: List[Tuple[Document, float]],
        include_confidence: bool,
    ) -> List[str]:
        """Build context section with document excerpts.

        Args:
            results: Search results
            include_confidence: Whether to include confidence scores

        Returns:
            List of context section lines
        """
        output_parts = ["## Retrieved Context", ""]

        for i, (doc, score) in enumerate(results, 1):
            # Format chunk reference
            chunk_ref = self._format_chunk_reference(doc.metadata, i)

            # Add content with reference
            output_parts.append(f"{chunk_ref} {doc.page_content.strip()}")

            # Add confidence if requested
            if include_confidence and score < 1.0:
                confidence_pct = format_confidence_score(score, as_percentage=True)
                output_parts.append(f"   *Confidence: {confidence_pct}*")

            output_parts.append("")  # Blank line between results

        return output_parts

    def _format_chunk_reference(self, metadata: dict, index: int) -> str:
        """Format chunk reference marker.

        Args:
            metadata: Document metadata
            index: Result index

        Returns:
            Formatted reference marker (e.g., "[1]" or "[1.5]")
        """
        chunk_index = metadata.get("chunk_index", "")
        if chunk_index:
            return f"[{index}.{chunk_index}]"
        return f"[{index}]"

    def _build_references(
        self,
        results: List[Tuple[Document, float]],
        include_confidence: bool,
    ) -> List[str]:
        """Build references section.

        Args:
            results: Search results
            include_confidence: Whether to include confidence scores

        Returns:
            List of reference lines
        """
        references = []

        for i, (doc, score) in enumerate(results, 1):
            metadata = doc.metadata
            ref_parts = [f"[{i}] {extract_document_name(metadata)}"]

            # Add page information
            page_info = format_page_info_structured(metadata)
            if page_info:
                ref_parts.append(page_info)

            # Add chunk information
            chunk_index = metadata.get("chunk_index", "")
            if chunk_index:
                ref_parts.append(f"Chunk {chunk_index}")

            # Add confidence score
            if include_confidence:
                ref_parts.append(f"Score: {score:.3f}")

            # Add a stable, PAT-authenticated document access URL. Prefer the
            # PAT view endpoint (skips OAuth2-Proxy, validated by the
            # caller's PAT (sent as a Bearer token), built from document_id so we never leak
            # short-lived blob SAS URLs into references. Fall back to any
            # explicit file_url only when document_id is unavailable.
            document_id = metadata.get("document_id")
            if document_id:
                ref_parts.append(f"URL: /api/pat/documents/{document_id}/view")
            else:
                file_url = metadata.get("file_url")
                if file_url:
                    ref_parts.append(f"URL: {file_url}")

            references.append(", ".join(ref_parts))

        return references

    def _build_quality_summary(
        self, results: List[Tuple[Document, float]]
    ) -> List[str]:
        """Build search quality summary section.

        Args:
            results: Search results

        Returns:
            List of quality summary lines
        """
        stats = calculate_search_statistics(results)

        summary = [
            "",
            "## Search Quality",
            f"- Average Confidence: {format_confidence_score(stats['avg_confidence'])}",
            f"- Best Match Score: {format_confidence_score(stats['best_match'])}",
        ]

        if len(results) > 1:
            summary.append(
                f"- Lowest Match Score: {format_confidence_score(stats['lowest_match'])}"
            )

        return summary
