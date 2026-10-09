"""OpenAI provider implementation."""

import logging
from typing import Any, Dict

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from backend.models.workflow.configs.llm import LLMConfig
from backend.services.config.execution import ExecutionConfig
from ..constants import LOG_PREFIX
from ..exceptions import CredentialMissingError
from ..param_transformer import get_param_transformer
from .base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        """Create OpenAI LLM instance."""
        api_key = self._get_credential(config, "api_key", "OPENAI_API_KEY")

        if not api_key:
            raise CredentialMissingError("OpenAI requires api_key")

        logger.info(
            "%s Creating OpenAI client (model=%s)",
            LOG_PREFIX,
            config.model_name,
        )

        kwargs: Dict[str, Any] = {}

        # Apply config-driven parameter transformations
        input_params: Dict[str, Any] = {
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "reasoning_effort": config.reasoning_effort,
        }
        transform = get_param_transformer().transform(
            provider="openai",
            model_name=config.model_name,
            params=input_params,
        )

        if transform.model_kwargs:
            kwargs["model_kwargs"] = {
                **kwargs.get("model_kwargs", {}),
                **transform.model_kwargs,
            }

        if transform.dropped_params:
            logger.info(
                "%s Dropped unsupported params for %s: %s",
                LOG_PREFIX,
                config.model_name,
                ", ".join(transform.dropped_params),
            )

        final_temperature = transform.direct_params.get("temperature")
        final_max_tokens = transform.direct_params.get("max_tokens")

        constructor_params: Dict[str, Any] = {
            "model": config.model_name,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "streaming": ExecutionConfig.enable_streaming(),
            "stream_usage": True,
        }
        if final_temperature is not None:
            constructor_params["temperature"] = final_temperature
        if final_max_tokens is not None:
            constructor_params["max_tokens"] = final_max_tokens
        final_top_p = transform.direct_params.get("top_p")
        if final_top_p is not None:
            constructor_params["top_p"] = final_top_p
        final_reasoning_effort = transform.direct_params.get("reasoning_effort")
        if final_reasoning_effort is not None:
            constructor_params["reasoning_effort"] = final_reasoning_effort

        verify_ssl_raw = config.config.get("verify_ssl", True)
        verify_ssl = (
            verify_ssl_raw in (True, "true", "True", "TRUE")
            if isinstance(verify_ssl_raw, (str, bool))
            else bool(verify_ssl_raw)
        )
        timeout_seconds = float(config.timeout or 60.0)
        constructor_params["http_client"] = httpx.Client(
            verify=verify_ssl, timeout=timeout_seconds
        )
        constructor_params["http_async_client"] = httpx.AsyncClient(
            verify=verify_ssl, timeout=timeout_seconds
        )
        if not verify_ssl:
            logger.warning(
                "%s SSL verification disabled for OpenAI model=%s; use only for development/testing",
                LOG_PREFIX,
                config.model_name,
            )
        # verify_ssl is a deployment-only setting, not a valid ChatOpenAI kwarg
        config.config.pop("verify_ssl", None)

        logger.debug(
            "%s OpenAI constructor params: %s, model_kwargs=%s, extra_kwargs=%s, config=%s",
            LOG_PREFIX,
            constructor_params,
            kwargs.get("model_kwargs"),
            {k: v for k, v in kwargs.items() if k != "model_kwargs"},
            config.config,
        )

        return ChatOpenAI(
            api_key=api_key,
            **constructor_params,
            **kwargs,
            **config.config,
        )

    def validate(self, config: LLMConfig) -> list[str]:
        """Validate OpenAI configuration."""
        errors = []

        api_key = self._get_credential(config, "api_key", "OPENAI_API_KEY")
        if not api_key:
            errors.append(
                "OpenAI requires api_key in credentials or OPENAI_API_KEY environment variable"
            )

        return errors
