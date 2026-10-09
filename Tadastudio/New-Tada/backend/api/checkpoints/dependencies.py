"""FastAPI dependencies for checkpoint endpoints.

This module provides dependency functions for checkpoint API endpoints,
including validation and dependency injection for execution engine access.
"""

from typing import Any

from fastapi import HTTPException

from backend.services.dependency_injection import get_execution_engine


def require_langgraph_engine() -> bool:
    """Dependency to ensure execution engine supports checkpoints.

    This function validates that the execution engine has checkpoint support.
    Currently, all execution engines support checkpoints, so this always returns True.
    The function is maintained for backward compatibility and future extensibility.

    Returns:
        bool: Always True, indicating checkpoint support is available.

    Example:
        >>> @router.get("/endpoint", dependencies=[Depends(require_langgraph_engine)])
        >>> async def my_endpoint():
        ...     pass
    """
    # The execution engine always supports checkpoints now
    # This function is kept for backward compatibility
    return True


def get_engine_with_checkpoint_support() -> Any:
    """Get execution engine and verify it supports checkpoints.

    This dependency retrieves the execution engine and validates that it has
    the required checkpoint methods (get_checkpoints, resume_from_checkpoint).

    Returns:
        ExecutionEngine: The execution engine instance.

    Raises:
        HTTPException: If engine doesn't support checkpoint operations.

    Example:
        >>> @router.get("/endpoint")
        >>> async def my_endpoint(engine = Depends(get_engine_with_checkpoint_support)):
        ...     checkpoints = engine.get_checkpoints(thread_id)
    """
    engine = get_execution_engine()

    # Verify checkpoint support
    if not hasattr(engine, "get_checkpoints") or not hasattr(
        engine, "resume_from_checkpoint"
    ):
        raise HTTPException(
            status_code=501,
            detail="Current execution engine does not support checkpoints",
        )

    return engine
