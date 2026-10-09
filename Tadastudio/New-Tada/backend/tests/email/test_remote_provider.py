"""
Unit tests for RemoteProvider with mocked HTTP calls.

Tests cover:
- Configuration validation
- Successful email relay
- API key header transmission
- Error handling (auth rejection, server errors, connection errors)
- Factory integration
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from backend.services.email.exceptions import (
    EmailConfigurationError,
    EmailSendError,
)
from backend.services.email.providers.remote import RemoteProvider
from backend.services.email.providers.factory import EmailServiceFactory


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Test RemoteProvider configuration and initialization."""

    def test_init_with_valid_config(self):
        """Test successful initialization with valid configuration."""
        provider = RemoteProvider(
            remote_url="https://remote.example.com",
            api_key="test-key-123",
        )

        assert provider.remote_url == "https://remote.example.com"
        assert provider.api_key == "test-key-123"
        assert provider.relay_endpoint == "https://remote.example.com/api/email/relay"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from remote_url."""
        provider = RemoteProvider(
            remote_url="https://remote.example.com/",
            api_key="test-key",
        )

        assert provider.remote_url == "https://remote.example.com"
        assert provider.relay_endpoint == "https://remote.example.com/api/email/relay"

    def test_init_without_remote_url(self):
        """Test initialization fails without remote_url."""
        with pytest.raises(EmailConfigurationError) as exc_info:
            RemoteProvider(remote_url=None, api_key="test-key")

        assert "remote_url is required" in str(exc_info.value)

    def test_init_without_api_key(self):
        """Test initialization fails without api_key."""
        with pytest.raises(EmailConfigurationError) as exc_info:
            RemoteProvider(remote_url="https://remote.example.com", api_key=None)

        assert "api_key is required" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Send Email Tests
# ---------------------------------------------------------------------------


class TestSendEmail:
    """Test send_email relay functionality."""

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful email relay."""
        provider = RemoteProvider(
            remote_url="https://remote.example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "status": "sent",
                "provider": "outlook",
                "to": "recipient@example.com",
                "from": "sender@example.com",
                "subject": "Test",
            },
        }

        with patch("backend.services.email.providers.remote.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await provider.send_email(
                from_address="sender@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

            assert result["status"] == "sent"
            assert result["provider"] == "outlook"

            # Verify the POST was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args.args[0] == "https://remote.example.com/api/email/relay"
            assert call_args.kwargs["headers"]["X-Email-API-Key"] == "test-key"
            assert call_args.kwargs["json"]["recipient"] == "recipient@example.com"
            assert call_args.kwargs["json"]["subject"] == "Test"

    @pytest.mark.asyncio
    async def test_send_email_includes_optional_fields(self):
        """Test that html_body and reply_to are included when provided."""
        provider = RemoteProvider(
            remote_url="https://remote.example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "result": {"status": "sent"}}

        with patch("backend.services.email.providers.remote.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await provider.send_email(
                from_address="sender@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Plain text",
                html_body="<p>HTML</p>",
                reply_to="reply@example.com",
            )

            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["html_body"] == "<p>HTML</p>"
            assert payload["reply_to"] == "reply@example.com"

    @pytest.mark.asyncio
    async def test_send_email_403_rejected(self):
        """Test error when remote rejects the API key."""
        provider = RemoteProvider(
            remote_url="https://remote.example.com",
            api_key="bad-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("backend.services.email.providers.remote.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            with pytest.raises(EmailSendError) as exc_info:
                await provider.send_email(
                    from_address="sender@example.com",
                    to_address="recipient@example.com",
                    subject="Test",
                    body="Test body",
                )

            assert "rejected the API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_server_error(self):
        """Test error handling for non-200 responses."""
        provider = RemoteProvider(
            remote_url="https://remote.example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("backend.services.email.providers.remote.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            with pytest.raises(EmailSendError) as exc_info:
                await provider.send_email(
                    from_address="sender@example.com",
                    to_address="recipient@example.com",
                    subject="Test",
                    body="Test body",
                )

            assert "status 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_connection_error(self):
        """Test error handling for connection failures."""
        import httpx

        provider = RemoteProvider(
            remote_url="https://unreachable.example.com",
            api_key="test-key",
        )

        with patch("backend.services.email.providers.remote.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            with pytest.raises(EmailSendError) as exc_info:
                await provider.send_email(
                    from_address="sender@example.com",
                    to_address="recipient@example.com",
                    subject="Test",
                    body="Test body",
                )

            assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_timeout(self):
        """Test error handling for timeout."""
        import httpx

        provider = RemoteProvider(
            remote_url="https://slow.example.com",
            api_key="test-key",
        )

        with patch("backend.services.email.providers.remote.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ReadTimeout("Timed out")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            with pytest.raises(EmailSendError) as exc_info:
                await provider.send_email(
                    from_address="sender@example.com",
                    to_address="recipient@example.com",
                    subject="Test",
                    body="Test body",
                )

            assert "Timeout" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Factory Integration Tests
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    """Test RemoteProvider integration with EmailServiceFactory."""

    def test_create_remote_provider_from_factory(self):
        """Test creating RemoteProvider via factory."""
        provider = EmailServiceFactory.create_provider(
            provider_name="remote",
            remote_url="https://remote.example.com",
            api_key="test-key",
        )

        assert isinstance(provider, RemoteProvider)
        assert provider.remote_url == "https://remote.example.com"
        assert provider.api_key == "test-key"

    def test_factory_remote_without_url(self):
        """Test factory fails when creating remote without URL."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EmailConfigurationError):
                EmailServiceFactory.create_provider(
                    provider_name="remote",
                    remote_url=None,
                    api_key="test-key",
                )

    def test_factory_remote_with_config_values(self):
        """Test factory uses config values when kwargs not provided."""
        with patch("backend.services.email.providers.factory.REMOTE_EMAIL_URL", "https://config.example.com"):
            with patch("backend.services.email.providers.factory.REMOTE_EMAIL_API_KEY", "config-key"):
                provider = EmailServiceFactory.create_provider(
                    provider_name="remote"
                )

                assert isinstance(provider, RemoteProvider)
                assert provider.remote_url == "https://config.example.com"
                assert provider.api_key == "config-key"


# ---------------------------------------------------------------------------
# Not Implemented Methods Tests
# ---------------------------------------------------------------------------


class TestNotImplementedMethods:
    """Test that unsupported methods raise appropriate exceptions."""

    @pytest.fixture
    def remote_provider(self):
        return RemoteProvider(
            remote_url="https://remote.example.com",
            api_key="test-key",
        )

    @pytest.mark.asyncio
    async def test_create_inbox_not_supported(self, remote_provider):
        from backend.services.email.exceptions import InboxCreationError

        with pytest.raises(InboxCreationError):
            await remote_provider.create_inbox()

    @pytest.mark.asyncio
    async def test_delete_inbox_not_supported(self, remote_provider):
        from backend.services.email.exceptions import InboxDeletionError

        with pytest.raises(InboxDeletionError):
            await remote_provider.delete_inbox("test-id")

    @pytest.mark.asyncio
    async def test_register_webhook_not_supported(self, remote_provider):
        from backend.services.email.exceptions import WebhookRegistrationError

        with pytest.raises(WebhookRegistrationError):
            await remote_provider.register_webhook("inbox-id", "https://example.com/webhook")

    @pytest.mark.asyncio
    async def test_get_emails_not_supported(self, remote_provider):
        from backend.services.email.exceptions import EmailRetrievalError

        with pytest.raises(EmailRetrievalError):
            await remote_provider.get_emails("inbox-id")

    def test_validate_webhook_signature_returns_false(self, remote_provider):
        result = remote_provider.validate_webhook_signature(
            payload=b"test", signature="sig"
        )
        assert result is False
