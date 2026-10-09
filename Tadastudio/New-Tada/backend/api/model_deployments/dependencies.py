"""FastAPI dependencies for model deployment API.

This module provides dependency injection functions for the
model deployment API endpoints.
"""

from __future__ import annotations

from functools import lru_cache

from ...services.llm_models import LLMFactory
from ...services.model_deployment import ModelDeploymentService


@lru_cache(maxsize=1)
def get_model_deployment_service() -> ModelDeploymentService:
    """Get model deployment service instance.

    Returns:
        ModelDeploymentService instance (singleton)
    """
    return ModelDeploymentService()


@lru_cache(maxsize=1)
def get_llm_factory() -> LLMFactory:
    """Get LLM factory instance.

    Returns:
        LLMFactory instance configured with model deployment service
    """
    service = get_model_deployment_service()
    return LLMFactory(model_service=service)
