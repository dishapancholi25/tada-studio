"""Dependencies for execution history API endpoints.

This module provides dependency injection functions for authentication and
user context extraction used by the execution history API.
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException

from ..auth.dependencies import get_current_user


def get_user_identifier(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """Extract user identifier from JWT claims.

    This dependency extracts a unique user identifier from the authenticated user's
    JWT token claims. It supports both AIPE users (using email) and legacy Azure AD
    users (falling back to 'sub' claim).

    Args:
        current_user: JWT claims dictionary from authentication

    Returns:
        User identifier string (email or sub claim)

    Raises:
        HTTPException: 401 error if no valid identifier is found in the token

    Examples:
        >>> @router.get("/my-endpoint")
        >>> async def my_endpoint(user_id: str = Depends(get_user_identifier)):
        ...     return {"user": user_id}
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier
