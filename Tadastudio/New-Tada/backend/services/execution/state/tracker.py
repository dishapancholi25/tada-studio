"""
State-based execution tracking for LangGraph workflows.

This module provides the StateExecutionTracker class for managing
execution order and node tracking through workflow state, replacing
context variable approaches with direct state management.
"""

from ...config import get_logger
from .exceptions import StateTrackingError, StateUpdateError
from .models import (
    ExecutionOrder,
    NodeExecutionInfo,
    NodeId,
    NodeName,
    NodeType,
    StateUpdate,
    WorkflowState,
)
from .validators import (
    safe_get_execution_order,
    safe_get_metadata,
    validate_execution_order,
    validate_node_id,
    validate_node_name,
    validate_node_type,
    validate_state_structure,
)


# Get logger for state tracking
state_tracker_logger = get_logger("state_execution_tracker")


class StateExecutionTracker:
    """
    Manages execution order tracking through workflow state.

    This class provides static methods for state-based execution tracking,
    replacing context variable approaches with direct state management.
    All operations are designed to be stateless and thread-safe.

    Example:
        >>> state = {"execution_order": 0}
        >>> order = StateExecutionTracker.get_execution_order(state)
        >>> update = StateExecutionTracker.increment_execution_order(state)
        >>> state.update(update)
    """

    @staticmethod
    def get_execution_order(state: WorkflowState) -> ExecutionOrder:
        """
        Get the current execution order from state.

        This method safely retrieves the execution order with validation
        and defaults to 0 if not present in the state.

        Args:
            state: The workflow state dictionary

        Returns:
            Current execution order (defaults to 0 if not set)

        Raises:
            InvalidStateStructureError: If state is not a valid dictionary
            InvalidExecutionOrderError: If execution_order in state is invalid

        Example:
            >>> state = {"execution_order": 5}
            >>> StateExecutionTracker.get_execution_order(state)
            5
        """
        try:
            validate_state_structure(state)
            order = safe_get_execution_order(state, default=0)
            state_tracker_logger.debug(
                f"[STATE-TRACKER] Getting execution order from state: {order}",
                extra={
                    "execution_order": order,
                    "execution_id": state.get("execution_id"),
                },
            )
            return order
        except StateTrackingError:
            # Re-raise state tracking errors
            raise
        except Exception as e:
            # Wrap unexpected errors
            state_tracker_logger.error(
                f"[STATE-TRACKER] Unexpected error getting execution order: {e}",
                extra={
                    "error": str(e),
                    "state_keys": list(state.keys())
                    if isinstance(state, dict)
                    else None,
                },
            )
            raise StateTrackingError(
                f"Failed to get execution order: {e}",
                state_snapshot={"execution_order": state.get("execution_order")}
                if isinstance(state, dict)
                else None,
            ) from e

    @staticmethod
    def increment_execution_order(state: WorkflowState) -> StateUpdate:
        """
        Increment the execution order in state and return the update.

        This method calculates the next execution order and returns
        a state update dictionary that can be merged into the state.

        Args:
            state: The workflow state dictionary

        Returns:
            State update dictionary with incremented order

        Raises:
            InvalidStateStructureError: If state is not a valid dictionary
            InvalidExecutionOrderError: If current execution_order is invalid

        Example:
            >>> state = {"execution_order": 5}
            >>> update = StateExecutionTracker.increment_execution_order(state)
            >>> update
            {'execution_order': 6}
        """
        try:
            validate_state_structure(state)
            current_order = StateExecutionTracker.get_execution_order(state)
            next_order = current_order + 1

            state_tracker_logger.debug(
                f"[STATE-TRACKER] Incrementing execution order: {current_order} -> {next_order}",
                extra={
                    "current_order": current_order,
                    "next_order": next_order,
                    "execution_id": state.get("execution_id"),
                },
            )

            return {"execution_order": next_order}
        except StateTrackingError:
            raise
        except Exception as e:
            state_tracker_logger.error(
                f"[STATE-TRACKER] Unexpected error incrementing execution order: {e}",
                extra={"error": str(e)},
            )
            raise StateUpdateError("increment execution order", str(e)) from e

    @staticmethod
    def set_execution_order(state: WorkflowState, order: ExecutionOrder) -> StateUpdate:
        """
        Set the execution order in state to a specific value.

        This method validates the provided order and returns a state
        update dictionary with the specified order.

        Args:
            state: The workflow state dictionary
            order: The execution order to set (must be non-negative)

        Returns:
            State update dictionary with the specified order

        Raises:
            InvalidStateStructureError: If state is not a valid dictionary
            InvalidExecutionOrderError: If the provided order is invalid

        Example:
            >>> state = {"execution_order": 5}
            >>> update = StateExecutionTracker.set_execution_order(state, 10)
            >>> update
            {'execution_order': 10}
        """
        try:
            validate_state_structure(state)
            validated_order = validate_execution_order(order)

            state_tracker_logger.debug(
                f"[STATE-TRACKER] Setting execution order to: {validated_order}",
                extra={
                    "new_order": validated_order,
                    "execution_id": state.get("execution_id"),
                },
            )

            return {"execution_order": validated_order}
        except StateTrackingError:
            raise
        except Exception as e:
            state_tracker_logger.error(
                f"[STATE-TRACKER] Unexpected error setting execution order: {e}",
                extra={"error": str(e), "requested_order": order},
            )
            raise StateUpdateError("set execution order", str(e)) from e

    @staticmethod
    def track_node_execution(
        state: WorkflowState, node_id: NodeId, node_name: NodeName, node_type: NodeType
    ) -> StateUpdate:
        """
        Track a node execution and update the state.

        This method records node execution information and optionally
        increments the execution order (depending on node type).

        Args:
            state: The workflow state dictionary
            node_id: The node's unique identifier
            node_name: The node's display name
            node_type: The type of node (AGENT, CONDITION, START, END, etc.)

        Returns:
            State update dictionary with tracking information

        Raises:
            InvalidStateStructureError: If state or inputs are invalid
            InvalidExecutionOrderError: If execution order operations fail

        Example:
            >>> state = {"execution_order": 5, "metadata": {}}
            >>> update = StateExecutionTracker.track_node_execution(
            ...     state, "node-123", "My Agent", "AGENT"
            ... )
            >>> "current_node" in update
            True
        """
        try:
            # Validate inputs
            validate_state_structure(state)
            validated_node_id = validate_node_id(node_id)
            validated_node_name = validate_node_name(node_name)
            validated_node_type = validate_node_type(node_type)

            current_order = StateExecutionTracker.get_execution_order(state)

            state_tracker_logger.info(
                f"[STATE-TRACKER] Tracking node execution: {validated_node_name} "
                f"({validated_node_type}) at order {current_order}",
                extra={
                    "node_id": validated_node_id,
                    "node_name": validated_node_name,
                    "node_type": validated_node_type,
                    "execution_order": current_order,
                    "execution_id": state.get("execution_id"),
                },
            )

            # Get existing metadata safely
            existing_metadata = safe_get_metadata(state)

            # Create the state update
            update: StateUpdate = {
                "current_node": validated_node_id,
                "metadata": {
                    **existing_metadata,
                    "current_node_name": validated_node_name,
                    "current_node_type": validated_node_type,
                    "last_execution_order": current_order,
                },
            }

            # Add execution order increment for most node types
            # START and END nodes typically don't increment the order
            if validated_node_type not in ["START", "END"]:
                order_update = StateExecutionTracker.increment_execution_order(state)
                update.update(order_update)  # type: ignore

            return update
        except StateTrackingError:
            raise
        except Exception as e:
            state_tracker_logger.error(
                f"[STATE-TRACKER] Unexpected error tracking node execution: {e}",
                extra={
                    "error": str(e),
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                },
            )
            raise StateUpdateError(
                f"track node execution for {node_name}", str(e)
            ) from e

    @staticmethod
    def get_node_execution_info(state: WorkflowState) -> NodeExecutionInfo:
        """
        Get information about the current node execution from state.

        This method safely extracts node execution information from
        the state with proper validation and defaults.

        Args:
            state: The workflow state dictionary

        Returns:
            Dictionary with node execution information

        Raises:
            InvalidStateStructureError: If state is not a valid dictionary
            InvalidExecutionOrderError: If execution order in state is invalid

        Example:
            >>> state = {
            ...     "execution_order": 5,
            ...     "current_node": "node-123",
            ...     "metadata": {
            ...         "current_node_name": "My Agent",
            ...         "current_node_type": "AGENT"
            ...     }
            ... }
            >>> info = StateExecutionTracker.get_node_execution_info(state)
            >>> info["current_order"]
            5
        """
        try:
            validate_state_structure(state)
            metadata = safe_get_metadata(state)

            info: NodeExecutionInfo = {
                "current_order": StateExecutionTracker.get_execution_order(state),
            }

            # Add optional fields if present
            current_node = state.get("current_node")
            if current_node is not None:
                info["current_node"] = current_node

            node_name = metadata.get("current_node_name")
            if node_name is not None:
                info["node_name"] = node_name

            node_type = metadata.get("current_node_type")
            if node_type is not None:
                info["node_type"] = node_type

            return info
        except StateTrackingError:
            raise
        except Exception as e:
            state_tracker_logger.error(
                f"[STATE-TRACKER] Unexpected error getting node execution info: {e}",
                extra={"error": str(e)},
            )
            raise StateTrackingError(f"Failed to get node execution info: {e}") from e
