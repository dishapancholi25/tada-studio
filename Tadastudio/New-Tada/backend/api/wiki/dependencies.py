"""Shared dependencies for Wiki API."""

import logging
from typing import Any, Dict

from fastapi import Depends, HTTPException

from backend.api.auth.dependencies import require_active_user
from backend.services.config import ExecutionConfig

logger = logging.getLogger(__name__)


async def require_wiki_access(
    current_user: Dict[str, Any] = Depends(require_active_user),
) -> Dict[str, Any]:
    """Dependency that requires both authentication and wiki feature flag.

    This is a security control for the wiki feature (XSS mitigation item #4).
    When the wiki feature is disabled via ENABLE_WIKI=false, this returns 404.
    Hiding the navigation item alone is not sufficient security.

    Args:
        current_user: Authenticated user from require_active_user dependency

    Returns:
        User claims dictionary if wiki is enabled

    Raises:
        HTTPException: 404 if wiki feature is disabled
    """
    if not ExecutionConfig.wiki_enabled():
        logger.warning(
            "[WIKI] Access denied - wiki feature is disabled. User: %s",
            current_user.get("email", "unknown"),
        )
        raise HTTPException(
            status_code=404,
            detail="Not Found",
        )

    return current_user


async def require_wiki_admin_access(
    current_user: Dict[str, Any] = Depends(require_wiki_access),
) -> Dict[str, Any]:
    """Dependency that restricts wiki write operations to admin users.

    Builds on require_wiki_access (authentication + feature flag), then
    checks the is_admin flag set during authentication. Non-admin users
    receive 403 Forbidden.

    Args:
        current_user: Authenticated user from require_wiki_access dependency

    Returns:
        User claims dictionary if the user is an admin

    Raises:
        HTTPException: 403 if the user is not an admin
    """
    if not current_user.get("is_admin"):
        logger.warning(
            "[WIKI] Write access denied - admin required. User: %s",
            current_user.get("email", "unknown"),
        )
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required to modify wiki pages",
        )

    return current_user


def get_wiki_user_id(current_user: Dict[str, Any]) -> str:
    """Extract user identifier from current_user dict.

    Uses 'sub' claim, falling back to 'email' for backwards compatibility.

    Args:
        current_user: JWT claims dictionary from authentication

    Returns:
        User identifier string
    """
    return current_user.get("sub") or current_user.get("email")
