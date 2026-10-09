"""
User resolution utilities for graph storage operations.

This module provides functions for resolving user identifiers (email or sub)
to user IDs for OAuth authenticated users.
"""

from typing import Optional

from sqlalchemy.orm import Session
from backend.models import User
from backend.services.auth.rbac import _redact_email
from backend.services.config import get_logger


logger = get_logger(__name__)


def resolve_user_id(user_identifier: str, db: Session) -> Optional[str]:
    """
    Resolve user identifier (email or sub) to actual user_id.

    This function attempts to find a user by trying multiple strategies:
    1. User by ID (sub)
    2. User by email

    Args:
        user_identifier: Email or sub (user ID)
        db: Database session

    Returns:
        user_id if found, None otherwise

    Examples:
        >>> resolve_user_id("user@example.com", db)
        "azure-sub-id"
        >>> resolve_user_id("azure-sub-id", db)
        "azure-sub-id"
    """
    if not user_identifier:
        return None

    # Try User by ID (sub)
    user = db.query(User).filter(User.id == user_identifier).first()
    if user:
        logger.debug(
            f"[GRAPH-STORAGE] Resolved user '{_redact_email(user_identifier)}' by ID"
        )
        return user.id

    # Try User by email
    user = db.query(User).filter(User.email == user_identifier).first()
    if user:
        logger.debug(
            f"[GRAPH-STORAGE] Resolved user '{_redact_email(user_identifier)}' by email"
        )
        return user.id

    logger.warning(
        f"[GRAPH-STORAGE] Could not resolve user identifier: {_redact_email(user_identifier)}"
    )
    return None


def get_user_info(user_identifier: str, db: Session) -> Optional[dict]:
    """
    Get detailed user information.

    Args:
        user_identifier: Email or sub of the user
        db: Database session

    Returns:
        Dictionary with user info if found, None otherwise
    """
    # Try user by ID
    user = db.query(User).filter(User.id == user_identifier).first()
    if user:
        return {
            "id": user.id,
            "email": user.email,
            "user_type": "oauth",
        }

    # Try user by email
    user = db.query(User).filter(User.email == user_identifier).first()
    if user:
        return {
            "id": user.id,
            "email": user.email,
            "user_type": "oauth",
        }

    return None
