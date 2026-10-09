"""Preset helpers for MCP server configurations.

Auth Type Conventions:
- "bearer": Static bearer token authentication (uses "token" or "bearer_token" field in auth_config)
- "oauth2": Static OAuth2 access token (uses "access_token" or "token" field in auth_config)
- "oauth": Dynamic OAuth flow requiring provider and user_id in auth_config (no direct token mapping)
          The token is fetched dynamically at runtime based on provider and user_id
- "api_key": API key authentication (uses "api_key" or "key" field in auth_config)
- "custom": Custom authentication (auth_config passed through as-is)
- "none": No authentication required
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


# Provider constants
PROVIDER_GITHUB = "github"
PROVIDER_NOTION = "notion"
PROVIDER_ATLASSIAN = "atlassian"
PROVIDER_DATABRICKS = "databricks"
PROVIDER_SHAREPOINT = "sharepoint"
PROVIDER_ONEDRIVE = "onedrive"
PROVIDER_DATABRICKS_DEVOPS = "databricks_devops"
PROVIDER_FABRIC = "fabric"


def get_provider_defaults(provider: str) -> Dict[str, Any]:
    """Get default configuration values for a specific MCP provider.

    Args:
        provider: The provider identifier ('github', 'notion', or empty).

    Returns:
        Dict with default configuration values for the provider.
    """
    if provider == PROVIDER_GITHUB:
        return {
            "provider": PROVIDER_GITHUB,
            "server_name": "GitHub MCP Server",
            "connection_type": "http",
            "server_url": "https://api.githubcopilot.com/mcp",
            "auth_type": "bearer",
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "description": "GitHub Copilot MCP Server for repository access",
        }
    elif provider == PROVIDER_NOTION:
        return {
            "provider": PROVIDER_NOTION,
            "server_name": "Notion MCP Server",
            "connection_type": "http",
            "server_url": "https://mcp.notion.com/mcp",
            "auth_type": "oauth",
            "auth_config": {"provider": "notion"},
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "Notion MCP Server for workspace access",
        }
    elif provider == PROVIDER_ATLASSIAN:
        return {
            "provider": PROVIDER_ATLASSIAN,
            "server_name": "Atlassian",
            "connection_type": "http",
            "server_url": "https://mcp.atlassian.com/v1/mcp",
            "auth_type": "mcp_oauth",
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "Atlassian MCP Server for Jira, Confluence, and Bitbucket",
        }
    elif provider == PROVIDER_DATABRICKS:
        return {
            "provider": PROVIDER_DATABRICKS,
            "server_name": "Databricks Catalog MCP Server",
            "connection_type": "http",
            "server_url": "",
            "auth_type": "bearer",
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "Databricks Catalog MCP Server for Unity Catalog functions",
        }
    elif provider == PROVIDER_ONEDRIVE:
        return {
            "provider": PROVIDER_ONEDRIVE,
            "server_name": "OneDrive MCP Server",
            "connection_type": "stdio",
            "command": "python",
            "args": ["-m", "backend.tools.onedrive_mcp"],
            "auth_type": "oauth",
            "auth_config": {"provider": "microsoft"},
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "OneDrive MCP Server for personal and shared file access",
        }
    elif provider == PROVIDER_SHAREPOINT:
        return {
            "provider": PROVIDER_SHAREPOINT,
            "server_name": "SharePoint MCP Server",
            "connection_type": "stdio",
            "command": "python",
            "args": ["-m", "backend.tools.sharepoint_mcp"],
            "auth_type": "oauth",
            "auth_config": {"provider": "microsoft"},
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "SharePoint MCP Server for document library and site access",
        }
    elif provider == PROVIDER_DATABRICKS_DEVOPS:
        return {
            "provider": PROVIDER_DATABRICKS_DEVOPS,
            "server_name": "Databricks DevOps MCP Server",
            "connection_type": "stdio",
            "command": "python",
            "args": ["-m", "backend.tools.databricks_devops_mcp"],
            "auth_type": "custom",
            "auth_config": {},
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "Databricks workspace & Azure DevOps notebook management",
        }
    elif provider == PROVIDER_FABRIC:
        return {
            "provider": PROVIDER_FABRIC,
            "server_name": "Microsoft Fabric MCP Server",
            "connection_type": "stdio",
            "command": "python",
            "args": ["-m", "backend.tools.fabric_mcp"],
            "auth_type": "oauth",
            "auth_config": {"provider": "fabric"},
            "timeout_seconds": 60,
            "max_retries": 3,
            "retry_delay": 2.0,
            "description": "Microsoft Fabric MCP Server for workspaces, lakehouses, notebooks, and pipelines",
        }
    else:
        # Generic/empty provider defaults
        return {
            "provider": "",
            "server_name": "MCP Server",
            "connection_type": "stdio",
            "auth_type": "none",
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "description": "",
        }


def create_github_mcp_config(
    *,
    access_token: str = "",
    node_id: str = "github_mcp",
    node_name: str = "GitHub MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a GitHub Copilot MCP configuration.

    Args:
        access_token: GitHub personal access token for authentication.
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for GitHub.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_GITHUB,
        "server_name": "GitHub MCP Server",
        "connection_type": "http",
        "server_url": "https://api.githubcopilot.com/mcp",
        "auth_type": "bearer",
        "auth_config": {"access_token": access_token} if access_token else {},
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description or "GitHub Copilot MCP Server",
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to GitHub MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created GitHub MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


# Default command arguments for the Notion MCP remote server via mcp-remote
_DEFAULT_NOTION_REMOTE_ARGS = [
    "-y",
    "mcp-remote",
    "https://mcp.notion.com/mcp",
]


def create_notion_mcp_config(
    *,
    node_id: str = "notion_mcp_preset",
    node_name: str = "Notion MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the canonical Notion MCP configuration for stdio connections.

    This configuration uses npx mcp-remote for local stdio-based connections.
    For OAuth-based connections, use :func:`create_notion_oauth_mcp_config` instead.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_NOTION,
        "server_name": "Notion MCP Server",
        "connection_type": "stdio",
        "command": "npx",
        "args": list(_DEFAULT_NOTION_REMOTE_ARGS),
        "working_directory": "",
        "auth_type": "none",
        "auth_config": {},
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "environment_variables": {},
        "node_id": node_id,
        "node_name": node_name,
        "description": description or "Notion MCP Server",
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to Notion MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created base Notion MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


def create_notion_oauth_mcp_config(
    *,
    user_id: str,
    node_id: str = "notion_mcp_oauth",
    node_name: str = "Notion MCP Server",
    description: Optional[str] = None,
    workspace_label: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a Notion MCP config that uses OAuth for authentication.

    This configuration connects directly to https://mcp.notion.com/mcp
    using OAuth tokens managed by the OAuth service. The user_id is required
    to fetch the correct OAuth token.

    Args:
        user_id: The user's email/ID for OAuth token lookup.
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        workspace_label: Optional label for the Notion workspace.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for Notion OAuth.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_NOTION,
        "server_name": "Notion MCP Server",
        "connection_type": "http",
        "server_url": "https://mcp.notion.com/mcp",
        "auth_type": "oauth",
        "auth_config": {
            "provider": "notion",
            "user_id": user_id,
        },
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description or "Notion MCP with OAuth authentication",
        "workspace_label": workspace_label,
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to Notion OAuth MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created Notion OAuth MCP config",
            extra={"node_id": node_id, "user_id": user_id},
        )

    return config


def is_notion_oauth_config(config: Dict[str, Any]) -> bool:
    """Check if a config is for Notion OAuth authentication.

    Args:
        config: MCP server configuration dict.

    Returns:
        True if this is a Notion OAuth config.
    """
    auth_type = config.get("auth_type", "")
    auth_config = config.get("auth_config", {})
    provider = auth_config.get("provider", "")

    return auth_type == "oauth" and provider == "notion"


def create_databricks_mcp_config(
    *,
    workspace_hostname: str = "",
    catalog: str = "",
    schema: str = "",
    server_url: str = "",
    access_token: str = "",
    node_id: str = "databricks_mcp",
    node_name: str = "Databricks MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a Databricks Unity Catalog MCP configuration.

    The server URL can either be provided directly or constructed from
    workspace_hostname, catalog, and schema. If server_url is provided,
    it takes precedence.

    URL pattern: https://<workspace-hostname>/api/2.0/mcp/functions/<catalog>/<schema>

    Args:
        workspace_hostname: Databricks workspace hostname (e.g., adb-123.3.azuredatabricks.net).
        catalog: Unity Catalog name.
        schema: Schema name within the catalog.
        server_url: Full URL (overrides hostname/catalog/schema if provided).
        access_token: Databricks personal access token (dapi...).
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for Databricks.
    """
    if not server_url and workspace_hostname and catalog and schema:
        hostname = workspace_hostname.strip()
        if hostname.startswith("https://"):
            hostname = hostname[8:]
        elif hostname.startswith("http://"):
            hostname = hostname[7:]
        hostname = hostname.rstrip("/")
        server_url = f"https://{hostname}/api/2.0/mcp/functions/{catalog.strip()}/{schema.strip()}"

    config: Dict[str, Any] = {
        "provider": PROVIDER_DATABRICKS,
        "server_name": "Databricks MCP Server",
        "connection_type": "http",
        "server_url": server_url,
        "auth_type": "bearer",
        "auth_config": {"access_token": access_token} if access_token else {},
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description or "Databricks Unity Catalog MCP Server",
        "metadata": {
            "workspace_hostname": workspace_hostname,
            "catalog": catalog,
            "schema": schema,
        },
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to Databricks MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created Databricks MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


def is_databricks_config(config: Dict[str, Any]) -> bool:
    """Check if a config is for Databricks.

    Args:
        config: MCP server configuration dict.

    Returns:
        True if this is a Databricks config.
    """
    return config.get("provider") == PROVIDER_DATABRICKS


def create_sharepoint_mcp_config(
    *,
    tenant_id: str = "",
    client_id: str = "",
    client_secret: str = "",
    site_url: str = "",
    node_id: str = "sharepoint_mcp",
    node_name: str = "SharePoint MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a SharePoint MCP configuration using stdio transport.

    The SharePoint MCP server runs as a Python subprocess that wraps
    the Microsoft Graph API. Credentials are passed as environment variables.

    Args:
        tenant_id: Azure AD tenant ID.
        client_id: Azure AD app registration client ID.
        client_secret: Azure AD app registration client secret.
        site_url: Optional SharePoint site URL to scope access.
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for SharePoint.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_SHAREPOINT,
        "server_name": "SharePoint MCP Server",
        "connection_type": "stdio",
        "command": "python",
        "args": ["-m", "backend.tools.sharepoint_mcp"],
        "working_directory": "",
        "auth_type": "oauth",
        "auth_config": {"provider": "microsoft"},
        "environment_variables": {
            "SHAREPOINT_SITE_URL": site_url,
        },
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description or "SharePoint MCP Server for document access",
        "metadata": {
            "tenant_id": tenant_id,
            "site_url": site_url,
        },
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to SharePoint MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created SharePoint MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


def is_sharepoint_config(config: Dict[str, Any]) -> bool:
    """Check if a config is for SharePoint.

    Args:
        config: MCP server configuration dict.

    Returns:
        True if this is a SharePoint config.
    """
    return config.get("provider") == PROVIDER_SHAREPOINT


def create_onedrive_mcp_config(
    *,
    node_id: str = "onedrive_mcp",
    node_name: str = "OneDrive MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a OneDrive MCP configuration using stdio transport.

    The OneDrive MCP server runs as a Python subprocess that wraps
    the Microsoft Graph API. Authentication is handled via OAuth delegation.

    Args:
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for OneDrive.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_ONEDRIVE,
        "server_name": "OneDrive MCP Server",
        "connection_type": "stdio",
        "command": "python",
        "args": ["-m", "backend.tools.onedrive_mcp"],
        "working_directory": "",
        "auth_type": "oauth",
        "auth_config": {"provider": "microsoft"},
        "environment_variables": {},
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description
        or "OneDrive MCP Server for personal and shared file access",
        "metadata": {},
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to OneDrive MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created OneDrive MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


def is_onedrive_config(config: Dict[str, Any]) -> bool:
    """Check if a config is for OneDrive.

    Args:
        config: MCP server configuration dict.

    Returns:
        True if this is a OneDrive config.
    """
    return config.get("provider") == PROVIDER_ONEDRIVE


def create_databricks_devops_mcp_config(
    *,
    databricks_host: str = "",
    databricks_token: str = "",
    devops_org: str = "",
    devops_project: str = "",
    devops_repo: str = "",
    devops_pat: str = "",
    git_folder_path: str = "",
    node_id: str = "databricks_devops_mcp",
    node_name: str = "Databricks DevOps MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a Databricks DevOps MCP configuration using stdio transport.

    The Databricks DevOps MCP server bridges Databricks workspace operations
    with Azure DevOps Git operations. It reads from Databricks Workspace API,
    writes to Azure DevOps REST API, and syncs via Databricks Repos API.

    Args:
        databricks_host: Databricks workspace URL (e.g. https://adb-xxxx.azuredatabricks.net).
        databricks_token: Databricks personal access token.
        devops_org: Azure DevOps organization name.
        devops_project: Azure DevOps project name.
        devops_repo: Azure DevOps repository name.
        devops_pat: Azure DevOps personal access token.
        git_folder_path: Workspace path to the Git folder in Databricks.
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for Databricks DevOps.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_DATABRICKS_DEVOPS,
        "server_name": "Databricks DevOps MCP Server",
        "connection_type": "stdio",
        "command": "python",
        "args": ["-m", "backend.tools.databricks_devops_mcp"],
        "working_directory": "",
        "auth_type": "custom",
        "auth_config": {
            "databricks_token": databricks_token,
            "devops_pat": devops_pat,
        },
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description
        or "Databricks workspace & Azure DevOps notebook management",
        "metadata": {
            "databricks_host": databricks_host,
            "devops_org": devops_org,
            "devops_project": devops_project,
            "devops_repo": devops_repo,
            "git_folder_path": git_folder_path,
        },
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to Databricks DevOps MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created Databricks DevOps MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


def is_databricks_devops_config(config: Dict[str, Any]) -> bool:
    """Check if a config is for Databricks DevOps.

    Args:
        config: MCP server configuration dict.

    Returns:
        True if this is a Databricks DevOps config.
    """
    return config.get("provider") == PROVIDER_DATABRICKS_DEVOPS


def create_fabric_mcp_config(
    *,
    node_id: str = "fabric_mcp",
    node_name: str = "Microsoft Fabric MCP Server",
    description: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a Microsoft Fabric MCP configuration.

    Uses the ms-fabric-mcp-server PyPI package wrapped by
    ``backend.tools.fabric_mcp`` which injects a delegated OAuth token
    via the ``FABRIC_ACCESS_TOKEN`` environment variable.

    Args:
        node_id: Unique node identifier.
        node_name: Display name for the node.
        description: Optional description.
        overrides: Optional dict to override specific config values.

    Returns:
        Dict with MCP configuration for Microsoft Fabric.
    """
    config: Dict[str, Any] = {
        "provider": PROVIDER_FABRIC,
        "server_name": "Microsoft Fabric MCP Server",
        "connection_type": "stdio",
        "command": "python",
        "args": ["-m", "backend.tools.fabric_mcp"],
        "auth_type": "oauth",
        "auth_config": {"provider": "fabric"},
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay": 2.0,
        "node_id": node_id,
        "node_name": node_name,
        "description": description or "Microsoft Fabric MCP Server for workspaces, lakehouses, notebooks, and pipelines",
    }

    if overrides:
        config.update(overrides)
        logger.debug(
            "Applied overrides to Fabric MCP config",
            extra={"overrides": overrides, "resulting_keys": list(config.keys())},
        )
    else:
        logger.debug(
            "Created Fabric MCP config",
            extra={"node_id": node_id, "node_name": node_name},
        )

    return config


def is_fabric_config(config: Dict[str, Any]) -> bool:
    """Check if a config is for Microsoft Fabric.

    Args:
        config: MCP server configuration dict.

    Returns:
        True if this is a Microsoft Fabric config.
    """
    return config.get("provider") == PROVIDER_FABRIC
