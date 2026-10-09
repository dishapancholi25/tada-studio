"""
Monitoring API module.

This module provides comprehensive monitoring capabilities including:
- Health checks (basic and detailed)
- System metrics and monitoring
- Diagnostics and component checks
- Feature flag status
- Cache management
- Performance optimization

The module follows a clean architecture with separation between:
- Routes: FastAPI endpoint definitions
- Services: Business logic and operations
- Models: Pydantic response models
- Utils: Shared utilities and helpers

Example usage:
    from backend.api.monitoring import router
    app.include_router(router)
"""

from .routes import router


__all__ = ["router"]
