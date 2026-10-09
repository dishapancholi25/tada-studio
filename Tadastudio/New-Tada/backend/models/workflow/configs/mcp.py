"""MCP server configuration for Model Context Protocol nodes.

This module defines the configuration for MCP (Model Context Protocol)
server tool nodes that enable integration with MCP servers.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import Any, Dict, List, Optional


@dataclass
class MCPServerConfig:
    """Configuration for MCP (Model Context Protocol) server tool nodes.

    Comprehensive configuration for connecting to and using MCP servers
    via different transport mechanisms (stdio, HTTP, WebSocket).

    Attributes:
        server_name: Display name for the server
        connection_type: Connection type (stdio, http, websocket)
        server_url: URL/path to the MCP server (for http/websocket)
        command: Command to launch local server (for stdio)
        args: Command arguments (for stdio)
        working_directory: Working directory for local server (for stdio)
        environment_variables: Environment variables for stdio servers
        workspace_label: Optional workspace label from frontend
        transport_config: Transport-specific settings
        requires_sidecar: Whether this MCP server requires the sidecar bridge
        auth_type: Authentication type (none, api_key, oauth2, bearer, custom)
        auth_config: Authentication details
        timeout_seconds: Connection timeout
        max_retries: Retry attempts
        retry_delay: Delay between retries
        keep_alive: Keep connection alive
        capabilities_filter: Filter which capabilities to expose
        resource_access: Permissions for resource access
        tool_permissions: Permissions for tool execution
        prompt_templates: Custom prompt templates
        ssl_config: SSL/TLS configuration
        proxy_config: Proxy settings
        rate_limit: Rate limiting configuration
        cache_config: Response caching settings
        logging_level: Logging level (debug, info, warning, error)
        enable_metrics: Enable performance metrics
        trace_requests: Trace all requests/responses
        metadata: Additional server metadata
        description: Server description for UI display
        version: Server version
        parent_agent_id: ID of the agent this tool belongs to
    """

    provider: str = ""  # 'github', 'notion', or empty for generic
    server_name: str = "MCP Server"
    connection_type: str = "stdio"
    server_url: str = ""
    command: str = ""
    args: List[str] = field(default_factory=list)
    working_directory: str = ""
    environment_variables: Dict[str, str] = field(default_factory=dict)
    workspace_label: Optional[str] = None
    transport_config: Dict[str, Any] = field(default_factory=dict)
    requires_sidecar: bool = False
    auth_type: str = "none"
    auth_config: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    keep_alive: bool = True
    capabilities_filter: List[str] = field(default_factory=list)
    resource_access: Dict[str, bool] = field(default_factory=dict)
    tool_permissions: Dict[str, bool] = field(default_factory=dict)
    prompt_templates: Dict[str, str] = field(default_factory=dict)
    ssl_config: Dict[str, Any] = field(default_factory=dict)
    proxy_config: Dict[str, str] = field(default_factory=dict)
    rate_limit: Dict[str, int] = field(default_factory=dict)
    cache_config: Dict[str, Any] = field(default_factory=dict)
    logging_level: str = "info"
    enable_metrics: bool = False
    trace_requests: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    version: str = ""
    parent_agent_id: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None
