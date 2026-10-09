"""Email polling package."""

from .processor import EmailResponseProcessor
from .service import (
    EmailPollingService,
    email_polling_service,
    get_email_polling_service,
)


__all__ = [
    "EmailPollingService",
    "get_email_polling_service",
    "email_polling_service",
    "EmailResponseProcessor",
]
