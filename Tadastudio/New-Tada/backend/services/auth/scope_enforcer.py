"""PAT scope enforcement for FastAPI routes.

This module provides:
- ``require_scope(required_scope)`` — dependency factory that enforces a scope
  on PAT-authenticated requests.  Session-authenticated requests are bypassed.
- ``_scopes_satisfy(held, required)`` — pure matching logic (no I/O).
- ``_record_rejection(...)`` — best-effort audit log writer.
"""

import json
import logging
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, Request

from backend.api.auth.dependencies import get_current_user
from backend.services.auth.scope_registry import is_valid_scope


logger = logging.getLogger(__name__)
LOG_PREFIX = "[SCOPE-ENFORCE]"


def require_scope(required_scope: str):
    """FastAPI dependency factory that enforces a PAT scope per route.

    Session-authenticated requests (OAuth2-proxy / JWT) bypass scope checks
    entirely — ``require_scope`` only applies when ``auth_via_pat=True`` is
    present in the claims dict.

    Usage::

        @router.get("/list", dependencies=[Depends(require_scope("workflow:*:read"))])
        async def list_graphs(...): ...

    Args:
        required_scope: Scope string the PAT must hold, e.g. "workflow:*:read".

    Returns:
        FastAPI dependency callable.

    Raises:
        AssertionError: At startup if required_scope is not in the registry.
    """
    assert is_valid_scope(required_scope), (
        f"Unknown scope passed to require_scope: '{required_scope}'. "
        "Register it in scope_registry.VALID_SCOPES first."
    )

    async def _check(
        request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> None:
        # Session-authenticated users bypass all scope checks
        if not current_user.get("auth_via_pat"):
            return

        active_scopes: List[str] = current_user.get("active_scopes", [])
        if _scopes_satisfy(active_scopes, required_scope):
            return

        # Rejection path
        _record_rejection(current_user, request, required_scope, active_scopes)
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have required scope: {required_scope}",
        )

    return _check


def require_any_scope(required_scopes: List[str]):
    """FastAPI dependency: grant access if the PAT satisfies ANY of the listed scopes.

    Session-authenticated requests bypass scope checks (same as require_scope).
    """
    for s in required_scopes:
        assert is_valid_scope(s), (
            f"Unknown scope in require_any_scope: '{s}'. "
            "Register it in scope_registry.VALID_SCOPES first."
        )

    async def _check(
        request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> None:
        if not current_user.get("auth_via_pat"):
            return

        active_scopes: List[str] = current_user.get("active_scopes", [])
        if any(_scopes_satisfy(active_scopes, s) for s in required_scopes):
            return

        _record_rejection(current_user, request, " | ".join(required_scopes), active_scopes)
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have any of the required scopes: {', '.join(required_scopes)}",
        )

    return _check


def _scopes_satisfy(held: List[str], required: str) -> bool:
    """Return True if the held scope list satisfies the required scope.

    Matching rules (evaluated in order):

    1. ``api:*`` in held — satisfies everything.
    2. ``api:*:read`` in held — satisfies any scope whose action is ``read``.
    3. ``api:*:write`` in held — satisfies any scope whose action is
       ``write`` or ``execute``.
    4. Exact match.
    5. Wildcard expansion: ``resource:*:action`` satisfies
       ``resource:<name>:action`` for any non-empty, non-asterisk ``<name>``.

    Args:
        held: Scopes the token holds.
        required: The scope string that must be satisfied.

    Returns:
        True if any held scope covers the required scope.
    """
    if "api:*" in held:
        return True

    # Admin read/write scopes: api:*:read covers all reads,
    # api:*:write covers all writes and executes.
    req_parts = required.split(":")
    if len(req_parts) >= 2:
        req_action = req_parts[-1]
        if req_action == "read" and "api:*:read" in held:
            return True
        if req_action in ("write", "execute") and "api:*:write" in held:
            return True

    if required in held:
        return True

    # Wildcard expansion: resource:*:action → resource:<name>:action
    if len(req_parts) == 3:
        resource, _name, action = req_parts
        wildcard = f"{resource}:*:{action}"
        if wildcard in held:
            return True
    return False


def _record_rejection(
    current_user: Dict[str, Any],
    request: Request,
    scope_required: str,
    scopes_held: List[str],
) -> None:
    """Write a ScopeRejectionLog row (best-effort; never raises).

    Args:
        current_user: Authenticated user claims dict.
        request: The incoming FastAPI request.
        scope_required: The scope that was missing.
        scopes_held: The scopes the token actually held.
    """
    try:
        from backend.models.auth.scope_rejection_log import ScopeRejectionLog
        from backend.services.database import get_db

        resource = f"{request.method} {request.url.path}"
        client_ip = request.client.host if request.client else None
        token_id = current_user.get("pat_token_id")
        token_prefix = current_user.get("pat_token_prefix")
        user_id = current_user.get("sub")

        with get_db() as db:
            entry = ScopeRejectionLog(
                token_id=token_id,
                token_prefix=token_prefix,
                user_id=user_id,
                resource=resource,
                scope_required=scope_required,
                scopes_held=json.dumps(scopes_held),
                client_ip=client_ip,
            )
            db.add(entry)
            db.commit()

        logger.warning(
            "%s Scope rejection: token=%s user=%s required=%s resource=%s",
            LOG_PREFIX,
            token_prefix,
            user_id,
            scope_required,
            resource,
        )
    except Exception as exc:
        logger.error("%s Failed to record scope rejection: %s", LOG_PREFIX, exc)
