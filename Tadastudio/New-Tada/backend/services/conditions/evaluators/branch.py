"""
Branch Condition Evaluator.

Evaluates conditions for multi-branch routing.
"""

from typing import Any

from backend.services.conditions.evaluators.single import SingleConditionEvaluator
from backend.services.conditions.value_extractor import ValueExtractor
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

branch_eval_logger = get_logger("conditions.evaluators.branch")


class BranchConditionEvaluator:
    """
    Evaluates branch conditions for multi-branch routing.

    Uses ValueExtractor to get values and SingleConditionEvaluator to
    evaluate the condition.
    """

    def __init__(self):
        """Initialize the branch condition evaluator."""
        self.value_extractor = ValueExtractor()
        self.single_evaluator = SingleConditionEvaluator()

    def evaluate(
        self, state: WorkflowState, branch_condition: Any, parent_config: Any = None
    ) -> bool:
        """
        Evaluate a branch condition.

        Extracts value based on input source and evaluates it against
        the branch condition.

        Args:
            state: The workflow state
            branch_condition: Branch condition configuration
            parent_config: Optional parent condition config for fallback source info

        Returns:
            True if branch condition is met, False otherwise
        """
        # Extract value using the same logic as ValueExtractor
        value = self._extract_value_from_branch(state, branch_condition, parent_config)
        branch_eval_logger.info(
            f"    Branch extracted value: {value!r} (type={type(value).__name__})"
        )

        # Evaluate the condition using single evaluator
        result = self.single_evaluator.evaluate(value, branch_condition)
        return result

    def _extract_value_from_branch(
        self, state: WorkflowState, branch_condition: Any, parent_config: Any = None
    ) -> Any:
        """
        Extract value for branch evaluation.

        This is similar to ValueExtractor but operates directly on
        branch_condition instead of condition_config.

        Args:
            state: The workflow state
            branch_condition: Branch condition with input source info
            parent_config: Optional parent condition config for fallback source info

        Returns:
            The extracted value
        """
        # Parse branch condition configuration, with parent fallback
        config = self._parse_branch_config(branch_condition, parent_config)
        input_source = config["input_source"]
        source_node_id = config["source_node_id"]
        field_path = config["field_path"]

        branch_eval_logger.info(
            f"    Branch extraction: source={input_source!r}, "
            f"node_id={source_node_id!r}, field_path={field_path!r}"
        )

        # Route to appropriate extraction method
        if input_source == "specific":
            return self.value_extractor._extract_from_specific_node(
                state, source_node_id, field_path
            )
        elif input_source == "previous":
            return self.value_extractor._extract_from_previous(state, field_path)
        elif input_source == "start":
            return self.value_extractor._extract_from_start(state)
        else:
            return ""

    def _parse_branch_config(
        self, branch_condition: Any, parent_config: Any = None
    ) -> dict:
        """
        Parse branch condition configuration.

        Handles both dict and dataclass formats. Falls back to parent_config
        for input_source/source_node_id when the branch condition uses defaults.

        Args:
            branch_condition: Branch condition configuration
            parent_config: Optional parent condition config for fallback values

        Returns:
            Dictionary with parsed configuration
        """
        if hasattr(branch_condition, "__dict__"):
            input_source = getattr(branch_condition, "input_source", None)
            source_node_id = getattr(branch_condition, "source_node_id", None)
            field_path = getattr(branch_condition, "field_path", "")
        else:
            input_source = branch_condition.get("input_source")
            source_node_id = branch_condition.get("source_node_id")
            field_path = branch_condition.get("field_path", "")

        # Fall back to parent config when branch doesn't specify source
        if (
            (not input_source or input_source == "previous")
            and not source_node_id
            and parent_config
        ):
            if hasattr(parent_config, "__dict__"):
                parent_source = getattr(parent_config, "input_source", None)
                parent_node_id = getattr(parent_config, "source_node_id", None)
            else:
                parent_source = (
                    parent_config.get("input_source")
                    if isinstance(parent_config, dict)
                    else None
                )
                parent_node_id = (
                    parent_config.get("source_node_id")
                    if isinstance(parent_config, dict)
                    else None
                )

            if parent_source and parent_source != "previous" and parent_node_id:
                branch_eval_logger.info(
                    f"    Using parent config fallback: source={parent_source!r}, "
                    f"node_id={parent_node_id!r}"
                )
                input_source = parent_source
                source_node_id = parent_node_id

        return {
            "input_source": input_source or "previous",
            "source_node_id": source_node_id,
            "field_path": field_path,
        }
