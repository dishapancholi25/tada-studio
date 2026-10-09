"""Guardrails service for enforcing safety policies on AI workflow executions.

Provides input/output content filtering, tool call validation (SSRF, SQL, file paths),
token budget tracking, and behavioral safety checks (LLM-as-judge classification).
"""

from typing import TYPE_CHECKING, Optional

from backend.services.guardrails.checkpoint import GuardrailCheckpoint, GuardrailContext
from backend.services.guardrails.engine import GuardrailsEngine, ResolvedGuardrails
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.guardrails.models import GuardrailResult, Violation

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

_guardrails_engine: Optional[GuardrailsEngine] = None


def _resolve_llm_deps(
    llm_factory: Optional["LLMFactory"] = None,
    model_service: Optional["ModelDeploymentService"] = None,
) -> tuple:
    """Resolve LLM dependencies, creating defaults if not provided."""
    if not llm_factory:
        from backend.services.llm_models import LLMFactory

        llm_factory = LLMFactory()
    if not model_service:
        from backend.services.model_deployment import ModelDeploymentService

        model_service = ModelDeploymentService()
    return llm_factory, model_service


def get_guardrails_engine(
    llm_factory: Optional["LLMFactory"] = None,
    model_service: Optional["ModelDeploymentService"] = None,
) -> GuardrailsEngine:
    """Get or create the singleton GuardrailsEngine instance.

    When llm_factory and model_service are provided, they are passed through
    to the behavioral evaluator for LLM-as-judge classification. If not
    provided, default instances are created automatically so LLM-based
    filters (topic guard, toxicity check, etc.) work out of the box.

    Args:
        llm_factory: Optional factory for creating LLM instances
        model_service: Optional service for model deployment management

    Returns:
        GuardrailsEngine instance
    """
    global _guardrails_engine
    if _guardrails_engine is None:
        llm_factory, model_service = _resolve_llm_deps(llm_factory, model_service)
        _guardrails_engine = GuardrailsEngine(
            llm_factory=llm_factory,
            model_service=model_service,
        )
    elif llm_factory and model_service:
        # Late-bind LLM dependencies if provided after initial creation
        _guardrails_engine.input_evaluator.behavioral_evaluator.llm_factory = (
            llm_factory
        )
        _guardrails_engine.input_evaluator.behavioral_evaluator.model_service = (
            model_service
        )
        _guardrails_engine.custom_filter_evaluator.llm_judge_executor.llm_factory = (
            llm_factory
        )
        _guardrails_engine.custom_filter_evaluator.llm_judge_executor.model_service = (
            model_service
        )
        _guardrails_engine.custom_filter_evaluator.declarative_executor.llm_factory = (
            llm_factory
        )
        _guardrails_engine.custom_filter_evaluator.declarative_executor.model_service = model_service
    return _guardrails_engine


__all__ = [
    "GuardrailCheckpoint",
    "GuardrailContext",
    "GuardrailsEngine",
    "ResolvedGuardrails",
    "GuardrailResult",
    "GuardrailViolationError",
    "Violation",
    "get_guardrails_engine",
]
