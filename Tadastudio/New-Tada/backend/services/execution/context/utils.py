"""Utility functions for execution context management.

This module provides high-level functions for getting, setting, and
managing execution context. These are the primary functions used by
consumers of the context system.
"""

from typing import Any, Dict, Optional

from backend.services.config import get_logger

from .exceptions import ContextValidationError
from .store import (
    current_db_execution_id,
    current_execution_data,
    current_execution_id,
    current_execution_order,
    current_user_access_token,
    current_user_id,
)


# Get logger for execution context
context_logger = get_logger("execution.context")


def get_current_execution_id() -> Optional[str]:
    """
    Get the current execution ID from context.

    Returns:
        The execution ID (thread_id) if set, None otherwise

    Example:
        >>> exec_id = get_current_execution_id()
        >>> if exec_id:
        ...     print(f"Current execution: {exec_id}")
    """
    return current_execution_id.get()


def get_current_db_execution_id() -> Optional[str]:
    """
    Get the current database execution ID from context.

    Returns:
        The database execution record ID if set, None otherwise

    Example:
        >>> db_id = get_current_db_execution_id()
        >>> if db_id:
        ...     print(f"Database execution ID: {db_id}")
    """
    return current_db_execution_id.get()


def set_execution_context(
    execution_id: str,
    db_execution_id: str,
    node_execution_map: Optional[Dict[str, str]] = None,
    user_access_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Set the current execution context.

    This function sets all the context variables needed for execution tracking.
    It validates the inputs and logs the operation.

    Args:
        execution_id: The thread/workflow execution ID (must be non-empty)
        db_execution_id: The database execution record ID (must be non-empty)
        node_execution_map: Optional mapping of node IDs to execution record IDs
        user_access_token: Optional user's JWT access token for MCP servers

    Raises:
        ContextValidationError: If execution_id or db_execution_id are invalid

    Example:
        >>> set_execution_context(
        ...     execution_id="thread_123",
        ...     db_execution_id="456",
        ...     node_execution_map={"node_1": "exec_1"},
        ...     user_access_token="eyJ..."
        ... )
    """
    # Validate inputs
    if not execution_id or not isinstance(execution_id, str):
        raise ContextValidationError(
            field="execution_id",
            value=execution_id,
            message="execution_id must be a non-empty string",
        )

    if not db_execution_id or not isinstance(db_execution_id, str):
        raise ContextValidationError(
            field="db_execution_id",
            value=db_execution_id,
            message="db_execution_id must be a non-empty string",
        )

    if node_execution_map is not None and not isinstance(node_execution_map, dict):
        raise ContextValidationError(
            field="node_execution_map",
            value=type(node_execution_map).__name__,
            message="node_execution_map must be a dictionary",
        )

    context_logger.debug(
        f"[CONTEXT] Setting execution context - "
        f"execution_id: {execution_id}, "
        f"db_execution_id: {db_execution_id}, "
        f"has_user_token: {user_access_token is not None}"
    )

    current_execution_id.set(execution_id)
    current_db_execution_id.set(db_execution_id)
    current_user_access_token.set(user_access_token)
    current_user_id.set(user_id)

    if node_execution_map is not None:
        context_logger.debug(
            f"[CONTEXT] Setting node execution map with "
            f"{len(node_execution_map)} entries"
        )
        current_execution_data.set(
            {
                "execution_id": execution_id,
                "db_execution_id": db_execution_id,
                "node_execution_map": node_execution_map,
            }
        )
    else:
        # Set with empty map if not provided
        current_execution_data.set(
            {
                "execution_id": execution_id,
                "db_execution_id": db_execution_id,
                "node_execution_map": {},
            }
        )


def get_current_user_access_token() -> Optional[str]:
    """
    Get the current user's access token from context.

    Returns:
        The user's JWT access token if set, None otherwise

    Example:
        >>> token = get_current_user_access_token()
        >>> if token:
        ...     print("User token available for MCP servers")
    """
    return current_user_access_token.get()


def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from context.

    Returns:
        The user ID (email or identifier) if set, None otherwise
    """
    return current_user_id.get()


def clear_execution_context() -> None:
    """
    Clear the current execution context.

    This resets all context variables to their default values and should
    be called at the end of workflow execution to prevent context leakage
    between executions.

    Example:
        >>> clear_execution_context()
    """
    context_logger.debug("[CONTEXT] Clearing execution context")
    execution_id = current_execution_id.get()
    if execution_id:
        try:
            from backend.services.file_content_references import (
                clear_file_content_references,
            )

            clear_file_content_references(execution_id)
        except Exception as cleanup_error:
            context_logger.debug(
                f"[CONTEXT] Failed to clear file content references: {cleanup_error}"
            )
    current_execution_id.set(None)
    current_db_execution_id.set(None)
    current_execution_data.set(None)
    current_execution_order.set(0)
    current_user_access_token.set(None)
    current_user_id.set(None)


def get_and_increment_execution_order() -> int:
    """
    Get the current execution order and increment it for the next call.

    This is used to track the sequence of node executions within a workflow.
    Each call returns the current value and increments the counter.

    Returns:
        The current execution order before incrementing

    Example:
        >>> order1 = get_and_increment_execution_order()  # Returns 0
        >>> order2 = get_and_increment_execution_order()  # Returns 1
        >>> order3 = get_and_increment_execution_order()  # Returns 2
    """
    order = current_execution_order.get()
    current_execution_order.set(order + 1)
    context_logger.debug(f"[CONTEXT] Execution order: {order} -> {order + 1}")
    return order


def get_current_execution_order() -> int:
    """
    Get the current execution order without incrementing.

    Returns:
        The current execution order value

    Example:
        >>> order = get_current_execution_order()
        >>> print(f"Current order: {order}")
    """
    return current_execution_order.get()


def set_execution_order(order: int) -> None:
    """
    Set the current execution order.

    This is useful for resetting or setting a specific execution order
    value, such as when resuming from a checkpoint.

    Args:
        order: The execution order value to set (must be non-negative)

    Raises:
        ContextValidationError: If order is negative

    Example:
        >>> set_execution_order(5)
        >>> assert get_current_execution_order() == 5
    """
    if not isinstance(order, int) or order < 0:
        raise ContextValidationError(
            field="order",
            value=order,
            message="execution order must be a non-negative integer",
        )

    context_logger.debug(f"[CONTEXT] Setting execution order to: {order}")
    current_execution_order.set(order)


def get_execution_data() -> Optional[Dict[str, Any]]:
    """
    Get the complete execution data dictionary.

    Returns:
        Dictionary containing execution_id, db_execution_id, and
        node_execution_map if set, None otherwise

    Example:
        >>> data = get_execution_data()
        >>> if data:
        ...     print(f"Execution: {data['execution_id']}")
        ...     print(f"Node map: {data['node_execution_map']}")
    """
    return current_execution_data.get()


def update_node_execution_map(node_id: str, execution_id: str) -> None:
    """
    Add or update a node_id -> execution_id mapping in the current context.

    This is used to track the database execution record ID for each node,
    enabling sub-agents to reference their parent's execution record.

    Args:
        node_id: The graph node's unique ID
        execution_id: The database node execution record ID

    Example:
        >>> update_node_execution_map("node-abc", "exec-123")
    """
    data = current_execution_data.get()
    if data is None:
        context_logger.debug(
            f"[CONTEXT] No execution data context, cannot update node map "
            f"for node {node_id}"
        )
        return

    node_map = data.get("node_execution_map", {})
    node_map[node_id] = execution_id
    data["node_execution_map"] = node_map
    current_execution_data.set(data)

    context_logger.debug(
        f"[CONTEXT] Updated node execution map: {node_id} -> {execution_id}"
    )


def get_node_execution_id(node_id: str) -> Optional[str]:
    """
    Get the database execution record ID for a node.

    Args:
        node_id: The graph node's unique ID

    Returns:
        The database node execution record ID, or None if not found

    Example:
        >>> exec_id = get_node_execution_id("node-abc")
        >>> if exec_id:
        ...     print(f"Node execution ID: {exec_id}")
    """
    data = current_execution_data.get()
    if data is None:
        return None

    node_map = data.get("node_execution_map", {})
    return node_map.get(node_id)
