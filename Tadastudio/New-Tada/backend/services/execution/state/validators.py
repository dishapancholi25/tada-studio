"""
Validation utilities for state execution tracking.

This module provides validation functions to ensure state integrity
and catch errors early in the execution pipeline.
"""

from typing import Any, Dict

from .exceptions import InvalidExecutionOrderError, InvalidStateStructureError
from .models import ExecutionOrder, WorkflowState


def validate_execution_order(order: Any) -> ExecutionOrder:
    """
    Validate that execution order is a non-negative integer.

    Args:
        order: The execution order value to validate

    Returns:
        The validated execution order as an integer

    Raises:
        InvalidExecutionOrderError: If the order is invalid
    """
    if not isinstance(order, int):
        raise InvalidExecutionOrderError(
            order, f"Execution order must be an integer, got {type(order).__name__}"
        )

    if order < 0:
        raise InvalidExecutionOrderError(order, "Execution order must be non-negative")

    return order


def validate_state_structure(state: Any) -> WorkflowState:
    """
    Validate that state has the expected dictionary structure.

    Args:
        state: The state object to validate

    Returns:
        The validated state dictionary

    Raises:
        InvalidStateStructureError: If the state structure is invalid
    """
    if not isinstance(state, dict):
        raise InvalidStateStructureError(
            expected="dictionary", actual=type(state).__name__
        )

    return state


def validate_metadata_structure(metadata: Any) -> Dict[str, Any]:
    """
    Validate that metadata has the expected dictionary structure.

    Args:
        metadata: The metadata object to validate

    Returns:
        The validated metadata dictionary

    Raises:
        InvalidStateStructureError: If the metadata structure is invalid
    """
    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        raise InvalidStateStructureError(
            expected="dictionary for metadata", actual=type(metadata).__name__
        )

    return metadata


def validate_node_id(node_id: Any) -> str:
    """
    Validate that node_id is a non-empty string.

    Args:
        node_id: The node ID to validate

    Returns:
        The validated node ID string

    Raises:
        InvalidStateStructureError: If the node_id is invalid
    """
    if not isinstance(node_id, str):
        raise InvalidStateStructureError(
            expected="string for node_id", actual=type(node_id).__name__
        )

    if not node_id.strip():
        raise InvalidStateStructureError(
            expected="non-empty string for node_id", actual="empty string"
        )

    return node_id


def validate_node_name(node_name: Any) -> str:
    """
    Validate that node_name is a non-empty string.

    Args:
        node_name: The node name to validate

    Returns:
        The validated node name string

    Raises:
        InvalidStateStructureError: If the node_name is invalid
    """
    if not isinstance(node_name, str):
        raise InvalidStateStructureError(
            expected="string for node_name", actual=type(node_name).__name__
        )

    if not node_name.strip():
        raise InvalidStateStructureError(
            expected="non-empty string for node_name", actual="empty string"
        )

    return node_name


def validate_node_type(node_type: Any) -> str:
    """
    Validate that node_type is a non-empty string.

    Args:
        node_type: The node type to validate

    Returns:
        The validated node type string

    Raises:
        InvalidStateStructureError: If the node_type is invalid
    """
    if not isinstance(node_type, str):
        raise InvalidStateStructureError(
            expected="string for node_type", actual=type(node_type).__name__
        )

    if not node_type.strip():
        raise InvalidStateStructureError(
            expected="non-empty string for node_type", actual="empty string"
        )

    return node_type


def safe_get_execution_order(state: WorkflowState, default: int = 0) -> ExecutionOrder:
    """
    Safely get execution order from state with validation.

    Args:
        state: The workflow state dictionary
        default: Default value if execution_order is not in state

    Returns:
        The validated execution order

    Raises:
        InvalidExecutionOrderError: If the order in state is invalid
    """
    order = state.get("execution_order", default)
    return validate_execution_order(order)


def safe_get_metadata(state: WorkflowState) -> Dict[str, Any]:
    """
    Safely get metadata from state with validation.

    Args:
        state: The workflow state dictionary

    Returns:
        The validated metadata dictionary (empty dict if not present)

    Raises:
        InvalidStateStructureError: If the metadata structure is invalid
    """
    metadata = state.get("metadata", {})
    return validate_metadata_structure(metadata)
