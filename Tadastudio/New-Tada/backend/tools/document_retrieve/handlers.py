"""Handler functions for document retrieve tool execution."""

import logging
from typing import List, Optional

from backend.services.document_storage.search_service import get_document_search_service
from backend.services.document_storage.storage.repository import DocumentRepository

logger = logging.getLogger(__name__)


def execute_retrieve(
    document_id: Optional[str],
    document_name: Optional[str],
    page_range: Optional[str],
    collection_ids: List[str],
    user_id: Optional[str] = None,
) -> str:
    """Retrieve full document content from a collection.

    Args:
        document_id: Specific document UUID
        document_name: Document name for fuzzy matching
        page_range: Page range string like "1-5"
        collection_ids: Allowed collection IDs
        user_id: User ID for access control

    Returns:
        Full document content as string
    """
    if not document_id and not document_name:
        return "Error: Either document_id or document_name must be provided."

    try:
        # Resolve document by name if needed
        if not document_id and document_name:
            document_id = _resolve_document_by_name(document_name, collection_ids)
            if not document_id:
                return f"Error: No document found matching name '{document_name}' in the configured collections."

        # Get document info
        doc_info = DocumentRepository.get_document(document_id)
        if not doc_info:
            return f"Error: Document with ID '{document_id}' not found."

        # Verify document is in an allowed collection
        if collection_ids and doc_info.collection_id not in collection_ids:
            return f"Error: Document '{doc_info.name}' is not in the configured collections."

        # Get full document content
        content = _get_document_content(document_id, page_range)
        if not content:
            return f"Error: No content found for document '{doc_info.name}'."

        return content

    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        return f"Error retrieving document: {str(e)}"


def _resolve_document_by_name(name: str, collection_ids: List[str]) -> Optional[str]:
    """Find a document by name within allowed collections."""
    try:
        for collection_id in collection_ids:
            documents = DocumentRepository.get_documents(
                collection_id=collection_id,
                status="processed",
            )
            # Exact match first
            for doc in documents:
                if doc.name.lower() == name.lower():
                    return doc.id
            # Partial match
            for doc in documents:
                if name.lower() in doc.name.lower():
                    return doc.id
        return None
    except Exception as e:
        logger.error(f"Error resolving document by name: {e}")
        return None


def _get_document_content(document_id: str, page_range: Optional[str] = None) -> str:
    """Get full document content, optionally filtered by page range."""
    search_service = get_document_search_service()
    chunks = search_service.get_all_chunks_for_document(document_id, include_metadata=True)

    if not chunks:
        return ""

    if page_range:
        chunks = _filter_chunks_by_page(chunks, page_range)

    return "\n\n".join(chunk["content"] for chunk in chunks if chunk.get("content"))


def _filter_chunks_by_page(chunks: list, page_range: str) -> list:
    """Filter chunks to only include those from specified pages."""
    try:
        pages = _parse_page_range(page_range)
        if not pages:
            return chunks

        filtered = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            chunk_page = metadata.get("page")
            page_span = metadata.get("page_span", [])

            if chunk_page is not None and chunk_page in pages:
                filtered.append(chunk)
            elif page_span:
                if any(p in pages for p in range(page_span[0], page_span[-1] + 1)):
                    filtered.append(chunk)

        return filtered if filtered else chunks
    except Exception:
        return chunks


def _parse_page_range(page_range: str) -> set:
    """Parse a page range string like '1-5' or '3' into a set of page numbers."""
    pages = set()
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start.strip()), int(end.strip()) + 1))
        else:
            pages.add(int(part))
    return pages
