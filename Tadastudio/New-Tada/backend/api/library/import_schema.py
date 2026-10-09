"""Schema definitions for importing agent configurations.

This module defines Pydantic models for validating agent import JSON,
supporting A2A-inspired format with Agentic Studio extensions.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Whitelist of allowed tools
# TEMPORARILY COMMENTED: file_reader disabled due to ISG security audit
# Will be re-enabled after fixes are implemented
ALLOWED_TOOLS = [
    "web_search",
    # "file_reader",  # Temporarily disabled
    "file_writer",
    "document_search",
    "database_query",
    "http_request",
    "mcp_server",
    "email_send",
]

# Maximum lengths for text fields to prevent abuse
MAX_PROMPT_LENGTH = 50000  # 50K characters
MAX_INSTRUCTIONS_LENGTH = 10000  # 10K characters


class ImportLLMConfig(BaseModel):
    """LLM configuration for imported agents."""

    provider: str = Field(
        default="azure_openai",
        description="LLM provider (azure_openai, openai, anthropic, ollama, etc.)",
    )
    model_name: str = Field(default="gpt-4o-latest", description="Model identifier")
    temperature: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0, though some providers may have different ranges)",
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Maximum tokens in response"
    )
    api_key_env_var: Optional[str] = Field(
        default=None, description="Environment variable for API key"
    )
    base_url_env_var: Optional[str] = Field(
        default=None, description="Environment variable for base URL"
    )
    api_base: Optional[str] = Field(default=None, description="API base URL")
    api_version: Optional[str] = Field(default=None, description="API version")
    deployment_name: Optional[str] = Field(
        default=None, description="Deployment name (Azure)"
    )
    timeout: Optional[int] = Field(
        default=120, ge=1, description="Request timeout in seconds"
    )
    max_retries: Optional[int] = Field(
        default=3, ge=0, description="Maximum retry attempts"
    )

    @field_validator("api_key_env_var")
    @classmethod
    def validate_api_key_env_var(cls, v: Optional[str]) -> Optional[str]:
        """Validate API key environment variable name."""
        if v is None:
            return v
        # Only allow alphanumeric and underscore, must start with letter or underscore
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            raise ValueError(
                "api_key_env_var must be a valid environment variable name "
                "(alphanumeric and underscore, starting with letter or underscore)"
            )
        # Maximum reasonable length for env var name
        if len(v) > 100:
            raise ValueError("api_key_env_var too long (max 100 characters)")
        return v

    @field_validator("base_url_env_var")
    @classmethod
    def validate_base_url_env_var(cls, v: Optional[str]) -> Optional[str]:
        """Validate base URL environment variable name."""
        if v is None:
            return v
        # Only allow alphanumeric and underscore, must start with letter or underscore
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            raise ValueError(
                "base_url_env_var must be a valid environment variable name "
                "(alphanumeric and underscore, starting with letter or underscore)"
            )
        # Maximum reasonable length for env var name
        if len(v) > 100:
            raise ValueError("base_url_env_var too long (max 100 characters)")
        return v


class ImportAgentConfig(BaseModel):
    """Agent configuration for imported agents."""

    agent_type: str = Field(
        default="conversational",
        description="Agent type (conversational, react, plan_and_execute)",
    )
    max_iterations: int = Field(
        default=10, ge=1, le=100, description="Maximum reasoning iterations"
    )
    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="Override temperature"
    )
    tools: List[str] = Field(default_factory=list, description="List of tool names")
    memory_enabled: bool = Field(
        default=False, description="Enable conversation memory"
    )
    memory_window_size: int = Field(
        default=10, ge=1, description="Recent messages in context"
    )
    memory_strategy: str = Field(
        default="thread_scoped",
        description="Memory scope (thread_scoped, agent_scoped, cross_execution)",
    )
    custom_instructions: str = Field(
        default="",
        description="Additional agent instructions",
        max_length=MAX_INSTRUCTIONS_LENGTH,
    )
    structured_outputs: List[Dict[str, Any]] = Field(
        default_factory=list, description="Structured output schemas"
    )

    # Document search configuration
    document_search_enabled: bool = Field(
        default=False, description="Enable document search"
    )
    document_collections: List[str] = Field(
        default_factory=list, description="Collections to search"
    )
    document_ids: List[str] = Field(
        default_factory=list, description="Specific documents to search"
    )
    search_k: int = Field(
        default=3, ge=1, description="Number of documents to retrieve"
    )
    search_type: str = Field(
        default="similarity",
        description="Search algorithm (similarity, mmr, similarity_score_threshold)",
    )
    citation_format: str = Field(
        default="structured",
        description="Citation style (inline, footnote, none, structured)",
    )

    # Orchestration configuration
    is_orchestrator: bool = Field(
        default=False, description="Whether this agent orchestrates others"
    )
    orchestrator_mode: str = Field(
        default="supervisor",
        description="Orchestration pattern (supervisor, hierarchical, collaborative)",
    )
    delegation_strategy: str = Field(
        default="dynamic",
        description="Delegation approach (dynamic, sequential, parallel)",
    )
    delegated_agents: List[str] = Field(
        default_factory=list, description="Agent node IDs for delegation"
    )

    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v: str) -> str:
        """Validate agent type."""
        valid_types = ["conversational", "react", "plan_and_execute"]
        if v not in valid_types:
            raise ValueError(f"agent_type must be one of {valid_types}, got '{v}'")
        return v

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v: List[str]) -> List[str]:
        """Validate tools against whitelist."""
        invalid_tools = [tool for tool in v if tool not in ALLOWED_TOOLS]
        if invalid_tools:
            raise ValueError(
                f"Invalid tools: {invalid_tools}. Allowed tools: {ALLOWED_TOOLS}"
            )
        return v

    @field_validator("custom_instructions")
    @classmethod
    def validate_custom_instructions(cls, v: str) -> str:
        """Sanitize custom instructions."""
        # Remove any potential script tags or dangerous content
        if "<script" in v.lower() or "javascript:" in v.lower():
            raise ValueError(
                "custom_instructions contains potentially dangerous content"
            )
        return v.strip()

    @field_validator("memory_strategy")
    @classmethod
    def validate_memory_strategy(cls, v: str) -> str:
        """Validate memory strategy."""
        valid_strategies = ["thread_scoped", "agent_scoped", "cross_execution"]
        if v not in valid_strategies:
            raise ValueError(
                f"memory_strategy must be one of {valid_strategies}, got '{v}'"
            )
        return v

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """Validate search type."""
        valid_types = ["similarity", "mmr", "similarity_score_threshold"]
        if v not in valid_types:
            raise ValueError(f"search_type must be one of {valid_types}, got '{v}'")
        return v

    @field_validator("citation_format")
    @classmethod
    def validate_citation_format(cls, v: str) -> str:
        """Validate citation format."""
        valid_formats = ["inline", "footnote", "none", "structured"]
        if v not in valid_formats:
            raise ValueError(
                f"citation_format must be one of {valid_formats}, got '{v}'"
            )
        return v

    @field_validator("orchestrator_mode")
    @classmethod
    def validate_orchestrator_mode(cls, v: str) -> str:
        """Validate orchestrator mode."""
        valid_modes = ["supervisor", "hierarchical", "collaborative"]
        if v not in valid_modes:
            raise ValueError(
                f"orchestrator_mode must be one of {valid_modes}, got '{v}'"
            )
        return v

    @field_validator("delegation_strategy")
    @classmethod
    def validate_delegation_strategy(cls, v: str) -> str:
        """Validate delegation strategy."""
        valid_strategies = ["dynamic", "sequential", "parallel"]
        if v not in valid_strategies:
            raise ValueError(
                f"delegation_strategy must be one of {valid_strategies}, got '{v}'"
            )
        return v


class ImportAgentMetadata(BaseModel):
    """Metadata for imported agents (library categorization)."""

    category: List[str] = Field(
        default_factory=list,
        description="Categories (e.g., Customer Service, Research)",
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for search and filtering"
    )
    complexity: Optional[str] = Field(
        default=None,
        description="Complexity level (beginner, intermediate, advanced)",
    )
    icon_color: Optional[str] = Field(
        default=None,
        description="Icon color (cyan, purple, orange, green, pink, blue)",
    )
    version: Optional[str] = Field(default=None, description="Version identifier")
    author: Optional[str] = Field(default=None, description="Agent author/creator")

    @field_validator("complexity")
    @classmethod
    def validate_complexity(cls, v: Optional[str]) -> Optional[str]:
        """Validate complexity level."""
        if v is None:
            return v
        valid_levels = ["beginner", "intermediate", "advanced"]
        if v not in valid_levels:
            raise ValueError(f"complexity must be one of {valid_levels}, got '{v}'")
        return v

    @field_validator("icon_color")
    @classmethod
    def validate_icon_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate icon color."""
        if v is None:
            return v
        valid_colors = ["cyan", "purple", "orange", "green", "pink", "blue"]
        if v not in valid_colors:
            raise ValueError(f"icon_color must be one of {valid_colors}, got '{v}'")
        return v


