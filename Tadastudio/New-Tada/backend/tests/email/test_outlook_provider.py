"""
Unit tests for OutlookProvider with mocked GraphServiceClient.

Tests cover:
- Input validation (fail-fast scenarios)
- from_address validation against configured senders
- Retry logic with exponential backoff
- Error handling and exception mapping
- Factory integration
- Configuration validation
"""

import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from azure.core.exceptions import HttpResponseError

from backend.services.email.exceptions import (
    EmailConfigurationError,
    EmailSendError,
)
from backend.services.email.providers.outlook import OutlookProvider
from backend.services.email.providers.factory import EmailServiceFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def create_http_error(status_code: int, reason: str) -> HttpResponseError:
    """
    Helper to create HttpResponseError with proper status_code.

    Args:
        status_code: HTTP status code (e.g., 429, 500, 401)
        reason: HTTP reason phrase (e.g., "Too Many Requests")

    Returns:
        HttpResponseError with the specified status_code
    """

    # Create a simple mock response object
    class MockResponse:
        def __init__(self, status_code, reason):
            self.status_code = status_code
            self.reason = reason

    mock_response = MockResponse(status_code, reason)
    return HttpResponseError(response=mock_response)


@pytest.fixture(autouse=True)
def fast_retries():
    """Make retry logic instant for tests by mocking asyncio.sleep."""

    # Patch asyncio.sleep to return immediately instead of actually waiting
    # This makes retry delays instant (0s instead of 2s, 4s, 8s)
    async def instant_sleep(delay):
        """Mock sleep that returns immediately."""
        pass

    with patch("asyncio.sleep", new=instant_sleep):
        yield


@pytest.fixture
def mock_graph_client():
    """Create a mocked GraphServiceClient."""
    mock_client = MagicMock()

    # Mock the send_mail chain
    mock_send_mail = AsyncMock()
    mock_client.users.by_user_id.return_value.send_mail.post = mock_send_mail

    return mock_client


