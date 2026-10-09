"""SSRF protection helper for MCP (Model Context Protocol) server connections.

Mirrors the SSRF guard used by the HTTP Request tool
(``backend/tools/http_request/handlers.py::_ssrf_validate_before_send``), but
uses its own admin-configurable tool id (``MCP_SERVER``) so MCP and
HTTP_REQUEST can have independent allow-lists while sharing the same
underlying validator and admin API (``/api/admin/ssrf-policies/{tool_id}``).
"""

import logging
from typing import Optional

from backend.models.workflow.configs.guardrails import ToolCallPolicy
from backend.services.guardrails.ssrf import validate_url
from backend.services.guardrails.ssrf_policy_service import get_effective_blocked_ranges

logger = logging.getLogger(__name__)

# Canonical tool identifier for MCP server connections (admin SSRF policy API).
MCP_SERVER_TOOL_ID = "MCP_SERVER"

BLOCKED_MESSAGE = "Blocked due to SSRF Policy"


def validate_mcp_server_url(url: str) -> Optional[str]:
    """Validate an MCP ``server_url`` before any outbound connection.

    The URL must match an entry in the admin-managed allow-list for the
    ``MCP_SERVER`` tool id (seeded from ``MCP_SERVER_ALLOWED_IPS`` on first
    use, then fully DB-managed). An empty allow-list fails closed.

    Returns:
        ``None`` if the URL is safe to use, otherwise the fixed error string
        ``"Blocked due to SSRF Policy"`` (detailed reason is logged, not
        surfaced to callers).
    """
    try:
        allowed_entries = get_effective_blocked_ranges(MCP_SERVER_TOOL_ID)
        policy = ToolCallPolicy(blocked_ip_ranges=allowed_entries)
    except Exception as exc:  # noqa: BLE001 - fail closed (empty allow-list)
        logger.warning(
            "[SSRF-MCP] Could not load allow-list, failing closed: %s",
            exc,
        )
        policy = ToolCallPolicy(blocked_ip_ranges=[])

    result = validate_url(url, policy)
    if not result.passed:
        reason = result.violations[0].message if result.violations else "SSRF check failed"
        logger.warning("[SSRF-MCP] Blocked outbound MCP request to %s: %s", url, reason)
        return BLOCKED_MESSAGE
    return None
