"""
Mailgun email service provider implementation.

Supports sending and receiving emails with webhook support using Mailgun API.
"""

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from ..config import (
    LOG_PREFIX_PROVIDER,
    MAILGUN_API_KEY,
    MAILGUN_BASE_URL,
    MAILGUN_DOMAIN,
)
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


class MailgunProvider(EmailServiceProvider):
    """Mailgun implementation of email service provider."""

    def __init__(self, api_key: str = None, domain: str = None):
        """
        Initialize Mailgun provider.

        Args:
            api_key: Mailgun API key (defaults to env variable)
            domain: Mailgun domain (defaults to env variable)

        Raises:
            EmailConfigurationError: If API key is missing
        """
        self.api_key = api_key or MAILGUN_API_KEY
        self.domain = domain or MAILGUN_DOMAIN

        if not self.api_key:
            raise EmailConfigurationError("Mailgun API key is required")

        # Use sandbox domain if no custom domain specified
        if "sandbox" not in self.domain and not domain:
            self.domain = os.getenv(
                "MAILGUN_SANDBOX_DOMAIN", f"sandbox{hash(self.api_key)}.mailgun.org"
            )

        self.base_url = MAILGUN_BASE_URL
        self.auth = aiohttp.BasicAuth("api", self.api_key)

        # Store active workflow mappings (email -> execution_id)
        self.workflow_mappings: Dict[str, str] = {}

        logger.info(
            f"{LOG_PREFIX_PROVIDER} Initialized Mailgun with domain: {self.domain}"
        )

    async def create_inbox(self, expires_in_minutes: int = 60) -> EmailInbox:
        """
        Create a unique email address for receiving responses.

        With Mailgun, we use catch-all routing instead of creating actual inboxes.

        Args:
            expires_in_minutes: How long the inbox should remain active

        Returns:
            EmailInbox with generated email address

        Raises:
            InboxCreationError: If inbox creation fails
        """
        try:
            unique_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
            email_address = f"workflow-{unique_id}@{self.domain}"
            expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)

            logger.info(f"{LOG_PREFIX_PROVIDER} Created inbox: {email_address}")

            return EmailInbox(
                inbox_id=unique_id,
                email_address=email_address,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                metadata={"provider": "mailgun", "domain": self.domain},
            )
        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to create inbox: {e}")
            raise InboxCreationError(f"Failed to create Mailgun inbox: {e}") from e

    async def delete_inbox(self, inbox_id: str) -> bool:
        """
        Clean up inbox mapping.

        With Mailgun, we just remove the mapping from tracking.

        Args:
            inbox_id: The inbox ID to delete

        Returns:
            True if successful
        """
        try:
            email_address = f"workflow-{inbox_id}@{self.domain}"
            if email_address in self.workflow_mappings:
                del self.workflow_mappings[email_address]

            logger.info(f"{LOG_PREFIX_PROVIDER} Deleted inbox mapping: {inbox_id}")
            return True
        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to delete inbox: {e}")
            raise InboxDeletionError(f"Failed to delete inbox: {e}") from e

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
        Send an email via Mailgun.

        Args:
            from_address: Sender email address
            to_address: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            reply_to: Optional reply-to address
            attachments: Optional list of file attachments

        Returns:
            Dict with send result

        Raises:
            EmailSendError: If sending fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = self._prepare_email_data(
                    from_address,
                    to_address,
                    subject,
                    body,
                    html_body,
                    reply_to,
                    attachments,
                )
                url = f"{self.base_url}/{self.domain}/messages"

                logger.info(
                    f"{LOG_PREFIX_PROVIDER} Sending email from {from_address} to {to_address}"
                    f" ({len(attachments or [])} attachments)"
                )

                result = await self._send_request(session, url, data)

                logger.info(
                    f"{LOG_PREFIX_PROVIDER} Email sent: {result.get('id', 'no-id')}"
                )
                return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to send email: {e}")
            raise EmailSendError(f"Failed to send email via Mailgun: {e}") from e

    def _prepare_email_data(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str],
        reply_to: Optional[str],
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> aiohttp.FormData:
        """Prepare form data for email sending."""
        data = aiohttp.FormData()
        data.add_field("from", from_address)
        data.add_field("to", to_address)
        data.add_field("subject", subject)

        if html_body:
            data.add_field("html", html_body)
            data.add_field("text", body)
        else:
            data.add_field("text", body)

        if reply_to:
            data.add_field("h:Reply-To", reply_to)

        if attachments:
            for attachment in attachments:
                data.add_field(
                    "attachment",
                    attachment.content,
                    filename=attachment.filename,
                    content_type=attachment.mime_type,
                )

        return data

    async def _send_request(
        self, session: aiohttp.ClientSession, url: str, data: aiohttp.FormData
    ) -> Dict[str, Any]:
        """Send request to Mailgun API."""
        async with session.post(url, auth=self.auth, data=data) as response:
            response_text = await response.text()

            if response.status >= 400:
                logger.error(
                    f"{LOG_PREFIX_PROVIDER} Mailgun error {response.status}: {response_text}"
                )
                response.raise_for_status()

            return json.loads(response_text)

    async def send_email_with_workflow_id(
        self,
        workflow_id: str,
        execution_id: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email with workflow tracking.

        Uses unique reply-to address for mapping responses.

        Args:
            workflow_id: The workflow ID
            execution_id: The execution ID
            to_address: Recipient email
            subject: Email subject
            body: Email body
            html_body: Optional HTML body

        Returns:
            Send result with workflow tracking info

        Raises:
            EmailSendError: If sending fails
        """
        try:
            reply_to_address = f"workflow-{execution_id}@{self.domain}"
            self.workflow_mappings[reply_to_address] = execution_id

            subject_with_ref = f"{subject} [REF:{execution_id[:8]}]"

            result = await self.send_email(
                from_address=f"AgenticStudio <noreply@{self.domain}>",
                to_address=to_address,
                subject=subject_with_ref,
                body=body,
                html_body=html_body,
                reply_to=reply_to_address,
            )

            result["workflow_id"] = workflow_id
            result["execution_id"] = execution_id
            result["reply_to"] = reply_to_address

            logger.info(
                f"{LOG_PREFIX_PROVIDER} Workflow email sent with reply-to: {reply_to_address}"
            )
            return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to send workflow email: {e}")
            raise EmailSendError(f"Failed to send workflow email: {e}") from e

    async def register_webhook(
        self, inbox_id: str, webhook_url: str, event_types: List[str] = None
    ) -> EmailWebhook:
        """
        Register a webhook for receiving email notifications.

        Creates a Mailgun route to forward emails to the webhook.

        Args:
            inbox_id: The inbox ID to monitor (* for catch-all)
            webhook_url: URL to send notifications
            event_types: Event types (defaults to ['inbound'])

        Returns:
            EmailWebhook with registration details

        Raises:
            WebhookRegistrationError: If registration fails
        """
        try:
            if event_types is None:
                event_types = ["inbound"]

            async with aiohttp.ClientSession() as session:
                data = self._prepare_webhook_data(inbox_id, webhook_url)
                url = f"{self.base_url}/routes"

                result = await self._register_webhook_request(session, url, data)
                route_id = result["route"]["id"]

                logger.info(f"{LOG_PREFIX_PROVIDER} Created webhook route: {route_id}")

                return EmailWebhook(
                    webhook_id=route_id,
                    inbox_id=inbox_id,
                    url=webhook_url,
                    event_types=event_types,
                    created_at=datetime.utcnow(),
                )

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to register webhook: {e}")
            raise WebhookRegistrationError(
                f"Failed to register Mailgun webhook: {e}"
            ) from e

    def _prepare_webhook_data(
        self, inbox_id: str, webhook_url: str
    ) -> aiohttp.FormData:
        """Prepare webhook registration data."""
        data = aiohttp.FormData()

        if inbox_id == "*":
            expression = f"match_recipient('workflow-.*@{self.domain}')"
        else:
            expression = f"match_recipient('workflow-{inbox_id}@{self.domain}')"

        data.add_field("priority", "0")
        data.add_field("description", f"Route for workflow {inbox_id}")
        data.add_field("expression", expression)
        data.add_field("action", f"forward('{webhook_url}')")
        data.add_field("action", "stop()")

        return data

    async def _register_webhook_request(
        self, session: aiohttp.ClientSession, url: str, data: aiohttp.FormData
    ) -> Dict[str, Any]:
        """Send webhook registration request."""
        async with session.post(url, auth=self.auth, data=data) as response:
            response_text = await response.text()

            if response.status >= 400:
                logger.error(
                    f"{LOG_PREFIX_PROVIDER} Failed to create route: {response_text}"
                )
                response.raise_for_status()

            return json.loads(response_text)

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Delete a Mailgun route.

        Args:
            webhook_id: The webhook/route ID to delete

        Returns:
            True if successful

        Raises:
            WebhookUnregistrationError: If deletion fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/routes/{webhook_id}"

                async with session.delete(url, auth=self.auth) as response:
                    success = response.status in [200, 204]

                    if success:
                        logger.info(
                            f"{LOG_PREFIX_PROVIDER} Unregistered webhook: {webhook_id}"
                        )
                    else:
                        logger.warning(
                            f"{LOG_PREFIX_PROVIDER} Failed to unregister webhook: {webhook_id}"
                        )

                    return success

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to unregister webhook: {e}")
            raise WebhookUnregistrationError(
                f"Failed to unregister webhook: {e}"
            ) from e

    async def get_emails(self, inbox_id: str, limit: int = 10) -> List[EmailMessage]:
        """
        Get stored messages from Mailgun.

        Note: Requires message storage to be enabled in Mailgun account.

        Args:
            inbox_id: The inbox ID
            limit: Maximum emails to retrieve

        Returns:
            List of EmailMessage objects

        Raises:
            EmailRetrievalError: If retrieval fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.domain}/events"
                params = {
                    "event": "stored",
                    "limit": limit,
                    "recipient": f"workflow-{inbox_id}@{self.domain}",
                }

                async with session.get(url, auth=self.auth, params=params) as response:
                    if response.status >= 400:
                        logger.error(
                            f"{LOG_PREFIX_PROVIDER} Failed to get emails: {response.status}"
                        )
                        return []

                    data = await response.json()
                    emails = await self._process_stored_messages(session, data)

                    logger.info(f"{LOG_PREFIX_PROVIDER} Retrieved {len(emails)} emails")
                    return emails

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to get emails: {e}")
            raise EmailRetrievalError(f"Failed to retrieve emails: {e}") from e

    async def _process_stored_messages(
        self, session: aiohttp.ClientSession, data: Dict[str, Any]
    ) -> List[EmailMessage]:
        """Process stored message events."""
        emails = []
        for item in data.get("items", []):
            if "storage" in item and "url" in item["storage"]:
                message = await self._fetch_stored_message(
                    session, item["storage"]["url"]
                )
                if message:
                    emails.append(message)
        return emails

    async def _fetch_stored_message(
        self, session: aiohttp.ClientSession, storage_url: str
    ) -> Optional[EmailMessage]:
        """Fetch a stored message from Mailgun."""
        try:
            async with session.get(storage_url, auth=self.auth) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                return EmailMessage(
                    id=data.get("Message-Id", ""),
                    from_address=data.get("From", ""),
                    to_addresses=[data.get("To", "")],
                    subject=data.get("Subject", ""),
                    body=data.get("body-plain", ""),
                    html_body=data.get("body-html"),
                    received_at=datetime.utcnow(),
                )

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to fetch message: {e}")
            return None

    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        """
        Validate Mailgun webhook signature.

        Args:
            payload: The webhook payload
            signature: The signature (unused for Mailgun, uses payload data)
            secret: Optional secret (uses API key if not provided)

        Returns:
            True if signature is valid
        """
        try:
            data = json.loads(payload) if isinstance(payload, bytes) else payload

            timestamp = data.get("signature", {}).get("timestamp", "")
            token = data.get("signature", {}).get("token", "")
            provided_signature = data.get("signature", {}).get("signature", "")

            string_to_sign = f"{timestamp}{token}"

            expected_signature = hmac.new(
                self.api_key.encode(), string_to_sign.encode(), hashlib.sha256
            ).hexdigest()

            is_valid = hmac.compare_digest(provided_signature, expected_signature)

            if is_valid:
                logger.debug(f"{LOG_PREFIX_PROVIDER} Webhook signature valid")
            else:
                logger.warning(f"{LOG_PREFIX_PROVIDER} Webhook signature invalid")

            return is_valid

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to validate signature: {e}")
            return False
