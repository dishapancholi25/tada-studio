"""
Remote email relay provider implementation.

Sends email by forwarding requests to another Agentic Studio deployment
that has a configured email provider (e.g., Outlook with Graph API).
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

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


class RemoteProvider(EmailServiceProvider):
    """Email provider that relays send requests to a remote Agentic Studio deployment."""

    def __init__(self, remote_url: str = None, api_key: str = None):
        """
        Initialize the remote email relay provider.

        Args:
            remote_url: Base URL of the remote deployment (e.g., https://agenticstudio.example.com)
            api_key: API key for authenticating with the remote relay endpoint

        Raises:
            EmailConfigurationError: If required configuration is missing
        """
        if not remote_url:
            raise EmailConfigurationError(
                "remote_url is required for remote email provider. "
                "Set the REMOTE_EMAIL_URL environment variable."
            )
        if not api_key:
            raise EmailConfigurationError(
                "api_key is required for remote email provider. "
                "Set the REMOTE_EMAIL_API_KEY environment variable."
            )

        self.remote_url = remote_url.rstrip("/")
        self.api_key = api_key
        self.relay_endpoint = f"{self.remote_url}/api/email/relay"
        # The remote deployment's provider determines the actual sender.
        # This placeholder satisfies the handler's from_address resolution.
        self.sender_email = "relay@remote"

        logger.info(
            f"{LOG_PREFIX_PROVIDER} Initialized remote email provider "
            f"targeting {self.remote_url}"
        )

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
        Send an email by relaying to the remote deployment.

        Args:
            from_address: Sender email address
            to_address: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            reply_to: Optional reply-to address

        Returns:
            Dict with send result from the remote deployment

        Raises:
            EmailSendError: If the relay request fails
        """
        payload = {
            "from_address": from_address,
            "recipient": to_address,
            "subject": subject,
            "body": body,
        }
        if html_body:
            payload["html_body"] = html_body
        if reply_to:
            payload["reply_to"] = reply_to

        headers = {"X-Email-API-Key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.relay_endpoint,
                    json=payload,
                    headers=headers,
                )

            if response.status_code == 403:
                raise EmailSendError(
                    "Remote relay rejected the API key. "
                    "Check REMOTE_EMAIL_API_KEY matches the key configured on the remote deployment."
                )

            if response.status_code != 200:
                raise EmailSendError(
                    f"Remote relay returned status {response.status_code}: {response.text}"
                )

            result = response.json()
            logger.info(
                f"{LOG_PREFIX_PROVIDER} Email relayed successfully to {to_address} "
                f"via {self.remote_url}"
            )
            return result.get("result", result)

        except httpx.ConnectError as e:
            raise EmailSendError(
                f"Failed to connect to remote relay at {self.relay_endpoint}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise EmailSendError(
                f"Timeout connecting to remote relay at {self.relay_endpoint}: {e}"
            ) from e
        except EmailSendError:
            raise
        except Exception as e:
            raise EmailSendError(
                f"Failed to relay email via {self.relay_endpoint}: {e}"
            ) from e

    async def create_inbox(self, expires_in_minutes: int = 60) -> EmailInbox:
        raise InboxCreationError(
            "Inbox creation not supported by remote email provider"
        )

    async def delete_inbox(self, inbox_id: str) -> bool:
        raise InboxDeletionError(
            "Inbox deletion not supported by remote email provider"
        )

    async def register_webhook(
        self, inbox_id: str, webhook_url: str, event_types: List[str] = None
    ) -> EmailWebhook:
        raise WebhookRegistrationError(
            "Webhook registration not supported by remote email provider"
        )

    async def unregister_webhook(self, webhook_id: str) -> bool:
        raise WebhookUnregistrationError(
            "Webhook unregistration not supported by remote email provider"
        )

    async def get_emails(self, inbox_id: str, limit: int = 10) -> List[EmailMessage]:
        raise EmailRetrievalError(
            "Email retrieval not supported by remote email provider"
        )

    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        logger.warning(
            f"{LOG_PREFIX_PROVIDER} Webhook signature validation not supported by remote provider"
        )
        return False
