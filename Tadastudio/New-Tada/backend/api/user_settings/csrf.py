"""CSRF protection for user settings API.

This module provides CSRF protection for state-changing operations
on user settings endpoints.
"""

import logging
from typing import Optional

from fastapi import Header, HTTPException


logger = logging.getLogger(__name__)


async def verify_csrf_token(
    x_csrf_token: Optional[str] = Header(None),
    origin: Optional[str] = Header(None),
    referer: Optional[str] = Header(None),
) -> None:
    """Verify CSRF protection for state-changing requests.

    Uses a combination of:
    1. Custom X-CSRF-Token header presence (custom header requirement)
    2. Origin/Referer header validation

    Args:
        x_csrf_token: Custom CSRF token header
        origin: Origin header from browser
        referer: Referer header from browser

    Raises:
        HTTPException: 403 if CSRF validation fails
    """
    # For API requests with custom headers, the browser will send a preflight
    # OPTIONS request. Requiring a custom header provides CSRF protection
    # because only JavaScript from the same origin can set custom headers.
    if not x_csrf_token:
        raise HTTPException(
            status_code=403,
            detail="CSRF validation failed: X-CSRF-Token header is required",
        )

    # Additional validation: check Origin/Referer matches expected domain
    # This is optional but provides defense-in-depth
    # In production, you might want to validate against a whitelist of domains
    if not origin and not referer:
        logger.warning("CSRF check: No Origin or Referer header present")
        # We don't fail here because the custom header is the main protection,
        # but this should be monitored

    logger.debug(
        f"CSRF validation passed. Origin: {origin}, Referer: {referer}, "
        f"Token present: {bool(x_csrf_token)}"
    )
