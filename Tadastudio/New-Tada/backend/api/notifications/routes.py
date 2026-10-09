"""Notification routes for access requests and real-time updates."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.api.auth.dependencies import get_current_user, get_current_user_ws
from backend.models import (
    AccessRequest,
    AccessRequestStatus,
    User,
    Workflow,
    WorkflowMembership,
    WorkflowRole,
)
from backend.services.config import get_logger
from backend.services.database import get_db

from .manager import notification_manager

logger = get_logger(__name__)
router = APIRouter(prefix="/api/ws/notifications", tags=["notifications"])


def _get_user_id(current_user: Dict[str, Any]) -> str:
    """Return the database user identifier from auth claims."""
    return current_user.get("sub") or current_user.get("user_id") or current_user.get("email")


def _get_user_email(current_user: Dict[str, Any]) -> Optional[str]:
    """Return the user email from auth claims for display and notifications."""
    return current_user.get("email") or current_user.get("preferred_username")


def _get_owned_workflow_ids(db, user_id: str) -> List[str]:
    """Return workflow IDs owned by a user through creator or membership records."""
    owner_memberships = db.query(WorkflowMembership.workflow_id).filter(
        WorkflowMembership.user_id == user_id,
        WorkflowMembership.role == WorkflowRole.OWNER,
    ).all()
    created_workflows = db.query(Workflow.id).filter(
        Workflow.created_by_user_id == user_id,
        Workflow.is_deleted == False,  # noqa: E712
    ).all()

    return list(
        {
            row.workflow_id
            for row in owner_memberships
        }
        | {
            row.id
            for row in created_workflows
        }
    )


# ============================================================================
# Pydantic Models
# ============================================================================


class AccessRequestCreate(BaseModel):
    """Request body for creating an access request."""
    workflow_id: str
    message: Optional[str] = None
    requested_role: str = "editor"


class AccessRequestResponse(BaseModel):
    """Response model for access request."""
    id: str
    workflow_id: str
    workflow_name: Optional[str] = None
    requester_id: str
    requester_email: Optional[str] = None
    requested_role: str
    status: str
    message: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None


class AccessRequestAction(BaseModel):
    """Request body for approving/rejecting access request."""
    action: str  # "approve" or "reject"


class NotificationCountResponse(BaseModel):
    """Response model for notification count."""
    count: int
    pending_requests: int


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@router.websocket("/ws")
async def notification_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications.

    Clients connect here to receive instant notifications about:
    - Access requests (for workflow owners)
    - Request approvals/rejections (for requesters)
    """
    user = None
    try:
        user = await get_current_user_ws(websocket)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return

        user_id = user.get("user_id") or user.get("email") or user.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid user")
            return

        await notification_manager.connect(websocket, user_id)

        # Send initial pending count
        with get_db() as db:
            pending_count = _get_pending_request_count(db, user_id)
            await websocket.send_json({
                "type": "init",
                "pending_count": pending_count,
            })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                # Handle ping/pong for keepalive
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"[Notifications] WebSocket receive error: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[Notifications] WebSocket error: {e}")
    finally:
        if user:
            user_id = user.get("user_id") or user.get("email") or user.get("sub")
            if user_id:
                await notification_manager.disconnect(websocket, user_id)


# ============================================================================
# REST API Endpoints
# ============================================================================


