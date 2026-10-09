"""Factory for creating embedding model instances with managed identity support."""

import logging
import os
from typing import Optional

import httpx
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

from backend.constants import EMBEDDING_DIMENSIONS

from ..model_deployment import ModelDeploymentService

# Only these models support the `dimensions` parameter
_MODELS_WITH_DIMENSIONS_SUPPORT = {"text-embedding-3-small", "text-embedding-3-large"}
from .constants import AZURE_COGNITIVE_SERVICES_SCOPE, LOG_PREFIX
from .exceptions import ManagedIdentityError

logger = logging.getLogger(__name__)


class EmbeddingFactory:
    """Factory for creating embedding instances from model deployments."""

    def __init__(self, model_service: Optional[ModelDeploymentService] = None):
        """Initialize embedding factory."""
        self.model_service = model_service or ModelDeploymentService()

    def create_embedding_instance(self, deployment_id: str):
        """
        Create an embedding instance from a model deployment.

        Args:
            deployment_id: ID of the model deployment

        Returns:
            Embedding instance (AzureOpenAIEmbeddings or OpenAIEmbeddings)

        Raises:
            ValueError: If deployment not found or configuration invalid
        """
        # Get deployment config
        deployment = self.model_service.get_deployment(
            deployment_id, include_credentials=True
        )
        if not deployment:
            raise ValueError(f"Embedding deployment '{deployment_id}' not found")

        if deployment.get("model_type") != "embedding":
            raise ValueError(f"Deployment '{deployment_id}' is not an embedding model")

        if not deployment.get("is_active"):
            raise ValueError(f"Embedding deployment '{deployment_id}' is not active")

        # Convert deployment dict to config structure
        provider = deployment["provider"]
        config_dict = {
            "provider": provider,
            "model_name": deployment["model_name"],
            "credentials": deployment.get("credentials", {}),
            "config": deployment.get("settings", {}),
        }

        # Create embedding based on provider
        if provider == "azure_openai":
            return self._create_azure_openai_embeddings(config_dict)
        elif provider == "azure_openai_ptu":
            return self._create_azure_openai_ptu_embeddings(config_dict)
        elif provider == "openai":
            return self._create_openai_embeddings(config_dict)
        elif provider == "gpu_con":
            return self._create_gpu_con_embeddings(config_dict)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def _create_gpu_con_embeddings(self, config: dict):
        """Create GPU CON embedding instance (OAuth client_credentials, OpenAI-compatible)."""
        from .providers.azure_openai_ptu import AzureOpenAIPTUProvider

        settings = config.get("config", {})
        creds = config.get("credentials", {})

        endpoint = (
            settings.get("endpoint") or settings.get("base_url") or settings.get("api_base")
        )
        if not endpoint:
            raise ValueError("GPU CON embeddings require an endpoint (gateway base URL) in settings")
        endpoint = endpoint.rstrip("/")
        if endpoint.endswith("/embeddings"):
            endpoint = endpoint.rsplit("/embeddings", 1)[0]  # OpenAIEmbeddings appends this itself

        verify_ssl_raw = settings.get("verify_ssl", False)
        verify_ssl = (
            verify_ssl_raw in (True, "true", "True", "TRUE")
            if isinstance(verify_ssl_raw, (str, bool))
            else bool(verify_ssl_raw)
        )

        token = AzureOpenAIPTUProvider.get_cached_token(
            token_url=settings.get("token_url") or creds.get("token_url"),
            client_id=settings.get("client_id") or creds.get("client_id"),
            client_secret=creds.get("client_secret"),
            scope=settings.get("oauth_scope") or settings.get("scope") or "CORP",
            grant_type=settings.get("grant_type") or "client_credentials",
            verify_ssl=verify_ssl,
            deployment=config["model_name"],
        )

        # Optional truncation for different dimension
        dims = settings.get("dimensions")
        extra = {"dimensions": int(dims)} if dims else {}

        logger.info(
            "%s Creating GPU CON embeddings (model=%s, endpoint=%s, dimensions=%s)",
            LOG_PREFIX,
            config["model_name"],
            endpoint,
            dims or "native",
        )

        return OpenAIEmbeddings(
            api_key=token,
            base_url=endpoint,
            model=config["model_name"],
            http_client=httpx.Client(verify=verify_ssl, timeout=60.0),
            http_async_client=httpx.AsyncClient(verify=verify_ssl, timeout=60.0),
            default_headers={
                "ClientId": settings.get("client_id") or creds.get("client_id") or "",
                "X-USER-ID": settings.get("x_user_id") or "TADAUSER",
            },
            check_embedding_ctx_length=False,
            **extra,
        )

    def _create_azure_openai_embeddings(self, config: dict):
        """Create Azure OpenAI embedding instance with managed identity support."""
        settings = config.get("config", {})
        credentials = config.get("credentials", {})

        # Get endpoint and deployment
        endpoint = settings.get("endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = settings.get("deployment_name") or config.get("model_name")
        api_version = settings.get("api_version") or "2024-02-15-preview"
        verify_ssl_raw = settings.get("verify_ssl", True)
        verify_ssl = (
            verify_ssl_raw in (True, "true", "True", "TRUE")
            if isinstance(verify_ssl_raw, (str, bool))
            else bool(verify_ssl_raw)
        )

        if not endpoint:
            raise ValueError("Azure OpenAI embeddings require an endpoint")

        if not deployment:
            raise ValueError("Azure OpenAI embeddings require a deployment name")

        # Get API key with fallback to DefaultAzureCredential
        credentials_api_key = credentials.get("api_key")
        env_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        use_managed_identity = settings.get("use_managed_identity", False)
        managed_identity_client_id = (
            settings.get("managed_identity_client_id")
            or settings.get("azure_managed_identity_client_id")
            or os.getenv("AZURE_MANAGED_IDENTITY_CLIENT_ID")
        )
        key_source = "unknown"
        azure_ad_token_provider = None
        api_key: Optional[str] = None

        if use_managed_identity:
            if credentials_api_key or env_api_key:
                logger.info(
                    "%s use_managed_identity=True; ignoring provided embedding API key (deployment=%s)",
                    LOG_PREFIX,
                    deployment,
                )
            azure_ad_token_provider = self._get_token_provider(
                prefer_managed_identity=True,
                managed_identity_client_id=managed_identity_client_id,
            )
            key_source = "managed_identity"
        else:
            api_key = credentials_api_key or env_api_key
            if api_key:
                key_source = "config" if credentials_api_key else "env"
            else:
                # Try DefaultAzureCredential as fallback
                logger.info(
                    "%s No API key provided for embeddings, attempting DefaultAzureCredential fallback",
                    LOG_PREFIX,
                )
                azure_ad_token_provider = self._get_token_provider(
                    prefer_managed_identity=False,
                    managed_identity_client_id=managed_identity_client_id,
                )
                key_source = "managed_identity_fallback"

        logger.info(
            "%s Creating Azure OpenAI embeddings (deployment=%s, endpoint=%s, api_version=%s, key_source=%s)",
            LOG_PREFIX,
            deployment,
            endpoint,
            api_version,
            key_source,
        )

        model_name = config["model_name"]
        supports_dims = model_name in _MODELS_WITH_DIMENSIONS_SUPPORT
        extra = {"dimensions": EMBEDDING_DIMENSIONS} if supports_dims else {}

        # Use azure_ad_token_provider for managed identity (auto-refreshing tokens)
        # or api_key for static credentials
        if azure_ad_token_provider:
            return AzureOpenAIEmbeddings(
                azure_ad_token_provider=azure_ad_token_provider,
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                model=model_name,
                api_version=api_version,
                http_client=httpx.Client(verify=verify_ssl, timeout=60.0),
                http_async_client=httpx.AsyncClient(verify=verify_ssl, timeout=60.0),
                **extra,
            )
        else:
            return AzureOpenAIEmbeddings(
                api_key=api_key,
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                model=model_name,
                api_version=api_version,
                http_client=httpx.Client(verify=verify_ssl, timeout=60.0),
                http_async_client=httpx.AsyncClient(verify=verify_ssl, timeout=60.0),
                **extra,
            )

    def _create_azure_openai_ptu_embeddings(self, config: dict):
        """Create an Azure OpenAI PTU (gateway) embedding instance.

        Reuses ``AzureOpenAIPTUProvider`` for endpoint/deployment resolution,
        OAuth token acquisition, and gateway header injection — no duplicated
        auth logic.
        """
        from backend.models.workflow.configs.llm import LLMConfig
        from .providers.azure_openai_ptu import AzureOpenAIPTUProvider

        settings = config.get("config", {})
        credentials = config.get("credentials", {})
        model_name = config["model_name"]

        llm_config = LLMConfig(
            provider="azure_openai_ptu",
            model_name=model_name,
            credentials=credentials,
            config=settings,
            timeout=settings.get("timeout", 60),
        )

        provider = AzureOpenAIPTUProvider()
        deployment = provider._get_deployment(llm_config)
        endpoint = provider._get_endpoint(llm_config)
        api_version = provider._get_api_version(llm_config)

        # Reuse the same cached OAuth token + gateway httpx client.
        auth_kwargs = provider._get_auth_params(llm_config, deployment)
        constructor_params: dict = {}
        provider._customize_constructor_params(constructor_params, llm_config)
        # ``streaming`` is not a valid AzureOpenAIEmbeddings kwarg.
        constructor_params.pop("streaming", None)

        logger.info(
            "%s Creating Azure OpenAI PTU embeddings "
            "(deployment=%s, endpoint=%s, api_version=%s)",
            LOG_PREFIX,
            deployment,
            endpoint,
            api_version,
        )

        supports_dims = model_name in _MODELS_WITH_DIMENSIONS_SUPPORT
        extra = {"dimensions": EMBEDDING_DIMENSIONS} if supports_dims else {}

        return AzureOpenAIEmbeddings(
            azure_endpoint=endpoint,
            azure_deployment=deployment,
            model=model_name,
            api_version=api_version,
            **constructor_params,
            **auth_kwargs,
            **extra,
        )

    def _create_openai_embeddings(self, config: dict):
        """Create OpenAI embedding instance."""
        settings = config.get("config", {})
        credentials = config.get("credentials", {})
        model_name = config.get("model_name", "text-embedding-3-small")

        # Get API key
        api_key = credentials.get("api_key") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OpenAI embeddings require an API key")

        verify_ssl_raw = settings.get("verify_ssl", True)
        verify_ssl = (
            verify_ssl_raw in (True, "true", "True", "TRUE")
            if isinstance(verify_ssl_raw, (str, bool))
            else bool(verify_ssl_raw)
        )

        logger.info(
            "%s Creating OpenAI embeddings (model=%s, dimensions=%d)",
            LOG_PREFIX,
            model_name,
            EMBEDDING_DIMENSIONS,
        )

        extra = {"dimensions": EMBEDDING_DIMENSIONS} if model_name in _MODELS_WITH_DIMENSIONS_SUPPORT else {}
        return OpenAIEmbeddings(
            api_key=api_key,
            model=model_name,
            http_client=httpx.Client(verify=verify_ssl, timeout=60.0),
            http_async_client=httpx.AsyncClient(verify=verify_ssl, timeout=60.0),
            **extra,
        )

    def _get_token_provider(
        self,
        *,
        prefer_managed_identity: bool,
        managed_identity_client_id: Optional[str] = None,
    ):
        """
        Get an Azure AD token provider for auto-refreshing managed identity tokens.

        Returns:
            Token provider callable that automatically refreshes tokens

        Raises:
            ManagedIdentityError: If credential initialization fails
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
                "%s Using Azure credential %s for embedding model (auto-refreshing)",
                LOG_PREFIX,
                credential_label,
            )
            return token_provider
        except Exception as e:
            logger.error(
                "%s Failed to create token provider via DefaultAzureCredential for embeddings: %s",
                LOG_PREFIX,
                e,
            )
            raise ManagedIdentityError(
                "Azure OpenAI embeddings configured for managed identity but failed to create token provider. "
                "Ensure you have run 'az login' or have proper managed identity configured."
            ) from e

    def validate_embedding_config(self, config: dict) -> list[str]:
        """
        Validate embedding configuration.

        Args:
            config: Configuration dictionary with provider, model_name, credentials, settings

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        provider = config.get("provider")
        if not provider:
            errors.append("Provider is required")
            return errors

        model_name = config.get("model_name")
        if not model_name:
            errors.append("Model name is required")

        if provider == "azure_openai":
            settings = config.get("settings", {})
            credentials = config.get("credentials", {})

            endpoint = settings.get("endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                errors.append("Azure OpenAI requires an endpoint")

            api_key = credentials.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
            use_managed_identity = settings.get("use_managed_identity", False)

            if not api_key and not use_managed_identity:
                errors.append(
                    "Azure OpenAI requires api_key or use_managed_identity flag"
                )

        elif provider == "azure_openai_ptu":
            settings = config.get("settings", {})
            credentials = config.get("credentials", {})

            if not (
                settings.get("endpoint")
                or settings.get("azure_endpoint")
                or settings.get("base_url")
                or settings.get("api_base")
            ):
                errors.append(
                    "Azure OpenAI PTU requires an endpoint (gateway base URL)"
                )
            if not (settings.get("client_id") or credentials.get("client_id")):
                errors.append("Azure OpenAI PTU requires client_id")
            if not credentials.get("client_secret"):
                errors.append("Azure OpenAI PTU requires client_secret")
            if not (settings.get("token_url") or credentials.get("token_url")):
                errors.append("Azure OpenAI PTU requires token_url")

        elif provider == "openai":
            credentials = config.get("credentials", {})
            api_key = credentials.get("api_key") or os.getenv("OPENAI_API_KEY")

            if not api_key:
                errors.append("OpenAI requires an API key")

        elif provider == "gpu_con":
            settings = config.get("settings", {})
            credentials = config.get("credentials", {})
            if not (settings.get("client_id") or credentials.get("client_id")):
                errors.append("GPU CON requires client_id")
            if not credentials.get("client_secret"):
                errors.append("GPU CON requires client_secret in credentials")
            if not (settings.get("token_url") or credentials.get("token_url")):
                errors.append("GPU CON requires token_url in deployment settings")
            if not (settings.get("endpoint") or settings.get("base_url")):
                errors.append("GPU CON requires an endpoint (gateway base URL) in settings")

        else:
            errors.append(f"Unsupported provider: {provider}")

        return errors
