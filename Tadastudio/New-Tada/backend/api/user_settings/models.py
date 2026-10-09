"""Pydantic models for user settings API.

This module defines request and response models for the user settings
API endpoints.
"""

import enum
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from .constants import MCP_SERVER_NAME_MAX_LENGTH


def _get_allowed_commands() -> Set[str]:
    """Get allowed MCP server commands from environment or defaults.

    Environment variable: MCP_ALLOWED_COMMANDS
    Format: Comma-separated list (e.g., "npx,node,python,python3")
    """
    env_value = os.getenv("MCP_ALLOWED_COMMANDS", "").strip()

    if env_value:
        # Parse from environment variable
        commands = {cmd.strip() for cmd in env_value.split(",") if cmd.strip()}
        if commands:
            return commands

    # Secure defaults - legitimate MCP server runtimes
    return {
        "npx",
        "node",
        "python",
        "python3",
        "python3.11",
        "python3.12",
        "uvx",
        "uv",
        "deno",
        "bun",
        "tsx",
        "ts-node",
    }


def _get_dangerous_chars_command() -> List[str]:
    """Get dangerous characters for commands from environment or defaults.

    Environment variable: MCP_DANGEROUS_CHARS_COMMAND
    Format: String of characters (e.g., ";|&$")
    """
    env_value = os.getenv("MCP_DANGEROUS_CHARS_COMMAND", "").strip()

    if env_value:
        # Parse from environment variable
        return list(env_value)

    # Secure defaults - shell metacharacters that enable injection
    return [";", "|", "&", "$", "`", "\n", "\r", ">", "<", "(", ")"]


def _get_dangerous_chars_args() -> List[str]:
    """Get dangerous characters for arguments from environment or defaults.

    Environment variable: MCP_DANGEROUS_CHARS_ARGS
    Format: String of characters (e.g., ";|&$")
    """
    env_value = os.getenv("MCP_DANGEROUS_CHARS_ARGS", "").strip()

    if env_value:
        # Parse from environment variable
        return list(env_value)

    # Secure defaults - subset focused on command injection
    return [";", "|", "&", "$", "`", "\n", "\r"]


class McpServerVisibility(str, enum.Enum):
    """MCP server visibility options."""

    PRIVATE = "private"
    SHARED = "shared"


class ExternalServiceInfo(BaseModel):
    """Information about a configured external service."""

    service_name: str = Field(..., description="Name of the external service")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    service_url: Optional[str] = Field(None, description="Service URL / endpoint")
    auth_type: Optional[str] = Field(
        None, description="Authentication type (e.g. api_key_header)"
    )
    is_active: bool = Field(..., description="Whether the service is active")
    api_key_configured: bool = Field(
        ..., description="Whether an API key is configured"
    )
    api_key_masked: Optional[str] = Field(
        None, description="Masked API key for display (e.g., '****...abcd')"
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Additional service settings"
    )
    created_at: Optional[datetime] = Field(
        None, description="When the service was configured"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When the service was last updated"
    )
    system_default_configured: bool = Field(
        False,
        description="Whether a system-level default is configured for this service",
    )


