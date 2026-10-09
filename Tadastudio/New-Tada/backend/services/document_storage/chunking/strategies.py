"""Chunking strategies for document processing."""

import logging
from typing import Dict, List, Tuple

from langchain_core.documents import Document

from ...text_splitting import TextSplitterFactory
from ..exceptions import ChunkingError
from .page_tracker import PageBoundaryTracker


logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking documents with page tracking support."""

    @staticmethod
    def chunk_documents(
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        strategy: str = "recursive",
    ) -> Tuple[List[Document], Dict]:
        """Chunk documents with optional page tracking.

        Args:
            documents: List of Document objects to chunk
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            strategy: Chunking strategy ('recursive', 'character', 'auto', 'whole_page', etc.)

        Returns:
            Tuple of (chunks, metadata)
                - chunks: List of chunked Document objects
                - metadata: Dictionary with chunking statistics

        Raises:
            ChunkingError: If chunking fails
        """
        try:
            # Handle whole_page strategy - keep pages intact without splitting
            if strategy == "whole_page":
                return ChunkingService._chunk_whole_page(documents)

            # Check if we have multi-page document with page metadata
            has_pages = all(
                hasattr(doc, "metadata") and "page" in doc.metadata for doc in documents
            )

            if has_pages and len(documents) > 1:
                # Multi-page document: combine pages and track boundaries
                logger.info(
                    "[CHUNKING] Using page-aware chunking for multi-page document"
                )
                chunks = ChunkingService._chunk_with_page_tracking(
                    documents, chunk_size, chunk_overlap, strategy
                )
            else:
                # Single document or no page metadata: use standard splitting
                logger.info(
                    "[CHUNKING] Using standard chunking (single page or no page metadata)"
                )
                chunks = ChunkingService._chunk_standard(
                    documents, chunk_size, chunk_overlap, strategy
                )

            metadata = {
                "chunk_count": len(chunks),
                "total_characters": sum(len(chunk.page_content) for chunk in chunks),
                "chunking_strategy": strategy,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "has_page_tracking": has_pages and len(documents) > 1,
            }

            return chunks, metadata

        except Exception as e:
            logger.error(f"[CHUNKING] Error chunking documents: {e}")
            raise ChunkingError(f"Failed to chunk documents: {str(e)}")

    @staticmethod
    def _chunk_with_page_tracking(
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        strategy: str,
    ) -> List[Document]:
        """Chunk documents while tracking which pages each chunk spans.

        Args:
            documents: List of Document objects (one per page)
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks
            strategy: Chunking strategy

        Returns:
            List of chunked Documents with page tracking metadata
        """
        # Build page boundary tracker
        tracker = PageBoundaryTracker(documents)
        full_text = tracker.get_full_text()

        # Split the continuous text
        text_splitter = TextSplitterFactory.create_splitter(
            strategy=strategy if strategy != "auto" else "recursive",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Split as text to get clean chunks
        text_chunks = text_splitter.split_text(full_text)

        # Create Document objects with page tracking
        chunks = []
        current_pos = 0  # Track position in full text

        for chunk_text in text_chunks:
            # Find where this chunk starts in the full text
            chunk_start = full_text.find(chunk_text, current_pos)
            if chunk_start == -1:
                # Fallback for overlapping chunks
                chunk_start = full_text.find(chunk_text)
            current_pos = chunk_start + 1  # Move past this occurrence

            # Get page metadata for this chunk
            chunk_metadata = tracker.assign_chunk_to_pages(chunk_text, chunk_start)

            # Rebuild the chunk text with explicit page boundary markers so each
            # page's content is clearly delimited within the chunk
            chunk_text = tracker.build_chunk_text_with_page_markers(
                chunk_text, chunk_start
            )

            # Create Document object
            chunk_doc = Document(page_content=chunk_text, metadata=chunk_metadata)
            chunks.append(chunk_doc)

        # Log statistics
        tracker.log_statistics(chunks)

        return chunks

    @staticmethod
    def _chunk_standard(
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        strategy: str,
    ) -> List[Document]:
        """Standard chunking without page tracking.

        Args:
            documents: List of Document objects
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks
            strategy: Chunking strategy

        Returns:
            List of chunked Documents
        """
        text_splitter = TextSplitterFactory.create_splitter(
            strategy=strategy if strategy != "auto" else "recursive",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunks = text_splitter.split_documents(documents)

        logger.info(
            f"[CHUNKING] Created {len(chunks)} chunks using {strategy} strategy"
        )

        return chunks

    @staticmethod
    def _chunk_whole_page(documents: List[Document]) -> Tuple[List[Document], Dict]:
        """Keep each page as a single chunk without splitting.

        This strategy preserves entire pages as individual chunks,
        which is useful for documents where page context is important.

        Args:
            documents: List of Document objects (typically one per page)

        Returns:
            Tuple of (chunks, metadata)
        """
        chunks = []

        for i, doc in enumerate(documents):
            # Preserve all existing metadata and add chunk-specific info
            chunk_metadata = doc.metadata.copy() if hasattr(doc, "metadata") else {}
            chunk_metadata["chunk_type"] = "whole_page"
            chunk_metadata["chunk_index"] = i

            # Ensure page number is set
            if "page" not in chunk_metadata:
                chunk_metadata["page"] = i

            chunks.append(
                Document(page_content=doc.page_content, metadata=chunk_metadata)
            )

        total_chars = sum(len(chunk.page_content) for chunk in chunks)
        avg_chunk_size = total_chars // len(chunks) if chunks else 0

        metadata = {
            "chunk_count": len(chunks),
            "total_characters": total_chars,
            "avg_chunk_size": avg_chunk_size,
            "chunking_strategy": "whole_page",
            "chunk_size": None,
            "chunk_overlap": 0,
            "has_page_tracking": True,
        }

        logger.info(
            f"[CHUNKING] Created {len(chunks)} whole-page chunks "
            f"(avg size: {avg_chunk_size} chars)"
        )

        return chunks, metadata
