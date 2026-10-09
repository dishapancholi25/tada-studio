"""User settings API endpoints.

This module provides REST API endpoints for managing user-specific
external service configurations like Tavily API keys.

Endpoints:
    GET /api/user/settings/external-services: List all external services
    GET /api/user/settings/external-services/{service_name}: Get service info
    PUT /api/user/settings/external-services/{service_name}: Save service config
    DELETE /api/user/settings/external-services/{service_name}: Delete service config
    GET /api/user/settings/external-services/{service_name}/for-node: Get config for node creation

Example:
    >>> from backend.api.user_settings import router
    >>> app.include_router(router)
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_

from backend.api.auth.dependencies import (
    get_current_user,
    require_active_user,
    require_feature_access,
)
from backend.models.auth.user_external_service import UserExternalService
from backend.encryption_utils import decrypt_credential
from backend.services.auth.user_external_service import UserExternalServiceService
from backend.services.configuration.credential_resolution_service import (
    CredentialResolutionService,
)
from backend.services.database import get_db

from .constants import (
    ALLOWED_SERVICE_NAMES,
    build_mcp_service_name,
    extract_mcp_server_name,
    is_mcp_server,
    validate_mcp_server_name,
)
from .csrf import verify_csrf_token
from .mcp_integration_handlers import (
    handle_delete_integration,
    handle_get_integration,
    handle_get_integration_for_workflow,
    handle_list_integrations,
    handle_save_integration,
    handle_toggle_integration,
)
from .models import (
    CloneMcpServerRequest,
    CloneMcpServerResponse,
    DeleteExternalServiceResponse,
    DeleteMcpIntegrationResponse,
    DeleteMcpServerResponse,
    ExportMcpServersRequest,
    ExportMcpServersResponse,
    ExternalServiceInfo,
    GetExternalServiceForNodeResponse,
    GetMcpIntegrationResponse,
    GetMcpServersForAgentResponse,
    ImportMcpServersRequest,
    ImportMcpServersResponse,
    ListExternalServicesResponse,
    ListMcpIntegrationsResponse,
    ListMcpServersResponse,
    ListPublicMcpServersResponse,
    McpIntegrationForWorkflowResponse,
    McpServerConfigRequest,
    McpServerForAgentConfig,
    McpServerInfo,
    McpServerVisibility,
    McpToolInfo,
    SaveExternalServiceRequest,
    SaveExternalServiceResponse,
    SaveMcpIntegrationRequest,
    SaveMcpIntegrationResponse,
    SaveMcpServerResponse,
    StandardMcpServerConfig,
    TestMcpConnectionResponse,
)


logger = logging.getLogger(__name__)
LOG_PREFIX = "[USER-SETTINGS]"

# Create router
router = APIRouter(
    prefix="/api/user/settings",
    tags=["user-settings"],
    dependencies=[Depends(require_active_user)],
)


def get_user_identifier(current_user: Dict[str, Any]) -> str:
    """Extract user identifier from JWT claims.

    Args:
        current_user: User claims from get_current_user dependency

    Returns:
        User identifier (sub claim)

    Raises:
        HTTPException: 401 if user identifier not in claims
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier


