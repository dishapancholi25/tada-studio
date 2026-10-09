"""Validation utilities for LLM configurations."""

from typing import Dict, Type

from backend.models.workflow.configs.llm import LLMConfig
from .constants import (
    AVAILABLE_MODELS,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    SUPPORTED_PROVIDERS,
)
from .providers.base import LLMProvider


def validate_llm_config(
    config: LLMConfig, providers: Dict[str, Type[LLMProvider]]
) -> list[str]:
    """
    Validate LLM configuration.

    Args:
        config: LLM configuration to validate
        providers: Dictionary of provider instances

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check provider
    if config.provider not in SUPPORTED_PROVIDERS:
        errors.append(f"Unsupported provider: {config.provider}")
        return errors  # Can't validate further without valid provider

    # Check model name
    provider_models = AVAILABLE_MODELS.get(config.provider, [])
    if config.model_name not in provider_models:
        errors.append(
            f"Model {config.model_name} not available for provider {config.provider}"
        )

    # Check temperature range
    if not MIN_TEMPERATURE <= config.temperature <= MAX_TEMPERATURE:
        errors.append(
            f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}"
        )

    # Check max_tokens
    if config.max_tokens is not None and config.max_tokens <= 0:
        errors.append("max_tokens must be positive")

    # Provider-specific validation
    provider_class = providers.get(config.provider)
    if provider_class:
        provider_instance = provider_class()
        provider_errors = provider_instance.validate(config)
        errors.extend(provider_errors)

    return errors
