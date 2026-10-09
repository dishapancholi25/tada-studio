"""Request utility functions for HTTP execution API.

This module provides helpers for extracting client information and context
from FastAPI requests.
"""

from typing import Optional, Tuple

from fastapi import Request
from backend.services.config import get_logger


logger = get_logger(__name__)


def extract_client_info(
    request: Optional[Request],
) -> Tuple[Optional[str], Optional[str]]:
    """Extract client IP and user agent from a FastAPI request.

    This function safely extracts client metadata from the request, handling
    proxy configurations (X-Forwarded-For header) and missing request objects.

    Args:
        request: FastAPI request object (can be None)

    Returns:
        Tuple of (client_ip, user_agent), either or both can be None

    Example:
        >>> from fastapi import Request
        >>> request = Request(...)
        >>> client_ip, user_agent = extract_client_info(request)
        >>> print(f"Request from {client_ip} using {user_agent}")
    """
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None

    if request is None:
        logger.debug(
            "[HTTP-EXEC] No request object provided for client info extraction"
        )
        return client_ip, user_agent

    try:
        # Prefer X-Forwarded-For if the app is behind a proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first (client)
            client_ip = forwarded_for.split(",")[0].strip()
            logger.debug(
                f"[HTTP-EXEC] Extracted client IP from X-Forwarded-For: {client_ip}"
            )
        elif request.client:
            client_ip = request.client.host
            logger.debug(
                f"[HTTP-EXEC] Extracted client IP from request.client: {client_ip}"
            )

        # Extract user agent
        user_agent = request.headers.get("user-agent")
        if user_agent:
            logger.debug(f"[HTTP-EXEC] Extracted user agent: {user_agent[:50]}...")

    except Exception as e:
        logger.warning(f"[HTTP-EXEC] Failed to extract client info: {e}")

    return client_ip, user_agent


def get_base_url(request: Optional[Request]) -> str:
    """Get the base URL from the request or configuration.

    Args:
        request: FastAPI request object (can be None)

    Returns:
        Base URL string (without trailing slash)

    Example:
        >>> base_url = get_base_url(request)
        >>> endpoint = f"{base_url}/api/http-execution/trigger/my-workflow"
    """
    if request is not None:
        try:
            return str(request.base_url).rstrip("/")
        except Exception as e:
            logger.warning(f"[HTTP-EXEC] Failed to extract base URL from request: {e}")

    # Fallback to configured base URL
    try:
        from backend.services.config import get_api_base_url

        base_url = get_api_base_url()
        logger.debug(f"[HTTP-EXEC] Using configured base URL: {base_url}")
        return base_url
    except Exception as e:
        logger.error(f"[HTTP-EXEC] Failed to get base URL from config: {e}")
        return "http://localhost:8000"  # Final fallback

