"""Service layer for managing paused executions."""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from ....services.config import get_logger
from .checkpoint_handler import CheckpointHandler
from .models import PausedExecutionSummary
from .queries import (
    get_all_paused_executions,
    get_checkpoint_node,
    get_execution_by_id,
    get_node_executions_by_execution_id,
    get_paused_executions_by_graph,
    get_paused_nodes_by_execution_id,
    get_previous_node,
)


# Get logger
logger = get_logger(__name__)


class PausedExecutionService:
    """
    Service for managing paused workflow executions.

    This service provides business logic for querying, inspecting, and
    managing workflow executions that are paused at checkpoints.

    Attributes:
        checkpoint_handler: Handler for checkpoint-related operations
    """

    def __init__(self, execution_engine: Any):
        """
        Initialize the paused execution service.

        Args:
            execution_engine: The LangGraph execution engine instance
        """
        self.checkpoint_handler = CheckpointHandler(execution_engine)
        logger.info("[PAUSED-EXEC-SERVICE] Initialized paused execution service")

    def get_paused_executions_by_graph(
        self, db: Session, graph_name: str, skip: int = 0, limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get all paused executions for a specific graph with pagination.

        Args:
            db: Database session
            graph_name: Name of the graph/workflow
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            Dictionary with paused execution summaries and pagination info

        Raises:
            Exception: If database query fails
        """
        logger.debug(
            f"[PAUSED-EXEC-SERVICE] Fetching paused executions for graph: "
            f"{graph_name} (skip={skip}, limit={limit})"
        )

        # Query for paused executions
        paused_executions, total_count = get_paused_executions_by_graph(
            db, graph_name, skip, limit
        )

        # Build summaries
        summaries = []
        for execution in paused_executions:
            checkpoint_node = get_checkpoint_node(db, execution.id)
            summary = PausedExecutionSummary(execution, checkpoint_node)
            summaries.append(summary.to_dict())

        # Calculate pagination metadata
        has_more = (skip + limit) < total_count
        next_skip = skip + limit if has_more else None

        logger.debug(
            f"[PAUSED-EXEC-SERVICE] Returning {len(summaries)} paused executions "
            f"for {graph_name}"
        )

        return {
            "executions": summaries,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
                "next_skip": next_skip,
            },
        }

    def get_all_paused_executions(
        self, db: Session, is_visible: Optional[Callable[[Any], bool]] = None
    ) -> Dict[str, Any]:
        """
        Get paused executions across all graphs.

        Args:
            db: Database session
            is_visible: Optional predicate deciding whether an execution may be
                shown to the caller. Applied before grouping so the returned
                total reflects only visible executions. Callers that omit it
                receive every paused execution, so API routes must supply one.

        Returns:
            Dictionary with graph names as keys and paused executions as values

        Raises:
            Exception: If database query fails
        """
        logger.info("[PAUSED-EXEC-SERVICE] Fetching all paused executions")

        # Query for all paused executions
        paused_executions = get_all_paused_executions(db)

        if is_visible is not None:
            total = len(paused_executions)
            paused_executions = [e for e in paused_executions if is_visible(e)]
            logger.info(
                f"[PAUSED-EXEC-SERVICE] Caller may view "
                f"{len(paused_executions)} of {total} paused executions"
            )

        # Group by graph name
        grouped = {}
        for execution in paused_executions:
            if execution.graph_name not in grouped:
                grouped[execution.graph_name] = []

            checkpoint_node = get_checkpoint_node(db, execution.id)
            summary = PausedExecutionSummary(execution, checkpoint_node)
            grouped[execution.graph_name].append(summary.to_dict())

        logger.info(
            f"[PAUSED-EXEC-SERVICE] Returning {len(paused_executions)} "
            f"total paused executions across {len(grouped)} graphs"
        )

        return {"total_paused": len(paused_executions), "by_graph": grouped}

    def get_execution_state(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """
        Get the complete state of an execution.

        This includes all node executions, checkpoint information, and
        graph definition.

        Args:
            db: Database session
            execution_id: The database execution ID

        Returns:
            Complete execution state with node history

        Raises:
            ValueError: If execution not found
            Exception: If database query fails
        """
        logger.info(
            f"[PAUSED-EXEC-SERVICE] Fetching execution state for: {execution_id}"
        )

        # Get the execution
        execution = get_execution_by_id(db, execution_id)
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")

        # Get all node executions
        node_executions = get_node_executions_by_execution_id(db, execution_id)

        # Find checkpoint info if paused
        checkpoint_info = None
        if execution.status == "paused":
            checkpoint_info = self._get_checkpoint_info_for_paused_execution(
                db, execution, node_executions
            )

        # Check if LangGraph checkpoint exists for resume capability
        can_resume = self.checkpoint_handler.can_resume_from_checkpoint(
            execution.thread_id
        )

        # Build node execution history
        nodes = self.checkpoint_handler.build_node_execution_details(node_executions)

        logger.info(
            f"[PAUSED-EXEC-SERVICE] Returning state for execution {execution_id} "
            f"with {len(nodes)} nodes (can_resume={can_resume})"
        )

        return {
            "execution": {
                "id": execution.id,
                "thread_id": execution.thread_id,
                "websocket_execution_id": execution.websocket_execution_id,
                "graph_name": execution.graph_name,
                "status": execution.status,
                "created_at": execution.created_at.isoformat(),
                "input_data": execution.input_data,
                "output_data": execution.output_data,
                "error_message": execution.error_message,
            },
            "nodes": nodes,
            "checkpoint_state": checkpoint_info,
            "can_resume": can_resume,
            "graph_definition": execution.graph_definition,
        }

    def cancel_paused_execution(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """
        Cancel a paused execution.

        Args:
            db: Database session
            execution_id: The database execution ID to cancel

        Returns:
            Status of the cancellation

        Raises:
            ValueError: If execution not found or not paused
            Exception: If database update fails
        """
        logger.info(
            f"[PAUSED-EXEC-SERVICE] Cancelling paused execution: {execution_id}"
        )

        # Get the execution
        execution = get_execution_by_id(db, execution_id)
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.status != "paused":
            raise ValueError(f"Execution is not paused (status: {execution.status})")

        # Update execution status
        execution.status = "cancelled"
        execution.end_time = datetime.utcnow()

        # Update any paused checkpoint nodes
        paused_nodes = get_paused_nodes_by_execution_id(db, execution_id)
        for node in paused_nodes:
            node.status = "cancelled"
            node.end_time = datetime.utcnow()

        db.commit()

        logger.info(
            f"[PAUSED-EXEC-SERVICE] Successfully cancelled execution: {execution_id} "
            f"(updated {len(paused_nodes)} paused nodes)"
        )

        return {
            "status": "cancelled",
            "execution_id": execution_id,
            "message": "Execution cancelled successfully",
        }

    def get_checkpoint_data(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """
        Get checkpoint-specific data for resuming an execution.

        Args:
            db: Database session
            execution_id: The database execution ID

        Returns:
            Checkpoint data needed for resuming

        Raises:
            ValueError: If execution not found, not paused, or no checkpoint found
            Exception: If database query fails
        """
        logger.info(
            f"[PAUSED-EXEC-SERVICE] Fetching checkpoint data for execution: {execution_id}"
        )

        # Get the execution
        execution = get_execution_by_id(db, execution_id)
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.status != "paused":
            raise ValueError(f"Execution is not paused (status: {execution.status})")

        # Find the checkpoint node
        checkpoint_node = get_checkpoint_node(db, execution_id)
        if not checkpoint_node:
            raise ValueError(
                f"No paused checkpoint found for execution: {execution_id}"
            )

        # Get the previous node's output
        previous_node = get_previous_node(
            db, execution_id, checkpoint_node.execution_order
        )

        # Get checkpoint info for resumption
        checkpoint_info = self.checkpoint_handler.get_checkpoint_info_for_resume(
            checkpoint_node, previous_node, execution.thread_id
        )

        logger.info(
            f"[PAUSED-EXEC-SERVICE] Returning checkpoint data for execution {execution_id}"
        )

        return {
            "execution_id": execution_id,
            "thread_id": execution.thread_id,
            "websocket_execution_id": execution.websocket_execution_id,
            "checkpoint": checkpoint_info,
            "graph_name": execution.graph_name,
        }

    def _get_checkpoint_info_for_paused_execution(
        self, db: Session, execution: Any, node_executions: List[Any]
    ) -> Dict[str, Any]:
        """
        Get checkpoint info for a paused execution.

        Args:
            db: Database session
            execution: GraphExecution database model
            node_executions: List of NodeExecution models

        Returns:
            Checkpoint information dictionary or None
        """
        # First, check for pending agent review state (new system)
        agent_review_info = self._get_agent_review_checkpoint_info(str(execution.id))
        if agent_review_info:
            logger.info(
                f"[PAUSED-EXEC-SERVICE] Found agent review state for "
                f"paused execution {execution.id}"
            )
            return agent_review_info

        # Fall back to regular checkpoint node lookup
        checkpoint_node = next(
            (
                n
                for n in node_executions
                if n.node_type == "CHECKPOINT" and n.status == "paused"
            ),
            None,
        )

        if not checkpoint_node:
            logger.debug(
                f"[PAUSED-EXEC-SERVICE] No checkpoint node found for "
                f"paused execution {execution.id}"
            )
            return None

        return self.checkpoint_handler.get_checkpoint_info(
            checkpoint_node, execution.thread_id
        )

    def _get_agent_review_checkpoint_info(
        self, execution_id: str
    ) -> Dict[str, Any] | None:
        """
        Get agent review checkpoint info if a pending review exists.

        Args:
            execution_id: The graph execution ID

        Returns:
            Agent review checkpoint info or None if no pending review
        """
        try:
            from backend.services.execution.review.state_manager import (
                AgentReviewStateManager,
            )

            review_state = AgentReviewStateManager.get_pending_by_execution(
                execution_id
            )

            if not review_state:
                return None

            # Build the interrupt payload matching frontend expectations
            interrupt_payload = {
                "type": "agent_review",
                "node_id": review_state.get("agent_node_id"),
                "node_name": review_state.get("agent_node_name")
                or review_state.get("agent_node_id"),
                "agent_output": review_state.get("current_agent_output"),
                "review_prompt": review_state.get("review_prompt"),
                "review_mode": review_state.get("review_mode", "human"),
                "current_iteration": review_state.get("current_iteration", 1),
                "max_iterations": review_state.get("max_iterations", 3),
                "review_history": review_state.get("review_history", []),
            }

            return {
                "checkpoint_id": review_state.get("checkpoint_id"),
                "review_checkpoint": True,
                "node_id": review_state.get("agent_node_id"),
                "thread_id": review_state.get("thread_id"),
                "interrupt_payload": interrupt_payload,
            }

        except Exception as e:
            logger.warning(
                f"[PAUSED-EXEC-SERVICE] Failed to get agent review info: {e}"
            )
            return None
