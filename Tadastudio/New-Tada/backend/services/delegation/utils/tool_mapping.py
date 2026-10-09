"""Tool node mapping utilities for delegation.

This module provides utilities for building mappings between tool names
and their corresponding node IDs, enabling sub-agents to resolve tools.
"""

from typing import Dict, Set

from backend.models.workflow import EnhancedNodeData, GraphData, NodeType
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name

logger = get_logger("delegation.tool_mapping")


def build_tool_node_mapping(
    graph: GraphData,
    agent_node_id: str,
) -> Dict[str, Dict[str, str]]:
    """Build tool node mapping for a sub-agent.

    This function creates a mapping of tool names to their node information,
    allowing sub-agents to resolve which node a tool corresponds to.

    Args:
        graph: The graph data containing nodes and connections
        agent_node_id: The agent node ID to build mapping for

    Returns:
        Dictionary mapping tool names to node information
    """
    tool_node_mapping = {}
    used_names: Set[str] = set()

    # Get tool nodes connected to this agent
    tool_nodes = graph.get_tool_nodes_for_agent(agent_node_id)
    logger.info(
        f"Building tool mapping for agent {agent_node_id}: "
        f"found {len(tool_nodes)} tool nodes"
    )

    for tool_node in tool_nodes:
        _map_tool_node(tool_node, tool_node_mapping, used_names)

    if tool_node_mapping:
        logger.debug(f"Built tool node mapping: {tool_node_mapping}")
    else:
        logger.warning(f"No tool node mapping available for agent {agent_node_id}")

    return tool_node_mapping


def _map_tool_node(
    tool_node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map a single tool node to the mapping dictionary.

    Args:
        tool_node: The tool node to map
        mapping: The mapping dictionary to update (modified in place)
        used_names: Set of already-used tool names for collision detection
    """
    if tool_node.type == NodeType.WEB_SEARCH and tool_node.web_search_config:
        _map_web_search_node(tool_node, mapping, used_names)
    elif (
        tool_node.type == NodeType.DOCUMENT_SEARCH and tool_node.document_search_config
    ):
        _map_document_search_node(tool_node, mapping, used_names)
    elif tool_node.type == NodeType.DATABASE_QUERY and tool_node.database_query_config:
        _map_database_query_node(tool_node, mapping, used_names)
    elif tool_node.type == NodeType.HTTP_REQUEST and tool_node.http_request_config:
        _map_http_request_node(tool_node, mapping, used_names)
    elif (
        tool_node.type == NodeType.EMAIL_SEND_TOOL and tool_node.email_send_tool_config
    ):
        _map_email_send_node(tool_node, mapping, used_names)
    elif tool_node.type == NodeType.FILE_WRITE and tool_node.file_write_config:
        _map_file_write_node(tool_node, mapping, used_names)
    elif tool_node.type == NodeType.DOCUMENT_RETRIEVE and tool_node.document_retrieve_config:
        _map_document_retrieve_node(tool_node, mapping, used_names)


def _map_web_search_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map a web search tool node.

    Args:
        node: The web search node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    # Use build_tool_name to match actual tool creation
    tool_name_key = build_tool_name(
        "web_search", node.name, node.uniq_id, used_names=used_names
    )
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.WEB_SEARCH,
    }

    mapping[tool_name_key] = node_info
    # Add base names for compatibility
    mapping["web_search"] = node_info
    mapping["search_web"] = node_info

    logger.debug(
        f"Mapped web search: {tool_name_key}, web_search, search_web "
        f"-> {node.uniq_id} ({node.name})"
    )


def _map_document_search_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map a document search tool node.

    Args:
        node: The document search node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    # Use build_tool_name to match actual tool creation
    tool_name_key = build_tool_name(
        "document_search", node.name, node.uniq_id, used_names=used_names
    )
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.DOCUMENT_SEARCH,
    }

    mapping[tool_name_key] = node_info
    # Add base names for compatibility
    mapping["document_search"] = node_info
    mapping["search_documents"] = node_info

    logger.debug(
        f"Mapped document search: {tool_name_key}, document_search, search_documents "
        f"-> {node.uniq_id} ({node.name})"
    )


def _map_document_retrieve_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map a document retrieve tool node.

    Args:
        node: The document retrieve node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    tool_name_key = build_tool_name("retrieve_document", node.name, node.uniq_id, used_names=used_names)
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.DOCUMENT_RETRIEVE,
    }

    mapping[tool_name_key] = node_info
    mapping["retrieve_document"] = node_info
    mapping["document_retrieve"] = node_info

    logger.debug(
        f"Mapped document retrieve: {tool_name_key}, retrieve_document, document_retrieve "
        f"-> {node.uniq_id} ({node.name})"
    )


def _map_database_query_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map a database query tool node.

    Args:
        node: The database query node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    # Use build_tool_name to match actual tool creation (prefix must match
    # creators/database_query.py which uses "database_query")
    tool_name_key = build_tool_name(
        "database_query", node.name, node.uniq_id, used_names=used_names
    )
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.DATABASE_QUERY,
    }

    mapping[tool_name_key] = node_info
    # Add base names for compatibility
    mapping["database_query"] = node_info
    mapping["query_db"] = node_info
    mapping["query_database"] = node_info

    logger.debug(
        f"Mapped database query: {tool_name_key}, database_query, query_db, query_database "
        f"-> {node.uniq_id} ({node.name})"
    )


def _map_http_request_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map an HTTP request tool node.

    Args:
        node: The HTTP request node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    # Use build_tool_name to match actual tool creation
    tool_name_key = build_tool_name(
        "http_request", node.name, node.uniq_id, used_names=used_names
    )
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.HTTP_REQUEST,
    }

    mapping[tool_name_key] = node_info
    # Add base name for compatibility
    mapping["http_request"] = node_info

    logger.debug(
        f"Mapped HTTP request: {tool_name_key}, http_request "
        f"-> {node.uniq_id} ({node.name})"
    )


def _map_email_send_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map an email send tool node.

    Args:
        node: The email send node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    # Use build_tool_name to match actual tool creation
    tool_name_key = build_tool_name(
        "email_send", node.name, node.uniq_id, used_names=used_names
    )
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.EMAIL_SEND_TOOL,
    }

    mapping[tool_name_key] = node_info
    # Add base names for compatibility
    mapping["email_send"] = node_info
    mapping["send_email"] = node_info

    logger.debug(
        f"Mapped email send: {tool_name_key}, email_send, send_email "
        f"-> {node.uniq_id} ({node.name})"
    )


def _map_file_write_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
    used_names: Set[str],
) -> None:
    """Map a file write tool node.

    Args:
        node: The file write node
        mapping: The mapping dictionary to update
        used_names: Set of already-used tool names for collision detection
    """
    # Use build_tool_name to match actual tool creation
    tool_name_key = build_tool_name(
        "file_write", node.name, node.uniq_id, used_names=used_names
    )
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.FILE_WRITE,
    }

    mapping[tool_name_key] = node_info
    # Add base names for compatibility
    mapping["file_write"] = node_info
    mapping["write_file"] = node_info

    logger.debug(
        f"Mapped file write: {tool_name_key}, file_write, write_file "
        f"-> {node.uniq_id} ({node.name})"
    )
