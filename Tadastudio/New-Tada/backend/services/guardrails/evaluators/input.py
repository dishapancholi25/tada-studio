"""Input guardrail evaluator.

Validates user input before it reaches the LLM by applying content
filters and behavioral checks (via LLM-as-judge classification).
"""

import logging
from typing import TYPE_CHECKING, Optional

from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.guardrails.pattern_rules import apply_pattern_rules
from backend.services.guardrails.evaluators.behavioral import (
    BehavioralGuardrailEvaluator,
)
from backend.services.guardrails.models import GuardrailResult

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

logger = logging.getLogger(__name__)


class InputGuardrailEvaluator:
    """Evaluates user input against content filters and behavioral checks."""

    def __init__(
        self,
        llm_factory: Optional["LLMFactory"] = None,
        model_service: Optional["ModelDeploymentService"] = None,
    ):
        self.behavioral_evaluator = BehavioralGuardrailEvaluator(
            llm_factory=llm_factory,
            model_service=model_service,
        )

    async def evaluate(
        self,
        content: str,
        config: GuardrailsConfig,
        vault_id: Optional[str] = None,
    ) -> GuardrailResult:
        """Evaluate user input against guardrails.

        Applies content filters and behavioral safety checks.

        Args:
            content: The user input text
            config: Guardrails configuration
            vault_id: Optional vault session id for PII anonymization

        Returns:
            GuardrailResult with any violations found
        """
        result = GuardrailResult(passed=True)

        # Apply pattern rules (synchronous)
        if config.pattern_rules:
            filter_result = apply_pattern_rules(content, config.pattern_rules, "input")
            result = result.merge(filter_result)

        # Apply behavioral checks (async — LLM-as-judge)
        # Chain content: use post-pattern sanitized text so behavioral scanners
        # operate on already-redacted input rather than raw content.
        if config.has_behavioral_checks:
            effective_content = (
                result.sanitized_content
                if result.sanitized_content is not None
                else content
            )
            behavioral_result = await self.behavioral_evaluator.evaluate(
                effective_content, config, vault_id=vault_id
            )
            result = result.merge(behavioral_result)

        return result
