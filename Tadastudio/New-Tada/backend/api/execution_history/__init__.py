"""Execution history API package.

This package provides REST API endpoints for querying workflow execution history,
including graph executions, node executions, and execution statistics.

Modules:
    - routes: API endpoint definitions
    - models: Pydantic response models
    - dependencies: Authentication and user context dependencies

Usage:
    >>> from backend.api.execution_history import router
    >>> app.include_router(router)
"""

from .routes import router


__all__ = ["router"]
