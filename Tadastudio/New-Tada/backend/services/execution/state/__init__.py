"""
State execution tracking service.

This module provides state-based execution tracking for LangGraph workflows,
replacing context variable approaches with direct state management.

Public API:
    - StateExecutionTracker: Main class for state tracking operations
    - Exceptions: Custom exception classes for error handling
    - Models: Type definitions for type-safe state operations
    - Validators: Utility functions for state validation

Example:
    >>> from backend.services.execution.state import StateExecutionTracker
    >>> state = {"execution_order": 0}
    >>> order = StateExecutionTracker.get_execution_order(state)
    >>> update = StateExecutionTracker.increment_execution_order(state)
"""

from typing import Any, Dict

# Exception classes
from .exceptions import (
    InvalidExecutionOrderError,
    InvalidStateStructureError,
    MissingStateKeyError,
    StateTrackingError,
    StateUpdateError,
)

# Type definitions
from .models import (
    ExecutionOrder,
    NodeExecutionInfo,
    NodeId,
    NodeName,
    NodeType,
    StateMetadata,
    StateUpdate,
    WorkflowState,
    WorkflowStateProtocol,
)

# Main tracker class
from .tracker import StateExecutionTracker

# Validators
from .validators import (
    safe_get_execution_order,
    safe_get_metadata,
    validate_execution_order,
    validate_node_id,
    validate_node_name,
    validate_node_type,
    validate_state_structure,
)


# ============================================================================
# Backward Compatibility Functions
# ============================================================================
# These functions maintain compatibility with code that used the old module
# structure. They delegate to StateExecutionTracker methods.
# ============================================================================


def get_execution_order_from_state(state: Dict[str, Any]) -> int:
    """
    Compatibility function to get execution order from state.

    This function is provided for backward compatibility with code
    that imported from the old state_execution_tracker module.

    Args:
        state: The workflow state dictionary

    Returns:
        Current execution order

    Note:
        Use StateExecutionTracker.get_execution_order() instead.
        This compatibility function may be deprecated in future versions.
    """
    return StateExecutionTracker.get_execution_order(state)


def update_execution_order_in_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility function to increment execution order in state.

    This function is provided for backward compatibility with code
    that imported from the old state_execution_tracker module.

    Args:
        state: The workflow state dictionary

    Returns:
        State update dictionary with incremented order

    Note:
        Use StateExecutionTracker.increment_execution_order() instead.
        This compatibility function may be deprecated in future versions.
    """
    return StateExecutionTracker.increment_execution_order(state)


# Public API exports
__all__ = [
    # Main class
    "StateExecutionTracker",
    # Exceptions
    "StateTrackingError",
    "InvalidExecutionOrderError",
    "MissingStateKeyError",
    "InvalidStateStructureError",
    "StateUpdateError",
    # Models
    "WorkflowState",
    "StateUpdate",
    "NodeExecutionInfo",
    "StateMetadata",
    "ExecutionOrder",
    "NodeId",
    "NodeName",
    "NodeType",
    "WorkflowStateProtocol",
    # Validators
    "validate_execution_order",
    "validate_state_structure",
    "validate_node_id",
    "validate_node_name",
    "validate_node_type",
    "safe_get_execution_order",
    "safe_get_metadata",
    # Backward compatibility
    "get_execution_order_from_state",
    "update_execution_order_in_state",
]
