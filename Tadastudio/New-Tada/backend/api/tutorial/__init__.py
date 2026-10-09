"""Tutorial API module.

Provides endpoints for retrieving and saving tutorial step overrides
(admin-customizable positions and text).

Example:
    from backend.api.tutorial import router
    app.include_router(router)
"""

from .routes import router

__all__ = ["router"]
