"""Model deployment configuration."""

from sqlalchemy import JSON, Boolean, Column, Float, String, Text

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ModelDeployment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing configured LLM deployments.

    Manages LLM provider configurations including credentials, settings,
    and operational flags for different model deployments.

    Attributes:
        id: Unique deployment identifier (UUID).
        name: Unique deployment name.
        description: Deployment description.
        provider: LLM provider (openai, anthropic, azure, etc.).
        model_name: Model identifier within the provider.
        model_type: Type of model ('llm' or 'embedding').
        display_name: Human-readable model name.
        settings: Provider-specific non-sensitive settings (JSON).
        encrypted_credentials: Encrypted credentials (JSON).
        input_cost_per_million: USD cost per 1M input tokens (LLM only).
        output_cost_per_million: USD cost per 1M output tokens (LLM only).
        is_default: Whether this is the default deployment.
        is_active: Whether this deployment is active.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "model_deployments"

    # Display metadata
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Provider configuration
    provider = Column(String(50), nullable=False)
    model_name = Column(String(255), nullable=False)
    model_type = Column(String(20), nullable=False, default="llm", server_default="llm")
    display_name = Column(String(255), nullable=True)
    settings = Column(JSON, nullable=True)

    # Sensitive credentials (encrypted per key)
    encrypted_credentials = Column(JSON, nullable=True)

    # Token pricing (USD per 1M tokens, LLM deployments only)
    input_cost_per_million = Column(Float, nullable=True)
    output_cost_per_million = Column(Float, nullable=True)

    # Operational flags
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
