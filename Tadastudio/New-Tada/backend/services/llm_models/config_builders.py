"""Utility functions for creating common LLM configurations."""

from typing import Optional

from backend.models.workflow.configs.llm import LLMConfig


def create_azure_openai_config(
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    api_version: str = "2024-02-15-preview",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """
    Create Azure OpenAI configuration.

    Args:
        model_name: Azure OpenAI model name
        api_key: Optional API key (uses env var if not provided)
        endpoint: Optional Azure endpoint (uses env var if not provided)
        api_version: Azure API version
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        LLMConfig for Azure OpenAI
    """
    credentials = {}
    if api_key:
        credentials["api_key"] = api_key
    if endpoint:
        credentials["endpoint"] = endpoint

    return LLMConfig(
        provider="azure_openai",
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        credentials=credentials,
        config={"api_version": api_version},
    )


def create_openai_config(
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """
    Create OpenAI configuration.

    Args:
        model_name: OpenAI model name
        api_key: Optional API key (uses env var if not provided)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        LLMConfig for OpenAI
    """
    credentials = {}
    if api_key:
        credentials["api_key"] = api_key

    return LLMConfig(
        provider="openai",
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        credentials=credentials,
    )


def create_anthropic_config(
    model_name: str = "claude-3-sonnet-20240229",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """
    Create Anthropic configuration.

    Args:
        model_name: Anthropic model name
        api_key: Optional API key (uses env var if not provided)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        LLMConfig for Anthropic
    """
    credentials = {}
    if api_key:
        credentials["api_key"] = api_key

    return LLMConfig(
        provider="anthropic",
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        credentials=credentials,
    )
