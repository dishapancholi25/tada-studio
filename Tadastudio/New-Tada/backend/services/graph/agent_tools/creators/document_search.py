"""Document search tool creator for agents.

This module creates document search tool instances that agents can use
to search through document collections.
"""

from typing import Any, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def create_document_search_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
    user_id: Optional[str] = None,
) -> Optional[Any]:
    """
    Create a document search tool from a DOCUMENT_SEARCH node.

    Args:
        target_node: The DOCUMENT_SEARCH node configuration
        used_tool_names: Optional set to track used tool names for collision detection

    Returns:
        Document search tool instance, or None if configuration is invalid

    Raises:
        ImportError: If document search tool module is not available
    """
    if not target_node.document_search_config:
        logger.warning(f"Node {target_node.name} missing document_search_config")
        return None

    logger.info(f"Creating document search tool from node: {target_node.name}")

    from backend.tools.document_search import create_document_search_tool

    doc_config = target_node.document_search_config

    # Handle both dict and DocumentSearchConfig object
    if isinstance(doc_config, dict):
        # Extract values from dict
        collection_names = doc_config.get("document_collections", [])
        document_ids = doc_config.get("document_ids", [])
        search_k = doc_config.get("search_k", 4)
        search_type = doc_config.get("search_type", "similarity")
        similarity_threshold = doc_config.get("similarity_threshold", 0.5)
        include_metadata = doc_config.get("include_metadata", True)
        citation_format = doc_config.get("citation_format", "inline")
        hybrid_search_enabled = doc_config.get("hybrid_search_enabled", False)
        search_mode = doc_config.get("search_mode", "vector")
        keyword_weight = doc_config.get("keyword_weight", 0.3)
        rrf_k = doc_config.get("rrf_k", 60)
        text_config = doc_config.get("full_text_config", None)
        return_full_document = doc_config.get("return_full_document", False)
    else:
        # Use object attributes
        collection_names = doc_config.document_collections
        document_ids = doc_config.document_ids
        search_k = doc_config.search_k
        search_type = doc_config.search_type
        similarity_threshold = doc_config.similarity_threshold
        include_metadata = doc_config.include_metadata
        citation_format = doc_config.citation_format
        hybrid_search_enabled = doc_config.hybrid_search_enabled
        search_mode = doc_config.search_mode
        keyword_weight = doc_config.keyword_weight
        rrf_k = doc_config.rrf_k
        text_config = doc_config.full_text_config
        return_full_document = doc_config.return_full_document

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="document_search",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="Document Search",
        used_names=used_tool_names,
    )

    # Build description prefix from node name if not default
    description_prefix = None
    if target_node.name and target_node.name != "Document Search":
        description_prefix = f"Search '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"

    doc_search_tool = create_document_search_tool(
        collection_names=collection_names,
        document_ids=document_ids,
        search_k=search_k,
        search_type=search_type,
        similarity_threshold=similarity_threshold,
        include_metadata=include_metadata,
        citation_format=citation_format,
        hybrid_search_enabled=hybrid_search_enabled,
        search_mode=search_mode,
        keyword_weight=keyword_weight,
        rrf_k=rrf_k,
        text_config=text_config,
        return_full_document=return_full_document,
        tool_name=tool_name,
        description_prefix=description_prefix,
        user_id=user_id,
    )

    logger.info(f"Created document search tool: {tool_name}")
    return doc_search_tool


def create_legacy_document_search_tool(agent_config: Any) -> Optional[Any]:
    """
    Create document search tool from legacy agent config (backward compatibility).

    Args:
        agent_config: Agent configuration with document_search_enabled

    Returns:
        Document search tool instance, or None if not enabled/configured

    Raises:
        ImportError: If document search tool module is not available
    """
    if (
        not hasattr(agent_config, "document_search_enabled")
        or not agent_config.document_search_enabled
    ):
        return None

    logger.info("Creating document search tool from legacy agent config")

    from backend.tools.document_search import create_document_search_tool

    # Get document search configuration
    collections = getattr(agent_config, "document_collections", [])
    document_ids = getattr(agent_config, "document_ids", [])
    search_k = getattr(agent_config, "search_k", 4)
    search_type = getattr(agent_config, "search_type", "similarity")
    similarity_threshold = getattr(agent_config, "similarity_threshold", 0.5)
    include_metadata = getattr(agent_config, "include_metadata", True)
    citation_format = getattr(agent_config, "citation_format", "inline")

    # Hybrid search configuration
    hybrid_search_enabled = getattr(agent_config, "hybrid_search_enabled", False)
    search_mode = getattr(agent_config, "search_mode", "vector")
    keyword_weight = getattr(agent_config, "keyword_weight", 0.3)
    rrf_k = getattr(agent_config, "rrf_k", 60)
    full_text_config = getattr(agent_config, "full_text_config", "english")

    if not collections and not document_ids:
        logger.warning(
            "Document search enabled but no collections or documents specified"
        )
        return None

    logger.info(
        f"Creating document search tool for collections: {collections}, documents: {document_ids}"
    )
    logger.info(f"Hybrid search enabled: {hybrid_search_enabled}, mode: {search_mode}")

    doc_search_tool = create_document_search_tool(
        collection_names=collections,
        document_ids=document_ids,
        search_k=search_k,
        search_type=search_type,
        similarity_threshold=similarity_threshold,
        include_metadata=include_metadata,
        citation_format=citation_format,
        hybrid_search_enabled=hybrid_search_enabled,
        search_mode=search_mode,
        keyword_weight=keyword_weight,
        rrf_k=rrf_k,
        text_config=full_text_config,
    )

    logger.info("Legacy document search tool created successfully")
    return doc_search_tool
