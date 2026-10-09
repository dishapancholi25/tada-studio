"""Handler functions for official MCP integration CRUD operations.

These handlers manage the lifecycle of preset MCP integrations (GitHub,
Atlassian, Databricks, etc.) stored in the user_external_services and
system_external_services tables with the ``mcp_preset_`` prefix.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_

from backend.encryption_utils import decrypt_credential
from backend.models.auth.user_external_service import UserExternalService
from backend.services.auth.user_external_service import UserExternalServiceService
from backend.services.configuration.credential_resolution_service import (
    CredentialResolutionService,
)
from backend.services.configuration.group_external_service_service import (
    GroupExternalServiceService,
)
from backend.services.configuration.system_external_service_service import (
    SystemExternalServiceService,
)
from backend.services.database import get_db
from backend.tools.mcp_presets import get_provider_defaults

from .constants import (
    OFFICIAL_PROVIDER_DISPLAY_NAMES,
    OFFICIAL_PROVIDERS,
    build_mcp_preset_name,
)
from .models import (
    DeleteMcpIntegrationResponse,
    GetMcpIntegrationResponse,
    ListMcpIntegrationsResponse,
    McpIntegrationConfig,
    McpIntegrationForWorkflowResponse,
    McpIntegrationSummary,
    SaveMcpIntegrationRequest,
    SaveMcpIntegrationResponse,
)


logger = logging.getLogger(__name__)
LOG_PREFIX = "[MCP-INTEGRATIONS]"


def _build_integration_summary(
    provider: str,
    user_service: Optional[UserExternalService],
    has_system_default: bool,
    has_group_default: bool = False,
    group_names: Optional[List[str]] = None,
) -> McpIntegrationSummary:
    """Build a summary for a single integration provider."""
    settings = (user_service.settings or {}) if user_service else {}
    tool_permissions = settings.get("tool_permissions", {})

    return McpIntegrationSummary(
        provider=provider,
        display_name=OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider),
        is_configured=user_service is not None,
        is_active=user_service.is_active
        if user_service
        else (has_group_default or has_system_default),
        has_system_default=has_system_default,
        has_group_default=has_group_default,
        group_names=group_names or [],
        tool_count=len(tool_permissions) if tool_permissions else None,
        tool_permissions=tool_permissions,
    )


def _build_integration_config(
    provider: str,
    user_service: Optional[UserExternalService],
    has_system_default: bool,
    has_group_default: bool = False,
    group_names: Optional[List[str]] = None,
) -> McpIntegrationConfig:
    """Build a full config response for a single integration provider."""
    settings = (user_service.settings or {}) if user_service else {}
    tool_permissions = settings.get("tool_permissions", {})

    credentials_configured = False
    if user_service and user_service.encrypted_api_key:
        try:
            decrypted = decrypt_credential(user_service.encrypted_api_key)
            credentials_configured = bool(decrypted)
        except Exception:
            pass

    # Group config counts as credentials configured if user has no personal config
    if not credentials_configured and has_group_default:
        credentials_configured = True

    return McpIntegrationConfig(
        provider=provider,
        display_name=OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider),
        is_configured=user_service is not None,
        is_active=user_service.is_active
        if user_service
        else (has_group_default or has_system_default),
        has_system_default=has_system_default,
        has_group_default=has_group_default,
        group_names=group_names or [],
        credentials_configured=credentials_configured,
        settings=settings,
        tool_permissions=tool_permissions,
    )


# ── List ─────────────────────────────────────────────────────────────────


async def handle_list_integrations(
    user_id: str,
) -> ListMcpIntegrationsResponse:
    """List all official integrations with their status for the current user."""
    # Fetch group configs once for efficiency
    group_configs = GroupExternalServiceService.get_configs_for_user(user_id)
    group_config_map: Dict[str, List[str]] = {}  # service_name -> [group_names]
    for config, gnames in group_configs:
        group_config_map.setdefault(config.service_name, []).extend(gnames)

    summaries = []
    for provider in OFFICIAL_PROVIDERS:
        service_name = build_mcp_preset_name(provider)
        user_service = UserExternalServiceService.get_service(user_id, service_name)
        has_system_default = CredentialResolutionService.system_default_configured(
            service_name
        )
        group_names = group_config_map.get(service_name, [])
        has_group_default = bool(group_names)
        summaries.append(
            _build_integration_summary(
                provider,
                user_service,
                has_system_default,
                has_group_default=has_group_default,
                group_names=group_names,
            )
        )

    return ListMcpIntegrationsResponse(success=True, integrations=summaries)


# ── Get ──────────────────────────────────────────────────────────────────


async def handle_get_integration(
    user_id: str,
    provider: str,
) -> GetMcpIntegrationResponse:
    """Get full config for a single integration."""
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)
    user_service = UserExternalServiceService.get_service(user_id, service_name)
    has_system_default = CredentialResolutionService.system_default_configured(
        service_name
    )
    group_config = None
    group_names: List[str] = []
    for cfg, gnames in GroupExternalServiceService.get_configs_for_user(user_id):
        if cfg.service_name == service_name and cfg.is_active:
            group_config = cfg
            group_names = gnames
            break
    has_group_default = group_config is not None

    config = _build_integration_config(
        provider,
        user_service,
        has_system_default,
        has_group_default=has_group_default,
        group_names=group_names,
    )
    return GetMcpIntegrationResponse(success=True, integration=config)


# ── Save ─────────────────────────────────────────────────────────────────


async def handle_save_integration(
    user_id: str,
    provider: str,
    request: SaveMcpIntegrationRequest,
) -> SaveMcpIntegrationResponse:
    """Save or update a personal integration config."""
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)
    existing = UserExternalServiceService.get_service(user_id, service_name)

    # Build settings dict: merge provider defaults with user-provided settings
    provider_defaults = get_provider_defaults(provider)
    settings: Dict[str, Any] = {}

    # Start with existing settings if updating
    if existing and existing.settings:
        settings.update(existing.settings)

    # Always ensure provider is set
    settings["provider"] = provider

    # Apply user-provided settings (overrides)
    if request.settings:
        settings.update(request.settings)

    # Copy relevant defaults from provider_defaults if not already set
    for key in (
        "connection_type",
        "server_url",
        "command",
        "args",
        "auth_type",
        "timeout_seconds",
        "max_retries",
        "retry_delay",
        "description",
    ):
        if key not in settings and key in provider_defaults:
            settings[key] = provider_defaults[key]

    # Handle credentials
    credentials_json: Optional[str] = None
    if request.credentials:
        credentials_json = json.dumps(request.credentials)

    auth_type = settings.get("auth_type", provider_defaults.get("auth_type", "none"))

    if credentials_json:
        api_key_to_save = credentials_json
    elif existing and existing.encrypted_api_key:
        api_key_to_save = None  # Preserve existing
    elif auth_type in ("none", "oauth", "oauth2", "mcp_oauth", "oauth_host_identity"):
        api_key_to_save = ""
    else:
        api_key_to_save = ""

    # Save
    if api_key_to_save is None:
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

    # Set active status
    if not request.is_active and service.is_active:
        _set_active_status(user_id, service_name, False)
    elif request.is_active and not service.is_active:
        _set_active_status(user_id, service_name, True)

    # Re-fetch for response
    updated = UserExternalServiceService.get_service(user_id, service_name)
    has_system_default = CredentialResolutionService.system_default_configured(
        service_name
    )
    integration_config = _build_integration_config(
        provider, updated, has_system_default
    )

    logger.info(
        "%s Saved integration '%s' for user '%s'", LOG_PREFIX, provider, user_id
    )

    return SaveMcpIntegrationResponse(
        success=True,
        message=f"{OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider)} integration configured successfully",
        integration=integration_config,
    )


# ── Delete ───────────────────────────────────────────────────────────────


async def handle_delete_integration(
    user_id: str,
    provider: str,
) -> DeleteMcpIntegrationResponse:
    """Remove a personal integration config (falls back to system default)."""
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)
    deleted = UserExternalServiceService.delete_service(user_id, service_name)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Integration '{provider}' not configured for this user",
        )

    logger.info(
        "%s Deleted integration '%s' for user '%s'", LOG_PREFIX, provider, user_id
    )

    return DeleteMcpIntegrationResponse(
        success=True,
        message=f"{OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider)} personal configuration removed",
    )


# ── Toggle ───────────────────────────────────────────────────────────────


async def handle_toggle_integration(
    user_id: str,
    provider: str,
) -> SaveMcpIntegrationResponse:
    """Toggle an integration's active status."""
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)
    existing = UserExternalServiceService.get_service(user_id, service_name)

    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Integration '{provider}' not configured. Configure it first.",
        )

    new_status = not existing.is_active
    _set_active_status(user_id, service_name, new_status)

    updated = UserExternalServiceService.get_service(user_id, service_name)
    has_system_default = CredentialResolutionService.system_default_configured(
        service_name
    )
    integration_config = _build_integration_config(
        provider, updated, has_system_default
    )

    display = OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider)
    status_label = "enabled" if new_status else "disabled"

    logger.info(
        "%s Toggled integration '%s' to %s for user '%s'",
        LOG_PREFIX,
        provider,
        status_label,
        user_id,
    )

    return SaveMcpIntegrationResponse(
        success=True,
        message=f"{display} integration {status_label} successfully",
        integration=integration_config,
    )


