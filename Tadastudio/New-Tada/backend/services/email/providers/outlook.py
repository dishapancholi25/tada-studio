"""
Outlook/Microsoft 365 email service provider implementation.

Supports sending emails via Microsoft Graph API using managed identity authentication.
Designed for use in Azure Kubernetes Service (AKS) with workload identity.
"""

import logging
from typing import Any, Dict, List, Optional

from azure.core.exceptions import HttpResponseError, ServiceRequestError
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.attachment import Attachment
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from ..config import LOG_PREFIX_PROVIDER
from ..exceptions import (
    EmailConfigurationError,
    EmailRetrievalError,
    EmailSendError,
    InboxCreationError,
    InboxDeletionError,
    WebhookRegistrationError,
    WebhookUnregistrationError,
)
from ..schemas import EmailInbox, EmailMessage, EmailWebhook
from .base import EmailAttachment, EmailServiceProvider

logger = logging.getLogger(__name__)

# Microsoft Graph sendMail endpoint inline attachment limits.
# Per-file cap is ~3 MB; total JSON request must stay under ~4 MB. Larger files
# require the draft + upload-session flow, which is not yet supported here.
GRAPH_INLINE_ATTACHMENT_MAX_BYTES = 3 * 1024 * 1024
GRAPH_INLINE_REQUEST_MAX_BYTES = 4 * 1024 * 1024


