"""RBAC (Role-Based Access Control) utilities for authorization.

This module provides functions for checking admin status and feature permissions
based on OAuth group membership and configuration.
"""

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from backend.services.auth.config import ADMINISTRATORS_GROUP_NAME, get_auth_config

logger = logging.getLogger(__name__)

# Debug mode: log user groups when DEBUG_GROUPS=true
DEBUG_GROUPS = os.getenv("DEBUG_GROUPS", "false").lower() in {"1", "true", "yes"}

# Cache TTL in seconds (default 5 minutes, configurable via env var)
try:
    _CACHE_TTL_SECONDS = int(os.getenv("FEATURE_ACCESS_CACHE_TTL_SECONDS", "300"))
    if _CACHE_TTL_SECONDS < 0:
        logger.warning(
            "FEATURE_ACCESS_CACHE_TTL_SECONDS must be non-negative, using default 300 seconds"
        )
        _CACHE_TTL_SECONDS = 300
except (ValueError, TypeError) as e:
    logger.warning(
        f"Invalid FEATURE_ACCESS_CACHE_TTL_SECONDS value: {os.getenv('FEATURE_ACCESS_CACHE_TTL_SECONDS')}. "
        f"Using default 300 seconds. Error: {e}"
    )
    _CACHE_TTL_SECONDS = 300


def _redact_email(email: str) -> str:
    """Redact email or username for logging.

    Examples:
        'john.doe@example.com' -> 'j**n.d*e@example.com'
        'admin' -> 'a***n'
        'john.smith' -> 'j**n.s***h'
    """
    if not isinstance(email, str):
        return "<redacted>"

    # Helper function to redact a name component
    def redact_name(name: str) -> str:
        parts = name.split(".")
        masked_parts = []
        for part in parts:
            if len(part) <= 1:
                masked_parts.append("*")
            elif len(part) == 2:
                masked_parts.append(part[0] + "*")
            else:
                # Show first and last char, mask middle with asterisks
                masked_parts.append(part[0] + "*" * (len(part) - 2) + part[-1])
        return ".".join(masked_parts)

    # If @ exists, split and redact the local part
    if "@" in email:
        local, domain = email.split("@", 1)
        masked_local = redact_name(local)
        return f"{masked_local}@{domain}"
    else:
        # No @, treat as plain username/name
        return redact_name(email)


# Cache for feature access settings with TTL
# Format: {feature_name: (admin_only_flag, timestamp)}
_feature_access_cache: Dict[str, Tuple[bool, float]] = {}

# Cache for Administrators DB group membership with TTL
# Format: {user_id: (is_member, timestamp)}
_admin_group_cache: Dict[str, Tuple[bool, float]] = {}


def _is_member_of_admin_group(user_id: str) -> bool:
    """Check if user is a member of the Administrators database group.

    Uses a TTL cache to avoid excessive DB queries.

    Args:
        user_id: The user's subject ID

    Returns:
        bool: True if user is in the Administrators group
    """
    current_time = time.time()

    if user_id in _admin_group_cache:
        cached_value, cached_time = _admin_group_cache[user_id]
        if (current_time - cached_time) < _CACHE_TTL_SECONDS:
            return cached_value
        del _admin_group_cache[user_id]

    try:
        from backend.models.auth import Group, GroupMembership
        from backend.services.database import get_db

        with get_db() as session:
            result = (
                session.query(GroupMembership)
                .join(Group, GroupMembership.group_id == Group.id)
                .filter(
                    Group.name == ADMINISTRATORS_GROUP_NAME,
                    GroupMembership.user_id == user_id,
                )
                .first()
            )
            is_member = result is not None

        _admin_group_cache[user_id] = (is_member, current_time)
        return is_member

    except Exception as e:
        logger.warning(f"[RBAC] Error checking Administrators group membership: {e}")
        return False


def clear_admin_group_cache(user_id: Optional[str] = None) -> None:
    """Clear the Administrators group membership cache.

    Args:
        user_id: If provided, clear only this user's cache entry.
                 If None, clear the entire cache.
    """
    if user_id:
        _admin_group_cache.pop(user_id, None)
    else:
        _admin_group_cache.clear()


def is_user_admin(user_claims: Dict[str, Any]) -> bool:
    """Check if user has admin privileges.

    Checks four sources (in order):
    1. User role from database - PRIMARY check
    2. Explicit admin users list (ADMIN_USERS env var) - fast, no DB
    3. OAuth admin group claim (ADMIN_GROUP env var) - fast, no DB
    4. Membership in the Administrators database group - DB query (cached)

    Args:
        user_claims: User claims dictionary from authentication

    Returns:
        bool: True if user is an admin, False otherwise
    """
    # Primary check: user role from database
    user_id = user_claims.get("sub")
    if user_id:
        try:
            from backend.models.auth import User
            from backend.services.database import get_db

            with get_db() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user and user.role == "ADMIN":
                    logger.debug("[RBAC] User is admin (role=ADMIN)")
                    return True
        except Exception as e:
            logger.warning(f"[RBAC] Error checking user role: {e}")

    auth_config = get_auth_config()

    # Check explicit admin users list
    user_email = user_claims.get("email")
    if user_email and user_email.lower() in auth_config.admin_users:
        logger.debug("[RBAC] User is admin (explicit user list)")
        return True

    # Check admin group membership via OAuth claims
    if auth_config.admin_group:
        user_groups = user_claims.get("groups", [])
        if isinstance(user_groups, list) and auth_config.admin_group in user_groups:
            logger.debug(f"[RBAC] User is admin (group: {auth_config.admin_group})")
            return True

    # Check membership in the Administrators database group
    if user_id and _is_member_of_admin_group(user_id):
        logger.debug("[RBAC] User is admin (Administrators DB group)")
        return True

    return False


