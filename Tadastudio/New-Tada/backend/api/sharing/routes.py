"""Workflow sharing API routes for managing workflow memberships."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from backend.models import User, Workflow, WorkflowMembership
from backend.models.enums import WorkflowRole
from backend.services.database import get_db
from backend.services.graph.storage.user_resolver import resolve_user_id

from ..auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_scope
from ..notifications.manager import notification_manager
from .models import (
    AddMemberRequest,
    UpdateMemberRoleRequest,
    WorkflowMemberResponse,
    WorkflowMembersResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/sharing", tags=["sharing"], dependencies=[Depends(require_active_user)]
)


def _get_owned_workflow(db, workflow_id: str, current_user_id: str) -> Workflow:
    """Get workflow and verify the current user is the owner."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.is_deleted.is_(False))
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.created_by_user_id != current_user_id:
        raise HTTPException(
            status_code=403, detail="Only the workflow owner can manage sharing"
        )

    return workflow


@router.get("/{workflow_id}/members", response_model=WorkflowMembersResponse, dependencies=[Depends(require_scope("workflow:*:read"))])
def get_workflow_members(workflow_id: str, current_user=Depends(get_current_user)):
    """List all members of a workflow, including the owner.

    Any member (owner, editor, viewer) can view the member list.
    """
    with get_db() as db:
        user_id = resolve_user_id(current_user.get("sub", ""), db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Could not resolve user")

        # Allow any member to view the member list (not just the owner)
        workflow = (
            db.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.is_deleted.is_(False))
            .first()
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Check user is owner or a member
        is_owner = workflow.created_by_user_id == user_id
        if not is_owner:
            membership = (
                db.query(WorkflowMembership)
                .filter(
                    WorkflowMembership.workflow_id == workflow_id,
                    WorkflowMembership.user_id == user_id,
                )
                .first()
            )
            if not membership:
                raise HTTPException(status_code=403, detail="You do not have access to this workflow")

        # Get owner info
        owner = db.query(User).filter(User.id == workflow.created_by_user_id).first()
        members = (
            [
                WorkflowMemberResponse(
                    user_id=owner.id,
                    user_name=owner.name,
                    user_email=owner.email,
                    role="owner",
                    is_owner=True,
                )
            ]
            if owner
            else []
        )

        # Get all memberships
        memberships = (
            db.query(WorkflowMembership, User)
            .join(User, WorkflowMembership.user_id == User.id)
            .filter(WorkflowMembership.workflow_id == workflow_id)
            .all()
        )
        for membership, user in memberships:
            role_value = (
                membership.role.value
                if isinstance(membership.role, WorkflowRole)
                else str(membership.role)
            )
            # Skip if this is the owner (already included above)
            if user.id == workflow.created_by_user_id:
                continue
            members.append(
                WorkflowMemberResponse(
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    role=role_value,
                    is_owner=False,
                )
            )

        return WorkflowMembersResponse(members=members, workflow_id=workflow_id, can_manage=is_owner)


@router.post("/{workflow_id}/members", dependencies=[Depends(require_scope("workflow:*:write"))])
async def add_workflow_member(
    workflow_id: str, req: AddMemberRequest, current_user=Depends(get_current_user)
):
    """Add a user as a member of a workflow."""
    with get_db() as db:
        user_id = resolve_user_id(current_user.get("sub", ""), db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Could not resolve user")

        workflow = _get_owned_workflow(db, workflow_id, user_id)

        # Prevent sharing with self
        if req.user_id == user_id:
            raise HTTPException(
                status_code=400, detail="Cannot share a workflow with yourself"
            )

        # Verify target user exists
        target_user = db.query(User).filter(User.id == req.user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create membership
        membership = WorkflowMembership(
            workflow_id=workflow_id,
            user_id=req.user_id,
            role=WorkflowRole[req.role.upper()],
        )
        try:
            db.add(membership)
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409, detail="User is already a member of this workflow"
            )

    # Notify the target user via WebSocket (non-blocking, after DB commit)
    target_email = target_user.email or req.user_id
    sharer_email = current_user.get("email", "Someone")
    await notification_manager.send_to_user(
        target_email,
        {
            "type": "workflow_shared",
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "shared_by": sharer_email,
            "role": req.role,
        },
    )

    return {
        "success": True,
        "message": f"Added {target_user.email or target_user.name} as {req.role}",
    }


@router.delete("/{workflow_id}/members/{member_user_id}", dependencies=[Depends(require_scope("workflow:*:write"))])
def remove_workflow_member(
    workflow_id: str, member_user_id: str, current_user=Depends(get_current_user)
):
    """Remove a member from a workflow."""
    with get_db() as db:
        user_id = resolve_user_id(current_user.get("sub", ""), db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Could not resolve user")

        workflow = _get_owned_workflow(db, workflow_id, user_id)

        # Prevent removing the owner
        if member_user_id == workflow.created_by_user_id:
            raise HTTPException(
                status_code=400, detail="Cannot remove the workflow owner"
            )

        membership = (
            db.query(WorkflowMembership)
            .filter(
                WorkflowMembership.workflow_id == workflow_id,
                WorkflowMembership.user_id == member_user_id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(status_code=404, detail="Member not found")

        db.delete(membership)

        return {"success": True, "message": "Member removed"}


@router.put("/{workflow_id}/members/{member_user_id}/role", dependencies=[Depends(require_scope("workflow:*:write"))])
def update_workflow_member_role(
    workflow_id: str,
    member_user_id: str,
    req: UpdateMemberRoleRequest,
    current_user=Depends(get_current_user),
):
    """Update a member's role in a workflow."""
    with get_db() as db:
        user_id = resolve_user_id(current_user.get("sub", ""), db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Could not resolve user")

        workflow = _get_owned_workflow(db, workflow_id, user_id)

        # Prevent changing owner's role
        if member_user_id == workflow.created_by_user_id:
            raise HTTPException(
                status_code=400, detail="Cannot change the owner's role"
            )

        membership = (
            db.query(WorkflowMembership)
            .filter(
                WorkflowMembership.workflow_id == workflow_id,
                WorkflowMembership.user_id == member_user_id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(status_code=404, detail="Member not found")

        membership.role = WorkflowRole[req.role.upper()]

        return {"success": True, "message": f"Role updated to {req.role}"}
