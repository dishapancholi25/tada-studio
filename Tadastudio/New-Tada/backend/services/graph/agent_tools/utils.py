"""Utility functions for agent tools.

This module provides common utilities used across agent tool creators.
"""

import re
from typing import Optional, Set

from backend.services.config import get_logger

logger = get_logger(__name__)


# Default node names that should trigger fallback to ID-based naming
DEFAULT_NODE_NAMES = {
    "Document Search",
    "Document Retrieve",
    "Web Search",
    "HTTP Request",
    "Database Query",
    "Email Send Tool",
    "Email Send",
    "File Write",
    "File Write Tool",
}


def sanitize_tool_name(name: str) -> str:
    """Convert a node name to a valid tool name.

    Tool names must be valid Python identifiers (lowercase, underscores, alphanumeric).

    Args:
        name: The human-readable node name (e.g., "Amex Fraud Hub API")

    Returns:
        Sanitized tool name (e.g., "amex_fraud_hub_api")

    Examples:
        >>> sanitize_tool_name("Amex Fraud Hub API")
        'amex_fraud_hub_api'
        >>> sanitize_tool_name("Customer Support Docs")
        'customer_support_docs'
        >>> sanitize_tool_name("API-v2 Endpoint")
        'api_v2_endpoint'
    """
    # Convert to lowercase
    result = name.lower()

    # Replace common separators with underscores
    result = re.sub(r"[-\s]+", "_", result)

    # Remove any character that isn't alphanumeric or underscore
    result = re.sub(r"[^a-z0-9_]", "", result)

    # Collapse multiple underscores
    result = re.sub(r"_+", "_", result)

    # Remove leading/trailing underscores
    result = result.strip("_")

    # Ensure it doesn't start with a number (prefix with underscore if so)
    if result and result[0].isdigit():
        result = "_" + result

    # Fallback if empty
    if not result:
        result = "tool"

    return result


def is_default_node_name(name: str) -> bool:
    """Check if a node name is a default/generic name.

    Args:
        name: The node name to check

    Returns:
        True if the name is a default node name, False otherwise
    """
    return name in DEFAULT_NODE_NAMES


def build_tool_name(
    tool_type_prefix: str,
    node_name: str,
    node_id: str,
    default_name: Optional[str] = None,
    used_names: Optional[Set[str]] = None,
) -> str:
    """Build a tool name from node information.

    Uses semantic naming (node name) when available, falls back to
    ID-based naming for default/generic node names.

    Detects and handles name collisions by appending a short node ID suffix.

    Args:
        tool_type_prefix: The tool type prefix (e.g., "document_search", "web_search")
        node_name: The human-readable node name
        node_id: The unique node ID
        default_name: Optional default name to check against (overrides DEFAULT_NODE_NAMES)
        used_names: Optional set to track used names and detect collisions.
                   If provided, will append node ID suffix on collision and
                   add the generated name to this set.

    Returns:
        Tool name in format "{prefix}_{sanitized_name}" or "{prefix}_{node_id[:8]}"
        If collision detected: "{prefix}_{sanitized_name}_{node_id[:6]}"

    Examples:
        >>> build_tool_name("document_search", "Amex Fraud Hub API", "f70424aa-...")
        'document_search_amex_fraud_hub_api'
        >>> build_tool_name("document_search", "Document Search", "f70424aa-...")
        'document_search_f70424aa'
        >>> used = set()
        >>> build_tool_name("http_request", "API v1", "abc123...", used_names=used)
        'http_request_api_v1'
        >>> build_tool_name("http_request", "API-v1", "def456...", used_names=used)
        'http_request_api_v1_def456'  # Collision detected, ID suffix added
    """
    # Check if using default name
    use_default = default_name and node_name == default_name
    use_default = use_default or is_default_node_name(node_name)

    if use_default or not node_name:
        # Fall back to ID-based naming
        sanitized = node_id[:8]  # Use ID as sanitized for collision handling
        tool_name = f"{tool_type_prefix}_{sanitized}"
    else:
        # Use semantic naming
        sanitized = sanitize_tool_name(node_name)
        tool_name = f"{tool_type_prefix}_{sanitized}"

    # Handle collision detection if tracking set provided
    if used_names is not None:
        if tool_name in used_names:
            # Collision detected - append short node ID suffix
            original_name = tool_name
            id_suffix = node_id[:6]
            tool_name = f"{tool_type_prefix}_{sanitized}_{id_suffix}"

            logger.warning(
                f"Tool name collision detected: '{original_name}' already exists. "
                f"Appending ID suffix to create unique name: '{tool_name}' "
                f"(node: '{node_name}', id: {node_id})"
            )

        # Add to tracking set
        used_names.add(tool_name)

    return tool_name
