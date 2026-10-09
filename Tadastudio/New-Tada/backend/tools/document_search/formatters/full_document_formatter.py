"""Full document formatter for retrieving complete documents."""

import logging
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class FullDocumentFormatter:
    """Formats full document content from chunks."""

    @staticmethod
    def format(
        chunks: List[Dict[str, Any]],
        document_id: str,
        citation_format: str = "structured",
    ) -> str:
        """Format full document from chunks.

        Args:
            chunks: List of document chunks with content and metadata
            document_id: Document ID
            citation_format: How to format the output

        Returns:
            Formatted full document string
        """
        if not chunks:
            return "No content found for the specified document."

        # Get document metadata from first chunk
        doc_name = (
            chunks[0]["metadata"].get("document_name", "Unknown")
            if chunks
            else "Unknown"
        )
        total_chunks = len(chunks)

        # Combine all chunk contents
        full_content = "\n\n".join(chunk["content"] for chunk in chunks)

        # Format based on citation format
        if citation_format == "structured":
            return FullDocumentFormatter._format_structured(
                full_content,
                doc_name,
                document_id,
                total_chunks,
                chunks,
            )

        # Simple format
        return FullDocumentFormatter._format_simple(
            full_content,
            doc_name,
            total_chunks,
        )

    @staticmethod
    def _format_structured(
        content: str,
        doc_name: str,
        document_id: str,
        total_chunks: int,
        chunks: List[Dict[str, Any]],
    ) -> str:
        """Format document in structured style.

        Args:
            content: Full document content
            doc_name: Document name
            document_id: Document ID
            total_chunks: Number of chunks
            chunks: Chunk data for metadata extraction

        Returns:
            Structured formatted string
        """
        output_parts = [
            "## Full Document Content",
            f"**Document:** {doc_name}",
            f"**Total Chunks:** {total_chunks}",
            "",
            "## Content",
            content,
            "",
            "## Document Information",
            f"- Document: {doc_name}",
            f"- Document ID: {document_id}",
            f"- Number of chunks: {total_chunks}",
        ]

        # Add file type if available
        if chunks and "file_type" in chunks[0]["metadata"]:
            output_parts.append(f"- File type: {chunks[0]['metadata']['file_type']}")

        return "\n".join(output_parts)

    @staticmethod
    def _format_simple(
        content: str,
        doc_name: str,
        total_chunks: int,
    ) -> str:
        """Format document in simple style.

        Args:
            content: Full document content
            doc_name: Document name
            total_chunks: Number of chunks

        Returns:
            Simple formatted string
        """
        header = f"=== Full Document: {doc_name} ===\n\n"
        footer = f"\n\n=== End of Document ({total_chunks} chunks) ==="
        return header + content + footer
