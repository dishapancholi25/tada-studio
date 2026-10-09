"""Page boundary tracking for document chunking."""

import logging
from typing import Dict, List

from langchain_core.documents import Document


logger = logging.getLogger(__name__)


class PageBoundaryTracker:
    """Tracks page boundaries when chunking multi-page documents."""

    def __init__(self, documents: List[Document]):
        """Initialize tracker with document pages.

        Args:
            documents: List of Document objects (one per page)
        """
        self.documents = documents
        self.full_text = ""
        self.page_boundaries: List[int] = []
        self.page_metadata_list: List[Dict] = []
        self._build_boundaries()

    def _build_boundaries(self) -> None:
        """Build page boundary index and metadata list."""
        for doc in self.documents:
            self.page_boundaries.append(len(self.full_text))
            self.full_text += doc.page_content
            self.page_metadata_list.append(doc.metadata)

        # Add end boundary
        self.page_boundaries.append(len(self.full_text))

    def get_full_text(self) -> str:
        """Get combined full text of all pages.

        Returns:
            Full text from all document pages
        """
        return self.full_text

    def assign_chunk_to_pages(self, chunk_text: str, chunk_start: int) -> Dict:
        """Determine which pages a chunk spans and build metadata.

        Args:
            chunk_text: The chunk text content
            chunk_start: Starting position of chunk in full text

        Returns:
            Dictionary with page tracking metadata
        """
        chunk_end = chunk_start + len(chunk_text)
        pages_spanned = []
        page_labels = []
        page_overlaps = []  # Track overlap length per page to find dominant page

        # Find which pages this chunk overlaps
        for page_num in range(len(self.documents)):
            page_start = self.page_boundaries[page_num]
            page_end = self.page_boundaries[page_num + 1]

            # Check if chunk overlaps with this page
            if chunk_start < page_end and chunk_end > page_start:
                overlap_length = min(chunk_end, page_end) - max(chunk_start, page_start)
                pages_spanned.append(page_num)
                page_overlaps.append(overlap_length)
                page_label = self.page_metadata_list[page_num].get(
                    "page_label", str(page_num + 1)
                )
                if page_label not in page_labels:
                    page_labels.append(page_label)

        # Build metadata
        chunk_metadata = {}

        # Determine the dominant page (page contributing most characters to this chunk)
        if pages_spanned:
            dominant_idx = page_overlaps.index(max(page_overlaps))
            dominant_page_num = pages_spanned[dominant_idx]
            dominant_page_meta = self.page_metadata_list[dominant_page_num]

            # Copy metadata from dominant page (for common fields)
            chunk_metadata.update(dominant_page_meta)

        # Add page tracking metadata
        if len(pages_spanned) == 1:
            # Single page chunk
            chunk_metadata["page"] = pages_spanned[0]
            chunk_metadata["page_label"] = (
                page_labels[0] if page_labels else str(pages_spanned[0] + 1)
            )
            chunk_metadata["page_range"] = chunk_metadata["page_label"]
        else:
            # Multi-page chunk — use dominant page for primary label/metadata
            chunk_metadata["pages"] = pages_spanned
            chunk_metadata["page"] = dominant_page_num  # Dominant page (most content)
            chunk_metadata["page_start"] = pages_spanned[0]
            chunk_metadata["page_end"] = pages_spanned[-1]
            chunk_metadata["page_label"] = dominant_page_meta.get(
                "page_label", str(dominant_page_num + 1)
            )
            chunk_metadata["spans_pages"] = True
            chunk_metadata["page_range"] = f"{page_labels[0]}-{page_labels[-1]}"

        return chunk_metadata

    def build_chunk_text_with_page_markers(
        self, chunk_text: str, chunk_start: int
    ) -> str:
        """Construct chunk text with explicit page boundary markers.

        Inserts a ``Page N starts here`` marker at the position where each
        page's content begins within the chunk, so the boundaries between
        pages are explicitly preserved in the text.

        Args:
            chunk_text: The original chunk text content
            chunk_start: Starting character position of the chunk in the full text

        Returns:
            Chunk text with page boundary markers inserted
        """
        chunk_end = chunk_start + len(chunk_text)

        # Collect (relative_position_in_chunk, page_label) for each page in the chunk
        markers: List[tuple] = []
        for page_num in range(len(self.documents)):
            page_begin = self.page_boundaries[page_num]
            page_finish = self.page_boundaries[page_num + 1]

            # Skip pages that don't overlap the chunk
            if page_begin >= chunk_end or page_finish <= chunk_start:
                continue

            page_label = self.page_metadata_list[page_num].get(
                "page_label", str(page_num + 1)
            )
            # Position where this page's content starts within the chunk (clamped to 0)
            relative_pos = max(0, page_begin - chunk_start)
            markers.append((relative_pos, page_label))

        if not markers:
            return chunk_text

        markers.sort(key=lambda x: x[0])

        # Build the new text, inserting markers at the recorded positions
        result_parts: List[str] = []
        prev = 0
        for pos, label in markers:
            result_parts.append(chunk_text[prev:pos])
            prefix = "" if pos == 0 else "\n\n"
            result_parts.append(f"{prefix}Page {label} starts here\n\n")
            prev = pos
        result_parts.append(chunk_text[prev:])

        return "".join(result_parts)

    def log_statistics(self, chunks: List[Document]) -> None:
        """Log statistics about page spanning.

        Args:
            chunks: List of chunk Documents
        """
        logger.info(
            f"[PAGE-TRACKER] Created {len(chunks)} chunks from {len(self.documents)} pages"
        )

        single_page_chunks = sum(
            1 for c in chunks if not c.metadata.get("spans_pages", False)
        )
        multi_page_chunks = len(chunks) - single_page_chunks

        if multi_page_chunks > 0:
            logger.info(
                f"[PAGE-TRACKER] {single_page_chunks} single-page chunks, "
                f"{multi_page_chunks} multi-page chunks"
            )
