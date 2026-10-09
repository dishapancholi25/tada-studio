"""Evaluation service package.

Provides the orchestrator, LLM dispatch queue, evaluation context,
and repository classes for the automated evaluation system.
"""

from .eval_context import (
    clear_evaluation_context,
    get_evaluation_run_id,
    is_evaluation_context,
    set_evaluation_context,
)
from .llm_dispatch_queue import EvaluationLLMDispatchQueue, get_llm_dispatch_queue
from .orchestrator import EvaluationOrchestrator
from .regression import RegressionPolicyService
from .repositories import (
    EvaluationDatasetRepository,
    EvaluationRecommendationRepository,
    EvaluationResultRepository,
    EvaluationRunRepository,
)
from .recommendations import RecommendationEngine
from .target_context import TargetContextService
from .trigger import EvaluationTriggerService

__all__ = [
    "EvaluationOrchestrator",
    "EvaluationLLMDispatchQueue",
    "get_llm_dispatch_queue",
    "set_evaluation_context",
    "clear_evaluation_context",
    "get_evaluation_run_id",
    "is_evaluation_context",
    "EvaluationRunRepository",
    "EvaluationResultRepository",
    "EvaluationDatasetRepository",
    "EvaluationRecommendationRepository",
    "RecommendationEngine",
    "EvaluationTriggerService",
    "RegressionPolicyService",
    "TargetContextService",
]
