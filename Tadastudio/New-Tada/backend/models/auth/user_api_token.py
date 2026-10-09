"""User API token model for Personal Access Tokens (PATs).

This module provides database models for user-scoped API tokens that allow
users to authenticate HTTP execution requests with their own credentials.
Similar to GitHub Personal Access Tokens or GitLab Personal Access Tokens.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class UserAPIToken(Base, UUIDPrimaryKeyMixin):
    """User-scoped API token for authenticating HTTP execution requests.

    Personal Access Tokens (PATs) allow users to generate their own API tokens
    that inherit their workflow permissions. This is more secure and flexible
    than workflow-scoped tokens as they:
    - Are scoped to the user's accessible workflows
    - Can be revoked individually without affecting other integrations
    - Provide audit trails of who is using which tokens
    - Support expiration and rotation policies

    Tokens are stored hashed for security and only shown in plaintext once
    during creation (similar to GitHub PATs).

    Attributes:
        id: Unique token identifier (UUID).
        user_id: User who owns this token (email).
        token_hash: Bcrypt hash of the token (not stored in plaintext).
        token_prefix: First 8 characters for identification (e.g., "na_AbCd").
        token_name: User-friendly name for the token.
        description: Optional description of token purpose.
        scopes: Token scopes (JSON array) - e.g., ["workflow:*", "workflow:my-workflow"].
        expires_at: Token expiration timestamp (null for no expiration).
        is_active: Whether token is active.
        last_used_at: Last usage timestamp.
        last_used_ip: Last client IP that used this token.
        usage_count: Total number of uses.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
        created_by_user_id: User who created the token (usually same as user_id).
    """

    __tablename__ = "user_api_tokens"

    # Owner
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Token details
    token_hash = Column(String, nullable=False, index=True)
    token_prefix = Column(
        String(12), nullable=False, index=True
    )  # "na_AbCdEfGh" for display
    token_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Access control
    scopes = Column(
        JSON, nullable=False, default=list
    )  # ["workflow:*"] or ["workflow:specific-name"]
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String, nullable=True)
    usage_count = Column(BigInteger, default=0, nullable=False)

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_user_id = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_tokens")

    def is_valid(self) -> bool:
        """Check if token is valid (active and not expired).

        Returns:
            True if token is valid, False otherwise.
        """
        if not self.is_active:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def has_scope(self, required_scope: str) -> bool:
        """Check if token has a specific scope.

        Delegates to the scope_enforcer helper so wildcard expansion and
        ``api:*`` super-scope logic live in one place.

        Args:
            required_scope: Scope to check (e.g., "workflow:my-workflow:execute")

        Returns:
            True if token has the required scope, False otherwise.

        Example:
            >>> token.scopes = ["workflow:*:execute"]
            >>> token.has_scope("workflow:my-workflow:execute")  # True
            >>> token.scopes = ["workflow:specific:execute"]
            >>> token.has_scope("workflow:other:execute")  # False
        """
        from backend.services.auth.scope_enforcer import _scopes_satisfy

        return _scopes_satisfy(self.scopes or [], required_scope)

    def update_usage(self, client_ip: str = None) -> None:
        """Update token usage statistics.

        Args:
            client_ip: Client IP address that used the token
        """
        self.last_used_at = datetime.now(timezone.utc)
        self.usage_count += 1
        if client_ip:
            self.last_used_ip = client_ip
