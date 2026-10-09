"""
MailSlurp email service provider implementation.

Supports sending and receiving emails using MailSlurp API.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from ..config import LOG_PREFIX_PROVIDER, MAILSLURP_API_KEY, MAILSLURP_BASE_URL
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


class MailSlurpProvider(EmailServiceProvider):
    """MailSlurp implementation of email service provider."""

    def __init__(self, api_key: str = None):
        """
        Initialize MailSlurp provider.

        Args:
            api_key: MailSlurp API key (defaults to env variable)

        Raises:
            EmailConfigurationError: If API key is missing
        """
        self.api_key = api_key or MAILSLURP_API_KEY
        if not self.api_key:
            raise EmailConfigurationError("MailSlurp API key is required")

        self.base_url = MAILSLURP_BASE_URL
        self.headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}

        logger.info(f"{LOG_PREFIX_PROVIDER} Initialized MailSlurp provider")

    async def create_inbox(self, expires_in_minutes: int = 60) -> EmailInbox:
        """
        Create a temporary MailSlurp inbox.

        Args:
            expires_in_minutes: How long the inbox should remain active

        Returns:
            EmailInbox with created inbox details

        Raises:
            InboxCreationError: If inbox creation fails
        """
        try:
            expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)

            async with aiohttp.ClientSession() as session:
                params = {
                    "expiresIn": expires_in_minutes * 60 * 1000,  # milliseconds
                    "inboxType": "SMTP_INBOX",
                }

                async with session.post(
                    f"{self.base_url}/inboxes", headers=self.headers, params=params
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    logger.info(
                        f"{LOG_PREFIX_PROVIDER} Created MailSlurp inbox: {data['emailAddress']}"
                    )

                    return EmailInbox(
                        inbox_id=data["id"],
                        email_address=data["emailAddress"],
                        created_at=datetime.utcnow(),
                        expires_at=expires_at,
                        metadata={"mailslurp_data": data},
                    )
        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to create MailSlurp inbox: {e}")
            raise InboxCreationError(f"Failed to create MailSlurp inbox: {e}") from e

    async def delete_inbox(self, inbox_id: str) -> bool:
        """
        Delete a MailSlurp inbox.

        Args:
            inbox_id: The inbox ID to delete

        Returns:
            True if successful

        Raises:
            InboxDeletionError: If deletion fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/inboxes/{inbox_id}", headers=self.headers
                ) as response:
                    success = response.status == 204

                    if success:
                        logger.info(
                            f"{LOG_PREFIX_PROVIDER} Deleted MailSlurp inbox: {inbox_id}"
                        )
                    else:
                        logger.warning(
                            f"{LOG_PREFIX_PROVIDER} Failed to delete inbox: {inbox_id}"
                        )

                    return success
        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to delete MailSlurp inbox: {e}")
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
        Send an email via MailSlurp POST /emails endpoint.

        Uses useDomainPool=true so MailSlurp auto-assigns a sending inbox
        when no specific inboxId is provided.

        Args:
            from_address: Sender email (optional, MailSlurp assigns one if empty)
            to_address: Recipient email
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            reply_to: Optional reply-to address

        Returns:
            Send result dict

        Raises:
            EmailSendError: If sending fails
        """
        try:
            payload = {
                "to": [to_address],
                "subject": subject,
                "body": html_body or body,
                "isHTML": bool(html_body),
            }
            if from_address:
                payload["from"] = from_address
            if reply_to:
                payload["replyTo"] = reply_to

            params = {"useDomainPool": "true"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/emails",
                    headers=self.headers,
                    json=payload,
                    params=params,
                ) as response:
                    if not response.ok:
                        error_body = await response.text()
                        logger.error(
                            f"{LOG_PREFIX_PROVIDER} MailSlurp API error {response.status}: {error_body}"
                        )
                        response.raise_for_status()

                    result = await response.json()
                    logger.info(f"{LOG_PREFIX_PROVIDER} Email sent to {to_address}")
                    return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to send email: {e}")
            raise EmailSendError(f"Failed to send email via MailSlurp: {e}") from e

    async def send_email_from_inbox(
        self,
        inbox_id: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email from a specific MailSlurp inbox.

        Args:
            inbox_id: The inbox ID to send from
            to_address: Recipient email
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body

        Returns:
            Send result dict

        Raises:
            EmailSendError: If sending fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "to": [to_address],
                    "subject": subject,
                    "body": html_body or body,
                    "isHTML": bool(html_body),
                }

                url = f"{self.base_url}/inboxes/{inbox_id}"

                logger.info(
                    f"{LOG_PREFIX_PROVIDER} Sending from inbox {inbox_id} to {to_address}"
                )

                async with session.post(
                    url, headers=self.headers, json=payload
                ) as response:
                    if response.status == 404:
                        error_text = await response.text()
                        logger.error(
                            f"{LOG_PREFIX_PROVIDER} 404 Error - Inbox not found: {error_text}"
                        )
                        raise EmailSendError(f"Inbox not found: {inbox_id}")

                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        result = await response.json()
                        logger.info(
                            f"{LOG_PREFIX_PROVIDER} Email sent: {result.get('id', 'no-id')}"
                        )
                        return result
                    else:
                        logger.info(
                            f"{LOG_PREFIX_PROVIDER} Email sent (status: {response.status})"
                        )
                        return {"success": True, "status": response.status}

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to send from inbox: {e}")
            raise EmailSendError(f"Failed to send from MailSlurp inbox: {e}") from e

    async def register_webhook(
        self, inbox_id: str, webhook_url: str, event_types: List[str] = None
    ) -> EmailWebhook:
        """
        Register a webhook for MailSlurp inbox events.

        Args:
            inbox_id: The inbox ID to monitor
            webhook_url: URL to send notifications
            event_types: Event types (defaults to NEW_EMAIL events)

        Returns:
            EmailWebhook with registration details

        Raises:
            WebhookRegistrationError: If registration fails
        """
        try:
            if event_types is None:
                event_types = ["NEW_EMAIL", "EMAIL_READ", "EMAIL_OPENED"]

            webhook_ids = []

            async with aiohttp.ClientSession() as session:
                for event_type in event_types:
                    payload = {
                        "url": webhook_url,
                        "eventName": event_type,
                        "inboxId": inbox_id,
                        "useStaticIpRange": False,
                        "includeHeaders": {
                            "X-Webhook-Event": event_type,
                            "X-Inbox-Id": inbox_id,
                        },
                    }

                    async with session.post(
                        f"{self.base_url}/webhooks", headers=self.headers, json=payload
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        webhook_ids.append(data["id"])

                logger.info(f"{LOG_PREFIX_PROVIDER} Registered webhooks: {webhook_ids}")

                return EmailWebhook(
                    webhook_id=webhook_ids[0] if webhook_ids else "",
                    inbox_id=inbox_id,
                    url=webhook_url,
                    event_types=event_types,
                    created_at=datetime.utcnow(),
                )

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to register webhook: {e}")
            raise WebhookRegistrationError(
                f"Failed to register MailSlurp webhook: {e}"
            ) from e

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a MailSlurp webhook.

        Args:
            webhook_id: The webhook ID to unregister

        Returns:
            True if successful

        Raises:
            WebhookUnregistrationError: If unregistration fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/webhooks/{webhook_id}", headers=self.headers
                ) as response:
                    success = response.status == 204

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
        Get emails from a MailSlurp inbox.

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
                params = {"size": limit, "sort": "DESC"}

                async with session.get(
                    f"{self.base_url}/inboxes/{inbox_id}/emails",
                    headers=self.headers,
                    params=params,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    emails = self._parse_email_list(data)

                    logger.info(f"{LOG_PREFIX_PROVIDER} Retrieved {len(emails)} emails")
                    return emails

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to get emails: {e}")
            raise EmailRetrievalError(f"Failed to get emails: {e}") from e

    def _parse_email_list(self, data: Dict[str, Any]) -> List[EmailMessage]:
        """Parse MailSlurp email list response."""
        emails = []
        for email_data in data.get("content", []):
            emails.append(
                EmailMessage(
                    id=email_data["id"],
                    from_address=email_data.get("from", ""),
                    to_addresses=email_data.get("to", []),
                    subject=email_data.get("subject", ""),
                    body=email_data.get("body", ""),
                    html_body=email_data.get("bodyHTML"),
                    received_at=datetime.fromisoformat(
                        email_data["createdAt"].replace("Z", "+00:00")
                    )
                    if email_data.get("createdAt")
                    else None,
                )
            )
        return emails

    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        """
        Validate MailSlurp webhook signature.

        Args:
            payload: The webhook payload
            signature: The signature to validate
            secret: Secret key for validation

        Returns:
            True if signature is valid
        """
        try:
            if not secret:
                logger.warning(
                    f"{LOG_PREFIX_PROVIDER} No secret provided for signature validation"
                )
                return True  # Skip validation if no secret

            expected_signature = hmac.new(
                secret.encode(), payload, hashlib.sha256
            ).hexdigest()

            is_valid = hmac.compare_digest(signature, expected_signature)

            if is_valid:
                logger.debug(f"{LOG_PREFIX_PROVIDER} Webhook signature valid")
            else:
                logger.warning(f"{LOG_PREFIX_PROVIDER} Webhook signature invalid")

            return is_valid

        except Exception as e:
            logger.error(f"{LOG_PREFIX_PROVIDER} Failed to validate signature: {e}")
            return False
