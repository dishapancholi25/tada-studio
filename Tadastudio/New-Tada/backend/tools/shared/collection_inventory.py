"""Shared utility for building collection document inventory strings.

Used by document tools (search, retrieve) to inject available document
listings into tool descriptions so agents know what documents exist
without needing a separate discovery tool call.
"""

import logging
from typing import List, Optional

from backend.services.document_storage.storage.repository import DocumentRepository

logger = logging.getLogger(__name__)

# Maximum documents to include in the inventory to avoid bloating the tool description
MAX_INVENTORY_ITEMS = 50


def build_collection_inventory(
    collection_ids: Optional[List[str]] = None,
    document_ids: Optional[List[str]] = None,
    status_filter: str = "processed",
) -> str:
    """Build a formatted inventory of available documents.

    Queries the configured collections/documents and returns a formatted
    string listing what's available. This gets injected into tool
    descriptions so agents can reference documents by exact name/ID.

    Args:
        collection_ids: Collection IDs to list documents from
        document_ids: Specific document IDs (listed individually)
        status_filter: Only include documents with this status

    Returns:
        Formatted string listing available documents, or empty string
        if no documents found or an error occurs
    """
    if not collection_ids and not document_ids:
        return ""

    try:
        docs = []

        # Get documents from collections
        if collection_ids:
            for coll_id in collection_ids:
                coll_docs = DocumentRepository.get_documents(
                    collection_id=coll_id,
                    status=status_filter,
                )
                for doc in coll_docs:
                    docs.append(doc)
                    if len(docs) >= MAX_INVENTORY_ITEMS:
                        break
                if len(docs) >= MAX_INVENTORY_ITEMS:
                    break

        # Get specific documents by ID
        if document_ids:
            for doc_id in document_ids:
                doc = DocumentRepository.get_document(doc_id)
                if doc and (not status_filter or doc.status == status_filter):
                    docs.append(doc)

        if not docs:
            return ""

        # Build the inventory string
        lines = ["\n\nAvailable documents:"]
        for doc in docs[:MAX_INVENTORY_ITEMS]:
            size_str = _format_size(doc.file_size) if doc.file_size else "unknown size"
            lines.append(f'- "{doc.name}" (id: {doc.id}, {doc.file_type or "unknown"}, {size_str})')

        if len(docs) > MAX_INVENTORY_ITEMS:
            lines.append(f"  ... and {len(docs) - MAX_INVENTORY_ITEMS} more documents")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Failed to build collection inventory: {e}")
        return ""


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
