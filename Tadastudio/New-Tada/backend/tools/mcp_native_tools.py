"""Native MCP tool loading using langchain-mcp-adapters.

Provides seamless integration of MCP servers as native LangChain tools.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool

from ..mcp_client_manager import mcp_client_manager
from .mcp_adapter_tool import _filter_tools, _HttpBridgeClient, _should_use_http_bridge


logger = logging.getLogger(__name__)


def _normalize_auth_config(config: Dict[str, Any]) -> None:
    """Normalize auth configuration, preserving OAuth for direct connections."""
    auth_type = (config.get("auth_type") or "none").lower()
    # Preserve OAuth config - it will be used for token injection during requests
    config["auth_type"] = auth_type


def _load_mcp_tools_with_fallback(config: Dict[str, Any]) -> List[BaseTool]:
    """Load MCP tools using the native client, falling back to the HTTP bridge when needed."""
    _normalize_auth_config(config)

    manual_client: Optional[_HttpBridgeClient] = None

    if _should_use_http_bridge(config):
        try:
            manual_client = _HttpBridgeClient(config)
        except Exception as exc:  # pragma: no cover - configuration errors
            logger.error(
                "[McpNativeTools] Failed to initialize HTTP bridge client: %s", exc
            )
            manual_client = None

    tools: List[BaseTool] = []
    native_error: Optional[Exception] = None

    logger.info(
        "[McpNativeTools] Loader context server=%s node=%s connection=%s url=%s auth_type=%s",
        config.get("server_name", "MCP Server"),
        config.get("node_id"),
        config.get("connection_type"),
        config.get("server_url"),
        config.get("auth_type", "none"),
    )

    try:
        tools = _load_mcp_tools_native(config)
    except Exception as exc:
        native_error = exc
        logger.warning(
            "[McpNativeTools] Native tool loading failed for %s: %s",
            config.get("server_name", "MCP Server"),
            exc,
        )

    if tools:
        return tools

    if manual_client:
        try:
            tools, _ = manual_client.discover_tools(config.get("tool_permissions", {}))
            logger.info(
                "[McpNativeTools] HTTP bridge returned %s tools for %s",
                len(tools),
                config.get("server_name", "MCP Server"),
            )
            if native_error:
                logger.info(
                    "[McpNativeTools] Using HTTP bridge tools after native failure for %s",
                    config.get("server_name", "MCP Server"),
                )
            return tools
        except Exception as exc:  # pragma: no cover - bridge failure
            logger.error(
                "[McpNativeTools] HTTP bridge tool discovery failed for %s: %s",
                config.get("server_name", "MCP Server"),
                exc,
            )
            # Fall through to empty list
    logger.warning(
        "[McpNativeTools] No MCP tools available for %s after all attempts",
        config.get("server_name", "MCP Server"),
    )
    return []


def _load_mcp_tools_native(config: Dict[str, Any]) -> List[BaseTool]:
    """Use the shared client manager to load tools synchronously."""
    return load_mcp_tools_sync(config)


async def load_mcp_tools_async(mcp_config: Dict[str, Any]) -> List[BaseTool]:
    """Load tools from an MCP server configuration asynchronously."""
    try:
        tools = await mcp_client_manager.load_tools_from_server(mcp_config)
        return tools
    except Exception as exc:
        logger.error("[McpNativeTools] Failed to load MCP tools: %s", exc)
        return []


def load_mcp_tools_sync(mcp_config: Dict[str, Any]) -> List[BaseTool]:
    """Load tools from an MCP server configuration synchronously."""
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tools = loop.run_until_complete(load_mcp_tools_async(mcp_config))
                return tools
            finally:
                loop.close()

        # Async loop already running; execute in a worker thread
        import concurrent.futures

        def run_async_in_thread() -> List[BaseTool]:
            return asyncio.run(load_mcp_tools_async(mcp_config))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_in_thread)
            timeout = mcp_config.get("timeout_seconds", 30)
            return future.result(timeout=timeout)

    except Exception as exc:
        logger.error("[McpNativeTools] Failed to load MCP tools synchronously: %s", exc)
        return []


def create_mcp_native_tools(
    server_name: str = "MCP Server",
    connection_type: str = "stdio",
    server_url: str = "",
    command: str = "",
    args: Optional[List[str]] = None,
    working_directory: str = "",
    auth_type: str = "none",
    auth_config: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    capabilities_filter: Optional[List[str]] = None,
    resource_access: Optional[Dict[str, bool]] = None,
    tool_permissions: Optional[Dict[str, bool]] = None,
    environment_variables: Optional[Dict[str, str]] = None,
    node_id: str = "",
    node_name: str = "MCP Server",
    **kwargs: Any,
) -> List[BaseTool]:
    """Create native MCP tools by auto-discovering from an MCP server."""
    # Remove deprecated sidecar flag if passed
    kwargs.pop("requires_sidecar", None)

    config: Dict[str, Any] = {
        "server_name": server_name,
        "connection_type": connection_type,
        "server_url": server_url,
        "command": command,
        "args": list(args or []),
        "working_directory": working_directory,
        "auth_type": auth_type,
        "auth_config": auth_config or {},
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "capabilities_filter": capabilities_filter or [],
        "resource_access": resource_access or {},
        "tool_permissions": tool_permissions or {},
        "environment_variables": environment_variables or {},
        **kwargs,
    }

    logger.info("[McpNativeTools] Creating native tools for %s", server_name)
    logger.info("[McpNativeTools] Connection: %s", connection_type)

    if connection_type == "stdio":
        logger.info("[McpNativeTools] Command: %s %s", command, " ".join(args or []))
        logger.info("[McpNativeTools] Working directory: '%s'", working_directory)
    elif connection_type == "http":
        logger.info("[McpNativeTools] Server URL: %s", server_url)
        logger.info("[McpNativeTools] Auth type: %s", auth_type)

    tools = _load_mcp_tools_with_fallback(config)
    tools = _filter_tools(tools, tool_permissions)

    if capabilities_filter:
        logger.info(
            "[McpNativeTools] Capabilities filter specified but not implemented: %s",
            capabilities_filter,
        )

    logger.info(
        "[McpNativeTools] Successfully created %s tools for %s", len(tools), server_name
    )
    return tools


async def test_mcp_server_async(mcp_config: Dict[str, Any]) -> Dict[str, Any]:
    """Test an MCP server connection and return capabilities."""
    try:
        result = await mcp_client_manager.test_connection(mcp_config)
        return result
    except Exception as exc:
        logger.error("[McpNativeTools] MCP server test failed: %s", exc)
        return {"success": False, "error": str(exc)}


def test_mcp_server_sync(mcp_config: Dict[str, Any]) -> Dict[str, Any]:
    """Test an MCP server connection synchronously."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_mcp_server_async(mcp_config))
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error("[McpNativeTools] MCP server test failed synchronously: %s", exc)
        return {"success": False, "error": str(exc)}
