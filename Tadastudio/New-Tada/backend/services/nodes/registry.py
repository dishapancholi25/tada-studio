"""
Node Executor Registry for managing executor instances.

This module provides a centralized registry for node executors, implementing
the Strategy pattern to allow dynamic executor selection based on node type.
"""

from typing import Any, Callable, Dict, List, Optional, Type

from backend.models.workflow import NodeType
from backend.services.config import get_logger

from .base import BaseNodeExecutor


registry_logger = get_logger("nodes.registry")


class NodeExecutorRegistry:
    """
    Centralized registry for node executors.

    Implements the Strategy pattern, allowing executors to be registered
    for specific node types and retrieved dynamically. Supports dependency
    injection through factory functions.

    Class Attributes:
        _executors: Mapping of NodeType to executor class or factory function
        _instances: Cached executor instances (when using factories)

    Example:
        >>> # Registration with class
        >>> NodeExecutorRegistry.register(NodeType.AGENT, AgentNodeExecutor)
        >>>
        >>> # Registration with factory (for dependency injection)
        >>> def create_agent_executor():
        ...     return AgentNodeExecutor(
        ...         execution_history_service=service,
        ...         ws_notifier=notifier
        ...     )
        >>> NodeExecutorRegistry.register(
        ...     NodeType.AGENT,
        ...     factory=create_agent_executor
        ... )
        >>>
        >>> # Retrieval
        >>> executor = NodeExecutorRegistry.get_executor(NodeType.AGENT)
        >>> result = await executor.execute(node, state, graph, exec_id)
    """

    # Class-level storage for registered executors
    _executors: Dict[str, Type[BaseNodeExecutor]] = {}
    _factories: Dict[str, Callable[[], BaseNodeExecutor]] = {}
    _instances: Dict[str, BaseNodeExecutor] = {}

    @classmethod
    def register(
        cls,
        node_type: NodeType,
        executor_class: Optional[Type[BaseNodeExecutor]] = None,
        factory: Optional[Callable[[], BaseNodeExecutor]] = None,
    ) -> None:
        """
        Register an executor for a specific node type.

        Can register either:
        1. An executor class (will be instantiated when needed)
        2. A factory function (for dependency injection)

        Args:
            node_type: The NodeType this executor handles
            executor_class: The executor class to register (mutually exclusive with factory)
            factory: Factory function that returns an executor instance (mutually exclusive with class)

        Raises:
            ValueError: If both or neither of executor_class and factory are provided

        Example:
            >>> # Register with class
            >>> NodeExecutorRegistry.register(NodeType.AGENT, AgentNodeExecutor)
            >>>
            >>> # Register with factory
            >>> NodeExecutorRegistry.register(
            ...     NodeType.HTTP_REQUEST,
            ...     factory=lambda: HttpNodeExecutor(service, notifier)
            ... )
        """
        if (executor_class is None) == (factory is None):
            raise ValueError("Must provide exactly one of executor_class or factory")

        node_type_str = (
            node_type.value if hasattr(node_type, "value") else str(node_type)
        )

        if executor_class:
            cls._executors[node_type_str] = executor_class
            registry_logger.info(
                f"Registered executor class {executor_class.__name__} "
                f"for node type {node_type_str}"
            )
        else:
            cls._factories[node_type_str] = factory
            registry_logger.info(
                f"Registered executor factory for node type {node_type_str}"
            )

    @classmethod
    def get_executor(
        cls,
        node_type: NodeType,
        dependencies: Optional[Dict[str, Any]] = None,
    ) -> BaseNodeExecutor:
        """
        Get an executor for a specific node type.

        If the executor was registered with:
        - A class: Instantiates it with provided dependencies
        - A factory: Calls the factory function and caches the instance

        Args:
            node_type: The NodeType to get an executor for
            dependencies: Optional dict of dependencies to pass to executor constructor
                         (only used when executor registered as class)

        Returns:
            Executor instance for the node type

        Raises:
            KeyError: If no executor is registered for the node type

        Example:
            >>> # Get executor registered as class
            >>> executor = NodeExecutorRegistry.get_executor(
            ...     NodeType.AGENT,
            ...     dependencies={
            ...         "execution_history_service": service,
            ...         "ws_notifier": notifier,
            ...     }
            ... )
            >>>
            >>> # Get executor registered as factory
            >>> executor = NodeExecutorRegistry.get_executor(NodeType.HTTP_REQUEST)
        """
        node_type_str = (
            node_type.value if hasattr(node_type, "value") else str(node_type)
        )

        # Check if registered as factory
        if node_type_str in cls._factories:
            # Use cached instance if available
            if node_type_str not in cls._instances:
                registry_logger.debug(
                    f"Creating executor instance from factory for {node_type_str}"
                )
                cls._instances[node_type_str] = cls._factories[node_type_str]()
            return cls._instances[node_type_str]

        # Check if registered as class
        if node_type_str in cls._executors:
            executor_class = cls._executors[node_type_str]
            if dependencies:
                registry_logger.debug(
                    f"Instantiating {executor_class.__name__} with dependencies"
                )
                return executor_class(**dependencies)
            else:
                registry_logger.debug(
                    f"Instantiating {executor_class.__name__} without dependencies"
                )
                # Try to instantiate without args (may fail if constructor requires args)
                try:
                    return executor_class()
                except TypeError as e:
                    registry_logger.error(
                        f"Failed to instantiate {executor_class.__name__}: {e}. "
                        f"Did you forget to provide dependencies?"
                    )
                    raise

        # Not found
        raise KeyError(
            f"No executor registered for node type: {node_type_str}. "
            f"Available types: {cls.list_registered_types()}"
        )

    @classmethod
    def is_registered(cls, node_type: NodeType) -> bool:
        """
        Check if an executor is registered for a node type.

        Args:
            node_type: The NodeType to check

        Returns:
            True if an executor is registered, False otherwise

        Example:
            >>> if NodeExecutorRegistry.is_registered(NodeType.AGENT):
            ...     executor = NodeExecutorRegistry.get_executor(NodeType.AGENT)
        """
        node_type_str = (
            node_type.value if hasattr(node_type, "value") else str(node_type)
        )
        return node_type_str in cls._executors or node_type_str in cls._factories

    @classmethod
    def list_registered_types(cls) -> List[str]:
        """
        List all registered node types.

        Returns:
            List of node type strings

        Example:
            >>> registered = NodeExecutorRegistry.list_registered_types()
            >>> print(f"Registered executors: {', '.join(registered)}")
        """
        return sorted(set(list(cls._executors.keys()) + list(cls._factories.keys())))

    @classmethod
    def unregister(cls, node_type: NodeType) -> None:
        """
        Unregister an executor for a node type.

        Useful for testing or hot-swapping executors.

        Args:
            node_type: The NodeType to unregister

        Example:
            >>> NodeExecutorRegistry.unregister(NodeType.AGENT)
            >>> # Re-register with different implementation
            >>> NodeExecutorRegistry.register(NodeType.AGENT, NewAgentExecutor)
        """
        node_type_str = (
            node_type.value if hasattr(node_type, "value") else str(node_type)
        )

        if node_type_str in cls._executors:
            del cls._executors[node_type_str]
            registry_logger.info(f"Unregistered executor class for {node_type_str}")

        if node_type_str in cls._factories:
            del cls._factories[node_type_str]
            registry_logger.info(f"Unregistered executor factory for {node_type_str}")

        if node_type_str in cls._instances:
            del cls._instances[node_type_str]
            registry_logger.debug(f"Cleared cached instance for {node_type_str}")

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered executors.

        Useful for testing or reinitialization.

        Example:
            >>> NodeExecutorRegistry.clear()
            >>> # Re-register executors
        """
        cls._executors.clear()
        cls._factories.clear()
        cls._instances.clear()
        registry_logger.info("Cleared all registered executors")
