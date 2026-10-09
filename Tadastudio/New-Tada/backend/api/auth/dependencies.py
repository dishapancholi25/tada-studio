"""FastAPI dependencies for authentication.

This module provides dependency functions for authenticating requests,
including the main get_current_user dependency used throughout the API.

Example:
    >>> from fastapi import Depends
    >>> from backend.api.auth.dependencies import get_current_user
    >>>
    >>> @app.get("/protected")
    >>> async def protected_endpoint(user: Dict[str, Any] = Depends(get_current_user)):
    ...     return {"user": user["email"]}
"""

import logging
import os
from typing import Any, Callable, Dict, Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.services.auth import (
    MissingEmailClaimError,
    MissingTokenError,
    OAuth2ConfigurationError,
    RequestContextUnavailableError,
    extract_token_from_request,
    get_oauth_proxy_auth,
)
from backend.services.auth.jwt_utils import decode_token_without_verification
from backend.services.auth.rbac import _redact_email
from backend.services.auth.token_extractor import (
    extract_email_from_oauth_proxy_headers,
    is_trusted_oauth_proxy_request,
)
from backend.services.auth.user_sync import sync_user_from_claims

# Development mode: skip auth when SKIP_AUTH=true
# Configure dev user via DEV_USER_EMAIL and DEV_USER_NAME in .env
SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() in {"1", "true", "yes"}
DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL", "dev@localhost")
DEV_USER_NAME = os.getenv("DEV_USER_NAME", "Development User")

# Debug mode: log user groups when DEBUG_GROUPS=true
DEBUG_GROUPS = os.getenv("DEBUG_GROUPS", "false").lower() in {"1", "true", "yes"}


logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


def _extract_websocket_user_email(websocket) -> Optional[str]:
    """Extract websocket user identity from proxy-forwarded headers."""
    header_candidates = (
        "X-User-Email",
        "X-Auth-Request-Email",
        "X-Forwarded-Email",
        "X-Auth-Request-User",
        "X-Forwarded-User",
        "X-Forwarded-Preferred-Username",
    )

    headers = websocket.headers
    for header_name in header_candidates:
        header_value = headers.get(header_name) or headers.get(header_name.lower())
        if header_value:
            return header_value.strip()

    return None


def _get_websocket_auth_header_names(websocket) -> list[str]:
    """Return auth-related WebSocket header names for safe diagnostics."""
    diagnostic_prefixes = (
        "authorization",
        "cookie",
        "host",
        "origin",
        "sec-websocket",
        "x-auth",
        "x-forwarded",
        "x-user",
    )
    return sorted(
        header_name
        for header_name in websocket.headers.keys()
        if header_name.lower().startswith(diagnostic_prefixes)
    )


