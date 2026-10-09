"""Agent Review State Manager.

This module manages persistent agent review state across checkpoint boundaries,
solving the LangGraph limitation where interrupt() returns stale values during
resume operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models.execution.agent_review_state import AgentReviewState
from backend.services.config import get_logger
from backend.services.database import get_db

logger = get_logger("execution.review.state_manager")


class AgentReviewStateManager:
    """Manages persistent agent review state.

    This class provides static methods for creating, updating, and retrieving
    agent review state from the database. It serves as the single source of
    truth for review context during execution.

    The manager handles:
    - Creating review state before interrupt
    - Retrieving pending reviews for resume detection
    - Storing user resume responses
    - Tracking feedback history across iterations
    - Linking checkpoint IDs after interrupt
    """

    @staticmethod
    def create_or_update_review_state(
        graph_execution_id: str,
        agent_node_id: str,
        thread_id: str,
        agent_output: str,
        review_mode: str = "human",
        review_prompt: Optional[str] = None,
        max_iterations: int = 3,
        current_iteration: int = 1,
        review_history: Optional[List[Dict[str, Any]]] = None,
        input_message: Optional[str] = None,
        review_config: Optional[Dict[str, Any]] = None,
        node_execution_id: Optional[str] = None,
        agent_node_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update review state before interrupt.

        If a pending review already exists for this execution/node combination,
        it will be updated. Otherwise, a new record is created.

        Args:
            graph_execution_id: Parent graph execution ID
            agent_node_id: Node identifier within the graph
            thread_id: LangGraph thread ID
            agent_output: The agent's output being reviewed
            review_mode: Review type - "human" or "llm"
            review_prompt: Guidance for reviewers
            max_iterations: Maximum allowed iterations
            current_iteration: Current iteration number (1-indexed)
            review_history: Previous review iterations
            input_message: Original input for re-execution
            review_config: Full review configuration
            node_execution_id: Associated node execution ID

        Returns:
            Dictionary with review state fields including the ID
        """
        with get_db() as db:
            # Check for existing pending review
            existing = (
                db.query(AgentReviewState)
                .filter(
                    AgentReviewState.graph_execution_id == graph_execution_id,
                    AgentReviewState.agent_node_id == agent_node_id,
                    AgentReviewState.status == "pending_review",
                )
                .first()
            )

            if existing:
                # Update existing record
                existing.current_agent_output = agent_output
                existing.current_iteration = current_iteration
                existing.review_history = review_history or []
                existing.input_message = input_message
                existing.updated_at = datetime.now(timezone.utc)
                if node_execution_id:
                    existing.node_execution_id = node_execution_id
                if agent_node_name:
                    existing.agent_node_name = agent_node_name

                db.commit()
                db.refresh(existing)

                logger.info(
                    f"[REVIEW-STATE] Updated review state: id={existing.id}, "
                    f"iteration={current_iteration}"
                )

                return _to_dict(existing)

            # Create new record
            review_state = AgentReviewState(
                graph_execution_id=graph_execution_id,
                node_execution_id=node_execution_id,
                agent_node_id=agent_node_id,
                agent_node_name=agent_node_name,
                thread_id=thread_id,
                status="pending_review",
                current_iteration=current_iteration,
                max_iterations=max_iterations,
                review_mode=review_mode,
                review_prompt=review_prompt,
                current_agent_output=agent_output,
                review_history=review_history or [],
                input_message=input_message,
                review_config=review_config,
            )

            db.add(review_state)
            db.commit()
            db.refresh(review_state)

            logger.info(
                f"[REVIEW-STATE] Created review state: id={review_state.id}, "
                f"node={agent_node_id}, mode={review_mode}"
            )

            return _to_dict(review_state)

    @staticmethod
    def get_pending_review(
        graph_execution_id: str,
        agent_node_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get pending review state for an agent node.

        This is the primary method used during resume to detect if we're
        resuming from an agent review interrupt.

        Args:
            graph_execution_id: Parent graph execution ID
            agent_node_id: Node identifier within the graph

        Returns:
            Dictionary with review state fields, or None if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(
                    AgentReviewState.graph_execution_id == graph_execution_id,
                    AgentReviewState.agent_node_id == agent_node_id,
                    AgentReviewState.status == "pending_review",
                )
                .first()
            )

            if review_state:
                return _to_dict(review_state)
            return None

    @staticmethod
    def get_pending_by_execution(
        graph_execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get any pending review state for an execution.

        Used by the API to return review context when loading paused executions.

        Args:
            graph_execution_id: Parent graph execution ID

        Returns:
            Dictionary with review state fields, or None if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(
                    AgentReviewState.graph_execution_id == graph_execution_id,
                    AgentReviewState.status == "pending_review",
                )
                .first()
            )

            if review_state:
                return _to_dict(review_state)
            return None

    @staticmethod
    def get_by_checkpoint_id(checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get review state by checkpoint ID.

        Used for frontend detection of agent review pauses.

        Args:
            checkpoint_id: LangGraph checkpoint ID

        Returns:
            Dictionary with review state fields, or None if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.checkpoint_id == checkpoint_id)
                .first()
            )

            if review_state:
                return _to_dict(review_state)
            return None

    @staticmethod
    def update_checkpoint_id(review_state_id: str, checkpoint_id: str) -> bool:
        """Update checkpoint ID after interrupt creates checkpoint.

        Args:
            review_state_id: Review state ID
            checkpoint_id: LangGraph checkpoint ID

        Returns:
            True if updated successfully, False if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.id == review_state_id)
                .first()
            )

            if not review_state:
                logger.warning(
                    f"[REVIEW-STATE] Cannot update checkpoint_id: "
                    f"state {review_state_id} not found"
                )
                return False

            review_state.checkpoint_id = checkpoint_id
            review_state.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"[REVIEW-STATE] Updated checkpoint_id: state={review_state_id}, "
                f"checkpoint={checkpoint_id}"
            )
            return True

    @staticmethod
    def set_resume_response(
        review_state_id: str,
        resume_response: Dict[str, Any],
    ) -> bool:
        """Store the user's resume response.

        Called by resume_handler when the user submits their review.

        Args:
            review_state_id: Review state ID
            resume_response: User's response (approved/feedback)

        Returns:
            True if updated successfully, False if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.id == review_state_id)
                .first()
            )

            if not review_state:
                logger.warning(
                    f"[REVIEW-STATE] Cannot set resume_response: "
                    f"state {review_state_id} not found"
                )
                return False

            review_state.resume_response = resume_response
            review_state.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"[REVIEW-STATE] Set resume_response: state={review_state_id}, "
                f"approved={resume_response.get('approved')}"
            )
            return True

    @staticmethod
    def clear_resume_response(review_state_id: str) -> bool:
        """Clear the resume response after it has been processed.

        This prevents the same response from being processed again on
        the next iteration of the review loop.

        Args:
            review_state_id: Review state ID

        Returns:
            True if cleared successfully, False if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.id == review_state_id)
                .first()
            )

            if not review_state:
                logger.warning(
                    f"[REVIEW-STATE] Cannot clear resume_response: "
                    f"state {review_state_id} not found"
                )
                return False

            review_state.resume_response = None
            review_state.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"[REVIEW-STATE] Cleared resume_response for state={review_state_id}"
            )
            return True

    @staticmethod
    def add_feedback_to_history(
        review_state_id: str,
        feedback: str,
        agent_output: str,
        reviewer_type: str = "human",
    ) -> bool:
        """Add feedback entry to review history.

        Called after rejection to track the feedback for this iteration.

        Args:
            review_state_id: Review state ID
            feedback: Feedback given
            agent_output: The agent output that was reviewed
            reviewer_type: Either "human" or "llm"

        Returns:
            True if updated successfully, False if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.id == review_state_id)
                .first()
            )

            if not review_state:
                logger.warning(
                    f"[REVIEW-STATE] Cannot add feedback: "
                    f"state {review_state_id} not found"
                )
                return False

            # Build new history entry
            history_entry = {
                "iteration": review_state.current_iteration,
                "agent_output": agent_output,
                "feedback": feedback,
                "reviewer_type": reviewer_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Append to history
            current_history = review_state.review_history or []
            current_history.append(history_entry)

            review_state.review_history = current_history
            review_state.current_iteration += 1
            review_state.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"[REVIEW-STATE] Added feedback: state={review_state_id}, "
                f"iteration={review_state.current_iteration}"
            )
            return True

    @staticmethod
    def complete_review(
        review_state_id: str,
        status: str = "approved",
    ) -> bool:
        """Mark review as complete.

        Args:
            review_state_id: Review state ID
            status: Final status - "approved", "rejected", or "max_iterations"

        Returns:
            True if updated successfully, False if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.id == review_state_id)
                .first()
            )

            if not review_state:
                logger.warning(
                    f"[REVIEW-STATE] Cannot complete: state {review_state_id} not found"
                )
                return False

            review_state.status = status
            review_state.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"[REVIEW-STATE] Completed review: state={review_state_id}, "
                f"status={status}"
            )
            return True

    @staticmethod
    def get_by_id(review_state_id: str) -> Optional[Dict[str, Any]]:
        """Get review state by ID.

        Args:
            review_state_id: Review state ID

        Returns:
            Dictionary with review state fields, or None if not found
        """
        with get_db() as db:
            review_state = (
                db.query(AgentReviewState)
                .filter(AgentReviewState.id == review_state_id)
                .first()
            )

            if review_state:
                return _to_dict(review_state)
            return None


def _to_dict(review_state: AgentReviewState) -> Dict[str, Any]:
    """Convert AgentReviewState to dictionary.

    Args:
        review_state: AgentReviewState instance

    Returns:
        Dictionary representation
    """
    return {
        "id": str(review_state.id),
        "graph_execution_id": review_state.graph_execution_id,
        "node_execution_id": review_state.node_execution_id,
        "agent_node_id": review_state.agent_node_id,
        "agent_node_name": review_state.agent_node_name,
        "checkpoint_id": review_state.checkpoint_id,
        "thread_id": review_state.thread_id,
        "status": review_state.status,
        "current_iteration": review_state.current_iteration,
        "max_iterations": review_state.max_iterations,
        "review_mode": review_state.review_mode,
        "review_prompt": review_state.review_prompt,
        "current_agent_output": review_state.current_agent_output,
        "review_history": review_state.review_history or [],
        "input_message": review_state.input_message,
        "resume_response": review_state.resume_response,
        "review_config": review_state.review_config,
        "created_at": (
            review_state.created_at.isoformat() if review_state.created_at else None
        ),
        "updated_at": (
            review_state.updated_at.isoformat() if review_state.updated_at else None
        ),
    }
