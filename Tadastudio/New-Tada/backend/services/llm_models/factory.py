"""Factory for creating and configuring language model instances."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from backend.models.workflow.configs.agent import AgentConfig
from backend.models.workflow.configs.llm import LLMConfig
from ..model_deployment import ModelDeploymentService
from .constants import (
    AVAILABLE_MODELS,
    LOG_PREFIX,
    SUPPORTED_PROVIDERS,
    TOOL_CALLING_PROVIDERS,
    TOOL_CHOICE_PROVIDERS,
)
from .exceptions import ProviderNotFoundError
from .models import LLMInstance
from .providers import (
    AnthropicProvider,
    AzureOpenAIProvider,
    AzureOpenAIPTUProvider,
    GPUConProvider,
    LLMProvider,
    OpenAIProvider,
)
from .validators import validate_llm_config

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from backend.services.graph.manager import GraphManager


logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory class for creating and managing LLM instances."""

    # Provider registry
    _providers: Dict[str, Type[LLMProvider]] = {
        "azure_openai": AzureOpenAIProvider,
        "azure_openai_ptu": AzureOpenAIPTUProvider,
        "gpu_con": GPUConProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    def __init__(
        self,
        graph_manager: Optional["GraphManager"] = None,
        model_service: Optional[ModelDeploymentService] = None,
    ):
        """
        Initialize LLM factory.

        Args:
            graph_manager: Optional graph manager for context
            model_service: Optional model deployment service for config enrichment
        """
        self.graph_manager = graph_manager
        self.model_service = model_service or ModelDeploymentService()

    def create_llm_instance(self, llm_config: LLMConfig) -> LLMInstance:
        """
        Create an LLM instance based on configuration.

        Args:
            llm_config: LLM configuration

        Returns:
            LLMInstance: Configured LLM instance

        Raises:
            ProviderNotFoundError: If provider is not supported
        """
        llm_config = self._enrich_config(llm_config)
        provider = llm_config.provider.lower()

        if provider not in self._providers:
            raise ProviderNotFoundError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
            )

        provider_class = self._providers[provider]
        provider_instance = provider_class()

        logger.info(
            "%s Creating LLM instance (provider=%s, model=%s)",
            LOG_PREFIX,
            provider,
            llm_config.model_name,
        )

        llm = provider_instance.create(llm_config)

        return LLMInstance(
            llm=llm,
            config=llm_config,
            supports_tool_calling=self._supports_tool_calling(provider),
        )

    def create_tool_calling_llm(
        self,
        llm_config: LLMConfig,
        tools: List[BaseTool],
        tool_choice: str = "auto",
    ) -> LLMInstance:
        """
        Create an LLM instance with tools bound for tool calling.

        Args:
            llm_config: LLM configuration
            tools: List of tools to bind to the LLM
            tool_choice: How to select tools - "auto", "any"/"required", or specific tool name

        Returns:
            LLMInstance: LLM instance with tools bound
        """
        llm_instance = self.create_llm_instance(llm_config)

        if not llm_instance.supports_tool_calling:
            logger.warning(
                "%s Provider %s may not support tool calling",
                LOG_PREFIX,
                llm_config.provider,
            )

        if tools and llm_instance.supports_tool_calling:
            try:
                # Prepare bind_tools kwargs
                bind_kwargs = {}

                # Only add tool_choice if it's not "auto" (the default)
                if tool_choice and tool_choice != "auto":
                    # Check if provider supports tool_choice
                    supports_tool_choice = (
                        llm_config.provider.lower() in TOOL_CHOICE_PROVIDERS
                    )

                    if supports_tool_choice:
                        bind_kwargs["tool_choice"] = tool_choice
                        logger.info("%s Using tool_choice: %s", LOG_PREFIX, tool_choice)
                    else:
                        logger.warning(
                            "%s Provider %s does not support tool_choice parameter",
                            LOG_PREFIX,
                            llm_config.provider,
                        )

                # Bind tools to the LLM
                llm_with_tools = llm_instance.llm.bind_tools(tools, **bind_kwargs)
                llm_instance.llm = llm_with_tools
                llm_instance.tools = tools
                logger.info(
                    "%s Bound %d tools to LLM with tool_choice=%s",
                    LOG_PREFIX,
                    len(tools),
                    tool_choice,
                )
            except Exception as e:
                logger.error("%s Failed to bind tools to LLM: %s", LOG_PREFIX, e)
                # Continue without tools

        return llm_instance

    def create_agent_llm(
        self,
        agent_config: AgentConfig,
        available_tools: Optional[List[BaseTool]] = None,
    ) -> LLMInstance:
        """
        Create an LLM instance specifically for an agent.

        Args:
            agent_config: Agent configuration containing LLM config
            available_tools: Tools available to the agent

        Returns:
            LLMInstance: Configured LLM for the agent

        Raises:
            ValueError: If agent configuration is missing LLM config
        """
        if not agent_config.llm_config:
            raise ValueError("Agent configuration missing LLM config")

        # Filter tools based on agent configuration
        agent_tools = self._filter_tools_for_agent(agent_config, available_tools or [])

        # Get tool_choice from agent config
        tool_choice = getattr(agent_config, "tool_choice", "auto")

        # Create LLM with tools
        llm_instance = self.create_tool_calling_llm(
            agent_config.llm_config, agent_tools, tool_choice
        )

        return llm_instance

    def validate_llm_config(self, llm_config: LLMConfig) -> list[str]:
        """
        Validate LLM configuration.

        Args:
            llm_config: LLM configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        return validate_llm_config(llm_config, self._providers)

    def test_llm_connection(self, llm_config: LLMConfig) -> Dict[str, Any]:
        """
        Test LLM connection with a simple query.

        Args:
            llm_config: LLM configuration to test

        Returns:
            Dict with test results
        """
        try:
            model_type = getattr(llm_config, "model_type", "llm")

            # For embedding models, test with embed_query
            if model_type == "embedding":
                return self._test_embedding_connection(llm_config)

            # For LLM models, test with chat completion
            llm_instance = self.create_llm_instance(llm_config)

            # Simple test message
            test_message = [
                HumanMessage(
                    content="Hello! Please respond with 'Connection successful'."
                )
            ]

            response = llm_instance.llm.invoke(test_message)

            return {
                "success": True,
                "response": response.content,
                "provider": llm_config.provider,
                "model": llm_config.model_name,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "provider": llm_config.provider,
                "model": llm_config.model_name,
            }

    def _test_embedding_connection(self, llm_config: LLMConfig) -> Dict[str, Any]:
        """
        Test embedding model connection.

        Args:
            llm_config: LLM configuration for embedding model

        Returns:
            Dict with test results
        """
        try:
            from .embedding_factory import EmbeddingFactory

            # Check if we have a deployment ID
            if not llm_config.model_deployment_id:
                raise ValueError("Embedding test requires a model_deployment_id")

            # Create embedding factory and instance
            embedding_factory = EmbeddingFactory(model_service=self.model_service)
            embeddings = embedding_factory.create_embedding_instance(
                llm_config.model_deployment_id
            )

            # Test with a simple query
            test_text = "This is a test query for embedding model connection."
            result = embeddings.embed_query(test_text)

            # Verify we got a valid embedding vector
            if not isinstance(result, list) or len(result) == 0:
                raise ValueError("Invalid embedding response")

            return {
                "success": True,
                "response": f"Successfully generated embedding vector of dimension {len(result)}",
                "provider": llm_config.provider,
                "model": llm_config.model_name,
                "embedding_dimension": len(result),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "provider": llm_config.provider,
                "model": llm_config.model_name,
            }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """
        Register a new LLM provider.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from LLMProvider)

        Raises:
            TypeError: If provider doesn't inherit from LLMProvider
        """
        if not issubclass(provider_class, LLMProvider):
            raise TypeError("Provider must inherit from LLMProvider")

        cls._providers[name] = provider_class
        logger.info("%s Registered provider: %s", LOG_PREFIX, name)

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())

    @staticmethod
    def get_available_models(provider: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get available models for each provider.

        Args:
            provider: Optional provider filter

        Returns:
            Dict mapping provider to list of model names
        """
        if provider:
            return {provider: AVAILABLE_MODELS.get(provider, [])}

        return AVAILABLE_MODELS.copy()

    def _enrich_config(self, config: LLMConfig) -> LLMConfig:
        """
        Inject deployment metadata/credentials if referenced by ID.

        Args:
            config: Base LLM configuration

        Returns:
            Enriched LLM configuration
        """
        if not getattr(config, "model_deployment_id", None):
            return config

        if not self.model_service:
            raise ValueError("Model deployment service not configured")

        return self.model_service.enrich_llm_config(config)

    @staticmethod
    def _supports_tool_calling(provider: str) -> bool:
        """Check if provider supports tool calling."""
        return provider.lower() in TOOL_CALLING_PROVIDERS

    @staticmethod
    def _filter_tools_for_agent(
        agent_config: AgentConfig, available_tools: List[BaseTool]
    ) -> List[BaseTool]:
        """Filter tools based on agent configuration."""
        if not agent_config.allowed_tools:
            return available_tools

        # Filter tools by name
        filtered_tools = []

        for tool_name in agent_config.allowed_tools:
            matching_tools = [
                tool for tool in available_tools if tool.name == tool_name
            ]
            filtered_tools.extend(matching_tools)

        return filtered_tools
