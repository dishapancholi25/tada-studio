"""HTTP Execution API Module.

This module provides REST API endpoints for HTTP-triggered workflow execution,
including:
- Workflow execution via JSON or form data
- Real-time execution streaming via Server-Sent Events (SSE)
- Checkpoint pause/resume functionality
- Execution status tracking

The module follows clean architecture with separation between:
- Routes: FastAPI endpoint definitions
- Models: Pydantic request/response models
- Handlers: Business logic for execution, checkpoints, SSE, and file uploads
- Services: Authentication and execution tracking
- Utils: Helper functions for request processing and output extraction
- Exceptions: Custom exception types for error handling

Example usage:
    from backend.api.http_execution import router
    app.include_router(router)
"""

from .routes import router


# Export the router for app registration
__all__ = ["router"]
