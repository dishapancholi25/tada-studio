"""
Custom exceptions for email service operations.

This module defines a hierarchy of exceptions for email-related errors,
providing better error handling and debugging capabilities.
"""


class EmailError(Exception):
    """Base exception for all email-related errors."""

    pass


class EmailProviderError(EmailError):
    """Base exception for email provider-specific errors."""

    pass


class EmailInboxError(EmailError):
    """Errors related to inbox operations."""

    pass


class InboxCreationError(EmailInboxError):
    """Failed to create email inbox."""

    pass


class InboxDeletionError(EmailInboxError):
    """Failed to delete email inbox."""

    pass


class InboxNotFoundError(EmailInboxError):
    """Email inbox not found."""

    pass


class EmailSendError(EmailError):
    """Errors related to sending emails."""

    pass


class EmailRetrievalError(EmailError):
    """Failed to retrieve emails from inbox."""

    pass


class WebhookError(EmailError):
    """Errors related to webhook operations."""

    pass


class WebhookRegistrationError(WebhookError):
    """Failed to register webhook."""

    pass


class WebhookUnregistrationError(WebhookError):
    """Failed to unregister webhook."""

    pass


class WebhookValidationError(WebhookError):
    """Webhook signature validation failed."""

    pass


class EmailExtractionError(EmailError):
    """Failed to extract content from email."""

    pass


class EmailConfigurationError(EmailError):
    """Email service configuration error."""

    pass


class EmailPollingError(EmailError):
    """Errors during email polling operations."""

    pass


class EmailPollingTimeoutError(EmailPollingError):
    """Email polling timed out waiting for response."""

    pass


class WorkflowResumptionError(EmailError):
    """Failed to resume workflow from email response."""

    pass
