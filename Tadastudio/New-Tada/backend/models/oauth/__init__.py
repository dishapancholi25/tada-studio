"""OAuth models for MCP provider authentication.

This module contains models for storing OAuth client registrations,
tokens, and state for providers like Notion MCP that require
Dynamic Client Registration (RFC 7591).
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from ..base import TimestampMixin, UUIDPrimaryKeyMixin
from ...services.database import Base


class OAuthClientRegistration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Dynamic OAuth client registration per user/provider.

    Stores the client_id and other metadata obtained from the OAuth
    provider's dynamic client registration endpoint.

    Attributes:
        id: UUID primary key.
        user_id: Foreign key to users table (email from oauth2proxy).
        provider: OAuth provider name (e.g., 'notion').
        client_id: OAuth client ID from provider.
        client_secret: Optional client secret (some providers don't require).
        registration_access_token: Token for managing the registration.
        metadata_: Additional registration metadata (JSON).
        created_at: Timestamp of record creation.
        updated_at: Timestamp of last update.
    """

    __tablename__ = "oauth_client_registrations"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False, default="notion")
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=True)
    registration_access_token = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    # Relationship
    user = relationship("User", backref="oauth_client_registrations")

    def __repr__(self) -> str:
        return f"<OAuthClientRegistration(user_id={self.user_id}, provider={self.provider})>"


class OAuthToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """OAuth access/refresh tokens per user/provider.

    Stores the access token, refresh token, and expiry information
    for authenticating with the OAuth provider's APIs.

    Attributes:
        id: UUID primary key.
        user_id: Foreign key to users table (email from oauth2proxy).
        provider: OAuth provider name (e.g., 'notion').
        client_id: OAuth client ID (for token refresh).
        access_token: The access token for API calls.
        refresh_token: Optional refresh token for obtaining new access tokens.
        expires_at: When the access token expires.
        scope: OAuth scope granted.
        created_at: Timestamp of record creation.
        updated_at: Timestamp of last update.
    """

    __tablename__ = "oauth_tokens"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False, default="notion")
    client_id = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String, nullable=True)

    # Relationship
    user = relationship("User", backref="oauth_tokens")

    def __repr__(self) -> str:
        return f"<OAuthToken(user_id={self.user_id}, provider={self.provider})>"

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired or will expire within buffer.

        Args:
            buffer_seconds: Number of seconds before actual expiry to consider
                          the token expired (default 5 minutes).

        Returns:
            True if token is expired or will expire within buffer.
        """
        if not self.expires_at:
            return False
        from datetime import timedelta

        buffer = timedelta(seconds=buffer_seconds)
        return datetime.utcnow() + buffer >= self.expires_at.replace(tzinfo=None)


class OAuthState(Base, UUIDPrimaryKeyMixin):
    """OAuth state for CSRF protection during authorization flow.

    Stores temporary state tokens that are used to prevent CSRF attacks
    during the OAuth authorization code flow.

    Attributes:
        id: UUID primary key.
        user_id: The user initiating the OAuth flow.
        provider: OAuth provider name (e.g., 'notion').
        state: The state token (base64-encoded JSON with user_id + nonce).
        expires_at: When this state expires (typically 10 minutes).
        created_at: Timestamp of record creation.
    """

    __tablename__ = "oauth_states"

    user_id = Column(String, nullable=False)
    provider = Column(String, nullable=False, default="notion")
    state = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default="now()")

    def __repr__(self) -> str:
        return f"<OAuthState(user_id={self.user_id}, provider={self.provider})>"

    def is_expired(self) -> bool:
        """Check if state has expired.

        Returns:
            True if state has expired.
        """
        return datetime.utcnow() >= self.expires_at.replace(tzinfo=None)


__all__ = [
    "OAuthClientRegistration",
    "OAuthToken",
    "OAuthState",
]
