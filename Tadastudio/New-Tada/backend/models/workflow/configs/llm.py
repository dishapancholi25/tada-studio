"""LLM configuration for agents and conditions.

This module defines the LLMConfig dataclass used to configure
language model connections across different providers.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LLMConfig:
    """Configuration for LLM connections.

    Supports multiple providers including Azure OpenAI, OpenAI, Anthropic,
    and others. Can reference managed model deployments or use direct credentials.

    Attributes:
        provider: LLM provider identifier (e.g., 'azure_openai', 'openai', 'anthropic')
        model_name: Model identifier (e.g., 'gpt-4o-latest', 'claude-3-5-sonnet')
        model_type: Model type ('llm' for chat/completion, 'embedding' for embeddings)
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens in response (None for provider default)
        top_p: Nucleus sampling threshold (0.0 to 1.0, None for provider default)
        reasoning_effort: Reasoning effort level for o-series models ('low', 'medium', 'high')
        api_base: Base URL for API requests
        api_version: API version string (Azure OpenAI)
        deployment_name: Deployment name (Azure OpenAI)
        api_key_env_var: Environment variable containing API key
        base_url_env_var: Environment variable containing base URL
        model_deployment_id: Reference to managed deployment in database
        display_name: Human-readable display name
        credentials: Decrypted credentials (populated at runtime)
        config: Provider-specific configuration options
        additional_params: [Deprecated] Alias for config (backward compatibility)
        supports_function_calling: Whether model supports function calling
        supports_streaming: Whether model supports streaming responses
        timeout: Request timeout in seconds
        organization_id: Organization ID (OpenAI)
        max_retries: Maximum number of retry attempts
    """

    provider: str = "azure_openai"
    model_name: str = "gpt-4o-latest"
    model_type: str = "llm"  # 'llm' or 'embedding'
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    reasoning_effort: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None
    api_key_env_var: str = "AZURE_OPENAI_API_KEY"
    base_url_env_var: str = "AZURE_OPENAI_ENDPOINT"
    model_deployment_id: Optional[str] = None
    display_name: Optional[str] = None
    credentials: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    additional_params: Dict[str, Any] = field(default_factory=dict)
    supports_function_calling: bool = True
    supports_streaming: bool = True
    timeout: int = 120
    organization_id: Optional[str] = None
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation with additional_params aliased to config
        """
        data = asdict(self)
        data["additional_params"] = self.config
        return data

    def __post_init__(self):
        """Initialize and validate configuration after creation."""
        # Ensure dictionaries are well-formed
        if not isinstance(self.credentials, dict):
            self.credentials = {}
        if not isinstance(self.config, dict):
            self.config = {}
        if not isinstance(self.additional_params, dict):
            self.additional_params = {}

        # Merge additional_params into config for backward compatibility
        if self.additional_params and not self.config:
            self.config = dict(self.additional_params)
        elif self.additional_params:
            merged = dict(self.additional_params)
            merged.update(self.config)
            self.config = merged

        # Keep legacy field pointing to current config for serialization compatibility
        self.additional_params = self.config

        # Clamp top_p to valid range [0, 1] — values like 10 cause API errors
        if self.top_p is not None:
            self.top_p = max(0.0, min(1.0, float(self.top_p)))

        # Ensure env var fields are never None — os.getenv(None) raises TypeError.
        # This can happen when a serialized config has explicit null values.
        if not self.api_key_env_var:
            self.api_key_env_var = "AZURE_OPENAI_API_KEY"
        if not self.base_url_env_var:
            self.base_url_env_var = "AZURE_OPENAI_ENDPOINT"

        # Apply provider-specific defaults when not using model_deployment_id
        # This ensures validation requirements are met for each provider
        if not self.model_deployment_id:
            self._apply_provider_defaults()

    def _apply_provider_defaults(self):
        """Apply provider-specific defaults for validation requirements.

        When not using a model_deployment_id, each provider has specific
        validation requirements. This method ensures those are met.

        Validation requirements from models/workflow/validation/llm_validator.py:
        - All providers: api_key_env_var required
        - Azure OpenAI: deployment_name and api_version required
        """
        provider_lower = self.provider.lower()

        if provider_lower == "azure_openai":
            # Azure OpenAI validation requires deployment_name and api_version
            if not self.deployment_name:
                self.deployment_name = self.model_name
            if not self.api_version:
                self.api_version = "2024-02-01"
            if (
                not self.api_key_env_var
                or self.api_key_env_var == "AZURE_OPENAI_API_KEY"
            ):
                # Keep Azure default if already set, otherwise set it
                self.api_key_env_var = "AZURE_OPENAI_API_KEY"
            if not self.base_url_env_var:
                self.base_url_env_var = "AZURE_OPENAI_ENDPOINT"

        elif provider_lower == "openai":
            # OpenAI doesn't need deployment_name or api_version
            if (
                not self.api_key_env_var
                or self.api_key_env_var == "AZURE_OPENAI_API_KEY"
            ):
                # Override Azure default with OpenAI default
                self.api_key_env_var = "OPENAI_API_KEY"
            # base_url_env_var is optional for OpenAI

        elif provider_lower == "anthropic":
            # Anthropic doesn't need deployment_name or api_version
            if (
                not self.api_key_env_var
                or self.api_key_env_var == "AZURE_OPENAI_API_KEY"
            ):
                # Override Azure default with Anthropic default
                self.api_key_env_var = "ANTHROPIC_API_KEY"
            # base_url_env_var is optional for Anthropic