@pytest.fixture
def outlook_provider(mock_graph_client):
    """Create an OutlookProvider instance with mocked dependencies."""
    with patch("backend.services.email.providers.outlook.DefaultAzureCredential"):
        with patch(
            "backend.services.email.providers.outlook.GraphServiceClient"
        ) as mock_gsc:
            mock_gsc.return_value = mock_graph_client

            provider = OutlookProvider(
                user_principal_name="test@example.com", sender_email="test@example.com"
            )
            provider.client = mock_graph_client

            yield provider


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Test OutlookProvider configuration and initialization."""

    def test_init_with_valid_config(self, mock_graph_client):
        """Test successful initialization with valid configuration."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential"):
            with patch(
                "backend.services.email.providers.outlook.GraphServiceClient"
            ) as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                provider = OutlookProvider(
                    user_principal_name="test@example.com",
                    sender_email="sender@example.com",
                )

                assert provider.user_principal_name == "test@example.com"
                assert provider.sender_email == "sender@example.com"

    def test_init_without_user_principal_name(self):
        """Test initialization fails without user_principal_name."""
        with pytest.raises(EmailConfigurationError) as exc_info:
            OutlookProvider(user_principal_name=None)

        assert "user_principal_name is required" in str(exc_info.value)

    def test_init_with_user_principal_name_only(self, mock_graph_client):
        """Test sender_email defaults to user_principal_name."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential"):
            with patch(
                "backend.services.email.providers.outlook.GraphServiceClient"
            ) as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                provider = OutlookProvider(user_principal_name="test@example.com")

                assert provider.sender_email == "test@example.com"

    def test_init_with_client_credentials(self, mock_graph_client):
        """Test initialization uses ClientSecretCredential when all cross-tenant params provided."""
        with patch("backend.services.email.providers.outlook.ClientSecretCredential") as mock_csc:
            with patch("backend.services.email.providers.outlook.GraphServiceClient") as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                provider = OutlookProvider(
                    user_principal_name="test@example.com",
                    tenant_id="tenant-123",
                    client_id="client-456",
                    client_secret="secret-789",
                )

                mock_csc.assert_called_once_with(
                    tenant_id="tenant-123",
                    client_id="client-456",
                    client_secret="secret-789",
                )
                assert provider.credential == mock_csc.return_value

    def test_init_falls_back_to_default_credential(self, mock_graph_client):
        """Test initialization uses DefaultAzureCredential when cross-tenant params not provided."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential") as mock_dac:
            with patch("backend.services.email.providers.outlook.GraphServiceClient") as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                provider = OutlookProvider(user_principal_name="test@example.com")

                mock_dac.assert_called_once()
                assert provider.credential == mock_dac.return_value

    def test_init_partial_client_credentials_falls_back(self, mock_graph_client):
        """Test DefaultAzureCredential is used when only some cross-tenant params are set."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential") as mock_dac:
            with patch("backend.services.email.providers.outlook.GraphServiceClient") as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                # Only tenant_id set, missing client_id and client_secret
                provider = OutlookProvider(
                    user_principal_name="test@example.com",
                    tenant_id="tenant-123",
                )

                mock_dac.assert_called_once()
                assert provider.credential == mock_dac.return_value

    def test_init_graph_client_failure(self):
        """Test initialization fails gracefully when Graph client creation fails."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential"):
            with patch(
                "backend.services.email.providers.outlook.GraphServiceClient"
            ) as mock_gsc:
                mock_gsc.side_effect = Exception("Graph API error")

                with pytest.raises(EmailConfigurationError) as exc_info:
                    OutlookProvider(user_principal_name="test@example.com")

                assert "Failed to initialize Microsoft Graph client" in str(
                    exc_info.value
                )


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Test input validation in _validate_email_inputs method."""

    @pytest.mark.asyncio
    async def test_validate_empty_to_address(self, outlook_provider):
        """Test validation fails with empty to_address."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="",
                subject="Test",
                body="Test body",
            )

        assert "to_address cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_whitespace_to_address(self, outlook_provider):
        """Test validation fails with whitespace-only to_address."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="   ",
                subject="Test",
                body="Test body",
            )

        assert "to_address cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_empty_from_address(self, outlook_provider):
        """Test validation fails with empty from_address."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        assert "from_address cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_empty_subject(self, outlook_provider):
        """Test validation fails with empty subject."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="",
                body="Test body",
            )

        assert "subject cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_no_body(self, outlook_provider):
        """Test validation fails when both body and html_body are missing."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="",
            )

        assert "Either body or html_body must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_invalid_to_address_format(self, outlook_provider):
        """Test validation fails with invalid to_address format."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="invalid-email",
                subject="Test",
                body="Test body",
            )

        assert "Invalid to_address format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_invalid_from_address_format(self, outlook_provider):
        """Test validation fails with invalid from_address format."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="invalid-email",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        assert "Invalid from_address format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_invalid_reply_to_format(self, outlook_provider):
        """Test validation fails with invalid reply_to format."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
                reply_to="invalid-email",
            )

        assert "Invalid reply_to format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_from_address_mismatch(self, outlook_provider):
        """Test validation fails when from_address doesn't match configured sender."""
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="different@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        assert "does not match configured sender" in str(exc_info.value)
        assert "test@example.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_from_address_case_insensitive(self, outlook_provider):
        """Test from_address validation is case-insensitive."""
        # Should not raise - case variation of configured sender
        await outlook_provider.send_email(
            from_address="TEST@EXAMPLE.COM",
            to_address="recipient@example.com",
            subject="Test",
            body="Test body",
        )


# ---------------------------------------------------------------------------
# Send Email Tests
# ---------------------------------------------------------------------------


