"""Configuration API endpoints for managing environment settings."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from .api.auth.dependencies import require_active_user, require_admin
from .config_service import ConfigurationService, get_config_service
from .services.auth.rbac import _redact_email


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["configuration"])

_OBS_LANGFUSE_ENABLED_KEY = "external_services.langfuse.enabled"
_OBS_PHOENIX_ENABLED_KEY = "external_services.phoenix.enabled"


def _has_observability_updates(updates: Dict[str, Any]) -> bool:
    """Return True when this update payload touches observability toggles."""
    return (
        _OBS_LANGFUSE_ENABLED_KEY in updates
        or _OBS_PHOENIX_ENABLED_KEY in updates
    )


def _parse_bool(value: Any, default: bool) -> bool:
    """Parse an update payload boolean value with a fallback default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _resolve_observability_request(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve requested observability states and enforce mutual exclusion."""
    from .services.langfuse.config import get_langfuse_config
    from .services.phoenix.config import get_phoenix_config

    current_langfuse = bool(get_langfuse_config().is_configured)
    current_phoenix = bool(get_phoenix_config().enabled)

    langfuse_changed = _OBS_LANGFUSE_ENABLED_KEY in updates
    phoenix_changed = _OBS_PHOENIX_ENABLED_KEY in updates

    requested_langfuse = _parse_bool(
        updates.get(_OBS_LANGFUSE_ENABLED_KEY), current_langfuse
    )
    requested_phoenix = _parse_bool(
        updates.get(_OBS_PHOENIX_ENABLED_KEY), current_phoenix
    )

    if requested_langfuse and requested_phoenix:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot enable both Langfuse and Phoenix at the same time. "
                "Disable one first."
            ),
        )

    return {
        "observability_update": langfuse_changed or phoenix_changed,
        "langfuse_changed": langfuse_changed,
        "phoenix_changed": phoenix_changed,
        "langfuse_enabled": requested_langfuse,
        "phoenix_enabled": requested_phoenix,
    }


def _reconcile_observability_runtime(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply runtime stop/start actions after observability config is persisted."""
    actions = []
    errors = []

    # Disable-first sequencing prevents short windows where both could export.
    if state["langfuse_changed"] and not state["langfuse_enabled"]:
        try:
            from .services.langfuse.instrumentation import (
                set_langfuse_export_enabled,
            )

            set_langfuse_export_enabled(False)
            actions.append("langfuse_export_disabled")
        except Exception as exc:
            errors.append(f"langfuse_export_disable_failed: {exc}")

    if state["phoenix_changed"] and not state["phoenix_enabled"]:
        actions.append("phoenix_export_disabled")

    if (
        state["langfuse_changed"]
        and state["langfuse_enabled"]
        and not state["phoenix_enabled"]
    ):
        try:
            from .services.langfuse.instrumentation import (
                initialize_langfuse_instrumentation,
            )
            

            initialize_langfuse_instrumentation()
            actions.append("langfuse_initialized")
        except Exception as exc:
            errors.append(f"langfuse_init_failed: {exc}")
    elif (
        state["phoenix_changed"]
        and state["phoenix_enabled"]
        and not state["langfuse_enabled"]
    ):
        try:
            from .services.phoenix.instrumentation import (
                initialize_phoenix_instrumentation,
            )


            _initialized=False

            initialize_phoenix_instrumentation()
            actions.append("phoenix_initialized")
        except Exception as exc:
            errors.append(f"phoenix_init_failed: {exc}")

    return {"actions": actions, "errors": errors}


async def _build_runtime_config() -> Dict[str, Any]:
    """Build runtime configuration for frontend clients."""
    from .services.scheduling import is_scheduling_enabled

    api_url = os.getenv("RUNTIME_API_URL", "")

    return {
        "apiUrl": api_url,
        "deployment": "separate-domains" if api_url else "reverse-proxy",
        "schedulingEnabled": is_scheduling_enabled(),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/")
async def get_runtime_config() -> Dict[str, Any]:
    """
    Provide lightweight runtime configuration for frontend clients.

    This endpoint is intentionally public so nginx can serve it through /api/config.
    """
    return await _build_runtime_config()


@router.get("", include_in_schema=False)
async def get_runtime_config_without_trailing_slash() -> Dict[str, Any]:
    """Allow access via /api/config without enforcing a trailing slash."""
    return await _build_runtime_config()


@router.get("/environment", dependencies=[Depends(require_admin)])
async def get_environment_config(
    sanitize: bool = True,
    config_service: ConfigurationService = Depends(get_config_service),
) -> Dict[str, Any]:
    """
    Get current environment configuration.

    Args:
        sanitize: If True, sensitive values will be masked

    Returns:
        Environment configuration
    """
    try:
        config = config_service.get_environment_config(sanitize=sanitize)
        return {
            "success": True,
            "data": config,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get environment config: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get environment config. Check server logs for details.",
        )


@router.put("/environment")
async def update_environment_config(
    updates: Dict[str, Any] = Body(...),
    config_service: ConfigurationService = Depends(get_config_service),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Update environment configuration.

    Args:
        updates: Dictionary with section.key: value pairs

    Returns:
        Update result
    """
    try:
        observability_state = {
            "observability_update": False,
            "langfuse_changed": False,
            "phoenix_changed": False,
            "langfuse_enabled": False,
            "phoenix_enabled": False,
        }
        if _has_observability_updates(updates):
            observability_state = _resolve_observability_request(updates)

        results = {}
        for key_path, value in updates.items():
            parts = key_path.split(".")
            if len(parts) >= 2:
                section = ".".join(parts[:-1])
                key = parts[-1]
                success = config_service.update_configuration(section, key, value)
                results[key_path] = success

        runtime_result = {"actions": [], "errors": []}
        if observability_state["observability_update"]:
            runtime_result = _reconcile_observability_runtime(observability_state)

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        updated_keys = ", ".join(results.keys())
        logger.info(
            f"[AUDIT] Environment configuration updated by {_redact_email(user_email)}: {updated_keys}"
        )

        return {
            "success": all(results.values()) and not runtime_result["errors"],
            "updates": results,
            "observability_runtime": (
                runtime_result if observability_state["observability_update"] else None
            ),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to update environment config: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update environment config. Check server logs for details.",
        )


@router.post("/test-connection", dependencies=[Depends(require_admin)])
async def test_connection(
    service_type: str = Body(..., embed=True),
    provider: Optional[str] = Body(None, embed=True),
    config_service: ConfigurationService = Depends(get_config_service),
) -> Dict[str, Any]:
    """
    Test connection to a service.

    Args:
        service_type: Type of service (llm, database, external)
        provider: Provider name for LLM services

    Returns:
        Connection test result
    """
    try:
        if service_type == "llm" and provider:
            result = config_service.test_llm_connection(provider)
        elif service_type == "database":
            result = config_service.test_database_connection()
        else:
            raise ValueError(f"Unknown service type: {service_type}")

        return {
            "success": result.get("success", False),
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to test connection: {e}")
        return {
            "success": False,
            "error": "Connection test failed. Check server logs for details.",
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/env-file", dependencies=[Depends(require_admin)])
async def get_env_file(
    config_service: ConfigurationService = Depends(get_config_service),
) -> Dict[str, Any]:
    """
    Get the content of the .env file.

    Returns:
        .env file content
    """
    try:
        content = config_service.get_env_file_content()
        return {
            "success": True,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get .env file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get .env file. Check server logs for details.",
        )


@router.get("/export")
async def export_configuration(
    config_service: ConfigurationService = Depends(get_config_service),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Export configuration for backup.

    Returns:
        Exportable configuration
    """
    try:
        config = config_service.export_configuration()

        # Save to file
        export_dir = Path("workspace/config_backups")
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"config_backup_{timestamp}.json"

        with open(export_file, "w") as f:
            json.dump(config, f, indent=2)

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] Configuration exported by {_redact_email(user_email)}: {export_file}"
        )

        return {
            "success": True,
            "data": config,
            "backup_file": str(export_file),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export configuration. Check server logs for details.",
        )


@router.post("/import")
async def import_configuration(
    config_data: Dict[str, Any] = Body(...),
    config_service: ConfigurationService = Depends(get_config_service),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Import configuration from backup.

    Args:
        config_data: Configuration data to import

    Returns:
        Import result
    """
    try:
        result = config_service.import_configuration(config_data)

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        num_sections = len(config_data.keys())
        logger.info(
            f"[AUDIT] Configuration imported by {_redact_email(user_email)}: {num_sections} sections"
        )

        return {
            "success": result.get("success", False),
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to import configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to import configuration. Check server logs for details.",
        )


@router.get("/services/status", dependencies=[Depends(require_active_user)])
async def get_services_status(
    config_service: ConfigurationService = Depends(get_config_service),
) -> Dict[str, Any]:
    """
    Get status of all configured services.

    Returns:
        Service status information
    """
    try:
        status = config_service.get_service_status()
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get services status. Check server logs for details.",
        )


@router.get("/available-models/{provider}", dependencies=[Depends(require_active_user)])
async def get_available_models(
    provider: str, config_service: ConfigurationService = Depends(get_config_service)
) -> Dict[str, Any]:
    """
    Get available models for a provider.

    Args:
        provider: Provider name

    Returns:
        List of available models
    """
    try:
        from .services.llm_models import LLMFactory

        factory = LLMFactory()
        models = factory.get_available_models(provider)

        return {
            "success": True,
            "provider": provider,
            "models": models.get(provider, []),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get available models. Check server logs for details.",
        )


@router.post("/generate-encryption-key")
async def generate_encryption_key(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Generate a new encryption key for credentials.

    Returns:
        New encryption key
    """
    try:
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        logger.info(f"[AUDIT] Encryption key generated by {_redact_email(user_email)}")

        return {
            "success": True,
            "key": key,
            "message": "Save this key in your .env file as CREDENTIAL_ENCRYPTION_KEY",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to generate encryption key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate encryption key. Check server logs for details.",
        )


@router.get("/system-info", dependencies=[Depends(require_active_user)])
async def get_system_info() -> Dict[str, Any]:
    """
    Get system information and diagnostics.

    Returns:
        System information
    """
    try:
        from .api.monitoring.services import get_system_info as get_sys_info

        info = get_sys_info()
        return {"success": True, "data": info, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get system info. Check server logs for details.",
        )


@router.get("/phoenix/project-url", dependencies=[Depends(require_active_user)])
async def get_phoenix_project_url(project_name: str) -> Dict[str, Any]:
    """Resolve a Phoenix project name to its UI URL (uses project ID).

    Phoenix UI routes use internal project IDs, not names. This endpoint
    queries the Phoenix API to resolve the name and returns the correct URL.
    """
    try:
        from .services.phoenix.config import build_project_url, get_phoenix_config

        config = get_phoenix_config()
        if not config.enabled:
            return {"success": True, "url": None, "reason": "phoenix_disabled"}

        url = build_project_url(project_name, config)
        return {"success": True, "url": url}
    except Exception as e:
        logger.warning(f"Failed to resolve Phoenix project URL: {e}")
        return {"success": True, "url": None, "reason": "resolution_failed"}
