"""MCP server tool creator for agents.

This module creates MCP (Model Context Protocol) server tool instances
that agents can use to interact with MCP servers.

Supports three implementation strategies:
1. Native: Loads individual tools from MCP server
2. Adapter: Single tool that adapts to MCP protocol
3. Legacy: Backward-compatible legacy implementation
"""

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.tools.mcp_config_utils import prepare_mcp_config_for_execution


logger = get_logger(__name__)


def _detect_mcp_implementation() -> Tuple[bool, bool, Any, Any, Any]:
    """
    Detect which MCP implementation is available.

    Returns:
        Tuple of (use_native, use_adapter, native_factory, adapter_factory, server_factory)
    """
    use_native = False
    use_adapter = False
    native_factory = None
    adapter_factory = None
    server_factory = None

    # Try native implementation first
    try:
        from backend.tools.mcp_native_tools import (
            create_mcp_native_tools as native_impl,
        )

        native_factory = native_impl
        use_native = True
        logger.info("Using native MCP tool loading implementation")
    except ImportError:
        # Try adapter implementation
        try:
            from backend.tools.mcp_adapter_tool import (
                create_mcp_adapter_tool as adapter_impl,
            )

            adapter_factory = adapter_impl
            use_adapter = True
            logger.info("Falling back to MCP adapter implementation")
        except ImportError:
            # Fall back to legacy
            from backend.tools.mcp_server_tool import (
                create_mcp_server_tool as server_impl,
            )

            server_factory = server_impl
            logger.info("Falling back to legacy MCP implementation")

    return use_native, use_adapter, native_factory, adapter_factory, server_factory