class TestSendEmail:
    """Test send_email functionality."""

    @pytest.mark.asyncio
    async def test_send_plain_text_email(self, outlook_provider, mock_graph_client):
        """Test sending a plain text email."""
        result = await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="Test Subject",
            body="Test body content",
        )

        assert result["status"] == "sent"
        assert result["provider"] == "outlook"
        assert result["to"] == "recipient@example.com"
        assert result["from"] == "test@example.com"
        assert result["subject"] == "Test Subject"

        # Verify Graph API was called
        mock_graph_client.users.by_user_id.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_send_html_email(self, outlook_provider, mock_graph_client):
        """Test sending an HTML email."""
        html_body = "<html><body><h1>Test</h1></body></html>"

        result = await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="HTML Test",
            body="Plain text fallback",
            html_body=html_body,
        )

        assert result["status"] == "sent"
        mock_graph_client.users.by_user_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_reply_to(self, outlook_provider, mock_graph_client):
        """Test sending an email with reply-to address."""
        result = await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="Test",
            body="Test body",
            reply_to="support@example.com",
        )

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_email_graph_api_error(
        self, outlook_provider, mock_graph_client
    ):
        """Test error handling when Graph API call fails."""
        # Make the Graph API call raise an exception
        mock_graph_client.users.by_user_id.return_value.send_mail.post.side_effect = (
            Exception("Graph API error")
        )

        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        assert "Failed to send email via Microsoft Graph" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Retry Logic Tests
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, outlook_provider, mock_graph_client):
        """Test retry logic retries on transient errors."""
        # First two calls fail with retryable errors, third succeeds
        mock_send_mail = mock_graph_client.users.by_user_id.return_value.send_mail.post

        # Create retryable errors (429 rate limit, 500 server error)
        # Use spec_set=[] to prevent auto-mocking of attributes
        mock_response_429 = Mock(spec_set=["status_code", "reason"])
        mock_response_429.status_code = 429
        mock_response_429.reason = "Too Many Requests"
        error_429 = HttpResponseError(response=mock_response_429)

        mock_response_500 = Mock(spec_set=["status_code", "reason"])
        mock_response_500.status_code = 500
        mock_response_500.reason = "Internal Server Error"
        error_500 = HttpResponseError(response=mock_response_500)

        mock_send_mail.side_effect = [
            error_429,  # First attempt: rate limited
            error_500,  # Second attempt: server error
            None,  # Third attempt: success
        ]

        result = await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="Test",
            body="Test body",
        )

        assert result["status"] == "sent"
        # Should have been called 3 times (2 failures + 1 success)
        assert mock_send_mail.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, outlook_provider, mock_graph_client, caplog):
        """Test retry logic fails after max attempts."""
        # All attempts fail with a retryable error
        mock_send_mail = mock_graph_client.users.by_user_id.return_value.send_mail.post

        # Create a persistent retryable error (503 service unavailable)
        mock_response_503 = Mock()
        mock_response_503.status_code = 503
        mock_response_503.reason = "Service Unavailable"
        persistent_error = HttpResponseError(response=mock_response_503)

        mock_send_mail.side_effect = persistent_error

        with caplog.at_level(logging.WARNING):
            with pytest.raises(EmailSendError):
                await outlook_provider.send_email(
                    from_address="test@example.com",
                    to_address="recipient@example.com",
                    subject="Test",
                    body="Test body",
                )

        # Should have attempted 3 times (max retries)
        assert mock_send_mail.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(
        self, outlook_provider, mock_graph_client
    ):
        """Test validation errors don't trigger retries."""
        mock_send_mail = mock_graph_client.users.by_user_id.return_value.send_mail.post

        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="",  # Invalid - empty
                subject="Test",
                body="Test body",
            )

        # Should not have called Graph API at all (validation happens first)
        assert mock_send_mail.call_count == 0
        assert "to_address cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, outlook_provider, mock_graph_client):
        """Test authentication errors (401) don't trigger retries."""
        mock_send_mail = mock_graph_client.users.by_user_id.return_value.send_mail.post

        # Create a 401 authentication error
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.reason = "Unauthorized"
        auth_error = HttpResponseError(response=mock_response_401)
        mock_send_mail.side_effect = auth_error

        with pytest.raises(EmailSendError):
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        # Should only have been called once (no retries on auth errors)
        assert mock_send_mail.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_permission_error(
        self, outlook_provider, mock_graph_client
    ):
        """Test permission errors (403) don't trigger retries."""
        mock_send_mail = mock_graph_client.users.by_user_id.return_value.send_mail.post

        # Create a 403 forbidden error
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        mock_response_403.reason = "Forbidden"
        permission_error = HttpResponseError(response=mock_response_403)
        mock_send_mail.side_effect = permission_error

        with pytest.raises(EmailSendError):
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        # Should only have been called once (no retries on permission errors)
        assert mock_send_mail.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_bad_request(self, outlook_provider, mock_graph_client):
        """Test bad request errors (400) don't trigger retries."""
        mock_send_mail = mock_graph_client.users.by_user_id.return_value.send_mail.post

        # Create a 400 bad request error
        mock_response_400 = Mock()
        mock_response_400.status_code = 400
        mock_response_400.reason = "Bad Request"
        bad_request_error = HttpResponseError(response=mock_response_400)
        mock_send_mail.side_effect = bad_request_error

        with pytest.raises(EmailSendError):
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test",
                body="Test body",
            )

        # Should only have been called once (no retries on bad request)
        assert mock_send_mail.call_count == 1


