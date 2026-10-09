"""
Passthrough Boolean Evaluator.

Interprets values directly as boolean (case-insensitive strict matching).
Used for binary condition nodes that simply route based on true/false input values.
"""

from typing import Any

from backend.services.config import get_logger

passthrough_logger = get_logger("conditions.evaluators.passthrough")


class PassthroughBooleanEvaluator:
    """
    Evaluates values as boolean directly without comparison operators.

    Handles case-insensitive string matching for "true"/"false".
    This is used when binary condition nodes want to simply interpret
    their input value as a boolean without additional comparison logic.
    """

    def evaluate(self, value: Any) -> bool:
        """
        Evaluate a value as boolean.

        Args:
            value: The value to interpret as boolean

        Returns:
            True if value represents truthy, False otherwise
        """
        passthrough_logger.info(
            f"    Passthrough interpreting: {value!r} (type={type(value).__name__})"
        )

        # Handle actual boolean type
        if isinstance(value, bool):
            passthrough_logger.info(f"    -> bool literal: {value}")
            return value

        # Handle string values (case-insensitive, strict "true"/"false" matching)
        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized == "true":
                passthrough_logger.info("    -> string 'true' matched")
                return True
            elif normalized == "false":
                passthrough_logger.info("    -> string 'false' matched")
                return False

            # Non-recognized strings: fall back to Python truthiness
            # (non-empty string is truthy)
            result = bool(normalized)
            passthrough_logger.info(
                f"    -> string truthiness ({normalized!r}): {result}"
            )
            return result

        # Handle None
        if value is None:
            passthrough_logger.info("    -> None: False")
            return False

        # Handle other types (int, float, list, dict, etc.)
        # Uses Python's built-in truthiness
        result = bool(value)
        passthrough_logger.info(f"    -> Python truthiness: {result}")
        return result
