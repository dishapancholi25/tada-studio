"""Email ORM models."""

from .ownership import EmailInboxOwnership, EmailWebhookOwnership

__all__ = ["EmailInboxOwnership", "EmailWebhookOwnership"]
