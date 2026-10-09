"""
Thread-safe dependency container with singleton pattern.

This module provides a centralized container for managing application dependencies
with thread-safe initialization and access patterns.
"""

import threading
from typing import Optional

from ..config import get_logger
from .exceptions import DependencyNotInitializedError, InitializationError
from .types import ExecutionEngineProtocol, GraphManagerProtocol


logger = get_logger("dependency_injection")


class DependencyContainer:
    """
    Thread-safe singleton container for application dependencies.

    This class manages the lifecycle of shared application dependencies,
    ensuring thread-safe initialization and providing type-safe access.

    Usage:
        # Initialize once during app startup
        container = DependencyContainer()
        container.initialize()

        # Access dependencies
        graph_mgr = container.graph_manager
        engine = container.execution_engine
    """

    _instance: Optional["DependencyContainer"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """
        Create or return the singleton instance.

        Uses double-checked locking pattern for thread safety.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check locking
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize the container.

        Note: This only runs once due to the _initialized flag.
        """
        if not hasattr(self, "_initialized"):
            self._graph_manager: Optional[GraphManagerProtocol] = None
            self._execution_engine: Optional[ExecutionEngineProtocol] = None
            self._init_lock = threading.Lock()
            self._initialized = True
            logger.debug("[DEPENDENCY-CONTAINER] Container instance created")

    def initialize(self) -> None:
        """
        Initialize all application dependencies.

        This method must be called once during application startup,
        preferably in the FastAPI lifespan context.

        Thread-safe: Multiple calls are safe; subsequent calls are no-ops.

        Raises:
            InitializationError: If initialization fails for any reason
        """
        with self._init_lock:
            if self._graph_manager is not None:
                logger.warning(
                    "[DEPENDENCY-CONTAINER] Dependencies already initialized, "
                    "skipping re-initialization"
                )
                return

            try:
                logger.info("[DEPENDENCY-CONTAINER] Initializing dependencies...")

                # Import here to avoid circular dependencies
                from ..graph import GraphManager
                from ..execution import get_executor, initialize_executor

                # Initialize GraphManager
                logger.debug("[DEPENDENCY-CONTAINER] Creating GraphManager...")
                self._graph_manager = GraphManager()
                logger.info(
                    "[DEPENDENCY-CONTAINER] GraphManager initialized successfully"
                )

                # Initialize LangGraph executor
                logger.debug("[DEPENDENCY-CONTAINER] Initializing ExecutionEngine...")
                initialize_executor(self._graph_manager)
                self._execution_engine = get_executor()
                logger.info(
                    "[DEPENDENCY-CONTAINER] ExecutionEngine initialized successfully"
                )

                logger.info(
                    "[DEPENDENCY-CONTAINER] All dependencies initialized successfully"
                )

            except Exception as e:
                logger.error(
                    f"[DEPENDENCY-CONTAINER] Initialization failed: {e}",
                    exc_info=True,
                )
                # Clean up partial initialization
                self._graph_manager = None
                self._execution_engine = None
                raise InitializationError(
                    f"Failed to initialize dependencies: {e}"
                ) from e

    @property
    def graph_manager(self) -> GraphManagerProtocol:
        """
        Get the GraphManager instance.

        Returns:
            GraphManagerProtocol: The initialized GraphManager instance

        Raises:
            DependencyNotInitializedError: If initialize() hasn't been called
        """
        if self._graph_manager is None:
            logger.error(
                "[DEPENDENCY-CONTAINER] Attempted to access uninitialized GraphManager"
            )
            raise DependencyNotInitializedError("GraphManager")
        return self._graph_manager

    @property
    def execution_engine(self) -> ExecutionEngineProtocol:
        """
        Get the ExecutionEngine instance.

        Returns:
            ExecutionEngineProtocol: The initialized ExecutionEngine instance

        Raises:
            DependencyNotInitializedError: If initialize() hasn't been called
        """
        if self._execution_engine is None:
            logger.error(
                "[DEPENDENCY-CONTAINER] Attempted to access uninitialized "
                "ExecutionEngine"
            )
            raise DependencyNotInitializedError("ExecutionEngine")
        return self._execution_engine

    def is_initialized(self) -> bool:
        """
        Check if dependencies are initialized.

        Returns:
            bool: True if both GraphManager and ExecutionEngine are initialized
        """
        return self._graph_manager is not None and self._execution_engine is not None

    def reset(self) -> None:
        """
        Reset the container (primarily for testing).

        Warning: This should only be used in test environments.
        """
        with self._init_lock:
            logger.warning(
                "[DEPENDENCY-CONTAINER] Resetting container "
                "(should only happen in tests)"
            )
            self._graph_manager = None
            self._execution_engine = None


# Global singleton instance
_container = DependencyContainer()
