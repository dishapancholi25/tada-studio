"""
Review node for sub-agent subgraphs.

This module provides the review node that handles human-in-the-loop
and LLM review for sub-agent outputs within subgraphs. It mirrors the
pattern in backend/services/nodes/executors/review.py for regular agents.
"""

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.execution.review.executor import ReviewExecutor
from backend.services.common.utils.websocket_notifier import ws_notifier

if TYPE_CHECKING:
    pass

review_node_logger = get_logger("subgraph.agent.review_node")


class SubAgentReviewNodeFactory:
    """
    Factory for creating review node functions for sub-agent subgraphs.

    Creates async functions that can be added to a sub-agent StateGraph.
    Each review node:
    1. Reads agent output from state.review_state
    2. Calls interrupt() ONCE for human review (deterministic)
    3. Processes the response and returns routing decision
    4. Updates state with feedback history if rejected
    """

    def __init__(
        self,
        llm_factory: Optional[Any] = None,
        model_service: Optional[Any] = None,
    ):
        """
        Initialize the review node function factory.

        Args:
            llm_factory: Factory for creating LLM instances (for LLM review)
            model_service: Service for model deployment (for LLM review)
        """
        self.llm_factory = llm_factory
        self.model_service = model_service
        self.review_executor = ReviewExecutor(
            llm_factory=llm_factory,
            model_service=model_service,
        )

    def create_review_function(
        self,
        agent_node: EnhancedNodeData,
    ) -> Callable:
        """
        Create a review node function for the given sub-agent.

        Args:
            agent_node: The agent node this review node is for

        Returns:
            An async function that can be added to a StateGraph
        """
        agent_node_id = agent_node.uniq_id
        agent_node_name = agent_node.name

        async def review_node_function(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Execute review for the sub-agent's output.

            This function:
            1. Reads review data from state.review_state
            2. If no review data, routes to continue (passthrough)
            3. For human review, calls interrupt() ONCE
            4. For LLM review, calls LLM synchronously
            5. Returns routing decision and state updates

            Returns:
                Dict with:
                - __review_route: "continue" (approved) or "retry" (rejected)
                - review_state: Updated review state
            """
            review_node_logger.info(
                f"[SUBAGENT-REVIEW-NODE] Executing review for: {agent_node_name}"
            )

            # Get review data from state
            review_state = state.get("review_state") or {}

            review_node_logger.debug(
                f"[SUBAGENT-REVIEW-NODE] State review_state: {review_state}"
            )

            if not review_state:
                review_node_logger.info(
                    f"[SUBAGENT-REVIEW-NODE] No review data for {agent_node_name}, "
                    "passing through"
                )
                return {"__review_route": "continue"}

            # Extract review context
            agent_output = review_state.get("output", "")
            config = review_state.get("config", {})
            iteration = review_state.get("iteration", 1)
            history = review_state.get("history", [])
            max_iterations = config.get("max_iterations", 3)
            review_mode = config.get("review_mode", "human")
            review_prompt = config.get("review_prompt", "Review the output")

            review_node_logger.info(
                f"[SUBAGENT-REVIEW-NODE] {agent_node_name} - Mode: {review_mode}, "
                f"Iteration: {iteration}/{max_iterations}"
            )

            # Check max iterations before review
            if iteration > max_iterations:
                review_node_logger.warning(
                    f"[SUBAGENT-REVIEW-NODE] Max iterations reached for {agent_node_name}, "
                    "auto-approving"
                )
                return _build_approved_response()

            # Execute review based on mode
            if review_mode == "human":
                result = await self._execute_human_review(
                    state=state,
                    agent_node_id=agent_node_id,
                    agent_node_name=agent_node_name,
                    agent_output=agent_output,
                    review_prompt=review_prompt,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    history=history,
                )
            else:
                # LLM review - synchronous, no interrupt
                result = await self._execute_llm_review(
                    agent_node_id=agent_node_id,
                    agent_node_name=agent_node_name,
                    agent_output=agent_output,
                    review_prompt=review_prompt,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    history=history,
                    config=config,
                )

            # Process result
            if result.get("approved"):
                review_node_logger.info(
                    f"[SUBAGENT-REVIEW-NODE] {agent_node_name} output APPROVED"
                )
                return _build_approved_response()
            else:
                feedback = result.get("feedback", "")
                review_node_logger.info(
                    f"[SUBAGENT-REVIEW-NODE] {agent_node_name} output REJECTED - "
                    f"Feedback: {feedback[:100]}..."
                )
                return _build_rejected_response(
                    review_state=review_state,
                    feedback=feedback,
                    reviewer_type=review_mode,
                    llm_metadata=result.get("llm_metadata"),
                )

        return review_node_function

    async def _execute_human_review(
        self,
        state: Dict[str, Any],
        agent_node_id: str,
        agent_node_name: str,
        agent_output: str,
        review_prompt: str,
        iteration: int,
        max_iterations: int,
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute human review using LangGraph's interrupt().

        Args:
            state: Current sub-agent state
            agent_node_id: ID of the agent being reviewed
            agent_node_name: Name of the agent
            agent_output: Output to review
            review_prompt: Criteria for review
            iteration: Current iteration number
            max_iterations: Maximum allowed iterations
            history: Previous review feedback history

        Returns:
            Review result dictionary with approved/feedback
        """
        from langgraph.types import interrupt

        # Build interrupt payload with sub-agent context
        interrupt_payload = {
            "type": "agent_review",
            "node_id": agent_node_id,
            "node_name": agent_node_name,
            "agent_output": agent_output,
            "review_prompt": review_prompt,
            "review_mode": "human",
            "current_iteration": iteration,
            "max_iterations": max_iterations,
            "review_history": history,
            "is_sub_agent": True,
            "parent_node_id": state.get("parent_node_id"),
            "parent_node_name": state.get("parent_node_name"),
        }

        review_node_logger.info(
            f"[SUBAGENT-REVIEW-NODE] Sending WebSocket pause notification for {agent_node_name}"
        )

        # Send WebSocket notification
        ws_execution_id = state.get("parent_execution_id")
        if ws_notifier and ws_execution_id:
            try:
                await ws_notifier.on_execution_paused(
                    ws_execution_id,
                    {
                        "thread_id": ws_execution_id,
                        "node_id": agent_node_id,
                        "node_name": agent_node_name,
                        "prompt": interrupt_payload,
                        "review_type": "agent_review",
                        "is_sub_agent": True,
                    },
                )
                review_node_logger.info(
                    f"[SUBAGENT-REVIEW-NODE] WebSocket pause notification sent for {agent_node_name}"
                )
            except Exception as e:
                review_node_logger.error(
                    f"[SUBAGENT-REVIEW-NODE] Failed to send WebSocket notification: {e}"
                )

        # Store review state in database for resume detection
        from backend.services.execution.review.state_manager import (
            AgentReviewStateManager,
        )

        graph_execution_id = state.get("parent_db_execution_id")
        if graph_execution_id:
            AgentReviewStateManager.create_or_update_review_state(
                graph_execution_id=str(graph_execution_id),
                agent_node_id=agent_node_id,
                thread_id=str(ws_execution_id) if ws_execution_id else "",
                agent_output=agent_output,
                review_mode="human",
                review_prompt=review_prompt,
                max_iterations=max_iterations,
                current_iteration=iteration,
                review_history=history,
                input_message=state.get("task_description"),
                review_config={
                    "review_enabled": True,
                    "review_mode": "human",
                    "review_prompt": review_prompt,
                    "max_iterations": max_iterations,
                },
                agent_node_name=agent_node_name,
            )
            review_node_logger.info(
                f"[SUBAGENT-REVIEW-NODE] Stored review state for {agent_node_name}"
            )

        review_node_logger.info(
            f"[SUBAGENT-REVIEW-NODE] Calling interrupt() for {agent_node_name}"
        )

        # Single deterministic interrupt call
        response = interrupt(interrupt_payload)

        review_node_logger.info(
            f"[SUBAGENT-REVIEW-NODE] Received resume response for {agent_node_name}: {response}"
        )

        # Process response
        return _process_human_response(response, iteration)

    async def _execute_llm_review(
        self,
        agent_node_id: str,
        agent_node_name: str,
        agent_output: str,
        review_prompt: str,
        iteration: int,
        max_iterations: int,
        history: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute LLM review synchronously (no interrupt).

        Args:
            agent_node_id: ID of the agent being reviewed
            agent_node_name: Name of the agent
            agent_output: Output to review
            review_prompt: Criteria for review
            iteration: Current iteration number
            max_iterations: Maximum allowed iterations
            history: Previous review feedback history
            config: Full review config dict including reviewer_llm_config

        Returns:
            Review result dictionary
        """
        review_node_logger.info(
            f"[SUBAGENT-REVIEW-NODE] Executing LLM review for {agent_node_name}"
        )

        # Check if LLM factory is configured
        if not self.llm_factory or not self.model_service:
            review_node_logger.warning(
                f"[SUBAGENT-REVIEW-NODE] No LLM factory configured for {agent_node_name}, "
                "auto-approving"
            )
            return {"approved": True, "iteration": iteration}

        # Get reviewer_llm_config from the config dict
        reviewer_llm_config_dict = config.get("reviewer_llm_config")

        if not reviewer_llm_config_dict:
            review_node_logger.warning(
                f"[SUBAGENT-REVIEW-NODE] No reviewer_llm_config for {agent_node_name}, "
                "auto-approving"
            )
            return {"approved": True, "iteration": iteration}

        try:
            from backend.models.workflow.configs import LLMConfig, ReviewConfig

            # Build ReviewConfig for the executor
            reviewer_llm_config = LLMConfig(**reviewer_llm_config_dict)
            review_config = ReviewConfig(
                review_enabled=True,
                review_mode="llm",
                review_prompt=review_prompt,
                max_iterations=max_iterations,
                reviewer_llm_config=reviewer_llm_config,
            )

            # Create mock node for ReviewExecutor
            from unittest.mock import MagicMock

            mock_node = MagicMock()
            mock_node.uniq_id = agent_node_id
            mock_node.name = agent_node_name

            # Delegate to ReviewExecutor
            result = await self.review_executor._execute_llm_review(
                node=mock_node,
                state={},  # State not needed for LLM review
                agent_output=agent_output,
                review_config=review_config,
                review_history=history,
                current_iteration=iteration,
            )

            review_node_logger.info(
                f"[SUBAGENT-REVIEW-NODE] LLM review result for {agent_node_name}: "
                f"approved={result.get('approved')}"
            )

            return {
                "approved": result.get("approved", False),
                "feedback": result.get("feedback", ""),
                "iteration": iteration,
                "llm_metadata": result.get("llm_metadata"),
            }

        except Exception as e:
            review_node_logger.error(
                f"[SUBAGENT-REVIEW-NODE] LLM review failed for {agent_node_name}: {e}"
            )
            return {
                "approved": True,
                "iteration": iteration,
                "llm_metadata": {"error": str(e), "auto_approved": True},
            }


def _process_human_response(response: Any, iteration: int) -> Dict[str, Any]:
    """
    Process the response from human review.

    Args:
        response: Response from interrupt resume
        iteration: Current iteration number

    Returns:
        Processed review result
    """
    review_node_logger.info(f"[SUBAGENT-REVIEW-NODE] Processing response: {response}")

    # Handle wrapped format: {"value": '{"approved": true}'}
    if isinstance(response, dict) and "value" in response:
        value = response.get("value", "")
        if isinstance(value, str):
            try:
                response = json.loads(value)
            except json.JSONDecodeError:
                response = value

    # Parse response format
    if isinstance(response, dict):
        approved = response.get("approved", False)
        feedback = response.get("feedback", "")
    elif isinstance(response, str):
        normalized = response.lower().strip()
        approved = normalized in ("approved", "approve", "proceed", "yes", "ok", "pass")
        feedback = "" if approved else response
    else:
        approved = False
        feedback = str(response) if response else ""

    return {
        "approved": approved,
        "feedback": feedback,
        "iteration": iteration,
    }


def _build_approved_response() -> Dict[str, Any]:
    """
    Build state update for approved review.

    Returns:
        State update dictionary
    """
    return {
        "__review_route": "continue",
        "review_state": None,  # Clear review state
    }


def _build_rejected_response(
    review_state: Dict[str, Any],
    feedback: str,
    reviewer_type: str,
    llm_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build state update for rejected review.

    Args:
        review_state: Current review state
        feedback: Rejection feedback
        reviewer_type: "human" or "llm"
        llm_metadata: Optional LLM review metadata

    Returns:
        State update dictionary
    """
    # Add feedback to history
    current_iteration = review_state.get("iteration", 1)
    history = review_state.get("history", []).copy()

    history_entry = {
        "iteration": current_iteration,
        "agent_output": review_state.get("output", ""),
        "feedback": feedback,
        "reviewer_type": reviewer_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if llm_metadata:
        history_entry["llm_metadata"] = llm_metadata

    history.append(history_entry)

    # Build updated review state
    updated_review_state = {
        **review_state,
        "iteration": current_iteration + 1,
        "history": history,
        "last_feedback": feedback,
    }

    return {
        "__review_route": "retry",
        "review_state": updated_review_state,
    }


def create_subagent_review_router() -> Callable:
    """
    Create a routing function for sub-agent review conditional edges.

    Returns:
        A function that routes based on the review result
    """

    def review_router(state: Dict[str, Any]) -> str:
        """
        Route based on review result.

        Args:
            state: Current sub-agent state (Dict to avoid TYPE_CHECKING import issues)

        Returns:
            "continue" to proceed to END or "retry" to loop back to agent
        """
        route = state.get("__review_route", "continue")
        review_node_logger.info(f"[SUBAGENT-REVIEW-ROUTER] Routing decision: {route}")
        return route

    return review_router
