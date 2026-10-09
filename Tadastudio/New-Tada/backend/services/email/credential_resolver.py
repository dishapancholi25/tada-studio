"""Resolve email provider configuration from user-tier or system-tier settings.

Follows the dual-tier fallback pattern:
  1. Try user-tier (personal) email settings first.
  2. Fall back to system-tier (org-wide, admin-managed) email settings.
  3. Return (None, {}) if neither tier is configured — the factory will
     then fall back to environment variables.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)
LOG_PREFIX = "[EMAIL-CRED-RESOLVE]"


def resolve_email_provider_config(
    user_id: Optional[str] = None,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Resolve email provider name and kwargs from user or system settings.

    Args:
        user_id: Authenticated user identifier, or None.

    Returns:
        Tuple of (provider_name, provider_kwargs). Both may be None/empty
        if neither tier is configured.
    """
    if user_id:
        result = _resolve_from_user_tier(user_id)
        if result[0] is not None:
            return result

    return _resolve_from_system_tier()


def _resolve_from_user_tier(user_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Resolve email config from user-tier external service settings."""
    from backend.services.auth.user_external_service import UserExternalServiceService

    try:
        email_service = UserExternalServiceService.get_service(user_id, "email")
        if (
            not email_service
            or not email_service.is_active
            or not email_service.settings
        ):
            return (None, {})

        provider_name = email_service.settings.get("provider")
        if not provider_name:
            return (None, {})

        provider_kwargs: Dict[str, Any] = {}

        if provider_name == "outlook":
            provider_kwargs["user_principal_name"] = email_service.settings.get(
                "user_principal_name"
            )
            provider_kwargs["sender_email"] = email_service.settings.get("sender_email")
        elif provider_name == "mailgun":
            provider_kwargs["domain"] = email_service.settings.get("domain")
            decrypted_key = UserExternalServiceService.get_decrypted_api_key(
                user_id, "email"
            )
            if decrypted_key:
                provider_kwargs["api_key"] = decrypted_key
        elif provider_name == "mailslurp":
            decrypted_key = UserExternalServiceService.get_decrypted_api_key(
                user_id, "email"
            )
            if decrypted_key:
                provider_kwargs["api_key"] = decrypted_key

        logger.info(
            "%s Resolved provider '%s' from user tier (user=%s)",
            LOG_PREFIX,
            provider_name,
            user_id,
        )
        return (provider_name, provider_kwargs)

    except Exception as e:
        logger.warning("%s Failed to resolve from user tier: %s", LOG_PREFIX, e)
        return (None, {})


def _resolve_from_system_tier() -> Tuple[Optional[str], Dict[str, Any]]:
    """Resolve email config from system-tier external service settings."""
    from backend.services.configuration.system_external_service_service import (
        SystemExternalServiceService,
    )

    try:
        sys_service = SystemExternalServiceService.get_service("email")
        if not sys_service or not sys_service.is_active or not sys_service.settings:
            return (None, {})

        provider_name = sys_service.settings.get("provider")
        if not provider_name:
            return (None, {})

        provider_kwargs: Dict[str, Any] = {}
        decrypted_creds = (
            SystemExternalServiceService.get_decrypted_credentials("email") or {}
        )

        if provider_name == "outlook":
            provider_kwargs["user_principal_name"] = sys_service.settings.get(
                "user_principal_name"
            )
            provider_kwargs["sender_email"] = sys_service.settings.get("sender_email")
            if decrypted_creds.get("client_secret"):
                provider_kwargs["client_secret"] = decrypted_creds["client_secret"]
            if sys_service.settings.get("tenant_id"):
                provider_kwargs["tenant_id"] = sys_service.settings["tenant_id"]
            if sys_service.settings.get("client_id"):
                provider_kwargs["client_id"] = sys_service.settings["client_id"]
        elif provider_name == "mailgun":
            provider_kwargs["domain"] = sys_service.settings.get("domain")
            if decrypted_creds.get("api_key"):
                provider_kwargs["api_key"] = decrypted_creds["api_key"]
        elif provider_name == "mailslurp":
            if decrypted_creds.get("api_key"):
                provider_kwargs["api_key"] = decrypted_creds["api_key"]

        logger.info(
            "%s Resolved provider '%s' from system tier", LOG_PREFIX, provider_name
        )
        return (provider_name, provider_kwargs)

    except Exception as e:
        logger.warning("%s Failed to resolve from system tier: %s", LOG_PREFIX, e)
        return (None, {})
