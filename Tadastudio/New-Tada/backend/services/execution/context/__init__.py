"""
Execution context management for tracking execution state across the application.

This package provides thread-safe execution context management using contextvars,
enabling proper tracking of workflow and sub-agent executions across async boundaries.

Public API:
    Core Classes:
        - ExecutionContext: Dataclass for managing execution context with context manager support

    Utility Functions:
        - get_current_execution_id(): Get the current execution ID
        - get_current_db_execution_id(): Get the database execution ID
        - set_execution_context(): Set the execution context
        - clear_execution_context(): Clear the execution context
        - get_and_increment_execution_order(): Get and increment execution order
        - get_current_execution_order(): Get execution order without incrementing
        - set_execution_order(): Set execution order to specific value
        - get_execution_data(): Get complete execution data dictionary

    Exceptions:
        - ExecutionContextError: Base exception
        - ContextNotSetError: Context not set when required
        - ContextAlreadySetError: Attempted to set already-active context
        - ContextValidationError: Context data validation failed

    Testing Utilities:
        - reset_all_contexts(): Reset all context variables (testing)
        - create_test_context(): Create test execution context
        - get_context_state(): Get current state of all context variables

Usage Examples:
    Basic usage with context manager:
        >>> from backend.services.execution.context import ExecutionContext
        >>> with ExecutionContext("exec_1", "db_1", {}) as ctx:
        ...     # Context is active here
        ...     do_work()
        >>> # Context automatically cleared

    Manual context management:
        >>> from backend.services.execution.context import (
        ...     set_execution_context,
        ...     get_current_execution_id,
        ...     clear_execution_context
        ... )
        >>> set_execution_context("exec_1", "db_1", {})
        >>> exec_id = get_current_execution_id()
        >>> clear_execution_context()

    Async context manager:
        >>> async with ExecutionContext("exec_1", "db_1", {}):
        ...     await async_work()
"""

# Core classes
from .manager import ExecutionContext

# Utility functions
from .utils import (
    clear_execution_context,
    get_and_increment_execution_order,
    get_current_db_execution_id,
    get_current_execution_id,
    get_current_execution_order,
    get_current_user_access_token,
    get_current_user_id,
    get_execution_data,
    get_node_execution_id,
    set_execution_context,
    set_execution_order,
    update_node_execution_map,
)

# Exceptions
from .exceptions import (
    ContextAlreadySetError,
    ContextNotSetError,
    ContextValidationError,
    ExecutionContextError,
)

# Testing utilities (optional)
from .testing import (
    create_test_context,
    get_context_state,
    reset_all_contexts,
)


__all__ = [
    # Core classes
    "ExecutionContext",
    # Utility functions
    "get_current_execution_id",
    "get_current_db_execution_id",
    "get_current_user_access_token",
    "get_current_user_id",
    "set_execution_context",
    "clear_execution_context",
    "get_and_increment_execution_order",
    "get_current_execution_order",
    "set_execution_order",
    "get_execution_data",
    "update_node_execution_map",
    "get_node_execution_id",
    # Exceptions
    "ExecutionContextError",
    "ContextNotSetError",
    "ContextAlreadySetError",
    "ContextValidationError",
    # Testing utilities
    "reset_all_contexts",
    "create_test_context",
    "get_context_state",
]
