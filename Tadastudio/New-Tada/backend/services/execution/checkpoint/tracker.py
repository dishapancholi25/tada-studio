"""
Checkpoint Iteration Tracker.

This module provides functionality for tracking checkpoint iterations
when checkpoints appear in loops. Each loop iteration gets a unique
checkpoint execution to support proper pause/resume behavior.
"""

from typing import Any, Dict

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState


tracker_logger = get_logger("execution.checkpoint.tracker")


class CheckpointIterationTracker:
    """
    Tracks checkpoint iterations for loop handling.

    When a checkpoint node appears in a loop, each pass through the loop
    should create a new checkpoint execution. This tracker manages the
    iteration numbers to ensure proper behavior.

    Example:
        Loop:
          - Node A
          - Checkpoint (iteration 1, then 2, then 3...)
          - Node B
          - Back to Node A

    Each time the checkpoint is reached, it gets a new iteration number.
    """

    @staticmethod
    def get_current_iteration(node: EnhancedNodeData, state: WorkflowState) -> int:
        """
        Get current iteration for a checkpoint node.

        Args:
            node: The checkpoint node
            state: Current workflow state

        Returns:
            Current iteration number (1-indexed)
        """
        checkpoint_iterations = state.get("checkpoint_iterations", {})
        current = checkpoint_iterations.get(node.uniq_id, 0) + 1

        tracker_logger.debug(
            f"Checkpoint {node.name} (ID: {node.uniq_id}): iteration {current}"
        )

        return current

    @staticmethod
    def update_iteration(
        node: EnhancedNodeData,
        state: WorkflowState,
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Update checkpoint iteration in state.

        Args:
            node: The checkpoint node
            state: Current workflow state
            iteration: New iteration number

        Returns:
            State update dict with updated checkpoint_iterations
        """
        checkpoint_iterations = state.get("checkpoint_iterations", {})
        updated_iterations = {**checkpoint_iterations, node.uniq_id: iteration}

        tracker_logger.debug(f"Updated checkpoint {node.name} to iteration {iteration}")

        return {"checkpoint_iterations": updated_iterations}

    @staticmethod
    def get_iteration_for_node(node_id: str, state: WorkflowState) -> int:
        """
        Get current iteration for a specific checkpoint node ID.

        Args:
            node_id: The checkpoint node ID
            state: Current workflow state

        Returns:
            Current iteration number (0 if never executed)
        """
        checkpoint_iterations = state.get("checkpoint_iterations", {})
        return checkpoint_iterations.get(node_id, 0)

    @staticmethod
    def reset_iteration(node: EnhancedNodeData, state: WorkflowState) -> Dict[str, Any]:
        """
        Reset iteration counter for a checkpoint node.

        Useful when restarting a loop or clearing checkpoint state.

        Args:
            node: The checkpoint node
            state: Current workflow state

        Returns:
            State update dict with reset iteration
        """
        checkpoint_iterations = state.get("checkpoint_iterations", {})
        updated_iterations = {**checkpoint_iterations, node.uniq_id: 0}

        tracker_logger.info(f"Reset checkpoint {node.name} iterations to 0")

        return {"checkpoint_iterations": updated_iterations}

    @staticmethod
    def get_all_iterations(state: WorkflowState) -> Dict[str, int]:
        """
        Get all checkpoint iterations from state.

        Args:
            state: Current workflow state

        Returns:
            Dict mapping node IDs to iteration numbers
        """
        return dict(state.get("checkpoint_iterations", {}))

    @staticmethod
    def clear_all_iterations(state: WorkflowState) -> Dict[str, Any]:
        """
        Clear all checkpoint iterations.

        Args:
            state: Current workflow state

        Returns:
            State update dict with empty iterations
        """
        tracker_logger.info("Cleared all checkpoint iterations")
        return {"checkpoint_iterations": {}}
