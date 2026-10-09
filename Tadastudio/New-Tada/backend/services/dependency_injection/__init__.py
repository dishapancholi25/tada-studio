"""
Dependency injection module for AgenticStudio application.

This module provides centralized management of shared application dependencies
including GraphManager and ExecutionEngine. It supports both direct access
for non-FastAPI code and FastAPI dependency injection patterns.

Quick Start:
    # 1. Initialize during app startup (in app.py lifespan)
    from backend.services.dependency_injection import initialize_dependencies
    initialize_dependencies()

    # 2a. Access directly (for non-FastAPI code)
    from backend.services.dependency_injection import (
        get_graph_manager,
        get_execution_engine
    )
    graph_mgr = get_graph_manager()
    engine = get_execution_engine()

    # 2b. Use as FastAPI dependency (recommended for route handlers)
    from backend.services.dependency_injection import GraphManager, ExecutionEngine

    @router.get("/example")
    async def example_route(
        graph_mgr: GraphManager,
        engine: ExecutionEngine
    ):
        graphs = graph_mgr.list_graphs()
        await engine.execute_graph(...)

Architecture:
    - container.py: Thread-safe singleton container for dependencies
    - providers.py: FastAPI dependency provider functions
    - types.py: Protocol definitions for type safety
    - exceptions.py: Custom exception classes

Benefits:
    - Type safety with Protocol definitions
    - Thread-safe initialization
    - FastAPI-native dependency injection
    - Easy to test and mock
    - Clear error messages
    - Comprehensive logging
"""

from .container import _container
from .exceptions import (
    DependencyError,
    DependencyNotInitializedError,
    InitializationError,
)
from .providers import (
    ExecutionEngine,
    GraphManager,
    get_execution_engine,
    get_graph_manager,
)
from .types import ExecutionEngineProtocol, GraphManagerProtocol


# Public API Functions
def initialize_dependencies() -> None:
    """
    Initialize all application dependencies.

    This function must be called once during application startup,
    preferably in the FastAPI lifespan context.

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            initialize_dependencies()
            yield
            # Shutdown
            pass

    Raises:
        InitializationError: If initialization fails
    """
    _container.initialize()


def is_initialized() -> bool:
    """
    Check if dependencies are initialized.

    Returns:
        bool: True if both GraphManager and ExecutionEngine are initialized

    Example:
        if not is_initialized():
            raise RuntimeError("Dependencies not initialized")
    """
    return _container.is_initialized()


# Public API Exports
__all__ = [
    # Initialization functions
    "initialize_dependencies",
    "is_initialized",
    # Direct access functions (for non-FastAPI code)
    "get_graph_manager",
    "get_execution_engine",
    # FastAPI dependency type aliases (use as type annotations)
    "GraphManager",
    "ExecutionEngine",
    # Type protocols (for type hints and testing)
    "GraphManagerProtocol",
    "ExecutionEngineProtocol",
    # Exception classes
    "DependencyError",
    "DependencyNotInitializedError",
    "InitializationError",
]
