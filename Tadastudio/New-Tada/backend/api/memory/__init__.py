"""Memory API module.

This module provides REST API endpoints for memory management including:
- Creating and retrieving agent memories
- Managing conversation history
- Agent memory profiles
- Memory pruning and cleanup

The module follows clean architecture with separation between:
- Routes: FastAPI endpoint definitions
- Models: Pydantic request/response models
- Dependencies: Dependency injection

Example usage:
    from backend.api.memory import router
    app.include_router(router)
"""

from .routes import router


__all__ = ["router"]
