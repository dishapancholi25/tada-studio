"""API endpoint for testing MCP server connections."""

import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


logger = logging.getLogger(__name__)


def _parse_legacy_test_result(result: str) -> Dict[str, Any]:
    """Parse the legacy MCP test result string format."""
    capabilities = {}

    if isinstance(result, str):
        # Parse text output to extract capabilities
        if "Tools" in result:
            # Extract tools count and names

            tools_match = re.search(r"Tools \((\d+)\)", result)
            if tools_match:
                tools_count = int(tools_match.group(1))
                # Extract tool names and descriptions from bullet points
                tool_section = result[result.find("Tools") :]
                if "Resources" in tool_section:
                    tool_section = tool_section[: tool_section.find("Resources")]
                elif "Prompts" in tool_section:
                    tool_section = tool_section[: tool_section.find("Prompts")]

                # Parse tool lines more carefully
                tool_lines = []
                for line in tool_section.split("\n"):
                    if line.strip().startswith("-") or line.strip().startswith("•"):
                        # Extract tool name and description
                        tool_text = line.strip()[1:].strip()
                        if ":" in tool_text:
                            name, desc = tool_text.split(":", 1)
                            tool_lines.append(
                                {"name": name.strip(), "description": desc.strip()}
                            )
                        else:
                            tool_lines.append(
                                {"name": tool_text.strip(), "description": ""}
                            )

                capabilities["tools"] = tool_lines[:tools_count] if tool_lines else []

        if "Resources" in result:
            # Extract resources

            resources_match = re.search(r"Resources \((\d+)\)", result)
            if resources_match:
                resources_count = int(resources_match.group(1))
                # Extract resource URIs from the resources section
                resource_section = result[result.find("Resources") :]
                if "Prompts" in resource_section:
                    resource_section = resource_section[
                        : resource_section.find("Prompts")
                    ]
                resource_lines = re.findall(r"[-•]\s+([^:\n]+)", resource_section)
                capabilities["resources"] = (
                    resource_lines[:resources_count] if resource_lines else []
                )

        if "Prompts" in result:
            # Extract prompts

            prompts_match = re.search(r"Prompts \((\d+)\)", result)
            if prompts_match:
                prompts_count = int(prompts_match.group(1))
                prompt_section = result[result.find("Prompts") :]
                prompt_lines = re.findall(r"[-•]\s+([^:\n]+)", prompt_section)
                capabilities["prompts"] = (
                    prompt_lines[:prompts_count] if prompt_lines else []
                )

    # Check if connection was successful
    if isinstance(result, str) and ("Failed to connect" in result or "Error" in result):
        # Extract error message
        try:
            error_match = re.search(r"Error[:\s]+(.+)", result)
            error_msg = error_match.group(1) if error_match else result
        except (AttributeError, TypeError):
            error_msg = result

        return {"success": False, "error": error_msg, "capabilities": None}

    return {
        "success": True,
        "message": "Successfully connected and discovered capabilities",
        "capabilities": capabilities,
        "raw_output": result[:500]
        if isinstance(result, str) and len(result) > 500
        else result,  # Include truncated raw output for debugging
    }


class McpServerTestRequest(BaseModel):
    """Request model for testing MCP server connection."""

    server_name: str = "MCP Server"
    connection_type: str = "stdio"
    server_url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    working_directory: Optional[str] = None
    environment_variables: Optional[Dict[str, str]] = None
    auth_type: str = "none"
    auth_config: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30
    max_retries: int = 1
    ssl_config: Optional[Dict[str, Any]] = None  # NEW: SSL/TLS configuration


