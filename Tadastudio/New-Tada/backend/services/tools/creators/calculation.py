"""
Calculation tool creators.

Handles creation of mathematical calculation tools.
"""

from typing import Any, Dict

from langchain_core.tools import BaseTool, Tool

from ...config import get_logger
from .base import BaseToolCreator


logger = get_logger("tool-creators")


class CalculationCreator(BaseToolCreator):
    """Creator for calculation tools."""

    def get_tool_names(self) -> list[str]:
        """Get list of calculation tool names."""
        return ["calculator"]

    def create(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        """
        Create a calculation tool.

        Args:
            tool_name: Name of the calculation tool
            config: Tool configuration

        Returns:
            Configured calculation tool

        Raises:
            ValueError: If tool_name is unknown
        """
        if tool_name == "calculator":
            return self._create_calculator_tool(config)
        else:
            raise ValueError(f"Unknown calculation tool: {tool_name}")

    def _create_calculator_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a calculator tool with safe evaluation.

        Args:
            config: Tool configuration

        Returns:
            Calculator tool instance
        """
        try:

            def safe_calculate(expression: str) -> str:
                """
                Safely evaluate mathematical expressions.

                Args:
                    expression: Mathematical expression to evaluate

                Returns:
                    String result of calculation or error message
                """
                try:
                    # Remove dangerous operations
                    dangerous_keywords = ["import", "exec", "eval", "__"]
                    if any(danger in expression for danger in dangerous_keywords):
                        return "Error: Unsafe expression"

                    # Use numexpr for safe evaluation
                    import numexpr

                    result = numexpr.evaluate(expression)
                    return str(result)
                except Exception as e:
                    return f"Error: {str(e)}"

            return Tool(
                name="calculator",
                description="Perform mathematical calculations",
                func=safe_calculate,
            )
        except Exception as e:
            logger.error(f"[CALCULATION-CREATOR] Failed to create calculator: {e}")
            raise
