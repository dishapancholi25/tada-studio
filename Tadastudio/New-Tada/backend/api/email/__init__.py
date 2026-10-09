"""Email API module.

This module provides REST API endpoints for email management including:
- Creating and managing email inboxes
- Sending emails from checkpoints
- Webhook callbacks for email responses
- Email checkpoint status tracking

The module follows clean architecture with separation between:
- Routes: FastAPI endpoint definitions
- Models: Pydantic request/response models
- Dependencies: Dependency injection
- Handlers: Business logic for webhooks and resumption

Example usage:
    from backend.api.email import router
    app.include_router(router)
"""

from .routes import router


__all__ = ["router"]
