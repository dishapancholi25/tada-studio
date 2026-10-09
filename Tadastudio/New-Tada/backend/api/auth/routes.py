"""Authentication API endpoints.

This module provides OAuth2 proxy authentication endpoints and
User API Token (Personal Access Token) management.

Endpoints:
    GET /api/auth/me: Get authenticated user profile
    GET /api/auth/access-token: Get current Azure AD access token
    POST /api/auth/tokens: Create new user API token
    GET /api/auth/tokens: List user's API tokens
    GET /api/auth/tokens/{token_id}: Get specific token info
    DELETE /api/auth/tokens/{token_id}: Revoke a token
    PUT /api/auth/tokens/{token_id}/scopes: Update token scopes

Example:
    >>> # Include router in FastAPI app
    >>> from backend.api.auth import router
    >>> app.include_router(router)
"""

import logging
import os
import time
from typing import Any, Dict

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from backend.models.auth.user import User
from backend.services.auth.config import get_auth_config
from backend.services.auth.rbac import _redact_email
from backend.services.auth.user_api_token_service import UserAPITokenService
from backend.services.database import get_db

from .dependencies import get_current_user, require_active_user, require_admin
from .models import (
    AccessTokenResponse,
    AvailableScopesResponse,
    CreateTokenRequest,
    CreateTokenResponse,
    ListTokensResponse,
    RevokeTokenResponse,
    ScopeDefinition,
    ScopeRejectionEntry,
    ScopeRejectionListResponse,
    TokenInfo,
    UpdateTokenScopesRequest,
    UserProfileResponse,
)


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserProfileResponse)
async def get_authenticated_user(
    claims: Dict[str, Any] = Depends(get_current_user),
) -> UserProfileResponse:
    """Get the authenticated user's profile.

    This endpoint returns the user's profile information from both
    JWT claims and the database (if available).

    Args:
        claims: User claims from get_current_user dependency

    Returns:
        UserProfileResponse: User claims and database profile

    Raises:
        HTTPException: 401 if token missing email claim

    Example:
        >>> # GET /api/auth/me
        >>> # Headers: Authorization: Bearer <token>
        >>>
        >>> # Response
        >>> {
        ...     "claims": {
        ...         "email": "user@example.com",
        ...         "sub": "user123",
        ...         "name": "John Doe",
        ...         "is_admin": true,
        ...         "groups": ["admins", "developers"]
        ...     },
        ...     "user": {
        ...         "id": "user123",
        ...         "email": "user@example.com",
        ...         "username": "johndoe",
        ...         "first_name": "John",
        ...         "last_name": "Doe",
        ...         "name": "John Doe",
        ...         "created_at": "2025-10-19T10:00:00Z"
        ...     }
        ... }
    """
    email: str = claims.get("email")
    if not email:
        logger.warning("[AUTH-ME] Token missing email claim")
        raise HTTPException(status_code=401, detail="Token missing email claim")

    db_user_payload: Dict[str, Any] = None

    try:
        with get_db() as db:
            user = db.query(User).filter(User.email == email).first()

            if user:
                db_user_payload = {
                    "id": user.id,
                    "email": user.email,
                    "username": None,  # OAuth users don't have usernames
                    "first_name": user.given_name,
                    "last_name": user.family_name,
                    "name": user.name
                    or f"{user.given_name or ''} {user.family_name or ''}".strip()
                    or user.email,
                    "role": user.role,
                    "is_pending": user.role == "PENDING",
                    "created_at": user.created_at.isoformat()
                    if user.created_at
                    else None,
                    "updated_at": user.updated_at.isoformat()
                    if user.updated_at
                    else None,
                }

                logger.debug(
                    f"[AUTH-ME] User profile loaded from database: {_redact_email(email)}"
                )
    except Exception as db_error:
        logger.warning(
            f"[AUTH-ME] Failed to load user {_redact_email(email)} from database: {db_error}"
        )

    return UserProfileResponse(claims=claims, user=db_user_payload)