# ---------------------------------------------------------------------------
# Factory Integration Tests
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    """Test OutlookProvider integration with EmailServiceFactory."""

    def test_create_outlook_provider_from_factory(self, mock_graph_client):
        """Test creating OutlookProvider via factory."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential"):
            with patch(
                "backend.services.email.providers.outlook.GraphServiceClient"
            ) as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                provider = EmailServiceFactory.create_provider(
                    provider_name="outlook",
                    user_principal_name="test@example.com",
                    sender_email="sender@example.com",
                )

                assert isinstance(provider, OutlookProvider)
                assert provider.user_principal_name == "test@example.com"
                assert provider.sender_email == "sender@example.com"

    def test_factory_outlook_without_user_principal_name(self):
        """Test factory fails when creating Outlook without user_principal_name."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EmailConfigurationError):
                EmailServiceFactory.create_provider(
                    provider_name="outlook", user_principal_name=None
                )

    def test_factory_passes_cross_tenant_config(self, mock_graph_client):
        """Test factory passes cross-tenant config values to OutlookProvider."""
        with patch("backend.services.email.providers.outlook.ClientSecretCredential") as mock_csc:
            with patch("backend.services.email.providers.outlook.GraphServiceClient") as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                with patch("backend.services.email.providers.factory.OUTLOOK_USER_PRINCIPAL_NAME", "user@example.com"):
                    with patch("backend.services.email.providers.factory.OUTLOOK_TENANT_ID", "tenant-abc"):
                        with patch("backend.services.email.providers.factory.OUTLOOK_CLIENT_ID", "client-def"):
                            with patch("backend.services.email.providers.factory.OUTLOOK_CLIENT_SECRET", "secret-ghi"):
                                provider = EmailServiceFactory.create_provider(
                                    provider_name="outlook"
                                )

                                assert isinstance(provider, OutlookProvider)
                                mock_csc.assert_called_once_with(
                                    tenant_id="tenant-abc",
                                    client_id="client-def",
                                    client_secret="secret-ghi",
                                )

    def test_factory_outlook_with_config_values(self, mock_graph_client):
        """Test factory uses config values for Outlook when kwargs not provided."""
        with patch("backend.services.email.providers.outlook.DefaultAzureCredential"):
            with patch(
                "backend.services.email.providers.outlook.GraphServiceClient"
            ) as mock_gsc:
                mock_gsc.return_value = mock_graph_client

                # Patch the config values directly
                with patch(
                    "backend.services.email.providers.factory.OUTLOOK_USER_PRINCIPAL_NAME",
                    "config-user@example.com",
                ):
                    with patch(
                        "backend.services.email.providers.factory.OUTLOOK_SENDER_EMAIL",
                        "config-sender@example.com",
                    ):
                        provider = EmailServiceFactory.create_provider(
                            provider_name="outlook"
                        )

                        assert isinstance(provider, OutlookProvider)
                        assert provider.user_principal_name == "config-user@example.com"
                        assert provider.sender_email == "config-sender@example.com"


# ---------------------------------------------------------------------------
# Not Implemented Methods Tests
# ---------------------------------------------------------------------------


class TestNotImplementedMethods:
    """Test that unimplemented methods raise appropriate exceptions."""

    @pytest.mark.asyncio
    async def test_create_inbox_not_implemented(self, outlook_provider):
        """Test create_inbox raises InboxCreationError."""
        from backend.services.email.exceptions import InboxCreationError

        with pytest.raises(InboxCreationError) as exc_info:
            await outlook_provider.create_inbox()

        assert "not yet implemented" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_inbox_not_implemented(self, outlook_provider):
        """Test delete_inbox raises InboxDeletionError."""
        from backend.services.email.exceptions import InboxDeletionError

        with pytest.raises(InboxDeletionError) as exc_info:
            await outlook_provider.delete_inbox("test-inbox-id")

        assert "not yet implemented" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_webhook_not_implemented(self, outlook_provider):
        """Test register_webhook raises WebhookRegistrationError."""
        from backend.services.email.exceptions import WebhookRegistrationError

        with pytest.raises(WebhookRegistrationError) as exc_info:
            await outlook_provider.register_webhook(
                "inbox-id", "https://example.com/webhook"
            )

        assert "not yet implemented" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unregister_webhook_not_implemented(self, outlook_provider):
        """Test unregister_webhook raises WebhookUnregistrationError."""
        from backend.services.email.exceptions import WebhookUnregistrationError

        with pytest.raises(WebhookUnregistrationError) as exc_info:
            await outlook_provider.unregister_webhook("webhook-id")

        assert "not yet implemented" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_emails_not_implemented(self, outlook_provider):
        """Test get_emails raises EmailRetrievalError."""
        from backend.services.email.exceptions import EmailRetrievalError

        with pytest.raises(EmailRetrievalError) as exc_info:
            await outlook_provider.get_emails("inbox-id")

        assert "not yet implemented" in str(exc_info.value)

    def test_validate_webhook_signature_not_implemented(self, outlook_provider):
        """Test validate_webhook_signature returns False."""
        result = outlook_provider.validate_webhook_signature(
            payload=b"test", signature="test-signature"
        )

        assert result is False


# ---------------------------------------------------------------------------
# Attachment Tests
# ---------------------------------------------------------------------------


