"""Authentication API module.

This package provides REST API endpoints for user authentication,
including login, registration, and user profile retrieval.

Routers:
    router: Main authentication router (login, register, /me)

Dependencies:
    get_current_user: FastAPI dependency for authenticating requests

Example:
    >>> # Include authentication router in FastAPI app
    >>> from backend.api.auth import router
    >>>
    >>> app.include_router(router)
"""

from .dependencies import get_current_user
from .routes import router


__all__ = [
    "router",
    "get_current_user",
]
