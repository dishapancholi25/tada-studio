"""JWT token validation utilities for checking token expiration and validity.

This module provides functions for validating JWT tokens before they are sent
to external services like MCP servers, preventing expired tokens from being used.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple

import jwt


logger = logging.getLogger(__name__)


def decode_token_without_verification(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT token without signature verification to read claims.

    This is useful for checking token expiration and other claims without
    needing the signing key.

    Args:
        token: JWT token string

    Returns:
        Dict containing token claims, or None if decode fails

    Example:
        >>> claims = decode_token_without_verification(token)
        >>> if claims:
        ...     print(f"Token expires at: {claims.get('exp')}")
    """
    try:
        return jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iss": False,
                "verify_exp": False,
            },
        )
    except Exception as e:
        logger.warning(f"[TOKEN-VALIDATOR] Failed to decode token: {e}")
        return None


def check_token_expiration(
    token: str, leeway_seconds: int = 120
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Check if a JWT token is expired or will expire soon.

    This function decodes the token and checks the 'exp' claim against the current
    time, with an optional leeway period to handle clock skew between systems.

    Args:
        token: JWT token string to validate
        leeway_seconds: Seconds of leeway to allow for clock skew (default: 120)
                       Tokens expiring within this window are considered expired

    Returns:
        Tuple of (is_valid, error_message, claims):
            - is_valid: True if token is valid and not expired
            - error_message: None if valid, error description if invalid
            - claims: Decoded token claims if successful, None otherwise

    Example:
        >>> is_valid, error, claims = check_token_expiration(token)
        >>> if not is_valid:
        ...     print(f"Token invalid: {error}")
    """
    if not token:
        return False, "Token is empty or None", None

    # Decode token to get claims
    claims = decode_token_without_verification(token)
    if not claims:
        return False, "Failed to decode token", None

    # Check for expiration claim
    exp = claims.get("exp")
    if not exp:
        logger.warning("[TOKEN-VALIDATOR] Token has no 'exp' claim")
        # Token without expiration - allow it but log warning
        return True, None, claims

    # Get current time and check expiration
    current_time = time.time()
    time_until_expiry = exp - current_time

    # Log token timing information
    logger.debug(
        f"[TOKEN-VALIDATOR] Token expiration check - "
        f"current_time={current_time}, exp={exp}, "
        f"time_until_expiry={time_until_expiry}s, "
        f"leeway={leeway_seconds}s"
    )

    # Check if token is expired (including leeway)
    if time_until_expiry < -leeway_seconds:
        # Token expired beyond leeway period
        expired_seconds = abs(time_until_expiry)
        error_msg = (
            f"Token expired {expired_seconds:.0f} seconds ago "
            f"(exp={exp}, current={current_time:.0f}, leeway={leeway_seconds}s)"
        )
        logger.error(f"[TOKEN-VALIDATOR] {error_msg}")
        return False, error_msg, claims

    # Check if token is about to expire (within minimum validity period)
    min_validity_seconds = 300  # 5 minutes
    if time_until_expiry < min_validity_seconds:
        logger.warning(
            f"[TOKEN-VALIDATOR] Token expires in {time_until_expiry:.0f} seconds "
            f"(less than {min_validity_seconds}s recommended minimum)"
        )
        # Still valid but warn about imminent expiration
        # We allow this because we can't refresh the token

    return True, None, claims


def log_token_details(token: str, context: str = "") -> None:
    """Log detailed information about a JWT token for debugging.

    This function decodes the token and logs all relevant claims and timing
    information. Useful for troubleshooting authentication issues.

    Args:
        token: JWT token to analyze
        context: Optional context string to include in logs

    Example:
        >>> log_token_details(token, context="MCP Server Request")
    """
    prefix = f"[TOKEN-VALIDATOR:{context}]" if context else "[TOKEN-VALIDATOR]"

    claims = decode_token_without_verification(token)
    if not claims:
        logger.error(f"{prefix} Failed to decode token")
        return

    # Extract common claims
    issued_at = claims.get("iat")
    expires_at = claims.get("exp")
    subject = claims.get("sub")
    issuer = claims.get("iss")
    audience = claims.get("aud")

    current_time = time.time()

    logger.debug(f"{prefix} Token details:")
    logger.debug(f"{prefix}   Subject (sub): {subject}")
    logger.debug(f"{prefix}   Issuer (iss): {issuer}")
    logger.debug(f"{prefix}   Audience (aud): {audience}")

    if issued_at:
        issued_ago = current_time - issued_at
        logger.debug(
            f"{prefix}   Issued at (iat): {issued_at} "
            f"({issued_ago / 60:.1f} minutes ago)"
        )

    if expires_at:
        time_until_expiry = expires_at - current_time
        if time_until_expiry > 0:
            logger.debug(
                f"{prefix}   Expires at (exp): {expires_at} "
                f"(in {time_until_expiry / 60:.1f} minutes)"
            )
        else:
            logger.debug(
                f"{prefix}   Expires at (exp): {expires_at} "
                f"(EXPIRED {abs(time_until_expiry) / 60:.1f} minutes ago)"
            )

        # Token lifetime
        if issued_at and expires_at:
            lifetime = expires_at - issued_at
            logger.debug(f"{prefix}   Token lifetime: {lifetime / 60:.1f} minutes")

    logger.debug(f"{prefix}   Current time: {current_time}")


def validate_token_for_mcp(token: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate a token before sending to an MCP server.

    This is a high-level validation function that performs all necessary checks
    before using a token with an MCP server.

    Args:
        token: JWT token to validate

    Returns:
        Tuple of (is_valid, error_message):
            - is_valid: True if token can be used
            - error_message: None if valid, error description if invalid

    Example:
        >>> is_valid, error = validate_token_for_mcp(token)
        >>> if not is_valid:
        ...     logger.error(f"Cannot use token: {error}")
        ...     raise ValueError(error)
    """
    if not token:
        return False, "No token provided"

    # Check expiration with 2-minute leeway for clock skew
    is_valid, error, claims = check_token_expiration(token, leeway_seconds=120)

    if not is_valid:
        return False, error

    return True, None
