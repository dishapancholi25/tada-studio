"""Factory functions for creating document retrieve tools."""

import logging
from typing import List, Optional

from langchain_core.tools import StructuredTool

from backend.tools.shared.collection_inventory import build_collection_inventory

from .handlers import execute_retrieve
from .schemas import DocumentRetrieveArgs

logger = logging.getLogger(__name__)


def create_document_retrieve_tool(
    collection_ids: Optional[List[str]] = None,
    tool_name: Optional[str] = None,
    description_prefix: Optional[str] = None,
    user_id: Optional[str] = None,
) -> StructuredTool:
    """Create a document retrieve tool for fetching full document content.

    Args:
        collection_ids: List of collection IDs the agent can retrieve from
        tool_name: Custom tool name
        description_prefix: Optional prefix for the tool description
        user_id: User ID for access control

    Returns:
        Configured StructuredTool for document retrieval
    """
    collection_ids = collection_ids or []

    def retrieve_document_impl(
        document_id: Optional[str] = None,
        document_name: Optional[str] = None,
        page_range: Optional[str] = None,
    ) -> str:
        """Retrieve the full content of a document from a collection.

        Use this tool to get the complete text of a specific document.
        You can retrieve by document ID or by name.

        Args:
            document_id: Specific document UUID to retrieve
            document_name: Document name to search for (case-insensitive partial match)
            page_range: Page range for partial retrieval, e.g. '1-5' or '3'

        Returns:
            Full document content
        """
        return execute_retrieve(
            document_id=document_id,
            document_name=document_name,
            page_range=page_range,
            collection_ids=collection_ids,
            user_id=user_id,
        )

    # Build description with collection inventory
    description = (
        "Retrieve the full content of a document from a collection. "
        "Use this when you need to read, summarize, translate, or process "
        "an entire document (not just search for specific information). "
        "Provide either a document_id or document_name to identify which document to retrieve."
    )
    if description_prefix:
        description = f"{description_prefix}. {description}"

    # Inject available document inventory into description
    inventory = build_collection_inventory(collection_ids=collection_ids)
    if inventory:
        description += inventory

    final_tool_name = tool_name or "retrieve_document"

    return StructuredTool(
        name=final_tool_name,
        description=description,
        func=retrieve_document_impl,
        args_schema=DocumentRetrieveArgs,
    )
