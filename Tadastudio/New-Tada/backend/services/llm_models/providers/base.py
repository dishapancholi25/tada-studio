"""Base provider interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.language_models import BaseChatModel

from backend.models.workflow.configs.llm import LLMConfig


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def create(self, config: LLMConfig) -> BaseChatModel:
        """
        Create an LLM instance from configuration.

        Args:
            config: LLM configuration

        Returns:
            BaseChatModel instance

        Raises:
            LLMConfigurationError: If configuration is invalid
            CredentialMissingError: If required credentials are missing
            ManagedIdentityError: If managed identity auth fails (Azure only)
        """
        pass

    @abstractmethod
    def validate(self, config: LLMConfig) -> list[str]:
        """
        Validate LLM configuration.

        Args:
            config: LLM configuration

        Returns:
            List of validation error messages (empty if valid)
        """
        pass

    @staticmethod
    def _get_credential(config: LLMConfig, key: str, env_var: str) -> Optional[str]:
        """
        Get credential from config or environment.

        Args:
            config: LLM configuration
            key: Credential key
            env_var: Environment variable name

        Returns:
            Credential value or None
        """
        import os

        # First try config
        if getattr(config, "credentials", None) and key in config.credentials:
            return config.credentials[key]

        # Then try environment
        return os.getenv(env_var)
