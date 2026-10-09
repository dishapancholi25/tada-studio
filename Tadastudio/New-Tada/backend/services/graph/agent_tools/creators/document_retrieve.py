"""Document retrieve tool creator for agents.

This module creates document retrieve tool instances that agents can use
to fetch full document content from collections.
"""

from typing import Any, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def create_document_retrieve_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
    user_id: Optional[str] = None,
) -> Optional[Any]:
    """Create a document retrieve tool from a DOCUMENT_RETRIEVE node.

    Args:
        target_node: The DOCUMENT_RETRIEVE node configuration
        used_tool_names: Optional set to track used tool names for collision detection
        user_id: User ID for access control

    Returns:
        Document retrieve tool instance, or None if configuration is invalid
    """
    if not target_node.document_retrieve_config:
        logger.warning(f"Node {target_node.name} missing document_retrieve_config")
        return None

    logger.info(f"Creating document retrieve tool from node: {target_node.name}")

    from backend.tools.document_retrieve import create_document_retrieve_tool

    config = target_node.document_retrieve_config

    # Handle both dict and config object
    if isinstance(config, dict):
        collection_ids = config.get("collection_ids", [])
    else:
        collection_ids = config.collection_ids

    # Build semantic tool name
    tool_name = build_tool_name(
        tool_type_prefix="retrieve_document",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="Document Retrieve",
        used_names=used_tool_names,
    )

    # Build description prefix from node name
    description_prefix = None
    if target_node.name and target_node.name != "Document Retrieve":
        description_prefix = f"Retrieve documents from '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"

    tool = create_document_retrieve_tool(
        collection_ids=collection_ids,
        tool_name=tool_name,
        description_prefix=description_prefix,
        user_id=user_id,
    )

    logger.info(f"Created document retrieve tool: {tool_name}")
    return tool