def _sent_message(mock_graph_client):
    """Extract the Message object passed to the most recent send_mail.post call."""
    mock_post = mock_graph_client.users.by_user_id.return_value.send_mail.post
    assert mock_post.called, "send_mail.post was not called"
    request_body = mock_post.call_args.args[0]
    return request_body.message


class TestAttachments:
    """Test file attachment handling for the Outlook provider."""

    @pytest.mark.asyncio
    async def test_send_email_without_attachments_leaves_attachments_unset(
        self, outlook_provider, mock_graph_client
    ):
        """No attachments argument should not populate message.attachments."""
        await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="No attachments",
            body="Body",
        )

        message = _sent_message(mock_graph_client)
        assert not message.attachments

    @pytest.mark.asyncio
    async def test_send_email_with_single_attachment(
        self, outlook_provider, mock_graph_client
    ):
        """A single attachment is serialized as a Graph FileAttachment."""
        from backend.services.email.providers.base import EmailAttachment
        from msgraph.generated.models.file_attachment import FileAttachment

        content = b"report body bytes"
        await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="With attachment",
            body="See attached",
            attachments=[
                EmailAttachment(
                    filename="report.pdf",
                    content=content,
                    mime_type="application/pdf",
                )
            ],
        )

        message = _sent_message(mock_graph_client)
        assert message.attachments is not None
        assert len(message.attachments) == 1
        att = message.attachments[0]
        assert isinstance(att, FileAttachment)
        assert att.odata_type == "#microsoft.graph.fileAttachment"
        assert att.name == "report.pdf"
        assert att.content_type == "application/pdf"
        assert att.content_bytes == content

    @pytest.mark.asyncio
    async def test_send_email_with_multiple_attachments_preserves_order(
        self, outlook_provider, mock_graph_client
    ):
        """Multiple attachments keep their input order on the Graph message."""
        from backend.services.email.providers.base import EmailAttachment

        attachments = [
            EmailAttachment(filename="a.txt", content=b"AAA", mime_type="text/plain"),
            EmailAttachment(filename="b.csv", content=b"B,B", mime_type="text/csv"),
            EmailAttachment(
                filename="c.json", content=b'{"x":1}', mime_type="application/json"
            ),
        ]
        await outlook_provider.send_email(
            from_address="test@example.com",
            to_address="recipient@example.com",
            subject="Three files",
            body="Body",
            attachments=attachments,
        )

        message = _sent_message(mock_graph_client)
        assert [a.name for a in message.attachments] == ["a.txt", "b.csv", "c.json"]
        assert [a.content_bytes for a in message.attachments] == [
            b"AAA",
            b"B,B",
            b'{"x":1}',
        ]

    @pytest.mark.asyncio
    async def test_send_email_rejects_oversize_single_attachment(
        self, outlook_provider, mock_graph_client
    ):
        """A single attachment above the per-file cap fails fast, no send call."""
        from backend.services.email.providers.base import EmailAttachment
        from backend.services.email.providers.outlook import (
            GRAPH_INLINE_ATTACHMENT_MAX_BYTES,
        )

        oversized = b"\x00" * (GRAPH_INLINE_ATTACHMENT_MAX_BYTES + 1)
        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Too big",
                body="Body",
                attachments=[
                    EmailAttachment(
                        filename="huge.bin",
                        content=oversized,
                        mime_type="application/octet-stream",
                    )
                ],
            )

        assert "huge.bin" in str(exc_info.value)
        mock_graph_client.users.by_user_id.return_value.send_mail.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_email_rejects_oversize_total(
        self, outlook_provider, mock_graph_client
    ):
        """Combined attachment payload above the request cap fails fast."""
        from backend.services.email.providers.base import EmailAttachment
        from backend.services.email.providers.outlook import (
            GRAPH_INLINE_ATTACHMENT_MAX_BYTES,
            GRAPH_INLINE_REQUEST_MAX_BYTES,
        )

        # Two files each just under the per-file cap, totaling above request cap.
        per_file = GRAPH_INLINE_ATTACHMENT_MAX_BYTES - 1
        attachments = [
            EmailAttachment(
                filename=f"f{i}.bin",
                content=b"\x00" * per_file,
                mime_type="application/octet-stream",
            )
            for i in range(2)
        ]
        assert sum(len(a.content) for a in attachments) > GRAPH_INLINE_REQUEST_MAX_BYTES

        with pytest.raises(EmailSendError) as exc_info:
            await outlook_provider.send_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Too much",
                body="Body",
                attachments=attachments,
            )

        assert "Total attachment size" in str(exc_info.value)
        mock_graph_client.users.by_user_id.return_value.send_mail.post.assert_not_called()
