"""
Tool type mapping utilities for determining node types from tool names.

This module provides functions to map tool names to their corresponding
NodeType values, handling synthetic tool names and common patterns.
"""

from backend.services.config import get_logger


mapper_logger = get_logger("common.tool_mapper")

# Tool name patterns for common tool types
TOOL_TYPE_PATTERNS = {
    "DATABASE_QUERY": ["query_database", "database", "query_db"],
    "WEB_SEARCH": ["search_web", "web_search"],
    "DOCUMENT_SEARCH": ["search_documents", "document_search"],
    "HTTP_REQUEST": ["http_request", "api_call"],
    "DOCUMENT_RETRIEVE": ["retrieve_document", "document_retrieve"],
    "EMAIL_SEND_TOOL": ["email_send", "send_email"],
    "FILE_WRITE": ["file_write", "write_file"],
    "MCP_SERVER": ["mcp"],
}


def extract_base_tool_name(synthetic_tool_name: str) -> str:
    """
    Extract the base tool name from a synthetic tool name.

    Synthetic tool names often have UUID suffixes (e.g., "query_db_d252e908").
    This function removes the suffix and maps to the canonical tool name.

    Args:
        synthetic_tool_name: The synthetic tool name (possibly with UUID suffix)

    Returns:
        The base tool name without synthetic suffixes

    Examples:
        >>> extract_base_tool_name("query_db_d252e908")
        "query_database"
        >>> extract_base_tool_name("web_search_abc12345")
        "web_search"
        >>> extract_base_tool_name("simple_tool")
        "simple_tool"
    """
    if "_" not in synthetic_tool_name:
        return synthetic_tool_name

    parts = synthetic_tool_name.split("_")

    # Check if last part looks like a UUID suffix (8 hex chars)
    if len(parts) >= 3 and len(parts[-1]) == 8:
        if all(c in "0123456789abcdef" for c in parts[-1]):
            # Reconstruct base name based on known patterns
            if parts[0] == "query" and parts[1] == "db":
                return "query_database"
            elif parts[0] == "web" and parts[1] == "search":
                return "web_search"
            elif parts[0] == "document" and parts[1] == "search":
                return "document_search"
            elif parts[0] == "http" and parts[1] == "request":
                return "http_request"
            elif parts[0] == "retrieve" and parts[1] == "document":
                return "retrieve_document"
            elif parts[0] == "email" and parts[1] == "send":
                return "email_send"
            elif parts[0] == "send" and parts[1] == "email":
                return "send_email"
            elif parts[0] == "file" and parts[1] == "write":
                return "file_write"
            elif parts[0] == "write" and parts[1] == "file":
                return "write_file"
            else:
                # Generic case: remove UUID suffix
                return "_".join(parts[:-1])

    return synthetic_tool_name


def get_tool_node_type(tool_name: str) -> str:
    """
    Map a tool name to its corresponding NodeType.

    This function checks tool name patterns to determine the appropriate
    node type for database recording and visualization.

    Args:
        tool_name: The tool name (base or synthetic)

    Returns:
        The NodeType as a string (e.g., "DATABASE_QUERY", "WEB_SEARCH", "TOOL")

    Examples:
        >>> get_tool_node_type("query_database")
        "DATABASE_QUERY"
        >>> get_tool_node_type("web_search_abc12345")
        "WEB_SEARCH"
        >>> get_tool_node_type("custom_tool")
        "TOOL"
    """
    tool_name_lower = tool_name.lower()

    # Check each pattern group
    for node_type, patterns in TOOL_TYPE_PATTERNS.items():
        if any(pattern in tool_name_lower for pattern in patterns):
            mapper_logger.debug(f"Mapped tool '{tool_name}' to node type '{node_type}'")
            return node_type

    # Default fallback
    mapper_logger.debug(
        f"Tool '{tool_name}' did not match any pattern, using default 'TOOL'"
    )
    return "TOOL"
