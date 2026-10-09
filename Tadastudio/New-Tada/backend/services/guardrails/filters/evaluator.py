"""Custom filter evaluator — orchestrates all three filter executor types.

Runs user-defined filters in priority order. Transform results cascade
through the chain (each filter's output becomes the next filter's input).
Block actions stop the pipeline immediately. Filter errors produce warnings.
"""

import logging
from typing import TYPE_CHECKING, List, Optional

from backend.services.guardrails.filters.executors.declarative import (
    DeclarativeFilterExecutor,
)
from backend.services.guardrails.filters.executors.llm_judge import (
    LLMJudgeFilterExecutor,
)
from backend.services.guardrails.filters.executors.python_sandbox import (
    CodeValidationError,
    FilterTimeoutError,
    get_shared_sandbox_executor,
)
from backend.services.guardrails.models import GuardrailResult, Violation

if TYPE_CHECKING:
    from backend.models.workflow.configs.guardrails import CustomFilter
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

logger = logging.getLogger(__name__)


class CustomFilterEvaluator:
    """Evaluates content through user-defined custom filters.

    Runs filters in priority order. For transform actions,
    each filter's output becomes the next filter's input.
    Block stops the pipeline. Errors produce warnings, never blocks.
    """

    def __init__(
        self,
        llm_factory: Optional["LLMFactory"] = None,
        model_service: Optional["ModelDeploymentService"] = None,
    ):
        self.python_executor = get_shared_sandbox_executor()
        self.llm_judge_executor = LLMJudgeFilterExecutor(
            llm_factory=llm_factory,
            model_service=model_service,
        )
        self.declarative_executor = DeclarativeFilterExecutor(
            llm_factory=llm_factory,
            model_service=model_service,
        )

    async def evaluate(
        self,
        content: str,
        filters: List["CustomFilter"],
        direction: str,
    ) -> GuardrailResult:
        """Run all applicable filters in priority order.

        Args:
            content: The content to filter
            filters: List of CustomFilter definitions
            direction: "ingress" or "egress"

        Returns:
            Merged GuardrailResult with all violations and any transforms applied
        """
        # Filter to applicable and enabled filters, sorted by priority
        applicable = [
            f for f in filters if f.enabled and f.scope in (direction, "both")
        ]
        applicable.sort(key=lambda f: f.priority)

        if not applicable:
            return GuardrailResult(passed=True)

        current_content = content
        all_violations: List[Violation] = []
        has_block = False
        has_transform = False

        for filter_def in applicable:
            try:
                result = await self._execute_single_filter(
                    filter_def, current_content, direction
                )
                all_violations.extend(result.violations)

                if result.action_taken == "blocked":
                    has_block = True
                    break  # Stop pipeline on block

                if result.sanitized_content is not None:
                    current_content = result.sanitized_content
                    has_transform = True

            except Exception as e:
                logger.error(
                    f"[GUARDRAILS] Custom filter '{filter_def.name}' unexpected error: {e}",
                    exc_info=True,
                )
                all_violations.append(
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_error",
                        severity="warn",
                        message=f"Filter '{filter_def.name}' failed: {str(e)[:200]}",
                        details={"error": str(e), "filter_id": filter_def.id},
                    )
                )

        # Build final result
        if has_block:
            return GuardrailResult(
                passed=False,
                violations=all_violations,
                action_taken="blocked",
            )
        if has_transform:
            return GuardrailResult(
                passed=True,
                violations=all_violations,
                action_taken="transformed",
                sanitized_content=current_content,
            )
        if all_violations:
            return GuardrailResult(
                passed=True,
                violations=all_violations,
                action_taken="warned",
            )
        return GuardrailResult(passed=True)

    async def _execute_single_filter(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Execute a single filter based on its type.

        Args:
            filter_def: The filter definition
            content: Content to filter
            direction: "ingress" or "egress"

        Returns:
            GuardrailResult from the filter execution
        """
        if filter_def.filter_type == "python_code":
            return await self._execute_python_filter(filter_def, content, direction)
        elif filter_def.filter_type == "llm_judge":
            return await self.llm_judge_executor.execute(filter_def, content, direction)
        elif filter_def.filter_type == "declarative":
            return await self.declarative_executor.execute(
                filter_def, content, direction
            )
        else:
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_unknown_type",
                        severity="warn",
                        message=f"Unknown filter type '{filter_def.filter_type}'",
                        details={"filter_id": filter_def.id},
                    )
                ],
                action_taken="warned",
            )

    async def _execute_python_filter(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Execute a Python code filter in the sandbox."""
        try:
            result = self.python_executor.execute(
                filter_def.python_code, content, direction, action=filter_def.action
            )
        except (CodeValidationError, FilterTimeoutError, ValueError) as e:
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_error",
                        severity="warn",
                        message=f"Python filter '{filter_def.name}' error: {str(e)[:200]}",
                        details={"filter_id": filter_def.id, "error": str(e)},
                    )
                ],
                action_taken="warned",
            )

        passed = result.get("passed", True)
        message = result.get("message", filter_def.message or "Filter triggered")
        transformed_content = result.get("content")

        if passed:
            # Filter passed — but may still have transformed content
            if filter_def.action == "transform" and transformed_content:
                return GuardrailResult(
                    passed=True,
                    sanitized_content=transformed_content,
                )
            return GuardrailResult(passed=True)

        # Filter triggered (passed=False)
        if filter_def.action == "transform" and transformed_content:
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=filter_def.name,
                        severity="warn",
                        message=message,
                        details={"filter_id": filter_def.id, "action": "transform"},
                    )
                ],
                action_taken="transformed",
                sanitized_content=transformed_content,
            )

        if filter_def.action == "block":
            return GuardrailResult(
                passed=False,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=filter_def.name,
                        severity="block",
                        message=message,
                        details={"filter_id": filter_def.id},
                    )
                ],
                action_taken="blocked",
            )

        # warn
        return GuardrailResult(
            passed=True,
            violations=[
                Violation(
                    category="custom_filter",
                    rule_name=filter_def.name,
                    severity="warn",
                    message=message,
                    details={"filter_id": filter_def.id},
                )
            ],
            action_taken="warned",
        )
