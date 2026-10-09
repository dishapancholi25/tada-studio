"""Workflow authentication token model."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ....services.database import Base
from ...base import UUIDPrimaryKeyMixin


class WorkflowAuthToken(Base, UUIDPrimaryKeyMixin):
    """Model for storing authentication tokens for published workflows.

    Manages API tokens for accessing published workflows with
    expiration, scopes, and usage tracking.

    Attributes:
        id: Unique token identifier (UUID).
        published_workflow_id: Associated published workflow ID.
        token: Authentication token (unique).
        token_name: Optional friendly name for the token.
        expires_at: Token expiration timestamp (null for no expiration).
        is_active: Whether token is active.
        scopes: Token scopes (JSON).
        last_used: Last usage timestamp.
        usage_count: Total number of uses.
        created_at: Record creation timestamp.
        created_by: User who created the token.
    """

    __tablename__ = "workflow_auth_tokens"

    published_workflow_id = Column(
        String, ForeignKey("published_workflows.id", ondelete="CASCADE"), nullable=False
    )

    # Token details
    token = Column(String, nullable=False, unique=True, index=True)
    token_name = Column(String, nullable=True)

    # Security
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    scopes = Column(JSON, nullable=True)

    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(BigInteger, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=True)

    # Relationships
    published_workflow = relationship("PublishedWorkflow", back_populates="auth_tokens")

    def is_valid(self) -> bool:
        """Check if token is valid (active and not expired).

        Returns:
            True if token is valid, False otherwise.
        """
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
