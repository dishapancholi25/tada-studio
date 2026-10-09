"""Token budget guardrail evaluator.

Tracks cumulative token usage across an execution and enforces
configured budget limits.
"""

import logging
from typing import Any, Dict

from backend.models.workflow.configs.guardrails import TokenBudget
from backend.services.guardrails.models import GuardrailResult, Violation

logger = logging.getLogger(__name__)


class TokenBudgetEvaluator:
    """Evaluates token usage against configured budget limits."""

    def evaluate(
        self, current_usage: Dict[str, Any], budget: TokenBudget
    ) -> GuardrailResult:
        """Check if current token usage exceeds budget limits.

        Args:
            current_usage: Dictionary with keys:
                - input_tokens: cumulative input tokens
                - output_tokens: cumulative output tokens
                - total_tokens: cumulative total tokens
                - llm_calls: cumulative LLM call count
            budget: Token budget configuration

        Returns:
            GuardrailResult with any violations found
        """
        violations = []
        input_tokens = current_usage.get("input_tokens", 0)
        output_tokens = current_usage.get("output_tokens", 0)
        total_tokens = current_usage.get("total_tokens", 0)
        llm_calls = current_usage.get("llm_calls", 0)

        # Check input tokens
        if (
            budget.max_input_tokens_per_execution
            and input_tokens > budget.max_input_tokens_per_execution
        ):
            violations.append(
                Violation(
                    category="token_budget",
                    rule_name="input_tokens_exceeded",
                    severity="block",
                    message=(
                        f"Input token budget exceeded "
                        f"({input_tokens} > {budget.max_input_tokens_per_execution})"
                    ),
                    details={
                        "current": input_tokens,
                        "limit": budget.max_input_tokens_per_execution,
                    },
                )
            )

        # Check output tokens
        if (
            budget.max_output_tokens_per_execution
            and output_tokens > budget.max_output_tokens_per_execution
        ):
            violations.append(
                Violation(
                    category="token_budget",
                    rule_name="output_tokens_exceeded",
                    severity="block",
                    message=(
                        f"Output token budget exceeded "
                        f"({output_tokens} > {budget.max_output_tokens_per_execution})"
                    ),
                    details={
                        "current": output_tokens,
                        "limit": budget.max_output_tokens_per_execution,
                    },
                )
            )

        # Check total tokens
        if (
            budget.max_total_tokens_per_execution
            and total_tokens > budget.max_total_tokens_per_execution
        ):
            violations.append(
                Violation(
                    category="token_budget",
                    rule_name="total_tokens_exceeded",
                    severity="block",
                    message=(
                        f"Total token budget exceeded "
                        f"({total_tokens} > {budget.max_total_tokens_per_execution})"
                    ),
                    details={
                        "current": total_tokens,
                        "limit": budget.max_total_tokens_per_execution,
                    },
                )
            )

        # Check LLM call count
        if llm_calls > budget.max_llm_calls_per_execution:
            violations.append(
                Violation(
                    category="token_budget",
                    rule_name="llm_calls_exceeded",
                    severity="block",
                    message=(
                        f"LLM call limit exceeded "
                        f"({llm_calls} > {budget.max_llm_calls_per_execution})"
                    ),
                    details={
                        "current": llm_calls,
                        "limit": budget.max_llm_calls_per_execution,
                    },
                )
            )

        # Check warning threshold
        if not violations and budget.warn_at_percentage < 1.0:
            self._check_warnings(current_usage, budget, violations)

        if any(v.severity == "block" for v in violations):
            return GuardrailResult(
                passed=False, violations=violations, action_taken="blocked"
            )

        if violations:
            return GuardrailResult(
                passed=True, violations=violations, action_taken="warned"
            )

        return GuardrailResult(passed=True)

    def _check_warnings(
        self, current_usage: Dict[str, Any], budget: TokenBudget, violations: list
    ) -> None:
        """Check if usage has reached the warning threshold."""
        threshold = budget.warn_at_percentage

        if budget.max_total_tokens_per_execution:
            total = current_usage.get("total_tokens", 0)
            limit = budget.max_total_tokens_per_execution
            if total >= limit * threshold:
                violations.append(
                    Violation(
                        category="token_budget",
                        rule_name="token_budget_warning",
                        severity="warn",
                        message=f"Token usage at {total / limit:.0%} of budget ({total}/{limit})",
                        details={
                            "current": total,
                            "limit": limit,
                            "threshold": threshold,
                        },
                    )
                )

        if budget.max_llm_calls_per_execution:
            calls = current_usage.get("llm_calls", 0)
            limit = budget.max_llm_calls_per_execution
            if calls >= limit * threshold:
                violations.append(
                    Violation(
                        category="token_budget",
                        rule_name="llm_calls_warning",
                        severity="warn",
                        message=f"LLM calls at {calls / limit:.0%} of budget ({calls}/{limit})",
                        details={
                            "current": calls,
                            "limit": limit,
                            "threshold": threshold,
                        },
                    )
                )
