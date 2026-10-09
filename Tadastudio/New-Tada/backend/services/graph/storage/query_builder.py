"""
Query builder utilities for graph storage operations.

This module provides reusable query building functions to reduce
complexity and duplication in storage operations.
"""

from typing import List, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.models import GraphDefinition, User, WorkflowMembership
from backend.services.config import get_logger

from .user_resolver import resolve_user_id


logger = get_logger(__name__)


def get_accessible_workflow_ids(
    user_identifier: str, db: Session
) -> Tuple[List[str], str]:
    """
    Get workflow IDs that a user can access and the resolved user ID.

    Args:
        user_identifier: Email or sub of the user
        db: Database session

    Returns:
        Tuple of (list of workflow IDs, resolved user ID)
    """
    # Resolve user identifier to user_id
    resolved_user_id = resolve_user_id(user_identifier, db)
    if not resolved_user_id:
        logger.warning(
            f"[GRAPH-STORAGE] Could not resolve user for access check: {user_identifier}"
        )
        return ([], None)

    # Get all workflows where user is a member
    memberships = (
        db.query(WorkflowMembership.workflow_id)
        .filter(WorkflowMembership.user_id == resolved_user_id)
        .all()
    )

    accessible_workflow_ids = [m.workflow_id for m in memberships if m.workflow_id]

    logger.debug(
        f"[GRAPH-STORAGE] User {user_identifier} has access to {len(accessible_workflow_ids)} workflows"
    )

    return (accessible_workflow_ids, resolved_user_id)


def build_workspace_access_filter(
    workspace_id: str, user_identifier: str, db: Session, resolve_user: bool = True
):
    """
    Build SQLAlchemy filter conditions for workspace access.

    This creates filter conditions that check both direct workspace ownership
    and workflow membership access.

    Args:
        workspace_id: Workspace identifier
        user_identifier: User identifier (email or sub)
        db: Database session
        resolve_user: Whether to resolve user identifier to user ID

    Returns:
        SQLAlchemy filter condition (for use in query.filter())
    """
    conditions = []

    # Direct workspace access
    if workspace_id:
        conditions.append(GraphDefinition.workspace_id == workspace_id)

    # Resolve user and add membership-based access
    if user_identifier:
        if resolve_user:
            resolved_user_id = resolve_user_id(user_identifier, db)
            if resolved_user_id:
                # Add alternative identifier conditions
                if resolved_user_id != user_identifier:
                    conditions.append(GraphDefinition.workspace_id == resolved_user_id)
        else:
            resolved_user_id = user_identifier

        # Get accessible workflows via membership
        accessible_workflow_ids, _ = get_accessible_workflow_ids(user_identifier, db)
        if accessible_workflow_ids:
            conditions.append(GraphDefinition.workflow_id.in_(accessible_workflow_ids))

    # Combine conditions with OR
    if len(conditions) > 1:
        return or_(*conditions)
    elif len(conditions) == 1:
        return conditions[0]
    else:
        # No conditions - return a condition that's always false
        return GraphDefinition.id.is_(None)


def get_workspace_membership_info(
    workspace_id: str, db: Session
) -> Tuple[List[str], dict]:
    """
    Get membership information for a workspace.

    Args:
        workspace_id: Workspace identifier (email or user ID)
        db: Database session

    Returns:
        Tuple of (accessible workflow IDs, membership role map)
    """
    # Resolve email to user_id if needed
    resolved_user_id = workspace_id
    user = (
        db.query(User)
        .filter(or_(User.id == workspace_id, User.email == workspace_id))
        .first()
    )
    if user:
        resolved_user_id = user.id

    # Get memberships
    memberships = (
        db.query(WorkflowMembership.workflow_id, WorkflowMembership.role)
        .filter(WorkflowMembership.user_id == resolved_user_id)
        .all()
    )

    accessible_workflow_ids = [m.workflow_id for m in memberships if m.workflow_id]

    # Build role mapping
    from backend.models import WorkflowRole

    membership_roles = {}
    for m in memberships:
        if m.workflow_id:
            role_value = (
                m.role.value if isinstance(m.role, WorkflowRole) else str(m.role)
            )
            membership_roles[m.workflow_id] = role_value

    return (accessible_workflow_ids, membership_roles)
