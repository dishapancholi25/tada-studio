"""Authorization helpers for object-level and function-level access control.

This module provides reusable functions to verify that a user has access to
specific resources (workflows, executions, datasets, etc.) before allowing
operations. These helpers are designed to be used across all API modules
to ensure consistent authorization enforcement.

ISG Finding 6430: Missing Object and Function-Level Authorization
"""

from collections.abc import Collection
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import Workflow, WorkflowMembership
from backend.models.execution.graph_execution import GraphExecution
from backend.models.workflows.graph_definition import GraphDefinition
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.graph.storage.access_control import (
    verify_workflow_access as _storage_verify_workflow_access,
)
from backend.services.graph.storage.user_resolver import resolve_user_id

logger = get_logger(__name__)

LOG_PREFIX = "[AUTHZ]"


def get_user_identifier(current_user: Dict[str, Any]) -> str:
    """Extract user identifier (sub claim) from JWT claims.

    Args:
        current_user: JWT claims dictionary from authentication

    Returns:
        User identifier (sub claim)

    Raises:
        HTTPException: 401 if token is missing user identifier
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier


def verify_workflow_access(
    user_identifier: str,
    graph_name: str,
    is_admin: bool = False,
) -> Optional[str]:
    """Verify user has access to a workflow by graph name.

    Looks up the workflow by name (scoped to user's workspace), then checks
    ownership, membership, or admin status.

    Args:
        user_identifier: User's sub claim (email or ID)
        graph_name: Name of the workflow/graph
        is_admin: Whether the user has admin privileges

    Returns:
        workflow_id if access is granted

    Raises:
        HTTPException: 403 if user does not have access
        HTTPException: 404 if workflow not found
    """
    with get_db() as db:
        # Find the graph definition by name, scoped to user's workspace
        gd = (
            db.query(GraphDefinition)
            .filter(
                GraphDefinition.name == graph_name,
                GraphDefinition.is_latest == True,
                GraphDefinition.workspace_id == user_identifier,
            )
            .first()
        )

        # If not found in user's workspace, try any workspace (for admin/membership)
        if not gd:
            gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.name == graph_name,
                    GraphDefinition.is_latest == True,
                )
                .first()
            )

        if not gd or not gd.workflow_id:
            logger.warning(
                f"{LOG_PREFIX} Workflow '{graph_name}' not found for user '{user_identifier}'"
            )
            raise HTTPException(status_code=404, detail=f"Workflow '{graph_name}' not found")

        workflow_id = gd.workflow_id

        if is_admin:
            logger.debug(f"{LOG_PREFIX} Admin access granted for graph '{graph_name}'")
            return workflow_id

        # Check access via existing access control (ownership or membership)
        if not _storage_verify_workflow_access(db, workflow_id, user_identifier, is_admin=False):
            logger.warning(
                f"{LOG_PREFIX} Access denied: user '{user_identifier}' -> workflow '{graph_name}'"
            )
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this workflow",
            )

        return workflow_id


def verify_workflow_access_by_id(
    user_identifier: str,
    workflow_id: str,
    is_admin: bool = False,
) -> bool:
    """Verify user has access to a workflow by workflow ID.

    Args:
        user_identifier: User's sub claim
        workflow_id: Workflow UUID
        is_admin: Whether the user has admin privileges

    Returns:
        True if access is granted

    Raises:
        HTTPException: 403 if user does not have access
        HTTPException: 404 if workflow not found
    """
    if is_admin:
        return True

    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if not _storage_verify_workflow_access(db, workflow_id, user_identifier, is_admin=False):
            logger.warning(
                f"{LOG_PREFIX} Access denied: user '{user_identifier}' -> workflow '{workflow_id}'"
            )
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this workflow",
            )

    return True


def filter_accessible_workflow_ids(
    user_identifier: str,
    workflow_ids: Collection[str],
    is_admin: bool = False,
) -> set[str]:
    """Return the subset of workflow IDs the user can access (batch, non-raising).

    Access means ownership or membership. Unknown workflow IDs are excluded.
    Use this to filter listings; use verify_workflow_access_by_id when a single
    denied ID should produce an HTTP error instead.

    Args:
        user_identifier: User's sub claim or email
        workflow_ids: Candidate workflow UUIDs (falsy entries are ignored)
        is_admin: Whether the user has admin privileges

    Returns:
        Set of workflow IDs from the input that the user may access
    """
    candidates = {workflow_id for workflow_id in workflow_ids if workflow_id}
    if not candidates:
        return set()
    if is_admin:
        return candidates

    with get_db() as db:
        user_id = resolve_user_id(user_identifier, db)
        if not user_id:
            logger.warning(
                f"{LOG_PREFIX} Could not resolve user for batch access check: {user_identifier}"
            )
            return set()

        owned_rows = (
            db.query(Workflow.id)
            .filter(
                Workflow.id.in_(candidates),
                Workflow.created_by_user_id == user_id,
            )
            .all()
        )
        member_rows = (
            db.query(WorkflowMembership.workflow_id)
            .filter(
                WorkflowMembership.workflow_id.in_(candidates),
                WorkflowMembership.user_id == user_id,
            )
            .all()
        )

    return {row[0] for row in owned_rows} | {row[0] for row in member_rows}


def verify_execution_access(
    user_identifier: str,
    execution_id: str,
    is_admin: bool = False,
) -> Optional[GraphExecution]:
    """Verify user has access to an execution.

    An execution is accessible if:
    - The user is an admin, OR
    - The user initiated the execution (user_id matches), OR
    - The user has access to the workflow that the execution belongs to

    Args:
        user_identifier: User's sub claim
        execution_id: Execution UUID or websocket execution ID
        is_admin: Whether the user has admin privileges

    Returns:
        The GraphExecution object if access is granted

    Raises:
        HTTPException: 403 if user does not have access
        HTTPException: 404 if execution not found
    """
    with get_db() as db:
        # Try by primary key first, then by websocket_execution_id
        execution = db.query(GraphExecution).filter(
            GraphExecution.id == execution_id
        ).first()

        if not execution:
            execution = db.query(GraphExecution).filter(
                GraphExecution.websocket_execution_id == execution_id
            ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        if is_admin:
            logger.debug(f"{LOG_PREFIX} Admin access granted for execution '{execution_id}'")
            return execution

        # Check if user initiated this execution
        resolved_user_id = resolve_user_id(user_identifier, db)

        if execution.user_id and resolved_user_id:
            if execution.user_id == resolved_user_id or execution.user_id == user_identifier:
                return execution

        # Fallback: check if user has access to the parent workflow
        if execution.workflow_id:
            if _storage_verify_workflow_access(
                db, execution.workflow_id, user_identifier, is_admin=False
            ):
                return execution

        logger.warning(
            f"{LOG_PREFIX} Access denied: user '{user_identifier}' -> execution '{execution_id}'"
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this execution",
        )


def require_workflow_access(
    current_user: Dict[str, Any],
    graph_name: str,
) -> Optional[str]:
    """Convenience function combining user extraction and workflow access check.

    Args:
        current_user: JWT claims dictionary
        graph_name: Name of the workflow

    Returns:
        workflow_id if access is granted

    Raises:
        HTTPException: 401/403/404 on failure
    """
    user_identifier = get_user_identifier(current_user)
    is_admin = current_user.get("is_admin", False)
    return verify_workflow_access(user_identifier, graph_name, is_admin)


def require_execution_access(
    current_user: Dict[str, Any],
    execution_id: str,
) -> Optional[GraphExecution]:
    """Convenience function combining user extraction and execution access check.

    Args:
        current_user: JWT claims dictionary
        execution_id: Execution UUID

    Returns:
        GraphExecution object if access is granted

    Raises:
        HTTPException: 401/403/404 on failure
    """
    user_identifier = get_user_identifier(current_user)
    is_admin = current_user.get("is_admin", False)
    return verify_execution_access(user_identifier, execution_id, is_admin)


def require_workflow_access_by_id(
    current_user: Dict[str, Any],
    workflow_id: str,
) -> bool:
    """Convenience function combining user extraction and workflow ID access check.

    Args:
        current_user: JWT claims dictionary
        workflow_id: Workflow UUID

    Returns:
        True if access is granted

    Raises:
        HTTPException: 401/403/404 on failure
    """
    user_identifier = get_user_identifier(current_user)
    is_admin = current_user.get("is_admin", False)
    return verify_workflow_access_by_id(user_identifier, workflow_id, is_admin)
