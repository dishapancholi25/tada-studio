"""HTTP MCP tool loading using streamable HTTP client.

Provides seamless integration of remote MCP servers as native LangChain tools.
"""

import asyncio
import logging
from typing import Any, Dict, List

from langchain_core.tools import BaseTool

from ..mcp_client_manager import mcp_client_manager


logger = logging.getLogger(__name__)


async def load_http_mcp_tools_async(mcp_config: Dict[str, Any]) -> List[BaseTool]:
    """
    Load tools from an HTTP MCP server configuration asynchronously.

    Args:
        mcp_config: HTTP MCP server configuration dictionary

    Returns:
        List of LangChain tools ready for use with agents
    """
    try:
        # Validate HTTP-specific configuration
        if mcp_config.get("connection_type") != "http":
            raise ValueError("Configuration must have connection_type='http'")

        server_url = mcp_config.get("server_url", "")
        if not server_url:
            raise ValueError("server_url is required for HTTP MCP connections")

        logger.info(f"[HttpMcpTools] Loading tools from HTTP MCP server: {server_url}")

        tools = await mcp_client_manager.load_tools_from_server(mcp_config)

        logger.info(
            f"[HttpMcpTools] Successfully loaded {len(tools)} tools from HTTP MCP server"
        )
        return tools

    except Exception as e:
        logger.error(f"[HttpMcpTools] Failed to load HTTP MCP tools: {e}")
        return []


def load_http_mcp_tools_sync(mcp_config: Dict[str, Any]) -> List[BaseTool]:
    """Load tools from an HTTP MCP server configuration synchronously.

    Handles both async and sync contexts properly.

    Args:
        mcp_config: HTTP MCP server configuration dictionary

    Returns:
        List of LangChain tools ready for use with agents
    """
    try:
        # Check if we're already in an event loop (async context)
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, run in a thread to avoid event loop conflicts
            import concurrent.futures

            def run_async_in_thread():
                # Create a new event loop for this thread
                return asyncio.run(load_http_mcp_tools_async(mcp_config))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                tools = future.result(timeout=mcp_config.get("timeout_seconds", 30))
                return tools

        except RuntimeError:
            # No event loop running, we can safely create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                tools = loop.run_until_complete(load_http_mcp_tools_async(mcp_config))
                return tools
            finally:
                loop.close()

    except Exception as e:
        logger.error(f"[HttpMcpTools] Failed to load HTTP MCP tools synchronously: {e}")
        return []


