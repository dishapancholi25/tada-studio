"""Testing utilities for execution context management.

This module provides helper functions and fixtures for testing code
that uses execution context. These utilities ensure clean test isolation
and make it easy to set up test contexts.
"""

from typing import Dict, Optional

from .manager import ExecutionContext
from .store import (
    current_db_execution_id,
    current_execution_data,
    current_execution_id,
    current_execution_order,
    current_user_id,
)


def reset_all_contexts() -> None:
    """
    Reset all context variables to their default values.

    This is useful for ensuring clean state between tests. Should be called
    in test teardown or setup to prevent context leakage between tests.

    Example:
        >>> def teardown():
        ...     reset_all_contexts()
    """
    current_execution_id.set(None)
    current_db_execution_id.set(None)
    current_execution_data.set(None)
    current_execution_order.set(0)
    current_user_id.set(None)


def create_test_context(
    execution_id: str = "test_exec_123",
    db_execution_id: str = "test_db_456",
    node_execution_map: Optional[Dict[str, str]] = None,
) -> ExecutionContext:
    """
    Create a test execution context with sensible defaults.

    This factory function creates an ExecutionContext instance suitable
    for testing, with default values that can be overridden as needed.

    Args:
        execution_id: Test execution ID (default: "test_exec_123")
        db_execution_id: Test database ID (default: "test_db_456")
        node_execution_map: Optional node execution map (default: empty dict)

    Returns:
        ExecutionContext instance ready for testing

    Example:
        >>> context = create_test_context()
        >>> context.set_as_current()
        >>> # ... run tests ...
        >>> context.clear()

        >>> # Or use as context manager
        >>> with create_test_context(execution_id="custom_id"):
        ...     # Test code here
        ...     pass
    """
    if node_execution_map is None:
        node_execution_map = {}

    return ExecutionContext(
        execution_id=execution_id,
        db_execution_id=db_execution_id,
        node_execution_map=node_execution_map,
    )


def get_context_state() -> Dict[str, any]:
    """
    Get the current state of all context variables.

    This is useful for debugging tests or verifying context state.

    Returns:
        Dictionary with current values of all context variables

    Example:
        >>> state = get_context_state()
        >>> print(f"Execution ID: {state['execution_id']}")
        >>> print(f"Order: {state['execution_order']}")
    """
    return {
        "execution_id": current_execution_id.get(),
        "db_execution_id": current_db_execution_id.get(),
        "execution_data": current_execution_data.get(),
        "execution_order": current_execution_order.get(),
        "user_id": current_user_id.get(),
    }


# Pytest fixture (if pytest is available)
try:
    import pytest

    @pytest.fixture
    def execution_context():
        """
        Pytest fixture that provides a clean execution context for each test.

        Automatically creates and clears the context, ensuring test isolation.

        Usage:
            def test_my_function(execution_context):
                # execution_context is already set and will be cleaned up
                exec_id = get_current_execution_id()
                assert exec_id == "test_exec_123"
        """
        context = create_test_context()
        context.set_as_current()
        yield context
        reset_all_contexts()

    @pytest.fixture
    def clean_execution_context():
        """
        Pytest fixture that ensures no execution context is set.

        This is useful for testing code that should handle missing context.

        Usage:
            def test_no_context(clean_execution_context):
                # No context is set
                exec_id = get_current_execution_id()
                assert exec_id is None
        """
        reset_all_contexts()
        yield
        reset_all_contexts()

except ImportError:
    # Pytest not available, skip fixture definitions
    pass
