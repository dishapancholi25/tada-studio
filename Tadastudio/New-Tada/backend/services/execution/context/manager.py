"""Execution context manager and dataclass.

This module provides the ExecutionContext dataclass for managing execution
context data, including support for context managers for automatic cleanup.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from backend.services.config import get_logger

from .store import (
    current_db_execution_id,
    current_execution_data,
    current_execution_id,
)


# Get logger for execution context
context_logger = get_logger("execution.context")


@dataclass
class ExecutionContext:
    """
    Container for execution context data.

    This class encapsulates all the execution tracking information needed
    for workflow and sub-agent execution, including database IDs and node
    execution mappings.

    Attributes:
        execution_id: The thread/workflow execution ID (used for checkpointing)
        db_execution_id: The database execution record ID
        node_execution_map: Mapping of node IDs to execution record IDs

    Example:
        >>> context = ExecutionContext(
        ...     execution_id="thread_123",
        ...     db_execution_id="456",
        ...     node_execution_map={"node_1": "exec_1"}
        ... )
        >>> context.set_as_current()
        >>> # ... do work ...
        >>> ExecutionContext.clear()
    """

    execution_id: str
    db_execution_id: str
    node_execution_map: Dict[str, str]

    def set_as_current(self) -> None:
        """
        Set this context as the current execution context.

        This updates all the thread-local context variables with the
        values from this ExecutionContext instance.

        Example:
            >>> context = ExecutionContext(
            ...     execution_id="thread_123",
            ...     db_execution_id="456",
            ...     node_execution_map={}
            ... )
            >>> context.set_as_current()
        """
        context_logger.debug(
            f"[CONTEXT] Setting execution context - "
            f"execution_id: {self.execution_id}, "
            f"db_execution_id: {self.db_execution_id}"
        )

        current_execution_id.set(self.execution_id)
        current_db_execution_id.set(self.db_execution_id)
        current_execution_data.set(
            {
                "execution_id": self.execution_id,
                "db_execution_id": self.db_execution_id,
                "node_execution_map": self.node_execution_map,
            }
        )

        context_logger.debug(
            f"[CONTEXT] Context set successfully with "
            f"{len(self.node_execution_map)} node mappings"
        )

    @classmethod
    def get_current(cls) -> Optional["ExecutionContext"]:
        """
        Get the current execution context if available.

        Returns:
            ExecutionContext instance if context is set, None otherwise

        Example:
            >>> context = ExecutionContext.get_current()
            >>> if context:
            ...     print(f"Current execution: {context.execution_id}")
        """
        exec_id = current_execution_id.get()
        db_exec_id = current_db_execution_id.get()
        exec_data = current_execution_data.get()

        if exec_id and db_exec_id and exec_data:
            return cls(
                execution_id=exec_id,
                db_execution_id=db_exec_id,
                node_execution_map=exec_data.get("node_execution_map", {}),
            )
        return None

    @classmethod
    def clear(cls) -> None:
        """
        Clear the current execution context.

        This resets all context variables to their default values.
        Should be called at the end of workflow execution to prevent
        context leakage.

        Example:
            >>> ExecutionContext.clear()
        """
        context_logger.debug("[CONTEXT] Clearing execution context")
        current_execution_id.set(None)
        current_db_execution_id.set(None)
        current_execution_data.set(None)

    def __enter__(self) -> "ExecutionContext":
        """
        Enter the context manager.

        Sets this context as current when entering a with block.

        Returns:
            This ExecutionContext instance

        Example:
            >>> context = ExecutionContext("thread_1", "db_1", {})
            >>> with context:
            ...     # Context is active here
            ...     pass
            >>> # Context is cleared here
        """
        self.set_as_current()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager.

        Clears the context when exiting a with block.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        self.clear()

    async def __aenter__(self) -> "ExecutionContext":
        """
        Enter the async context manager.

        Sets this context as current when entering an async with block.

        Returns:
            This ExecutionContext instance

        Example:
            >>> async with ExecutionContext("thread_1", "db_1", {}):
            ...     # Context is active here
            ...     await some_async_function()
        """
        self.set_as_current()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager.

        Clears the context when exiting an async with block.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        self.clear()
