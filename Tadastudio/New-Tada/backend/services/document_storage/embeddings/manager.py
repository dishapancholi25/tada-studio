"""Embedding manager for document storage."""

import logging
import os
from typing import Optional

from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

from ..config import (
    AZURE_API_VERSION,
    EMBEDDING_DIMENSIONS,
    FALLBACK_EMBEDDING_DEPLOYMENTS,
    LOG_PREFIX,
)
from ..exceptions import EmbeddingError

_MODELS_WITH_DIMENSIONS_SUPPORT = {"text-embedding-3-small", "text-embedding-3-large"}


logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages embedding instances for document storage."""

    def __init__(self):
        """Initialize embedding manager."""
        # Lazy import to avoid circular dependency with llm_models.embedding_factory
        from ...llm_models.embedding_factory import EmbeddingFactory

        self.embedding_factory = EmbeddingFactory()
        self.embeddings = None
        self._init_default_embeddings()

    def _init_default_embeddings(self) -> None:
        """Initialize default embeddings from environment variables.

        This provides backward compatibility for existing code that expects
        embeddings to be available without specifying a deployment ID.
        """
        try:
            # Try Azure OpenAI first
            if self._try_azure_init():
                return

            # Fallback to OpenAI
            if self._try_openai_init():
                return

            # Final fallback to mock embeddings
            self._init_mock_embeddings()

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Error initializing embeddings: {e}")
            self.embeddings = None

    def _try_azure_init(self) -> bool:
        """Try to initialize Azure OpenAI embeddings.

        Returns:
            True if successful, False otherwise
        """
        azure_api_key = os.getenv("AZURE_OPENAI_EMBEDDING_KEY") or os.getenv(
            "AZURE_OPENAI_API_KEY"
        )
        azure_endpoint = (
            os.getenv("AZURE_OPENAI_EMBEDDING_HOST")
            or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        ).rstrip("/")

        # Try DefaultAzureCredential if no API key - use token provider for auto-refresh
        azure_token_provider = None
        if not azure_api_key and azure_endpoint:
            azure_token_provider = self._get_azure_token_provider()

        if not ((azure_api_key or azure_token_provider) and azure_endpoint):
            return False

        # Try deployments in order
        deployment_names = []

        # Primary deployment from environment
        primary_deployment = os.getenv("KEY_OPENAI_API_EMBEDDING_MODEL")
        if primary_deployment:
            deployment_names.append(primary_deployment)

        # Add fallbacks
        deployment_names.extend(FALLBACK_EMBEDDING_DEPLOYMENTS)

        for deployment in deployment_names:
            if deployment and self._try_azure_deployment(
                azure_api_key, azure_endpoint, deployment, azure_token_provider
            ):
                return True

        return False

    def _get_azure_token_provider(self):
        """Get Azure AD token provider for auto-refreshing managed identity tokens.

        Returns:
            Token provider callable or None
        """
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            logger.info(
                f"{LOG_PREFIX} Using DefaultAzureCredential token provider (auto-refreshing) for embeddings"
            )
            return token_provider
        except Exception as e:
            logger.debug(
                f"{LOG_PREFIX} Failed to create token provider via DefaultAzureCredential: {e}"
            )
            return None

    def _try_openai_init(self) -> bool:
        """Try to initialize OpenAI embeddings.

        Returns:
            True if successful, False otherwise
        """
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return False

        try:
            self.embeddings = OpenAIEmbeddings(
                api_key=openai_api_key,
                model="text-embedding-3-small",
                dimensions=EMBEDDING_DIMENSIONS,
            )
            # Test the embeddings
            test_result = self.embeddings.embed_query("test")
            if test_result:
                logger.info(
                    f"{LOG_PREFIX} Successfully initialized OpenAI embeddings (dimensions={EMBEDDING_DIMENSIONS})"
                )
                return True
        except Exception as e:
            logger.debug(f"{LOG_PREFIX} Failed to initialize OpenAI embeddings: {e}")

        return False

    def _init_mock_embeddings(self) -> None:
        """Initialize mock embeddings for testing."""
        logger.warning(
            f"{LOG_PREFIX} No embeddings service available - using mock embeddings"
        )
        from ...mock_embeddings import MockEmbeddings

        self.embeddings = MockEmbeddings()
        logger.info(f"{LOG_PREFIX} Initialized mock embeddings for testing")

    def _try_azure_deployment(
        self,
        api_key: Optional[str],
        endpoint: str,
        deployment: str,
        token_provider=None,
    ) -> bool:
        """Try to initialize Azure embeddings with a specific deployment.

        Args:
            api_key: Azure API key (optional if using token_provider)
            endpoint: Azure endpoint
            deployment: Deployment name
            token_provider: Optional token provider for managed identity

        Returns:
            True if successful, False otherwise
        """
        try:
            supports_dims = deployment in _MODELS_WITH_DIMENSIONS_SUPPORT
            extra = {"dimensions": EMBEDDING_DIMENSIONS} if supports_dims else {}

            # Use token provider for managed identity (auto-refresh) or api_key for static auth
            if token_provider:
                self.embeddings = AzureOpenAIEmbeddings(
                    azure_ad_token_provider=token_provider,
                    azure_endpoint=endpoint,
                    azure_deployment=deployment,
                    api_version=AZURE_API_VERSION,
                    **extra,
                )
            else:
                self.embeddings = AzureOpenAIEmbeddings(
                    api_key=api_key,
                    azure_endpoint=endpoint,
                    azure_deployment=deployment,
                    api_version=AZURE_API_VERSION,
                    **extra,
                )

            # Test the embeddings
            test_result = self.embeddings.embed_query("test")
            if test_result:
                auth_method = (
                    "managed_identity_token_provider" if token_provider else "api_key"
                )
                logger.info(
                    f"{LOG_PREFIX} Successfully initialized Azure embeddings "
                    f"with deployment: {deployment} (auth: {auth_method}, dimensions: {EMBEDDING_DIMENSIONS})"
                )
                return True

        except Exception as e:
            logger.debug(
                f"{LOG_PREFIX} Deployment {deployment} initialization failed: {e}"
            )

        return False

    def get_embeddings(self, embedding_deployment_id: Optional[str] = None):
        """Get embeddings instance, either from deployment or default.

        Args:
            embedding_deployment_id: Optional ID of embedding model deployment

        Returns:
            Embeddings instance (AzureOpenAIEmbeddings, OpenAIEmbeddings, or MockEmbeddings)

        Raises:
            EmbeddingError: If specified deployment not found or invalid
        """
        if embedding_deployment_id:
            # Load embeddings from specific deployment
            try:
                logger.info(
                    f"{LOG_PREFIX} Loading embeddings from deployment: {embedding_deployment_id}"
                )
                return self.embedding_factory.create_embedding_instance(
                    embedding_deployment_id
                )
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to load embeddings from deployment "
                    f"{embedding_deployment_id}: {e}"
                )
                raise EmbeddingError(f"Failed to load embeddings deployment: {str(e)}")
        else:
            # Fall back to environment variable configuration
            if self.embeddings is None:
                logger.warning(
                    f"{LOG_PREFIX} No embedding deployment specified and no default embeddings"
                )
                logger.warning(
                    f"{LOG_PREFIX} Consider configuring an embedding model in Settings → LLM Providers"
                )
            return self.embeddings
