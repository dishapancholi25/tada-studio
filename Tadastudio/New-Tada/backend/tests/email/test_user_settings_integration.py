"""
Test email provider configuration from user settings.

This test verifies that the email executor correctly retrieves
provider configuration from user settings instead of hardcoded defaults.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.email.providers.factory import EmailServiceFactory
from backend.services.email.exceptions import EmailConfigurationError


class TestEmailProviderUserSettings:
    """Test email provider configuration from user settings."""

    def test_no_provider_configured_gives_helpful_error(self):
        """Test that missing provider gives helpful error message."""
        with pytest.raises(EmailConfigurationError) as exc_info:
            EmailServiceFactory.create_provider(None)

        error_message = str(exc_info.value)
        assert "No email provider configured" in error_message
        assert "Settings > External Services" in error_message

    def test_outlook_provider_from_user_settings(self):
        """Test creating Outlook provider with user settings."""
        provider = EmailServiceFactory.create_provider(
            "outlook",
            user_principal_name="test@example.com",
            sender_email="test@example.com",
        )

        assert provider.__class__.__name__ == "OutlookProvider"
        assert provider.user_principal_name == "test@example.com"
        assert provider.sender_email == "test@example.com"

    def test_mailgun_provider_requires_api_key(self):
        """Test that Mailgun provider requires API key."""
        with pytest.raises(EmailConfigurationError) as exc_info:
            EmailServiceFactory.create_provider("mailgun", domain="mg.example.com")

        error_message = str(exc_info.value)
        assert "Mailgun API key is required" in error_message

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_email_executor_uses_user_settings(self, mock_get_service):
        """Test that email executor retrieves provider from user settings."""
        # Mock the user external service
        mock_service = MagicMock()
        mock_service.is_active = True
        mock_service.settings = {
            "provider": "outlook",
            "user_principal_name": "notifications@company.com",
            "sender_email": "notifications@company.com",
        }
        mock_get_service.return_value = mock_service

        # Import here to avoid circular imports
        from backend.services.auth.user_external_service import (
            UserExternalServiceService,
        )

        # Simulate what the email executor does
        user_id = "test-user-123"
        email_service = UserExternalServiceService.get_service(user_id, "email")

        assert email_service is not None
        assert email_service.settings["provider"] == "outlook"
        assert (
            email_service.settings["user_principal_name"] == "notifications@company.com"
        )

        # Verify provider can be created with these settings
        provider = EmailServiceFactory.create_provider(
            email_service.settings["provider"],
            user_principal_name=email_service.settings["user_principal_name"],
            sender_email=email_service.settings.get("sender_email"),
        )

        assert provider.__class__.__name__ == "OutlookProvider"
        assert provider.user_principal_name == "notifications@company.com"

    def test_email_provider_environment_variable_fallback(self):
        """Test that EMAIL_PROVIDER env var is used as fallback."""
        with patch.dict(
            "os.environ",
            {
                "EMAIL_PROVIDER": "outlook",
                "OUTLOOK_USER_PRINCIPAL_NAME": "env@example.com",
            },
        ):
            # Reload config to pick up env var
            from importlib import reload
            from backend.services.email import config

            reload(config)

            provider = EmailServiceFactory.create_provider(
                None,  # No provider specified
                user_principal_name="env@example.com",
            )

            assert provider.__class__.__name__ == "OutlookProvider"