def _authenticate_oauth_proxy_with_headers(request: Request) -> Dict[str, Any]:
    """Authenticate using OAuth2 proxy headers.

    This function trusts the authentication done by oauth2-proxy and builds
    user claims from the forwarded headers. Requests only reach here if
    oauth2-proxy's auth_request succeeded.

    Args:
        request: FastAPI Request object

    Returns:
        Dict[str, Any]: User claims dictionary

    Raises:
        MissingEmailClaimError: If X-Auth-Request-Email header is missing
    """
    oauth_proxy_auth = get_oauth_proxy_auth()
    if not is_trusted_oauth_proxy_request(request):
        raise MissingTokenError("Untrusted proxy identity headers")

    # Get email from oauth2-proxy header
    email = extract_email_from_oauth_proxy_headers(request)
    if not email:
        raise MissingEmailClaimError("Missing email from oauth2-proxy")

    # Detect auth source: nginx basic auth tokens use "basic_auth_<user>" format,
    # while real OAuth2 proxy forwards actual JWT tokens.
    token = extract_token_from_request(request)
    is_basic_auth = token and token.startswith("basic_auth_")

    # Build base claims from headers
    claims: Dict[str, Any] = {
        "email": email,
        "auth_source": "basic_auth" if is_basic_auth else "oauth_proxy",
        "sub": email,  # Use email as subject
    }
    # Try to extract additional info from a real JWT token (skip basic auth tokens)
    if token and not is_basic_auth:
        try:
            # Decode WITHOUT validation (oauth2-proxy already did this)
            unverified_claims = decode_token_without_verification(token)
            if unverified_claims:
                # Debug: Log claim keys when DEBUG_GROUPS is enabled
                if DEBUG_GROUPS:
                    claim_keys = list(unverified_claims.keys())
                    logger.debug(
                        f"[AUTH-TOKEN-CLAIMS] Available claim keys: {claim_keys}"
                    )

                # Extract useful fields from the token
                claims["name"] = unverified_claims.get("name", "")
                claims["given_name"] = unverified_claims.get("given_name", "")
                claims["family_name"] = unverified_claims.get("family_name", "")
                claims["oid"] = unverified_claims.get("oid")
                claims["tid"] = unverified_claims.get("tid")

                # Try multiple group claim names (Azure AD can use different names)
                groups = (
                    unverified_claims.get("groups")  # Standard groups claim
                    or unverified_claims.get("roles")  # Application roles
                    or unverified_claims.get(
                        "wids"
                    )  # Well-known IDs for directory roles
                    or []
                )
                claims["groups"] = (
                    groups if isinstance(groups, list) else [groups] if groups else []
                )

                # Check for groups from oauth2-proxy header (used when token has group overage)
                # OAuth2-proxy fetches groups via Graph API and passes them in X-Auth-Request-Groups header
                groups_header = request.headers.get("X-Auth-Request-Groups")
                if groups_header:
                    # Parse comma-separated group IDs from header
                    header_groups = [
                        g.strip() for g in groups_header.split(",") if g.strip()
                    ]
                    if header_groups:
                        claims["groups"] = header_groups
                        if DEBUG_GROUPS:
                            logger.debug(
                                "[AUTH-TOKEN-CLAIMS] Using groups from X-Auth-Request-Groups header"
                            )

                if DEBUG_GROUPS and claims["groups"]:
                    logger.debug("[AUTH-TOKEN-CLAIMS] Extracted groups from token")
                elif DEBUG_GROUPS:
                    logger.warning(
                        "[AUTH-TOKEN-CLAIMS] No groups found in token. Check Azure AD app registration for group claims configuration."
                    )
        except Exception as exc:
            logger.warning(
                f"[AUTH] Could not decode token for additional claims: {exc}"
            )

    # Sync user to database
    if oauth_proxy_auth:
        from backend.services.auth.user_sync import sync_user_from_claims

        sync_user_from_claims(claims)

    # Enrich claims with admin status and normalized groups
    from backend.services.auth.rbac import get_user_groups, is_user_admin

    claims["is_admin"] = is_user_admin(claims)
    claims["groups"] = get_user_groups(claims)

    if DEBUG_GROUPS:
        logger.debug("[AUTH-GROUPS] User group enrichment complete")

    logger.debug("[AUTH] OAuth proxy header authentication successful")
    return claims


def _authenticate_oauth_proxy_with_token(
    token: str, request: Request
) -> Dict[str, Any]:
    """Authenticate using OAuth2 proxy with token validation.

    This function performs full JWT token validation using the OAuth2ProxyAuth
    provider and returns the validated claims.

    Args:
        token: JWT access token
        request: FastAPI Request object

    Returns:
        Dict[str, Any]: Validated user claims

    Raises:
        OAuth2ConfigurationError: If OAuth authentication is not configured
        RequestContextUnavailableError: If request context is unavailable
    """
    oauth_proxy_auth = get_oauth_proxy_auth()

    if oauth_proxy_auth is None:
        raise OAuth2ConfigurationError("OAuth authentication is not configured")

    if request is None:
        # FastAPI always injects Request, but guard defensively for tests
        raise RequestContextUnavailableError()

    claims = oauth_proxy_auth.verify_and_sync(token, request)
    logger.debug(
        f"[AUTH] OAuth proxy token authentication successful: {_redact_email(claims.get('email', 'unknown'))}"
    )
    return claims


