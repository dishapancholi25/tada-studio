"""User settings API module.

This package provides REST API endpoints for managing user-specific
settings, including external service configurations like Tavily API keys.

Routers:
    router: Main user settings router

Example:
    >>> from backend.api.user_settings import router
    >>> app.include_router(router)
"""

from .routes import router


__all__ = [
    "router",
]
