"""MCP Client Manager for managing Model Context Protocol client connections and sessions.

Provides connection pooling, lifecycle management, and environment variable resolution.
"""

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import os
import platform
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ISG Security Finding #1 (Critical, Open):
# "Remote Code Execution In MCP Server Configuration".
#
# The "stdio" MCP connection type spawns an arbitrary local command/args taken
# from user-supplied server configuration, which is a Remote Code Execution
# vector. stdio MCP servers are DISABLED in code (and hidden in the UI). HTTP
# MCP connections are unaffected.
# TODO(security): re-enable only once stdio commands are sandboxed.
# ---------------------------------------------------------------------------


@dataclass
class _ToolCacheEntry:
    """Cached MCP tool definitions with metadata."""

    tools: List[Any]
    timestamp: float
    server_name: str
    tool_count: int
    access_count: int = 0


class McpClientManager:
    """Manages MCP client connections and tool loading."""

    def __init__(self):
        """Initialize MCP client manager."""
        self._active_clients: Dict[str, Any] = {}
        self._client_sessions: Dict[str, ClientSession] = {}
        # Tool definition cache — avoids repeated MCP handshakes
        self._tool_cache: Dict[str, _ToolCacheEntry] = {}
        self._tool_cache_lock = threading.Lock()
        self._tool_cache_ttl = int(os.getenv("MCP_TOOL_CACHE_TTL_SECONDS", "300"))
        self._tool_cache_max_size = int(os.getenv("MCP_TOOL_CACHE_MAX_SIZE", "50"))

    @staticmethod
    def _resolve_environment_variables(
        env_map: Optional[Dict[str, str]],
    ) -> Dict[str, str]:
        """Resolve environment variables, expanding secret references."""
        resolved: Dict[str, str] = {}
        if not env_map:
            return resolved

        for key, value in env_map.items():
            if value is None:
                continue
            if isinstance(value, str) and value.startswith("secret://"):
                secret_ref = value[len("secret://") :].strip()
                if not secret_ref:
                    continue
                secret_env_key = f"MCP_SECRET_{secret_ref.upper()}"
                secret_value = os.getenv(secret_env_key) or os.getenv(secret_ref)
                if secret_value:
                    resolved[key] = secret_value
                else:
                    logger.warning(
                        f"[McpClientManager] Secret for key '{key}' not found in environment"
                    )
            else:
                resolved[key] = str(value)
        return resolved

    @staticmethod
    def _run_coroutine_sync(
        coroutine_factory: Callable[[], Awaitable[Any]], timeout: Optional[float] = None
    ) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(coroutine_factory()))
                return future.result(timeout=timeout)
        return asyncio.run(coroutine_factory())

    def _ensure_sync_tool(self, tool: BaseTool) -> BaseTool:
        if isinstance(tool, StructuredTool):
            if getattr(tool, "func", None) is None and getattr(tool, "coroutine", None):
                async_coroutine = tool.coroutine

                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    call_kwargs = dict(kwargs) if kwargs else {}
                    call_args = list(args)
                    if (
                        call_args
                        and len(call_args) == 1
                        and isinstance(call_args[0], dict)
                    ):
                        call_kwargs = {**call_args[0], **call_kwargs}
                        call_args = []

                    metadata_keys = {
                        "config",
                        "run_manager",
                        "callbacks",
                        "tags",
                        "metadata",
                    }
                    for key in list(call_kwargs.keys()):
                        if key in metadata_keys:
                            call_kwargs.pop(key)

                    if call_args:
                        return self._run_coroutine_sync(
                            lambda: async_coroutine(*call_args, **call_kwargs)
                        )
                    return self._run_coroutine_sync(
                        lambda: async_coroutine(**call_kwargs)
                    )

                tool.func = sync_wrapper
                logger.debug(
                    f"[McpClientManager] Added sync wrapper to MCP tool {getattr(tool, 'name', '<unknown>')}"
                )
        return tool

    def _build_connection_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Translate internal config into langchain-mcp-adapters connection settings."""
        connection_type = config.get("connection_type", "stdio")

        if connection_type == "stdio":
            server_params = self._prepare_stdio_parameters(config)
            connection: Dict[str, Any] = {
                "transport": "stdio",
                "command": server_params.command,
                "args": list(server_params.args),
            }
            if server_params.env:
                connection["env"] = server_params.env
            if server_params.cwd:
                connection["cwd"] = str(server_params.cwd)
            if getattr(server_params, "encoding", None):
                connection["encoding"] = server_params.encoding
            if getattr(server_params, "encoding_error_handler", None):
                connection["encoding_error_handler"] = (
                    server_params.encoding_error_handler
                )
            return connection

        if connection_type == "http":
            http_params = self._prepare_http_parameters(config)

            from backend.services.guardrails.ssrf_mcp import validate_mcp_server_url

            blocked_reason = validate_mcp_server_url(http_params["url"])
            if blocked_reason:
                raise ValueError(blocked_reason)

            connection: Dict[str, Any] = {
                "transport": "streamable_http",
                "url": http_params["url"],
            }
            if http_params.get("headers"):
                connection["headers"] = http_params["headers"]
            if http_params.get("timeout") is not None:
                connection["timeout"] = http_params["timeout"]
            if http_params.get("sse_read_timeout") is not None:
                connection["sse_read_timeout"] = http_params["sse_read_timeout"]
            if http_params.get("auth"):
                connection["auth"] = http_params["auth"]

            # Apply SSL/TLS verification setting via a custom httpx client factory
            ssl_config = http_params.get("ssl_config") or {}
            verify_ssl = ssl_config.get("verify", True)
            connection["httpx_client_factory"] = self._build_http_client_factory(
                verify_ssl
            )
            return connection

        raise ValueError(
            f"Unsupported connection type for MCP tools: {connection_type}"
        )

    @staticmethod
    def _create_client_key(config: Dict[str, Any]) -> str:
        """Create a unique key for the MCP client configuration."""
        import json

        # Create a key based on essential connection parameters
        connection_type = config.get("connection_type", "stdio")

        if connection_type == "stdio":
            key_data = {
                "connection_type": connection_type,
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "working_directory": config.get("working_directory", ""),
            }
        elif connection_type == "http":
            key_data = {
                "connection_type": connection_type,
                "server_url": config.get("server_url", ""),
                "auth_type": config.get("auth_type", "none"),
                # Include auth identifiers but not sensitive tokens
                "auth_user": config.get("auth_config", {}).get("username", ""),
            }
        else:
            key_data = {
                "connection_type": connection_type,
                "server_url": config.get("server_url", ""),
            }

        return f"mcp_client_{hash(json.dumps(key_data, sort_keys=True))}"

    def _create_tool_cache_key(self, connection_config: Dict[str, Any]) -> str:
        """Create a cache key for tool definitions based on the effective connection config.

        Unlike _create_client_key (which excludes tokens for session pooling),
        this includes auth headers so different tokens get separate cache entries.
        """
        config_for_key = dict(connection_config)

        if "env" in config_for_key:
            # For stdio, env includes full os.environ copy — extract only
            # known token/credential env vars that affect tool availability
            env = config_for_key.pop("env", {})
            token_keys = [
                "SHAREPOINT_ACCESS_TOKEN",
                "ONEDRIVE_ACCESS_TOKEN",
                "DATABRICKS_TOKEN",
                "DEVOPS_PAT",
                "DATABRICKS_HOST",
                "DEVOPS_ORG",
                "DEVOPS_PROJECT",
                "DEVOPS_REPO",
            ]
            relevant_env = {k: env.get(k, "") for k in token_keys if env.get(k)}
            if relevant_env:
                config_for_key["_auth_env"] = relevant_env

        canonical = json.dumps(config_for_key, sort_keys=True, default=str)
        config_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return f"mcp_tools_{config_hash}"

    def _prepare_server_parameters(self, config: Dict[str, Any]):
        """Prepare MCP server parameters from configuration."""
        connection_type = config.get("connection_type", "stdio")

        if connection_type == "stdio":
            return self._prepare_stdio_parameters(config)
        elif connection_type == "http":
            return self._prepare_http_parameters(config)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

    def _prepare_stdio_parameters(
        self, config: Dict[str, Any]
    ) -> StdioServerParameters:
        """Prepare stdio server parameters."""
        # ISG Security Finding #1 (Critical): stdio MCP servers spawn arbitrary
        # local commands from user config (RCE). Disabled in code.
        logger.warning(
            "[McpClientManager] Blocked stdio MCP connection: stdio transport is "
            "disabled (ISG Critical finding #1). Use an HTTP MCP connection."
        )
        raise ValueError(
            "stdio MCP connections are disabled for security reasons "
            "(remote code execution risk). Use an HTTP MCP connection instead."
        )

        command = config.get("command", "")
        args = config.get("args", [])
        working_dir = config.get("working_directory", None)
        environment_variables = config.get("environment_variables", {})

        if not command:
            raise ValueError("Command is required for stdio connection")

        # Handle empty working directory - convert to None
        if working_dir == "":
            working_dir = None

        # Resolve and validate command on all platforms
        import shutil

        original_command = command

        if platform.system() == "Windows":
            # First try to resolve the command as-is
            resolved_path = shutil.which(command)
            if resolved_path:
                # Use the resolved path (which includes proper extension)
                command = resolved_path
                logger.info(
                    f"[McpClientManager] Resolved '{original_command}' to '{command}'"
                )
            elif command.lower() in ["npx", "npm", "node"]:
                # Fallback: add .cmd extension
                command = f"{command}.cmd"
                logger.info(
                    f"[McpClientManager] Applied .cmd extension: '{original_command}' -> '{command}'"
                )
        else:
            # For Linux/macOS/Docker, validate command exists
            resolved_path = shutil.which(command)
            if not resolved_path:
                # Command not found in PATH
                raise ValueError(
                    f"Command '{command}' not found in PATH. "
                    f"Please ensure the command is installed and available. "
                    f"Supported: node, npm, npx (Node.js), uvx (Python uv), and other executables in PATH."
                )
            command = resolved_path
            logger.info(
                f"[McpClientManager] Resolved '{original_command}' to '{command}'"
            )

        # Resolve environment variables
        resolved_env = self._resolve_environment_variables(environment_variables)
        env = os.environ.copy()
        if resolved_env:
            env.update(resolved_env)

        # Inject credentials for Databricks DevOps provider (custom auth with two PATs)
        config_provider = config.get("provider", "")
        if config_provider == "databricks_devops":
            auth_config = config.get("auth_config", {})
            metadata = config.get("metadata", {})

            # Inject auth tokens as env vars
            if auth_config.get("databricks_token"):
                env["DATABRICKS_TOKEN"] = auth_config["databricks_token"]
            if auth_config.get("devops_pat"):
                env["DEVOPS_PAT"] = auth_config["devops_pat"]

            # Inject connection metadata as env vars
            if metadata.get("databricks_host"):
                env["DATABRICKS_HOST"] = metadata["databricks_host"]
            if metadata.get("devops_org"):
                env["DEVOPS_ORG"] = metadata["devops_org"]
            if metadata.get("devops_project"):
                env["DEVOPS_PROJECT"] = metadata["devops_project"]
            if metadata.get("devops_repo"):
                env["DEVOPS_REPO"] = metadata["devops_repo"]
            if metadata.get("git_folder_path"):
                env["DATABRICKS_GIT_FOLDER_PATH"] = metadata["git_folder_path"]

            logger.info(
                "[McpClientManager] Injected Databricks DevOps credentials as environment variables"
            )

        # Inject OAuth token for providers that use stdio + delegated OAuth
        auth_type = config.get("auth_type", "")
        auth_config = config.get("auth_config", {})
        provider = auth_config.get("provider", "")

        if auth_type == "oauth" and provider == "microsoft":
            user_id = auth_config.get("user_id", "")
            if user_id:
                try:
                    from .services.oauth.microsoft_handler import (
                        microsoft_oauth_handler,
                    )

                    token = self._run_coroutine_sync(
                        lambda: microsoft_oauth_handler.get_valid_token(user_id)
                    )
                    # Both servers use the same Microsoft Graph OAuth token
                    env["SHAREPOINT_ACCESS_TOKEN"] = token
                    env["ONEDRIVE_ACCESS_TOKEN"] = token
                    logger.info(
                        f"[McpClientManager] Injected Microsoft OAuth token as SHAREPOINT_ACCESS_TOKEN "
                        f"and ONEDRIVE_ACCESS_TOKEN (token length: {len(token)})"
                    )
                except ValueError as e:
                    logger.warning(
                        f"[McpClientManager] No Microsoft OAuth token for user: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"[McpClientManager] Failed to get Microsoft OAuth token: {e}"
                    )
            else:
                logger.warning(
                    "[McpClientManager] Microsoft OAuth configured for stdio but no user_id in auth_config"
                )

        elif auth_type == "oauth" and provider == "fabric":
            user_id = auth_config.get("user_id", "")
            if user_id:
                try:
                    from .services.oauth.microsoft_handler import (
                        fabric_oauth_handler,
                    )

                    token = self._run_coroutine_sync(
                        lambda: fabric_oauth_handler.get_valid_token(user_id)
                    )
                    env["FABRIC_ACCESS_TOKEN"] = token
                    logger.info(
                        f"[McpClientManager] Injected Fabric OAuth token as FABRIC_ACCESS_TOKEN "
                        f"(token length: {len(token)})"
                    )

                    # Also inject SQL token (different audience — auto-acquire if needed)
                    try:
                        from .services.oauth.microsoft_handler import (
                            MicrosoftOAuthHandler,
                        )

                        _uid = user_id  # capture for lambda
                        sql_token = self._run_coroutine_sync(
                            lambda: fabric_oauth_handler.get_valid_cross_resource_token(
                                _uid,
                                target_scope=MicrosoftOAuthHandler.SQL_SCOPE,
                                target_provider="fabric_sql",
                            )
                        )
                        if sql_token:
                            env["FABRIC_SQL_TOKEN"] = sql_token
                            logger.info(
                                f"[McpClientManager] Injected Fabric SQL token as FABRIC_SQL_TOKEN "
                                f"(token length: {len(sql_token)})"
                            )
                    except Exception as e:
                        logger.debug(
                            f"[McpClientManager] SQL token not available (non-fatal): {e}"
                        )
                except ValueError as e:
                    logger.warning(
                        f"[McpClientManager] No Fabric OAuth token for user: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"[McpClientManager] Failed to get Fabric OAuth token: {e}"
                    )
            else:
                logger.warning(
                    "[McpClientManager] Fabric OAuth configured for stdio but no user_id in auth_config"
                )

        # Add detailed logging for debugging
        logger.info("[McpClientManager] Creating stdio server parameters:")
        logger.info(f"  Original command: {original_command}")
        logger.info(f"  Resolved command: {command}")
        logger.info(f"  Arguments: {args}")
        logger.info(f"  Working directory: {working_dir}")
        logger.info(f"  Platform: {platform.system()}")
        logger.info(f"  Environment variables added: {len(resolved_env)}")

        return StdioServerParameters(command=command, args=args, env=env)

    def _prepare_http_parameters(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare HTTP client parameters."""
        server_url = config.get("server_url", "")
        if not server_url:
            raise ValueError("Server URL is required for HTTP connection")

        # Build headers from configuration
        headers = {}

        # Add authentication headers
        # Auth type conventions (matching routes.py and mcp_presets.py):
        # - "bearer": Static bearer token (uses "token" or "bearer_token" field)
        # - "oauth2": Static OAuth2 access token (uses "access_token" or "token" field)
        # - "oauth": Dynamic OAuth flow requiring provider and user_id (fetches token at runtime)
        # - "oauth_host_identity": Cloud provider managed identity (AWS/Azure)
        # - "api_key": API key authentication (uses "api_key" or "key" field)
        # - "custom": Custom authentication (pass through as-is)
        auth_type = config.get("auth_type", "none")
        auth_config = config.get("auth_config", {})

        if auth_type == "bearer" or auth_type == "oauth2":
            # Handle Bearer token (PAT or OAuth access token)
            # For bearer: looks for "token" field
            # For oauth2: tries to get runtime user token from execution context first,
            #             then falls back to static "access_token" field
            if auth_type == "bearer":
                token = auth_config.get("token") or auth_config.get("access_token")

                # Validate bearer token if it looks like a JWT (has 3 parts separated by dots)
                if token and token.count(".") == 2:
                    from backend.services.auth.token_validator import (
                        validate_token_for_mcp,
                        log_token_details,
                    )

                    # Log detailed token information for debugging
                    log_token_details(token, context="Bearer MCP Auth")

                    # Validate token is not expired
                    is_valid, validation_error = validate_token_for_mcp(token)
                    if not is_valid:
                        logger.warning(
                            f"[McpClientManager] Bearer token validation failed: {validation_error}"
                        )
                        logger.warning(
                            "[McpClientManager] Bearer token has expired, but passing it anyway. "
                            "The downstream MCP server may reject it. "
                            "Consider using a non-expiring PAT or implement token refresh."
                        )
                        # Pass the token anyway - let the MCP server decide if it's acceptable
            else:  # oauth2 - User Identity authentication
                # First try to get the user's access token from execution context
                token = None
                try:
                    from backend.services.execution.context import (
                        get_current_user_access_token,
                    )

                    token = get_current_user_access_token()
                    if token:
                        logger.debug(
                            f"[McpClientManager] Using user's JWT token from execution context for oauth2 auth (length: {len(token)})"
                        )
                except Exception as e:
                    logger.warning(
                        f"[McpClientManager] Failed to get user token from execution context: {e}"
                    )

                # Fallback to static token in auth_config if available
                # NOTE: This should rarely happen for oauth2 - tokens should come from execution context
                if not token:
                    token = auth_config.get("access_token") or auth_config.get("token")
                    if token:
                        logger.warning(
                            f"[McpClientManager] Using static access_token from auth_config for oauth2 (length: {len(token)}). "
                            f"This is unusual - oauth2 should use dynamic user tokens from execution context. "
                            f"This static token may be expired. Consider removing credentials from MCP server config."
                        )

                # Validate token expiration before using it
                if token:
                    from backend.services.auth.token_validator import (
                        validate_token_for_mcp,
                        log_token_details,
                    )

                    # Log detailed token information for debugging
                    log_token_details(token, context="OAuth2 MCP Auth")

                    # Validate token is not expired
                    is_valid, validation_error = validate_token_for_mcp(token)
                    if not is_valid:
                        logger.warning(
                            f"[McpClientManager] Token validation failed: {validation_error}"
                        )
                        logger.warning(
                            "[McpClientManager] OAuth2 token has expired, but passing it anyway. "
                            "The downstream MCP server may reject it. "
                            "Agentic Studio should implement token refresh logic to get fresh tokens."
                        )
                        # Pass the token anyway - let the MCP server decide if it's acceptable

            if token:
                headers["Authorization"] = f"Bearer {token}"
                # Log token length for debugging (but not the actual token)
                logger.info(
                    f"[McpClientManager] Added Bearer token authentication (token length: {len(token)})"
                )
            else:
                logger.warning(
                    f"[McpClientManager] {auth_type} auth configured but no token found in auth_config or execution context"
                )
        elif auth_type == "oauth":
            # Handle OAuth with dynamic token fetch (e.g., Notion MCP)
            # Expects provider and user_id in auth_config
            provider = auth_config.get("provider", "")
            user_id = auth_config.get("user_id", "")

            if provider == "notion" and user_id:
                try:
                    from .services.oauth.notion_handler import notion_oauth_handler

                    # Get valid token (auto-refreshes if expired)
                    token = self._run_coroutine_sync(
                        lambda: notion_oauth_handler.get_valid_token(user_id)
                    )
                    headers["Authorization"] = f"Bearer {token}"
                    logger.info(
                        f"[McpClientManager] Added Notion OAuth token for user (token length: {len(token)})"
                    )
                except ValueError as e:
                    logger.warning(
                        f"[McpClientManager] No Notion OAuth token found for user: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"[McpClientManager] Failed to get Notion OAuth token: {e}"
                    )
            elif provider == "databricks" and auth_config.get("client_id"):
                # Databricks OAuth M2M (service principal client_credentials flow)
                workspace_hostname = auth_config.get("workspace_hostname", "")
                client_id = auth_config.get("client_id", "")
                client_secret = auth_config.get("client_secret", "")

                if workspace_hostname and client_id and client_secret:
                    from .services.oauth.databricks_handler import DatabricksM2MHandler

                    handler = DatabricksM2MHandler(
                        workspace_hostname, client_id, client_secret
                    )
                    token = self._run_coroutine_sync(lambda: handler.get_valid_token())
                    headers["Authorization"] = f"Bearer {token}"
                    logger.info(
                        f"[McpClientManager] Added Databricks M2M OAuth token (token length: {len(token)})"
                    )
                else:
                    logger.warning(
                        "[McpClientManager] Databricks OAuth configured but missing workspace_hostname, "
                        "client_id, or client_secret in auth_config"
                    )
            elif provider and not user_id and provider != "databricks":
                logger.warning(
                    f"[McpClientManager] OAuth provider '{provider}' configured but no user_id provided"
                )
        elif auth_type == "mcp_oauth":
            # Handle generic MCP OAuth with dynamic token fetch
            # Expects server_name, user_id, and server_url in auth_config
            server_name = auth_config.get("server_name", "")
            user_id = auth_config.get("user_id", "")
            server_url = auth_config.get("server_url", "")

            if server_name and user_id:
                try:
                    from .services.oauth.mcp_handler import McpOAuthHandler

                    handler = McpOAuthHandler(
                        server_url=server_url,
                        server_name=server_name,
                    )
                    # Get valid token (auto-refreshes if expired)
                    token = self._run_coroutine_sync(
                        lambda: handler.get_valid_token(user_id)
                    )
                    headers["Authorization"] = f"Bearer {token}"
                    logger.info("[McpClientManager] Added MCP OAuth token")
                except ValueError:
                    logger.warning("[McpClientManager] No MCP OAuth token found")
                except Exception:
                    logger.error("[McpClientManager] Failed to get MCP OAuth token")
            else:
                logger.warning(
                    "[McpClientManager] mcp_oauth configured but missing server_name or user_id"
                )
        elif auth_type == "oauth_host_identity":
            # Handle managed identity authentication (AWS/Azure)
            # Generates tokens dynamically using cloud provider credentials
            try:
                from .services.managed_identity_service import ManagedIdentityService

                # Get cloud provider from environment
                cloud_provider = os.getenv("CLOUD_PROVIDER", "none").lower()

                if cloud_provider in ["aws", "azure"]:
                    identity_service = ManagedIdentityService(cloud_provider)

                    # Get token parameters from auth_config
                    if cloud_provider == "azure":
                        resource = auth_config.get(
                            "resource", "https://database.windows.net/.default"
                        )
                        client_id = auth_config.get("client_id")
                        token = identity_service.get_token(
                            resource=resource, client_id=client_id
                        )
                    elif cloud_provider == "aws":
                        role_arn = auth_config.get("role_arn")
                        # For AWS, we might need to add the credentials to headers differently
                        # depending on the MCP server's expectations
                        # For now, treat it as a bearer token if we get JSON back
                        token = identity_service.get_token(role_arn=role_arn)

                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                        logger.info(
                            f"[McpClientManager] Added {cloud_provider.upper()} managed identity token (length: {len(token)})"
                        )
                    else:
                        logger.warning(
                            f"[McpClientManager] Failed to retrieve managed identity token for {cloud_provider}"
                        )
                else:
                    logger.warning(
                        f"[McpClientManager] oauth_host_identity requires CLOUD_PROVIDER to be 'aws' or 'azure', got: {cloud_provider}"
                    )
            except ImportError:
                logger.error(
                    "[McpClientManager] Managed identity service not available. Check dependencies."
                )
            except Exception as e:
                logger.error(
                    f"[McpClientManager] Failed to get managed identity token: {e}"
                )
        # Add required Accept header for HTTP Streamable protocol
        # The MCP server requires both application/json and text/event-stream
        headers["Accept"] = "application/json, text/event-stream"

        # Add any custom headers
        custom_headers = config.get("headers", {})
        headers.update(custom_headers)

        # Resolve environment variables in headers
        resolved_env = self._resolve_environment_variables(
            config.get("environment_variables", {})
        )
        for key, value in resolved_env.items():
            if key.startswith("HEADER_"):
                header_name = key[7:]  # Remove 'HEADER_' prefix
                headers[header_name] = value

        timeout = config.get("timeout_seconds", 30)
        sse_timeout = config.get(
            "sse_timeout_seconds", 300
        )  # 5 minutes default for SSE

        logger.info("[McpClientManager] Creating HTTP client parameters:")
        logger.info(f"  Server URL: {server_url}")
        logger.info(f"  Headers: {len(headers)} headers configured")
        logger.info(f"  Timeout: {timeout}s, SSE timeout: {sse_timeout}s")

        # Log headers for debugging (but mask sensitive data)
        safe_headers = {}
        for key, value in headers.items():
            if key.lower() == "authorization":
                safe_headers[key] = (
                    f"Bearer ***{value[-4:] if len(value) > 4 else '***'}"
                )
            else:
                safe_headers[key] = value
        logger.info(f"  Headers detail: {safe_headers}")

        # Extract SSL/TLS configuration (verify flag, defaults to True)
        ssl_config = config.get("ssl_config") or {}
        verify_ssl = ssl_config.get("verify", True)
        if not verify_ssl:
            logger.warning(
                f"[McpClientManager] SSL certificate verification is DISABLED for "
                f"server URL '{server_url}'. This should only be used for testing "
                f"with self-signed certificates, never in production."
            )

        return {
            "url": server_url,
            "headers": headers,
            "timeout": timeout,
            "sse_read_timeout": sse_timeout,
            "auth": None,  # For future OAuth implementation
            "ssl_config": ssl_config,
        }

    @asynccontextmanager
    async def get_client_session(self, config: Dict[str, Any]):
        """Get or create an MCP client session with proper lifecycle management."""
        client_key = self._create_client_key(config)
        server_name = config.get("server_name", "MCP Server")
        connection_type = config.get("connection_type", "stdio")

        # Check if we already have an active session for this configuration
        if client_key in self._client_sessions:
            logger.info(
                f"[McpClientManager] Reusing existing session for {server_name}"
            )
            yield self._client_sessions[client_key]
            return

        logger.info(
            f"[McpClientManager] Creating new session for {server_name} ({connection_type})"
        )

        try:
            # Prepare server parameters
            server_params = self._prepare_server_parameters(config)

            if connection_type == "stdio":
                async with self._create_stdio_session(
                    server_params, server_name, client_key
                ) as session:
                    yield session
            elif connection_type == "http":
                async with self._create_http_session(
                    server_params, server_name, client_key
                ) as session:
                    yield session
            else:
                raise ValueError(f"Unsupported connection type: {connection_type}")

        except Exception as e:
            logger.error(
                f"[McpClientManager] Failed to create session for {server_name}: {e}"
            )
            logger.error(f"[McpClientManager] Error type: {type(e).__name__}")
            # Clean up any partial state
            if client_key in self._client_sessions:
                del self._client_sessions[client_key]
            raise

    @asynccontextmanager
    async def _create_stdio_session(
        self, server_params, server_name: str, client_key: str
    ):
        """Create a stdio-based MCP session."""
        logger.info(
            f"[McpClientManager] Attempting to start stdio client for {server_name}"
        )
        logger.info(f"[McpClientManager] Command: {server_params.command}")
        logger.info(f"[McpClientManager] Args: {server_params.args}")

        try:
            # Create client connection
            async with stdio_client(server_params) as (read, write):
                logger.info(
                    f"[McpClientManager] Stdio client started successfully for {server_name}"
                )

                # Create client session
                async with ClientSession(read, write) as session:
                    # Cache the session
                    self._client_sessions[client_key] = session

                    try:
                        logger.info(
                            f"[McpClientManager] Session established for {server_name}"
                        )
                        yield session
                    finally:
                        # Remove from cache when done
                        if client_key in self._client_sessions:
                            del self._client_sessions[client_key]
                        logger.info(
                            f"[McpClientManager] Session closed for {server_name}"
                        )

        except FileNotFoundError as e:
            logger.error(
                f"[McpClientManager] Command not found for {server_name}: "
                f"command='{server_params.command}', args={server_params.args}"
            )
            logger.error(
                "[McpClientManager] Make sure the command is installed and available in PATH. "
                "For complex arguments (like Python scripts with -c), consider using a shell script instead."
            )
            raise ValueError(
                f"Command '{server_params.command}' not found. Make sure it's installed in the Docker container."
            ) from e

    def _build_http_client_factory(self, verify_ssl: bool):
        """Build an httpx AsyncClient factory honoring the SSL verify flag.

        The MCP SDK's ``streamablehttp_client`` accepts an ``httpx_client_factory``
        callable (headers, timeout, auth) -> httpx.AsyncClient. We provide our own
        so the user-configured ``ssl_config.verify`` flag actually controls TLS
        certificate verification for HTTP/HTTPS MCP connections.
        """
        import httpx

        def factory(
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[httpx.Timeout] = None,
            auth: Optional[httpx.Auth] = None,
        ) -> httpx.AsyncClient:
            kwargs: Dict[str, Any] = {
                "follow_redirects": True,
                "verify": verify_ssl,
            }
            kwargs["timeout"] = timeout if timeout is not None else httpx.Timeout(30.0)
            if headers is not None:
                kwargs["headers"] = headers
            if auth is not None:
                kwargs["auth"] = auth
            return httpx.AsyncClient(**kwargs)

        return factory

    @asynccontextmanager
    async def _create_http_session(
        self, http_params: Dict[str, Any], server_name: str, client_key: str
    ):
        """Create an HTTP-based MCP session."""
        from mcp.client.streamable_http import streamablehttp_client

        logger.info(
            f"[McpClientManager] Attempting to start HTTP client for {server_name}"
        )
        logger.info(f"[McpClientManager] URL: {http_params['url']}")

        # Log what we're sending to the HTTP client (with masked auth)
        masked_headers = {}
        for key, value in http_params.get("headers", {}).items():
            if key.lower() == "authorization":
                masked_headers[key] = (
                    f"Bearer ***{value[-4:] if len(value) > 4 else '***'}"
                )
            else:
                masked_headers[key] = value
        logger.info(
            f"[McpClientManager] HTTP client params: headers={masked_headers}, timeout={http_params.get('timeout', 30)}, sse_timeout={http_params.get('sse_read_timeout', 300)}"
        )

        # Determine SSL verification behavior and build a custom httpx client
        # factory so the MCP streamable HTTP transport honors it.
        ssl_config = http_params.get("ssl_config") or {}
        verify_ssl = ssl_config.get("verify", True)
        httpx_client_factory = self._build_http_client_factory(verify_ssl)

        try:
            # Create HTTP client connection - simplified to match working test script
            async with streamablehttp_client(
                http_params["url"],
                headers=http_params.get("headers", {}),
                httpx_client_factory=httpx_client_factory,
            ) as (read, write, _meta):
                logger.info(
                    f"[McpClientManager] HTTP client started successfully for {server_name}"
                )

                # Create client session
                async with ClientSession(read, write) as session:
                    # Cache the session
                    self._client_sessions[client_key] = session

                    try:
                        logger.info(
                            f"[McpClientManager] HTTP session established for {server_name}"
                        )

                        # Try to initialize the session to see if that's where the 400 happens
                        logger.info(
                            f"[McpClientManager] Attempting to initialize MCP session for {server_name}"
                        )
                        try:
                            init_result = await session.initialize()
                            logger.info(
                                f"[McpClientManager] MCP session initialized successfully for {server_name}"
                            )
                            logger.info(
                                f"[McpClientManager] Server info: {init_result}"
                            )
                        except Exception as init_e:
                            logger.error(
                                f"[McpClientManager] MCP session initialization failed for {server_name}: {init_e}"
                            )
                            raise

                        yield session
                    finally:
                        # Remove from cache when done
                        if client_key in self._client_sessions:
                            del self._client_sessions[client_key]
                        logger.info(
                            f"[McpClientManager] HTTP session closed for {server_name}"
                        )

        except Exception as e:
            # Check if this is an HTTP error with specific status code
            if hasattr(e, "__cause__") and hasattr(e.__cause__, "response"):
                response = e.__cause__.response
                logger.error(
                    f"[McpClientManager] HTTP {response.status_code} error for {server_name}"
                )
                logger.error(
                    f"[McpClientManager] Response headers: {dict(response.headers)}"
                )
                logger.error(f"[McpClientManager] Response text: {response.text}")

            logger.error(
                f"[McpClientManager] HTTP connection failed for {server_name}: {e}"
            )
            import traceback

            logger.error(f"[McpClientManager] Traceback: {traceback.format_exc()}")
            raise

    # ---- Tool definition cache helpers ----

    def _get_cached_tools(
        self, cache_key: str, server_name: str
    ) -> Optional[List[Any]]:
        """Retrieve tools from cache if a valid entry exists."""
        with self._tool_cache_lock:
            entry = self._tool_cache.get(cache_key)
            if entry is None:
                return None

            age = time.time() - entry.timestamp
            if age > self._tool_cache_ttl:
                logger.info(
                    f"[McpClientManager] Cache expired for {server_name} "
                    f"(age={age:.1f}s, ttl={self._tool_cache_ttl}s)"
                )
                del self._tool_cache[cache_key]
                return None

            entry.access_count += 1
            logger.info(
                f"[McpClientManager] Cache hit for {server_name} "
                f"({entry.tool_count} tools, age={age:.1f}s, hits={entry.access_count})"
            )
            return list(entry.tools)

    def _cache_tools(self, cache_key: str, tools: List[Any], server_name: str) -> None:
        """Store tools in cache with size management."""
        with self._tool_cache_lock:
            self._evict_expired_entries()

            if (
                len(self._tool_cache) >= self._tool_cache_max_size
                and cache_key not in self._tool_cache
            ):
                self._evict_lru_entry()

            self._tool_cache[cache_key] = _ToolCacheEntry(
                tools=list(tools),
                timestamp=time.time(),
                server_name=server_name,
                tool_count=len(tools),
            )
            logger.info(
                f"[McpClientManager] Cached {len(tools)} tools for {server_name} "
                f"(cache_size={len(self._tool_cache)})"
            )

    def _evict_expired_entries(self) -> None:
        """Remove expired entries. Caller must hold _tool_cache_lock."""
        now = time.time()
        expired_keys = [
            key
            for key, entry in self._tool_cache.items()
            if (now - entry.timestamp) > self._tool_cache_ttl
        ]
        for key in expired_keys:
            entry = self._tool_cache.pop(key)
            logger.debug(
                f"[McpClientManager] Evicted expired cache entry for {entry.server_name}"
            )

    def _evict_lru_entry(self) -> None:
        """Remove least-recently-used entry. Caller must hold _tool_cache_lock."""
        if not self._tool_cache:
            return
        lru_key = min(
            self._tool_cache.keys(),
            key=lambda k: (
                self._tool_cache[k].access_count,
                self._tool_cache[k].timestamp,
            ),
        )
        entry = self._tool_cache.pop(lru_key)
        logger.info(
            f"[McpClientManager] Evicted LRU cache entry for {entry.server_name} "
            f"(accesses={entry.access_count})"
        )

    def invalidate_tool_cache(self, server_name: Optional[str] = None) -> int:
        """Invalidate tool cache entries.

        Args:
            server_name: If provided, only invalidate entries for this server.
                         If None, invalidate all entries.

        Returns:
            Number of entries invalidated.
        """
        with self._tool_cache_lock:
            if server_name is None:
                count = len(self._tool_cache)
                self._tool_cache.clear()
                logger.info(
                    f"[McpClientManager] Invalidated all {count} tool cache entries"
                )
                return count

            keys_to_remove = [
                key
                for key, entry in self._tool_cache.items()
                if entry.server_name == server_name
            ]
            for key in keys_to_remove:
                del self._tool_cache[key]
            logger.info(
                f"[McpClientManager] Invalidated {len(keys_to_remove)} cache entries "
                f"for {server_name}"
            )
            return len(keys_to_remove)

    def get_tool_cache_stats(self) -> Dict[str, Any]:
        """Return current cache statistics for monitoring."""
        with self._tool_cache_lock:
            now = time.time()
            entries = []
            for key, entry in self._tool_cache.items():
                entries.append(
                    {
                        "server_name": entry.server_name,
                        "tool_count": entry.tool_count,
                        "age_seconds": round(now - entry.timestamp, 1),
                        "access_count": entry.access_count,
                        "expired": (now - entry.timestamp) > self._tool_cache_ttl,
                    }
                )
            return {
                "cache_size": len(self._tool_cache),
                "max_size": self._tool_cache_max_size,
                "ttl_seconds": self._tool_cache_ttl,
                "entries": entries,
            }

    # ---- Tool loading ----

    async def load_tools_from_server(self, config: Dict[str, Any]) -> List[Any]:
        """Load all tools from an MCP server, with TTL-based caching."""
        server_name = config.get("server_name", "MCP Server")

        try:
            connection_config = self._build_connection_config(config)

            # Check cache first
            cache_key = self._create_tool_cache_key(connection_config)
            cached_tools = self._get_cached_tools(cache_key, server_name)
            if cached_tools is not None:
                return cached_tools

            # Cache miss — perform full MCP handshake
            logger.info(
                f"[McpClientManager] Cache miss for {server_name}, performing MCP handshake"
            )
            tools = await load_mcp_tools(None, connection=connection_config)
            tools = [self._ensure_sync_tool(tool) for tool in tools]

            logger.info(
                f"[McpClientManager] Loaded {len(tools)} tools from {server_name}"
            )
            for tool in tools:
                tool_name = getattr(tool, "name", str(tool))
                tool_desc = getattr(tool, "description", "No description")
                logger.info(f"  - {tool_name}: {tool_desc}")

            # Store in cache
            self._cache_tools(cache_key, tools, server_name)

            return tools

        except Exception as e:
            logger.error(
                f"[McpClientManager] Failed to load tools from {server_name}: {e}"
            )
            return []

    @staticmethod
    def _extract_tool_schema(tool) -> dict:
        """Extract JSON Schema from a LangChain tool's args_schema."""
        args_schema = getattr(tool, "args_schema", None)
        if args_schema is not None:
            try:
                return args_schema.schema()
            except Exception:
                pass
        mcp_schema = getattr(tool, "_mcp_input_schema", None)
        if isinstance(mcp_schema, dict):
            return mcp_schema
        return {}

    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to an MCP server and return status."""
        server_name = config.get("server_name", "MCP Server")

        try:
            logger.info(f"[McpClientManager] Testing connection to {server_name}")

            connection_config = self._build_connection_config(config)
            tools = await load_mcp_tools(None, connection=connection_config)

            return {
                "success": True,
                "server_name": server_name,
                "tool_count": len(tools),
                "tools": [
                    {
                        "name": getattr(tool, "name", str(tool)),
                        "description": getattr(tool, "description", "No description"),
                        "input_schema": self._extract_tool_schema(tool),
                    }
                    for tool in tools
                ],
            }

        except Exception as e:
            # Extract more detailed error information
            error_msg = str(e)

            # Log the full exception for debugging
            import traceback

            full_traceback = traceback.format_exc()
            logger.error(
                f"[McpClientManager] Full exception traceback for {server_name}:\n{full_traceback}"
            )

            # STEP 1: Extract the real error from ExceptionGroups/TaskGroups
            if "TaskGroup" in error_msg or "ExceptionGroup" in error_msg:
                # Check for exceptions attribute in ExceptionGroup (Python 3.11+)
                if hasattr(e, "exceptions"):
                    for sub_exc in e.exceptions:
                        logger.error(
                            f"[McpClientManager] Sub-exception type: {type(sub_exc).__name__}, message: {sub_exc}"
                        )
                        # Walk the exception chain to find HTTP errors or other meaningful errors
                        cause = sub_exc
                        while cause:
                            # Check for HTTP response errors
                            if hasattr(cause, "response"):
                                response = cause.response
                                # httpx Response objects use status_code and reason_phrase
                                status_code = getattr(
                                    response, "status_code", "Unknown"
                                )
                                reason = getattr(
                                    response,
                                    "reason_phrase",
                                    getattr(response, "reason", "Error"),
                                )
                                error_msg = f"HTTP {status_code}: {reason}"
                                logger.error(
                                    f"[McpClientManager] HTTP error details for {server_name}: Status={status_code}"
                                )
                                break

                            # Check for connection errors
                            if isinstance(cause, (ConnectionError, OSError)):
                                error_msg = f"Connection error: {str(cause)}"
                                logger.error(
                                    f"[McpClientManager] Connection error: {cause}"
                                )
                                break

                            # Use the innermost exception message if it's more specific
                            cause_str = str(cause)
                            if (
                                cause_str
                                and cause_str != error_msg
                                and "TaskGroup" not in cause_str
                            ):
                                error_msg = cause_str

                            # Try both __cause__ and __context__
                            if hasattr(cause, "__cause__") and cause.__cause__:
                                cause = cause.__cause__
                            elif hasattr(cause, "__context__") and cause.__context__:
                                cause = cause.__context__
                            else:
                                break

                        if error_msg != str(e) and "Connection closed" not in error_msg:
                            break

            # STEP 2: Apply helpful error messages based on the extracted error
            # Now that we have the real error message, provide context-specific guidance
            if "not found in PATH" in error_msg:
                # Command not installed - the validation error message is already clear
                pass
            elif (
                "Connection closed" in error_msg
                and config.get("connection_type") == "stdio"
            ):
                # Generic "Connection closed" usually means subprocess failed
                # Provide helpful context
                command = config.get("command", "")
                args = config.get("args", [])

                # Build helpful hints
                hints = []
                hints.append(
                    "The command process exited unexpectedly before establishing connection."
                )
                hints.append("\nCommon causes:")
                hints.append("• Invalid command arguments or syntax")
                hints.append(
                    "• Missing dependencies or packages required by the server"
                )
                hints.append("• Command not installed or not in PATH")
                hints.append("• Incorrect file paths or working directory")
                hints.append("• Permission issues")

                # Check for specific issues
                if args:
                    # Check for quoted arguments that shouldn't be quoted
                    if any(arg.startswith('"') or arg.startswith("'") for arg in args):
                        hints.append(
                            "\n⚠️  Detected quoted arguments - remove quotes from individual arguments"
                        )

                # Add command details
                hints.append("\nCommand executed:")
                hints.append(
                    f"  {command} {' '.join(str(arg) for arg in args) if args else '(no arguments)'}"
                )

                hints.append(
                    "\nTip: Check the backend logs for detailed error output from the command."
                )

                error_msg = "\n".join(hints)

            logger.error(
                f"[McpClientManager] Connection test failed for {server_name}: {error_msg}"
            )
            return {"success": False, "server_name": server_name, "error": error_msg}

    async def cleanup_all_sessions(self):
        """Clean up all active sessions and cached tools."""
        logger.info("[McpClientManager] Cleaning up all sessions and cached tools")

        session_count = len(self._client_sessions)
        self._client_sessions.clear()

        cache_count = self.invalidate_tool_cache()

        logger.info(
            f"[McpClientManager] Cleaned up {session_count} sessions "
            f"and {cache_count} cached tool entries"
        )


# Global instance for use throughout the application
mcp_client_manager = McpClientManager()
