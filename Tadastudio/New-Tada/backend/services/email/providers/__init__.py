"""Email service providers package."""

from .base import EmailProviderProtocol, EmailServiceProvider
from .factory import EmailServiceFactory
from .mailgun import MailgunProvider
from .mailslurp import MailSlurpProvider
from .outlook import OutlookProvider


__all__ = [
    "EmailServiceProvider",
    "EmailProviderProtocol",
    "MailgunProvider",
    "MailSlurpProvider",
    "OutlookProvider",
    "EmailServiceFactory",
]
