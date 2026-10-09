"""Dependencies for chat API endpoints."""

from typing import Any, Dict

from fastapi import Depends, HTTPException

from ..auth.dependencies import get_current_user


def get_user_identifier(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """Extract user identifier from JWT claims.

    Args:
        current_user: JWT claims dictionary from authentication

    Returns:
        User identifier string (sub claim)

    Raises:
        HTTPException: 401 error if no valid identifier is found
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier
