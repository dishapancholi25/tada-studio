"""Custom exceptions for LLM models service."""


class LLMConfigurationError(Exception):
    """Raised when LLM configuration is invalid."""

    pass


class ProviderNotFoundError(LLMConfigurationError):
    """Raised when requested provider is not found."""

    pass


class ManagedIdentityError(LLMConfigurationError):
    """Raised when Azure Managed Identity authentication fails."""

    pass


class CredentialMissingError(LLMConfigurationError):
    """Raised when required credentials are missing."""

    pass


class ValidationError(LLMConfigurationError):
    """Raised when validation fails."""

    pass