class ImportAgentRequest(BaseModel):
    """Request model for importing an agent from JSON.

    This schema is A2A-inspired with Agentic Studio extensions.
    """

    # Required core fields
    name: str = Field(..., min_length=1, description="Agent display name")
    description: str = Field(..., min_length=1, description="Agent description")
    system_prompt: str = Field(
        ...,
        min_length=1,
        max_length=MAX_PROMPT_LENGTH,
        description="System instructions for the agent",
    )

    # Optional configuration
    llm_config: Optional[ImportLLMConfig] = Field(
        default=None, description="LLM configuration"
    )
    agent_config: Optional[ImportAgentConfig] = Field(
        default=None, description="Agent behavior configuration"
    )
    metadata: Optional[ImportAgentMetadata] = Field(
        default=None, description="Library metadata"
    )

    # Legacy/compatibility fields
    version: Optional[str] = Field(
        default=None, description="Agent version (alternative to metadata.version)"
    )
    tools: Optional[List[str]] = Field(
        default=None,
        description="Tools list (alternative to agent_config.tools)",
    )

    def get_effective_metadata(self) -> ImportAgentMetadata:
        """Get effective metadata, merging top-level fields if needed."""
        if self.metadata:
            return self.metadata
        return ImportAgentMetadata()

    def get_effective_agent_config(self) -> ImportAgentConfig:
        """Get effective agent config, merging top-level fields if needed."""
        config = self.agent_config or ImportAgentConfig()
        # Merge top-level tools if specified
        if self.tools and not config.tools:
            config.tools = self.tools
        return config

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name."""
        if len(v.strip()) == 0:
            raise ValueError("name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description."""
        if len(v.strip()) == 0:
            raise ValueError("description cannot be empty or whitespace only")
        return v.strip()

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        """Validate and sanitize system prompt."""
        if len(v.strip()) == 0:
            raise ValueError("system_prompt cannot be empty or whitespace only")
        # Check for potentially dangerous content
        if "<script" in v.lower() or "javascript:" in v.lower():
            raise ValueError("system_prompt contains potentially dangerous content")
        return v.strip()
