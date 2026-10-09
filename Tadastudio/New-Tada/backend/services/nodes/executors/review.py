"""
Review Node Executor.

This module provides a dedicated review node that handles human-in-the-loop
and LLM review for agent outputs. It uses LangGraph's interrupt() mechanism
with deterministic behavior - exactly ONE interrupt call per node execution.

The review node is automatically inserted by GraphBuilder for agents with
review_config.review_enabled = True.
"""

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.execution.review.executor import ReviewExecutor
from backend.services.websocket import notifier as ws_notifier

if TYPE_CHECKING:
    from backend.services.workflow.state import WorkflowState

review_node_logger = get_logger("nodes.executors.review")


class ReviewNodeFunctionFactory:
    """
    Factory for creating review node functions.

    Creates async functions that can be added to a LangGraph StateGraph.
    Each review node:
    1. Reads agent output from state.review_state[agent_node_id]
    2. Calls interrupt() ONCE for human review (deterministic)
    3. Processes the response and returns routing decision
    4. Updates state with feedback history if rejected

    This follows LangGraph's interrupt pattern by ensuring deterministic
    interrupt ordering - the same number of interrupts in the same order
    on every execution.
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
        Create a review node function for the given agent node.

        Args:
            agent_node: The agent node this review node is for

        Returns:
            An async function that can be added to a StateGraph
        """
        agent_node_id = agent_node.uniq_id
        agent_node_name = agent_node.name

        async def review_node_function(state: "WorkflowState") -> Dict[str, Any]:
            """
            Execute review for the agent's output.

            This function:
            1. Reads review data from state.review_state[agent_node_id]
            2. If no review data, routes to continue (passthrough)
            3. For human review, calls interrupt() ONCE
            4. For LLM review, calls LLM synchronously
            5. Returns routing decision and state updates

            Returns:
                Dict with:
                - route: "continue" (approved) or "retry" (rejected)
                - review_state: Updated review state
                - pending_review: Cleared when approved
            """
            review_node_logger.info(
                f"[REVIEW-NODE] Executing review node for agent: {agent_node_name}"
            )

            # Debug: Log what review_state we received
            review_node_logger.info(
                f"[REVIEW-STATE-DEBUG] {agent_node_name} received state with "
                f"review_state keys: {list(state.get('review_state', {}).keys())}"
            )

            # Get review data from state
            review_state = state.get("review_state", {})
            review_data = review_state.get(agent_node_id)

            if not review_data:
                review_node_logger.info(
                    f"[REVIEW-NODE] No review data for {agent_node_name}, "
                    "passing through"
                )
                # Store route in custom_data for the router to read
                return {"custom_data": {"__review_route": "continue"}}

            # Extract review context
            agent_output = review_data.get("output", "")
            config = review_data.get("config", {})
            iteration = review_data.get("iteration", 1)
            history = review_data.get("history", [])
            max_iterations = config.get("max_iterations", 3)
            review_mode = config.get("review_mode", "human")
            review_prompt = config.get("review_prompt", "Review the output")

            review_node_logger.info(
                f"[REVIEW-NODE] {agent_node_name} - Mode: {review_mode}, "
                f"Iteration: {iteration}/{max_iterations}"
            )

            # Check max iterations before review
            if iteration > max_iterations:
                review_node_logger.warning(
                    f"[REVIEW-NODE] Max iterations reached for {agent_node_name}, "
                    "auto-approving"
                )
                return self._build_approved_response(agent_node_id, agent_output)

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
                # Send "running" notification BEFORE LLM call so frontend has
                # a node entry to receive streaming tokens
                ws_execution_id = state.get("execution_id")
                # Use same node ID format as LangGraph (builder.py:343)
                review_node_id = f"{agent_node_id}_review"
                review_node_name = f"Review: {agent_node_name} (Iteration {iteration})"

                if ws_notifier and ws_execution_id:
                    try:
                        await ws_notifier.on_node_start(
                            ws_execution_id,
                            review_node_id,
                            review_node_name,
                            "REVIEW",
                        )
                        review_node_logger.info(
                            f"[REVIEW-NODE] Sent running notification for {review_node_name}"
                        )
                    except Exception as ws_error:
                        review_node_logger.warning(
                            f"[REVIEW-NODE] Failed to send running notification: {ws_error}"
                        )

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

            # Create review node execution record
            try:
                from backend.services.execution.history.node_execution import (
                    create_review_node_execution,
                )

                graph_execution_id = state.get("db_execution_id") or state.get(
                    "execution_id"
                )
                ws_execution_id = state.get("execution_id")

                if graph_execution_id:
                    llm_metadata = result.get("llm_metadata", {})
                    reviewer_model = None
                    if llm_metadata:
                        reviewer_model = llm_metadata.get("model")

                    node_exec_result = create_review_node_execution(
                        graph_execution_id=str(graph_execution_id),
                        agent_node_id=agent_node_id,
                        agent_node_name=agent_node_name,
                        review_mode=review_mode,
                        iteration=iteration,
                        max_iterations=max_iterations,
                        approved=result.get("approved", False),
                        feedback=result.get("feedback"),
                        agent_output=agent_output,
                        review_prompt=review_prompt,
                        reviewer_model=reviewer_model,
                        llm_metadata=llm_metadata if llm_metadata else None,
                    )
                    review_node_logger.info(
                        f"[REVIEW-NODE] Created review node execution for {agent_node_name}"
                    )

                    # Send WebSocket notification for the review node
                    if ws_notifier and ws_execution_id and node_exec_result:
                        try:
                            review_node_logger.info(
                                f"[REVIEW-NODE-WS-DEBUG] Sending node_complete: "
                                f"node_id={node_exec_result['node_id']}, "
                                f"node_name={node_exec_result['node_name']}, "
                                f"db_node_id={node_exec_result['id']}, "
                                f"execution_order={node_exec_result['execution_order']}, "
                                f"iteration={iteration}"
                            )
                            await ws_notifier.on_node_complete(
                                ws_execution_id,
                                node_exec_result["node_id"],
                                node_exec_result["node_name"],
                                node_exec_result["output_data"],
                                "REVIEW",
                                0.1,  # duration_seconds
                                None,  # input_data
                                None,  # start_time
                                None,  # end_time
                                None,  # input_tokens
                                None,  # output_tokens
                                None,  # total_tokens
                                False,  # is_sub_agent
                                None,  # parent_agent_id
                                node_exec_result["id"],  # database_node_id
                                node_exec_result["execution_order"],  # execution_order
                            )
                            review_node_logger.info(
                                "[REVIEW-NODE] Sent WebSocket notification for review node"
                            )
                        except Exception as ws_error:
                            review_node_logger.warning(
                                f"[REVIEW-NODE] Failed to send WebSocket notification: {ws_error}"
                            )
            except Exception as e:
                review_node_logger.warning(
                    f"[REVIEW-NODE] Failed to create review node execution: {e}"
                )

            # Process result
            if result.get("approved"):
                review_node_logger.info(
                    f"[REVIEW-NODE] {agent_node_name} output APPROVED"
                )
                return self._build_approved_response(agent_node_id, agent_output)
            else:
                feedback = result.get("feedback", "")
                review_node_logger.info(
                    f"[REVIEW-NODE] {agent_node_name} output REJECTED - "
                    f"Feedback: {feedback[:100]}..."
                )
                return self._build_rejected_response(
                    agent_node_id=agent_node_id,
                    review_data=review_data,
                    feedback=feedback,
                    reviewer_type=review_mode,
                    llm_metadata=result.get("llm_metadata"),
                )

        return review_node_function

    async def _execute_human_review(
        self,
        state: "WorkflowState",
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

        This is the ONLY interrupt() call in the review node, ensuring
        deterministic interrupt ordering.

        Args:
            state: Current workflow state
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

        # Build interrupt payload
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
        }

        review_node_logger.info(
            f"[REVIEW-NODE] Sending WebSocket pause notification for {agent_node_name}"
        )

        # Send WebSocket notification
        ws_execution_id = state.get("execution_id")
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
                    },
                )
                review_node_logger.info(
                    f"[REVIEW-NODE] WebSocket pause notification sent for {agent_node_name}"
                )
            except Exception as e:
                review_node_logger.error(
                    f"[REVIEW-NODE] Failed to send WebSocket notification: {e}"
                )

        review_node_logger.info(
            f"[REVIEW-NODE] Calling interrupt() for {agent_node_name} - "
            "this is the ONLY interrupt in this node"
        )

        # Single deterministic interrupt call
        response = interrupt(interrupt_payload)

        review_node_logger.info(
            f"[REVIEW-NODE] Received resume response for {agent_node_name}: {response}"
        )

        # Process response
        return self._process_human_response(response, iteration)

    def _process_human_response(self, response: Any, iteration: int) -> Dict[str, Any]:
        """
        Process the response from human review.

        Args:
            response: Response from interrupt resume
            iteration: Current iteration number

        Returns:
            Processed review result
        """
        review_node_logger.info(f"[REVIEW-NODE] Processing response: {response}")

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
            approved = normalized in (
                "approved",
                "approve",
                "proceed",
                "yes",
                "ok",
                "pass",
            )
            feedback = "" if approved else response
        else:
            approved = False
            feedback = str(response) if response else ""

        return {
            "approved": approved,
            "feedback": feedback,
            "iteration": iteration,
        }

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
            f"[REVIEW-NODE] Executing LLM review for {agent_node_name}"
        )

        # Check if LLM factory is configured
        if not self.llm_factory or not self.model_service:
            review_node_logger.warning(
                f"[REVIEW-NODE] No LLM factory configured for {agent_node_name}, "
                "auto-approving"
            )
            return {"approved": True, "iteration": iteration}

        # Build ReviewConfig from the stored config dict
        from backend.models.workflow.configs import LLMConfig, ReviewConfig

        # Get reviewer_llm_config from the config dict
        reviewer_llm_config_dict = config.get("reviewer_llm_config")

        # For LLM review, we need reviewer_llm_config
        if not reviewer_llm_config_dict:
            review_node_logger.warning(
                f"[REVIEW-NODE] No reviewer_llm_config for {agent_node_name}, "
                "auto-approving (LLM review requires reviewer_llm_config)"
            )
            return {"approved": True, "iteration": iteration}

        try:
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
                f"[REVIEW-NODE] LLM review result for {agent_node_name}: "
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
                f"[REVIEW-NODE] LLM review failed for {agent_node_name}: {e}"
            )
            # On error, auto-approve with warning
            return {
                "approved": True,
                "iteration": iteration,
                "llm_metadata": {
                    "error": str(e),
                    "auto_approved": True,
                },
            }

    def _build_approved_response(
        self, agent_node_id: str, agent_output: str
    ) -> Dict[str, Any]:
        """
        Build state update for approved review.

        Args:
            agent_node_id: ID of the reviewed agent
            agent_output: The approved output

        Returns:
            State update dictionary
        """
        return {
            # Store route in custom_data for the router to read
            "custom_data": {"__review_route": "continue"},
            # Clear review state for this agent (set to None to trigger removal)
            "review_state": {agent_node_id: None},
            # Clear pending review
            "pending_review": None,
        }

    def _build_rejected_response(
        self,
        agent_node_id: str,
        review_data: Dict[str, Any],
        feedback: str,
        reviewer_type: str,
        llm_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build state update for rejected review.

        Args:
            agent_node_id: ID of the reviewed agent
            review_data: Current review data
            feedback: Rejection feedback
            reviewer_type: "human" or "llm"
            llm_metadata: Optional LLM review metadata

        Returns:
            State update dictionary
        """
        # Add feedback to history
        current_iteration = review_data.get("iteration", 1)
        history = review_data.get("history", []).copy()

        history_entry = {
            "iteration": current_iteration,
            "agent_output": review_data.get("output", ""),
            "feedback": feedback,
            "reviewer_type": reviewer_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if llm_metadata:
            history_entry["llm_metadata"] = llm_metadata

        history.append(history_entry)

        # Build updated review state
        updated_review_data = {
            **review_data,
            "iteration": current_iteration + 1,
            "history": history,
            "last_feedback": feedback,
        }

        return {
            # Store route in custom_data for the router to read
            "custom_data": {"__review_route": "retry"},
            "review_state": {agent_node_id: updated_review_data},
        }


def create_review_router() -> Callable:
    """
    Create a routing function for review node conditional edges.

    Returns:
        A function that routes based on the review result
    """

    def review_router(state: "WorkflowState") -> str:
        """
        Route based on review result.

        Reads the 'route' field from the last update to determine
        whether to continue to the next node or retry the agent.

        Args:
            state: Current workflow state

        Returns:
            "continue" to proceed or "retry" to loop back to agent
        """
        # The route is stored in state by the review node's return value
        # LangGraph applies state updates before calling the router
        route = state.get("__review_route", "continue")
        review_node_logger.info(f"[REVIEW-ROUTER] Routing decision: {route}")
        return route

    return review_router