# ── For Workflow ─────────────────────────────────────────────────────────


async def handle_get_integration_for_workflow(
    user_id: str,
    provider: str,
) -> McpIntegrationForWorkflowResponse:
    """Get resolved integration config ready for workflow node population.

    Resolution order: user-tier → group-tier → system-tier → provider defaults.
    Credentials are decrypted server-side.
    """
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)

    # Try user tier first
    user_service = UserExternalServiceService.get_service(user_id, service_name)

    # Try group tier
    group_config = None
    if not user_service or not user_service.is_active:
        group_config = GroupExternalServiceService.get_config_for_user_service(
            user_id, service_name
        )

    # Try system tier
    sys_service = None
    if (not user_service or not user_service.is_active) and not group_config:
        sys_service = SystemExternalServiceService.get_service(service_name)

    # Determine which tier is active
    if user_service:
        source_service = user_service
        source_is_active = user_service.is_active
    elif group_config:
        source_service = None  # handled separately below
        source_is_active = group_config.is_active
    elif sys_service:
        source_service = sys_service
        source_is_active = sys_service.is_active
    else:
        source_service = None
        source_is_active = False

    if not source_is_active and group_config is None:
        return McpIntegrationForWorkflowResponse(
            success=True, configured=False, mcp_server_config=None
        )

    if group_config is not None and not user_service and not sys_service:
        # Build from group config
        provider_defaults = get_provider_defaults(provider)
        settings = group_config.settings or {}

        mcp_config: Dict[str, Any] = {
            "provider": provider,
            "server_name": settings.get(
                "server_name", provider_defaults.get("server_name", "")
            ),
            "connection_type": settings.get(
                "connection_type", provider_defaults.get("connection_type", "http")
            ),
            "auth_type": settings.get(
                "auth_type", provider_defaults.get("auth_type", "none")
            ),
            "timeout_seconds": settings.get(
                "timeout_seconds", provider_defaults.get("timeout_seconds", 30)
            ),
            "max_retries": settings.get(
                "max_retries", provider_defaults.get("max_retries", 3)
            ),
            "retry_delay": settings.get(
                "retry_delay", provider_defaults.get("retry_delay", 1.0)
            ),
            "description": settings.get(
                "description", provider_defaults.get("description", "")
            ),
        }
        for key in (
            "server_url",
            "command",
            "args",
            "working_directory",
            "environment_variables",
            "metadata",
        ):
            val = settings.get(key, provider_defaults.get(key))
            if val:
                mcp_config[key] = val
        if "tool_permissions" in settings:
            mcp_config["tool_permissions"] = settings["tool_permissions"]

        # Resolve credentials from group config
        auth_config: Dict[str, Any] = {}
        group_api_key = GroupExternalServiceService.get_decrypted_api_key(group_config)
        if group_api_key:
            try:
                auth_config = json.loads(group_api_key)
            except json.JSONDecodeError:
                auth_config = {"access_token": group_api_key}
        else:
            group_creds = GroupExternalServiceService.get_decrypted_credentials(
                group_config
            )
            if group_creds:
                auth_config = group_creds

        auth_type = mcp_config["auth_type"]
        if auth_type == "oauth":
            oauth_provider = provider_defaults.get("auth_config", {}).get(
                "provider", provider
            )
            auth_config["provider"] = oauth_provider
            auth_config["user_id"] = user_id
        elif auth_type == "mcp_oauth":
            auth_config["user_id"] = user_id

        mcp_config["auth_config"] = auth_config
        return McpIntegrationForWorkflowResponse(
            success=True, configured=True, mcp_server_config=mcp_config
        )

    # Build MCP server config from stored settings + provider defaults
    provider_defaults = get_provider_defaults(provider)
    settings = source_service.settings or {}

    mcp_config: Dict[str, Any] = {
        "provider": provider,
        "server_name": settings.get(
            "server_name", provider_defaults.get("server_name", "")
        ),
        "connection_type": settings.get(
            "connection_type", provider_defaults.get("connection_type", "http")
        ),
        "auth_type": settings.get(
            "auth_type", provider_defaults.get("auth_type", "none")
        ),
        "timeout_seconds": settings.get(
            "timeout_seconds", provider_defaults.get("timeout_seconds", 30)
        ),
        "max_retries": settings.get(
            "max_retries", provider_defaults.get("max_retries", 3)
        ),
        "retry_delay": settings.get(
            "retry_delay", provider_defaults.get("retry_delay", 1.0)
        ),
        "description": settings.get(
            "description", provider_defaults.get("description", "")
        ),
    }

    # Add optional fields
    for key in (
        "server_url",
        "command",
        "args",
        "working_directory",
        "environment_variables",
        "metadata",
    ):
        val = settings.get(key, provider_defaults.get(key))
        if val:
            mcp_config[key] = val

    # Tool permissions
    if "tool_permissions" in settings:
        mcp_config["tool_permissions"] = settings["tool_permissions"]

    # Resolve auth_config with decrypted credentials
    auth_config: Dict[str, Any] = {}
    if source_service.encrypted_api_key:
        try:
            decrypted = decrypt_credential(source_service.encrypted_api_key)
            if decrypted:
                try:
                    auth_config = json.loads(decrypted)
                except json.JSONDecodeError:
                    # Single key value
                    auth_config = {"access_token": decrypted}
        except Exception as e:
            logger.warning(
                "%s Failed to decrypt credentials for %s: %s",
                LOG_PREFIX,
                provider,
                e,
            )

    # For OAuth providers, inject user_id and provider into auth_config
    auth_type = mcp_config["auth_type"]
    if auth_type == "oauth":
        oauth_provider = provider_defaults.get("auth_config", {}).get(
            "provider", provider
        )
        auth_config["provider"] = oauth_provider
        auth_config["user_id"] = user_id
    elif auth_type == "mcp_oauth":
        auth_config["user_id"] = user_id

    mcp_config["auth_config"] = auth_config

    return McpIntegrationForWorkflowResponse(
        success=True, configured=True, mcp_server_config=mcp_config
    )


