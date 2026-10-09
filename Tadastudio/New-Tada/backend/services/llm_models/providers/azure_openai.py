"""Azure OpenAI provider implementation."""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI

from backend.models.workflow.configs.llm import LLMConfig
from backend.services.config.execution import ExecutionConfig
from ..constants import AZURE_COGNITIVE_SERVICES_SCOPE, LOG_PREFIX
from ..exceptions import CredentialMissingError, ManagedIdentityError
from ..param_transformer import get_param_transformer
from .base import LLMProvider

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """Provider for Azure OpenAI models with managed identity support."""

    # Chat model class used for construction. Subclasses may override to
    # supply a customised client (e.g. a non-streaming gateway variant).
    _chat_model_cls: type[AzureChatOpenAI] = AzureChatOpenAI

    def create(self, config: LLMConfig) -> BaseChatModel:
        """Create Azure OpenAI LLM instance."""
        endpoint = self._get_endpoint(config)
        deployment = self._get_deployment(config)
        api_version = self._get_api_version(config)
        key_source = self._describe_key_source(config)
        auth_kwargs = self._get_auth_params(config, deployment)

        logger.info(
            "%s Creating Azure OpenAI client (deployment=%s, endpoint=%s, api_version=%s, key_source=%s)",
            LOG_PREFIX,
            deployment,
            endpoint,
            api_version,
            key_source,
        )

        extra_kwargs: Dict[str, Any] = {}

        # Apply config-driven parameter transformations (includes api_version rules)
        input_params: Dict[str, Any] = {
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "reasoning_effort": config.reasoning_effort,
        }
        transform = get_param_transformer().transform(
            provider="azure_openai",
            model_name=config.model_name,
            params=input_params,
            api_version=api_version,
        )

        if transform.model_kwargs:
            extra_kwargs["model_kwargs"] = {
                **extra_kwargs.get("model_kwargs", {}),
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
            "azure_endpoint": endpoint,
            "api_version": api_version,
            "azure_deployment": deployment,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "streaming": ExecutionConfig.enable_streaming(),
            "stream_usage": True,
        }
        # Distinct from azure_deployment: this is the true underlying model
        # name (e.g. "gpt-4.1"), used by LangChain/OpenInference for tracing
        # and token counting. Without it, Langfuse shows model/model_name as
        # null and falls back to the deployment name instead of the model.
        if config.model_name:
            constructor_params["model"] = config.model_name
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
                "%s SSL verification disabled for Azure OpenAI deployment=%s; "
                "use only for development/testing",
                LOG_PREFIX,
                deployment,
            )

        logger.debug(
            "%s Azure OpenAI constructor params: %s, model_kwargs=%s, extra_kwargs=%s",
            LOG_PREFIX,
            {k: v for k, v in constructor_params.items() if k != "azure_endpoint"},
            extra_kwargs.get("model_kwargs"),
            {k: v for k, v in extra_kwargs.items() if k != "model_kwargs"},
        )

        # Allow subclasses to adjust constructor params (e.g. force
        # non-streaming, inject a custom http client) before building.
        self._customize_constructor_params(constructor_params, config)

        return self._chat_model_cls(
            **constructor_params,
            **extra_kwargs,
            **auth_kwargs,
        )

    def _customize_constructor_params(
        self, constructor_params: Dict[str, Any], config: LLMConfig
    ) -> None:
        """Hook for subclasses to mutate constructor params in place.

        The base implementation is a no-op.
        """

    def validate(self, config: LLMConfig) -> list[str]:
        """Validate Azure OpenAI configuration."""
        errors = []

        # Check endpoint
        endpoint = self._get_endpoint(config)
        if not endpoint:
            errors.append(
                "Azure OpenAI requires endpoint in credentials or AZURE_OPENAI_ENDPOINT environment variable"
            )

        # Check API key or managed identity
        api_key = self._get_credential(config, "api_key", "AZURE_OPENAI_API_KEY")
        use_managed_identity = config.config.get("use_managed_identity", False)

        if not api_key and not use_managed_identity:
            errors.append(
                "Azure OpenAI requires api_key in credentials or AZURE_OPENAI_API_KEY environment variable "
                "(or enable use_managed_identity for Azure DefaultAzureCredential)"
            )

        return errors

    def _get_endpoint(self, config: LLMConfig) -> Optional[str]:
        """Get Azure endpoint from config or environment."""
        base_url_env = config.base_url_env_var or "AZURE_OPENAI_ENDPOINT"
        endpoint = (
            config.config.get("endpoint")
            or config.config.get("azure_endpoint")
            or config.config.get("base_url")
            or os.getenv(base_url_env)
        )

        if not endpoint:
            raise CredentialMissingError("Azure OpenAI requires an endpoint")

        return endpoint

    def _get_deployment(self, config: LLMConfig) -> str:
        """Get Azure deployment name from config or environment."""
        deployment = (
            config.deployment_name
            or config.config.get("deployment_name")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        )
        return deployment or config.model_name

    def _get_api_version(self, config: LLMConfig) -> str:
        """Get Azure API version from config or environment."""
        api_version = (
            config.api_version
            or config.config.get("api_version")
            or os.getenv("AZURE_OPENAI_API_VERSION")
        )
        return api_version or "2024-02-15-preview"

    def _describe_key_source(self, config: LLMConfig) -> str:
        """Return a non-sensitive label describing which auth source will be used.

        This is intentionally separate from _get_auth_params so that the
        label never shares a data-flow path with actual credentials.
        """
        use_managed_identity = config.config.get("use_managed_identity", False)
        if use_managed_identity:
            return "managed_identity"

        has_credentials_key = (
            bool(getattr(config, "credentials", None))
            and "api_key" in config.credentials
        )
        if has_credentials_key:
            return "config"

        api_key_env = config.api_key_env_var or "AZURE_OPENAI_API_KEY"
        if os.getenv(api_key_env):
            return f"env:{api_key_env}"

        return "managed_identity_fallback"

    def _get_auth_params(self, config: LLMConfig, deployment: str) -> Dict[str, Any]:
        """
        Resolve authentication kwargs for AzureChatOpenAI.

        Returns:
            Auth kwargs dict for AzureChatOpenAI constructor.
        """
        credentials_api_key = (
            config.credentials.get("api_key")
            if getattr(config, "credentials", None)
            else None
        )
        api_key_env = config.api_key_env_var or "AZURE_OPENAI_API_KEY"
        env_api_key = os.getenv(api_key_env)
        use_managed_identity = config.config.get("use_managed_identity", False)
        managed_identity_client_id = (
            config.config.get("managed_identity_client_id")
            or config.config.get("azure_managed_identity_client_id")
            or os.getenv("AZURE_MANAGED_IDENTITY_CLIENT_ID")
        )

        if use_managed_identity:
            if credentials_api_key or env_api_key:
                logger.info(
                    "%s use_managed_identity=True; ignoring provided API key for deployment %s",
                    LOG_PREFIX,
                    deployment,
                )
            token_provider = self._get_token_provider(
                deployment,
                prefer_managed_identity=True,
                managed_identity_client_id=managed_identity_client_id,
            )
            return {"azure_ad_token_provider": token_provider}

        if credentials_api_key:
            return {"api_key": credentials_api_key}

        if env_api_key:
            return {"api_key": env_api_key}

        # Fallback to DefaultAzureCredential if no API key provided
        logger.info(
            "%s No API key provided for LLM, attempting DefaultAzureCredential fallback",
            LOG_PREFIX,
        )
        token_provider = self._get_token_provider(
            deployment,
            prefer_managed_identity=False,
            managed_identity_client_id=managed_identity_client_id,
        )
        return {"azure_ad_token_provider": token_provider}

    def _get_token_provider(
        self,
        deployment: Optional[str],
        *,
        prefer_managed_identity: bool,
        managed_identity_client_id: Optional[str] = None,
    ) -> Any:
        """
        Acquire an Azure AD token provider via DefaultAzureCredential.

        Args:
            deployment: Deployment name for logging

        Returns:
            Callable token provider for azure_ad_token_provider

        Raises:
            ManagedIdentityError: If token acquisition fails
        """
        try:
            from azure.identity import (
                DefaultAzureCredential,
                ManagedIdentityCredential,
                get_bearer_token_provider,
            )

            if prefer_managed_identity:
                credential = ManagedIdentityCredential(
                    client_id=managed_identity_client_id
                )
            else:
                credential = DefaultAzureCredential(
                    managed_identity_client_id=managed_identity_client_id,
                    exclude_environment_credential=False,
                )
            credential_label = credential.__class__.__name__
            token_provider = get_bearer_token_provider(
                credential, AZURE_COGNITIVE_SERVICES_SCOPE
            )
            logger.info(
                "%s Using Azure credential %s for LLM (deployment=%s)",
                LOG_PREFIX,
                credential_label,
                deployment,
            )
            return token_provider
        except Exception as e:
            logger.error(
                "%s Failed to acquire token provider via DefaultAzureCredential: %s",
                LOG_PREFIX,
                e,
            )
            raise ManagedIdentityError(
                "Azure OpenAI configured for managed identity but failed to acquire token. "
                "Ensure the application identity has access to the Azure OpenAI resource."
            ) from e
