"""
Workflow management operations for graph storage.

This module handles workflow creation, membership management,
and workflow-related database operations.
"""

import secrets
from typing import Optional

from sqlalchemy.orm import Session
from backend.models.workflow import GraphData
from backend.models import User, Workflow, WorkflowMembership, WorkflowRole
from backend.services.config import get_logger


logger = get_logger(__name__)


def get_or_create_workflow(
    db: Session, graph: GraphData, user_identifier: Optional[str]
) -> Optional[Workflow]:
    """
    Ensure a workflow container exists for the given graph and user.

    This function finds an existing workflow or creates a new one, ensuring
    the creator is properly registered as an owner.

    Args:
        db: Database session
        graph: Graph data containing name and description
        user_identifier: Email (for AIPE users) or user_id (legacy)

    Returns:
        Workflow object if successful, None if user not found

    Complexity: 8 (reduced from previous complexity)
    """
    if not user_identifier:
        return None

    # Resolve user identifier to user_id
    user_id = _resolve_user_for_workflow(db, user_identifier)
    if not user_id:
        logger.warning(f"[GRAPH-STORAGE] User not found: {user_identifier}")
        return None

    # 1. If graph already has a workflow_id, look it up directly
    #    (preserves existing memberships when shared users save)
    workflow = None
    if getattr(graph, "workflow_id", None):
        workflow = _find_workflow_by_id(db, graph.workflow_id)

    # 2. Fall back to name+creator lookup (for new graphs without workflow_id)
    if not workflow:
        workflow = _find_existing_workflow(db, graph.name, user_id)

    # 3. Check if user has membership access (shared workflows)
    if not workflow:
        workflow = _find_workflow_by_membership(db, graph.name, user_id)

    # 4. Create new workflow only if nothing found
    if not workflow:
        workflow = _create_new_workflow(db, graph, user_id)

    # Update workflow description if provided
    _update_workflow_description(workflow, graph.description)

    # Ensure saving user has a membership (no-op if they already have one)
    _ensure_workflow_membership(db, workflow.id, user_id)

    return workflow


def _resolve_user_for_workflow(db: Session, user_identifier: str) -> Optional[str]:
    """
    Resolve user identifier to user_id for workflow operations.

    Args:
        db: Database session
        user_identifier: Email or user_id

    Returns:
        User ID if found, None otherwise
    """
    # Try to find user by ID first
    user = db.query(User).filter(User.id == user_identifier).first()
    if user:
        return user.id

    # Try finding user by email
    user = db.query(User).filter(User.email == user_identifier).first()
    if user:
        return user.id

    return None


def _find_workflow_by_id(db: Session, workflow_id: str) -> Optional[Workflow]:
    """
    Find an existing workflow by its ID.

    Returns the workflow if it exists and is not soft-deleted.

    Args:
        db: Database session
        workflow_id: Workflow UUID

    Returns:
        Workflow if found and active, None otherwise
    """
    return (
        db.query(Workflow)
        .filter(
            Workflow.id == workflow_id,
            ~Workflow.is_deleted,
        )
        .first()
    )


def _find_existing_workflow(
    db: Session, graph_name: str, user_id: str
) -> Optional[Workflow]:
    """
    Find an existing workflow by name and creator.

    Returns the first non-deleted workflow matching the name and creator.
    The unique index ``uq_workflow_name_user_active`` guarantees at most
    one active row per (name, created_by_user_id).

    Args:
        db: Database session
        graph_name: Name of the graph/workflow
        user_id: User ID of the creator

    Returns:
        Workflow if found, None otherwise
    """
    return (
        db.query(Workflow)
        .filter(
            Workflow.name == graph_name,
            Workflow.created_by_user_id == user_id,
            ~Workflow.is_deleted,
        )
        .first()
    )


def _find_workflow_by_membership(
    db: Session, graph_name: str, user_id: str
) -> Optional[Workflow]:
    """
    Find a workflow by name that the user has membership access to.

    Used as a fallback when the user didn't create the workflow
    but has access via sharing.

    Args:
        db: Database session
        graph_name: Name of the graph/workflow
        user_id: User ID of the member

    Returns:
        Workflow if found, None otherwise
    """
    return (
        db.query(Workflow)
        .join(WorkflowMembership, WorkflowMembership.workflow_id == Workflow.id)
        .filter(
            Workflow.name == graph_name,
            WorkflowMembership.user_id == user_id,
            ~Workflow.is_deleted,
        )
        .first()
    )


def _create_new_workflow(db: Session, graph: GraphData, user_id: str) -> Workflow:
    """
    Create a new workflow.

    If a concurrent request already inserted a row with the same
    (name, created_by_user_id) the unique index will reject the INSERT.
    In that case we roll back the failed flush and return the existing row.

    Args:
        db: Database session
        graph: Graph data
        user_id: User ID of the creator

    Returns:
        Newly created (or existing) Workflow object
    """
    from sqlalchemy.exc import IntegrityError

    workflow = Workflow(
        name=graph.name,
        description=graph.description,
        created_by_user_id=user_id,
        latest_version=1,
        http_trigger_token="wf_" + secrets.token_urlsafe(32),
    )
    try:
        db.add(workflow)
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info(
            f"[GRAPH-STORAGE] Duplicate workflow detected for '{graph.name}', reusing existing"
        )
        existing = (
            db.query(Workflow)
            .filter(
                Workflow.name == graph.name,
                Workflow.created_by_user_id == user_id,
                ~Workflow.is_deleted,
            )
            .first()
        )
        if existing:
            return existing
        raise

    logger.info(
        f"[GRAPH-STORAGE] Created new workflow: {graph.name} (id={workflow.id})"
    )

    return workflow


def _update_workflow_description(
    workflow: Workflow, description: Optional[str]
) -> None:
    """
    Update workflow description if provided and different.

    Args:
        workflow: Workflow object to update
        description: New description (if provided)
    """
    if description and workflow.description != description:
        workflow.description = description
        logger.debug(
            f"[GRAPH-STORAGE] Updated workflow description for: {workflow.name}"
        )


def _ensure_workflow_membership(db: Session, workflow_id: str, user_id: str) -> None:
    """
    Ensure the user is registered as an owner of the workflow.

    Args:
        db: Database session
        workflow_id: Workflow ID
        user_id: User ID
    """
    # Check if membership already exists
    membership = (
        db.query(WorkflowMembership)
        .filter(
            WorkflowMembership.workflow_id == workflow_id,
            WorkflowMembership.user_id == user_id,
        )
        .first()
    )

    if not membership:
        # Create owner membership
        membership = WorkflowMembership(
            workflow_id=workflow_id, user_id=user_id, role=WorkflowRole.OWNER
        )
        db.add(membership)
        logger.debug(
            f"[GRAPH-STORAGE] Created owner membership for workflow: {workflow_id}"
        )