async def _authenticate_pat(token: str, request: Request) -> Dict[str, Any]:
    """Authenticate a PAT (na_-prefixed token) and return synthetic claims.

    The returned claims dict includes ``active_scopes`` (the token's scope list)
    and ``auth_via_pat=True`` so downstream scope enforcement knows to check.

    Args:
        token: The plaintext ``na_``-prefixed token.
        request: Incoming FastAPI request (used for IP logging).

    Returns:
        Dict[str, Any]: Synthetic user claims.

    Raises:
        HTTPException 401: If token is invalid, expired, or inactive.
    """
    from backend.models.auth.user import User
    from backend.services.auth.user_api_token_service import UserAPITokenService
    from backend.services.database import get_db

    result = UserAPITokenService.validate_token_no_scope_check(token)
    if result is None:
        logger.warning("[AUTH] Invalid or expired PAT presented")
        raise HTTPException(status_code=401, detail="Invalid or expired API token")

    token_obj, user_id = result

    # Fetch user record for is_admin flag and email
    is_admin = False
    email = user_id
    try:
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                is_admin = user.role == "ADMIN"
                email = user.email or user_id
    except Exception as exc:
        logger.warning("[AUTH] Could not fetch user record for PAT: %s", exc)

    client_ip = request.client.host if request and request.client else None

    # Best-effort usage update (no scope guard yet — usage is for auth events)
    try:
        from backend.services.database import get_db as _get_db

        with _get_db() as db:
            from backend.models.auth.user_api_token import UserAPIToken as _UAT

            tok = db.query(_UAT).filter(_UAT.id == token_obj.id).first()
            if tok:
                tok.update_usage(client_ip)
                db.commit()
    except Exception:
        pass  # best-effort; never block auth

    logger.debug("[AUTH] PAT authentication successful for token prefix=%s", token_obj.token_prefix)

    return {
        "sub": user_id,
        "email": email,
        "is_admin": is_admin,
        "groups": [],
        "auth_via_pat": True,
        "pat_token_id": str(token_obj.id),
        "pat_token_prefix": token_obj.token_prefix,
        "active_scopes": token_obj.scopes or [],
        "auth_source": "pat",
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request: Request = None,
) -> Dict[str, Any]:
    """Resolve the authenticated user from OAuth2 proxy request.

    This dependency function extracts and validates authentication from
    OAuth2 proxy headers or tokens, returning the user's claims.

    PATs (``na_``-prefixed tokens) are detected first and handled via a
    separate code path that returns synthetic claims with ``auth_via_pat=True``
    and an ``active_scopes`` list for per-route scope enforcement.

    Args:
        credentials: HTTPAuthorizationCredentials from Security dependency
        request: FastAPI Request object

    Returns:
        Dict[str, Any]: User claims dictionary containing email, name, etc.

    Raises:
        MissingTokenError: If authentication token is missing
        MissingEmailClaimError: If OAuth proxy email header is missing
        OAuth2ConfigurationError: If OAuth is not configured properly
        RequestContextUnavailableError: If request context is unavailable

    Example:
        >>> from fastapi import Depends
        >>>
        >>> @app.get("/profile")
        >>> async def get_profile(user = Depends(get_current_user)):
        ...     return {"email": user["email"]}
    """

    # Development mode: return mock user when SKIP_AUTH is enabled
    # Configure via DEV_USER_EMAIL and DEV_USER_NAME in .env
    if SKIP_AUTH:
        logger.debug(
            f"[AUTH] SKIP_AUTH enabled - using dev user: {_redact_email(DEV_USER_EMAIL)}"
        )
        dev_claims = {
            "email": DEV_USER_EMAIL,
            "name": DEV_USER_NAME,
            "sub": DEV_USER_EMAIL,  # Use email directly for consistency with OAuth
            "auth_source": "skip_auth",
        }
        # Sync dev user to database so workflows can be created
        sync_user_from_claims(dev_claims)

        # Enrich claims with admin status and normalized groups
        from backend.services.auth.rbac import get_user_groups, is_user_admin

        dev_claims["is_admin"] = is_user_admin(dev_claims)
        dev_claims["groups"] = get_user_groups(dev_claims)

        if DEBUG_GROUPS:
            logger.debug(
                f"[AUTH-GROUPS] Dev user {_redact_email(DEV_USER_EMAIL)} has {len(dev_claims['groups'])} groups, is_admin={dev_claims['is_admin']}"
            )

        return dev_claims

    # Local email/password cookie check (defence-in-depth alongside nginx-check)
    # Only active when ENABLE_LOCAL_AUTH=true
    if request is not None:
        from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED

        local_token = request.cookies.get("_local_auth") if LOCAL_AUTH_ENABLED else None
        if local_token:
            from backend.services.auth.local_auth import validate_local_jwt

            local_claims = validate_local_jwt(local_token)
            if local_claims:
                from backend.services.auth.rbac import get_user_groups, is_user_admin

                sync_user_from_claims(local_claims)
                local_claims["is_admin"] = is_user_admin(local_claims)
                local_claims["groups"] = get_user_groups(local_claims)
                logger.debug("[AUTH] Local cookie authentication successful")
                return local_claims
    # --- PAT detection: handle na_-prefixed tokens before OAuth proxy path ---
    token = extract_token_from_request(request, credentials)
    if token and token.startswith("na_"):
        return await _authenticate_pat(token, request)
    # --- End PAT detection ---

    # OAuth proxy header-based authentication (preferred)
    # In this mode, oauth2-proxy validates the user and forwards headers
    if request is not None and request.headers.get("X-Auth-Request-Email"):
        if is_trusted_oauth_proxy_request(request):
            # Email header present from trusted proxy: use header-based auth path.
            return _authenticate_oauth_proxy_with_headers(request)
        logger.warning(
            "[AUTH] Ignoring untrusted X-Auth-Request-Email header; falling back to token-based auth"
        )

    # OAuth proxy token-based authentication (fallback)
    if not token:
        raise MissingTokenError()

    claims = _authenticate_oauth_proxy_with_token(token, request)

    # Enrich claims with admin status and normalized groups
    from backend.services.auth.rbac import get_user_groups, is_user_admin

    claims["is_admin"] = is_user_admin(claims)
    claims["groups"] = get_user_groups(claims)

    if DEBUG_GROUPS:
        logger.debug("[AUTH-GROUPS] User group enrichment complete")

    return claims


