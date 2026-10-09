"""JWT token utilities for OAuth2 proxy authentication.

This module provides functions for decoding JWT tokens that have already
been validated by OAuth2 proxy. It does not create or verify tokens.

Example:
    >>> from backend.services.auth.jwt_utils import decode_token_without_verification
    >>> # Only use after oauth2-proxy has validated the token
    >>> payload = decode_token_without_verification(proxy_token)
    >>> print(payload["email"])
    user@example.com
"""

import logging
from typing import Any, Dict, Optional

import jwt


logger = logging.getLogger(__name__)


def decode_token_without_verification(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT token without verifying signature or expiration.

    This function is used in OAuth proxy mode where the proxy has already
    validated the token. It extracts claims for enrichment purposes only.

    Args:
        token: JWT token string to decode

    Returns:
        Optional[Dict[str, Any]]: Decoded payload if parseable, None otherwise

    Warning:
        This function does NOT validate the token. Only use it when the
        token has been validated by a trusted upstream service (e.g., oauth2-proxy).

    Example:
        >>> # Only use this when oauth2-proxy has already validated the token
        >>> unverified_claims = decode_token_without_verification(proxy_token)
        >>> if unverified_claims:
        ...     name = unverified_claims.get("name", "")
    """
    # Check if token looks like a JWT (3 parts separated by dots)
    # This prevents attempting to decode non-JWT tokens like "basic_auth_user@example.com"
    if not token or token.count(".") != 2:
        logger.debug(
            "[AUTH-JWT] Token does not appear to be a JWT format (expected 3 segments), skipping decode"
        )
        return None

    try:
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iss": False,
                "verify_exp": False,
            },
        )
        logger.debug("[AUTH-JWT] Token decoded without verification")
        return payload

    except Exception as exc:
        logger.warning(f"[AUTH-JWT] Failed to decode token without verification: {exc}")
        return None
