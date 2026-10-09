"""Shared authorization framework for AgenticStudio.

Provides reusable authorization helpers to enforce object-level and
function-level access control across all API modules.

Usage:
    from backend.services.authorization import (
        verify_workflow_access,
        verify_execution_access,
        require_workflow_access,
        require_execution_access,
    )
"""

from .helpers import (
    get_user_identifier,
    verify_workflow_access,
    verify_execution_access,
    require_workflow_access,
    require_execution_access,
    require_workflow_access_by_id,
)

__all__ = [
    "get_user_identifier",
    "verify_workflow_access",
    "verify_execution_access",
    "require_workflow_access",
    "require_execution_access",
    "require_workflow_access_by_id",
]
