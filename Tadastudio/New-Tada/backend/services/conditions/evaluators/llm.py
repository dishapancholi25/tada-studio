"""
LLM Condition Evaluator.

Evaluates conditions using Language Model reasoning.
"""

from typing import Any

from backend.services.execution.logging import execution_logger
from backend.services.workflow.state import WorkflowState


class LLMConditionEvaluator:
    """
    Evaluates conditions using an LLM.

    Formats a prompt with context and uses LLM to make routing decisions.
    """

    def __init__(self, graph_manager):
        """
        Initialize the LLM condition evaluator.

        Args:
            graph_manager: GraphManager instance for getting LLM instances
        """
        self.graph_manager = graph_manager

    def evaluate(self, state: WorkflowState, condition_config: Any, graph: Any) -> str:
        """
        Evaluate a condition using an LLM.

        Args:
            state: The workflow state
            condition_config: Configuration with prompt and LLM settings
            graph: The graph containing default LLM config

        Returns:
            String result: "true"/"false" for binary, or branch index for multi-branch
        """
        # Extract configuration
        config = self._parse_config(condition_config, graph)
        llm_prompt = config["llm_prompt"]
        llm_config = config["llm_config"]
        branch_labels = config["branch_labels"]

        if not llm_prompt:
            execution_logger.warning("No LLM prompt provided for evaluation")
            return "false"

        if not llm_config:
            execution_logger.warning("No LLM config for LLM condition evaluation")
            return "false"

        try:
            # Build and format prompt
            formatted_prompt = self._format_prompt(llm_prompt, state)

            # Get LLM and invoke
            response = self._invoke_llm(llm_config, formatted_prompt)

            # Parse response
            return self._parse_response(response, branch_labels)

        except Exception as e:
            execution_logger.error(f"Failed to evaluate LLM condition: {e}")
            return "false"

    def _parse_config(self, condition_config: Any, graph: Any) -> dict:
        """
        Parse configuration for LLM evaluation.

        Handles both dict and dataclass formats.

        Args:
            condition_config: Configuration object
            graph: Graph with default LLM config

        Returns:
            Dictionary with parsed configuration
        """
        if hasattr(condition_config, "__dict__"):
            # Dataclass format
            return {
                "llm_prompt": getattr(condition_config, "llm_prompt", ""),
                "llm_config": (
                    getattr(condition_config, "llm_config", None) or graph.llm_config
                ),
                "branch_labels": getattr(condition_config, "branch_labels", []),
            }
        else:
            # Dict format
            return {
                "llm_prompt": condition_config.get("llm_prompt", ""),
                "llm_config": condition_config.get("llm_config") or graph.llm_config,
                "branch_labels": condition_config.get("branch_labels", []),
            }

    def _format_prompt(self, llm_prompt: str, state: WorkflowState) -> str:
        """
        Format the LLM prompt with context from state.

        Args:
            llm_prompt: Template prompt string
            state: The workflow state

        Returns:
            Formatted prompt string
        """
        # Build context for the prompt
        context = {
            "last_message": state["messages"][-1].content
            if state.get("messages")
            else "",
            "original_message": state.get("original_message", ""),
            "node_outputs": state.get("node_outputs", {}),
        }

        # Format the prompt with context
        return llm_prompt.format(**context)

    def _invoke_llm(self, llm_config: Any, prompt: str) -> Any:
        """
        Invoke the LLM with the formatted prompt.

        Args:
            llm_config: LLM configuration
            prompt: Formatted prompt

        Returns:
            LLM response
        """
        llm = self.graph_manager.get_llm(llm_config)
        return llm.invoke(prompt)

    def _parse_response(self, response: Any, branch_labels: list) -> str:
        """
        Parse LLM response to determine routing.

        Args:
            response: LLM response object
            branch_labels: List of branch labels for multi-branch mode

        Returns:
            Routing decision as string
        """
        # Extract text from response
        response_text = (
            response.content.strip().lower()
            if hasattr(response, "content")
            else str(response).strip().lower()
        )

        # Check for branch labels if in multi-branch mode
        if branch_labels:
            for i, label in enumerate(branch_labels):
                if label.lower() in response_text:
                    return str(i)

        # Default to binary evaluation
        if "true" in response_text or "yes" in response_text:
            return "true"
        elif "false" in response_text or "no" in response_text:
            return "false"
        else:
            # Try to determine from response
            return "true" if response_text else "false"