# ── Admin (system-wide) handlers ────────────────────────────────────────


async def handle_list_system_integrations() -> ListMcpIntegrationsResponse:
    """List all system-wide integration configs."""
    summaries = []
    for provider in OFFICIAL_PROVIDERS:
        service_name = build_mcp_preset_name(provider)
        sys_service = SystemExternalServiceService.get_service(service_name)
        is_configured = sys_service is not None
        is_active = sys_service.is_active if sys_service else False

        settings = {}
        if sys_service and sys_service.settings:
            settings = sys_service.settings
        tool_permissions = settings.get("tool_permissions", {})

        summaries.append(
            McpIntegrationSummary(
                provider=provider,
                display_name=OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider),
                is_configured=is_configured,
                is_active=is_active,
                has_system_default=False,  # This IS the system level
                tool_count=len(tool_permissions) if tool_permissions else None,
                tool_permissions=tool_permissions,
            )
        )

    return ListMcpIntegrationsResponse(success=True, integrations=summaries)


async def handle_save_system_integration(
    provider: str,
    request: SaveMcpIntegrationRequest,
) -> SaveMcpIntegrationResponse:
    """Save or update a system-wide integration config (admin only)."""
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)
    provider_defaults = get_provider_defaults(provider)

    settings: Dict[str, Any] = {"provider": provider}
    if request.settings:
        settings.update(request.settings)

    for key in (
        "connection_type",
        "server_url",
        "command",
        "args",
        "auth_type",
        "timeout_seconds",
        "max_retries",
        "retry_delay",
        "description",
    ):
        if key not in settings and key in provider_defaults:
            settings[key] = provider_defaults[key]

    from backend.models.configuration.system_external_service import (
        ExternalServiceAuthType,
    )

    auth_type_str = settings.get(
        "auth_type", provider_defaults.get("auth_type", "none")
    )
    try:
        auth_type = ExternalServiceAuthType(auth_type_str)
    except ValueError:
        auth_type = ExternalServiceAuthType.API_KEY

    display_name = OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider)

    SystemExternalServiceService.save_service(
        service_name=service_name,
        display_name=display_name,
        description=settings.get("description", ""),
        service_url=settings.get("server_url"),
        auth_type=auth_type,
        credentials=request.credentials,
        settings=settings,
        is_active=request.is_active,
    )

    logger.info("%s Saved system integration '%s'", LOG_PREFIX, provider)

    # Build response
    sys_service = SystemExternalServiceService.get_service(service_name)
    sys_settings = sys_service.settings or {} if sys_service else {}
    tool_permissions = sys_settings.get("tool_permissions", {})

    integration = McpIntegrationConfig(
        provider=provider,
        display_name=display_name,
        is_configured=True,
        is_active=request.is_active,
        has_system_default=False,
        credentials_configured=bool(request.credentials),
        settings=sys_settings,
        tool_permissions=tool_permissions,
    )

    return SaveMcpIntegrationResponse(
        success=True,
        message=f"{display_name} system integration configured successfully",
        integration=integration,
    )


async def handle_delete_system_integration(
    provider: str,
) -> DeleteMcpIntegrationResponse:
    """Delete a system-wide integration config (admin only)."""
    _validate_provider(provider)

    service_name = build_mcp_preset_name(provider)
    deleted = SystemExternalServiceService.delete_service(service_name)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"System integration '{provider}' not configured",
        )

    display = OFFICIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider)
    logger.info("%s Deleted system integration '%s'", LOG_PREFIX, provider)

    return DeleteMcpIntegrationResponse(
        success=True,
        message=f"{display} system configuration removed",
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _validate_provider(provider: str) -> None:
    """Raise 400 if provider is not in the official list."""
    if provider not in OFFICIAL_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Must be one of: {', '.join(OFFICIAL_PROVIDERS)}",
        )


def _set_active_status(user_id: str, service_name: str, active: bool) -> None:
    """Set the is_active flag on a user external service."""
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
            service.is_active = active
            db.commit()
