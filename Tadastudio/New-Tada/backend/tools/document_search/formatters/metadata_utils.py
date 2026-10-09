"""Utility functions for extracting and formatting document metadata."""

import logging
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


def extract_document_name(metadata: Dict[str, Any]) -> str:
    """Extract document name from metadata.

    Args:
        metadata: Document metadata dictionary

    Returns:
        Document name or 'Unknown'
    """
    return metadata.get("document_name", metadata.get("source", "Unknown"))


def extract_page_info(metadata: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """Extract page information from metadata.

    Args:
        metadata: Document metadata dictionary

    Returns:
        Tuple of (page_label, page_number) where either may be None
    """
    page_label = metadata.get("page_label", metadata.get("page", ""))
    page_number = metadata.get("page")

    return page_label, page_number


def format_page_info_inline(metadata: Dict[str, Any]) -> str:
    """Format page information for inline citations.

    Args:
        metadata: Document metadata dictionary

    Returns:
        Formatted page info string (e.g., ", pages 1-3" or ", page 5")
    """
    # Handle multi-page spans
    if metadata.get("spans_pages", False):
        # Prefer page_range (e.g. "1-2") over page_label, which for multi-page
        # chunks only holds the dominant page's own single-number label.
        page_range = metadata.get("page_range", "")
        if page_range:
            return f", pages {page_range}"
        page_label = metadata.get("page_label", "")
        if page_label:
            return f", pages {page_label}"
        page_start = metadata.get("page_start", 0)
        page_end = metadata.get("page_end", page_start)
        return f", pages {page_start + 1}-{page_end + 1}"

    # Single page chunk
    page_label = metadata.get("page_label", "")
    page = metadata.get("page", "")

    if page_label:
        return f", page {page_label}"
    if page is not None and page != "":
        return f", page {page + 1}"
    return ""


def format_page_info_structured(metadata: Dict[str, Any]) -> str:
    """Format page information for structured output.

    Args:
        metadata: Document metadata dictionary

    Returns:
        Formatted page info string (e.g., "Page 5" or "Pages 1-3")
    """
    # Handle multi-page spans
    if metadata.get("spans_pages", False):
        # Prefer page_range (e.g. "1-2"), which reflects every page the chunk
        # actually overlaps. page_label only holds the *dominant* page's own
        # label (a single number) and would otherwise make a multi-page chunk
        # look like it came from just one page.
        page_range = metadata.get("page_range", "")
        if page_range:
            return f"Pages {page_range}"
        page_label = metadata.get("page_label", "")
        if page_label:
            return f"Pages {page_label}"
        page_start = metadata.get("page_start", 0)
        page_end = metadata.get("page_end", page_start)
        return f"Pages {page_start + 1}-{page_end + 1}"

    # Single page
    page_label, page = extract_page_info(metadata)
    if page_label and isinstance(page_label, str):
        return f"Page {page_label}"
    if isinstance(page, int):
        return f"Page {page + 1}"
    if page_label:
        return f"Page {page_label}"
    return ""


def format_confidence_score(score: float, as_percentage: bool = True) -> str:
    """Format confidence score.

    Args:
        score: Confidence score (0.0-1.0)
        as_percentage: Whether to format as percentage

    Returns:
        Formatted score string
    """
    if as_percentage:
        return f"{int(score * 100)}%"
    return f"{score:.2f}"


def build_citation_parts(
    metadata: Dict[str, Any],
    include_page: bool = True,
    include_chunk: bool = True,
) -> list:
    """Build citation parts list.

    Args:
        metadata: Document metadata dictionary
        include_page: Whether to include page information
        include_chunk: Whether to include chunk information

    Returns:
        List of citation parts
    """
    parts = []

    # Add document name
    doc_name = extract_document_name(metadata)
    parts.append(doc_name)

    # Add page information
    if include_page:
        page_info = format_page_info_structured(metadata)
        if page_info:
            parts.append(page_info)

    # Add chunk information
    if include_chunk:
        chunk_index = metadata.get("chunk_index", "")
        if chunk_index:
            parts.append(f"Chunk {chunk_index}")

    return parts


def calculate_search_statistics(
    results: list,
) -> Dict[str, Any]:
    """Calculate search quality statistics.

    Args:
        results: List of (Document, score) tuples

    Returns:
        Dictionary with statistics
    """
    if not results:
        return {
            "avg_confidence": 0,
            "best_match": 0,
            "lowest_match": 0,
            "result_count": 0,
        }

    scores = [score for _, score in results]
    return {
        "avg_confidence": sum(scores) / len(scores),
        "best_match": max(scores),
        "lowest_match": min(scores),
        "result_count": len(results),
    }
