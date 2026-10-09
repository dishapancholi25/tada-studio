"""
Review Executor for Agent Output Gating.

This module handles agent output review functionality, supporting both
human-in-the-loop review and automated LLM review. Uses LangGraph's
interrupt mechanism for human review pausing.
"""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs import LLMConfig, ReviewConfig
from backend.services.common.utils.websocket_notifier import ws_notifier
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

review_logger = get_logger("execution.review")


# System prompt for LLM reviewer
LLM_REVIEWER_SYSTEM_PROMPT = """You are a review agent responsible for evaluating AI agent outputs.
Your task is to review the output and determine if it meets the specified criteria.

You MUST respond with a JSON object in the following format:
{
    "proceed": true/false,
    "feedback": "Detailed feedback explaining your decision. If proceed is false, explain what needs to be improved.",
    "confidence_score": 0.0-1.0,
    "issue_categories": ["category1", "category2"],
    "reasoning": "Your reasoning for the decision"
}

The "proceed" field indicates whether the output passes review:
- true: The output meets the criteria and can proceed
- false: The output needs revision based on the feedback provided

Be specific and actionable in your feedback so the agent can improve its output."""


class ReviewExecutor:
    """
    Executes review gating for agent outputs.

    Supports two modes:
    - Human review: Pauses execution using interrupt() for human approval/feedback
    - LLM review: Synchronously calls a reviewer LLM to evaluate output

    Manages feedback loops with ephemeral history within execution context.
    """

    def __init__(
        self,
        llm_factory: Optional["LLMFactory"] = None,
        model_service: Optional["ModelDeploymentService"] = None,
    ):
        """
        Initialize review executor.

        Args:
            llm_factory: Factory for creating LLM instances (required for LLM review)
            model_service: Service for model deployment management (required for LLM review)
        """
        self.llm_factory = llm_factory
        self.model_service = model_service
        self.logger = review_logger

    async def execute_review(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        agent_output: str,
        review_config: ReviewConfig,
        review_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute review for an agent's output.

        Args:
            node: The agent node being reviewed
            state: Current workflow state
            agent_output: The agent's output to review
            review_config: Review configuration
            review_history: Ephemeral review history from previous iterations

        Returns:
            Dictionary with:
            - approved: bool - Whether output passed review
            - final_output: str - The output (unchanged if approved)
            - feedback: str - Feedback if not approved
            - llm_metadata: dict - LLM review metadata (for LLM mode)
        """
        current_iteration = len(review_history) + 1
        self.logger.info(
            f"[REVIEW] Executing {review_config.review_mode} review for {node.name}, "
            f"iteration {current_iteration}/{review_config.max_iterations}"
        )

        if review_config.review_mode == "human":
            return await self._execute_human_review(
                node,
                state,
                agent_output,
                review_config,
                review_history,
                current_iteration,
            )
        else:
            return await self._execute_llm_review(
                node,
                state,
                agent_output,
                review_config,
                review_history,
                current_iteration,
            )

    async def _execute_human_review(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        agent_output: str,
        review_config: ReviewConfig,
        review_history: List[Dict[str, Any]],
        current_iteration: int,
    ) -> Dict[str, Any]:
        """
        Execute human review using LangGraph's interrupt() mechanism.

        Args:
            node: The agent node being reviewed
            state: Current workflow state
            agent_output: The agent's output to review
            review_config: Review configuration
            review_history: Previous review iterations
            current_iteration: Current iteration number

        Returns:
            Review result dictionary
        """
        from langgraph.types import interrupt

        # Build interrupt payload with all context for UI
        interrupt_payload = {
            "type": "agent_review",
            "node_id": node.uniq_id,
            "node_name": node.name,
            "agent_output": agent_output,
            "review_prompt": review_config.review_prompt,
            "review_mode": "human",
            "current_iteration": current_iteration,
            "max_iterations": review_config.max_iterations,
            "review_history": review_history,
            "timeout_seconds": review_config.timeout_seconds,
        }

        # [REVIEW-DEBUG] Log the interrupt payload being built
        self.logger.info(
            f"[REVIEW-DEBUG] Built interrupt_payload with type='agent_review', "
            f"node_id={node.uniq_id}, iteration={current_iteration}/{review_config.max_iterations}"
        )

        # Send WebSocket pause notification
        ws_execution_id = state.get("execution_id")
        if ws_notifier and ws_execution_id:
            try:
                ws_payload = {
                    "thread_id": ws_execution_id,
                    "node_id": node.uniq_id,
                    "node_name": node.name,
                    "prompt": interrupt_payload,
                    "review_type": "agent_review",
                }
                self.logger.info(
                    f"[REVIEW-DEBUG] ReviewExecutor SENDING WebSocket pause - "
                    f"prompt.type={interrupt_payload.get('type')}, "
                    f"ws_execution_id={ws_execution_id}"
                )
                await ws_notifier.on_execution_paused(ws_execution_id, ws_payload)
                self.logger.info(
                    f"[REVIEW-DEBUG] ReviewExecutor WebSocket pause SENT for {node.name}"
                )
            except Exception as e:
                self.logger.error(
                    f"[REVIEW-DEBUG] ReviewExecutor WebSocket pause FAILED: {e}"
                )

        # Use LangGraph interrupt - execution pauses here
        self.logger.info(
            f"[REVIEW-DEBUG] ReviewExecutor calling interrupt() for {node.name}, "
            f"interrupt_payload keys: {list(interrupt_payload.keys())}"
        )
        review_response = interrupt(interrupt_payload)

        # When resumed, process the response
        return self._process_human_review_response(
            review_response, agent_output, current_iteration
        )

    def _process_human_review_response(
        self,
        review_response: Any,
        agent_output: str,
        current_iteration: int,
    ) -> Dict[str, Any]:
        """
        Process the response from human review.

        Args:
            review_response: Response from interrupt resume
            agent_output: Original agent output
            current_iteration: Current iteration number

        Returns:
            Review result dictionary
        """
        self.logger.info(
            f"[REVIEW] Processing human review response: {review_response}"
        )

        # Handle wrapped format from checkpoint resume: {"value": "{\"approved\": true}"}
        if isinstance(review_response, dict) and "value" in review_response:
            value = review_response.get("value", "")
            if isinstance(value, str):
                try:
                    review_response = json.loads(value)
                    self.logger.info(
                        f"[REVIEW] Unwrapped response to: {review_response}"
                    )
                except json.JSONDecodeError:
                    # Not JSON, treat as string response
                    review_response = value

        # Handle different response formats
        if isinstance(review_response, dict):
            approved = review_response.get("approved", False)
            feedback = review_response.get("feedback", "")
        elif isinstance(review_response, str):
            # Simple string response - treat as feedback if not "approved" or "proceed"
            normalized = review_response.lower().strip()
            approved = normalized in (
                "approved",
                "approve",
                "proceed",
                "yes",
                "ok",
                "pass",
            )
            feedback = "" if approved else review_response
        else:
            approved = False
            feedback = str(review_response) if review_response else ""

        self.logger.info(
            f"[REVIEW] Human review result: approved={approved}, "
            f"feedback_length={len(feedback)}"
        )

        if approved:
            return {
                "approved": True,
                "final_output": agent_output,
                "iteration": current_iteration,
            }
        else:
            return {
                "approved": False,
                "feedback": feedback,
                "iteration": current_iteration,
            }

    async def _execute_llm_review(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        agent_output: str,
        review_config: ReviewConfig,
        review_history: List[Dict[str, Any]],
        current_iteration: int,
    ) -> Dict[str, Any]:
        """
        Execute LLM review synchronously (no interrupt needed).

        Args:
            node: The agent node being reviewed
            state: Current workflow state
            agent_output: The agent's output to review
            review_config: Review configuration
            review_history: Previous review iterations
            current_iteration: Current iteration number

        Returns:
            Review result dictionary
        """
        self.logger.info(f"[REVIEW] Executing LLM review for {node.name}")

        if not review_config.reviewer_llm_config:
            self.logger.warning(
                f"[REVIEW] No reviewer LLM config for {node.name}, auto-approving"
            )
            return {
                "approved": True,
                "final_output": agent_output,
                "iteration": current_iteration,
            }

        if not self.llm_factory or not self.model_service:
            self.logger.error(
                "[REVIEW] LLM factory or model service not provided, auto-approving"
            )
            return {
                "approved": True,
                "final_output": agent_output,
                "iteration": current_iteration,
            }

        try:
            # Build reviewer LLM
            llm = await self._build_reviewer_llm(review_config.reviewer_llm_config)

            # Build review prompt
            review_prompt = self._build_llm_review_prompt(
                agent_output, review_config, review_history
            )

            # Call reviewer LLM
            messages = [
                SystemMessage(content=LLM_REVIEWER_SYSTEM_PROMPT),
                HumanMessage(content=review_prompt),
            ]

            self.logger.debug(f"[REVIEW] Invoking reviewer LLM for {node.name}")
            response = await llm.ainvoke(messages)

            # Parse response
            llm_result = self._parse_llm_review_response(response.content)

            self.logger.info(
                f"[REVIEW] LLM review result for {node.name}: proceed={llm_result['proceed']}, "
                f"confidence={llm_result.get('confidence_score', 'N/A')}"
            )

            if llm_result["proceed"]:
                return {
                    "approved": True,
                    "final_output": agent_output,
                    "llm_metadata": llm_result,
                    "iteration": current_iteration,
                }
            else:
                return {
                    "approved": False,
                    "feedback": llm_result.get("feedback", ""),
                    "llm_metadata": llm_result,
                    "iteration": current_iteration,
                }

        except Exception as e:
            self.logger.error(f"[REVIEW] LLM review failed for {node.name}: {e}")
            # On LLM failure, auto-approve with low confidence
            return {
                "approved": True,
                "final_output": agent_output,
                "llm_metadata": {
                    "proceed": True,
                    "feedback": f"Review skipped due to error: {str(e)}",
                    "confidence_score": 0.0,
                    "issue_categories": ["review_error"],
                    "reasoning": "LLM review failed, auto-approved",
                },
                "iteration": current_iteration,
            }

    async def _build_reviewer_llm(self, llm_config: LLMConfig) -> Any:
        """
        Build LLM instance for reviewer.

        Args:
            llm_config: LLM configuration for reviewer

        Returns:
            LLM instance

        Raises:
            ValueError: If LLM cannot be built
        """
        # Convert dict to LLMConfig if needed
        if isinstance(llm_config, dict):
            llm_config = LLMConfig(**llm_config)

        # Enrich config with model deployment settings
        enriched_config = self.model_service.enrich_llm_config(llm_config)

        # Create LLM instance
        llm_instance = self.llm_factory.create_llm_instance(enriched_config)

        if not llm_instance or not llm_instance.llm:
            raise ValueError("Failed to create reviewer LLM instance")

        return llm_instance.llm

    def _build_llm_review_prompt(
        self,
        agent_output: str,
        review_config: ReviewConfig,
        review_history: List[Dict[str, Any]],
    ) -> str:
        """
        Build the review prompt for LLM reviewer.

        Args:
            agent_output: Agent's output to review
            review_config: Review configuration
            review_history: Previous review iterations

        Returns:
            Formatted review prompt
        """
        prompt_parts = []

        # Add review criteria
        prompt_parts.append("## Review Criteria")
        prompt_parts.append(review_config.review_prompt)
        prompt_parts.append("")

        # Add history if present
        if review_history:
            prompt_parts.append("## Previous Review Iterations")
            for entry in review_history:
                prompt_parts.append(f"### Iteration {entry.get('iteration', '?')}")
                prompt_parts.append(
                    f"**Output:** {entry.get('agent_output', '')[:500]}..."
                )
                prompt_parts.append(f"**Feedback:** {entry.get('feedback', '')}")
                prompt_parts.append("")

        # Add current output
        prompt_parts.append("## Current Output to Review")
        prompt_parts.append(agent_output)
        prompt_parts.append("")

        prompt_parts.append(
            "Please review the output against the criteria and respond with JSON."
        )

        return "\n".join(prompt_parts)

    def _parse_llm_review_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse LLM reviewer response.

        Args:
            response_content: Raw response from LLM

        Returns:
            Parsed review result dictionary
        """
        try:
            # Try to extract JSON from response
            content = response_content.strip()

            # Handle markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            result = json.loads(content)

            # Validate required fields
            return {
                "proceed": bool(result.get("proceed", False)),
                "feedback": str(result.get("feedback", "")),
                "confidence_score": float(result.get("confidence_score", 0.5)),
                "issue_categories": list(result.get("issue_categories", [])),
                "reasoning": str(result.get("reasoning", "")),
            }

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.warning(
                f"[REVIEW] Failed to parse LLM review response: {e}, "
                f"content: {response_content[:200]}"
            )
            # Default to not proceeding if we can't parse
            return {
                "proceed": False,
                "feedback": f"Unable to parse review response. Raw: {response_content[:500]}",
                "confidence_score": 0.0,
                "issue_categories": ["parse_error"],
                "reasoning": "Failed to parse LLM response",
            }

    @staticmethod
    def build_feedback_context(review_history: List[Dict[str, Any]]) -> str:
        """
        Build feedback context string from review history.

        Used to augment agent input with previous feedback for re-execution.

        Args:
            review_history: List of review history entries

        Returns:
            Formatted feedback context string
        """
        if not review_history:
            return ""

        context_parts = [
            "\n\n---",
            "## Previous Review Feedback",
            "Your previous responses were reviewed and feedback was provided. "
            "Please address the feedback in your response:",
            "",
        ]

        for entry in review_history:
            iteration = entry.get("iteration", "?")
            feedback = entry.get("feedback", "")
            reviewer = entry.get("reviewer_type", "unknown")
            agent_output = entry.get("agent_output", "")

            context_parts.append(
                f"### Feedback from {reviewer} (Iteration {iteration})"
            )
            if agent_output:
                context_parts.append(f"**Your previous response:**\n{agent_output}")
                context_parts.append("")
            context_parts.append(f"**Feedback:** {feedback}")
            context_parts.append("")

        context_parts.append(
            "Please provide an improved response that addresses the feedback above."
        )
        context_parts.append("---\n")

        return "\n".join(context_parts)

    @staticmethod
    def create_history_entry(
        iteration: int,
        agent_output: str,
        feedback: str,
        reviewer_type: str,
        llm_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a review history entry.

        Args:
            iteration: Iteration number
            agent_output: Agent's output that was reviewed
            feedback: Feedback provided
            reviewer_type: "human" or "llm"
            llm_metadata: Optional LLM metadata (for LLM reviews)

        Returns:
            History entry dictionary
        """
        entry = {
            "iteration": iteration,
            "agent_output": agent_output,
            "feedback": feedback,
            "reviewer_type": reviewer_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if llm_metadata:
            entry["llm_metadata"] = llm_metadata

        return entry
