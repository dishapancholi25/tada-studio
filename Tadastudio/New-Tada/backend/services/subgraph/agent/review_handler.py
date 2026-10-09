"""
Review handler for sub-agent execution.

This module handles review gating for sub-agent outputs, supporting both
LLM review (inline) and human review (using LangGraph interrupt).
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from backend.services.config import get_logger

if TYPE_CHECKING:
    from backend.models.workflow import EnhancedNodeData
    from backend.models.workflow.configs import ReviewConfig
    from ..models import SubAgentState

review_handler_logger = get_logger("subgraph.agent.review_handler")


async def execute_subagent_review(
    agent_node: "EnhancedNodeData",
    state: "SubAgentState",
    agent_output: str,
    graph_manager: Any,
) -> Optional[Dict[str, Any]]:
    """
    Execute review for a sub-agent's output if review is enabled.

    This function handles both initial review and resume scenarios:
    - Initial: Stores state and triggers interrupt for human review
    - Resume: Checks for pending review with response and processes it

    Args:
        agent_node: The agent node that produced the output
        state: Current sub-agent state
        agent_output: The agent's output to review
        graph_manager: The graph manager instance

    Returns:
        Review result dict with 'approved' and optionally 'feedback',
        or None if review is not enabled
    """
    # Check if review is enabled for this agent
    review_config = _get_review_config(agent_node)
    if not review_config or not review_config.review_enabled:
        review_handler_logger.debug(
            f"[SUBAGENT-REVIEW] Review not enabled for {agent_node.name}"
        )
        return None

    review_handler_logger.info(
        f"[SUBAGENT-REVIEW] Review enabled for sub-agent {agent_node.name}, "
        f"mode={review_config.review_mode}"
    )

    # For human review, check if we're resuming from a pending review
    if review_config.review_mode == "human":
        from backend.services.execution.review.state_manager import (
            AgentReviewStateManager,
        )

        graph_execution_id = state.get("parent_db_execution_id")
        if graph_execution_id:
            # Check for pending review with a resume response
            pending_review = AgentReviewStateManager.get_pending_review(
                graph_execution_id=str(graph_execution_id),
                agent_node_id=agent_node.uniq_id,
            )

            if pending_review and pending_review.get("resume_response"):
                review_handler_logger.info(
                    f"[SUBAGENT-REVIEW] Found pending review with response for {agent_node.name}, "
                    "processing resume response"
                )
                # Process the stored resume response
                resume_response = pending_review["resume_response"]
                review_state_id = pending_review["id"]

                # Mark review as complete
                approved = resume_response.get("approved", False)
                if approved:
                    AgentReviewStateManager.complete_review(review_state_id, "approved")
                    return {
                        "approved": True,
                        "iteration": pending_review.get("current_iteration", 1),
                        "review_mode": "human",
                    }
                else:
                    feedback = resume_response.get("feedback", "")
                    # Add feedback to history (this also increments iteration)
                    AgentReviewStateManager.add_feedback_to_history(
                        review_state_id,
                        feedback,
                        pending_review.get("current_agent_output", agent_output),
                        "human",
                    )
                    # Clear resume_response to prevent reprocessing on next iteration
                    AgentReviewStateManager.clear_resume_response(review_state_id)
                    return {
                        "approved": False,
                        "feedback": feedback,
                        "iteration": pending_review.get("current_iteration", 1),
                        "review_mode": "human",
                    }

    # Initialize review history (for potential iteration loops)
    # Check if there's an existing pending review to get iteration count
    review_history: List[Dict[str, Any]] = []
    current_iteration = 1

    # For re-execution after rejection, get the current iteration from pending review
    if review_config.review_mode == "human":
        from backend.services.execution.review.state_manager import (
            AgentReviewStateManager,
        )

        graph_execution_id = state.get("parent_db_execution_id")
        if graph_execution_id:
            pending_review = AgentReviewStateManager.get_pending_review(
                graph_execution_id=str(graph_execution_id),
                agent_node_id=agent_node.uniq_id,
            )
            if pending_review:
                # Use iteration and history from pending review
                current_iteration = pending_review.get("current_iteration", 1)
                review_history = pending_review.get("review_history", [])
                review_handler_logger.info(
                    f"[SUBAGENT-REVIEW] Found pending review for {agent_node.name}, "
                    f"continuing at iteration {current_iteration}"
                )

    if review_config.review_mode == "llm":
        return await _execute_llm_review(
            agent_node=agent_node,
            state=state,
            agent_output=agent_output,
            review_config=review_config,
            review_history=review_history,
            current_iteration=current_iteration,
            graph_manager=graph_manager,
        )
    else:
        # Human review - uses interrupt
        return await _execute_human_review(
            agent_node=agent_node,
            state=state,
            agent_output=agent_output,
            review_config=review_config,
            review_history=review_history,
            current_iteration=current_iteration,
        )


def _get_review_config(agent_node: "EnhancedNodeData") -> Optional["ReviewConfig"]:
    """Extract review config from agent node.

    Handles both ReviewConfig objects and dict representations.
    """
    review_handler_logger.debug(
        f"[SUBAGENT-REVIEW-DEBUG] _get_review_config called for {agent_node.name}, "
        f"has_agent_config={agent_node.agent_config is not None}"
    )

    if not agent_node.agent_config:
        review_handler_logger.debug(
            f"[SUBAGENT-REVIEW-DEBUG] No agent_config for {agent_node.name}"
        )
        return None

    review_config = agent_node.agent_config.review_config
    review_handler_logger.debug(
        f"[SUBAGENT-REVIEW-DEBUG] review_config for {agent_node.name}: "
        f"type={type(review_config).__name__}, value={review_config}"
    )

    if review_config is None:
        return None

    # Handle dict representation
    if isinstance(review_config, dict):
        from backend.models.workflow.configs import ReviewConfig

        try:
            parsed = ReviewConfig(**review_config)
            review_handler_logger.debug(
                f"[SUBAGENT-REVIEW-DEBUG] Parsed dict to ReviewConfig: "
                f"review_enabled={parsed.review_enabled}, review_mode={parsed.review_mode}"
            )
            return parsed
        except Exception as e:
            review_handler_logger.warning(
                f"[SUBAGENT-REVIEW] Failed to parse review_config dict: {e}"
            )
            return None

    review_handler_logger.debug(
        f"[SUBAGENT-REVIEW-DEBUG] Using ReviewConfig object: "
        f"review_enabled={review_config.review_enabled}, review_mode={review_config.review_mode}"
    )
    return review_config


async def _execute_llm_review(
    agent_node: "EnhancedNodeData",
    state: "SubAgentState",
    agent_output: str,
    review_config: "ReviewConfig",
    review_history: List[Dict[str, Any]],
    current_iteration: int,
    graph_manager: Any,
) -> Dict[str, Any]:
    """
    Execute LLM review for sub-agent output.

    Args:
        agent_node: The agent node being reviewed
        state: Current sub-agent state
        agent_output: Output to review
        review_config: Review configuration
        review_history: Previous review iterations
        current_iteration: Current iteration number
        graph_manager: Graph manager instance

    Returns:
        Review result dictionary
    """
    review_handler_logger.info(
        f"[SUBAGENT-REVIEW] Executing LLM review for {agent_node.name}, "
        f"iteration {current_iteration}/{review_config.max_iterations}"
    )

    # Check if we have reviewer LLM config
    if not review_config.reviewer_llm_config:
        review_handler_logger.warning(
            f"[SUBAGENT-REVIEW] No reviewer_llm_config for {agent_node.name}, "
            "auto-approving"
        )
        return {"approved": True, "iteration": current_iteration}

    try:
        # Import review executor and dependencies
        from backend.services.execution.review.executor import ReviewExecutor
        from backend.services.llm_models import LLMFactory
        from backend.services.model_deployment import ModelDeploymentService

        # Get services from graph_manager or create new instances
        llm_factory = getattr(graph_manager, "llm_factory", None)
        model_service = getattr(graph_manager, "model_service", None)

        if not llm_factory:
            llm_factory = LLMFactory()
        if not model_service:
            model_service = ModelDeploymentService()

        # Create review executor
        review_executor = ReviewExecutor(
            llm_factory=llm_factory,
            model_service=model_service,
        )

        # Execute LLM review
        result = await review_executor._execute_llm_review(
            node=agent_node,
            state={},  # State not needed for LLM review
            agent_output=agent_output,
            review_config=review_config,
            review_history=review_history,
            current_iteration=current_iteration,
        )

        review_handler_logger.info(
            f"[SUBAGENT-REVIEW] LLM review result for {agent_node.name}: "
            f"approved={result.get('approved')}"
        )

        return {
            "approved": result.get("approved", False),
            "feedback": result.get("feedback", ""),
            "iteration": current_iteration,
            "llm_metadata": result.get("llm_metadata"),
            "review_mode": "llm",
        }

    except Exception as e:
        review_handler_logger.error(
            f"[SUBAGENT-REVIEW] LLM review failed for {agent_node.name}: {e}"
        )
        # On error, auto-approve with warning
        return {
            "approved": True,
            "iteration": current_iteration,
            "llm_metadata": {"error": str(e), "auto_approved": True},
            "review_mode": "llm",
        }


async def _execute_human_review(
    agent_node: "EnhancedNodeData",
    state: "SubAgentState",
    agent_output: str,
    review_config: "ReviewConfig",
    review_history: List[Dict[str, Any]],
    current_iteration: int,
) -> Dict[str, Any]:
    """
    Execute human review for sub-agent output using LangGraph interrupt.

    Args:
        agent_node: The agent node being reviewed
        state: Current sub-agent state
        agent_output: Output to review
        review_config: Review configuration
        review_history: Previous review iterations
        current_iteration: Current iteration number

    Returns:
        Review result dictionary
    """
    from langgraph.types import interrupt

    from backend.services.common.utils.websocket_notifier import ws_notifier

    review_handler_logger.info(
        f"[SUBAGENT-REVIEW] Executing human review for {agent_node.name}, "
        f"iteration {current_iteration}/{review_config.max_iterations}"
    )

    # Store review state BEFORE interrupt so resume can find it
    from backend.services.execution.review.state_manager import AgentReviewStateManager

    graph_execution_id = state.get("parent_db_execution_id")
    thread_id = state.get("parent_execution_id", "")

    if graph_execution_id:
        review_state = AgentReviewStateManager.create_or_update_review_state(
            graph_execution_id=str(graph_execution_id),
            agent_node_id=agent_node.uniq_id,
            thread_id=str(thread_id),
            agent_output=agent_output,
            review_mode="human",
            review_prompt=review_config.review_prompt,
            max_iterations=review_config.max_iterations,
            current_iteration=current_iteration,
            review_history=review_history,
            input_message=state.get("task_description"),
            review_config={
                "review_enabled": True,
                "review_mode": "human",
                "review_prompt": review_config.review_prompt,
                "max_iterations": review_config.max_iterations,
            },
            agent_node_name=agent_node.name,
        )
        review_handler_logger.info(
            f"[SUBAGENT-REVIEW] Stored review state for {agent_node.name}: "
            f"id={review_state.get('id')}"
        )

    # Build interrupt payload with context for UI
    interrupt_payload = {
        "type": "agent_review",
        "node_id": agent_node.uniq_id,
        "node_name": agent_node.name,
        "agent_output": agent_output,
        "review_prompt": review_config.review_prompt,
        "review_mode": "human",
        "current_iteration": current_iteration,
        "max_iterations": review_config.max_iterations,
        "review_history": review_history,
        "is_sub_agent": True,
        "parent_node_id": state.get("parent_node_id"),
        "parent_node_name": state.get("parent_node_name"),
    }

    # Send WebSocket notification
    ws_execution_id = state.get("parent_execution_id")
    if ws_notifier and ws_execution_id:
        try:
            await ws_notifier.on_execution_paused(
                ws_execution_id,
                {
                    "thread_id": ws_execution_id,
                    "node_id": agent_node.uniq_id,
                    "node_name": agent_node.name,
                    "prompt": interrupt_payload,
                    "review_type": "agent_review",
                    "is_sub_agent": True,
                },
            )
            review_handler_logger.info(
                f"[SUBAGENT-REVIEW] WebSocket pause notification sent for {agent_node.name}"
            )
        except Exception as e:
            review_handler_logger.error(
                f"[SUBAGENT-REVIEW] Failed to send WebSocket notification: {e}"
            )

    review_handler_logger.info(
        f"[SUBAGENT-REVIEW] Calling interrupt() for sub-agent {agent_node.name}"
    )

    # Call interrupt - execution pauses here until resumed
    response = interrupt(interrupt_payload)

    review_handler_logger.info(
        f"[SUBAGENT-REVIEW] Received resume response for {agent_node.name}: {response}"
    )

    # Process response
    return _process_human_response(response, current_iteration)


def _process_human_response(response: Any, iteration: int) -> Dict[str, Any]:
    """
    Process the response from human review.

    Args:
        response: Response from interrupt resume
        iteration: Current iteration number

    Returns:
        Processed review result
    """
    import json

    review_handler_logger.info(f"[SUBAGENT-REVIEW] Processing response: {response}")

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
        "review_mode": "human",
    }
