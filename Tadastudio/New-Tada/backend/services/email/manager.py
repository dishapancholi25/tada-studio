"""
High-level email service manager.

Provides a unified interface for email operations across different providers.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from backend.models.email import EmailInboxOwnership, EmailWebhookOwnership
from backend.services.database import get_db

from .config import LOG_PREFIX_EMAIL
from .exceptions import (
    EmailInboxError,
    InboxCreationError,
    InboxDeletionError,
    WebhookError,
    WebhookRegistrationError,
    WebhookUnregistrationError,
)
from .providers import EmailServiceFactory, EmailServiceProvider
from .schemas import EmailInbox, EmailMessage, EmailWebhook

logger = logging.getLogger(__name__)


class EmailManager:
    """
    High-level manager for email service operations.

    Provides a unified interface for sending emails, managing inboxes,
    and handling webhooks across different email providers.
    """

    def __init__(self, provider: EmailServiceProvider = None):
        """
        Initialize email manager.

        Args:
            provider: EmailServiceProvider instance (defaults to factory-created provider)
        """
        self._provider = provider or EmailServiceFactory.create_provider()
        logger.info(
            f"{LOG_PREFIX_EMAIL} Email manager initialized with "
            f"provider: {self._provider.__class__.__name__}"
        )

    @property
    def provider(self) -> EmailServiceProvider:
        """Get the current email provider."""
        return self._provider

    async def create_inbox(
        self, expires_in_minutes: int = 60, owner_id: Optional[str] = None
    ) -> EmailInbox:
        """
        Create a temporary email inbox.

        Args:
            expires_in_minutes: How long the inbox should remain active

        Returns:
            EmailInbox with inbox details

        Raises:
            InboxCreationError: If inbox creation fails
        """
        logger.info(
            f"{LOG_PREFIX_EMAIL} Creating inbox (expires in {expires_in_minutes}m)"
        )
        inbox = await self._provider.create_inbox(expires_in_minutes)
        inbox.owner_id = owner_id
        if owner_id is not None:
            try:
                with get_db() as db:
                    db.merge(
                        EmailInboxOwnership(
                            inbox_id=inbox.inbox_id,
                            owner_id=owner_id,
                        )
                    )
            except SQLAlchemyError as e:
                logger.error(
                    "%s Failed to persist inbox ownership for %s: %s",
                    LOG_PREFIX_EMAIL,
                    inbox.inbox_id,
                    e,
                )
                raise InboxCreationError(
                    f"Failed to persist inbox ownership for {inbox.inbox_id}"
                ) from e
        return inbox

    async def delete_inbox(self, inbox_id: str) -> bool:
        """
        Delete an email inbox.

        Args:
            inbox_id: The inbox ID to delete

        Returns:
            True if successful

        Raises:
            InboxDeletionError: If deletion fails
        """
        logger.info(f"{LOG_PREFIX_EMAIL} Deleting inbox: {inbox_id}")
        success = await self._provider.delete_inbox(inbox_id)
        if success:
            try:
                with get_db() as db:
                    ownership = (
                        db.query(EmailInboxOwnership)
                        .filter(EmailInboxOwnership.inbox_id == inbox_id)
                        .first()
                    )
                    if ownership:
                        db.delete(ownership)
            except SQLAlchemyError as e:
                logger.error(
                    "%s Failed to delete inbox ownership for %s: %s",
                    LOG_PREFIX_EMAIL,
                    inbox_id,
                    e,
                )
                raise InboxDeletionError(
                    f"Failed to delete inbox ownership for {inbox_id}"
                ) from e
        return success

    async def send_email(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
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

        Returns:
            Send result dict

        Raises:
            EmailSendError: If sending fails
        """
        logger.info(
            f"{LOG_PREFIX_EMAIL} Sending email from {from_address} to {to_address}"
        )
        return await self._provider.send_email(
            from_address, to_address, subject, body, html_body, reply_to
        )

    async def send_workflow_email(
        self,
        workflow_id: str,
        execution_id: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a workflow-tracked email (if provider supports it).

        Args:
            workflow_id: Workflow ID
            execution_id: Execution ID
            to_address: Recipient email
            subject: Email subject
            body: Email body
            html_body: Optional HTML body

        Returns:
            Send result with workflow tracking info

        Raises:
            EmailSendError: If sending fails
        """
        logger.info(
            f"{LOG_PREFIX_EMAIL} Sending workflow email "
            f"(execution: {execution_id}) to {to_address}"
        )

        # Check if provider has workflow support
        if hasattr(self._provider, "send_email_with_workflow_id"):
            return await self._provider.send_email_with_workflow_id(
                workflow_id, execution_id, to_address, subject, body, html_body
            )

        # Fallback to regular send
        logger.warning(
            f"{LOG_PREFIX_EMAIL} Provider doesn't support workflow tracking, "
            "using regular send"
        )
        return await self.send_email(
            from_address="noreply@nexusagent.ai",
            to_address=to_address,
            subject=subject,
            body=body,
            html_body=html_body,
        )

    async def register_webhook(
        self,
        inbox_id: str,
        webhook_url: str,
        event_types: List[str] = None,
        owner_id: Optional[str] = None,
    ) -> EmailWebhook:
        """
        Register a webhook for email notifications.

        Args:
            inbox_id: Inbox ID to monitor
            webhook_url: URL for webhook notifications
            event_types: Event types to monitor

        Returns:
            EmailWebhook with registration details

        Raises:
            WebhookRegistrationError: If registration fails
        """
        logger.info(f"{LOG_PREFIX_EMAIL} Registering webhook for inbox: {inbox_id}")
        webhook = await self._provider.register_webhook(
            inbox_id, webhook_url, event_types
        )
        webhook.owner_id = owner_id
        if owner_id is not None:
            try:
                with get_db() as db:
                    db.merge(
                        EmailWebhookOwnership(
                            webhook_id=webhook.webhook_id,
                            owner_id=owner_id,
                            inbox_id=inbox_id,
                        )
                    )
            except SQLAlchemyError as e:
                logger.error(
                    "%s Failed to persist webhook ownership for %s: %s",
                    LOG_PREFIX_EMAIL,
                    webhook.webhook_id,
                    e,
                )
                raise WebhookRegistrationError(
                    f"Failed to persist webhook ownership for {webhook.webhook_id}"
                ) from e
        return webhook

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook.

        Args:
            webhook_id: Webhook ID to unregister

        Returns:
            True if successful

        Raises:
            WebhookUnregistrationError: If unregistration fails
        """
        logger.info(f"{LOG_PREFIX_EMAIL} Unregistering webhook: {webhook_id}")
        success = await self._provider.unregister_webhook(webhook_id)
        if success:
            try:
                with get_db() as db:
                    ownership = (
                        db.query(EmailWebhookOwnership)
                        .filter(EmailWebhookOwnership.webhook_id == webhook_id)
                        .first()
                    )
                    if ownership:
                        db.delete(ownership)
            except SQLAlchemyError as e:
                logger.error(
                    "%s Failed to delete webhook ownership for %s: %s",
                    LOG_PREFIX_EMAIL,
                    webhook_id,
                    e,
                )
                raise WebhookUnregistrationError(
                    f"Failed to delete webhook ownership for {webhook_id}"
                ) from e
        return success

    def get_inbox_owner(self, inbox_id: str) -> Optional[str]:
        """Return recorded inbox owner, or None for unknown/legacy inboxes."""
        try:
            with get_db() as db:
                ownership = (
                    db.query(EmailInboxOwnership.owner_id)
                    .filter(EmailInboxOwnership.inbox_id == inbox_id)
                    .first()
                )
                return ownership[0] if ownership else None
        except SQLAlchemyError as e:
            logger.error(
                "%s Failed to read inbox ownership for %s: %s",
                LOG_PREFIX_EMAIL,
                inbox_id,
                e,
            )
            raise EmailInboxError(
                f"Failed to read inbox ownership for {inbox_id}"
            ) from e

    def get_webhook_owner(self, webhook_id: str) -> Optional[str]:
        """Return recorded webhook owner, or None for unknown/legacy webhooks."""
        try:
            with get_db() as db:
                ownership = (
                    db.query(EmailWebhookOwnership.owner_id)
                    .filter(EmailWebhookOwnership.webhook_id == webhook_id)
                    .first()
                )
                return ownership[0] if ownership else None
        except SQLAlchemyError as e:
            logger.error(
                "%s Failed to read webhook ownership for %s: %s",
                LOG_PREFIX_EMAIL,
                webhook_id,
                e,
            )
            raise WebhookError(
                f"Failed to read webhook ownership for {webhook_id}"
            ) from e

    async def get_emails(self, inbox_id: str, limit: int = 10) -> List[EmailMessage]:
        """
        Get emails from an inbox.

        Args:
            inbox_id: Inbox ID
            limit: Maximum number of emails to retrieve

        Returns:
            List of EmailMessage objects

        Raises:
            EmailRetrievalError: If retrieval fails
        """
        logger.info(f"{LOG_PREFIX_EMAIL} Retrieving emails from inbox: {inbox_id}")
        return await self._provider.get_emails(inbox_id, limit)

    def validate_webhook_signature(
        self, payload: bytes, signature: str, secret: str = None
    ) -> bool:
        """
        Validate webhook signature.

        Args:
            payload: Webhook payload
            signature: Signature to validate
            secret: Optional secret key

        Returns:
            True if signature is valid
        """
        return self._provider.validate_webhook_signature(payload, signature, secret)


# Singleton instance
_email_manager: Optional[EmailManager] = None


def get_email_manager(provider: EmailServiceProvider = None) -> EmailManager:
    """
    Get the email manager instance (singleton).

    Args:
        provider: Optional provider to use (only for first initialization)

    Returns:
        EmailManager instance
    """
    global _email_manager

    if _email_manager is None:
        _email_manager = EmailManager(provider)
        logger.info(f"{LOG_PREFIX_EMAIL} Email manager singleton created")

    return _email_manager


def reset_email_manager():
    """Reset the email manager singleton (useful for testing)."""
    global _email_manager
    _email_manager = None
    logger.info(
        "%s Email manager singleton reset; persistent ownership rows are unchanged",
        LOG_PREFIX_EMAIL,
    )


# Backwards compatibility - provide get_email_service alias
def get_email_service() -> EmailServiceProvider:
    """
    Get the email service provider (backwards compatibility).

    Returns:
        EmailServiceProvider instance
    """
    return get_email_manager().provider


def initialize_email_service(provider_name: str = None):
    """
    Initialize the email service with a specific provider (backwards compatibility).

    Args:
        provider_name: Provider name to use
    """
    global _email_manager
    provider = EmailServiceFactory.create_provider(provider_name)
    _email_manager = EmailManager(provider)
    logger.info(
        f"{LOG_PREFIX_EMAIL} Email service initialized with provider: "
        f"{provider_name or 'default'}"
    )