def create_http_mcp_tools(
    server_name: str = "HTTP MCP Server",
    server_url: str = "",
    auth_type: str = "none",
    auth_config: Dict[str, str] = None,
    headers: Dict[str, str] = None,
    timeout_seconds: int = 30,
    sse_timeout_seconds: int = 300,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    capabilities_filter: List[str] = None,
    resource_access: Dict[str, bool] = None,
    tool_permissions: Dict[str, bool] = None,
    environment_variables: Dict[str, str] = None,
    node_id: str = "",
    node_name: str = "HTTP MCP Server",
    **kwargs,
) -> List[BaseTool]:
    """
    Create native MCP tools by connecting to an HTTP MCP server.

    This function connects to a remote HTTP MCP server, discovers all available tools,
    and returns them as native LangChain tools that can be used directly
    with LangGraph agents.

    Args:
        server_name: Display name for the MCP server
        server_url: URL of the HTTP MCP server
        auth_type: Authentication type (none, bearer, oauth2)
        auth_config: Authentication configuration (tokens, credentials)
        headers: Additional HTTP headers to send
        timeout_seconds: HTTP timeout for requests
        sse_timeout_seconds: Timeout for SSE stream reading
        max_retries: Number of retry attempts
        retry_delay: Delay between retries
        capabilities_filter: Filter which capabilities to expose
        resource_access: Permissions for resource access
        tool_permissions: Permissions for tool execution
        environment_variables: Environment variables for headers/auth
        node_id: Node ID for tracking
        node_name: Node name for display
        **kwargs: Additional configuration options

    Returns:
        List of LangChain tools discovered from the HTTP MCP server
    """
    if not server_url:
        logger.error("[HttpMcpTools] Server URL is required for HTTP MCP connection")
        return []

    # Build configuration
    config = {
        "server_name": server_name,
        "connection_type": "http",
        "server_url": server_url,
        "auth_type": auth_type,
        "auth_config": auth_config or {},
        "headers": headers or {},
        "timeout_seconds": timeout_seconds,
        "sse_timeout_seconds": sse_timeout_seconds,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "capabilities_filter": capabilities_filter or [],
        "resource_access": resource_access or {},
        "tool_permissions": tool_permissions or {},
        "environment_variables": environment_variables or {},
        **kwargs,
    }

    logger.info(f"[HttpMcpTools] Creating HTTP MCP tools for {server_name}")
    logger.info(f"[HttpMcpTools] Server URL: {server_url}")
    logger.info(f"[HttpMcpTools] Auth type: {auth_type}")

    # Load tools synchronously
    tools = load_http_mcp_tools_sync(config)

    # Apply permissions filtering if configured
    if tool_permissions:
        filtered_tools = []
        for tool in tools:
            tool_name = getattr(tool, "name", str(tool))
            if tool_name in tool_permissions:
                if tool_permissions[tool_name]:
                    filtered_tools.append(tool)
                else:
                    logger.info(
                        f"[HttpMcpTools] Tool '{tool_name}' blocked by permissions"
                    )
            else:
                # If not explicitly configured, allow the tool
                filtered_tools.append(tool)

        logger.info(
            f"[HttpMcpTools] Applied permissions filter: {len(filtered_tools)}/{len(tools)} tools allowed"
        )
        tools = filtered_tools

    # Apply capabilities filtering if configured
    if capabilities_filter:
        # For now, we don't have a way to map tools to capabilities
        # This could be enhanced in the future
        logger.info(
            f"[HttpMcpTools] Capabilities filter specified but not implemented: {capabilities_filter}"
        )

    logger.info(
        f"[HttpMcpTools] Successfully created {len(tools)} HTTP MCP tools for {server_name}"
    )
    return tools


async def test_http_mcp_server_async(mcp_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test an HTTP MCP server connection and return capabilities.

    Args:
        mcp_config: HTTP MCP server configuration dictionary

    Returns:
        Dictionary with test results and discovered capabilities
    """
    try:
        # Validate HTTP configuration
        if mcp_config.get("connection_type") != "http":
            mcp_config["connection_type"] = "http"

        result = await mcp_client_manager.test_connection(mcp_config)
        return result
    except Exception as e:
        logger.error(f"[HttpMcpTools] HTTP MCP server test failed: {e}")
        return {"success": False, "error": str(e)}


def test_http_mcp_server_sync(mcp_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test an HTTP MCP server connection synchronously.

    Args:
        mcp_config: HTTP MCP server configuration dictionary

    Returns:
        Dictionary with test results and discovered capabilities
    """
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(test_http_mcp_server_async(mcp_config))
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"[HttpMcpTools] HTTP MCP server test failed synchronously: {e}")
        return {"success": False, "error": str(e)}


def create_github_copilot_mcp_tools(
    access_token: str,
    server_name: str = "GitHub Copilot MCP",
    node_id: str = "",
    node_name: str = "GitHub Copilot MCP",
    **kwargs,
) -> List[BaseTool]:
    """
    Create GitHub Copilot MCP tools.

    Args:
        access_token: GitHub Personal Access Token or OAuth token
        server_name: Display name for the server
        node_id: Node ID for tracking
        node_name: Node name for display
        **kwargs: Additional configuration options

    Returns:
        List of LangChain tools from GitHub Copilot MCP server
    """
    if not access_token:
        logger.error("[HttpMcpTools] Access token is required for GitHub Copilot MCP")
        return []

    return create_http_mcp_tools(
        server_name=server_name,
        server_url="https://api.githubcopilot.com/mcp/",
        auth_type="bearer",
        auth_config={"access_token": access_token},
        node_id=node_id,
        node_name=node_name,
        **kwargs,
    )
