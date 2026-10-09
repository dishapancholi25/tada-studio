"""Credential resolution service for three-tier external service fallback.

Implements the personal -> group -> system resolution order:
  1. Check user-tier (personal) credentials first.
  2. Fall back to group-tier (admin-managed, group-scoped) credentials.
  3. Fall back to system-tier (org-wide, admin-managed) credentials.
  4. Return None if no tier has the service configured.
"""

from typing import Dict, Optional

from ..auth.user_external_service import UserExternalServiceService
from ..config import get_logger
from .group_external_service_service import GroupExternalServiceService
from .system_external_service_service import SystemExternalServiceService

logger = get_logger(__name__)
LOG_PREFIX = "[CRED-RESOLUTION]"


class CredentialResolutionService:
    """Resolve external-service credentials using the three-tier fallback chain.

    Resolution order: personal -> group -> system.
    All methods are static; no instance state required.
    """

    @staticmethod
    def resolve_api_key(service_name: str, user_id: Optional[str]) -> Optional[str]:
        """Resolve a single API key for *service_name*.

        Args:
            service_name: Stable machine identifier (e.g. ``tavily``).
            user_id: Authenticated user identifier, or ``None`` for anonymous access.

        Returns:
            Plaintext API key string, or ``None`` if no tier is configured.
        """
        # 1. User tier
        if user_id:
            key = UserExternalServiceService.get_decrypted_api_key(
                user_id, service_name
            )
            if key:
                logger.debug(
                    "%s Resolved '%s' api_key from user tier for user '%s'",
                    LOG_PREFIX,
                    service_name,
                    user_id,
                )
                return key

        # 2. Group tier
        if user_id:
            group_config = GroupExternalServiceService.get_config_for_user_service(
                user_id, service_name
            )
            if group_config:
                key = GroupExternalServiceService.get_decrypted_api_key(group_config)
                if key:
                    logger.debug(
                        "%s Resolved '%s' api_key from group tier for user '%s'",
                        LOG_PREFIX,
                        service_name,
                        user_id,
                    )
                    return key

        # 3. System tier
        sys_creds = SystemExternalServiceService.get_decrypted_credentials(service_name)
        if sys_creds:
            api_key = sys_creds.get("api_key")
            if api_key:
                logger.debug(
                    "%s Resolved '%s' api_key from system tier",
                    LOG_PREFIX,
                    service_name,
                )
                return api_key

        return None

    @staticmethod
    def resolve_credentials(
        service_name: str, user_id: Optional[str]
    ) -> Optional[Dict[str, str]]:
        """Resolve the full credentials dict for *service_name*.

        Args:
            service_name: Stable machine identifier.
            user_id: Authenticated user identifier, or ``None``.

        Returns:
            Decrypted credentials dict, or ``None`` if no tier is configured.
        """
        # 1. User tier
        if user_id:
            creds = UserExternalServiceService.get_decrypted_credentials(
                user_id, service_name
            )
            if creds:
                logger.debug(
                    "%s Resolved '%s' credentials from user tier for user '%s'",
                    LOG_PREFIX,
                    service_name,
                    user_id,
                )
                return creds

        # 2. Group tier
        if user_id:
            group_config = GroupExternalServiceService.get_config_for_user_service(
                user_id, service_name
            )
            if group_config:
                group_creds = GroupExternalServiceService.get_decrypted_credentials(
                    group_config
                )
                if group_creds:
                    logger.debug(
                        "%s Resolved '%s' credentials from group tier for user '%s'",
                        LOG_PREFIX,
                        service_name,
                        user_id,
                    )
                    return group_creds
                api_key = GroupExternalServiceService.get_decrypted_api_key(
                    group_config
                )
                if api_key:
                    logger.debug(
                        "%s Resolved '%s' api_key (as creds) from group tier for user '%s'",
                        LOG_PREFIX,
                        service_name,
                        user_id,
                    )
                    return {"api_key": api_key}

        # 3. System tier
        sys_creds = SystemExternalServiceService.get_decrypted_credentials(service_name)
        if sys_creds is not None:
            logger.debug(
                "%s Resolved '%s' credentials from system tier",
                LOG_PREFIX,
                service_name,
            )
            return sys_creds

        return None

    @staticmethod
    def system_default_configured(service_name: str) -> bool:
        """Return True if a system-tier entry exists and is active for *service_name*."""
        svc = SystemExternalServiceService.get_service(service_name)
        return svc is not None and svc.is_active

    @staticmethod
    def group_default_configured(service_name: str, user_id: str) -> bool:
        """Return True if a group-tier config exists for the user and service."""
        config = GroupExternalServiceService.get_config_for_user_service(
            user_id, service_name
        )
        return config is not None