@router.get("/access-token", response_model=AccessTokenResponse)
async def get_access_token(
    claims: Dict[str, Any] = Depends(get_current_user),
) -> AccessTokenResponse:
    """Generate a short-lived JWT for HTTP execution use.

    Creates a backend-signed HS256 token containing the user's identity,
    valid for 1 hour. Users can copy this token and pass it as
    ``Authorization: Bearer <token>`` when triggering workflows via HTTP.

    Args:
        claims: User claims from get_current_user dependency

    Returns:
        AccessTokenResponse: The generated JWT, expiry timestamp, and user email

    Raises:
        HTTPException: 401 if user claims are missing email
    """
    auth_config = get_auth_config()

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email claim")

    now = int(time.time())
    expires_at = now + 3600  # 1 hour

    # Use the original "sub" claim as the subject — this is what the system
    # stores as user_id everywhere (e.g. "dev-..." in dev mode, email in prod).
    user_sub = claims.get("sub", email)

    payload = {
        "sub": user_sub,
        "email": email,
        "name": claims.get("name", ""),
        "iss": "agenticstudio",
        "aud": "http-execution",
        "iat": now,
        "exp": expires_at,
    }

    token = pyjwt.encode(payload, auth_config.jwt_secret, algorithm="HS256")

    logger.debug(
        f"[AUTH-TOKEN] Generated HTTP execution token for user '{_redact_email(email)}'"
    )

    return AccessTokenResponse(
        token=token,
        expires_at=expires_at,
        email=email,
    )


# ============================================================================
# User API Token (Personal Access Token) Endpoints
# ============================================================================


def get_user_identifier(current_user: Dict[str, Any]) -> str:
    """Extract user identifier (email) from JWT claims.

    Args:
        current_user: User claims from get_current_user dependency

    Returns:
        User email

    Raises:
        HTTPException: 401 if email not in claims
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier


@router.get("/available-scopes", response_model=AvailableScopesResponse)
async def get_available_scopes(
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> AvailableScopesResponse:
    """Return the scopes the authenticated user is permitted to assign to their tokens.

    Args:
        current_user: Authenticated user from OAuth2 proxy or PAT

    Returns:
        AvailableScopesResponse: Filtered scope catalogue and restriction state
    """
    from backend.services.auth.constants import FeatureName
    from backend.services.auth.rbac import _get_feature_admin_only
    from backend.services.auth.scope_registry import get_user_available_scope_definitions

    is_admin = current_user.get("is_admin", False)

    # Determine if non-admin restriction toggle is enabled (fail-closed)
    try:
        admin_only_flag = _get_feature_admin_only(FeatureName.API_TOKENS_RESTRICT_TO_WORKFLOW.value)
        restrict = admin_only_flag if admin_only_flag is not None else True
    except Exception:
        restrict = True  # fail closed

    scope_dicts = get_user_available_scope_definitions(is_admin=is_admin, restrict_to_workflow=restrict)
    scope_defs = [ScopeDefinition(**s) for s in scope_dicts]

    named_workflow_actions = (
        ["read", "execute", "write"] if is_admin else ["read", "execute"]
    )

    return AvailableScopesResponse(
        scopes=scope_defs,
        restrict_to_workflow=restrict and not is_admin,
        named_workflow_actions=named_workflow_actions,
    )


def _validate_and_check_scopes(scopes: list, current_user: Dict[str, Any]) -> None:
    """Validate scope list and enforce creator ceiling + admin restriction.

    Args:
        scopes: Requested scope strings.
        current_user: Authenticated user claims.

    Raises:
        HTTPException 422: Unknown scope strings.
        HTTPException 403: Scopes exceed ceiling or admin restriction.
    """
    from backend.services.auth.constants import FeatureName
    from backend.services.auth.rbac import _get_feature_admin_only
    from backend.services.auth.scope_registry import validate_scopes

    # 1. Validate against registry
    try:
        validate_scopes(scopes)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))

    is_admin = current_user.get("is_admin", False)

    # 2. Ceiling rule — non-admins cannot grant admin-only scopes
    try:
        UserAPITokenService.enforce_creator_ceiling(scopes, is_admin)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

    # 3. Admin restriction toggle — fail closed
    if not is_admin:
        try:
            admin_only_flag = _get_feature_admin_only(FeatureName.API_TOKENS_RESTRICT_TO_WORKFLOW.value)
            restrict = admin_only_flag if admin_only_flag is not None else True
        except Exception:
            restrict = True

        if restrict:
            non_workflow = [s for s in scopes if not s.startswith("workflow:")]
            if non_workflow:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Non-workflow scopes are restricted for non-admin users: {non_workflow}. "
                        "Contact an administrator to enable broader token scopes."
                    ),
                )


@router.post("/tokens", response_model=CreateTokenResponse)
async def create_user_api_token(
    request: CreateTokenRequest,
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> CreateTokenResponse:
    """Create a new user API token (Personal Access Token).

    This endpoint creates a new API token that the user can use to authenticate
    HTTP execution requests. The token is only shown once and cannot be retrieved later.

    **IMPORTANT**: Save the token immediately as it cannot be retrieved again!

    Args:
        request: Token creation request
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        CreateTokenResponse: Token details including the plaintext token

    Raises:
        HTTPException: 401 if not authenticated, 422 for invalid scopes,
            403 for ceiling/restriction violations, 500 if creation fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/auth/tokens" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "Content-Type: application/json" \\
          -d '{
            "name": "My Integration Token",
            "scopes": ["workflow:*:execute"],
            "expires_in_days": 90,
            "description": "Token for CI/CD pipeline"
          }'
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate scopes, check ceiling, and check admin restriction
        _validate_and_check_scopes(request.scopes, current_user)

        # Create token
        token_obj, plaintext_token = UserAPITokenService.create_token(
            user_id=user_id,
            token_name=request.name,
            scopes=request.scopes,
            description=request.description,
            expires_in_days=request.expires_in_days,
        )

        logger.info(
            f"[AUTH-TOKENS] Created token '{request.name}' for user '{user_id}'"
        )

        return CreateTokenResponse(
            success=True,
            message="Token created successfully. Save it now - it won't be shown again!",
            token=plaintext_token,
            token_id=str(token_obj.id),
            token_name=token_obj.token_name,
            token_prefix=token_obj.token_prefix,
            created_at=token_obj.created_at,
            expires_at=token_obj.expires_at,
            scopes=token_obj.scopes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH-TOKENS] Error creating token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")


