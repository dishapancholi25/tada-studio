"""
Expression Condition Evaluator.

Evaluates Python expression-based conditions safely using AST visitor pattern.
"""

import ast
import operator
from typing import Any

from backend.services.execution.logging import execution_logger
from backend.services.workflow.state import WorkflowState


class SafeExpressionEvaluator(ast.NodeVisitor):
    """
    AST-based safe expression evaluator.

    Only allows whitelisted operations and prevents code injection.
    """

    # Whitelisted comparison operators
    COMPARE_OPS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
    }

    # Whitelisted boolean operators
    BOOL_OPS = {
        ast.And: all,
        ast.Or: any,
    }

    # Whitelisted unary operators
    UNARY_OPS = {
        ast.Not: operator.not_,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    # Whitelisted binary operators
    BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    # Whitelisted functions
    SAFE_FUNCTIONS = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
    }

    def __init__(self, context: dict):
        """
        Initialize the safe evaluator.

        Args:
            context: Variable context for evaluation
        """
        self.context = context

    def evaluate(self, expression: str) -> Any:
        """
        Safely evaluate an expression.

        Args:
            expression: The expression string to evaluate

        Returns:
            The evaluation result

        Raises:
            ValueError: If expression contains disallowed operations
            SyntaxError: If expression has invalid syntax
        """
        tree = ast.parse(expression, mode="eval")
        return self.visit(tree.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        """Visit a constant value (string, number, None, bool)."""
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        """Visit a variable name."""
        if node.id not in self.context:
            raise NameError(f"Name '{node.id}' is not defined")
        return self.context[node.id]

    def visit_Compare(self, node: ast.Compare) -> bool:
        """Visit a comparison operation."""
        left = self.visit(node.left)

        for op, comparator in zip(node.ops, node.comparators):
            if type(op) not in self.COMPARE_OPS:
                raise ValueError(f"Comparison operator {type(op).__name__} not allowed")

            right = self.visit(comparator)
            op_func = self.COMPARE_OPS[type(op)]

            if not op_func(left, right):
                return False
            left = right

        return True

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:
        """Visit a boolean operation (and/or)."""
        if type(node.op) not in self.BOOL_OPS:
            raise ValueError(f"Boolean operator {type(node.op).__name__} not allowed")

        values = [self.visit(value) for value in node.values]

        if isinstance(node.op, ast.And):
            return all(values)
        else:  # ast.Or
            return any(values)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        """Visit a unary operation (not, +, -)."""
        if type(node.op) not in self.UNARY_OPS:
            raise ValueError(f"Unary operator {type(node.op).__name__} not allowed")

        operand = self.visit(node.operand)
        op_func = self.UNARY_OPS[type(node.op)]

        return op_func(operand)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        """Visit a binary operation (+, -, *, /, etc)."""
        if type(node.op) not in self.BIN_OPS:
            raise ValueError(f"Binary operator {type(node.op).__name__} not allowed")

        left = self.visit(node.left)
        right = self.visit(node.right)
        op_func = self.BIN_OPS[type(node.op)]

        return op_func(left, right)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        """Visit subscript access (dict['key'], list[0])."""
        value = self.visit(node.value)
        index = self.visit(node.slice)

        try:
            return value[index]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Subscript access failed: {e}")

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Visit attribute access (obj.attr)."""
        # Block access to dunder attributes for security
        if node.attr.startswith("__") and node.attr.endswith("__"):
            raise ValueError(f"Access to special attribute '{node.attr}' not allowed")

        value = self.visit(node.value)

        try:
            return getattr(value, node.attr)
        except AttributeError as e:
            raise ValueError(f"Attribute access failed: {e}")

    def visit_List(self, node: ast.List) -> list:
        """Visit a list literal."""
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple:
        """Visit a tuple literal."""
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_Dict(self, node: ast.Dict) -> dict:
        """Visit a dict literal."""
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def visit_Call(self, node: ast.Call) -> Any:
        """Visit a function call (only whitelisted functions)."""
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")

        func_name = node.func.id

        if func_name not in self.SAFE_FUNCTIONS:
            raise ValueError(f"Function '{func_name}' is not allowed")

        # Evaluate arguments
        args = [self.visit(arg) for arg in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}

        func = self.SAFE_FUNCTIONS[func_name]

        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise ValueError(f"Function call failed: {e}")

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        """Visit a ternary expression (a if condition else b)."""
        test = self.visit(node.test)
        if test:
            return self.visit(node.body)
        else:
            return self.visit(node.orelse)

    def generic_visit(self, node: ast.AST) -> None:
        """
        Reject any AST node types not explicitly whitelisted.
        """
        raise ValueError(
            f"Operation '{type(node).__name__}' is not allowed for security reasons"
        )


class ExpressionConditionEvaluator:
    """
    Evaluates conditions based on Python expressions.

    Uses a safe AST-based evaluator to prevent code injection.
    """

    def evaluate(self, state: WorkflowState, condition_config: Any) -> bool:
        """
        Evaluate a Python expression condition safely.

        Args:
            state: The workflow state
            condition_config: Configuration containing the expression

        Returns:
            True if expression evaluates to truthy value, False otherwise
        """
        # Extract expression from config
        expression = self._extract_expression(condition_config)
        if not expression:
            execution_logger.warning("No expression provided for evaluation")
            return False

        # Build evaluation context
        context = self._build_context(state)

        # Evaluate expression
        return self._evaluate_expression(expression, context)

    def _extract_expression(self, condition_config: Any) -> str:
        """
        Extract expression from configuration.

        Handles both dict and dataclass formats.

        Args:
            condition_config: Configuration object

        Returns:
            The expression string
        """
        if hasattr(condition_config, "__dict__"):
            return getattr(condition_config, "expression", "")
        else:
            return condition_config.get("expression", "")

    def _build_context(self, state: WorkflowState) -> dict:
        """
        Build a safe context for expression evaluation.

        Provides access to state data and safe built-in functions.

        Args:
            state: The workflow state

        Returns:
            Context dictionary for expression evaluation
        """
        return {
            "messages": state.get("messages", []),
            "node_outputs": state.get("node_outputs", {}),
            "original_message": state.get("original_message", ""),
        }

    def _evaluate_expression(self, expression: str, context: dict) -> bool:
        """
        Safely evaluate a Python expression using AST visitor pattern.

        Args:
            expression: The expression to evaluate
            context: Context with available variables

        Returns:
            Boolean result of evaluation
        """
        try:
            evaluator = SafeExpressionEvaluator(context)
            result = evaluator.evaluate(expression)
            return bool(result)

        except SyntaxError as e:
            execution_logger.warning(f"Syntax error in expression '{expression}': {e}")
            return False

        except (ValueError, NameError, TypeError) as e:
            execution_logger.warning(
                f"Failed to evaluate expression '{expression}': {e}"
            )
            return False

        except Exception as e:
            execution_logger.warning(
                f"Unexpected error evaluating expression '{expression}': {e}"
            )
            return False
