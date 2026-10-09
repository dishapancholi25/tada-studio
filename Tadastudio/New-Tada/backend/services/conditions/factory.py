"""
Condition Function Factory.

Creates condition functions for conditional routing in graphs.
"""

from typing import Any, Callable

from backend.services.conditions.evaluator import ConditionEvaluator
from backend.services.execution.logging import execution_logger
from backend.services.workflow.state import WorkflowState


class ConditionFunctionFactory:
    """
    Factory for creating condition functions.

    Creates functions that evaluate conditions and return routing decisions.
    """

    def __init__(self, condition_evaluator: ConditionEvaluator):
        """
        Initialize the factory.

        Args:
            condition_evaluator: The condition evaluator to use
        """
        self.evaluator = condition_evaluator

    def create_condition_function(
        self, node: Any, graph: Any
    ) -> Callable[[WorkflowState], str]:
        """
        Create a condition function for conditional routing.

        Args:
            node: The condition node
            graph: The complete graph

        Returns:
            A function that evaluates the condition and returns the next node
        """

        def condition_function(state: WorkflowState) -> str:
            """Evaluate condition and return next node ID or branch label."""
            execution_logger.info(f"Evaluating condition: {node.name}")

            # Check if result was pre-computed
            stored_result = self._get_stored_result(state, node.uniq_id)
            if stored_result is not None:
                return stored_result

            # Get and validate configuration
            condition_config = node.condition_config
            if not condition_config:
                execution_logger.warning(
                    f"No condition config for {node.name}, using default"
                )
                return "default"

            # Parse configuration
            config = self._parse_config(condition_config)
            branch_mode = config["branch_mode"]
            branches = config["branches"]
            condition_type = config["condition_type"]

            # Evaluate based on mode and type
            final_result = self._evaluate_condition(
                state,
                condition_config,
                branch_mode,
                branches,
                condition_type,
                node,
                graph,
            )

            # Store result for later retrieval
            self._store_result(state, node.uniq_id, final_result)

            return final_result

        return condition_function

    def _get_stored_result(self, state: WorkflowState, node_id: str) -> str:
        """
        Get pre-computed condition result if available.

        Args:
            state: The workflow state
            node_id: Unique node identifier

        Returns:
            Stored result or None
        """
        stored_result = state.get(f"__condition_result_{node_id}")
        if stored_result is not None:
            execution_logger.info(
                f"Using pre-computed condition result: {stored_result}"
            )
        return stored_result

    def _store_result(self, state: WorkflowState, node_id: str, result: str):
        """
        Store condition result in state.

        Args:
            state: The workflow state
            node_id: Unique node identifier
            result: Evaluation result
        """
        state[f"__condition_result_{node_id}"] = result

    def _parse_config(self, condition_config: Any) -> dict:
        """
        Parse condition configuration.

        Handles both dict and dataclass formats.

        Args:
            condition_config: Configuration object

        Returns:
            Dictionary with parsed configuration
        """
        if hasattr(condition_config, "__dict__"):
            # It's a dataclass
            return {
                "branch_mode": getattr(condition_config, "branch_mode", "binary"),
                "branches": getattr(condition_config, "branches", []),
                "condition_type": getattr(condition_config, "condition_type", "simple"),
            }
        else:
            # It's a dict
            return {
                "branch_mode": condition_config.get("branch_mode", "binary"),
                "branches": condition_config.get("branches", []),
                "condition_type": condition_config.get("condition_type", "simple"),
            }

    def _evaluate_condition(
        self,
        state: WorkflowState,
        condition_config: Any,
        branch_mode: str,
        branches: list,
        condition_type: str,
        node: Any,
        graph: Any,
    ) -> str:
        """
        Evaluate condition and return routing decision.

        Args:
            state: The workflow state
            condition_config: Condition configuration
            branch_mode: Mode (binary or multi)
            branches: List of branches for multi mode
            condition_type: Type (simple, expression, or llm)
            node: The condition node
            graph: The complete graph

        Returns:
            Routing decision as string
        """
        if branch_mode == "multi":
            return self._evaluate_multi_branch(state, branches, node)
        elif condition_type == "expression":
            return self._evaluate_expression_type(state, condition_config, node)
        elif condition_type == "llm":
            return self._evaluate_llm_type(state, condition_config, node, graph)
        else:
            return self._evaluate_binary_type(state, condition_config, node)

    def _evaluate_multi_branch(
        self, state: WorkflowState, branches: list, node: Any
    ) -> str:
        """
        Evaluate multi-branch condition.

        Args:
            state: The workflow state
            branches: List of branch configurations
            node: The condition node

        Returns:
            Branch handle ID or "0" for default
        """
        execution_logger.info(f"Multi-branch mode with {len(branches)} branches")

        result = self.evaluator.evaluate_multi_branch(state, branches)

        if result == "0":
            execution_logger.info(
                f"No branches matched for {node.name}, using default: {result}"
            )
        else:
            execution_logger.info(
                f"Condition {node.name} matched branch, returning: {result}"
            )

        return result

    def _evaluate_expression_type(
        self, state: WorkflowState, condition_config: Any, node: Any
    ) -> str:
        """
        Evaluate expression-based condition.

        Binary mode uses branch handles "branch-0" (True) and "branch-1" (False).
        The edge builder strips the "branch-" prefix, so routing keys are "0" and "1".

        Args:
            state: The workflow state
            condition_config: Configuration with expression
            node: The condition node

        Returns:
            "0" for true branch, "1" for false branch
        """
        result = self.evaluator.evaluate_expression(state, condition_config)
        execution_logger.info(
            f"Expression condition {node.name} evaluated to: {result}"
        )
        # Return "0" for true (branch-0), "1" for false (branch-1)
        return "0" if result else "1"

    def _evaluate_llm_type(
        self, state: WorkflowState, condition_config: Any, node: Any, graph: Any
    ) -> str:
        """
        Evaluate LLM-based condition.

        Args:
            state: The workflow state
            condition_config: Configuration with LLM prompt
            node: The condition node
            graph: The complete graph

        Returns:
            Routing decision from LLM
        """
        result = self.evaluator.evaluate_llm(state, condition_config, graph)
        execution_logger.info(f"LLM condition {node.name} evaluated to: {result}")
        return result

    def _evaluate_binary_type(
        self, state: WorkflowState, condition_config: Any, node: Any
    ) -> str:
        """
        Evaluate binary condition.

        Binary mode uses branch handles "branch-0" (True) and "branch-1" (False).
        The edge builder strips the "branch-" prefix, so routing keys are "0" and "1".

        Args:
            state: The workflow state
            condition_config: Condition configuration
            node: The condition node

        Returns:
            "0" for true branch, "1" for false branch
        """
        result = self.evaluator.evaluate_binary_condition(state, condition_config)
        execution_logger.info(f"Binary condition {node.name} evaluated to: {result}")
        # Return "0" for true (branch-0), "1" for false (branch-1)
        return "0" if result else "1"