def is_user_pending(user_claims: Dict[str, Any]) -> bool:
    """Check if user has pending status.

    Args:
        user_claims: User claims dictionary from authentication

    Returns:
        bool: True if user has PENDING role, False otherwise
    """
    user_id = user_claims.get("sub")
    if not user_id:
        return False

    try:
        from backend.models.auth import User
        from backend.services.database import get_db

        with get_db() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user and user.role == "PENDING":
                logger.debug("[RBAC] User is pending approval")
                return True
    except Exception as e:
        logger.warning(f"[RBAC] Error checking user pending status: {e}")

    return False


def can_user_access_system(user_claims: Dict[str, Any]) -> bool:
    """Check if user can access the system.

    Users with PENDING role cannot access the system until approved.

    Args:
        user_claims: User claims dictionary from authentication

    Returns:
        bool: True if user can access system, False if pending
    """
    return not is_user_pending(user_claims)


def get_user_groups(user_claims: Dict[str, Any]) -> list:
    """Extract user groups from claims.

    Args:
        user_claims: User claims dictionary from authentication

    Returns:
        list: List of group names, empty list if no groups
    """
    groups = user_claims.get("groups", [])
    if isinstance(groups, list):
        return groups

    if DEBUG_GROUPS:
        logger.debug(
            "[RBAC-GROUPS] Invalid groups format for user, returning empty list"
        )
    return []


def check_feature_access(user_claims: Dict[str, Any], feature: str) -> bool:
    """Check if user has access to a specific feature.

    Queries the feature_access table to determine if the feature requires
    admin privileges. Admins always have access. For non-admin users,
    access is granted if admin_only is False for the feature.

    Args:
        user_claims: User claims dictionary from authentication
        feature: Feature identifier (e.g., "settings.database", "settings.llm_providers")

    Returns:
        bool: True if user has access, False otherwise
    """
    # Admins always have access to all features
    if is_user_admin(user_claims):
        return True

    # Try to get feature access setting from database
    admin_only = _get_feature_admin_only(feature)

    # If admin_only is None (feature not found), default to accessible by all users
    if admin_only is None:
        logger.debug(
            f"[RBAC] Feature '{feature}' not found in database, defaulting to accessible by all users"
        )
        return True

    # If admin_only is False, grant access to all authenticated users
    # If admin_only is True, deny access (we already checked admin status above)
    return not admin_only


def _get_feature_admin_only(feature: str) -> Optional[bool]:
    """Get admin_only flag for a feature from database.

    Uses TTL-based caching to avoid repeated database queries while ensuring
    consistency across multiple workers. Cache entries expire after the configured
    TTL, forcing a fresh database query.

    Args:
        feature: Feature identifier

    Returns:
        bool | None: admin_only flag, or None if feature not found
    """
    current_time = time.time()

    # Check cache first and validate TTL
    if feature in _feature_access_cache:
        cached_value, cached_time = _feature_access_cache[feature]
        age = current_time - cached_time

        if age < _CACHE_TTL_SECONDS:
            logger.debug(f"[RBAC] Cache hit for '{feature}' (age: {age:.1f}s)")
            return cached_value
        else:
            logger.debug(
                f"[RBAC] Cache expired for '{feature}' (age: {age:.1f}s, TTL: {_CACHE_TTL_SECONDS}s)"
            )
            # Remove expired entry
            del _feature_access_cache[feature]

    # Query database
    try:
        from backend.models.configuration import FeatureAccess
        from backend.services.database import get_db

        with get_db() as session:
            feature_access = (
                session.query(FeatureAccess)
                .filter(FeatureAccess.feature_name == feature)
                .first()
            )

            if feature_access:
                admin_only = feature_access.admin_only
                # Cache the result with timestamp
                _feature_access_cache[feature] = (admin_only, current_time)
                logger.debug(
                    f"[RBAC] Cached '{feature}' = {admin_only} (TTL: {_CACHE_TTL_SECONDS}s)"
                )
                return admin_only

            # Feature not found
            return None

    except Exception as e:
        logger.error(f"[RBAC] Error querying feature_access table: {e}")
        # On error, fail closed (admin-only) for security
        # Return True to indicate feature requires admin access
        return True


def clear_feature_access_cache():
    """Clear the feature access cache.

    Should be called when feature access settings are updated via the admin API.
    Note: With TTL-based caching, manual clearing provides immediate invalidation
    within the current worker, while other workers will pick up changes automatically
    when their cached entries expire (within FEATURE_ACCESS_CACHE_TTL_SECONDS).
    """
    _feature_access_cache.clear()
    logger.info(f"[RBAC] Feature access cache cleared (TTL: {_CACHE_TTL_SECONDS}s)")
