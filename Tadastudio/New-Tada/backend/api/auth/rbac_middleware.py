"""
RBAC Middleware Module

Provides FastAPI decorators and middleware functions for enforcing role-based access control
at the API endpoint level. Integrates with the existing RBAC utility functions and authentication flow.
"""

import logging
from functools import wraps
from typing import Callable

from fastapi import HTTPException

from backend.services.auth.rbac import (
    _redact_email,
    is_user_admin,
    check_feature_access,
)

logger = logging.getLogger(__name__)


def admin_required(func: Callable) -> Callable:
    """
    Decorator that enforces admin-only access to route handlers.

    Extracts user claims from the route handler's dependencies and verifies
    admin status using the RBAC utility function. Raises 403 Forbidden if
    the user is not an admin.

    Usage:
        @router.get("/admin-endpoint")
        @admin_required
        async def admin_only_route(current_user: Dict = Depends(get_current_user)):
            return {"message": "Admin access granted"}

    Args:
        func: The route handler function to wrap

    Returns:
        Wrapped function with admin access enforcement

    Raises:
        HTTPException: 403 Forbidden if user is not an admin
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user from kwargs (injected by FastAPI dependency)
        current_user = kwargs.get("current_user")

        if not current_user:
            logger.error("[RBAC] admin_required: No current_user found in dependencies")
            raise HTTPException(status_code=403, detail="Admin access required")

        user_email = current_user.get("email", "unknown")

        # Check admin status using RBAC utility
        if not is_user_admin(current_user):
            logger.warning(
                f"[RBAC] Admin access denied for user: {user_email} at endpoint: {func.__name__}"
            )
            raise HTTPException(status_code=403, detail="Admin access required")

        logger.info(
            f"[RBAC] Admin access granted for user: {user_email} at endpoint: {func.__name__}"
        )

        return await func(*args, **kwargs)

    return wrapper


def feature_access_required(feature: str) -> Callable:
    """
    Decorator factory that enforces feature-level access control.

    Creates a decorator that checks if the current user has access to the
    specified feature using the RBAC utility function. Raises 403 Forbidden
    if access is denied.

    Usage:
        @router.get("/settings/database")
        @feature_access_required("settings.database")
        async def database_settings(current_user: Dict = Depends(get_current_user)):
            return {"message": "Database settings access granted"}

    Args:
        feature: Feature identifier (e.g., "settings.database", "settings.llm_providers")

    Returns:
        Decorator function that enforces feature access

    Raises:
        HTTPException: 403 Forbidden if user doesn't have access to the feature
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (injected by FastAPI dependency)
            current_user = kwargs.get("current_user")

            if not current_user:
                logger.error(
                    f"[RBAC] feature_access_required({feature}): No current_user found in dependencies"
                )
                raise HTTPException(
                    status_code=403, detail=f"Access denied to feature: {feature}"
                )

            user_email = current_user.get("email", "unknown")

            # Check feature access using RBAC utility
            has_access = check_feature_access(current_user, feature)

            if not has_access:
                logger.warning(
                    f"[RBAC] Feature access denied for user: {_redact_email(user_email)}, "
                    f"feature: {feature}, endpoint: {func.__name__}"
                )
                raise HTTPException(
                    status_code=403, detail=f"Access denied to feature: {feature}"
                )

            logger.info(
                f"[RBAC] Feature access granted for user: {_redact_email(user_email)}, "
                f"feature: {feature}, endpoint: {func.__name__}"
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