@router.get("/external-services", response_model=ListExternalServicesResponse)
async def list_external_services(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ListExternalServicesResponse:
    """List all external services configured for the current user.

    Args:
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        ListExternalServicesResponse: List of configured services

    Example:
        ```bash
        curl "http://localhost:8000/api/user/settings/external-services" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        services = UserExternalServiceService.list_user_services(user_id)

        service_infos = []
        for service in services:
            # Decrypt API key directly from the service object to avoid redundant queries
            api_key_masked = None
            if service.encrypted_api_key:
                try:
                    from backend.encryption_utils import decrypt_credential

                    decrypted_key = decrypt_credential(service.encrypted_api_key)
                    api_key_masked = UserExternalServiceService.mask_api_key(
                        decrypted_key
                    )
                except Exception as e:
                    logger.error(
                        f"{LOG_PREFIX} Failed to decrypt API key for service "
                        f"'{service.service_name}': {e}"
                    )
                    api_key_masked = None

            service_infos.append(
                ExternalServiceInfo(
                    service_name=service.service_name,
                    is_active=service.is_active,
                    api_key_configured=bool(service.encrypted_api_key),
                    api_key_masked=api_key_masked,
                    settings=service.settings or {},
                    created_at=service.created_at,
                    updated_at=service.updated_at,
                    display_name=service.display_name,
                    service_url=service.service_url,
                    auth_type=service.auth_type.value if service.auth_type else None,
                    system_default_configured=CredentialResolutionService.system_default_configured(
                        service.service_name
                    ),
                )
            )

        logger.debug(
            f"{LOG_PREFIX} Listed {len(service_infos)} external services "
            f"for user '{user_id}'"
        )

        return ListExternalServicesResponse(success=True, services=service_infos)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error listing external services: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list external services: {str(e)}"
        )


@router.get("/external-services/{service_name}", response_model=ExternalServiceInfo)
async def get_external_service(
    service_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ExternalServiceInfo:
    """Get information about a specific external service.

    Args:
        service_name: Name of the external service (e.g., 'tavily')
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        ExternalServiceInfo: Service configuration (API key masked)

    Raises:
        HTTPException: 404 if service not configured

    Example:
        ```bash
        curl "http://localhost:8000/api/user/settings/external-services/tavily" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        service = UserExternalServiceService.get_service(user_id, service_name)

        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"External service '{service_name}' not configured",
            )

        api_key = UserExternalServiceService.get_decrypted_api_key(
            user_id, service_name
        )

        return ExternalServiceInfo(
            service_name=service.service_name,
            is_active=service.is_active,
            api_key_configured=bool(service.encrypted_api_key),
            api_key_masked=UserExternalServiceService.mask_api_key(api_key)
            if api_key
            else None,
            settings=service.settings or {},
            created_at=service.created_at,
            updated_at=service.updated_at,
            display_name=service.display_name,
            service_url=service.service_url,
            auth_type=service.auth_type.value if service.auth_type else None,
            system_default_configured=CredentialResolutionService.system_default_configured(
                service_name
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error getting external service: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get external service: {str(e)}"
        )


@router.put(
    "/external-services/{service_name}", response_model=SaveExternalServiceResponse
)
async def save_external_service(
    service_name: str,
    request: SaveExternalServiceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
) -> SaveExternalServiceResponse:
    """Save or update external service configuration.

    Args:
        service_name: Name of the external service (e.g., 'tavily')
        request: Service configuration with API key
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        SaveExternalServiceResponse: Confirmation with updated service info

    Example:
        ```bash
        curl -X PUT "http://localhost:8000/api/user/settings/external-services/tavily" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "Content-Type: application/json" \\
          -d '{"api_key": "tvly-xxxxxxxx"}'
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate service name
        if service_name not in ALLOWED_SERVICE_NAMES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid service name. Allowed services: {', '.join(ALLOWED_SERVICE_NAMES)}",
            )

        # Save the service configuration
        service = UserExternalServiceService.save_service(
            user_id=user_id,
            service_name=service_name,
            api_key=request.api_key or "",
            settings=request.settings,
            display_name=request.display_name,
            service_url=request.service_url,
            auth_type=request.auth_type,
            credentials=request.credentials,
        )

        logger.info(
            f"{LOG_PREFIX} Saved {service_name} configuration for user '{user_id}'"
        )

        # Determine masked key for response
        masked_key = None
        if request.api_key:
            masked_key = UserExternalServiceService.mask_api_key(request.api_key)
        elif request.credentials and request.credentials.get("api_key"):
            masked_key = UserExternalServiceService.mask_api_key(
                request.credentials["api_key"]
            )

        return SaveExternalServiceResponse(
            success=True,
            message=f"External service '{service_name}' configured successfully",
            service=ExternalServiceInfo(
                service_name=service.service_name,
                is_active=service.is_active,
                api_key_configured=bool(request.api_key or request.credentials),
                api_key_masked=masked_key,
                settings=service.settings or {},
                created_at=service.created_at,
                updated_at=service.updated_at,
                display_name=request.display_name,
                service_url=request.service_url,
                auth_type=request.auth_type,
                system_default_configured=CredentialResolutionService.system_default_configured(
                    service_name
                ),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error saving external service: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save external service: {str(e)}"
        )


@router.delete(
    "/external-services/{service_name}", response_model=DeleteExternalServiceResponse
)
async def delete_external_service(
    service_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
) -> DeleteExternalServiceResponse:
    """Delete external service configuration.

    Args:
        service_name: Name of the external service (e.g., 'tavily')
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        DeleteExternalServiceResponse: Confirmation of deletion

    Raises:
        HTTPException: 404 if service not configured

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/user/settings/external-services/tavily" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        success = UserExternalServiceService.delete_service(user_id, service_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"External service '{service_name}' not configured",
            )

        logger.info(
            f"{LOG_PREFIX} Deleted {service_name} configuration for user '{user_id}'"
        )

        return DeleteExternalServiceResponse(
            success=True,
            message=f"External service '{service_name}' deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error deleting external service: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete external service: {str(e)}"
        )


@router.get(
    "/external-services/{service_name}/for-node",
    response_model=GetExternalServiceForNodeResponse,
)
async def get_external_service_for_node(
    service_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> GetExternalServiceForNodeResponse:
    """Get external service configuration for node creation.

    This endpoint returns the decrypted API key for use when creating
    new nodes that need the service configuration. This is used internally
    when creating web search nodes to auto-populate the Tavily API key.

    Args:
        service_name: Name of the external service (e.g., 'tavily')
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        GetExternalServiceForNodeResponse: Service config with decrypted key

    Example:
        ```bash
        curl "http://localhost:8000/api/user/settings/external-services/tavily/for-node" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Use dual-tier resolution: user credentials first, then system defaults
        api_key = CredentialResolutionService.resolve_api_key(service_name, user_id)

        if not api_key:
            return GetExternalServiceForNodeResponse(
                configured=False,
                api_key=None,
                settings={},
            )

        # Retrieve settings from user record if it exists
        settings: dict = {}
        user_service = UserExternalServiceService.get_service(user_id, service_name)
        if user_service and user_service.settings:
            settings = user_service.settings

        return GetExternalServiceForNodeResponse(
            configured=True,
            api_key=api_key,
            settings=settings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error getting external service for node: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get external service for node: {str(e)}",
        )


# MCP Server Helper Functions


def _serialize_mcp_config_to_settings(
    request: McpServerConfigRequest,
) -> Dict[str, Any]:
    """Extract non-sensitive configuration fields from request.

    Args:
        request: MCP server configuration request

    Returns:
        Dictionary to be stored in settings JSON field
    """
    settings = {
        "server_name": request.server_name,
        "connection_type": request.connection_type,
        "auth_type": request.auth_type,
        "timeout_seconds": request.timeout_seconds,
        "max_retries": request.max_retries,
        "retry_delay": request.retry_delay,
    }

    # Add optional fields if provided
    if request.server_url:
        settings["server_url"] = request.server_url
    if request.command:
        settings["command"] = request.command
    if request.args:
        settings["args"] = request.args
    if request.working_directory:
        settings["working_directory"] = request.working_directory
    if request.environment_variables:
        settings["environment_variables"] = request.environment_variables
    if request.description:
        settings["description"] = request.description
    if request.ssl_config:
        settings["ssl_config"] = request.ssl_config

    return settings


def _transform_mcp_request_to_config(request: McpServerConfigRequest) -> Dict[str, Any]:
    """Transform MCP server config request to format expected by mcp_client_manager.

    Args:
        request: MCP server configuration request

    Returns:
        Dictionary config for mcp_client_manager.test_connection()
    """
    config = {
        "server_name": request.server_name,
        "connection_type": request.connection_type,
        "auth_type": request.auth_type,
        "timeout_seconds": request.timeout_seconds,
        "max_retries": request.max_retries,
        "retry_delay": request.retry_delay,
    }

    # Add optional connection fields
    if request.server_url:
        config["server_url"] = request.server_url
    if request.command:
        config["command"] = request.command
    if request.args:
        config["args"] = request.args
    if request.working_directory:
        config["working_directory"] = request.working_directory
    if request.environment_variables:
        config["environment_variables"] = request.environment_variables
    if request.ssl_config:
        config["ssl_config"] = request.ssl_config

    # Transform auth_credentials to auth_config
    # Auth type conventions:
    # - "bearer": Static bearer token (uses "token" or "bearer_token" field)
    # - "oauth2": Static OAuth2 access token (uses "access_token" or "token" field)
    # - "oauth": Dynamic OAuth flow requiring provider and user_id (no direct token mapping)
    # - "oauth_host_identity": Cloud provider managed identity (AWS/Azure)
    # - "api_key": API key authentication (uses "api_key" or "key" field)
    # - "custom": Custom authentication (pass through as-is)
    auth_config = {}
    if request.auth_credentials:
        if request.auth_type == "bearer":
            # Map bearer_token or token to token for bearer authentication
            if "bearer_token" in request.auth_credentials:
                auth_config["token"] = request.auth_credentials["bearer_token"]
            elif "token" in request.auth_credentials:
                auth_config["token"] = request.auth_credentials["token"]
            else:
                # Fallback to passing through as-is
                auth_config = request.auth_credentials
        elif request.auth_type == "oauth2":
            # Map access_token or token to access_token for static OAuth2 tokens
            if "access_token" in request.auth_credentials:
                auth_config["access_token"] = request.auth_credentials["access_token"]
            elif "token" in request.auth_credentials:
                auth_config["access_token"] = request.auth_credentials["token"]
            else:
                # Fallback to passing through as-is
                auth_config = request.auth_credentials
        elif request.auth_type == "oauth":
            # Dynamic OAuth flow - expects provider and user_id, no direct token mapping
            # Pass through as-is (should contain provider and user_id fields)
            auth_config = request.auth_credentials
        elif request.auth_type == "mcp_oauth":
            # MCP server OAuth flow - pass through server_name, user_id, server_url
            auth_config = request.auth_credentials or {}
        elif request.auth_type == "oauth_host_identity":
            # Managed identity - pass through configuration (resource, client_id, role_arn)
            # Token generation happens at runtime in mcp_client_manager
            auth_config = request.auth_credentials
        elif request.auth_type == "api_key":
            # Map api_key or key to api_key
            if "api_key" in request.auth_credentials:
                auth_config["api_key"] = request.auth_credentials["api_key"]
            elif "key" in request.auth_credentials:
                auth_config["api_key"] = request.auth_credentials["key"]
            else:
                # Fallback to passing through as-is
                auth_config = request.auth_credentials
        elif request.auth_type == "custom":
            # Pass through custom credentials as-is
            auth_config = request.auth_credentials
        else:
            # For any other type, pass through as-is
            auth_config = request.auth_credentials

    config["auth_config"] = auth_config

    return config


def _extract_credentials_from_request(
    request: McpServerConfigRequest,
) -> Optional[str]:
    """Extract and serialize credentials from request.

    Args:
        request: MCP server configuration request

    Returns:
        JSON string of credentials, or None if no credentials
    """
    if not request.auth_credentials:
        return None

    return json.dumps(request.auth_credentials)


def _get_user_display_name(user) -> Optional[str]:
    """Get a display name from a User object, trying name, given+family, then email."""
    if not user:
        return None
    name = getattr(user, "name", None)
    if name:
        return name
    given = getattr(user, "given_name", None)
    family = getattr(user, "family_name", None)
    if given and family:
        return f"{given} {family}"
    if given:
        return given
    if family:
        return family
    email = getattr(user, "email", None)
    if email:
        return email
    return None


def _build_mcp_server_info(
    service: UserExternalService, mask_credentials: bool = False
) -> McpServerInfo:
    """Build MCP server info response from service record.

    Args:
        service: User external service database record
        mask_credentials: If True, mask sensitive credential information (for non-owners)

    Returns:
        McpServerInfo response model

    Raises:
        ValueError: If service settings are invalid
    """
    settings = service.settings or {}

    # Extract server name from service name
    try:
        server_name = extract_mcp_server_name(service.service_name)
    except ValueError:
        # Fallback to service_name if extraction fails
        server_name = service.service_name

    # Check if credentials are configured
    credentials_configured = False
    if not mask_credentials and service.encrypted_api_key:
        try:
            decrypted = decrypt_credential(service.encrypted_api_key)
            credentials_configured = bool(decrypted)
        except Exception as e:
            logger.warning(
                f"{LOG_PREFIX} Failed to decrypt credentials for "
                f"'{service.service_name}': {e}"
            )

    # Build config summary with non-sensitive fields
    config_summary = {
        "timeout_seconds": settings.get("timeout_seconds", 30),
        "max_retries": settings.get("max_retries", 3),
        "retry_delay": settings.get("retry_delay", 1.0),
    }

    if "args" in settings:
        config_summary["args"] = settings["args"]
    if "working_directory" in settings:
        config_summary["working_directory"] = settings["working_directory"]
    # Only include environment variables if not masking credentials
    if "environment_variables" in settings and not mask_credentials:
        config_summary["environment_variables"] = settings["environment_variables"]
    if "ssl_config" in settings:
        config_summary["ssl_config"] = settings["ssl_config"]

    # Convert database visibility enum (PRIVATE/PUBLIC) to API enum (private/shared)
    # DB PUBLIC maps to API "shared"; DB PRIVATE maps to API "private"
    shared_group_ids = getattr(service, "shared_with_group_ids", None) or []
    if service.visibility and service.visibility.value == "PUBLIC":
        api_visibility = McpServerVisibility.SHARED
    else:
        api_visibility = McpServerVisibility.PRIVATE
        shared_group_ids = []

    # Resolve group IDs to names for display
    shared_group_names: list[str] = []
    display_group_ids = [gid for gid in shared_group_ids if gid != "__all__"]
    if display_group_ids:
        try:
            from backend.models.auth.group import Group
            from backend.services.database import get_db

            with get_db() as db:
                groups = db.query(Group).filter(Group.id.in_(display_group_ids)).all()
                shared_group_names = [g.name for g in groups]
        except Exception:
            logger.warning(
                f"{LOG_PREFIX} Failed to resolve group names for MCP server sharing"
            )

    return McpServerInfo(
        id=service.id,
        service_name=service.service_name,
        server_name=settings.get("server_name", server_name),
        connection_type=settings.get("connection_type", "http"),
        server_url=settings.get("server_url"),
        command=settings.get("command"),
        auth_type=settings.get("auth_type", "none"),
        credentials_configured=credentials_configured,
        description=settings.get("description"),
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at,
        config_summary=config_summary,
        visibility=api_visibility,
        shared_with_group_ids=shared_group_ids,
        shared_with_group_names=shared_group_names,
        is_template=service.is_template,
        original_server_id=service.original_server_id,
        clone_count=service.clone_count,
        creator_id=service.user_id,
        creator_name=None,  # Can be populated by caller if needed
        is_owned_by_current_user=True,  # Default, can be overridden by caller
    )


def _build_mcp_server_for_agent(
    service: UserExternalService,
) -> McpServerForAgentConfig:
    """Build MCP server config for agent tool creation with decrypted credentials.

    Args:
        service: User external service database record

    Returns:
        McpServerForAgentConfig with decrypted credentials.
        If credential decryption fails, returns config with empty auth_config
        and has_credential_error=True to indicate the server cannot be used
        until credentials are fixed.
    """
    settings = service.settings or {}

    # Extract server name
    try:
        server_name = extract_mcp_server_name(service.service_name)
    except ValueError:
        server_name = service.service_name

    # Decrypt credentials
    auth_config = {}
    has_credential_error = False

    if service.encrypted_api_key:
        try:
            decrypted = decrypt_credential(service.encrypted_api_key)
            if decrypted:
                # Parse JSON credentials
                credentials = json.loads(decrypted)

                # Map credentials to auth_config based on auth_type with defensive fallbacks
                # Auth type conventions (matching _transform_mcp_request_to_config):
                # - "bearer": Static bearer token (uses "token" or "bearer_token" field)
                # - "oauth2": Static OAuth2 access token (uses "access_token" or "token" field)
                # - "oauth": Dynamic OAuth flow requiring provider and user_id (no direct token mapping)
                # - "oauth_host_identity": Cloud provider managed identity (AWS/Azure)
                # - "api_key": API key authentication (uses "api_key" or "key" field)
                # - "custom": Custom authentication (pass through as-is)
                auth_type = settings.get("auth_type", "none")
                if auth_type == "bearer":
                    # Check both preferred new key and common legacy/equivalent keys
                    token = credentials.get("bearer_token") or credentials.get("token")
                    if token:
                        auth_config["token"] = token
                    else:
                        # If neither key is present, use the full credentials dict as-is
                        auth_config = credentials
                elif auth_type == "oauth2":
                    # Check both access_token and any legacy token field
                    access_token = credentials.get("access_token") or credentials.get(
                        "token"
                    )
                    if access_token:
                        auth_config["access_token"] = access_token
                    else:
                        # If neither key is present, use the full credentials dict as-is
                        auth_config = credentials
                elif auth_type == "oauth":
                    # Dynamic OAuth flow - expects provider and user_id, no direct token mapping
                    # Pass through as-is (should contain provider and user_id fields)
                    auth_config = credentials
                elif auth_type == "mcp_oauth":
                    # MCP server OAuth flow - pass through server_name, user_id, server_url
                    auth_config = credentials
                elif auth_type == "oauth_host_identity":
                    # Managed identity - pass through configuration (resource, client_id, role_arn)
                    # Token generation happens at runtime in mcp_client_manager
                    auth_config = credentials
                elif auth_type == "api_key":
                    # Check api_key, then key, then pass through
                    api_key = credentials.get("api_key") or credentials.get("key")
                    if api_key:
                        auth_config["api_key"] = api_key
                    else:
                        # If neither key is present, use the full credentials dict as-is
                        auth_config = credentials
                elif auth_type == "custom":
                    auth_config = credentials
                else:
                    auth_config = credentials
        except Exception as e:
            logger.error(
                f"{LOG_PREFIX} Failed to decrypt credentials for '{service.service_name}': {e}. "
                "Server will be returned with has_credential_error=True."
            )
            # Set error flag instead of returning None
            has_credential_error = True

    return McpServerForAgentConfig(
        service_name=service.service_name,
        server_name=settings.get("server_name", server_name),
        connection_type=settings.get("connection_type", "http"),
        server_url=settings.get("server_url"),
        command=settings.get("command"),
        args=settings.get("args"),
        working_directory=settings.get("working_directory"),
        environment_variables=settings.get("environment_variables"),
        auth_type=settings.get("auth_type", "none"),
        auth_config=auth_config,
        timeout_seconds=settings.get("timeout_seconds", 30),
        max_retries=settings.get("max_retries", 3),
        retry_delay=settings.get("retry_delay", 1.0),
        description=settings.get("description"),
        has_credential_error=has_credential_error,
    )


def _build_mcp_server_for_agent_shared(
    service: UserExternalService,
) -> McpServerForAgentConfig:
    """Build MCP server config for a shared server (owned by another user).

    Uses the connection details from the shared server's settings.
    For auth types that don't require static credentials (none, oauth2,
    oauth_host_identity, mcp_oauth), the server works directly.
    For credential-based auth types, has_credential_error is set since
    the consuming user doesn't have access to the owner's credentials.
    """
    settings = service.settings or {}

    try:
        server_name = extract_mcp_server_name(service.service_name)
    except ValueError:
        server_name = service.service_name

    auth_type = settings.get("auth_type", "none")

    # Auth types that work without the owner's stored credentials
    runtime_auth_types = {"none", "oauth2", "oauth_host_identity", "mcp_oauth"}
    needs_credentials = auth_type not in runtime_auth_types
    has_credential_error = needs_credentials  # Can't decrypt another user's creds

    return McpServerForAgentConfig(
        service_name=service.service_name,
        server_name=settings.get("server_name", server_name),
        connection_type=settings.get("connection_type", "http"),
        server_url=settings.get("server_url"),
        command=settings.get("command"),
        args=settings.get("args"),
        working_directory=settings.get("working_directory"),
        environment_variables=settings.get("environment_variables"),
        auth_type=auth_type,
        auth_config={},
        timeout_seconds=settings.get("timeout_seconds", 30),
        max_retries=settings.get("max_retries", 3),
        retry_delay=settings.get("retry_delay", 1.0),
        description=settings.get("description"),
        has_credential_error=has_credential_error,
    )


# MCP Server Export/Import Helper Functions


def _transform_internal_to_standard(
    service: UserExternalService,
) -> tuple[str, StandardMcpServerConfig]:
    """Transform internal MCP server config to standard .mcp.json format.

    Args:
        service: UserExternalService database record

    Returns:
        Tuple of (server_key, StandardMcpServerConfig)

    Raises:
        ValueError: If service settings are invalid or missing required fields
    """
    from .models import McpAdvancedSettings, McpAuthenticationSettings

    settings = service.settings or {}

    # Extract server name for the key
    try:
        server_key = extract_mcp_server_name(service.service_name)
    except ValueError:
        server_key = service.service_name

    # Get connection type (required)
    connection_type = settings.get("connection_type", "http")

    # Map connection_type to standard type field
    # Internal: "stdio", "http", "sse" → Standard: same
    standard_type = connection_type

    # Build standard config based on type
    config_dict = {"type": standard_type}

    if standard_type == "stdio":
        # Stdio servers require command
        command = settings.get("command")
        if command:
            config_dict["command"] = command

        # Optional stdio fields
        if "args" in settings and settings["args"]:
            config_dict["args"] = settings["args"]

        if "environment_variables" in settings and settings["environment_variables"]:
            config_dict["env"] = settings["environment_variables"]

        if "working_directory" in settings and settings["working_directory"]:
            config_dict["cwd"] = settings["working_directory"]

    elif standard_type in ("http", "sse"):
        # HTTP/SSE servers require URL
        server_url = settings.get("server_url")
        if server_url:
            config_dict["url"] = server_url

    # Add description if present
    if "description" in settings and settings["description"]:
        config_dict["description"] = settings["description"]

    # Build advanced settings node (only include non-default values)
    # Defaults: timeout=30, retries=3, retryDelay=1.0
    advanced_dict = {}
    if (
        "timeout_seconds" in settings
        and settings["timeout_seconds"] is not None
        and settings["timeout_seconds"] != 30
    ):
        advanced_dict["timeout"] = settings["timeout_seconds"]

    if (
        "max_retries" in settings
        and settings["max_retries"] is not None
        and settings["max_retries"] != 3
    ):
        advanced_dict["retries"] = settings["max_retries"]

    if (
        "retry_delay" in settings
        and settings["retry_delay"] is not None
        and settings["retry_delay"] != 1.0
    ):
        advanced_dict["retryDelay"] = settings["retry_delay"]

    if advanced_dict:
        config_dict["advanced"] = McpAdvancedSettings(**advanced_dict)

    # Build authentication node
    auth_type = settings.get("auth_type", "none")
    auth_dict = {}

    if auth_type != "none":
        auth_dict["type"] = auth_type

        if auth_type == "bearer" and service.encrypted_api_key:
            # Decrypt and add bearer token
            try:
                decrypted = decrypt_credential(service.encrypted_api_key)
                if decrypted:
                    credentials = json.loads(decrypted)
                    token = credentials.get("bearer_token") or credentials.get("token")
                    if token:
                        auth_dict["token"] = token
            except Exception as e:
                logger.warning(
                    f"{LOG_PREFIX} Failed to decrypt bearer token for export: {e}"
                )

        elif auth_type == "api_key" and service.encrypted_api_key:
            # Decrypt and add API key
            try:
                decrypted = decrypt_credential(service.encrypted_api_key)
                if decrypted:
                    credentials = json.loads(decrypted)
                    api_key = credentials.get("api_key") or credentials.get("key")
                    header_name = credentials.get("header_name", "X-API-Key")
                    if api_key:
                        auth_dict["apiKey"] = api_key
                        if header_name != "X-API-Key":
                            auth_dict["headerName"] = header_name
            except Exception as e:
                logger.warning(
                    f"{LOG_PREFIX} Failed to decrypt API key for export: {e}"
                )

        if auth_dict:
            config_dict["authentication"] = McpAuthenticationSettings(**auth_dict)

    return server_key, StandardMcpServerConfig(**config_dict)


def _transform_standard_to_internal(
    server_key: str, config: StandardMcpServerConfig
) -> tuple[McpServerConfigRequest, str]:
    """Transform standard .mcp.json config to internal format.

    Args:
        server_key: Server name key from mcpServers object
        config: Standard MCP server configuration

    Returns:
        Tuple of (McpServerConfigRequest, extracted_server_name)
        where extracted_server_name is the server_key to use

    Raises:
        ValueError: If config is invalid or missing required fields
    """
    # Build internal config request
    server_name = server_key  # Use the key as display name

    # Map standard type to internal connection_type
    connection_type = config.type

    # Validate type
    if connection_type not in ("stdio", "http", "sse"):
        raise ValueError(
            f"Invalid server type '{connection_type}'. Must be stdio, http, or sse"
        )

    # Extract advanced settings (with defaults)
    timeout_seconds = 30
    max_retries = 3
    retry_delay = 1.0

    if config.advanced:
        if config.advanced.timeout is not None:
            timeout_seconds = config.advanced.timeout
        if config.advanced.retries is not None:
            max_retries = config.advanced.retries
        if config.advanced.retryDelay is not None:
            retry_delay = config.advanced.retryDelay

    # Build request based on type
    request_dict = {
        "server_name": server_name,
        "connection_type": connection_type,
        "auth_type": "none",  # Default, will be updated based on authentication
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
    }

    # Add optional description
    if config.description:
        request_dict["description"] = config.description

    auth_credentials = {}

    if connection_type == "stdio":
        # Stdio servers
        if not config.command:
            raise ValueError(
                f"stdio server '{server_key}' missing required 'command' field"
            )

        request_dict["command"] = config.command

        if config.args:
            request_dict["args"] = config.args

        if config.env:
            request_dict["environment_variables"] = config.env

        if config.cwd:
            request_dict["working_directory"] = config.cwd

    elif connection_type in ("http", "sse"):
        # HTTP/SSE servers
        if not config.url:
            raise ValueError(
                f"{connection_type} server '{server_key}' missing required 'url' field"
            )

        request_dict["server_url"] = config.url

    # Extract authentication settings
    if config.authentication:
        auth_type = config.authentication.type or "none"
        request_dict["auth_type"] = auth_type

        if auth_type == "bearer" and config.authentication.token:
            auth_credentials = {"bearer_token": config.authentication.token}

        elif auth_type == "api_key" and config.authentication.apiKey:
            auth_credentials = {"api_key": config.authentication.apiKey}
            if config.authentication.headerName:
                auth_credentials["header_name"] = config.authentication.headerName

        elif config.authentication.headers:
            # Custom headers-based authentication
            # Try to detect auth type from headers
            if "Authorization" in config.authentication.headers:
                auth_header = config.authentication.headers["Authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    request_dict["auth_type"] = "bearer"
                    auth_credentials = {"bearer_token": token}
            else:
                # Check for API key headers
                api_key_headers = [
                    k
                    for k in config.authentication.headers.keys()
                    if "api" in k.lower() and "key" in k.lower()
                ]
                if api_key_headers:
                    header_name = api_key_headers[0]
                    api_key = config.authentication.headers[header_name]
                    request_dict["auth_type"] = "api_key"
                    auth_credentials = {"api_key": api_key, "header_name": header_name}

    if auth_credentials:
        request_dict["auth_credentials"] = auth_credentials

    return McpServerConfigRequest(**request_dict), server_key


# MCP Server API Endpoints


@router.get("/mcp-servers", response_model=ListMcpServersResponse)
async def list_mcp_servers(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ListMcpServersResponse:
    """List all MCP servers configured for the current user.

    Args:
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        ListMcpServersResponse: List of configured MCP servers

    Example:
        ```bash
        curl "http://localhost:8000/api/user/settings/mcp-servers" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Get user's own MCP servers
        all_services = UserExternalServiceService.list_user_services(user_id)
        mcp_services = [s for s in all_services if is_mcp_server(s.service_name)]

        # Build server info for each of the user's own MCP servers
        servers = []
        for service in mcp_services:
            try:
                server_info = _build_mcp_server_info(service)
                servers.append(server_info)
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to build info for MCP server "
                    f"'{service.service_name}': {e}"
                )

        # Collect IDs of servers the user has cloned (original_server_id)
        cloned_source_ids = {
            s.original_server_id
            for s in mcp_services
            if s.is_template and s.original_server_id
        }

        # Also include MCP servers shared with this user (via groups or everyone)
        try:
            shared_services = (
                UserExternalServiceService.list_shared_mcp_servers_for_user(user_id)
            )
            for service in shared_services:
                # Skip shared servers the user has already cloned
                if str(service.id) in cloned_source_ids:
                    continue
                try:
                    server_info = _build_mcp_server_info(
                        service, mask_credentials=True
                    )
                    server_info.is_owned_by_current_user = False
                    server_info.creator_name = _get_user_display_name(service.user)
                    servers.append(server_info)
                except Exception as e:
                    logger.error(
                        f"{LOG_PREFIX} Failed to build info for shared MCP server "
                        f"'{service.service_name}': {e}"
                    )
        except Exception as e:
            logger.warning(
                f"{LOG_PREFIX} Failed to load shared MCP servers for user '{user_id}': {e}"
            )

        logger.debug(
            f"{LOG_PREFIX} Listed {len(servers)} MCP servers for user '{user_id}'"
        )

        return ListMcpServersResponse(success=True, servers=servers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error listing MCP servers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list MCP servers: {str(e)}"
        )


