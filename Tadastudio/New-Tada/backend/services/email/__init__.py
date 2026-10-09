"""Email service package.

This package provides comprehensive email service capabilities for workflows,
including sending emails, managing inboxes, webhook handling, and polling.

Basic Usage:
    from backend.services.email import get_email_manager

    # Get manager instance
    manager = get_email_manager()

    # Create inbox
    inbox = await manager.create_inbox(expires_in_minutes=60)

    # Send email
    result = await manager.send_email(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Hello",
        body="Email body"
    )

Key Features:
- Multiple provider support (Mailgun, MailSlurp)
- Async/await support throughout
- Type-safe operations with Pydantic schemas
- Custom exceptions for better error handling
- Workflow-tracked emails
- Webhook and polling support
- Modular architecture

Architecture:
- manager: High-level interface for email operations
- providers: Email service provider implementations (Mailgun, MailSlurp)
- polling: Email polling service for non-webhook scenarios
- schemas: Service-layer data models
- exceptions: Domain-specific errors
- utils: Shared utilities
- config: Configuration constants

Backwards Compatibility:
    # Old import style (still works)
    from backend.services.email import get_email_service
    email_service = get_email_service()

    # Old polling import (still works)
    from backend.services.email import email_polling_service
"""

# Exceptions
from .exceptions import (
    EmailConfigurationError,
    EmailError,
    EmailExtractionError,
    EmailInboxError,
    EmailPollingError,
    EmailPollingTimeoutError,
    EmailProviderError,
    EmailRetrievalError,
    EmailSendError,
    InboxCreationError,
    InboxDeletionError,
    InboxNotFoundError,
    WebhookError,
    WebhookRegistrationError,
    WebhookUnregistrationError,
    WebhookValidationError,
    WorkflowResumptionError,
)

# Main API
from .manager import get_email_service  # Backwards compatibility
from .manager import initialize_email_service  # Backwards compatibility
from .manager import EmailManager, get_email_manager, reset_email_manager

# Polling
from .polling import email_polling_service  # Backwards compatibility
from .polling import (
    EmailPollingService,
    EmailResponseProcessor,
    get_email_polling_service,
)

# Providers
from .providers import (
    EmailProviderProtocol,
    EmailServiceFactory,
    EmailServiceProvider,
    MailgunProvider,
    MailSlurpProvider,
)

# Schemas
from .schemas import (
    EmailExtractionConfig,
    EmailInbox,
    EmailMessage,
    EmailPollingConfig,
    EmailProviderConfig,
    EmailSendRequest,
    EmailWebhook,
    WebhookPayload,
    WorkflowEmailRequest,
)

# Utils
from .utils import (
    extract_email_content,
    extract_workflow_id_from_email,
    format_email_address,
    sanitize_subject,
    validate_email_address,
)


__all__ = [
    # Main API
    "EmailManager",
    "get_email_manager",
    "reset_email_manager",
    "get_email_service",  # Backwards compatibility
    "initialize_email_service",  # Backwards compatibility
    # Providers
    "EmailServiceProvider",
    "EmailProviderProtocol",
    "MailgunProvider",
    "MailSlurpProvider",
    "EmailServiceFactory",
    # Polling
    "EmailPollingService",
    "get_email_polling_service",
    "email_polling_service",  # Backwards compatibility
    "EmailResponseProcessor",
    # Schemas
    "EmailInbox",
    "EmailMessage",
    "EmailWebhook",
    "EmailSendRequest",
    "WorkflowEmailRequest",
    "EmailExtractionConfig",
    "WebhookPayload",
    "EmailPollingConfig",
    "EmailProviderConfig",
    # Exceptions
    "EmailError",
    "EmailProviderError",
    "EmailInboxError",
    "InboxCreationError",
    "InboxDeletionError",
    "InboxNotFoundError",
    "EmailSendError",
    "EmailRetrievalError",
    "WebhookError",
    "WebhookRegistrationError",
    "WebhookUnregistrationError",
    "WebhookValidationError",
    "EmailExtractionError",
    "EmailConfigurationError",
    "EmailPollingError",
    "EmailPollingTimeoutError",
    "WorkflowResumptionError",
    # Utils
    "extract_email_content",
    "extract_workflow_id_from_email",
    "validate_email_address",
    "format_email_address",
    "sanitize_subject",
]
