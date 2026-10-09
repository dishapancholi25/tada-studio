"""
Access control operations for graph storage.

This module handles permission checking and access verification
for workflows and graphs.
"""

from typing import Optional

from sqlalchemy.orm import Session
from backend.models import Workflow, WorkflowMembership
from backend.services.config import get_logger

from .user_resolver import resolve_user_id


logger = get_logger(__name__)


def verify_workflow_access(db: Session, workflow_id: str, user_identifier: str, is_admin: bool = False) -> bool:
    """
    Verify user has access to a workflow.

    Checks admin privileges, direct ownership, and membership-based access.

    Args:
        db: Database session
        workflow_id: Workflow UUID
        user_identifier: Email (for AIPE users) or sub (for legacy Azure AD users)
        is_admin: Whether the user has admin privileges

    Returns:
        True if user has access, False otherwise

    Complexity: 4 (reduced from previous implementation)
    """
    # Admin users have access to all workflows
    if is_admin:
        logger.debug(
            f"[GRAPH-STORAGE] Access granted via admin privileges: {user_identifier} -> {workflow_id}"
        )
        return True

    # Resolve user identifier to user_id
    user_id = resolve_user_id(user_identifier, db)
    if not user_id:
        logger.warning(
            f"[GRAPH-STORAGE] Could not resolve user for access check: {user_identifier}"
        )
        return False

    # Check direct ownership
    if check_workflow_ownership(db, workflow_id, user_id):
        logger.debug(
            f"[GRAPH-STORAGE] Access granted via ownership: {user_identifier} -> {workflow_id}"
        )
        return True

    # Check membership
    if check_workflow_membership(db, workflow_id, user_id):
        logger.debug(
            f"[GRAPH-STORAGE] Access granted via membership: {user_identifier} -> {workflow_id}"
        )
        return True

    logger.warning(f"[GRAPH-STORAGE] Access denied: {user_identifier} -> {workflow_id}")
    return False


def check_workflow_ownership(db: Session, workflow_id: str, user_id: str) -> bool:
    """
    Check if a user owns a workflow.

    Args:
        db: Database session
        workflow_id: Workflow UUID
        user_id: User ID

    Returns:
        True if user owns the workflow, False otherwise
    """
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.created_by_user_id == user_id)
        .first()
    )

    return workflow is not None


def check_workflow_membership(db: Session, workflow_id: str, user_id: str) -> bool:
    """
    Check if a user is a member of a workflow.

    Args:
        db: Database session
        workflow_id: Workflow UUID
        user_id: User ID

    Returns:
        True if user is a member, False otherwise
    """
    membership = (
        db.query(WorkflowMembership)
        .filter(
            WorkflowMembership.workflow_id == workflow_id,
            WorkflowMembership.user_id == user_id,
        )
        .first()
    )

    return membership is not None


def get_user_workflow_role(
    db: Session, workflow_id: str, user_id: str
) -> Optional[str]:
    """
    Get the role of a user in a workflow.

    Args:
        db: Database session
        workflow_id: Workflow UUID
        user_id: User ID

    Returns:
        Role string if user is a member/creator, None otherwise
    """
    membership = (
        db.query(WorkflowMembership)
        .filter(
            WorkflowMembership.workflow_id == workflow_id,
            WorkflowMembership.user_id == user_id,
        )
        .first()
    )

    if membership:
        from backend.models import WorkflowRole

        return (
            membership.role.value
            if isinstance(membership.role, WorkflowRole)
            else str(membership.role)
        )

    # Fallback: check if user is the workflow creator (handles legacy workflows
    # that may not have a WorkflowMembership row for the creator)
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.created_by_user_id == user_id)
        .first()
    )
    if workflow:
        logger.debug(
            f"[GRAPH-STORAGE] User '{user_id}' is workflow creator, returning 'owner' role"
        )
        return "owner"

    return None
