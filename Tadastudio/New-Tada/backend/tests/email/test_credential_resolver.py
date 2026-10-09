"""Tests for email credential resolver dual-tier fallback logic."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.email.credential_resolver import resolve_email_provider_config


@pytest.fixture
def mock_user_service():
    """Create a mock user external service record."""
    svc = MagicMock()
    svc.is_active = True
    svc.settings = {"provider": "mailgun", "domain": "mg.example.com"}
    return svc


@pytest.fixture
def mock_system_service():
    """Create a mock system external service record."""
    svc = MagicMock()
    svc.is_active = True
    svc.settings = {"provider": "mailgun", "domain": "sys.example.com"}
    return svc


class TestResolveFromUserTier:
    """Test user-tier resolution."""

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_decrypted_api_key"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_mailgun_returns_api_key_and_domain(
        self, mock_get_svc, mock_get_key, mock_user_service
    ):
        mock_get_svc.return_value = mock_user_service
        mock_get_key.return_value = "key-abc123"

        name, kwargs = resolve_email_provider_config("user-1")

        assert name == "mailgun"
        assert kwargs["api_key"] == "key-abc123"
        assert kwargs["domain"] == "mg.example.com"

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_decrypted_api_key"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_mailslurp_returns_api_key(self, mock_get_svc, mock_get_key):
        svc = MagicMock()
        svc.is_active = True
        svc.settings = {"provider": "mailslurp"}
        mock_get_svc.return_value = svc
        mock_get_key.return_value = "ms-key-456"

        name, kwargs = resolve_email_provider_config("user-1")

        assert name == "mailslurp"
        assert kwargs["api_key"] == "ms-key-456"

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_outlook_returns_principal_and_sender(self, mock_get_svc):
        svc = MagicMock()
        svc.is_active = True
        svc.settings = {
            "provider": "outlook",
            "user_principal_name": "user@corp.com",
            "sender_email": "noreply@corp.com",
        }
        mock_get_svc.return_value = svc

        name, kwargs = resolve_email_provider_config("user-1")

        assert name == "outlook"
        assert kwargs["user_principal_name"] == "user@corp.com"
        assert kwargs["sender_email"] == "noreply@corp.com"


class TestResolveFromSystemTier:
    """Test system-tier resolution."""

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_decrypted_credentials"
    )
    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_fallback_when_no_user_config(
        self, mock_user_svc, mock_sys_svc, mock_sys_creds, mock_system_service
    ):
        mock_user_svc.return_value = None
        mock_sys_svc.return_value = mock_system_service
        mock_sys_creds.return_value = {"api_key": "sys-key-789"}

        name, kwargs = resolve_email_provider_config("user-1")

        assert name == "mailgun"
        assert kwargs["api_key"] == "sys-key-789"
        assert kwargs["domain"] == "sys.example.com"

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_decrypted_credentials"
    )
    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    def test_fallback_when_no_user_id(
        self, mock_sys_svc, mock_sys_creds, mock_system_service
    ):
        mock_sys_svc.return_value = mock_system_service
        mock_sys_creds.return_value = {"api_key": "sys-key-789"}

        name, kwargs = resolve_email_provider_config(None)

        assert name == "mailgun"
        assert kwargs["api_key"] == "sys-key-789"

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_decrypted_credentials"
    )
    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_inactive_user_service_falls_through(
        self, mock_user_svc, mock_sys_svc, mock_sys_creds, mock_system_service
    ):
        inactive_user_svc = MagicMock()
        inactive_user_svc.is_active = False
        mock_user_svc.return_value = inactive_user_svc
        mock_sys_svc.return_value = mock_system_service
        mock_sys_creds.return_value = {"api_key": "sys-key-789"}

        name, kwargs = resolve_email_provider_config("user-1")

        assert name == "mailgun"
        assert kwargs["api_key"] == "sys-key-789"


class TestPrecedenceAndEdgeCases:
    """Test tier precedence and edge cases."""

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_decrypted_api_key"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_user_tier_takes_precedence(
        self, mock_user_svc, mock_user_key, mock_sys_svc, mock_user_service
    ):
        mock_user_svc.return_value = mock_user_service
        mock_user_key.return_value = "user-key"

        name, kwargs = resolve_email_provider_config("user-1")

        assert name == "mailgun"
        assert kwargs["api_key"] == "user-key"
        assert kwargs["domain"] == "mg.example.com"
        # System tier should NOT have been called
        mock_sys_svc.assert_not_called()

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_returns_none_when_neither_configured(self, mock_user_svc, mock_sys_svc):
        mock_user_svc.return_value = None
        mock_sys_svc.return_value = None

        name, kwargs = resolve_email_provider_config("user-1")

        assert name is None
        assert kwargs == {}

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_returns_none_when_no_user_and_no_system(self, mock_user_svc, mock_sys_svc):
        mock_sys_svc.return_value = None

        name, kwargs = resolve_email_provider_config(None)

        assert name is None
        assert kwargs == {}
        mock_user_svc.assert_not_called()

    @patch(
        "backend.services.configuration.system_external_service_service.SystemExternalServiceService.get_service"
    )
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_user_service_exception_falls_through(self, mock_user_svc, mock_sys_svc):
        mock_user_svc.side_effect = Exception("DB error")
        mock_sys_svc.return_value = None

        name, kwargs = resolve_email_provider_config("user-1")

        assert name is None
        assert kwargs == {}
