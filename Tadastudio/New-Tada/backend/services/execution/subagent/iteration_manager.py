"""Subagent Iteration State Manager.

This module manages persistent subagent iteration state across checkpoint boundaries,
ensuring proper iteration tracking for resume/retry operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.models.execution.subagent_iteration_state import SubagentIterationState
from backend.services.config import get_logger
from backend.services.database import get_db

logger = get_logger("execution.subagent.iteration_manager")


class SubagentIterationManager:
    """Manages persistent subagent iteration state.

    This class provides static methods for creating, updating, and retrieving
    subagent iteration state from the database. It tracks which iteration a
    subagent is on when called multiple times by a parent agent.
    """

    @staticmethod
    def get_or_create_iteration_state(
        graph_execution_id: str,
        parent_agent_id: str,
        subagent_node_id: str,
        thread_id: str,
    ) -> Dict[str, Any]:
        """Get existing or create new iteration state for a subagent.

        Args:
            graph_execution_id: Parent graph execution ID
            parent_agent_id: ID of the orchestrator calling the subagent
            subagent_node_id: Node identifier of the subagent
            thread_id: LangGraph thread ID

        Returns:
            Dictionary with iteration state fields including current_iteration
        """
        with get_db() as db:
            # Look for existing active iteration state
            existing = (
                db.query(SubagentIterationState)
                .filter(
                    SubagentIterationState.graph_execution_id == graph_execution_id,
                    SubagentIterationState.parent_agent_id == parent_agent_id,
                    SubagentIterationState.subagent_node_id == subagent_node_id,
                    SubagentIterationState.status == "active",
                )
                .first()
            )

            if existing:
                logger.info(
                    f"[ITERATION-STATE] Found existing state: id={existing.id}, "
                    f"iteration={existing.current_iteration}"
                )
                return _to_dict(existing)

            # Create new record
            iteration_state = SubagentIterationState(
                graph_execution_id=graph_execution_id,
                parent_agent_id=parent_agent_id,
                subagent_node_id=subagent_node_id,
                thread_id=thread_id,
                current_iteration=1,
                status="active",
                iteration_history=[],
            )

            db.add(iteration_state)
            db.commit()
            db.refresh(iteration_state)

            logger.info(
                f"[ITERATION-STATE] Created new state: id={iteration_state.id}, "
                f"subagent={subagent_node_id}"
            )

            return _to_dict(iteration_state)

    @staticmethod
    def increment_iteration(
        iteration_state_id: str,
        node_execution_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Increment iteration counter and record in history.

        Called when a subagent execution completes, preparing for the next
        potential invocation.

        Args:
            iteration_state_id: Iteration state ID
            node_execution_id: Database ID of the node execution for this iteration

        Returns:
            Updated iteration state dictionary, or None if not found
        """
        with get_db() as db:
            state = (
                db.query(SubagentIterationState)
                .filter(SubagentIterationState.id == iteration_state_id)
                .first()
            )

            if not state:
                logger.warning(
                    f"[ITERATION-STATE] Cannot increment: state {iteration_state_id} not found"
                )
                return None

            # Add current iteration to history
            history_entry = {
                "iteration": state.current_iteration,
                "node_execution_id": node_execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            current_history = state.iteration_history or []
            current_history.append(history_entry)

            # Increment
            state.iteration_history = current_history
            state.current_iteration += 1
            state.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(state)

            logger.info(
                f"[ITERATION-STATE] Incremented: id={iteration_state_id}, "
                f"new_iteration={state.current_iteration}"
            )

            return _to_dict(state)

    @staticmethod
    def get_current_iteration(
        graph_execution_id: str,
        parent_agent_id: str,
        subagent_node_id: str,
    ) -> int:
        """Get current iteration number for a subagent.

        Args:
            graph_execution_id: Parent graph execution ID
            parent_agent_id: ID of the orchestrator calling the subagent
            subagent_node_id: Node identifier of the subagent

        Returns:
            Current iteration number (1 if no state exists)
        """
        with get_db() as db:
            state = (
                db.query(SubagentIterationState)
                .filter(
                    SubagentIterationState.graph_execution_id == graph_execution_id,
                    SubagentIterationState.parent_agent_id == parent_agent_id,
                    SubagentIterationState.subagent_node_id == subagent_node_id,
                    SubagentIterationState.status == "active",
                )
                .first()
            )

            if state:
                return state.current_iteration
            return 1

    @staticmethod
    def complete_iteration_tracking(iteration_state_id: str) -> bool:
        """Mark iteration tracking as complete.

        Called when the graph execution completes or the parent agent finishes.

        Args:
            iteration_state_id: Iteration state ID

        Returns:
            True if updated successfully
        """
        with get_db() as db:
            state = (
                db.query(SubagentIterationState)
                .filter(SubagentIterationState.id == iteration_state_id)
                .first()
            )

            if not state:
                return False

            state.status = "completed"
            state.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"[ITERATION-STATE] Completed: id={iteration_state_id}")
            return True

    @staticmethod
    def get_by_id(iteration_state_id: str) -> Optional[Dict[str, Any]]:
        """Get iteration state by ID.

        Args:
            iteration_state_id: Iteration state ID

        Returns:
            Dictionary with iteration state fields, or None if not found
        """
        with get_db() as db:
            state = (
                db.query(SubagentIterationState)
                .filter(SubagentIterationState.id == iteration_state_id)
                .first()
            )

            if state:
                return _to_dict(state)
            return None


def _to_dict(state: SubagentIterationState) -> Dict[str, Any]:
    """Convert SubagentIterationState to dictionary."""
    return {
        "id": str(state.id),
        "graph_execution_id": state.graph_execution_id,
        "parent_agent_id": state.parent_agent_id,
        "subagent_node_id": state.subagent_node_id,
        "thread_id": state.thread_id,
        "current_iteration": state.current_iteration,
        "status": state.status,
        "iteration_history": state.iteration_history or [],
        "created_at": state.created_at.isoformat() if state.created_at else None,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }
