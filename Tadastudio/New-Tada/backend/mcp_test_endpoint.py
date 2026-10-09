"""
MCP diagnostic endpoints for testing MCP server connections.

These routes allow engineers to verify that MCP servers are accessible
from the backend and to surface useful environment metadata.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth.dependencies import require_active_user
from backend.tools.mcp_adapter_tool import create_mcp_adapter_tool


logger = logging.getLogger(__name__)

# Create router
mcp_test_router = APIRouter(
    prefix="/api/mcp-test",
    tags=["mcp-test"],
    dependencies=[Depends(require_active_user)],
)


@mcp_test_router.get("/environment-info")
async def get_environment_info() -> Dict[str, Any]:
    """Expose environment details useful for debugging MCP connections."""
    info = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "environment_type": "cloud"
        if any(
            [
                os.path.exists("/.dockerenv"),
                os.getenv("WEBSITE_INSTANCE_ID"),
            ]
        )
        else "local",
        "docker_env": os.path.exists("/.dockerenv"),
        "azure_app_service": bool(os.getenv("WEBSITE_INSTANCE_ID")),
    }

    logger.debug("Environment info payload", extra=info)
    return info


def _summarise_discovery(discovery_result: Any) -> Dict[str, Any]:
    """Normalise the discovery payload to something easier to read."""
    summary: Dict[str, Any] = {"raw": discovery_result}
    try:
        if isinstance(discovery_result, str):
            summary["parsed"] = json.loads(discovery_result)
        elif isinstance(discovery_result, dict):
            summary["parsed"] = discovery_result
    except json.JSONDecodeError:
        summary["parsed"] = "unparseable-json"
    return summary


@mcp_test_router.post("/test-connection")
async def test_mcp_connection(
    server_name: str = "Test MCP Server",
    connection_type: str = "http",
    server_url: str = "",
    auth_type: str = "none",
) -> Dict[str, Any]:
    """Test connection to an MCP server."""
    if not server_url:
        raise HTTPException(status_code=400, detail="server_url is required")

    try:
        logger.info(
            "Testing MCP connection",
            extra={
                "server_name": server_name,
                "connection_type": connection_type,
                "server_url": server_url,
                "auth_type": auth_type,
            },
        )

        config = {
            "server_name": server_name,
            "connection_type": connection_type,
            "server_url": server_url,
            "auth_type": auth_type,
            "auth_config": {},
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "node_id": "mcp_test_probe",
            "node_name": "MCP Test Probe",
        }

        mcp_tool = create_mcp_adapter_tool(**config)

        discovery_result = mcp_tool.invoke("discover")
        logger.debug(
            "Discovery result",
            extra={"summary": _summarise_discovery(discovery_result)},
        )

        tools_list = mcp_tool.invoke("list_tools")
        logger.info(
            "Retrieved MCP tools",
            extra={
                "tool_count": len(tools_list)
                if isinstance(tools_list, list)
                else "unknown"
            },
        )

        return {
            "status": "success",
            "connection_type": connection_type,
            "server_url": server_url,
            "tools": tools_list,
            "discovery": _summarise_discovery(discovery_result),
        }

    except Exception as exc:
        logger.exception("Failed to connect to MCP server")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to MCP server. Check server logs for details.",
        ) from exc
