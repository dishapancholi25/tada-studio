"""Token extraction utilities for authentication.

This module provides functions for extracting authentication tokens
from various sources in HTTP requests, including Authorization headers,
OAuth2 proxy headers, and credentials objects.

Example:
    >>> from backend.services.auth.token_extractor import extract_token_from_request
    >>> from fastapi import Request
    >>> token = extract_token_from_request(request, credentials)
"""

import logging
import hmac
from typing import Optional

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from backend.services.auth.config import get_auth_config


logger = logging.getLogger(__name__)
_proxy_secret_missing_warned = False


def _redact_email(email: str) -> str:
    """Import _redact_email locally to avoid circular imports."""
    from backend.services.auth.rbac import _redact_email as redact_fn

    return redact_fn(email)


def extract_token_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """Extract token from HTTPAuthorizationCredentials object.

    This function extracts the bearer token from FastAPI's security
    credentials object if available.

    Args:
        credentials: FastAPI HTTPAuthorizationCredentials object

    Returns:
        Optional[str]: Token string if present, None otherwise

    Example:
        >>> from fastapi.security import HTTPBearer
        >>> security = HTTPBearer()
        >>> # In endpoint:
        >>> token = extract_token_from_credentials(credentials)
    """
    if credentials and credentials.credentials:
        logger.debug("[AUTH-TOKEN] Token extracted from credentials object")
        return credentials.credentials
    return None


def extract_token_from_authorization_header(request: Request) -> Optional[str]:
    """Extract token from Authorization header.

    This function parses the Authorization header and extracts the
    bearer token if present in the format "Bearer <token>".

    Args:
        request: FastAPI Request object

    Returns:
        Optional[str]: Token string if present, None otherwise

    Example:
        >>> token = extract_token_from_authorization_header(request)
        >>> if token:
        ...     print("Authorization header token found")
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        logger.debug("[AUTH-TOKEN] Token extracted from Authorization header")
        return token
    return None


def extract_token_from_oauth_proxy_header(request: Request) -> Optional[str]:
    """Extract token from OAuth2 proxy header.

    This function extracts the access token from the X-Auth-Request-Access-Token
    header set by oauth2-proxy when forwarding requests.

    Args:
        request: FastAPI Request object

    Returns:
        Optional[str]: Token string if present, None otherwise

    Example:
        >>> token = extract_token_from_oauth_proxy_header(request)
        >>> if token:
        ...     print("OAuth proxy token found")
    """
    proxy_token = request.headers.get("X-Auth-Request-Access-Token")
    if proxy_token:
        logger.debug(
            "[AUTH-TOKEN] Token extracted from X-Auth-Request-Access-Token header"
        )
        return proxy_token
    return None


def extract_token_from_request(
    request: Optional[Request],
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """Extract authentication token from request using multiple strategies.

    This function attempts to extract a token from various sources in order:
    1. HTTPAuthorizationCredentials object (from FastAPI Security dependency)
    2. Authorization header (Bearer token)
    3. X-Auth-Request-Access-Token header (OAuth2 proxy)

    Args:
        request: FastAPI Request object
        credentials: Optional HTTPAuthorizationCredentials from Security dependency

    Returns:
        Optional[str]: First token found, or None if no token present

    Example:
        >>> token = extract_token_from_request(request, credentials)
        >>> if not token:
        ...     raise HTTPException(status_code=401, detail="Missing token")
    """
    # Try credentials object first
    token = extract_token_from_credentials(credentials)
    if token:
        return token

    # Request is required for header-based extraction
    if request is None:
        logger.debug("[AUTH-TOKEN] No request object available for token extraction")
        return None

    # Try Authorization header
    token = extract_token_from_authorization_header(request)
    if token:
        return token

    # Try OAuth proxy header
    token = extract_token_from_oauth_proxy_header(request)
    if token:
        return token

    logger.debug("[AUTH-TOKEN] No token found in request")
    return None


def log_auth_headers(request: Request) -> None:
    """Log authentication-related headers for debugging.

    This function extracts and logs all authentication-related headers
    from a request for troubleshooting purposes. Only logs at DEBUG level.

    Args:
        request: FastAPI Request object

    Example:
        >>> if logger.isEnabledFor(logging.DEBUG):
        ...     log_auth_headers(request)
    """
    # Extract all auth-related headers
    auth_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower().startswith(("x-auth", "x-forwarded", "authorization", "cookie"))
    }

    logger.debug(
        "[AUTH-TOKEN] Auth debug - authorization_header=%s, "
        "proxy_token_present=%s, cookies=%s, all_auth_headers=%s",
        "present" if request.headers.get("Authorization") else "missing",
        bool(request.headers.get("X-Auth-Request-Access-Token")),
        bool(request.headers.get("cookie")),
        auth_headers,
    )


def extract_email_from_oauth_proxy_headers(request: Request) -> Optional[str]:
    """Extract email from OAuth2 proxy headers.

    This function extracts the user's email from the X-Auth-Request-Email
    header set by oauth2-proxy. This header is only present when oauth2-proxy
    has successfully authenticated the user.

    Args:
        request: FastAPI Request object

    Returns:
        Optional[str]: User email if present, None otherwise

    Example:
        >>> email = extract_email_from_oauth_proxy_headers(request)
        >>> if email:
        ...     print(f"Authenticated as: {email}")
    """
    email = request.headers.get("X-Auth-Request-Email")
    if email:
        logger.debug(
            f"[AUTH-TOKEN] Email extracted from OAuth proxy headers: {_redact_email(email)}"
        )
    return email


def is_trusted_oauth_proxy_request(request: Request) -> bool:
    """Verify request authenticity for header-based OAuth proxy identity.

    Behaviour:
    - If AUTH_PROXY_SHARED_SECRET is NOT configured: returns True (backward-
      compatible; trust headers as before). This ensures existing deployments
      keep working when the secret hasn't been rolled out yet.
    - If AUTH_PROXY_SHARED_SECRET IS configured: enforce that the request
      carries the matching secret header. This is the hardened state.
    """
    global _proxy_secret_missing_warned

    config = get_auth_config()
    expected_secret = (config.proxy_auth_shared_secret or "").strip()

    # Backward-compatible: if secret is not configured, trust headers as before.
    # This avoids breaking UAT where the JWT audience is graph.microsoft.com
    # and token-based fallback would fail.
    if not expected_secret:
        if not _proxy_secret_missing_warned:
            logger.warning(
                "[AUTH-TOKEN] AUTH_PROXY_SHARED_SECRET is not configured; "
                "header-based identity is TRUSTED by default (backward-compatible mode). "
                "Configure the secret to enable enforcement."
            )
            _proxy_secret_missing_warned = True
        return True

    header_name = config.proxy_auth_secret_header
    provided_secret = request.headers.get(header_name)
    if not provided_secret:
        logger.warning(
            "[AUTH-TOKEN] Missing trusted proxy authenticity header: %s",
            header_name,
        )
        return False

    trusted = hmac.compare_digest(provided_secret, expected_secret)
    if not trusted:
        logger.warning(
            "[AUTH-TOKEN] Invalid trusted proxy authenticity header: %s",
            header_name,
        )
    return trusted
