"""
Single Condition Evaluator.

Evaluates individual conditions with various operators.
"""

import re
from typing import Any

from backend.services.config import get_logger

single_eval_logger = get_logger("conditions.evaluators.single")


class SingleConditionEvaluator:
    """
    Evaluates single conditions with support for multiple operators.

    Supports:
    - Numeric comparisons: ==, !=, >, <, >=, <=
    - String comparisons: ==, !=, contains, not_contains
    - String patterns: starts_with, ends_with, matches (regex)
    - String checks: is_empty, is_not_empty
    - List operations: in, not_in
    """

    def evaluate(self, value: Any, condition: Any) -> bool:
        """
        Evaluate a single condition against a value.

        Args:
            value: The value to evaluate
            condition: Condition configuration with operator and compare value

        Returns:
            True if condition is met, False otherwise
        """
        # Parse condition configuration
        config = self._parse_condition(condition)
        operator_type = config["operator"]
        compare_value = config["compare_value"]
        value_type = config["value_type"]

        is_numeric = self._should_use_numeric_comparison(value_type, compare_value)
        mode = "numeric" if is_numeric else "string"
        single_eval_logger.info(
            f"    Comparing: {value!r} {operator_type} {compare_value!r} "
            f"(mode={mode}, value_type={value_type})"
        )

        # Determine if numeric comparison
        if is_numeric:
            result = self._evaluate_numeric(value, compare_value, operator_type)
        else:
            result = self._evaluate_string(value, compare_value, operator_type)

        single_eval_logger.info(f"    Comparison result: {result}")
        return result

    def _parse_condition(self, condition: Any) -> dict:
        """
        Parse condition configuration to extract operator and values.

        Handles both dict and dataclass formats.
        """
        if hasattr(condition, "__dict__"):
            # It's a dataclass
            return {
                "operator": getattr(condition, "operator", "=="),
                "compare_value": getattr(condition, "value", ""),
                "value_type": getattr(condition, "value_type", "auto"),
            }
        else:
            # It's a dict
            return {
                "operator": condition.get("operator", "=="),
                "compare_value": condition.get("value", ""),
                "value_type": condition.get("value_type", "auto"),
            }

    def _should_use_numeric_comparison(
        self, value_type: str, compare_value: Any
    ) -> bool:
        """
        Determine if numeric comparison should be used.

        Args:
            value_type: Specified value type ('number', 'string', or 'auto')
            compare_value: The comparison value

        Returns:
            True if numeric comparison should be used
        """
        return value_type == "number" or (
            value_type == "auto" and self._is_numeric(compare_value)
        )

    def _evaluate_numeric(self, value: Any, compare_value: Any, operator: str) -> bool:
        """
        Evaluate numeric condition.

        Args:
            value: The value to evaluate
            compare_value: The value to compare against
            operator: Comparison operator

        Returns:
            True if condition is met, False otherwise
        """
        try:
            value_num = float(value) if value is not None else 0
            compare_num = float(compare_value) if compare_value is not None else 0

            if operator == "==":
                return value_num == compare_num
            elif operator == "!=":
                return value_num != compare_num
            elif operator == ">":
                return value_num > compare_num
            elif operator == "<":
                return value_num < compare_num
            elif operator == ">=":
                return value_num >= compare_num
            elif operator == "<=":
                return value_num <= compare_num
            else:
                return False
        except (ValueError, TypeError):
            return False

    def _evaluate_string(self, value: Any, compare_value: Any, operator: str) -> bool:
        """
        Evaluate string condition.

        Args:
            value: The value to evaluate
            compare_value: The value to compare against
            operator: Comparison operator

        Returns:
            True if condition is met, False otherwise
        """
        value_str = str(value) if value is not None else ""
        compare_str = str(compare_value) if compare_value is not None else ""

        if operator == "==":
            return value_str == compare_str
        elif operator == "!=":
            return value_str != compare_str
        elif operator == "contains":
            return compare_str.lower() in value_str.lower()
        elif operator == "not_contains":
            return compare_str.lower() not in value_str.lower()
        elif operator == "starts_with":
            return value_str.lower().startswith(compare_str.lower())
        elif operator == "ends_with":
            return value_str.lower().endswith(compare_str.lower())
        elif operator == "is_empty":
            return not value_str.strip()
        elif operator == "is_not_empty":
            return bool(value_str.strip())
        elif operator == "matches":
            return self._evaluate_regex(value_str, compare_str)
        elif operator == "in":
            return self._evaluate_in_list(value_str, compare_value)
        elif operator == "not_in":
            return self._evaluate_not_in_list(value_str, compare_value)
        else:
            return False

    @staticmethod
    def _evaluate_regex(value_str: str, pattern: str) -> bool:
        """
        Evaluate regex pattern matching.

        Args:
            value_str: String to match against
            pattern: Regex pattern

        Returns:
            True if pattern matches, False otherwise
        """
        try:
            return bool(re.search(pattern, value_str))
        except Exception:
            return False

    @staticmethod
    def _evaluate_in_list(value_str: str, compare_value: Any) -> bool:
        """
        Check if value is in a list.

        Args:
            value_str: String value to check
            compare_value: List to check against

        Returns:
            True if value is in list, False otherwise
        """
        if isinstance(compare_value, list):
            return value_str in [str(v) for v in compare_value]
        return False

    @staticmethod
    def _evaluate_not_in_list(value_str: str, compare_value: Any) -> bool:
        """
        Check if value is not in a list.

        Args:
            value_str: String value to check
            compare_value: List to check against

        Returns:
            True if value is not in list, False or True based on type
        """
        if isinstance(compare_value, list):
            return value_str not in [str(v) for v in compare_value]
        return True

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        """
        Check if a value can be converted to a number.

        Args:
            value: Value to check

        Returns:
            True if value is numeric, False otherwise
        """
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False
        return False