async def require_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dependency that enforces active (non-pending) user access.

    This dependency checks if the authenticated user has an active account
    (not PENDING status). Users with PENDING status cannot access the system
    until approved by an admin.

    Args:
        current_user: User claims dictionary from get_current_user dependency

    Returns:
        Dict[str, Any]: User claims dictionary (allows chaining)

    Raises:
        HTTPException: 403 Forbidden if user is pending approval

    Example:
        >>> @router.get("/protected", dependencies=[Depends(require_active_user)])
        >>> async def protected_endpoint():
        ...     return {"message": "Active user access granted"}
    """
    from backend.services.auth.rbac import is_user_pending

    if is_user_pending(current_user):
        user_email = current_user.get("email", "unknown")
        logger.warning(
            f"[RBAC] Access denied for pending user: {_redact_email(user_email)}"
        )
        raise HTTPException(
            status_code=403,
            detail="Account pending approval. Please contact an administrator.",
        )

    return current_user


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dependency that enforces admin-only access to endpoints.

    This dependency checks if the authenticated user has admin privileges
    by examining the is_admin flag set by get_current_user. Raises 403
    Forbidden if the user is not an admin.

    Args:
        current_user: User claims dictionary from get_current_user dependency

    Returns:
        Dict[str, Any]: User claims dictionary (allows chaining)

    Raises:
        HTTPException: 403 Forbidden if user is not an admin

    Example:
        >>> @router.get("/admin-only", dependencies=[Depends(require_admin)])
        >>> async def admin_endpoint():
        ...     return {"message": "Admin access granted"}
    """
    if not current_user.get("is_admin"):
        user_email = current_user.get("email", "unknown")
        logger.warning(
            f"[RBAC] Admin access denied for user: {_redact_email(user_email)}"
        )
        raise HTTPException(status_code=403, detail="Admin privileges required")

    logger.debug(
        f"[RBAC] Admin access granted for user: {_redact_email(current_user.get('email', 'unknown'))}"
    )
    return current_user


