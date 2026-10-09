"""Shared utilities for async agent execution.

This module provides common utility functions used across different
async agent execution components.
"""

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage


def extract_response_content(response: Any, default: str = "") -> str:
    """Extract string content from various response types.

    Handles different response formats from LLM execution including
    AIMessage objects, dictionaries, and plain strings.

    Args:
        response: LLM response in various formats
        default: Default value if content cannot be extracted

    Returns:
        Extracted string content or default value
    """
    if isinstance(response, AIMessage):
        return response.content if hasattr(response, "content") else default
    elif isinstance(response, dict):
        return response.get("content", default)
    elif isinstance(response, str):
        return response
    else:
        return str(response) if response else default


def safe_dict_get(
    data: Optional[Dict[str, Any]], *keys: str, default: Any = None
) -> Any:
    """Safely navigate nested dictionary with multiple fallback keys.

    Args:
        data: Dictionary to navigate
        *keys: Sequence of keys to try in order
        default: Default value if none of the keys exist

    Returns:
        Value from first found key or default

    Example:
        >>> d = {"a": {"b": 1}}
        >>> safe_dict_get(d, "a", "b")  # Returns {"b": 1}
        >>> safe_dict_get(d["a"], "b", "c", default=0)  # Returns 1
        >>> safe_dict_get(d, "x", "y", default=0)  # Returns 0
    """
    if data is None:
        return default

    for key in keys:
        if key in data:
            return data[key]

    return default


def is_http_request_tool(tool_name: str) -> bool:
    """Check if a tool name indicates an HTTP request tool.

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if this is an HTTP request tool, False otherwise
    """
    return tool_name.startswith("http_request") if tool_name else False


def extract_node_id_from_tool_name(
    tool_name: str, prefix: str = "http_request_"
) -> Optional[str]:
    """Extract node ID from tool name.

    Many tools encode the node ID in their name (e.g., "http_request_node123").
    This function extracts that ID.

    Args:
        tool_name: Tool name that may contain node ID
        prefix: Prefix to remove to get node ID

    Returns:
        Extracted node ID or None if no match
    """
    if not tool_name or not tool_name.startswith(prefix):
        return None
    return tool_name.replace(prefix, "")
