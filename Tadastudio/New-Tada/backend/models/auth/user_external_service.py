"""User external service credentials model.

This module provides database models for storing user-specific external service
API keys and configurations, such as Tavily API keys for web search.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin
from ..configuration.system_external_service import ExternalServiceAuthType


class McpVisibility(enum.Enum):
    """MCP server visibility options."""

    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"


class UserExternalService(Base, UUIDPrimaryKeyMixin):
    """User-specific external service credentials and settings.

    Stores encrypted credentials and configuration for external services
    like Tavily web search. Each user can have one configuration per service.

    Attributes:
        id: Unique identifier (UUID).
        user_id: User who owns this configuration.
        service_name: Name of the external service (e.g., 'tavily', 'mcp_server_*').
        encrypted_api_key: Encrypted credentials or secrets using CredentialEncryption.
                          This field can store a single API key or a JSON-encoded structure
                          containing multiple credentials (e.g., for MCP servers).
        settings: Additional service-specific settings (JSON).
        is_active: Whether this service configuration is active.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
        visibility: Visibility of MCP server (private or public).
        is_template: Whether this server was cloned from another server.
        original_server_id: ID of the original server if this is a clone.
        clone_count: Number of times this server has been cloned.
        shared_at: Timestamp when server was made public.
    """

    __tablename__ = "user_external_services"

    # Owner
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Service identification
    service_name = Column(String(50), nullable=False)
    display_name = Column(String(255), nullable=True)

    # Connection details (non-sensitive)
    service_url = Column(Text, nullable=True)
    auth_type = Column(
        SQLEnum(
            ExternalServiceAuthType,
            name="external_service_auth_type",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ExternalServiceAuthType.API_KEY_HEADER,
        server_default=ExternalServiceAuthType.API_KEY_HEADER.value,
    )

    # Credentials (encrypted)
    encrypted_api_key = Column(String, nullable=False)
    encrypted_credentials = Column(JSON, nullable=True)

    # Additional settings
    settings = Column(JSON, nullable=False, default=dict, server_default="{}")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Visibility and sharing fields (for MCP servers)
    visibility = Column(
        SQLEnum(McpVisibility, name="mcp_visibility", create_type=False),
        nullable=False,
        default=McpVisibility.PRIVATE,
        server_default="PRIVATE",
    )
    shared_with_group_ids = Column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    is_template = Column(Boolean, default=False, nullable=False, server_default="false")
    original_server_id = Column(
        String,  # UUID as string to match existing id type
        ForeignKey("user_external_services.id", ondelete="SET NULL"),
        nullable=True,
    )
    clone_count = Column(Integer, default=0, nullable=False, server_default="0")
    shared_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="external_services")
    original_server = relationship(
        "UserExternalService",
        remote_side="UserExternalService.id",
        foreign_keys=[original_server_id],
        back_populates="clones",
    )
    clones = relationship(
        "UserExternalService",
        foreign_keys="UserExternalService.original_server_id",
        back_populates="original_server",
    )

    # Constraints
    __table_args__ = (
        Index(
            "idx_user_external_services_user_service",
            "user_id",
            "service_name",
            unique=True,
        ),
        Index("idx_user_external_services_visibility", "visibility", "is_active"),
        Index(
            "idx_user_external_services_original",
            "original_server_id",
            postgresql_where=Column("original_server_id").isnot(None),
        ),
    )
