"""
Condition Evaluator Orchestrator.

Central orchestrator for all condition evaluation types.
"""

from typing import Any

from backend.services.conditions.evaluators import (
    BranchConditionEvaluator,
    ExpressionConditionEvaluator,
    LLMConditionEvaluator,
    PassthroughBooleanEvaluator,
    SingleConditionEvaluator,
)
from backend.services.conditions.value_extractor import ValueExtractor
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

condition_eval_logger = get_logger("conditions.evaluator")


class ConditionEvaluator:
    """
    Orchestrates condition evaluation for all condition types.

    Handles:
    - Binary conditions (true/false)
    - Multi-branch conditions
    - Expression-based conditions
    - LLM-based conditions
    """

    def __init__(self, graph_manager=None):
        """
        Initialize the condition evaluator.

        Args:
            graph_manager: Optional GraphManager for LLM evaluation
        """
        self.value_extractor = ValueExtractor()
        self.single_evaluator = SingleConditionEvaluator()
        self.branch_evaluator = BranchConditionEvaluator()
        self.expression_evaluator = ExpressionConditionEvaluator()
        self.passthrough_evaluator = PassthroughBooleanEvaluator()
        self.llm_evaluator = (
            LLMConditionEvaluator(graph_manager) if graph_manager else None
        )

    def evaluate_binary_condition(
        self, state: WorkflowState, condition_config: Any
    ) -> bool:
        """
        Evaluate a binary condition (true/false).

        Supports two modes:
        - Passthrough: Directly interprets input value as boolean (case-insensitive)
        - Legacy: Uses comparison operators with simple_conditions

        Args:
            state: The workflow state
            condition_config: Configuration for the condition

        Returns:
            True if condition is met, False otherwise
        """
        # Check if passthrough mode is active (no simple_conditions configured)
        if self._is_passthrough_mode(condition_config):
            condition_eval_logger.info(
                "  Binary evaluation: passthrough mode (no simple_conditions)"
            )
            value = self.value_extractor.extract(state, condition_config)
            condition_eval_logger.info(
                f"  Extracted value: {value!r} (type={type(value).__name__})"
            )
            result = self.passthrough_evaluator.evaluate(value)
            condition_eval_logger.info(f"  Passthrough result: {result}")
            return result

        # Legacy mode: Extract value and evaluate with operators
        condition_eval_logger.info(
            "  Binary evaluation: operator mode (with simple_conditions)"
        )
        value = self.value_extractor.extract(state, condition_config)
        condition_eval_logger.info(
            f"  Extracted value: {value!r} (type={type(value).__name__})"
        )
        result = self._evaluate_with_logic_operators(value, condition_config)
        condition_eval_logger.info(f"  Logic operator result: {result}")
        return result

    def _is_passthrough_mode(self, condition_config: Any) -> bool:
        """
        Determine if passthrough boolean evaluation should be used.

        Passthrough mode is active when:
        - simple_conditions is empty or not present
        - input_source is configured at the root level

        Args:
            condition_config: The condition configuration

        Returns:
            True if passthrough mode should be used
        """
        if hasattr(condition_config, "__dict__"):
            simple_conditions = getattr(condition_config, "simple_conditions", [])
            input_source = getattr(condition_config, "input_source", None)
        else:
            simple_conditions = condition_config.get("simple_conditions", [])
            input_source = condition_config.get("input_source", None)

        # Passthrough if no simple conditions and input_source is set
        has_no_conditions = not simple_conditions or len(simple_conditions) == 0
        has_input_source = input_source is not None and input_source != ""

        return has_no_conditions and has_input_source

    def evaluate_multi_branch(
        self, state: WorkflowState, branches: list, condition_config: Any = None
    ) -> str:
        """
        Evaluate multi-branch conditions.

        Args:
            state: The workflow state
            branches: List of branch configurations
            condition_config: Optional parent condition config for fallback source info

        Returns:
            Branch handle ID or "0" for default
        """
        condition_eval_logger.info(
            f"  Multi-branch evaluation: {len(branches)} branches"
        )
        for i, branch in enumerate(branches):
            # Parse branch configuration
            branch_condition = self._extract_branch_condition(branch)
            handle_id = self._extract_handle_id(branch)
            branch_label = (
                branch.get("label", handle_id)
                if isinstance(branch, dict)
                else getattr(branch, "label", handle_id)
            )

            condition_eval_logger.info(
                f"  Evaluating branch[{i}]: {branch_label!r} (handle={handle_id})"
            )

            # Evaluate branch condition, passing parent config for fallback
            matched = self.branch_evaluator.evaluate(
                state, branch_condition, condition_config
            )
            condition_eval_logger.info(
                f"  Branch[{i}] {branch_label!r} matched: {matched}"
            )

            if matched:
                result = handle_id.replace("branch-", "")
                condition_eval_logger.info(
                    f"  Routed to branch[{i}]: {branch_label!r} -> {result!r}"
                )
                return result

        # No branches matched, return default
        condition_eval_logger.info("  No branches matched, using default (0)")
        return "0"

    def evaluate_expression(self, state: WorkflowState, condition_config: Any) -> bool:
        """
        Evaluate an expression-based condition.

        Args:
            state: The workflow state
            condition_config: Configuration with expression

        Returns:
            True if expression evaluates to truthy, False otherwise
        """
        return self.expression_evaluator.evaluate(state, condition_config)

    def evaluate_llm(
        self, state: WorkflowState, condition_config: Any, graph: Any
    ) -> str:
        """
        Evaluate an LLM-based condition.

        Args:
            state: The workflow state
            condition_config: Configuration with LLM prompt
            graph: Graph with LLM config

        Returns:
            Routing decision as string
        """
        if not self.llm_evaluator:
            raise ValueError("LLM evaluator not initialized with graph_manager")
        return self.llm_evaluator.evaluate(state, condition_config, graph)

    def _evaluate_with_logic_operators(self, value: Any, condition_config: Any) -> bool:
        """
        Evaluate condition with AND/OR logic operators.

        Args:
            value: Extracted value
            condition_config: Configuration with conditions and logic operator

        Returns:
            Combined evaluation result
        """
        # Parse configuration
        config = self._parse_logic_config(condition_config)
        simple_conditions = config["simple_conditions"]
        logic_operator = config["logic_operator"]

        if simple_conditions and len(simple_conditions) > 0:
            # Multiple conditions with logic operator (AND/OR)
            condition_eval_logger.info(
                f"  Evaluating {len(simple_conditions)} conditions with {logic_operator} logic"
            )
            results = []
            for j, condition in enumerate(simple_conditions):
                single_result = self.single_evaluator.evaluate(value, condition)
                results.append(single_result)
                condition_eval_logger.info(
                    f"    Condition[{j}] result: {single_result}"
                )

            combined = any(results) if logic_operator == "OR" else all(results)
            condition_eval_logger.info(f"  Combined ({logic_operator}): {combined}")
            return combined
        else:
            # Single condition (backward compatibility)
            result = self.single_evaluator.evaluate(value, condition_config)
            condition_eval_logger.info(f"  Single condition result: {result}")
            return result

    def _parse_logic_config(self, condition_config: Any) -> dict:
        """
        Parse configuration for logic operators.

        Handles both dict and dataclass formats.
        """
        if hasattr(condition_config, "__dict__"):
            # It's a dataclass
            return {
                "simple_conditions": getattr(condition_config, "simple_conditions", []),
                "logic_operator": getattr(condition_config, "logic_operator", "AND"),
            }
        else:
            # It's a dict
            return {
                "simple_conditions": condition_config.get("simple_conditions", []),
                "logic_operator": condition_config.get("logic_operator", "AND"),
            }

    def _extract_branch_condition(self, branch: Any) -> Any:
        """
        Extract condition from branch configuration.

        Handles both dict and dataclass formats.
        """
        if hasattr(branch, "__dict__"):
            return getattr(branch, "condition", {})
        else:
            return branch.get("condition", {})

    def _extract_handle_id(self, branch: Any) -> str:
        """
        Extract handle ID from branch configuration.

        Handles both dict and dataclass formats.
        """
        if hasattr(branch, "__dict__"):
            return getattr(branch, "handle_id", "branch-0")
        else:
            return branch.get("handle_id", "branch-0")
