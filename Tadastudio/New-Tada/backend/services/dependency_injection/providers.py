"""
FastAPI dependency providers for dependency injection.

This module provides FastAPI-compatible dependency provider functions
that can be used with the Depends() pattern in route handlers.
"""

from typing import Annotated

from fastapi import Depends, HTTPException

from ..config import get_logger
from .container import _container
from .exceptions import DependencyNotInitializedError
from .types import ExecutionEngineProtocol, GraphManagerProtocol


logger = get_logger("dependency_providers")


def get_graph_manager() -> GraphManagerProtocol:
    """
    Provide FastAPI dependency for GraphManager.

    This function can be used as a FastAPI dependency to inject the
    GraphManager instance into route handlers.

    Usage:
        @router.get("/graphs")
        async def list_graphs(
            graph_mgr: Annotated[GraphManagerProtocol, Depends(get_graph_manager)]
        ):
            return graph_mgr.list_graphs()

        # Or with the convenience type alias:
        from backend.services.dependency_injection import GraphManager

        @router.get("/graphs")
        async def list_graphs(graph_mgr: GraphManager):
            return graph_mgr.list_graphs()

    Returns:
        GraphManagerProtocol: The initialized GraphManager instance

    Raises:
        HTTPException: 503 Service Unavailable if GraphManager not initialized
    """
    try:
        manager = _container.graph_manager
        return manager
    except DependencyNotInitializedError as e:
        logger.error(
            f"[DEPENDENCY-PROVIDER] GraphManager access failed: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "GraphManager not available. "
                "Service may be starting up or initialization failed."
            ),
        ) from e


def get_execution_engine() -> ExecutionEngineProtocol:
    """
    Provide FastAPI dependency for ExecutionEngine.

    This function can be used as a FastAPI dependency to inject the
    ExecutionEngine instance into route handlers.

    Usage:
        @router.post("/execute")
        async def execute_workflow(
            engine: Annotated[ExecutionEngineProtocol, Depends(get_execution_engine)]
        ):
            await engine.execute_graph(...)

        # Or with the convenience type alias:
        from backend.services.dependency_injection import ExecutionEngine

        @router.post("/execute")
        async def execute_workflow(engine: ExecutionEngine):
            await engine.execute_graph(...)

    Returns:
        ExecutionEngineProtocol: The initialized ExecutionEngine instance

    Raises:
        HTTPException: 503 Service Unavailable if ExecutionEngine not initialized
    """
    try:
        engine = _container.execution_engine
        return engine
    except DependencyNotInitializedError as e:
        logger.error(
            f"[DEPENDENCY-PROVIDER] ExecutionEngine access failed: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "ExecutionEngine not available. "
                "Service may be starting up or initialization failed."
            ),
        ) from e


# Type aliases for convenience in FastAPI route handlers
# These can be used directly as type annotations without needing Depends()
GraphManager = Annotated[GraphManagerProtocol, Depends(get_graph_manager)]
ExecutionEngine = Annotated[ExecutionEngineProtocol, Depends(get_execution_engine)]
