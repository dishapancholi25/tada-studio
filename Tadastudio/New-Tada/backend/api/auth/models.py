"""Pydantic models for authentication API endpoints.

This module defines response models for OAuth2 proxy authentication endpoints
and User API Token (Personal Access Token) management.

Example:
    >>> from backend.api.auth.models import UserProfileResponse
    >>> response = UserProfileResponse(claims={"email": "user@example.com"}, user=None)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """Response model for /me endpoint.

    Attributes:
        claims: JWT token claims including is_admin and groups for RBAC
        user: User profile from database (if available)

    Example:
        >>> response = UserProfileResponse(
        ...     claims={
        ...         "email": "user@example.com",
        ...         "sub": "user123",
        ...         "is_admin": True,
        ...         "groups": ["admins", "developers"]
        ...     },
        ...     user={"id": "user123", "email": "user@example.com"}
        ... )
    """

    claims: Dict[str, Any] = Field(
        ..., description="JWT token claims including is_admin and groups for RBAC"
    )
    user: Optional[Dict[str, Any]] = Field(
        None, description="User profile from database"
    )


# ============================================================================
# User API Token (Personal Access Token) Models
# ============================================================================


class CreateTokenRequest(BaseModel):
    """Request model for creating a new user API token.

    Example:
        >>> request = CreateTokenRequest(
        ...     name="My Integration Token",
        ...     scopes=["workflow:*"],
        ...     expires_in_days=90,
        ...     description="Token for CI/CD pipeline"
        ... )
    """

    name: str = Field(
        ...,
        description="User-friendly name for the token",
        min_length=1,
        max_length=100,
    )
    scopes: List[str] = Field(
        default=["workflow:*:execute"],
        description="List of scopes from the scope registry (e.g., 'workflow:*:execute')",
    )
    description: Optional[str] = Field(
        None, description="Optional description of token purpose", max_length=500
    )
    expires_in_days: Optional[int] = Field(
        None,
        description="Number of days until expiration (null for no expiration)",
        ge=1,
        le=365,
    )


class CreateTokenResponse(BaseModel):
    """Response model for token creation.

    IMPORTANT: The token is only shown once and cannot be retrieved again.

    Example:
        >>> response = CreateTokenResponse(
        ...     success=True,
        ...     token="na_abc123def456...",
        ...     token_id="uuid-here",
        ...     token_name="My Integration Token",
        ...     token_prefix="na_abc123de",
        ...     created_at=datetime.now(),
        ...     expires_at=None,
        ...     scopes=["workflow:*"]
        ... )
    """

    success: bool = Field(..., description="Whether token creation succeeded")
    message: str = Field(
        default="Token created successfully", description="Success or error message"
    )
    token: str = Field(..., description="The full token (only shown once!)")
    token_id: str = Field(..., description="Token UUID for management operations")
    token_name: str = Field(..., description="User-friendly token name")
    token_prefix: str = Field(
        ..., description="Token prefix for identification (e.g., 'na_abc123de')"
    )
    created_at: datetime = Field(..., description="Token creation timestamp")
    expires_at: Optional[datetime] = Field(
        None, description="Token expiration timestamp"
    )
    scopes: List[str] = Field(..., description="Token scopes")


class TokenInfo(BaseModel):
    """Information about a user API token (without the plaintext token).

    Example:
        >>> token_info = TokenInfo(
        ...     id="uuid-here",
        ...     name="My Integration Token",
        ...     prefix="na_abc123de",
        ...     scopes=["workflow:*"],
        ...     is_active=True,
        ...     created_at=datetime.now(),
        ...     last_used_at=None,
        ...     usage_count=0
        ... )
    """

    id: str = Field(..., description="Token UUID")
    name: str = Field(..., description="User-friendly token name")
    prefix: str = Field(..., description="Token prefix for identification")
    description: Optional[str] = Field(None, description="Token description")
    scopes: List[str] = Field(..., description="Token scopes")
    is_active: bool = Field(..., description="Whether token is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    last_used_ip: Optional[str] = Field(
        None, description="Last client IP that used this token"
    )
    usage_count: int = Field(..., description="Total number of uses")


class ListTokensResponse(BaseModel):
    """Response model for listing user tokens.

    Example:
        >>> response = ListTokensResponse(
        ...     success=True,
        ...     tokens=[token_info1, token_info2],
        ...     total_count=2
        ... )
    """

    success: bool = Field(..., description="Whether request succeeded")
    tokens: List[TokenInfo] = Field(..., description="List of user tokens")
    total_count: int = Field(..., description="Total number of tokens")


class UpdateTokenScopesRequest(BaseModel):
    """Request model for updating token scopes.

    Example:
        >>> request = UpdateTokenScopesRequest(
        ...     scopes=["workflow:specific-workflow"]
        ... )
    """

    scopes: List[str] = Field(..., description="New list of scopes")


class RevokeTokenResponse(BaseModel):
    """Response model for token revocation.

    Example:
        >>> response = RevokeTokenResponse(
        ...     success=True,
        ...     message="Token revoked successfully",
        ...     token_id="uuid-here"
        ... )
    """

    success: bool = Field(..., description="Whether revocation succeeded")
    message: str = Field(..., description="Success or error message")
    token_id: str = Field(..., description="UUID of revoked token")


class AccessTokenResponse(BaseModel):
    """Response model for the access token endpoint.

    Returns the user's current Azure AD access token for use in HTTP execution.
    """

    token: str = Field(..., description="The Azure AD access token")
    expires_at: Optional[int] = Field(
        None, description="Token expiration as Unix timestamp"
    )
    email: Optional[str] = Field(None, description="Email of the authenticated user")


# ============================================================================
# Scope catalogue models
# ============================================================================


class ScopeDefinition(BaseModel):
    """Metadata about a single permission scope."""

    scope: str = Field(..., description="Scope identifier, e.g. 'workflow:*:execute'")
    label: str = Field(..., description="Human-readable label")
    description: str = Field(..., description="What this scope permits")
    resource: str = Field(..., description="Resource category, e.g. 'workflow'")
    action: str = Field(..., description="Action, e.g. 'execute'")
    admin_only: bool = Field(default=False, description="True if only admins can assign this scope")


class AvailableScopesResponse(BaseModel):
    """Response for GET /api/auth/available-scopes."""

    scopes: List[ScopeDefinition] = Field(..., description="Scopes the caller may assign")
    restrict_to_workflow: bool = Field(
        ...,
        description="True if non-admin scope restriction is currently active for the caller",
    )
    named_workflow_actions: List[str] = Field(
        ...,
        description="Actions allowed on workflow:<name>:* scopes for this user",
    )


# ============================================================================
# Scope rejection log models
# ============================================================================


class ScopeRejectionEntry(BaseModel):
    """A single scope rejection audit log entry."""

    id: str
    token_id: Optional[str] = None
    token_prefix: Optional[str] = None
    user_id: Optional[str] = None
    resource: str
    scope_required: str
    scopes_held: List[str]
    client_ip: Optional[str] = None
    timestamp: Any  # datetime


class ScopeRejectionListResponse(BaseModel):
    """Paginated list of scope rejection entries."""

    entries: List[ScopeRejectionEntry]
    total_count: int