async def test_mcp_server_connection(
    request: McpServerTestRequest, user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test MCP server connection and discover capabilities using native MCP client.

    Args:
        request: Test configuration for MCP server
        user_id: Authenticated user ID (needed for OAuth token lookup)

    Returns:
        Dictionary with test results and discovered capabilities
    """
    try:
        use_native = False
        use_adapter = False
        test_mcp_server_async = None
        create_mcp_adapter_tool = None
        create_mcp_server_tool = None

        # Try to use the new native MCP tool loading first
        try:
            # Try both import paths for compatibility
            try:
                from backend.tools.mcp_native_tools import (
                    test_mcp_server_async as native_test_fn,
                )
            except ImportError:
                from tools.mcp_native_tools import (
                    test_mcp_server_async as native_test_fn,
                )
            test_mcp_server_async = native_test_fn
        except ImportError:
            test_mcp_server_async = None

        if test_mcp_server_async:
            use_native = True
            logger.info("Testing with native MCP implementation")
        else:
            # Attempt adapter-based implementation before falling back to legacy
            adapter_factory = None
            try:
                from backend.tools.mcp_adapter_tool import (
                    create_mcp_adapter_tool as adapter_factory,
                )
            except ImportError:
                try:
                    from tools.mcp_adapter_tool import (
                        create_mcp_adapter_tool as adapter_factory,
                    )
                except ImportError:
                    adapter_factory = None

            if adapter_factory:
                create_mcp_adapter_tool = adapter_factory
                use_native = False
                use_adapter = True
                logger.info("Falling back to MCP adapter for testing")
            else:
                try:
                    from backend.tools.mcp_server_tool import (
                        create_mcp_server_tool as server_factory,
                    )
                except ImportError:
                    from tools.mcp_server_tool import (
                        create_mcp_server_tool as server_factory,
                    )
                create_mcp_server_tool = server_factory
                use_native = False
                use_adapter = False
                logger.info("Falling back to legacy MCP implementation for testing")

        # Build configuration for testing
        auth_config = request.auth_config or {}

        # For mcp_oauth, inject user_id and server identifiers so the
        # McpClientManager can look up the stored OAuth token.
        if request.auth_type == "mcp_oauth" and user_id:
            auth_config.setdefault("user_id", user_id)
            auth_config.setdefault("server_name", request.server_name)
            auth_config.setdefault("server_url", request.server_url or "")

        mcp_config = {
            "server_name": request.server_name,
            "connection_type": request.connection_type,
            "server_url": request.server_url or "",
            "command": request.command or "",
            "args": request.args or [],
            "working_directory": request.working_directory or "",
            "auth_type": request.auth_type,
            "auth_config": auth_config,
            "timeout_seconds": request.timeout_seconds,
            "max_retries": request.max_retries,
            "environment_variables": request.environment_variables or {},
        }

        # Test the connection and discover capabilities using the appropriate method
        if use_native:
            # Use native MCP client for async testing
            logger.info("Testing MCP server connection with native client")
            result = await test_mcp_server_async(mcp_config)

            if result["success"]:
                # Format tools list for consistency with legacy response format
                capabilities = {
                    "tools": result.get("tools", []),
                    "tool_count": result.get("tool_count", 0),
                }

                return {
                    "success": True,
                    "message": "Successfully connected and discovered capabilities",
                    "capabilities": capabilities,
                    "server_name": result.get("server_name", request.server_name),
                    "tool_count": result.get("tool_count", 0),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "capabilities": None,
                }

        elif use_adapter:
            # Fall back to adapter implementation
            logger.info("Testing with MCP adapter")
            tool = create_mcp_adapter_tool(
                server_name=request.server_name,
                connection_type=request.connection_type,
                server_url=request.server_url or "",
                command=request.command or "",
                args=request.args or [],
                working_directory=request.working_directory or "",
                auth_type=request.auth_type,
                auth_config=request.auth_config or {},
                timeout_seconds=request.timeout_seconds,
                max_retries=request.max_retries,
                environment_variables=request.environment_variables or {},
                use_legacy=False,
            )
            result = tool.invoke(
                {"action": "discover", "target": "capabilities", "arguments": None}
            )

            # Parse legacy string result
            return _parse_legacy_test_result(result)

        else:
            # Fall back to legacy implementation
            logger.info("Testing with legacy MCP implementation")
            try:
                from backend.tools.mcp_server_tool import create_mcp_server_tool
            except ImportError:
                from tools.mcp_server_tool import create_mcp_server_tool

            tool = create_mcp_server_tool(
                server_name=request.server_name,
                connection_type=request.connection_type,
                server_url=request.server_url or "",
                command=request.command or "",
                args=request.args or [],
                working_directory=request.working_directory or "",
                auth_type=request.auth_type,
                auth_config=request.auth_config or {},
                timeout_seconds=request.timeout_seconds,
                max_retries=request.max_retries,
                environment_variables=request.environment_variables or {},
            )
            result = tool.invoke(
                {"action": "discover", "target": "capabilities", "arguments": None}
            )

            # Parse legacy string result
            return _parse_legacy_test_result(result)

    except Exception as e:
        logger.error("Error testing MCP server: %s", e)
        # Surface the SSRF guardrail message as-is (it is a known-safe, fixed
        # string with no internal details); everything else stays generic to
        # avoid leaking stack traces or internal errors to the caller.
        from backend.services.guardrails.ssrf_mcp import BLOCKED_MESSAGE

        if str(e) == BLOCKED_MESSAGE:
            return {
                "success": False,
                "error": BLOCKED_MESSAGE,
                "capabilities": None,
            }
        return {
            "success": False,
            "error": "MCP server connection test failed",
            "capabilities": None,
        }
