"""Constants for user settings API."""

import re
from enum import Enum


class ExternalServiceName(str, Enum):
    """Allowed external service names."""

    TAVILY = "tavily"
    EMAIL = "email"


# Set of allowed service names for validation
ALLOWED_SERVICE_NAMES = {service.value for service in ExternalServiceName}

# MCP Server Constants
MCP_SERVER_PREFIX = "mcp_server_"
# Database service_name column is 50 chars; effective limit for user-provided name
# is 50 - len(MCP_SERVER_PREFIX) = 39 to avoid DB errors
MCP_SERVER_NAME_MAX_LENGTH = 50 - len(MCP_SERVER_PREFIX)
# Allow alphanumeric, spaces, and most special chars (exclude path separators, quotes, wildcards)
MCP_SERVER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9 _\-#@!$%&()+={}\[\];',.]+$")


def is_mcp_server(service_name: str) -> bool:
    """Check if a service name represents an MCP server.

    Args:
        service_name: The full service name from the database

    Returns:
        True if the service name starts with the MCP server prefix
    """
    return service_name.startswith(MCP_SERVER_PREFIX)


def extract_mcp_server_name(service_name: str) -> str:
    """Extract the user-provided name from a full MCP service name.

    Args:
        service_name: The full service name (e.g., "mcp_server_my_server")

    Returns:
        The user-provided server name (e.g., "my_server")

    Raises:
        ValueError: If the service name is not a valid MCP server name
    """
    if not is_mcp_server(service_name):
        raise ValueError(f"Service name '{service_name}' is not an MCP server")
    return service_name[len(MCP_SERVER_PREFIX) :]


def build_mcp_service_name(server_name: str) -> str:
    """Construct the full service name from a user-provided server name.

    Args:
        server_name: The user-provided server name (e.g., "my_server")

    Returns:
        The full service name (e.g., "mcp_server_my_server")
    """
    return f"{MCP_SERVER_PREFIX}{server_name}"


# MCP Integration (Official Provider) Constants
MCP_PRESET_PREFIX = "mcp_preset_"

OFFICIAL_PROVIDERS = [
    "github",
    "atlassian",
    "databricks",
    "databricks_devops",
    "sharepoint",
    "onedrive",
    "notion",
    "fabric",
]

OFFICIAL_PROVIDER_DISPLAY_NAMES = {
    "github": "GitHub",
    "atlassian": "Atlassian",
    "databricks": "Databricks",
    "databricks_devops": "Databricks DevOps",
    "sharepoint": "SharePoint",
    "onedrive": "OneDrive",
    "notion": "Notion",
    "fabric": "Microsoft Fabric",
}


def is_mcp_preset(service_name: str) -> bool:
    """Check if a service name represents an official MCP integration preset."""
    return service_name.startswith(MCP_PRESET_PREFIX)


def build_mcp_preset_name(provider: str) -> str:
    """Construct the full service name from a provider identifier.

    Args:
        provider: Provider identifier (e.g., "github")

    Returns:
        Full service name (e.g., "mcp_preset_github")
    """
    return f"{MCP_PRESET_PREFIX}{provider}"


def extract_preset_provider(service_name: str) -> str:
    """Extract the provider identifier from a full preset service name.

    Args:
        service_name: Full service name (e.g., "mcp_preset_github")

    Returns:
        Provider identifier (e.g., "github")

    Raises:
        ValueError: If the service name is not a valid MCP preset
    """
    if not is_mcp_preset(service_name):
        raise ValueError(f"Service name '{service_name}' is not an MCP preset")
    return service_name[len(MCP_PRESET_PREFIX) :]


def validate_mcp_server_name(server_name: str) -> None:
    """Validate an MCP server name.

    Args:
        server_name: The user-provided server name to validate

    Raises:
        ValueError: If the server name is invalid
    """
    if not server_name:
        raise ValueError("Server name cannot be empty")

    if len(server_name) > MCP_SERVER_NAME_MAX_LENGTH:
        raise ValueError(
            f"Server name cannot exceed {MCP_SERVER_NAME_MAX_LENGTH} characters"
        )

    if not MCP_SERVER_NAME_PATTERN.match(server_name):
        raise ValueError(
            'Server name cannot contain path separators (/\\), quotes ("), wildcards (*?), pipes (|), colons (:), or angle brackets (<>)'
        )