def _is_retryable_exception(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.

    Retryable errors:
    - Rate limiting (429)
    - Server errors (5xx)
    - Network/connection errors
    - Temporary service unavailability (503)

    Non-retryable errors:
    - Authentication failures (401)
    - Permission errors (403)
    - Bad request/validation errors (400)
    - Not found errors (404)

    Args:
        exception: The exception to evaluate

    Returns:
        True if the exception should trigger a retry, False otherwise
    """
    # Network/connection errors are always retryable
    if isinstance(exception, (ServiceRequestError, ConnectionError, TimeoutError)):
        return True

    # For HTTP response errors, check the status code
    if isinstance(exception, HttpResponseError):
        status_code = getattr(exception, "status_code", None)
        if status_code:
            # Rate limiting - definitely retry
            if status_code == 429:
                return True
            # Server errors - retry
            if 500 <= status_code < 600:
                return True
            # Service unavailable - retry
            if status_code == 503:
                return True
            # Client errors (4xx except 429) - don't retry
            # These include 400 (bad request), 401 (auth), 403 (forbidden), 404 (not found)
            if 400 <= status_code < 500:
                return False

    # For unknown errors, don't retry to avoid masking issues
    return False


class OutlookProvider(EmailServiceProvider):
    """Microsoft Outlook/365 implementation using Graph API with managed identity."""

    def __init__(
        self,
        sender_email: str = None,
        user_principal_name: str = None,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
    ):
        """
        Initialize Outlook provider with managed identity or client credentials.

        When tenant_id, client_id, and client_secret are all provided, uses
        ClientSecretCredential for cross-tenant authentication. Otherwise falls
        back to DefaultAzureCredential which supports:
        - Workload Identity (recommended for AKS)
        - Managed Identity
        - Azure CLI (for local development)
        - Environment variables

        Args:
            sender_email: Email address to send from (defaults to user_principal_name)
            user_principal_name: The UPN or email of the user/service account
                                 in Azure AD that will send emails
            tenant_id: Azure AD tenant ID (for cross-tenant auth)
            client_id: App registration client ID (for cross-tenant auth)
            client_secret: App registration client secret (for cross-tenant auth)

        Raises:
            EmailConfigurationError: If configuration is invalid
        """
        self.user_principal_name = user_principal_name
        self.sender_email = sender_email or user_principal_name
        if sender_email is not None and "@" in sender_email:
            self.domain = sender_email.split("@")[-1]

        if not self.user_principal_name:
            raise EmailConfigurationError(
                "user_principal_name is required for Outlook provider"
            )

        # Use ClientSecretCredential for cross-tenant, DefaultAzureCredential otherwise
        if tenant_id and client_id and client_secret:
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            logger.info(
                f"{LOG_PREFIX_PROVIDER} Using ClientSecretCredential for tenant {tenant_id}"
            )
        else:
            self.credential = DefaultAzureCredential()
            logger.info(f"{LOG_PREFIX_PROVIDER} Using DefaultAzureCredential")

        # Initialize Microsoft Graph client
        # Scopes for sending mail via Graph API
        self.scopes = ["https://graph.microsoft.com/.default"]

        try:
            self.client = GraphServiceClient(
                credentials=self.credential,
                scopes=self.scopes,
            )
            logger.info(
                f"{LOG_PREFIX_PROVIDER} Initialized Outlook provider for {self.user_principal_name}"
            )
        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_PROVIDER} Failed to initialize Graph client: {e}"
            )
            raise EmailConfigurationError(
                f"Failed to initialize Microsoft Graph client: {e}"
            ) from e

    def _validate_email_inputs(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> None:
        """
        Validate email inputs before sending.

        Args:
            from_address: Sender email address
            to_address: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            reply_to: Optional reply-to address

        Raises:
            EmailSendError: If validation fails
        """
        # Validate required fields are not empty
        if not to_address or not to_address.strip():
            raise EmailSendError("to_address cannot be empty")

        if not from_address or not from_address.strip():
            raise EmailSendError("from_address cannot be empty")

        if not subject or not subject.strip():
            raise EmailSendError("subject cannot be empty")

        if not body and not html_body:
            raise EmailSendError("Either body or html_body must be provided")

        # Basic email format validation
        if "@" not in to_address or "." not in to_address.split("@")[-1]:
            raise EmailSendError(f"Invalid to_address format: {to_address}")

        if "@" not in from_address or "." not in from_address.split("@")[-1]:
            raise EmailSendError(f"Invalid from_address format: {from_address}")

        if reply_to and ("@" not in reply_to or "." not in reply_to.split("@")[-1]):
            raise EmailSendError(f"Invalid reply_to format: {reply_to}")

        # Validate from_address matches configured sender
        # Graph API requires the from_address to match the authenticated user or a delegated mailbox
        if from_address.lower() not in [
            self.sender_email.lower(),
            self.user_principal_name.lower(),
        ]:
            raise EmailSendError(
                f"from_address '{from_address}' does not match configured sender. "
                f"Expected '{self.sender_email}' or '{self.user_principal_name}'"
            )

    @staticmethod
    def _build_graph_attachments(
        attachments: List[EmailAttachment],
    ) -> List[Attachment]:
        """Convert EmailAttachment objects to Microsoft Graph FileAttachments.

        Enforces Graph's inline-attachment size limits and raises EmailSendError
        before any network call if a file or the combined payload is too large.
        """
        total_bytes = 0
        for att in attachments:
            size = len(att.content)
            if size > GRAPH_INLINE_ATTACHMENT_MAX_BYTES:
                raise EmailSendError(
                    f"Attachment '{att.filename}' is {size} bytes; Outlook inline "
                    f"attachments must be <= {GRAPH_INLINE_ATTACHMENT_MAX_BYTES} bytes"
                )
            total_bytes += size

        if total_bytes > GRAPH_INLINE_REQUEST_MAX_BYTES:
            raise EmailSendError(
                f"Total attachment size {total_bytes} bytes exceeds Outlook inline "
                f"request limit of {GRAPH_INLINE_REQUEST_MAX_BYTES} bytes"
            )

        graph_attachments: List[Attachment] = []
        for att in attachments:
            file_att = FileAttachment()
            file_att.odata_type = "#microsoft.graph.fileAttachment"
            file_att.name = att.filename
            file_att.content_type = att.mime_type
            file_att.content_bytes = att.content
            graph_attachments.append(file_att)
        return graph_attachments

    @retry(
        retry=retry_if_exception(_is_retryable_exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_email_impl(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> Dict[str, Any]:
        """
        Internal implementation of send_email with retry logic.

        This method contains the core logic and lets retryable exceptions bubble up
        to the retry decorator.
        """
        # Create the message
        message = Message()
        message.subject = subject

        # Set body (prefer HTML if provided)
        message.body = ItemBody()
        if html_body:
            message.body.content_type = BodyType.Html
            message.body.content = html_body
        else:
            message.body.content_type = BodyType.Text
            message.body.content = body

        # Set recipients
        to_recipient = Recipient()
        to_recipient.email_address = EmailAddress()
        to_recipient.email_address.address = to_address
        message.to_recipients = [to_recipient]

        # Set reply-to if provided
        if reply_to:
            reply_to_recipient = Recipient()
            reply_to_recipient.email_address = EmailAddress()
            reply_to_recipient.email_address.address = reply_to
            message.reply_to = [reply_to_recipient]

        if attachments:
            message.attachments = self._build_graph_attachments(attachments)

        # Create send mail request body
        request_body = SendMailPostRequestBody()
        request_body.message = message
        request_body.save_to_sent_items = True

        logger.info(
            f"{LOG_PREFIX_PROVIDER} Sending email via Graph API from {from_address} to {to_address}"
            f" ({len(attachments or [])} attachments)"
        )

        # Send the email using the user's mailbox
        # Let exceptions bubble up for retry handling
        await self.client.users.by_user_id(self.user_principal_name).send_mail.post(
            request_body
        )

        logger.info(f"{LOG_PREFIX_PROVIDER} Email sent successfully to {to_address}")

        return {
            "status": "sent",
            "provider": "outlook",
            "to": to_address,
            "from": from_address,
            "subject": subject,
        }

    async def send_email(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via Microsoft Graph API.

        Implements retry logic with exponential backoff to handle:
        - Rate limiting (429 errors)
        - Transient network errors
        - Temporary service unavailability

        Retry strategy:
        - Maximum 3 attempts
        - Exponential backoff: 2s, 4s, 8s (capped at 10s)
        - Logs warning before each retry

        Non-retryable errors (fail immediately):
        - Authentication failures (401)
        - Permission errors (403)
        - Validation errors (400)
        - Not found errors (404)

        Args:
            from_address: Sender email address (must match configured sender or delegate)
            to_address: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body (takes precedence over plain text)
            reply_to: Optional reply-to address

        Returns:
            Dict with send result (includes message_id if available)

        Raises:
            EmailSendError: If sending fails after all retries
        """
        # Validate inputs before making API call
        # Validation errors should not trigger retries
        self._validate_email_inputs(
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            body=body,
            html_body=html_body,
            reply_to=reply_to,
        )

        try:
            return await self._send_email_impl(
                from_address=from_address,
                to_address=to_address,
                subject=subject,
                body=body,
                html_body=html_body,
                reply_to=reply_to,
                attachments=attachments,
            )
        except EmailSendError:
            # Validation / size-limit errors already have clear messages; don't re-wrap.
            raise
        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_PROVIDER} Failed to send email via Graph API: {e}"
            )
            raise EmailSendError(
                f"Failed to send email via Microsoft Graph: {e}"
            ) from e

    async def create_inbox(self, expires_in_minutes: int = 60) -> EmailInbox:
        """
        Create a temporary inbox for receiving emails.

        NOT IMPLEMENTED YET for Outlook provider.

        Args:
            expires_in_minutes: How long the inbox should remain active

        Returns:
            EmailInbox object with inbox details

        Raises:
            InboxCreationError: Not implemented
        """
        raise InboxCreationError(
            "Inbox creation not yet implemented for Outlook provider"
        )

    async def delete_inbox(self, inbox_id: str) -> bool:
        """
        Delete an inbox.

        NOT IMPLEMENTED YET for Outlook provider.

        Args:
            inbox_id: The inbox ID to delete

        Returns:
            True if successful, False otherwise

        Raises:
            InboxDeletionError: Not implemented
        """
        raise InboxDeletionError(
            "Inbox deletion not yet implemented for Outlook provider"
        )

    async def register_webhook(
        self, inbox_id: str, webhook_url: str, event_types: List[str] = None
    ) -> EmailWebhook:
        """
        Register a webhook for inbox events.

        NOT IMPLEMENTED YET for Outlook provider.

        Args:
            inbox_id: The inbox ID to monitor
            webhook_url: URL to send webhook notifications
            event_types: List of event types to monitor

        Returns:
            EmailWebhook object with registration details

        Raises:
            WebhookRegistrationError: Not implemented
        """
        raise WebhookRegistrationError(
            "Webhook registration not yet implemented for Outlook provider"
        )

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook.

        NOT IMPLEMENTED YET for Outlook provider.

        Args:
            webhook_id: The webhook ID to unregister

        Returns:
            True if successful, False otherwise

        Raises:
            WebhookUnregistrationError: Not implemented
        """
        raise WebhookUnregistrationError(
            "Webhook unregistration not yet implemented for Outlook provider"
        )

    async def get_emails(self, inbox_id: str, limit: int = 10) -> List[EmailMessage]:
        """
        Get emails from an inbox.

        NOT IMPLEMENTED YET for Outlook provider.

        Args:
            inbox_id: The inbox ID
            limit: Maximum number of emails to retrieve

        Returns:
            List of EmailMessage objects

        Raises:
            EmailRetrievalError: Not implemented
        """
        raise EmailRetrievalError(
            "Email retrieval not yet implemented for Outlook provider"
        )

    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        """
        Validate webhook signature for security.

        NOT IMPLEMENTED YET for Outlook provider.

        Args:
            payload: The webhook payload
            signature: The signature to validate
            secret: Optional secret key for validation

        Returns:
            True if signature is valid, False otherwise
        """
        logger.warning(
            f"{LOG_PREFIX_PROVIDER} Webhook signature validation not implemented for Outlook"
        )
        return False
