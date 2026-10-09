"""Model deployments API module.

This module provides REST API endpoints for managing LLM model deployments,
including CRUD operations and connection testing.

The module follows FastAPI best practices with:
- Routes: API endpoint definitions
- Schemas: Pydantic request/response models
- Dependencies: FastAPI dependency injection

Example usage:
    from backend.api.model_deployments import router
    app.include_router(router)
"""

from .routes import router


__all__ = ["router"]
