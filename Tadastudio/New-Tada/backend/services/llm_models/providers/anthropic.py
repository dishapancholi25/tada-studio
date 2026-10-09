"""Anthropic provider implementation."""

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from backend.models.workflow.configs.llm import LLMConfig
from backend.services.config.execution import ExecutionConfig
from ..constants import LOG_PREFIX
from ..exceptions import CredentialMissingError
from .base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic models."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        """Create Anthropic LLM instance."""
        api_key = self._get_credential(config, "api_key", "ANTHROPIC_API_KEY")

        if not api_key:
            raise CredentialMissingError("Anthropic requires api_key")

        logger.info(
            "%s Creating Anthropic client (model=%s)",
            LOG_PREFIX,
            config.model_name,
        )

        kwargs: dict = {}
        if config.top_p is not None:
            kwargs["top_p"] = config.top_p
        # verify_ssl is not supported by ChatAnthropic; strip it before spreading
        config.config.pop("verify_ssl", None)

        return ChatAnthropic(
            api_key=api_key,
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
            streaming=ExecutionConfig.enable_streaming(),
            **kwargs,
            **config.config,
        )

    def validate(self, config: LLMConfig) -> list[str]:
        """Validate Anthropic configuration."""
        errors = []

        api_key = self._get_credential(config, "api_key", "ANTHROPIC_API_KEY")
        if not api_key:
            errors.append(
                "Anthropic requires api_key in credentials or ANTHROPIC_API_KEY environment variable"
            )

        return errors
