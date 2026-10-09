"""Factory functions for creating document search tools."""

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.tools import StructuredTool, tool

from backend.services.document_storage.search_service import document_search_service
from backend.tools.shared.collection_inventory import build_collection_inventory
from .config import ToolDescriptionBuilder
from .handlers import execute_search
from .schemas import DocumentSearchArgs, DocumentSearchConfig


logger = logging.getLogger(__name__)


def create_document_search_tool(
    collection_names: Optional[List[str]] = None,
    document_ids: Optional[List[str]] = None,
    search_k: int = 6,
    search_type: str = "similarity",
    similarity_threshold: float = 0.5,
    include_metadata: bool = True,
    citation_format: str = "structured",
    hybrid_search_enabled: bool = True,
    search_mode: str = "hybrid",
    keyword_weight: float = 0.5,
    rrf_k: int = 60,
    text_config: str = "english",
    prompt_template: str = "structured",
    include_confidence_scores: bool = True,
    max_context_tokens: int = 2000,
    return_full_document: bool = False,
    tool_name: Optional[str] = None,
    description_prefix: Optional[str] = None,
    user_id: Optional[str] = None,
) -> StructuredTool:
    """Create a document search tool with specific configuration.

    Args:
        collection_names: List of collection IDs to search (searches all docs in collections)
        document_ids: List of specific document IDs to search
        search_k: Number of results to return
        search_type: Type of search (similarity, mmr, similarity_score_threshold)
        similarity_threshold: Minimum similarity score for results
        include_metadata: Whether to include metadata in results
        citation_format: How to format citations (inline, footnote, structured, none)
        hybrid_search_enabled: Whether to enable hybrid (vector + keyword) search
        search_mode: Search mode when hybrid is enabled (vector, keyword, hybrid)
        keyword_weight: Weight for keyword search in hybrid mode (0-1)
        rrf_k: Reciprocal Rank Fusion constant (typically 50-60)
        text_config: PostgreSQL text search configuration (english, simple, etc.)
        prompt_template: Template for formatting results (structured, etc.)
        include_confidence_scores: Whether to include confidence scores
        max_context_tokens: Maximum context tokens (not enforced yet)
        return_full_document: Return full document instead of chunks (single doc only)
        tool_name: Custom tool name (defaults to 'search_documents')
        description_prefix: Optional prefix for the tool description (e.g., "Search 'Amex API'")

    Returns:
        Configured StructuredTool for document search
    """
    # Ensure at least one source is specified (or empty for all docs)
    collection_names = collection_names or []
    document_ids = document_ids or []

    # Create configuration
    config = DocumentSearchConfig(
        collection_names=collection_names,
        document_ids=document_ids,
        search_k=search_k,
        search_type=search_type,
        similarity_threshold=similarity_threshold,
        include_metadata=include_metadata,
        citation_format=citation_format,
        prompt_template=prompt_template,
        include_confidence_scores=include_confidence_scores,
        max_context_tokens=max_context_tokens,
        hybrid_search_enabled=hybrid_search_enabled,
        search_mode=search_mode,
        keyword_weight=keyword_weight,
        rrf_k=rrf_k,
        text_config=text_config,
        return_full_document=return_full_document,
        tool_name=tool_name,
    )

    def search_documents_impl(query: str) -> str:
        """Search through configured documents and collections for relevant information.

        Args:
            query: The search query to find relevant documents

        Returns:
            Formatted string with relevant document excerpts and citations
        """
        return execute_search(query=query, config=config, user_id=user_id)

    # Build description with collection inventory
    description = ToolDescriptionBuilder.build_description(config)
    if description_prefix:
        description = f"{description_prefix}. {description}"

    # Inject available document inventory into description
    inventory = build_collection_inventory(
        collection_ids=collection_names,
        document_ids=document_ids,
    )
    if inventory:
        description += inventory

    # Generate tool name
    final_tool_name = tool_name or "search_documents"

    # Create the tool
    document_tool = StructuredTool(
        name=final_tool_name,
        description=description,
        func=search_documents_impl,
        args_schema=DocumentSearchArgs,
    )

    return document_tool


def create_document_qa_tool(
    collection_names: List[str],
    search_k: int = 4,
    search_type: str = "similarity",
) -> tool:
    """Create a document Q&A tool that can answer questions based on documents.

    Args:
        collection_names: List of collection IDs to search
        search_k: Number of results to retrieve
        search_type: Type of search (similarity, mmr)

    Returns:
        Configured tool for document Q&A
    """

    @tool
    def answer_from_documents(question: str) -> str:
        """Answer questions based on information found in documents.

        Args:
            question: The question to answer using document context

        Returns:
            An answer based on relevant documents, or indication that answer wasn't found
        """
        try:
            # Search for relevant documents using custom service
            if search_type == "similarity":
                results = document_search_service.search_multiple_collections(
                    collection_ids=collection_names,
                    query=question,
                    k=search_k,
                    search_type="similarity",
                    include_metadata=True,
                )
            else:
                # MMR not supported, use similarity
                logger.warning("MMR search not implemented, using similarity search")
                results = document_search_service.search_multiple_collections(
                    collection_ids=collection_names,
                    query=question,
                    k=search_k,
                    search_type="similarity",
                    include_metadata=True,
                )

            # Convert results to Document format
            documents = []
            for result in results:
                doc = Document(
                    page_content=result["content"],
                    metadata=result.get("metadata", {}),
                )
                documents.append(doc)

            if not documents:
                return "I couldn't find any relevant information in the documents to answer your question."

            # Compile context from documents
            context_parts = []
            sources = set()

            for doc in documents:
                context_parts.append(doc.page_content)
                source = doc.metadata.get(
                    "document_name", doc.metadata.get("source", "Unknown")
                )
                if source != "Unknown":
                    sources.add(source)

            # Format response with context
            context = "\n\n".join(context_parts)

            response = f"Based on the documents, here's what I found:\n\n{context}"

            if sources:
                response += f"\n\nSources: {', '.join(sorted(sources))}"

            return response

        except Exception as e:
            logger.error(f"Error in document Q&A: {str(e)}")
            return f"Error answering from documents: {str(e)}"

    # Update tool metadata
    answer_from_documents.name = "answer_from_documents"
    answer_from_documents.description = (
        f"Answer questions using information from {len(collection_names)} "
        f"document collection(s). Best for factual questions that can be "
        f"answered from the available documents."
    )

    return answer_from_documents