@router.get("/mcp-servers/for-agent", response_model=GetMcpServersForAgentResponse)
async def get_mcp_servers_for_agent(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> GetMcpServersForAgentResponse:
    """Get all MCP servers configured for the current user with decrypted credentials.

    This endpoint returns full MCP server configurations including decrypted
    credentials for use when creating agent tool nodes. Only active servers
    are returned.

    Args:
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        GetMcpServersForAgentResponse: List of MCP servers with full configs

    Example:
        ```bash
        curl "http://localhost:8000/api/user/settings/mcp-servers/for-agent" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Get user's own active MCP servers
        all_services = UserExternalServiceService.list_user_services(user_id)
        mcp_services = [
            s for s in all_services if is_mcp_server(s.service_name) and s.is_active
        ]

        # Build full configs with decrypted credentials
        servers = []
        failed_count = 0
        seen_service_names = set()
        for service in mcp_services:
            try:
                server_config = _build_mcp_server_for_agent(service)
                servers.append(server_config)
                seen_service_names.add(service.service_name)
                if server_config.has_credential_error:
                    failed_count += 1
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to build config for MCP server "
                    f"'{service.service_name}': {e}"
                )

        # Also include shared MCP servers visible to this user
        try:
            shared_services = (
                UserExternalServiceService.list_shared_mcp_servers_for_user(user_id)
            )
            for service in shared_services:
                if service.service_name in seen_service_names:
                    continue  # User's own config takes precedence
                try:
                    server_config = _build_mcp_server_for_agent_shared(service)
                    servers.append(server_config)
                    seen_service_names.add(service.service_name)
                except Exception as e:
                    logger.error(
                        f"{LOG_PREFIX} Failed to build config for shared MCP server "
                        f"'{service.service_name}': {e}"
                    )
        except Exception as e:
            logger.warning(
                f"{LOG_PREFIX} Failed to load shared MCP servers for agent "
                f"for user '{user_id}': {e}"
            )

        # Log prominent warning if any servers have credential errors
        if failed_count > 0:
            logger.warning(
                f"{LOG_PREFIX} {failed_count} of {len(servers)} MCP servers have credential decryption errors "
                f"for user '{user_id}'. These servers are included in the response with has_credential_error=True "
                "and cannot be used until credentials are fixed."
            )

        logger.debug(
            f"{LOG_PREFIX} Retrieved {len(servers)} MCP servers for agent tool creation "
            f"({failed_count} with credential errors) for user '{user_id}'"
        )

        return GetMcpServersForAgentResponse(success=True, servers=servers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error getting MCP servers for agent: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get MCP servers for agent: {str(e)}"
        )


@router.post(
    "/mcp-servers/export-selected",
    response_model=ExportMcpServersResponse,
    response_model_exclude_none=True,
)
async def export_selected_mcp_servers(
    request: ExportMcpServersRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ExportMcpServersResponse:
    """Export selected MCP servers in standard .mcp.json format.

    This endpoint exports specific MCP servers by their IDs in the standard
    MCPServers JSON format compatible with Anthropic's Claude Code.

    Args:
        request: Export request with optional server_ids list
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        ExportMcpServersResponse: Selected MCP servers in standard format

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/user/settings/mcp-servers/export-selected" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "Content-Type: application/json" \\
          -d '{"server_ids": ["server-id-1", "server-id-2"]}'
        ```

    Notes:
        - If server_ids is empty or not provided, all active servers are exported
        - Only servers owned by the current user are exported
        - Credentials are included in the export (be careful with sensitive data)
    """
    try:
        user_id = get_user_identifier(current_user)

        # Get all MCP servers for the user
        all_services = UserExternalServiceService.list_user_services(user_id)
        mcp_services = [
            s for s in all_services if is_mcp_server(s.service_name) and s.is_active
        ]

        # Filter by server_ids if provided
        if request.server_ids:
            server_id_set = set(request.server_ids)
            mcp_services = [s for s in mcp_services if s.id in server_id_set]

        # Transform to standard format
        mcp_servers = {}
        exported_count = 0

        for service in mcp_services:
            try:
                server_key, standard_config = _transform_internal_to_standard(service)
                mcp_servers[server_key] = standard_config
                exported_count += 1
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to export MCP server "
                    f"'{service.service_name}': {e}"
                )
                # Continue with other servers

        logger.info(
            f"{LOG_PREFIX} Exported {exported_count} selected MCP servers for user '{user_id}'"
        )

        return ExportMcpServersResponse(mcpServers=mcp_servers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error exporting selected MCP servers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to export selected MCP servers: {str(e)}"
        )


@router.post("/mcp-servers/import", response_model=ImportMcpServersResponse)
async def import_mcp_servers(
    request: ImportMcpServersRequest,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> ImportMcpServersResponse:
    """Import MCP servers from standard .mcp.json format.

    This endpoint imports MCP servers from the standard MCPServers JSON format
    used by Anthropic's Claude Code and other MCP clients.

    Args:
        request: Import request with mcpServers configuration
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        ImportMcpServersResponse: Import status with counts and errors

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/user/settings/mcp-servers/import" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "Content-Type: application/json" \\
          -H "X-CSRF-Token: 1" \\
          -d @my-mcp-servers.json
        ```

    Notes:
        - By default, existing servers with same name are skipped
        - Set overwrite_existing=true to replace existing servers
        - Environment variable expansion (${VAR}) is not performed server-side
        - Failed imports are reported in the errors array
    """
    try:
        user_id = get_user_identifier(current_user)

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        errors = []

        logger.info(
            f"{LOG_PREFIX} Importing {len(request.mcpServers)} MCP servers "
            f"for user '{user_id}' (overwrite={request.overwrite_existing})"
        )

        for server_key, server_config in request.mcpServers.items():
            try:
                # Validate server name
                validate_mcp_server_name(server_key)

                # Check if server already exists
                service_name = build_mcp_service_name(server_key)
                existing_service = UserExternalServiceService.get_service(
                    user_id, service_name
                )

                if existing_service and not request.overwrite_existing:
                    logger.debug(
                        f"{LOG_PREFIX} Skipping existing MCP server '{server_key}'"
                    )
                    skipped_count += 1
                    continue

                # Transform to internal format
                internal_request, _ = _transform_standard_to_internal(
                    server_key, server_config
                )

                # Save the server
                settings = _serialize_mcp_config_to_settings(internal_request)
                credentials_json = _extract_credentials_from_request(internal_request)

                UserExternalServiceService.save_service(
                    user_id=user_id,
                    service_name=service_name,
                    api_key=credentials_json or "",
                    settings=settings,
                )

                imported_count += 1
                logger.debug(
                    f"{LOG_PREFIX} Imported MCP server '{server_key}' "
                    f"({'overwrote' if existing_service else 'created'})"
                )

            except ValueError as e:
                # Validation error
                error_msg = f"Validation error for server '{server_key}': {str(e)}"
                logger.warning(f"{LOG_PREFIX} {error_msg}")
                errors.append({"server": server_key, "error": error_msg})
                failed_count += 1

            except Exception as e:
                # Other errors
                error_msg = f"Failed to import server '{server_key}': {str(e)}"
                logger.error(f"{LOG_PREFIX} {error_msg}")
                errors.append({"server": server_key, "error": error_msg})
                failed_count += 1

        # Build response message
        message_parts = []
        if imported_count > 0:
            message_parts.append(f"{imported_count} server(s) imported")
        if skipped_count > 0:
            message_parts.append(f"{skipped_count} server(s) skipped (already exist)")
        if failed_count > 0:
            message_parts.append(f"{failed_count} server(s) failed")

        message = ", ".join(message_parts) if message_parts else "No servers imported"

        logger.info(f"{LOG_PREFIX} Import completed for user '{user_id}': {message}")

        return ImportMcpServersResponse(
            success=failed_count == 0,
            message=message,
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error importing MCP servers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to import MCP servers: {str(e)}"
        )


@router.get("/mcp-servers/public", response_model=ListPublicMcpServersResponse)
async def list_public_mcp_servers(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ListPublicMcpServersResponse:
    """List all public MCP servers from other users.

    This endpoint returns MCP servers that other users have marked as public,
    allowing the current user to discover and clone them.

    Returns:
        ListPublicMcpServersResponse: List of public servers (excluding current user's)
    """
    try:
        user_id = get_user_identifier(current_user)

        # Get public servers excluding current user's own public servers
        public_services = UserExternalServiceService.list_public_mcp_servers(
            exclude_user_id=user_id
        )

        # Build server info with creator attribution and masked credentials
        servers = []
        for service in public_services:
            try:
                # Mask credentials for public servers viewed by non-owners
                server_info = _build_mcp_server_info(service, mask_credentials=True)

                # Override ownership flag
                server_info.is_owned_by_current_user = False
                server_info.creator_name = _get_user_display_name(service.user)

                servers.append(server_info)
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to build info for public MCP server "
                    f"'{service.service_name}': {e}"
                )

        logger.debug(
            f"{LOG_PREFIX} Listed {len(servers)} public MCP servers for user '{user_id}'"
        )

        return ListPublicMcpServersResponse(success=True, servers=servers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error listing public MCP servers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list public MCP servers: {str(e)}"
        )


@router.get("/mcp-servers/{server_name}", response_model=McpServerInfo)
async def get_mcp_server(
    server_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> McpServerInfo:
    """Get details for a specific MCP server.

    Args:
        server_name: User-provided name of the MCP server
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        McpServerInfo: Server configuration details

    Raises:
        HTTPException: 404 if server not found, 400 if invalid name

    Example:
        ```bash
        curl "http://localhost:8000/api/user/settings/mcp-servers/my-server" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate server name format
        try:
            validate_mcp_server_name(server_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Build full service name
        service_name = build_mcp_service_name(server_name)

        # Get service record
        service = UserExternalServiceService.get_service(user_id, service_name)

        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"MCP server '{server_name}' not configured",
            )

        # Build and return server info
        return _build_mcp_server_info(service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error getting MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get MCP server: {str(e)}"
        )


@router.put("/mcp-servers/{server_name}", response_model=SaveMcpServerResponse)
async def save_mcp_server(
    server_name: str,
    request: McpServerConfigRequest,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> SaveMcpServerResponse:
    """Create or update an MCP server configuration.

    Args:
        server_name: User-provided name of the MCP server
        request: MCP server configuration
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        SaveMcpServerResponse: Confirmation with server info

    Raises:
        HTTPException: 400 if validation fails

    Example:
        ```bash
        curl -X PUT "http://localhost:8000/api/user/settings/mcp-servers/my-server" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "Content-Type: application/json" \\
          -d '{
            "server_name": "My Custom Server",
            "connection_type": "http",
            "server_url": "https://mcp.example.com",
            "auth_type": "bearer",
            "auth_credentials": {"bearer_token": "my-token"}
          }'
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate server name format
        try:
            validate_mcp_server_name(server_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Build full service name
        service_name = build_mcp_service_name(server_name)

        # Serialize non-sensitive config to settings
        settings = _serialize_mcp_config_to_settings(request)

        # Extract credentials as JSON string (not pre-encrypted)
        # Let save_service() perform the single encryption
        credentials_json = _extract_credentials_from_request(request)

        # Check if this is an update of an existing server
        existing_service = UserExternalServiceService.get_service(user_id, service_name)

        # Determine the credentials to save
        # Special handling for oauth2: Never save access tokens to database
        # oauth2 auth uses runtime user tokens from execution context
        if request.auth_type == "oauth2" and credentials_json:
            # User provided credentials for oauth2, but we should NOT save them
            # because oauth2 uses dynamic user tokens, not static credentials
            logger.warning(
                f"{LOG_PREFIX} oauth2 auth_type provided with credentials, but oauth2 should use "
                f"dynamic user tokens from execution context. Credentials will NOT be saved to database. "
                f"If you need a static token, use auth_type 'bearer' instead."
            )
            api_key_to_save = ""
        elif credentials_json:
            # New credentials provided - use them
            api_key_to_save = credentials_json
        elif existing_service and existing_service.encrypted_api_key:
            # No new credentials provided, but existing credentials exist - preserve them
            # We'll use a special flag to indicate "preserve existing"
            api_key_to_save = None  # Signal to preserve
        elif request.auth_type not in (
            "none",
            "oauth2",
            "oauth_host_identity",
            "mcp_oauth",
        ):
            # No credentials provided, no existing credentials, but auth requires them
            raise HTTPException(
                status_code=400,
                detail=f"auth_credentials is required when creating a new server with auth_type '{request.auth_type}'",
            )
        else:
            # No auth required or oauth2 (which may not need upfront credentials)
            api_key_to_save = ""

        logger.info(
            f"{LOG_PREFIX} Saving MCP server '{server_name}': "
            f"auth_type={request.auth_type}, "
            f"has_new_credentials={bool(credentials_json)}, "
            f"has_existing_credentials={bool(existing_service and existing_service.encrypted_api_key)}, "
            f"will_preserve_existing={api_key_to_save is None}, "
            f"credentials_keys={list(request.auth_credentials.keys()) if request.auth_credentials else []}"
        )

        # Save the service configuration
        if api_key_to_save is None:
            # Preserve existing credentials - use the encrypted value directly
            service = UserExternalServiceService.save_service_preserve_credentials(
                user_id=user_id,
                service_name=service_name,
                settings=settings,
            )
        else:
            service = UserExternalServiceService.save_service(
                user_id=user_id,
                service_name=service_name,
                api_key=api_key_to_save,
                settings=settings,
            )

        logger.info(
            f"{LOG_PREFIX} Saved MCP server '{server_name}' for user '{user_id}'"
        )

        # Update visibility and sharing if provided
        if request.visibility is not None:
            service = UserExternalServiceService.update_server_visibility(
                user_id=user_id,
                service_name=service_name,
                visibility=request.visibility.value,
                shared_with_group_ids=request.shared_with_group_ids,
            )
            logger.info(
                f"{LOG_PREFIX} Updated visibility for server '{server_name}' to '{request.visibility.value}'"
            )

        # Build response
        server_info = _build_mcp_server_info(service)

        return SaveMcpServerResponse(
            success=True,
            message=f"MCP server '{server_name}' configured successfully",
            server=server_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error saving MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save MCP server: {str(e)}"
        )


@router.patch("/mcp-servers/{server_name}/toggle", response_model=SaveMcpServerResponse)
async def toggle_mcp_server(
    server_name: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> SaveMcpServerResponse:
    """Toggle MCP server active status.

    Args:
        server_name: User-provided name of the MCP server
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        SaveMcpServerResponse: Updated server info

    Raises:
        HTTPException: 404 if server not found, 400 if invalid name

    Example:
        ```bash
        curl -X PATCH "http://localhost:8000/api/user/settings/mcp-servers/my-server/toggle" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "X-CSRF-Token: 1"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate server name format
        try:
            validate_mcp_server_name(server_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Build full service name
        service_name = build_mcp_service_name(server_name)

        # Get existing service
        existing_service = UserExternalServiceService.get_service(user_id, service_name)

        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail=f"MCP server '{server_name}' not configured",
            )

        # Toggle the is_active field
        new_active_status = not existing_service.is_active

        # Update the service with toggled status
        with get_db() as db:
            service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if service:
                service.is_active = new_active_status
                db.commit()
                db.refresh(service)
                db.expunge(service)

        logger.info(
            f"{LOG_PREFIX} Toggled MCP server '{server_name}' for user '{user_id}': is_active={new_active_status}"
        )

        # Fetch updated service
        updated_service = UserExternalServiceService.get_service(user_id, service_name)

        # Build response
        server_info = _build_mcp_server_info(updated_service)

        return SaveMcpServerResponse(
            success=True,
            message=f"MCP server '{server_name}' {'enabled' if new_active_status else 'disabled'} successfully",
            server=server_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error toggling MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to toggle MCP server: {str(e)}"
        )


@router.delete("/mcp-servers/by-id/{server_id}", response_model=DeleteMcpServerResponse)
async def delete_mcp_server_by_id(
    server_id: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> DeleteMcpServerResponse:
    """Delete an MCP server configuration by ID.

    Args:
        server_id: Unique ID of the MCP server
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        DeleteMcpServerResponse: Confirmation of deletion

    Raises:
        HTTPException: 404 if server not found

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/user/settings/mcp-servers/by-id/{server_id}" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Look up the service before deleting to get server_name for cleanup
        server_name_for_cleanup = None
        try:
            with get_db() as db:
                service = (
                    db.query(UserExternalService)
                    .filter(
                        UserExternalService.id == server_id,
                        UserExternalService.user_id == user_id,
                    )
                    .first()
                )
                if service and is_mcp_server(service.service_name):
                    server_name_for_cleanup = extract_mcp_server_name(
                        service.service_name
                    )
        except Exception:
            pass  # Non-critical — cleanup is best-effort

        # Delete the service by ID
        success = UserExternalServiceService.delete_service_by_id(user_id, server_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"MCP server with ID '{server_id}' not found",
            )

        # Clean up any MCP OAuth data for this server
        if server_name_for_cleanup:
            try:
                from backend.services.oauth.storage import oauth_storage

                provider = f"mcp:{server_name_for_cleanup}"
                oauth_storage.delete_all_for_user(user_id, provider)
            except Exception as e:
                logger.warning(
                    f"{LOG_PREFIX} Failed to clean up MCP OAuth data for '{server_name_for_cleanup}': {e}"
                )

        logger.info(
            f"{LOG_PREFIX} Deleted MCP server with ID '{server_id}' for user '{user_id}'"
        )

        return DeleteMcpServerResponse(
            success=True,
            message="MCP server deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error deleting MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete MCP server: {str(e)}"
        )


@router.delete("/mcp-servers/{server_name}", response_model=DeleteMcpServerResponse)
async def delete_mcp_server(
    server_name: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> DeleteMcpServerResponse:
    """Delete an MCP server configuration by name (deprecated - use by-id endpoint).

    Args:
        server_name: User-provided name of the MCP server
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        DeleteMcpServerResponse: Confirmation of deletion

    Raises:
        HTTPException: 404 if server not found, 400 if invalid name

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/user/settings/mcp-servers/my-server" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate server name format
        try:
            validate_mcp_server_name(server_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Build full service name
        service_name = build_mcp_service_name(server_name)

        # Delete the service
        success = UserExternalServiceService.delete_service(user_id, service_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"MCP server '{server_name}' not configured",
            )

        # Clean up any MCP OAuth data for this server
        try:
            from backend.services.oauth.storage import oauth_storage

            provider = f"mcp:{server_name}"
            oauth_storage.delete_all_for_user(user_id, provider)
        except Exception as e:
            logger.warning(
                f"{LOG_PREFIX} Failed to clean up MCP OAuth data for '{server_name}': {e}"
            )

        logger.info(
            f"{LOG_PREFIX} Deleted MCP server '{server_name}' for user '{user_id}'"
        )

        return DeleteMcpServerResponse(
            success=True,
            message=f"MCP server '{server_name}' deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error deleting MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete MCP server: {str(e)}"
        )


@router.post("/mcp-servers/test-connection", response_model=TestMcpConnectionResponse)
async def test_mcp_connection(
    mcp_request: McpServerConfigRequest,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> TestMcpConnectionResponse:
    """Test MCP server connection without saving configuration.

    This endpoint tests an MCP server connection using the provided configuration
    without persisting it to the database. It verifies connectivity and retrieves
    available tools from the server.

    Args:
        mcp_request: MCP server configuration to test
        http_request: HTTP request object for extracting user token
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        TestMcpConnectionResponse: Connection status, available tools, and error details

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/user/settings/mcp-servers/test-connection" \\
          -H "Authorization: Bearer <jwt>" \\
          -H "Content-Type: application/json" \\
          -d '{
            "server_name": "Test Server",
            "connection_type": "http",
            "server_url": "https://mcp.example.com",
            "auth_type": "bearer",
            "auth_credentials": {"bearer_token": "my-token"},
            "timeout_seconds": 30
          }'
        ```

    Note:
        - This endpoint does not require CSRF token since it's a read-only test operation
        - Credentials are not stored, only used for testing
        - The test uses mcp_client_manager.test_connection() for consistency with production
    """
    # Initialize user_id to a safe default before the try block
    user_id = "<unknown>"
    try:
        user_id = get_user_identifier(current_user)

        logger.info(
            f"{LOG_PREFIX} Testing MCP connection for user '{user_id}': "
            f"server_name='{mcp_request.server_name}', "
            f"connection_type='{mcp_request.connection_type}', "
            f"auth_type='{mcp_request.auth_type}'"
        )

        # Transform request to config format expected by mcp_client_manager
        config = _transform_mcp_request_to_config(mcp_request)

        # For OAuth2 (User Identity) auth, set user's access token in execution context
        if mcp_request.auth_type == "oauth2":
            from backend.services.auth import extract_token_from_request
            from backend.services.execution.context.store import (
                current_user_access_token,
            )

            # Debug: Log request headers
            logger.debug(
                f"{LOG_PREFIX} Request headers for OAuth2: {dict(http_request.headers)}"
            )

            user_access_token = extract_token_from_request(http_request)
            logger.debug(
                f"{LOG_PREFIX} Extracted token from request "
                f"(present={bool(user_access_token)}, length={len(user_access_token) if user_access_token else 0})"
            )

            if user_access_token:
                logger.debug(
                    f"{LOG_PREFIX} Setting user access token in execution context for OAuth2 test (length: {len(user_access_token)})"
                )
                # Set token in execution context so mcp_client_manager can retrieve it
                current_user_access_token.set(user_access_token)
            else:
                logger.warning(
                    f"{LOG_PREFIX} OAuth2 auth requested but no user token found in request"
                )

        # For MCP OAuth, inject user_id and server_url into auth_config
        if mcp_request.auth_type == "mcp_oauth":
            config["auth_config"]["user_id"] = user_id
            config["auth_config"]["server_name"] = mcp_request.server_name
            config["auth_config"]["server_url"] = mcp_request.server_url or ""

        # Import mcp_client_manager
        from backend.mcp_client_manager import mcp_client_manager

        # Test the connection
        result = await mcp_client_manager.test_connection(config)

        # Extract response fields
        success = result.get("success", False)
        server_name = result.get("server_name", mcp_request.server_name)
        tool_count = result.get("tool_count", 0)
        error_msg = result.get("error")

        # Map tools to McpToolInfo models
        tools = []
        if success and "tools" in result:
            for tool in result["tools"]:
                tools.append(
                    McpToolInfo(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                    )
                )

        # Log the result
        if success:
            logger.info(
                f"{LOG_PREFIX} MCP connection test successful for user '{user_id}': "
                f"server='{server_name}', tools={tool_count}"
            )
        else:
            logger.warning(
                f"{LOG_PREFIX} MCP connection test failed for user '{user_id}': "
                f"server='{server_name}', error='{error_msg}'"
            )

        return TestMcpConnectionResponse(
            success=success,
            server_name=server_name,
            tool_count=tool_count,
            tools=tools,
            error=error_msg,
            connection_type=mcp_request.connection_type,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            f"{LOG_PREFIX} Validation error testing MCP connection for user '{user_id}': {e}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"{LOG_PREFIX} Unexpected error testing MCP connection for user '{user_id}': "
            f"server_name='{mcp_request.server_name}', "
            f"connection_type='{mcp_request.connection_type}', "
            f"auth_type='{mcp_request.auth_type}', "
            f"error={e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to test MCP connection: An unexpected error occurred",
        )
    finally:
        # Clean up: Clear the user access token from execution context
        # to prevent token leakage between requests
        if mcp_request.auth_type == "oauth2":
            from backend.services.execution.context.store import (
                current_user_access_token,
            )

            current_user_access_token.set(None)
            logger.debug(
                f"{LOG_PREFIX} Cleared user access token from execution context"
            )


@router.post("/mcp-servers/clone", response_model=CloneMcpServerResponse)
async def clone_mcp_server(
    request: CloneMcpServerRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
) -> CloneMcpServerResponse:
    """Clone a public MCP server to current user's account.

    Creates a copy of a public MCP server with the user's chosen name.
    Credentials are NOT copied - user must provide their own credentials.

    Args:
        request: Clone request with source server ID and new name
        current_user: Authenticated user

    Returns:
        CloneMcpServerResponse: Information about cloned server
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate server name
        try:
            validate_mcp_server_name(request.new_server_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Clone the server
        cloned_server = UserExternalServiceService.clone_mcp_server(
            source_server_id=request.source_server_id,
            target_user_id=user_id,
            new_server_name=request.new_server_name,
        )

        logger.info(
            f"{LOG_PREFIX} User '{user_id}' cloned server '{request.source_server_id}' "
            f"as '{request.new_server_name}'"
        )

        # Build response
        server_info = _build_mcp_server_info(cloned_server)

        return CloneMcpServerResponse(
            success=True,
            message=f"Server '{request.new_server_name}' cloned successfully. "
            "Please configure credentials to activate.",
            server=server_info,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error cloning MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to clone MCP server: {str(e)}"
        )


@router.patch(
    "/mcp-servers/{server_name}/visibility", response_model=SaveMcpServerResponse
)
async def update_mcp_server_visibility(
    server_name: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
) -> SaveMcpServerResponse:
    """Update MCP server visibility and sharing.

    When changing to shared:
    - Credentials are kept but masked from non-owners for security
    - Server becomes discoverable by other users (everyone or specific groups)
    - Other users can clone it (without credentials)

    Request body:
        visibility: "private" or "shared"
        shared_with_group_ids: list of group IDs (optional, empty = everyone)

    Args:
        server_name: Name of the server to update
        request: HTTP request with JSON body
        current_user: Authenticated user

    Returns:
        SaveMcpServerResponse: Updated server information
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate server name
        try:
            validate_mcp_server_name(server_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Parse request body
        body = await request.json()
        visibility_str = body.get("visibility")
        if not visibility_str:
            raise HTTPException(status_code=400, detail="visibility is required")

        # Validate visibility value
        try:
            visibility = McpServerVisibility(visibility_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid visibility: {visibility_str}. Must be 'private' or 'shared'.",
            )

        shared_with_group_ids = body.get("shared_with_group_ids", [])

        service_name = build_mcp_service_name(server_name)

        # Update visibility and sharing
        updated_server = UserExternalServiceService.update_server_visibility(
            user_id=user_id,
            service_name=service_name,
            visibility=visibility.value,
            shared_with_group_ids=shared_with_group_ids,
        )

        logger.info(
            f"{LOG_PREFIX} Updated visibility for server '{server_name}' to "
            f"'{visibility.value}' for user '{user_id}'"
        )

        # Build response
        server_info = _build_mcp_server_info(updated_server)

        message = f"Server '{server_name}' is now {visibility.value}"
        if visibility == McpServerVisibility.SHARED:
            message += ". Credentials will be masked from other users."

        return SaveMcpServerResponse(success=True, message=message, server=server_info)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error updating server visibility: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update server visibility: {str(e)}"
        )


# ── MCP Integration (Official Provider) Endpoints ───────────────────────


@router.get("/mcp-integrations", response_model=ListMcpIntegrationsResponse)
async def list_mcp_integrations(
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
) -> ListMcpIntegrationsResponse:
    """List all official MCP integrations with their configuration status."""
    user_id = get_user_identifier(current_user)
    return await handle_list_integrations(user_id)


@router.get(
    "/mcp-integrations/{provider}/for-workflow",
    response_model=McpIntegrationForWorkflowResponse,
)
async def get_mcp_integration_for_workflow(
    provider: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
) -> McpIntegrationForWorkflowResponse:
    """Get resolved integration config ready for workflow node population."""
    user_id = get_user_identifier(current_user)
    return await handle_get_integration_for_workflow(user_id, provider)


@router.get("/mcp-integrations/{provider}", response_model=GetMcpIntegrationResponse)
async def get_mcp_integration(
    provider: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
) -> GetMcpIntegrationResponse:
    """Get full configuration for a specific official integration."""
    user_id = get_user_identifier(current_user)
    return await handle_get_integration(user_id, provider)


@router.put("/mcp-integrations/{provider}", response_model=SaveMcpIntegrationResponse)
async def save_mcp_integration(
    provider: str,
    request: SaveMcpIntegrationRequest,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> SaveMcpIntegrationResponse:
    """Save or update a personal official integration configuration."""
    user_id = get_user_identifier(current_user)
    return await handle_save_integration(user_id, provider, request)


@router.delete(
    "/mcp-integrations/{provider}", response_model=DeleteMcpIntegrationResponse
)
async def delete_mcp_integration(
    provider: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> DeleteMcpIntegrationResponse:
    """Remove personal integration config (falls back to system default)."""
    user_id = get_user_identifier(current_user)
    return await handle_delete_integration(user_id, provider)


@router.patch(
    "/mcp-integrations/{provider}/toggle", response_model=SaveMcpIntegrationResponse
)
async def toggle_mcp_integration(
    provider: str,
    current_user: Dict[str, Any] = Depends(
        require_feature_access("settings.mcp_servers")
    ),
    _csrf: None = Depends(verify_csrf_token),
) -> SaveMcpIntegrationResponse:
    """Toggle an official integration's active status."""
    user_id = get_user_identifier(current_user)
    return await handle_toggle_integration(user_id, provider)
