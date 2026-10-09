"""LLM configuration validation.

This module provides validation logic for LLM configurations.
"""

from typing import List

from ..configs.llm import LLMConfig


def validate_llm_config(llm_config: LLMConfig) -> List[str]:
    """Validate LLM configuration.

    Args:
        llm_config: LLM configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not llm_config.provider and not llm_config.model_deployment_id:
        errors.append("LLM provider is required")

    if not llm_config.model_name:
        errors.append("Model name is required")

    if llm_config.temperature < 0 or llm_config.temperature > 2:
        errors.append("Temperature must be between 0 and 2")

    if llm_config.max_tokens is not None and llm_config.max_tokens <= 0:
        errors.append("Max tokens must be positive")

    # Additional validation only required when no managed deployment is referenced
    if not llm_config.model_deployment_id:
        if llm_config.provider == "azure_openai":
            if not llm_config.deployment_name:
                errors.append("Deployment name is required for Azure OpenAI")
            if not llm_config.api_version:
                errors.append("API version is required for Azure OpenAI")

        if not llm_config.api_key_env_var:
            errors.append("API key environment variable name is required")

    return errors