@router.get("/tokens", response_model=ListTokensResponse)
async def list_user_api_tokens(
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> ListTokensResponse:
    """List all API tokens for the authenticated user.

    Returns token metadata without the plaintext tokens (which cannot be retrieved).

    Args:
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        ListTokensResponse: List of user's tokens

    Raises:
        HTTPException: 401 if not authenticated, 500 if listing fails

    Example:
        ```bash
        curl "http://localhost:8000/api/auth/tokens" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Get all tokens for user
        tokens = UserAPITokenService.list_user_tokens(user_id)

        # Convert to response models
        token_infos = [
            TokenInfo(
                id=str(token.id),
                name=token.token_name,
                prefix=token.token_prefix,
                description=token.description,
                scopes=token.scopes,
                is_active=token.is_active,
                created_at=token.created_at,
                expires_at=token.expires_at,
                last_used_at=token.last_used_at,
                last_used_ip=token.last_used_ip,
                usage_count=token.usage_count,
            )
            for token in tokens
        ]

        logger.debug(
            f"[AUTH-TOKENS] Listed {len(token_infos)} tokens for user '{user_id}'"
        )

        return ListTokensResponse(
            success=True,
            tokens=token_infos,
            total_count=len(token_infos),
        )

    except Exception as e:
        logger.error(f"[AUTH-TOKENS] Error listing tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tokens: {str(e)}")


@router.get("/tokens/{token_id}", response_model=TokenInfo)
async def get_user_api_token(
    token_id: str,
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> TokenInfo:
    """Get details of a specific API token.

    Args:
        token_id: Token UUID
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        TokenInfo: Token details

    Raises:
        HTTPException: 401 if not authenticated, 404 if not found, 500 if error

    Example:
        ```bash
        curl "http://localhost:8000/api/auth/tokens/{token_id}" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Get token
        token = UserAPITokenService.get_token_by_id(token_id, user_id)

        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_id}' not found")

        return TokenInfo(
            id=str(token.id),
            name=token.token_name,
            prefix=token.token_prefix,
            description=token.description,
            scopes=token.scopes,
            is_active=token.is_active,
            created_at=token.created_at,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            last_used_ip=token.last_used_ip,
            usage_count=token.usage_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH-TOKENS] Error getting token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")


@router.delete("/tokens/{token_id}", response_model=RevokeTokenResponse)
async def revoke_user_api_token(
    token_id: str,
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> RevokeTokenResponse:
    """Revoke (deactivate) an API token.

    Revoked tokens cannot be used for authentication and cannot be reactivated.

    Args:
        token_id: Token UUID to revoke
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        RevokeTokenResponse: Revocation confirmation

    Raises:
        HTTPException: 401 if not authenticated, 404 if not found, 500 if error

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/auth/tokens/{token_id}" \\
          -H "Authorization: Bearer <your-jwt>"
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Revoke token
        success = UserAPITokenService.revoke_token(token_id, user_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Token '{token_id}' not found or you don't have permission to revoke it",
            )

        logger.info(
            f"[AUTH-TOKENS] Revoked token '{token_id}' for user '{_redact_email(user_id)}'"
        )

        return RevokeTokenResponse(
            success=True,
            message="Token revoked successfully",
            token_id=token_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH-TOKENS] Error revoking token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to revoke token: {str(e)}")


@router.put("/tokens/{token_id}/scopes", response_model=TokenInfo)
async def update_token_scopes(
    token_id: str,
    request: UpdateTokenScopesRequest,
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> TokenInfo:
    """Update the scopes of an API token.

    Args:
        token_id: Token UUID
        request: New scopes
        current_user: Authenticated user from OAuth2 proxy

    Returns:
        TokenInfo: Updated token details

    Raises:
        HTTPException: 401 if not authenticated, 404 if not found, 500 if error

    Example:
        ```bash
        curl -X PUT "http://localhost:8000/api/auth/tokens/{token_id}/scopes" \\
          -H "Authorization: Bearer <your-jwt>" \\
          -H "Content-Type: application/json" \\
          -d '{
            "scopes": ["workflow:specific-workflow"]
          }'
        ```
    """
    try:
        user_id = get_user_identifier(current_user)

        # Validate scopes, check ceiling, and check admin restriction
        _validate_and_check_scopes(request.scopes, current_user)

        # Update scopes
        token = UserAPITokenService.update_token_scopes(
            token_id, user_id, request.scopes
        )

        if not token:
            raise HTTPException(
                status_code=404,
                detail=f"Token '{token_id}' not found or you don't have permission to update it",
            )

        logger.info(
            f"[AUTH-TOKENS] Updated scopes for token '{token_id}' "
            f"for user '{user_id}' to {request.scopes}"
        )

        return TokenInfo(
            id=str(token.id),
            name=token.token_name,
            prefix=token.token_prefix,
            description=token.description,
            scopes=token.scopes,
            is_active=token.is_active,
            created_at=token.created_at,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            last_used_ip=token.last_used_ip,
            usage_count=token.usage_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH-TOKENS] Error updating token scopes: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update token scopes: {str(e)}"
        )


# ============================================================================
# Local Email/Password Authentication Endpoints
# ============================================================================


class LocalLoginRequest(BaseModel):
    email: str
    password: str


class CreateLocalUserRequest(BaseModel):
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.get("/nginx-check")
async def nginx_session_check(request: Request):
    """Unified session check for nginx auth_request.

    1. If _local_auth cookie exists and is valid -> 200 + X-Auth-Request-Email header
    2. Otherwise -> forward to oauth2-proxy /oauth2/auth -> mirror its response
    """
    from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED, validate_local_jwt

    # Check local auth cookie first
    if LOCAL_AUTH_ENABLED:
        local_token = request.cookies.get("_local_auth")
        if local_token:
            claims = validate_local_jwt(local_token)
            if claims:
                resp = Response(status_code=200)
                resp.headers["X-Auth-Request-User"] = claims["email"]
                resp.headers["X-Auth-Request-Email"] = claims["email"]
                return resp

    # Fall through to oauth2-proxy
    try:
        async with httpx.AsyncClient() as client:
            # Forward the original request headers that oauth2-proxy needs
            headers = {
                "Cookie": request.headers.get("cookie", ""),
                "X-Original-URI": request.headers.get("x-original-uri", "/"),
                "X-Real-IP": request.headers.get("x-real-ip", ""),
                "X-Scheme": request.headers.get("x-scheme", "https"),
                "Host": request.headers.get("host", ""),
            }
            proxy_resp = await client.get(
               os.getenv("OAUTH2_PROXY_AUTH_URL", "http://10.226.36.5:8880/oauth2/auth"),
                headers=headers,
                follow_redirects=False,
            )

        # nginx auth_request expects 200 for success, not 202
        status = 200 if proxy_resp.status_code in (200, 202) else proxy_resp.status_code
        resp = Response(status_code=status)
        # Forward auth headers from oauth2-proxy
        # NOTE: Only forward identity headers needed for auth_request.
        # Access tokens and Authorization headers are intentionally excluded
        # to prevent token leakage to the browser (ISG Finding 1.9).
        for header_name in (
            "X-Auth-Request-User",
            "X-Auth-Request-Email",
            "X-Auth-Request-Groups",
        ):
            value = proxy_resp.headers.get(header_name)
            if value:
                resp.headers[header_name] = value

        # oauth2-proxy emits X-Auth-Request-* only when --set-xauthrequest is on.
        # Deployments that disable it (so those headers can never reach a browser)
        # still return the session identity in GAP-Auth, so fall back to that:
        # without an email here, nginx's auth_request_set resolves to empty and
        # every downstream request is rejected as unauthenticated.
        if not resp.headers.get("X-Auth-Request-Email"):
            gap_auth = proxy_resp.headers.get("GAP-Auth")
            if gap_auth:
                resp.headers["X-Auth-Request-Email"] = gap_auth
                if not resp.headers.get("X-Auth-Request-User"):
                    resp.headers["X-Auth-Request-User"] = gap_auth
                logger.debug(
                    "[NGINX-CHECK] X-Auth-Request-* absent (set_xauthrequest disabled); "
                    "using GAP-Auth for identity"
                )
        return resp
    except Exception as exc:
        logger.warning(f"[NGINX-CHECK] Failed to reach oauth2-proxy: {exc}")
        return Response(status_code=401)


@router.get("/local/status")
async def local_auth_status():
    """Return whether local email/password authentication is enabled."""
    from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED

    return {"enabled": LOCAL_AUTH_ENABLED}


@router.post("/local/login")
async def local_login(body: LocalLoginRequest, response: Response):
    """Authenticate with email/password and set _local_auth cookie."""
    from backend.services.auth.local_auth import (
        LOCAL_AUTH_ENABLED,
        create_local_jwt,
        verify_local_user,
    )

    if not LOCAL_AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Local auth is not enabled")

    user = verify_local_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_local_jwt(user.email)

    # Set HttpOnly cookie -- secure=True in production (behind HTTPS via nginx)
    is_secure = os.getenv("COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}
    response.set_cookie(
        key="_local_auth",
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/",
    )

    logger.info(f"[LOCAL-AUTH] Login successful for {_redact_email(user.email)}")
    return {"success": True, "email": user.email}


@router.post("/local/logout")
async def local_logout(response: Response):
    """Clear the _local_auth cookie."""
    response.delete_cookie(key="_local_auth", path="/")
    return {"success": True}


# --- Admin-only user management ---


@router.post("/local/users")
async def create_local_user_endpoint(
    body: CreateLocalUserRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    """Create a new local user account (admin only)."""
    from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED, create_local_user

    if not LOCAL_AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Local auth is not enabled")

    try:
        user = create_local_user(body.email, body.password)
        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/local/users")
async def list_local_users_endpoint(
    current_user: Dict[str, Any] = Depends(require_admin),
):
    """List all local users (admin only)."""
    from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED, get_local_users

    if not LOCAL_AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Local auth is not enabled")

    users = get_local_users()
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


@router.delete("/local/users/{user_id}")
async def deactivate_local_user_endpoint(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    """Deactivate a local user (admin only)."""
    from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED, deactivate_local_user

    if not LOCAL_AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Local auth is not enabled")

    if not deactivate_local_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True}


@router.put("/local/users/{user_id}/reset-password")
async def reset_local_user_password_endpoint(
    user_id: str,
    body: ResetPasswordRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    """Reset a local user's password (admin only)."""
    from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED, reset_local_user_password

    if not LOCAL_AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Local auth is not enabled")

    if not reset_local_user_password(user_id, body.new_password):
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True}
@router.get("/tokens/{token_id}/rejections", response_model=ScopeRejectionListResponse)
async def get_token_rejection_log(
    token_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> ScopeRejectionListResponse:
    """Return scope rejection log entries for a specific token.

    The token must belong to the authenticated user. Admins can view any token.

    Args:
        token_id: Token UUID
        limit: Maximum number of entries to return (default 50)
        offset: Pagination offset (default 0)
        current_user: Authenticated user

    Returns:
        ScopeRejectionListResponse: Paginated rejection log entries

    Raises:
        HTTPException: 404 if token not found or not owned by caller
    """
    import json

    from backend.models.auth.scope_rejection_log import ScopeRejectionLog
    from backend.services.database import get_db

    user_id = get_user_identifier(current_user)
    is_admin = current_user.get("is_admin", False)

    # Verify token ownership (admins can view any token)
    token = UserAPITokenService.get_token_by_id(
        token_id, user_id=None if is_admin else user_id
    )
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"Token '{token_id}' not found or you don't have permission to view it",
        )

    try:
        with get_db() as db:
            query = db.query(ScopeRejectionLog).filter(
                ScopeRejectionLog.token_id == token_id
            )
            total_count = query.count()
            rows = (
                query.order_by(ScopeRejectionLog.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            entries = [
                ScopeRejectionEntry(
                    id=str(r.id),
                    token_id=r.token_id,
                    token_prefix=r.token_prefix,
                    user_id=r.user_id,
                    resource=r.resource,
                    scope_required=r.scope_required,
                    scopes_held=json.loads(r.scopes_held) if r.scopes_held else [],
                    client_ip=r.client_ip,
                    timestamp=r.timestamp,
                )
                for r in rows
            ]

        return ScopeRejectionListResponse(entries=entries, total_count=total_count)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH-TOKENS] Error fetching rejection log: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch rejection log: {str(e)}"
        )
