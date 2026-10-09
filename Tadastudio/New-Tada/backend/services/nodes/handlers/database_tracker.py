"""
Node Database Tracker.

This module provides shared functionality for tracking node executions
in the database. It's reusable across all node executor types.
"""

from typing import Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.execution.history import ExecutionHistoryService
from backend.services.config import get_logger
from backend.services.execution.state import StateExecutionTracker
from backend.services.workflow.state import WorkflowState


tracker_logger = get_logger("nodes.handlers.database_tracker")


class NodeDatabaseTracker:
    """
    Tracks node execution in the database.

    Provides methods for creating, updating, and completing node execution
    records in the execution history database.

    Example:
        >>> tracker = NodeDatabaseTracker()
        >>> node_id = await tracker.create_node_execution(node, state, "AGENT", input_data)
        >>> await tracker.complete_node_execution(node_id, output_data)
    """

    def __init__(self, execution_history_service: Optional[Any] = None):
        """
        Initialize database tracker.

        Args:
            execution_history_service: Optional service instance (uses global if not provided)
        """
        self.execution_history_service = (
            execution_history_service or ExecutionHistoryService
        )

    async def create_node_execution(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_type: str,
        input_data: Dict[str, Any],
        is_sub_agent: bool = False,
        parent_agent_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
    ) -> Optional[int]:
        """
        Create a node execution record in the database.

        Args:
            node: The node being executed
            state: Current workflow state
            node_type: Type of node (e.g., "AGENT", "HTTP_REQUEST")
            input_data: Input data for the node
            is_sub_agent: Whether this is a sub-agent
            parent_agent_id: Parent agent ID if this is a sub-agent
            review_iteration: Review iteration number (for multi-iteration review flows)

        Returns:
            Node execution ID, or None if tracking is disabled
        """
        db_execution_id = state.get("db_execution_id")
        if not db_execution_id:
            tracker_logger.debug(
                f"Database tracking disabled for {node.name} (no db_execution_id)"
            )
            return None

        try:
            current_order = StateExecutionTracker.get_execution_order(state)

            # STATUS-MISMATCH-DEBUG: Check for existing record to avoid duplicates on resume
            tracker_logger.info(
                f"[STATUS-DEBUG] create_node_execution called for {node.name} "
                f"(node_id={node.uniq_id}, type={node_type}, is_sub_agent={is_sub_agent})"
            )

            # Skip dedup for FOR_EACH body nodes — each iteration must get
            # its own record so the UI can track per-iteration status.
            is_for_each_body = state.get("__for_each_body_execution", False)

            # Check if there's already a paused record for this node
            # This happens when resuming after a sub-agent review pause
            if not is_for_each_body:
                existing_record = (
                    self.execution_history_service.get_node_execution_by_node_id(
                        graph_execution_id=db_execution_id,
                        node_id=node.uniq_id,
                    )
                )
                if existing_record:
                    existing_status = existing_record.get("status")
                    existing_id = existing_record.get("id")
                    tracker_logger.info(
                        f"[STATUS-DEBUG] Found existing record for {node.name}: "
                        f"id={existing_id}, status={existing_status}"
                    )

                    # If the existing record is paused or running, reuse it instead of creating duplicate
                    # This handles both first resume (paused→running) and subsequent resumes
                    # where status is still running from the previous resume cycle
                    if existing_status in ("paused", "running"):
                        tracker_logger.info(
                            f"[STATUS-DEBUG] Reusing {existing_status} record for {node.name} "
                            f"(id={existing_id}) - updating status to 'running'"
                        )
                        # Update the paused record to running
                        self.execution_history_service.start_node_execution(existing_id)
                        return existing_id

            tracker_logger.info(
                f"Creating node execution record for {node.name} "
                f"(type={node_type}, order={current_order})"
            )

            # Record which loop iteration a body node belongs to, so the UI can
            # group a loop's runs instead of showing repeated look-alike rows.
            node_metadata = None
            if is_for_each_body:
                node_metadata = {
                    "for_each": {
                        "node_id": state.get("__for_each_node_id"),
                        "iteration": state.get("__for_each_iteration_index"),
                        "total": state.get("__for_each_total"),
                    }
                }

            # Create node execution record
            node_exec = self.execution_history_service.create_node_execution(
                graph_execution_id=db_execution_id,
                node_id=node.uniq_id,
                node_name=node.name,
                node_type=node_type,
                execution_order=current_order,
                input_data=input_data,
                node_metadata=node_metadata,
                is_sub_agent=is_sub_agent,
                parent_agent_id=parent_agent_id,
                review_iteration=review_iteration,
            )
            node_exec_id = node_exec["id"]

            # Mark as started
            self.execution_history_service.start_node_execution(node_exec_id)

            tracker_logger.info(
                f"Created node execution record: {node_exec_id} for {node.name}"
            )

            return node_exec_id

        except Exception as e:
            tracker_logger.error(
                f"Failed to create node execution record for {node.name}: {e}",
                exc_info=True,
            )
            return None

    async def update_node_execution(
        self,
        node_exec_id: Optional[int],
        progress_data: Dict[str, Any],
    ) -> bool:
        """
        Update a node execution record with progress data.

        Args:
            node_exec_id: Node execution ID
            progress_data: Progress data to update

        Returns:
            True if update successful, False otherwise
        """
        if not node_exec_id:
            return False

        try:
            tracker_logger.debug(
                f"Updating node execution {node_exec_id} with progress data"
            )

            # This would update intermediate progress
            # For now, execution history service doesn't have an update method
            # but this provides the hook for future enhancement
            return True

        except Exception as e:
            tracker_logger.error(
                f"Failed to update node execution {node_exec_id}: {e}",
                exc_info=True,
            )
            return False

    async def complete_node_execution(
        self,
        node_exec_id: Optional[int],
        output_data: Dict[str, Any],
        token_counts: Optional[Dict[str, int]] = None,
        llm_metadata: Optional[Dict[str, Any]] = None,
        message_structure: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a node execution as completed.

        Args:
            node_exec_id: Node execution ID
            output_data: Output data from node execution
            token_counts: Optional token usage counts
            llm_metadata: Optional LLM metadata including cost information
            message_structure: Optional message structure for trace viewer

        Returns:
            True if completion successful, False otherwise
        """
        if not node_exec_id:
            return False

        try:
            # STATUS-MISMATCH-DEBUG: Get current status before completing
            try:
                current_record = (
                    self.execution_history_service.get_node_execution_by_id(
                        node_exec_id
                    )
                )
                if current_record:
                    tracker_logger.info(
                        f"[STATUS-DEBUG] complete_node_execution called for db_id={node_exec_id}: "
                        f"node_name={current_record.get('node_name')}, "
                        f"current_status={current_record.get('status')} -> will become 'completed'"
                    )
            except Exception:
                pass

            tracker_logger.info(f"Completing node execution {node_exec_id}")

            # Prepare output data
            complete_output = output_data.copy()

            # Pass token counts as separate parameter (NOT in output_data)
            # ExecutionHistoryService.complete_node_execution extracts these
            # into input_tokens, output_tokens, total_tokens database fields
            self.execution_history_service.complete_node_execution(
                node_execution_id=node_exec_id,
                status="completed",
                output_data=complete_output,
                token_counts=token_counts,
                llm_metadata=llm_metadata,
                message_structure=message_structure,
            )

            tracker_logger.info(f"Node execution {node_exec_id} marked as completed")
            return True

        except Exception as e:
            tracker_logger.error(
                f"Failed to complete node execution {node_exec_id}: {e}",
                exc_info=True,
            )
            return False

    async def fail_node_execution(
        self,
        node_exec_id: Optional[int],
        error_message: str,
        error_output: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a node execution as failed.

        Args:
            node_exec_id: Node execution ID
            error_message: Error message
            error_output: Optional error output data

        Returns:
            True if failure marking successful, False otherwise
        """
        if not node_exec_id:
            return False

        try:
            tracker_logger.warning(
                f"Marking node execution {node_exec_id} as failed: {error_message}"
            )

            output = error_output or {"error": error_message, "success": False}

            self.execution_history_service.complete_node_execution(
                node_execution_id=node_exec_id,
                status="failed",
                output_data=output,
                error_message=error_message,
            )

            tracker_logger.info(f"Node execution {node_exec_id} marked as failed")
            return True

        except Exception as e:
            tracker_logger.error(
                f"Failed to mark node execution {node_exec_id} as failed: {e}",
                exc_info=True,
            )
            return False

    def get_execution_order(self, state: WorkflowState) -> int:
        """
        Get current execution order from state.

        Args:
            state: Current workflow state

        Returns:
            Current execution order
        """
        return StateExecutionTracker.get_execution_order(state)

    def increment_execution_order(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Increment execution order in state.

        Args:
            state: Current workflow state

        Returns:
            State update dictionary with incremented order
        """
        current_order = self.get_execution_order(state)
        return StateExecutionTracker.set_execution_order(state, current_order + 1)