def require_feature_access(feature: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Dependency factory that enforces feature-level access control.

    Creates a dependency function that checks if the authenticated user
    has access to the specified feature using the RBAC utility function.
    Raises 403 Forbidden if access is denied.

    Args:
        feature: Feature identifier (e.g., "settings.database", "settings.llm_providers")

    Returns:
        Callable[[Dict[str, Any]], Dict[str, Any]]: Async dependency function that
            takes current_user dict and returns it if access is granted

    Raises:
        HTTPException: 403 Forbidden if user doesn't have access to the feature

    Example:
        >>> @router.get("/settings/database", dependencies=[Depends(require_feature_access("settings.database"))])
        >>> async def database_settings():
        ...     return {"message": "Database settings access granted"}
    """

    async def _check_access(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """Inner dependency function that performs the access check.

        Args:
            current_user: Authenticated user claims from JWT

        Returns:
            Dict[str, Any]: User claims if access is granted

        Raises:
            HTTPException: 403 if access denied
        """
        from backend.services.auth.rbac import check_feature_access

        if not check_feature_access(current_user, feature):
            user_email = current_user.get("email", "unknown")
            logger.warning(
                f"[RBAC] Feature access denied for user: {_redact_email(user_email)}, feature: {feature}"
            )
            raise HTTPException(status_code=403, detail=f"Access denied to {feature}")

        logger.debug(
            f"[RBAC] Feature access granted for user: {_redact_email(current_user.get('email', 'unknown'))}, feature: {feature}"
        )
        return current_user

    return _check_access


async def get_current_user_ws(websocket) -> Optional[Dict[str, Any]]:
    """Get current user from WebSocket connection.

    Mirrors get_current_user: the forwarded bearer token is tried first, then
    proxy identity headers. Resolving the token first keeps the claims -- most
    importantly "sub" and "is_admin" -- identical to the HTTP path, so
    ownership checks against records written by HTTP handlers succeed.

    Args:
        websocket: FastAPI WebSocket connection

    Returns:
        Dict with user claims if authenticated, None otherwise
    """
    import os

    _skip_auth = os.getenv("SKIP_AUTH", "false").lower() in {"1", "true", "yes"}

    if _skip_auth:
        # Check for SSO email in query params or cookies
        sso_email = None

        # Try query params first (for testing)
        test_user = websocket.query_params.get("test_user")
        if test_user:
            sso_email = test_user

        # Try cookies (jwtToken from SSO)
        if not sso_email:
            jwt_token = websocket.cookies.get("jwtToken")
            if jwt_token:
                try:
                    jwt_claims = decode_token_without_verification(jwt_token)
                    if jwt_claims:
                        sso_email = jwt_claims.get("email")
                except Exception as e:
                    logger.warning(f"[AUTH-WS] Failed to decode jwtToken: {e}")

        user_email = sso_email if sso_email else DEV_USER_EMAIL
        user_name = DEV_USER_NAME if not sso_email else user_email.split("@")[0].replace(".", " ").title()

        return {
            "email": user_email,
            "name": user_name,
            "sub": user_email,
            "user_id": user_email,
            "auth_source": "websocket_skip_auth",
        }

    from backend.services.auth.rbac import is_user_admin

    # Production: prefer the bearer token forwarded by oauth2-proxy
    # (pass_authorization_header). It resolves the same "sub" the HTTP path
    # records as GraphExecution.user_id, so ownership checks agree. Header
    # identity uses the email as "sub", which does not match a token "sub"
    # in deployments where oauth2-proxy proxies straight to the backend.
    #
    # is_user_admin looks the role up in the database keyed on that same "sub";
    # oauth2-proxy only establishes *who* the user is, never what they may do.
    token = extract_token_from_request(websocket)
    if token:
        try:
            claims = _authenticate_oauth_proxy_with_token(token, websocket)
            claims["is_admin"] = is_user_admin(claims)
            claims["auth_source"] = "websocket_token"
            logger.debug("[AUTH-WS] Token authentication successful")
            return claims
        except Exception as exc:
            logger.warning(
                "[AUTH-WS] Bearer token validation failed, falling back to identity headers: %s",
                exc,
            )

    # Fallback: headers set by oauth2-proxy / ingress. Used by nginx
    # auth_request topologies, where the HTTP path also derives "sub" from
    # the email and the two therefore agree.
    #
    # Apply the same trust check as the HTTP header path: when
    # AUTH_PROXY_SHARED_SECRET is configured, identity headers are only
    # accepted if the request carries the matching X-Auth-Proxy-Secret,
    # closing the header-spoofing gap for direct backend access.
    if not is_trusted_oauth_proxy_request(websocket):
        logger.warning(
            "[AUTH-WS] Rejecting untrusted proxy identity headers "
            "(missing or invalid proxy authenticity secret)"
        )
        return None

    user_email = _extract_websocket_user_email(websocket)
    if not user_email:
        websocket_path = getattr(getattr(websocket, "url", None), "path", "unknown")
        logger.warning(
            "[AUTH-WS] Missing WebSocket user identity for path=%s; auth_header_names=%s",
            websocket_path,
            _get_websocket_auth_header_names(websocket),
        )
        return None

    claims = {
        "email": user_email,
        "name": user_email.split("@")[0].replace(".", " ").title(),
        "sub": user_email,
        "user_id": user_email,
        "auth_source": "websocket_oauth",
    }
    claims["is_admin"] = is_user_admin(claims)
    return claims
