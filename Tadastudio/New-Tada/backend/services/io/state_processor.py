"""
State Processor.

Processes state updates for real-time tracking.
"""

from typing import Any, Dict, Optional

from backend.services.config import get_logger


state_processor_logger = get_logger("io.state_processor")


class StateProcessor:
    """
    Processes state updates for real-time workflow tracking.

    Updates active execution tracking and prepares for WebSocket events.
    """

    def __init__(self, active_executions: dict):
        """
        Initialize the state processor.

        Args:
            active_executions: Dictionary tracking active executions
        """
        self.active_executions = active_executions

    async def process_update(
        self,
        state_update: Dict[str, Any],
        execution_id: str,
        db_execution_id: Optional[int],
    ):
        """
        Process state updates for real-time tracking.

        Args:
            state_update: State update data
            execution_id: Execution identifier
            db_execution_id: Optional database execution ID
        """
        # Guard against non-dict updates (can happen during interrupts)
        if not isinstance(state_update, dict):
            state_processor_logger.debug(
                f"Skipping non-dict state update for {execution_id}: "
                f"type={type(state_update)}"
            )
            return

        # Update active execution tracking
        if execution_id in self.active_executions:
            self._update_current_node(state_update, execution_id)
            self._update_metadata(state_update, execution_id)

        # Log state update for debugging
        state_processor_logger.debug(
            f"State update for {execution_id}: "
            f"current_node={state_update.get('current_node')}"
        )

    def _update_current_node(self, state_update: Dict[str, Any], execution_id: str):
        """
        Update current node in execution tracking.

        Args:
            state_update: State update data
            execution_id: Execution identifier
        """
        if "current_node" in state_update:
            self.active_executions[execution_id]["current_node"] = state_update[
                "current_node"
            ]

    def _update_metadata(self, state_update: Dict[str, Any], execution_id: str):
        """
        Update metadata in execution tracking.

        Args:
            state_update: State update data
            execution_id: Execution identifier
        """
        if "metadata" in state_update:
            metadata = state_update["metadata"]
            if "current_node_name" in metadata:
                self.active_executions[execution_id]["current_node_name"] = metadata[
                    "current_node_name"
                ]