class SaveExternalServiceRequest(BaseModel):
    """Request to save external service configuration."""

    api_key: Optional[str] = Field(
        None, description="API key for the service", max_length=500
    )
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    service_url: Optional[str] = Field(None, description="Service URL / endpoint")
    auth_type: Optional[str] = Field(
        None, description="Authentication type (e.g. api_key_header)"
    )
    credentials: Optional[Dict[str, str]] = Field(
        None, description="Structured credentials (e.g. api_key, secret)"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Additional service settings"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate API key is not empty or whitespace when provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("API key cannot be empty or whitespace")
        if len(v) > 500:
            raise ValueError("API key cannot exceed 500 characters")
        return v.strip()


class SaveExternalServiceResponse(BaseModel):
    """Response after saving external service configuration."""

    success: bool = Field(..., description="Whether the save was successful")
    message: str = Field(..., description="Status message")
    service: ExternalServiceInfo = Field(..., description="Updated service info")


class ListExternalServicesResponse(BaseModel):
    """Response containing list of external services."""

    success: bool = Field(..., description="Whether the request was successful")
    services: List[ExternalServiceInfo] = Field(
        ..., description="List of configured services"
    )


class DeleteExternalServiceResponse(BaseModel):
    """Response after deleting external service configuration."""

    success: bool = Field(..., description="Whether the delete was successful")
    message: str = Field(..., description="Status message")


class GetExternalServiceForNodeResponse(BaseModel):
    """Response for getting external service config for node creation.

    This endpoint returns the decrypted API key for use when creating
    new nodes that need the configuration.
    """

    configured: bool = Field(..., description="Whether the service is configured")
    api_key: Optional[str] = Field(
        None, description="Decrypted API key (only for node creation)"
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Additional service settings"
    )


# MCP Server Models


class McpAdvancedSettings(BaseModel):
    """Advanced settings for MCP server configuration."""

    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retries: Optional[int] = Field(None, description="Maximum retry attempts")
    retryDelay: Optional[float] = Field(
        None, description="Delay between retries in seconds"
    )


class McpAuthenticationSettings(BaseModel):
    """Authentication settings for MCP server configuration."""

    type: Optional[str] = Field(
        None, description="Authentication type: bearer, api_key, oauth2, etc."
    )
    token: Optional[str] = Field(
        None, description="Bearer token for bearer authentication"
    )
    apiKey: Optional[str] = Field(
        None, description="API key for api_key authentication"
    )
    headerName: Optional[str] = Field(
        None, description="Header name for API key (default: X-API-Key)"
    )
    headers: Optional[Dict[str, str]] = Field(
        None, description="Custom authentication headers"
    )


class StandardMcpServerConfig(BaseModel):
    """Standard MCP server configuration (.mcp.json format).

    This matches the format used by Anthropic's Claude Code and other MCP clients,
    with settings organized under advanced and authentication nodes.
    """

    type: str = Field(..., description="Transport type: stdio, http, or sse")
    command: Optional[str] = Field(None, description="Command to execute (stdio only)")
    args: Optional[List[str]] = Field(
        None, description="Command arguments (stdio only)"
    )
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    cwd: Optional[str] = Field(None, description="Working directory (stdio only)")
    url: Optional[str] = Field(None, description="Server URL (http/sse only)")
    description: Optional[str] = Field(None, description="Server description")
    advanced: Optional[McpAdvancedSettings] = Field(
        None, description="Advanced settings (timeout, retries, etc.)"
    )
    authentication: Optional[McpAuthenticationSettings] = Field(
        None, description="Authentication settings"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: Optional[str]) -> Optional[str]:
        """Validate command is in allowlist and doesn't contain shell metacharacters.

        Security: Only permit specific, pre-approved commands to prevent arbitrary
        command execution. This is critical for stdio MCP servers.

        Configuration: Customize via MCP_ALLOWED_COMMANDS and MCP_DANGEROUS_CHARS_COMMAND
        environment variables.
        """
        if v is None:
            return v

        import os

        # STEP 1: Block shell metacharacters FIRST (before parsing)
        # This prevents injection attempts like "node; ls /tmp"
        dangerous_chars = _get_dangerous_chars_command()
        for char in dangerous_chars:
            if char in v:
                raise ValueError(
                    f"Command contains dangerous shell metacharacter '{char}'. "
                    "Only simple command names are allowed."
                )

        # STEP 2: Extract base command name (handle paths)
        base_cmd = os.path.basename(v.strip())

        # STEP 3: Check against allowlist
        allowed_commands = _get_allowed_commands()
        if base_cmd not in allowed_commands:
            raise ValueError(
                f"Command '{base_cmd}' is not in the allowlist. "
                f"Permitted commands: {', '.join(sorted(allowed_commands))}"
            )

        return v.strip()

    @field_validator("args")
    @classmethod
    def validate_args(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate args don't contain shell metacharacters.

        Security: Prevent command injection through argument values.

        Configuration: Customize via MCP_DANGEROUS_CHARS_ARGS environment variable.
        """
        if v is None:
            return v

        # Block shell metacharacters in arguments
        dangerous_chars = _get_dangerous_chars_args()

        for i, arg in enumerate(v):
            if not isinstance(arg, str):
                raise ValueError(f"Argument at index {i} must be a string")

            for char in dangerous_chars:
                if char in arg:
                    raise ValueError(
                        f"Argument at index {i} ('{arg[:50]}...') contains dangerous "
                        f"shell metacharacter '{char}'. Arguments should not contain "
                        "shell metacharacters."
                    )

        return v


class ExportMcpServersRequest(BaseModel):
    """Request to export specific MCP servers by server IDs.

    If server_ids is empty or not provided, all active servers will be exported.
    """

    server_ids: Optional[List[str]] = Field(
        None,
        description="List of server IDs to export. If not provided, all active servers are exported.",
    )


class ExportMcpServersResponse(BaseModel):
    """Response containing MCP servers in standard .mcp.json format.

    This matches the exact format used by Claude Code's .mcp.json configuration files.
    The response contains only the mcpServers object for direct compatibility.
    """

    mcpServers: Dict[str, StandardMcpServerConfig] = Field(
        default_factory=dict,
        description="MCP servers in standard format, keyed by server name",
    )


class ImportMcpServersRequest(BaseModel):
    """Request to import MCP servers from standard .mcp.json format."""

    mcpServers: Dict[str, StandardMcpServerConfig] = Field(
        ..., description="MCP servers in standard format"
    )
    overwrite_existing: bool = Field(
        False, description="Whether to overwrite existing servers with same name"
    )


class ImportMcpServersResponse(BaseModel):
    """Response after importing MCP servers."""

    success: bool = Field(..., description="Whether the import was successful")
    message: str = Field(..., description="Status message")
    imported_count: int = Field(
        ..., description="Number of servers successfully imported"
    )
    skipped_count: int = Field(
        ..., description="Number of servers skipped (already exist)"
    )
    failed_count: int = Field(
        ..., description="Number of servers that failed to import"
    )
    errors: List[Dict[str, str]] = Field(
        default_factory=list, description="List of errors encountered during import"
    )


class McpServerConfigRequest(BaseModel):
    """Request model for creating/updating MCP servers."""

    server_name: str = Field(
        ...,
        description="Display name for the MCP server",
        min_length=1,
        max_length=MCP_SERVER_NAME_MAX_LENGTH,
    )
    connection_type: str = Field(..., description="Connection type: stdio or http")
    server_url: Optional[str] = Field(
        None, description="Server URL (required for http connections)"
    )
    command: Optional[str] = Field(
        None, description="Command to execute (required for stdio connections)"
    )
    args: Optional[List[str]] = Field(
        None, description="Command arguments (for stdio connections)"
    )
    working_directory: Optional[str] = Field(
        None, description="Working directory for stdio process"
    )
    environment_variables: Optional[Dict[str, str]] = Field(
        None, description="Environment variables for the server"
    )
    auth_type: str = Field(
        ...,
        description="Authentication type: none, api_key, bearer, oauth2, oauth_host_identity, mcp_oauth, or custom",
    )
    auth_credentials: Optional[Dict[str, str]] = Field(
        None,
        description="Sensitive credentials to be encrypted (e.g., api_key, bearer_token)",
    )
    timeout_seconds: Optional[int] = Field(
        30, description="Request timeout in seconds", ge=1
    )
    max_retries: Optional[int] = Field(
        3, description="Maximum number of retry attempts", ge=0
    )
    retry_delay: Optional[float] = Field(
        1.0, description="Delay between retries in seconds", ge=0.0
    )
    description: Optional[str] = Field(
        None, description="Optional description of the MCP server"
    )
    visibility: Optional[McpServerVisibility] = Field(
        None, description="Server visibility (private or shared). Defaults to private."
    )
    shared_with_group_ids: Optional[List[str]] = Field(
        None,
        description="Group IDs to share with. Empty list or ['__all__'] for everyone. "
        "Only used when visibility is 'shared'.",
    )
    ssl_config: Optional[Dict[str, Any]] = Field(
        None,
        description="SSL/TLS configuration for http connections, e.g. {'verify': true|false}",
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: Optional[str]) -> Optional[str]:
        """Validate command is in allowlist and doesn't contain shell metacharacters.

        Security: Only permit specific, pre-approved commands to prevent arbitrary
        command execution. This is critical for stdio MCP servers.

        Configuration: Customize via MCP_ALLOWED_COMMANDS and MCP_DANGEROUS_CHARS_COMMAND
        environment variables.
        """
        if v is None:
            return v

        import os

        # STEP 1: Block shell metacharacters FIRST (before parsing)
        # This prevents injection attempts like "node; ls /tmp"
        dangerous_chars = _get_dangerous_chars_command()
        for char in dangerous_chars:
            if char in v:
                raise ValueError(
                    f"Command contains dangerous shell metacharacter '{char}'. "
                    "Only simple command names are allowed."
                )

        # STEP 2: Extract base command name (handle paths)
        base_cmd = os.path.basename(v.strip())

        # STEP 3: Check against allowlist
        allowed_commands = _get_allowed_commands()
        if base_cmd not in allowed_commands:
            raise ValueError(
                f"Command '{base_cmd}' is not in the allowlist. "
                f"Permitted commands: {', '.join(sorted(allowed_commands))}"
            )

        return v.strip()

    @field_validator("args")
    @classmethod
    def validate_args(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate args don't contain shell metacharacters.

        Security: Prevent command injection through argument values.

        Configuration: Customize via MCP_DANGEROUS_CHARS_ARGS environment variable.
        """
        if v is None:
            return v

        # Block shell metacharacters in arguments
        dangerous_chars = _get_dangerous_chars_args()

        for i, arg in enumerate(v):
            if not isinstance(arg, str):
                raise ValueError(f"Argument at index {i} must be a string")

            for char in dangerous_chars:
                if char in arg:
                    raise ValueError(
                        f"Argument at index {i} ('{arg[:50]}...') contains dangerous "
                        f"shell metacharacter '{char}'. Arguments should not contain "
                        "shell metacharacters."
                    )

        return v

    @field_validator("connection_type")
    @classmethod
    def validate_connection_type(cls, v: str) -> str:
        """Validate connection type is one of the allowed values."""
        allowed = {"stdio", "http"}
        if v not in allowed:
            raise ValueError(
                f"Invalid connection_type. Must be one of: {', '.join(allowed)}"
            )
        return v

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """Validate auth type is one of the allowed values."""
        allowed = {
            "none",
            "api_key",
            "bearer",
            "oauth2",
            "oauth_host_identity",
            "custom",
            "mcp_oauth",
        }
        if v not in allowed:
            raise ValueError(f"Invalid auth_type. Must be one of: {', '.join(allowed)}")
        return v

    @field_validator("server_url")
    @classmethod
    def validate_server_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate server URL format when provided."""
        if v is None:
            return v

        # Parse the URL to validate its structure
        try:
            parsed = urlparse(v)

            # Check that scheme and netloc (domain) are present
            if not parsed.scheme:
                raise ValueError(
                    "Server URL must include a scheme (e.g., http://, https://, ws://, wss://)"
                )

            if not parsed.netloc:
                raise ValueError("Server URL must include a valid domain or IP address")

            # For http/websocket connections, validate appropriate schemes
            valid_schemes = {"http", "https", "ws", "wss"}
            if parsed.scheme not in valid_schemes:
                raise ValueError(
                    f"Server URL scheme must be one of: {', '.join(valid_schemes)}"
                )

            return v
        except ValueError:
            # Re-raise ValueError from our validation above
            raise
        except Exception as e:
            raise ValueError(f"Invalid server URL format: {str(e)}")

    @model_validator(mode="after")
    def validate_connection_requirements(self):
        """Validate connection-type-specific required fields."""
        if self.connection_type == "stdio":
            if not self.command:
                raise ValueError("command is required for stdio connection_type")
        elif self.connection_type == "http":
            if not self.server_url:
                raise ValueError(
                    f"server_url is required for {self.connection_type} connection_type"
                )

        return self

    @model_validator(mode="after")
    def validate_auth_requirements(self):
        """Validate auth credentials are provided when needed.

        Note: This validation is lenient to allow updating servers without
        re-providing credentials. The route handler will preserve existing
        credentials if auth_credentials is not provided.
        """
        # OAuth2 doesn't require credentials to be provided (handled separately)
        # For other auth types, credentials are optional on update (existing preserved)
        # But if creating a new server with auth, credentials should be provided
        # However, we can't distinguish create vs update at the model level,
        # so we make this validation lenient and handle it in the route
        return self


class McpServerInfo(BaseModel):
    """Response model for MCP server information."""

    id: Optional[str] = Field(None, description="Server unique identifier")
    service_name: str = Field(..., description="The full service name with prefix")
    server_name: str = Field(..., description="Display name for the server")
    connection_type: str = Field(
        ..., description="Connection type (stdio/http/websocket)"
    )
    server_url: Optional[str] = Field(None, description="Server URL if applicable")
    command: Optional[str] = Field(None, description="Command if stdio connection")
    auth_type: str = Field(..., description="Authentication type")
    credentials_configured: bool = Field(
        ..., description="Whether credentials are stored"
    )
    description: Optional[str] = Field(None, description="Server description")
    is_active: bool = Field(..., description="Whether the server is active")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    config_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Non-sensitive configuration details"
    )
    visibility: McpServerVisibility = Field(
        McpServerVisibility.PRIVATE, description="Server visibility (private or shared)"
    )
    shared_with_group_ids: List[str] = Field(
        default_factory=list,
        description="Group IDs this server is shared with. ['__all__'] means everyone.",
    )
    shared_with_group_names: List[str] = Field(
        default_factory=list,
        description="Human-readable group names (for display).",
    )
    is_template: bool = Field(
        False, description="Whether this server was cloned from a public server"
    )
    original_server_id: Optional[str] = Field(
        None, description="ID of original server if this is a clone"
    )
    clone_count: int = Field(
        0,
        description="Number of times this server has been cloned (for public servers)",
    )
    creator_name: Optional[str] = Field(
        None, description="Name of user who created this server (for public servers)"
    )
    creator_id: Optional[str] = Field(
        None, description="ID of user who created this server (for public servers)"
    )
    is_owned_by_current_user: bool = Field(
        True, description="Whether the current user owns this server"
    )


class ListMcpServersResponse(BaseModel):
    """Response for listing all MCP servers."""

    success: bool = Field(..., description="Whether the request was successful")
    servers: List[McpServerInfo] = Field(
        ..., description="List of configured MCP servers"
    )


class SaveMcpServerResponse(BaseModel):
    """Response after saving MCP server."""

    success: bool = Field(..., description="Whether the save was successful")
    message: str = Field(..., description="Status message")
    server: McpServerInfo = Field(..., description="Saved server information")


class DeleteMcpServerResponse(BaseModel):
    """Response after deleting MCP server."""

    success: bool = Field(..., description="Whether the delete was successful")
    message: str = Field(..., description="Status message")


class McpToolInfo(BaseModel):
    """Information about a tool available from an MCP server."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")


class TestMcpConnectionResponse(BaseModel):
    """Response from testing an MCP server connection."""

    success: bool = Field(..., description="Whether connection succeeded")
    server_name: str = Field(..., description="Name of the tested server")
    tool_count: int = Field(..., description="Number of tools discovered")
    tools: List[McpToolInfo] = Field(
        default_factory=list,
        description="List of available tools with names and descriptions",
    )
    error: Optional[str] = Field(None, description="Error message if connection failed")
    connection_type: str = Field(
        ..., description="The connection type used (stdio/http/websocket)"
    )


class McpServerForAgentConfig(BaseModel):
    """MCP server configuration for agent tool creation with decrypted credentials."""

    service_name: str = Field(..., description="Full service name (mcp_server_<name>)")
    server_name: str = Field(..., description="Display name")
    connection_type: str = Field(..., description="Connection type (stdio/http)")
    server_url: Optional[str] = Field(
        None, description="Server URL for http connections"
    )
    command: Optional[str] = Field(None, description="Command for stdio connections")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    working_directory: Optional[str] = Field(None, description="Working directory")
    environment_variables: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    auth_type: str = Field(..., description="Authentication type")
    auth_config: Dict[str, Any] = Field(
        default_factory=dict, description="Auth config with decrypted credentials"
    )
    timeout_seconds: int = Field(30, description="Timeout in seconds")
    max_retries: int = Field(3, description="Max retry attempts")
    retry_delay: float = Field(1.0, description="Retry delay in seconds")
    description: Optional[str] = Field(None, description="Server description")
    has_credential_error: bool = Field(
        False, description="True if credential decryption failed for this server"
    )


class GetMcpServersForAgentResponse(BaseModel):
    """Response for getting MCP servers configured for agent tool creation."""

    success: bool = Field(..., description="Whether the request was successful")
    servers: List[McpServerForAgentConfig] = Field(
        default_factory=list, description="List of MCP servers with full configuration"
    )


class CloneMcpServerRequest(BaseModel):
    """Request to clone a public MCP server."""

    source_server_id: str = Field(..., description="ID of the public server to clone")
    new_server_name: str = Field(
        ...,
        description="Name for the cloned server",
        min_length=1,
        max_length=MCP_SERVER_NAME_MAX_LENGTH,
    )


class CloneMcpServerResponse(BaseModel):
    """Response after cloning a server."""

    success: bool = Field(..., description="Whether clone was successful")
    message: str = Field(..., description="Status message")
    server: McpServerInfo = Field(..., description="Cloned server information")


class ListPublicMcpServersResponse(BaseModel):
    """Response for listing public MCP servers."""

    success: bool = Field(..., description="Whether the request was successful")
    servers: List[McpServerInfo] = Field(
        ..., description="List of public MCP servers from all users"
    )


# ── MCP Integration (Official Provider) Models ──────────────────────────


class McpIntegrationSummary(BaseModel):
    """Summary info for an official MCP integration."""

    provider: str = Field(..., description="Provider identifier (e.g. 'github')")
    display_name: str = Field(..., description="Human-readable provider name")
    is_configured: bool = Field(..., description="Whether user has saved a config")
    is_active: bool = Field(True, description="Whether the integration is enabled")
    has_system_default: bool = Field(
        False, description="Whether a system-wide default is configured"
    )
    has_group_default: bool = Field(
        False, description="Whether a group-level default is configured for this user"
    )
    group_names: List[str] = Field(
        default_factory=list,
        description="Names of groups that provision this tool for the user",
    )
    tool_count: Optional[int] = Field(
        None,
        description="Number of explicitly managed tools; None means all tools enabled (unmanaged)",
    )
    tool_permissions: Dict[str, bool] = Field(
        default_factory=dict, description="Tool name -> enabled mapping"
    )


class ListMcpIntegrationsResponse(BaseModel):
    """Response for listing all official MCP integrations."""

    success: bool = Field(..., description="Whether the request was successful")
    integrations: List[McpIntegrationSummary] = Field(
        ..., description="List of all official integrations with status"
    )


class McpIntegrationConfig(BaseModel):
    """Full configuration for an official MCP integration."""

    provider: str = Field(..., description="Provider identifier")
    display_name: str = Field(..., description="Human-readable provider name")
    is_configured: bool = Field(..., description="Whether user has saved a config")
    is_active: bool = Field(True, description="Whether the integration is enabled")
    has_system_default: bool = Field(False, description="Whether system default exists")
    has_group_default: bool = Field(
        False, description="Whether a group-level default is configured for this user"
    )
    group_names: List[str] = Field(
        default_factory=list,
        description="Names of groups that provision this tool for the user",
    )
    credentials_configured: bool = Field(
        False, description="Whether credentials are stored"
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Non-sensitive config (connection details, metadata, etc.)",
    )
    tool_permissions: Dict[str, bool] = Field(
        default_factory=dict, description="Tool name -> enabled mapping"
    )


class GetMcpIntegrationResponse(BaseModel):
    """Response for getting a single integration config."""

    success: bool = Field(..., description="Whether the request was successful")
    integration: McpIntegrationConfig = Field(
        ..., description="Integration configuration"
    )


class SaveMcpIntegrationRequest(BaseModel):
    """Request to save an official MCP integration config."""

    credentials: Optional[Dict[str, str]] = Field(
        None, description="Sensitive credentials to encrypt (PATs, tokens, etc.)"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None,
        description="Non-sensitive configuration (URLs, metadata, tool_permissions, etc.)",
    )
    is_active: bool = Field(True, description="Whether to enable the integration")

    @field_validator("credentials")
    @classmethod
    def validate_credentials(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Validate credentials are not empty strings."""
        if v is None:
            return v
        for key, val in v.items():
            if isinstance(val, str) and not val.strip():
                raise ValueError(f"Credential '{key}' cannot be empty")
        return v


class SaveMcpIntegrationResponse(BaseModel):
    """Response after saving an integration config."""

    success: bool = Field(..., description="Whether the save was successful")
    message: str = Field(..., description="Status message")
    integration: McpIntegrationConfig = Field(
        ..., description="Updated integration config"
    )


class DeleteMcpIntegrationResponse(BaseModel):
    """Response after deleting an integration config."""

    success: bool = Field(..., description="Whether the delete was successful")
    message: str = Field(..., description="Status message")


class McpIntegrationForWorkflowResponse(BaseModel):
    """Response for getting integration config ready for workflow node population."""

    success: bool = Field(..., description="Whether the request was successful")
    configured: bool = Field(..., description="Whether the integration is configured")
    mcp_server_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Full MCP server config ready for workflow node, or None if not configured",
    )
