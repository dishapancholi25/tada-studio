"""Utilities for preparing MCP configurations for execution."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional


def prepare_mcp_config_for_execution(
    config: Dict[str, Any],
    *,
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Return config ready for execution with node metadata applied.

    This function adds node_id and node_name to the config if not present,
    and logs the prepared configuration for debugging.

    Args:
        config: The MCP configuration dictionary
        node_id: Optional node ID to add to config
        node_name: Optional node name to add to config
        logger: Optional logger for debug output

    Returns:
        The prepared configuration dictionary
    """
    working = dict(config or {})

    if node_id:
        working.setdefault("node_id", node_id)
    if node_name:
        working.setdefault("node_name", node_name)

    # Remove deprecated sidecar flag if present
    working.pop("requires_sidecar", None)

    if logger:
        logger.info(
            "[MCP] Prepared config for execution node=%s server=%s connection=%s url=%s auth_type=%s",
            working.get("node_id"),
            working.get("server_name"),
            working.get("connection_type"),
            working.get("server_url"),
            working.get("auth_type", "none"),
        )

    return working