def _extract_mcp_config_from_dict(mcp_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract MCP configuration from a dictionary.

    Args:
        mcp_config: MCP configuration dictionary

    Returns:
        Dictionary of configuration parameters
    """
    return {
        "provider": mcp_config.get("provider", ""),
        "server_name": mcp_config.get("server_name", "MCP Server"),
        "connection_type": mcp_config.get("connection_type", "stdio"),
        "server_url": mcp_config.get("server_url", ""),
        "command": mcp_config.get("command", ""),
        "args": mcp_config.get("args", []),
        "working_directory": mcp_config.get("working_directory", ""),
        "environment_variables": mcp_config.get("environment_variables", {}),
        "auth_type": mcp_config.get("auth_type", "none"),
        "auth_config": mcp_config.get("auth_config", {}),
        "timeout_seconds": mcp_config.get("timeout_seconds", 30),
        "max_retries": mcp_config.get("max_retries", 3),
        "retry_delay": mcp_config.get("retry_delay", 1.0),
        "keep_alive": mcp_config.get("keep_alive", True),
        "capabilities_filter": mcp_config.get("capabilities_filter", []),
        "resource_access": mcp_config.get("resource_access", {}),
        "tool_permissions": mcp_config.get("tool_permissions", {}),
        "logging_level": mcp_config.get("logging_level", "info"),
        "ssl_verify": mcp_config.get("ssl_config", {}).get("verify", True),
        # Preserved as a dict too so native tool loading (which delegates to
        # mcp_client_manager) can read the same "ssl_config" key it expects.
        "ssl_config": mcp_config.get("ssl_config", {}),
        "metadata": mcp_config.get("metadata", {}),
    }


def _extract_mcp_config_from_object(mcp_config: Any) -> Dict[str, Any]:
    """
    Extract MCP configuration from a config object.

    Args:
        mcp_config: MCP configuration object

    Returns:
        Dictionary of configuration parameters
    """
    return {
        "provider": getattr(mcp_config, "provider", ""),
        "server_name": mcp_config.server_name,
        "connection_type": mcp_config.connection_type,
        "server_url": mcp_config.server_url,
        "command": mcp_config.command,
        "args": mcp_config.args,
        "working_directory": mcp_config.working_directory,
        "environment_variables": getattr(mcp_config, "environment_variables", {}),
        "auth_type": mcp_config.auth_type,
        "auth_config": mcp_config.auth_config,
        "timeout_seconds": mcp_config.timeout_seconds,
        "max_retries": mcp_config.max_retries,
        "retry_delay": mcp_config.retry_delay,
        "keep_alive": mcp_config.keep_alive,
        "capabilities_filter": mcp_config.capabilities_filter,
        "resource_access": mcp_config.resource_access,
        "tool_permissions": mcp_config.tool_permissions,
        "logging_level": mcp_config.logging_level,
        "ssl_verify": (
            mcp_config.ssl_config.get("verify", True) if mcp_config.ssl_config else True
        ),
        "ssl_config": getattr(mcp_config, "ssl_config", {}) or {},
        "metadata": getattr(mcp_config, "metadata", {}),
    }


def _apply_notion_preset(
    config: Dict[str, Any], target_node: EnhancedNodeData, mcp_config: Any
) -> Dict[str, Any]:
    """
    Log Notion MCP configuration detection.

    Args:
        config: Current configuration dictionary
        target_node: The node being configured
        mcp_config: Original MCP config (dict or object)

    Returns:
        The configuration dictionary (unchanged)
    """

    # Detect Notion signature
    def is_notion_mcp_url(value):
        try:
            parsed = urlparse(str(value))
            return parsed.hostname == "mcp.notion.com"
        except Exception:
            return False

    notion_signature = (
        any(
            is_notion_mcp_url(value)
            for value in (
                ([config["server_url"]] if config["server_url"] else [])
                + list(config["args"] or [])
            )
        )
        or "notion" in config["server_name"].lower()
    )

    if notion_signature:
        logger.info(
            "Detected Notion MCP config",
            extra={
                "node_id": target_node.uniq_id,
                "connection_type": config["connection_type"],
                "server_url": config["server_url"],
                "auth_type": config["auth_type"],
            },
        )

    return config


def _create_native_mcp_tools(
    config: Dict[str, Any], target_node: EnhancedNodeData, native_factory: Any
) -> List[Any]:
    """
    Create tools using native MCP implementation.

    Args:
        config: MCP configuration
        target_node: The node being configured
        native_factory: The native tool creation function

    Returns:
        List of MCP tools
    """
    logger.info(
        "Loading native MCP tools from server: %s (auth_type=%s)",
        config["server_name"],
        config.get("auth_type", "none"),
    )

    mcp_tools = native_factory(
        server_name=config["server_name"],
        connection_type=config["connection_type"],
        server_url=config["server_url"],
        command=config["command"],
        args=config["args"],
        working_directory=config["working_directory"],
        auth_type=config["auth_type"],
        auth_config=config["auth_config"],
        timeout_seconds=config["timeout_seconds"],
        max_retries=config["max_retries"],
        retry_delay=config["retry_delay"],
        capabilities_filter=config["capabilities_filter"],
        resource_access=config["resource_access"],
        tool_permissions=config["tool_permissions"],
        environment_variables=config["environment_variables"],
        node_id=target_node.uniq_id,
        node_name=target_node.name,
        provider=config.get("provider", ""),
        metadata=config.get("metadata", {}),
        ssl_config=config.get("ssl_config", {}),
    )

    # Try HTTP fallback if native returned no tools
    if not mcp_tools and config["connection_type"] == "http":
        logger.info(
            "Native loader returned no tools for %s; falling back to HTTP MCP loader",
            config["server_name"],
        )
        try:
            from backend.tools.mcp_http_tools import create_http_mcp_tools

            fallback_tools = create_http_mcp_tools(
                server_name=config["server_name"],
                server_url=config["server_url"],
                auth_type=config["auth_type"],
                auth_config=config["auth_config"],
                timeout_seconds=config["timeout_seconds"],
                sse_timeout_seconds=config["timeout_seconds"] * 10,
                max_retries=config["max_retries"],
                retry_delay=config["retry_delay"],
                capabilities_filter=config["capabilities_filter"],
                resource_access=config["resource_access"],
                tool_permissions=config["tool_permissions"],
                environment_variables=config["environment_variables"],
                node_id=target_node.uniq_id,
                node_name=target_node.name,
                ssl_config=config.get("ssl_config", {}),
            )
            mcp_tools.extend(fallback_tools)
        except ImportError as exc:
            logger.error("Failed to import HTTP MCP tools: %s", exc)
        except Exception as exc:
            logger.error(
                "Failed to load HTTP MCP tools from %s via fallback: %s",
                config["server_name"],
                exc,
            )

    logger.info(
        f"Added {len(mcp_tools)} native tools from MCP server: {config['server_name']}"
    )
    for tool in mcp_tools:
        logger.info(
            f"  - {getattr(tool, 'name', str(tool))}: {getattr(tool, 'description', 'No description')}"
        )

    return mcp_tools


def create_mcp_server_tools_from_node(
    target_node: EnhancedNodeData,
    user_id: Optional[str] = None,
) -> List[Any]:
    """
    Create MCP server tools from an MCP_SERVER node.

    Automatically selects the best available implementation:
    1. Native (individual tools)
    2. Adapter (single interaction tool)
    3. Legacy (backward compatible)

    Args:
        target_node: The MCP_SERVER node configuration
        user_id: User ID for OAuth token lookup (injected into auth_config)

    Returns:
        List of MCP tool instances

    Raises:
        ImportError: If no MCP tool implementation is available
    """
    if not target_node.mcp_server_config:
        logger.warning(f"Node {target_node.name} missing mcp_server_config")
        return []

    logger.info(f"Creating MCP server tools from node: {target_node.name}")

    # Detect implementation
    use_native, use_adapter, native_factory, adapter_factory, server_factory = (
        _detect_mcp_implementation()
    )

    # Extract configuration
    mcp_config = target_node.mcp_server_config
    if isinstance(mcp_config, dict):
        config = _extract_mcp_config_from_dict(mcp_config)
    else:
        config = _extract_mcp_config_from_object(mcp_config)

    # Inject user_id for OAuth configs (both generic "oauth" and "mcp_oauth")
    if user_id and config.get("auth_type") in ("oauth", "mcp_oauth"):
        if "auth_config" not in config:
            config["auth_config"] = {}
        config["auth_config"]["user_id"] = user_id
        # mcp_oauth also needs server_name and server_url in auth_config
        # for token retrieval in mcp_client_manager.
        # Use canonical names for known providers so the token lookup key
        # matches what the frontend sends during OAuth initiation.
        # E.g., the Atlassian OAuth flow always uses "Atlassian" regardless
        # of what the user names their MCP node ("Confluence", "Jira", etc.)
        if config.get("auth_type") == "mcp_oauth":
            _MCP_OAUTH_CANONICAL_NAMES = {
                "atlassian": "Atlassian",
            }
            provider = config.get("provider", "")
            canonical_name = _MCP_OAUTH_CANONICAL_NAMES.get(
                provider, config.get("server_name", "")
            )
            config["auth_config"]["server_name"] = canonical_name
            config["auth_config"]["server_url"] = config.get("server_url", "")
        logger.info(
            "Injected user_id for OAuth MCP config",
            extra={"user_id": user_id, "server": config.get("server_name")},
        )

    # Extract user token from execution context for oauth2 (User Identity)
    if config.get("auth_type") == "oauth2":
        try:
            from backend.services.execution.context import get_current_user_access_token

            token = get_current_user_access_token()
            if token:
                if "auth_config" not in config:
                    config["auth_config"] = {}
                config["auth_config"]["access_token"] = token
                logger.info(
                    f"Injected user access token from execution context for oauth2 MCP config "
                    f"(server: {config.get('server_name')}, token_length: {len(token)})"
                )
            else:
                logger.warning(
                    f"oauth2 auth type configured for {config.get('server_name')} but no token in execution context"
                )
        except Exception as e:
            logger.error(f"Failed to get user token from execution context: {e}")

    # Apply Notion preset if detected
    config = _apply_notion_preset(config, target_node, mcp_config)

    # Prepare configuration for execution
    prepared_config = prepare_mcp_config_for_execution(
        config, node_id=target_node.uniq_id, node_name=target_node.name, logger=logger
    )

    # Update config with prepared values
    config.update(prepared_config)

    # Create tools based on available implementation
    tools = []

    if use_native:
        tools = _create_native_mcp_tools(config, target_node, native_factory)
    elif use_adapter:
        # Adapter implementation (single tool)
        mcp_tool = adapter_factory(
            server_name=config["server_name"],
            connection_type=config["connection_type"],
            server_url=config["server_url"],
            command=config["command"],
            args=config["args"],
            working_directory=config["working_directory"],
            auth_type=config["auth_type"],
            auth_config=config["auth_config"],
            timeout_seconds=config["timeout_seconds"],
            max_retries=config["max_retries"],
            retry_delay=config["retry_delay"],
            keep_alive=config["keep_alive"],
            capabilities_filter=config["capabilities_filter"],
            resource_access=config["resource_access"],
            tool_permissions=config["tool_permissions"],
            environment_variables=config["environment_variables"],
            node_id=target_node.uniq_id,
            node_name=target_node.name,
            logging_level=config["logging_level"],
            verify_ssl=config["ssl_verify"],
            use_legacy=False,
        )
        tools.append(mcp_tool)
        logger.info(f"Added MCP adapter tool: {mcp_tool.name}")
    else:
        # Legacy implementation
        mcp_tool = server_factory(
            server_name=config["server_name"],
            connection_type=config["connection_type"],
            server_url=config["server_url"],
            command=config["command"],
            args=config["args"],
            working_directory=config["working_directory"],
            auth_type=config["auth_type"],
            auth_config=config["auth_config"],
            timeout_seconds=config["timeout_seconds"],
            max_retries=config["max_retries"],
            retry_delay=config["retry_delay"],
            keep_alive=config["keep_alive"],
            capabilities_filter=config["capabilities_filter"],
            resource_access=config["resource_access"],
            tool_permissions=config["tool_permissions"],
            environment_variables=config["environment_variables"],
            node_id=target_node.uniq_id,
            node_name=target_node.name,
            logging_level=config["logging_level"],
            verify_ssl=config["ssl_verify"],
        )
        tools.append(mcp_tool)
        logger.info(f"Added legacy MCP server tool: {mcp_tool.name}")

    # Attach parent MCP server metadata to each tool for tracking
    # This allows tool executions to be mapped back to their parent MCP server node
    for tool in tools:
        tool._mcp_server_node_id = target_node.uniq_id
        tool._mcp_server_node_name = target_node.name
        tool._mcp_server_node_type = target_node.type

    if tools:
        logger.debug(
            f"Attached MCP server metadata to {len(tools)} tools from {target_node.name}"
        )

    return tools
