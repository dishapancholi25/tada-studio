"""
Abstract base classes and protocols for email service providers.

Defines the contract that all email providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from ..schemas import EmailInbox, EmailMessage, EmailWebhook


@dataclass
class EmailAttachment:
    """An email attachment with binary content."""

    filename: str
    content: bytes
    mime_type: str


class EmailServiceProvider(ABC):
    """Abstract base class for email service providers."""

    @abstractmethod
    async def create_inbox(self, expires_in_minutes: int = 60) -> EmailInbox:
        """
        Create a temporary inbox for receiving emails.

        Args:
            expires_in_minutes: How long the inbox should remain active

        Returns:
            EmailInbox object with inbox details

        Raises:
            InboxCreationError: If inbox creation fails
        """
        pass

    @abstractmethod
    async def delete_inbox(self, inbox_id: str) -> bool:
        """
        Delete an inbox.

        Args:
            inbox_id: The inbox ID to delete

        Returns:
            True if successful, False otherwise

        Raises:
            InboxDeletionError: If deletion fails
        """
        pass

    @abstractmethod
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
        Send an email.

        Args:
            from_address: Sender email address
            to_address: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            reply_to: Optional reply-to address
            attachments: Optional list of file attachments

        Returns:
            Dict with send result (message_id, status, etc.)

        Raises:
            EmailSendError: If sending fails
        """
        pass

    @abstractmethod
    async def register_webhook(
        self, inbox_id: str, webhook_url: str, event_types: List[str] = None
    ) -> EmailWebhook:
        """
        Register a webhook for inbox events.

        Args:
            inbox_id: The inbox ID to monitor
            webhook_url: URL to send webhook notifications
            event_types: List of event types to monitor

        Returns:
            EmailWebhook object with registration details

        Raises:
            WebhookRegistrationError: If registration fails
        """
        pass

    @abstractmethod
    async def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook.

        Args:
            webhook_id: The webhook ID to unregister

        Returns:
            True if successful, False otherwise

        Raises:
            WebhookUnregistrationError: If unregistration fails
        """
        pass

    @abstractmethod
    async def get_emails(self, inbox_id: str, limit: int = 10) -> List[EmailMessage]:
        """
        Get emails from an inbox.

        Args:
            inbox_id: The inbox ID
            limit: Maximum number of emails to retrieve

        Returns:
            List of EmailMessage objects

        Raises:
            EmailRetrievalError: If retrieval fails
        """
        pass

    @abstractmethod
    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        """
        Validate webhook signature for security.

        Args:
            payload: The webhook payload
            signature: The signature to validate
            secret: Optional secret key for validation

        Returns:
            True if signature is valid, False otherwise
        """
        pass


class EmailProviderProtocol(Protocol):
    """
    Protocol defining the interface for email providers.

    This provides type checking for duck-typed providers without
    requiring explicit inheritance.
    """

    async def create_inbox(self, expires_in_minutes: int = 60) -> EmailInbox:
        """Create a temporary inbox."""
        ...

    async def delete_inbox(self, inbox_id: str) -> bool:
        """Delete an inbox."""
        ...

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
        """Send an email."""
        ...

    async def register_webhook(
        self, inbox_id: str, webhook_url: str, event_types: List[str] = None
    ) -> EmailWebhook:
        """Register a webhook."""
        ...

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        ...

    async def get_emails(self, inbox_id: str, limit: int = 10) -> List[EmailMessage]:
        """Get emails from inbox."""
        ...

    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        """Validate webhook signature."""
        ...