@router.post("/access-requests", response_model=AccessRequestResponse)
async def create_access_request(
    request: AccessRequestCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Request edit access to a workflow.

    Only viewers can request access. Owners automatically get notified.
    """
    user_id = _get_user_id(current_user)
    user_email = _get_user_email(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identifier")

    with get_db() as db:
        # Check workflow exists
        workflow = db.query(Workflow).filter(Workflow.id == request.workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Check user has viewer access (can't request if they already have editor/owner)
        membership = db.query(WorkflowMembership).filter(
            WorkflowMembership.workflow_id == request.workflow_id,
            WorkflowMembership.user_id == user_id,
        ).first()

        if membership:
            role_value = membership.role.value if hasattr(membership.role, 'value') else str(membership.role)
            if role_value in ["owner", "editor"]:
                raise HTTPException(
                    status_code=400,
                    detail="You already have edit access to this workflow"
                )

        # Check for existing pending request
        existing = db.query(AccessRequest).filter(
            AccessRequest.workflow_id == request.workflow_id,
            AccessRequest.requester_id == user_id,
            AccessRequest.status == AccessRequestStatus.PENDING,
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="You already have a pending access request for this workflow"
            )

        # Create access request
        access_request = AccessRequest(
            workflow_id=request.workflow_id,
            requester_id=user_id,
            requester_email=user_email,
            requested_role=WorkflowRole.EDITOR,
            status=AccessRequestStatus.PENDING,
            message=request.message,
        )
        db.add(access_request)
        db.commit()
        db.refresh(access_request)

        # Find workflow owners to notify - need emails since WebSocket uses email as key
        owner_rows = db.query(User.email).select_from(
            WorkflowMembership
        ).join(
            User, WorkflowMembership.user_id == User.id
        ).filter(
            WorkflowMembership.workflow_id == request.workflow_id,
            WorkflowMembership.role == WorkflowRole.OWNER,
        ).all()
        owner_ids = {row.email for row in owner_rows if row.email}

        if workflow.created_by_user_id:
            creator = db.query(User.email).filter(User.id == workflow.created_by_user_id).first()
            if creator and creator.email:
                owner_ids.add(creator.email)

        # Get workflow name for notification
        workflow_name = workflow.name if hasattr(workflow, 'name') else "Unknown"

    # Send real-time notification to owners
    notification = {
        "type": "access_request",
        "request_id": str(access_request.id),
        "workflow_id": request.workflow_id,
        "workflow_name": workflow_name,
        "requester_id": user_id,
        "requester_email": user_email,
        "message": request.message,
        "created_at": access_request.created_at.isoformat() if access_request.created_at else None,
    }
    await notification_manager.broadcast_to_users(list(owner_ids), notification)

    logger.info(f"[Notifications] Access request created by {user_id} for workflow {request.workflow_id}")

    return AccessRequestResponse(
        id=str(access_request.id),
        workflow_id=access_request.workflow_id,
        workflow_name=workflow_name,
        requester_id=access_request.requester_id,
        requester_email=access_request.requester_email,
        requested_role=access_request.requested_role.value,
        status=access_request.status.value,
        message=access_request.message,
        created_at=access_request.created_at.isoformat() if access_request.created_at else "",
    )


@router.get("/access-requests", response_model=List[AccessRequestResponse])
async def get_access_requests(
    status: Optional[str] = "pending",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get access requests for workflows the current user owns."""
    user_id = _get_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identifier")

    with get_db() as db:
        owned_workflow_ids = _get_owned_workflow_ids(db, user_id)
        if not owned_workflow_ids:
            return []

        # Get access requests for owned workflows
        query = db.query(AccessRequest).filter(
            AccessRequest.workflow_id.in_(owned_workflow_ids)
        )

        if status:
            try:
                status_enum = AccessRequestStatus(status)
                query = query.filter(AccessRequest.status == status_enum)
            except ValueError:
                pass

        requests = query.order_by(AccessRequest.created_at.desc()).all()

        # Get workflow names
        workflow_names = {}
        if requests:
            workflows = db.query(Workflow).filter(
                Workflow.id.in_([r.workflow_id for r in requests])
            ).all()
            workflow_names = {w.id: w.name for w in workflows if hasattr(w, 'name')}

        return [
            AccessRequestResponse(
                id=str(r.id),
                workflow_id=r.workflow_id,
                workflow_name=workflow_names.get(r.workflow_id),
                requester_id=r.requester_id,
                requester_email=r.requester_email,
                requested_role=r.requested_role.value if r.requested_role else "editor",
                status=r.status.value if r.status else "pending",
                message=r.message,
                created_at=r.created_at.isoformat() if r.created_at else "",
                resolved_at=r.resolved_at.isoformat() if r.resolved_at else None,
                resolved_by=r.resolved_by,
            )
            for r in requests
        ]


@router.post("/access-requests/{request_id}/resolve")
async def resolve_access_request(
    request_id: str,
    action: AccessRequestAction,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Approve or reject an access request.

    Only workflow owners can resolve requests.
    """
    user_id = _get_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identifier")

    with get_db() as db:
        # Find the access request
        access_request = db.query(AccessRequest).filter(
            AccessRequest.id == request_id
        ).first()

        if not access_request:
            raise HTTPException(status_code=404, detail="Access request not found")

        workflow = db.query(Workflow).filter(Workflow.id == access_request.workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Verify user is owner of the workflow
        ownership = db.query(WorkflowMembership).filter(
            WorkflowMembership.workflow_id == access_request.workflow_id,
            WorkflowMembership.user_id == user_id,
            WorkflowMembership.role == WorkflowRole.OWNER,
        ).first()

        if not ownership and workflow.created_by_user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only workflow owners can resolve access requests"
            )

        if access_request.status != AccessRequestStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Request already {access_request.status.value}"
            )

        workflow_name = workflow.name if workflow and hasattr(workflow, 'name') else "Unknown"

        if action.action == "approve":
            # Update request status
            access_request.status = AccessRequestStatus.APPROVED
            access_request.resolved_at = datetime.utcnow()
            access_request.resolved_by = user_id

            # Add or update membership to editor
            existing_membership = db.query(WorkflowMembership).filter(
                WorkflowMembership.workflow_id == access_request.workflow_id,
                WorkflowMembership.user_id == access_request.requester_id,
            ).first()

            if existing_membership:
                existing_membership.role = WorkflowRole.EDITOR
            else:
                new_membership = WorkflowMembership(
                    workflow_id=access_request.workflow_id,
                    user_id=access_request.requester_id,
                    role=WorkflowRole.EDITOR,
                )
                db.add(new_membership)

            db.commit()

            # Notify requester
            notification = {
                "type": "access_approved",
                "request_id": str(access_request.id),
                "workflow_id": access_request.workflow_id,
                "workflow_name": workflow_name,
                "approved_by": user_id,
                "new_role": "editor",
            }
            await notification_manager.send_to_user(
                access_request.requester_email or access_request.requester_id,
                notification,
            )

            logger.info(f"[Notifications] Access request {request_id} approved by {user_id}")
            return {"status": "approved", "message": "Access granted"}

        elif action.action == "reject":
            access_request.status = AccessRequestStatus.REJECTED
            access_request.resolved_at = datetime.utcnow()
            access_request.resolved_by = user_id
            db.commit()

            # Notify requester
            notification = {
                "type": "access_rejected",
                "request_id": str(access_request.id),
                "workflow_id": access_request.workflow_id,
                "workflow_name": workflow_name,
                "rejected_by": user_id,
            }
            await notification_manager.send_to_user(
                access_request.requester_email or access_request.requester_id,
                notification,
            )

            logger.info(f"[Notifications] Access request {request_id} rejected by {user_id}")
            return {"status": "rejected", "message": "Access request rejected"}

        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")


@router.get("/count", response_model=NotificationCountResponse)
async def get_notification_count(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get count of pending notifications for the current user."""
    user_id = _get_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identifier")

    with get_db() as db:
        pending_count = _get_pending_request_count(db, user_id)

    return NotificationCountResponse(
        count=pending_count,
        pending_requests=pending_count,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _get_pending_request_count(db, user_id: str) -> int:
    """Get count of pending access requests for workflows the user owns."""
    owned_workflow_ids = _get_owned_workflow_ids(db, user_id)

    if not owned_workflow_ids:
        return 0

    # Count pending requests
    return db.query(AccessRequest).filter(
        AccessRequest.workflow_id.in_(owned_workflow_ids),
        AccessRequest.status == AccessRequestStatus.PENDING,
    ).count()
