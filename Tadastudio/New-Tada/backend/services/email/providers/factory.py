"""
Factory for creating email service providers.

Provides dynamic provider creation and registration.
"""

import logging
import os
from typing import Dict, Type

from ..config import (
    DEFAULT_EMAIL_PROVIDER,
    LOG_PREFIX_PROVIDER,
    OUTLOOK_CLIENT_ID,
    OUTLOOK_CLIENT_SECRET,
    OUTLOOK_SENDER_EMAIL,
    OUTLOOK_TENANT_ID,
    OUTLOOK_USER_PRINCIPAL_NAME,
    REMOTE_EMAIL_API_KEY,
    REMOTE_EMAIL_URL,
    SUPPORTED_PROVIDERS,
)
from ..exceptions import EmailConfigurationError
from .base import EmailServiceProvider
from .mailgun import MailgunProvider
from .mailslurp import MailSlurpProvider
from .outlook import OutlookProvider
from .remote import RemoteProvider


logger = logging.getLogger(__name__)


class EmailServiceFactory:
    """Factory for creating email service provider instances."""

    _providers: Dict[str, Type[EmailServiceProvider]] = {
        "mailgun": MailgunProvider,
        "mailslurp": MailSlurpProvider,
        "outlook": OutlookProvider,
        "remote": RemoteProvider,
    }

    @classmethod
    def create_provider(
        cls, provider_name: str = None, **kwargs
    ) -> EmailServiceProvider:
        """
        Create an email service provider instance.

        Args:
            provider_name: Provider name (mailgun, mailslurp, outlook) or None for default
            **kwargs: Additional provider-specific configuration parameters

        Returns:
            EmailServiceProvider instance

        Raises:
            EmailConfigurationError: If provider is unknown or unavailable
        """
        provider_name = provider_name or os.getenv(
            "EMAIL_PROVIDER", DEFAULT_EMAIL_PROVIDER
        )

        if not provider_name:
            raise EmailConfigurationError(
                "No email provider configured. Please configure an email provider "
                "in Settings > External Services or set the EMAIL_PROVIDER environment variable."
            )

        if provider_name not in SUPPORTED_PROVIDERS:
            raise EmailConfigurationError(
                f"Unknown email provider: {provider_name}. "
                f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
            )

        if provider_name not in cls._providers:
            raise EmailConfigurationError(
                f"Provider '{provider_name}' is not registered"
            )

        provider_class = cls._providers[provider_name]

        try:
            # Handle provider-specific initialization
            if provider_name == "outlook":
                # Outlook requires user_principal_name
                user_principal_name = (
                    kwargs.get("user_principal_name") or OUTLOOK_USER_PRINCIPAL_NAME
                )
                sender_email = kwargs.get("sender_email") or OUTLOOK_SENDER_EMAIL
                tenant_id = kwargs.get("tenant_id") or OUTLOOK_TENANT_ID
                client_id = kwargs.get("client_id") or OUTLOOK_CLIENT_ID
                client_secret = kwargs.get("client_secret") or OUTLOOK_CLIENT_SECRET
                provider = provider_class(
                    user_principal_name=user_principal_name,
                    sender_email=sender_email,
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            elif provider_name == "remote":
                remote_url = kwargs.get("remote_url") or REMOTE_EMAIL_URL
                api_key = kwargs.get("api_key") or REMOTE_EMAIL_API_KEY
                provider = provider_class(
                    remote_url=remote_url,
                    api_key=api_key,
                )
            else:
                # Other providers accept kwargs
                provider = provider_class(**kwargs)

            logger.info(f"{LOG_PREFIX_PROVIDER} Created provider: {provider_name}")
            return provider
        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_PROVIDER} Failed to create provider '{provider_name}': {e}"
            )
            raise EmailConfigurationError(
                f"Failed to create provider '{provider_name}': {e}"
            ) from e

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[EmailServiceProvider]):
        """
        Register a new email service provider.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from EmailServiceProvider)

        Raises:
            EmailConfigurationError: If provider doesn't inherit from base class
        """
        if not issubclass(provider_class, EmailServiceProvider):
            raise EmailConfigurationError(
                "Provider must inherit from EmailServiceProvider"
            )

        cls._providers[name] = provider_class
        logger.info(f"{LOG_PREFIX_PROVIDER} Registered provider: {name}")

    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available provider names."""
        return list(cls._providers.keys())
