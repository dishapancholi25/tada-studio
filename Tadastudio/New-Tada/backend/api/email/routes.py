"""
API routes for email checkpoint functionality.

DISABLED: Email checkpoint endpoints are temporarily disabled pending security review.
Specifically: sender validation and authorization checks for webhook callbacks.

All endpoints will return 503 Service Unavailable. Users must use Manual checkpoints.
"""

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.api.auth.dependencies import require_active_user
from backend.models import GraphExecution, NodeExecution
from backend.services.authorization import get_user_identifier, require_execution_access
from backend.services.config import get_logger
from backend.services.email import get_email_manager

from .dependencies import get_db
from .handlers import EmailWebhookHandler
from .models import (
    CheckpointStatusResponse,
    CreateInboxRequest,
    CreateInboxResponse,
    DeleteInboxResponse,
    RegisterWebhookRequest,
    RegisterWebhookResponse,
    SendEmailRequest,
    SendEmailResponse,
    UnregisterWebhookResponse,
    WebhookCallbackResponse,
)

logger = get_logger("email_api")
ActiveUser = Annotated[dict[str, Any], Depends(require_active_user)]

# Create router
router = APIRouter(
    prefix="/api/email",
    tags=["email_checkpoint"],
    # DISABLED: Email checkpoint endpoints temporarily unavailable
    deprecated=True,
)


def _require_email_resource_owner(
    owner_id: str | None,
    current_user: dict[str, Any],
    resource_type: str,
) -> None:
    """Require owner access for email resources; unknown legacy records are admin-only."""
    if current_user.get("is_admin"):
        return

    caller_id = get_user_identifier(current_user)
    if owner_id is None or owner_id != caller_id:
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized for this {resource_type}",
        )


@router.post("/inbox/create", response_model=CreateInboxResponse)
async def create_email_inbox(
    request: CreateInboxRequest,
    current_user: ActiveUser,
) -> CreateInboxResponse:
    """
    Create a temporary email inbox for receiving checkpoint responses.

    Args:
        request: Inbox creation request

    Returns:
        Inbox details including ID and email address
    """
    try:
        email_manager = get_email_manager()
        owner_id = get_user_identifier(current_user)
        inbox = await email_manager.create_inbox(
            request.expires_in_minutes,
            owner_id=owner_id,
        )

        logger.info(
            f"Created email inbox: {inbox.email_address} (ID: {inbox.inbox_id})"
        )

        return CreateInboxResponse(
            inbox_id=inbox.inbox_id,
            email_address=inbox.email_address,
            expires_at=inbox.expires_at.isoformat() if inbox.expires_at else None,
            metadata=request.metadata,
        )
    except Exception as e:
        logger.error(f"Failed to create email inbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/inbox/{inbox_id}", response_model=DeleteInboxResponse)
async def delete_email_inbox(
    inbox_id: str,
    current_user: ActiveUser,
) -> DeleteInboxResponse:
    """
    Delete an email inbox.

    Args:
        inbox_id: The ID of the inbox to delete

    Returns:
        Success status
    """
    try:
        email_manager = get_email_manager()
        _require_email_resource_owner(
            email_manager.get_inbox_owner(inbox_id),
            current_user,
            "inbox",
        )
        success = await email_manager.delete_inbox(inbox_id)

        if success:
            logger.info(f"Deleted email inbox: {inbox_id}")
        else:
            logger.warning(f"Failed to delete email inbox: {inbox_id}")

        return DeleteInboxResponse(success=success)
    except Exception as e:
        logger.error(f"Failed to delete email inbox {inbox_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=SendEmailResponse)
async def send_checkpoint_email(
    request: SendEmailRequest,
    current_user: ActiveUser,
) -> SendEmailResponse:
    """
    Send an email from a checkpoint node.

    Args:
        request: Email sending request

    Returns:
        Send status and result
    """
    try:
        email_manager = get_email_manager()

        # Check if sending from specific inbox
        if request.inbox_id and hasattr(
            email_manager.provider, "send_email_from_inbox"
        ):
            _require_email_resource_owner(
                email_manager.get_inbox_owner(request.inbox_id),
                current_user,
                "inbox",
            )
            result = await email_manager.provider.send_email_from_inbox(
                inbox_id=request.inbox_id,
                to_address=request.recipient,
                subject=request.subject,
                body=request.body,
                html_body=request.html_body,
            )
        else:
            result = await email_manager.send_email(
                from_address="noreply@nexusagent.ai",
                to_address=request.recipient,
                subject=request.subject,
                body=request.body,
                html_body=request.html_body,
                reply_to=request.reply_to,
            )

        logger.info(f"Sent checkpoint email to {request.recipient}")
        return SendEmailResponse(success=True, result=result)
    except Exception as e:
        logger.error(f"Failed to send checkpoint email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/callback", response_model=WebhookCallbackResponse)
async def email_webhook_callback(
    request: Request, db: Session = Depends(get_db)
) -> WebhookCallbackResponse:
    """
    Webhook callback endpoint for email receipt notifications.

    This endpoint is called by email providers when an email is received.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Success status
    """
    try:
        # Parse webhook payload (form data for Mailgun)
        form_data = await request.form()
        payload = {key: value for key, value in form_data.items()}

        # Handle the webhook
        result = await EmailWebhookHandler.handle_mailgun_webhook(payload, db)

        return WebhookCallbackResponse(**result)

    except Exception as e:
        logger.error(f"Failed to process email webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/register", response_model=RegisterWebhookResponse)
async def register_email_webhook(
    request: RegisterWebhookRequest,
    current_user: ActiveUser,
) -> RegisterWebhookResponse:
    """
    Register a webhook for email notifications.

    Args:
        request: Webhook registration request

    Returns:
        Webhook registration details
    """
    try:
        email_manager = get_email_manager()
        owner_id = get_user_identifier(current_user)
        _require_email_resource_owner(
            email_manager.get_inbox_owner(request.inbox_id),
            current_user,
            "inbox",
        )

        # Construct webhook URL
        base_url = request.webhook_base_url or os.getenv(
            "EMAIL_WEBHOOK_BASE_URL", "http://localhost:8000"
        )
        webhook_url = f"{base_url}/api/email/webhooks/callback"

        # Register webhook
        webhook = await email_manager.register_webhook(
            inbox_id=request.inbox_id,
            webhook_url=webhook_url,
            event_types=["NEW_EMAIL"],
            owner_id=owner_id,
        )

        logger.info(
            f"Registered email webhook for inbox {request.inbox_id}: {webhook_url}"
        )

        return RegisterWebhookResponse(
            webhook_id=webhook.webhook_id,
            inbox_id=request.inbox_id,
            webhook_url=webhook_url,
            event_types=webhook.event_types,
        )
    except Exception as e:
        logger.error(f"Failed to register email webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}", response_model=UnregisterWebhookResponse)
async def unregister_email_webhook(
    webhook_id: str,
    current_user: ActiveUser,
) -> UnregisterWebhookResponse:
    """
    Unregister an email webhook.

    Args:
        webhook_id: The webhook ID to unregister

    Returns:
        Success status
    """
    try:
        email_manager = get_email_manager()
        _require_email_resource_owner(
            email_manager.get_webhook_owner(webhook_id),
            current_user,
            "webhook",
        )
        success = await email_manager.unregister_webhook(webhook_id)

        if success:
            logger.info(f"Unregistered email webhook: {webhook_id}")
        else:
            logger.warning(f"Failed to unregister email webhook: {webhook_id}")

        return UnregisterWebhookResponse(success=success)
    except Exception as e:
        logger.error(f"Failed to unregister email webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inbox/{inbox_id}/emails")
async def get_inbox_emails(
    inbox_id: str,
    current_user: ActiveUser,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Get emails from an inbox (for debugging/monitoring).

    Args:
        inbox_id: The inbox ID
        limit: Maximum number of emails to retrieve

    Returns:
        List of emails in the inbox
    """
    try:
        email_manager = get_email_manager()
        _require_email_resource_owner(
            email_manager.get_inbox_owner(inbox_id),
            current_user,
            "inbox",
        )
        emails = await email_manager.get_emails(inbox_id, limit)

        return {
            "emails": [
                {
                    "id": email.id,
                    "from": email.from_address,
                    "to": email.to_addresses,
                    "subject": email.subject,
                    "body": email.body,
                    "received_at": email.received_at.isoformat()
                    if email.received_at
                    else None,
                }
                for email in emails
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get emails from inbox {inbox_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/checkpoint/{execution_id}/status", response_model=CheckpointStatusResponse
)
async def get_email_checkpoint_status(
    execution_id: str,
    current_user: ActiveUser,
    db: Session = Depends(get_db),
) -> CheckpointStatusResponse:
    """
    Get the status of an email checkpoint.

    Args:
        execution_id: The workflow execution ID
        db: Database session

    Returns:
        Email checkpoint status and details
    """
    try:
        require_execution_access(current_user, execution_id)

        # Find the execution
        execution = (
            db.query(GraphExecution)
            .filter(GraphExecution.websocket_execution_id == execution_id)
            .first()
        )

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Find email checkpoint nodes
        email_checkpoints = []
        node_executions = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == execution.id,
                NodeExecution.node_type == "CHECKPOINT",
            )
            .all()
        )

        for node_exec in node_executions:
            metadata = node_exec.node_metadata or {}
            if metadata.get("await_mode") == "email":
                email_checkpoints.append(
                    {
                        "node_id": node_exec.node_id,
                        "node_name": node_exec.node_name,
                        "status": node_exec.status,
                        "inbox_id": metadata.get("inbox_id"),
                        "reply_to_address": metadata.get("reply_to_address"),
                        "email_sent": metadata.get("email_sent", False),
                        "email_received": node_exec.status == "completed",
                        "start_time": node_exec.start_time.isoformat()
                        if node_exec.start_time
                        else None,
                        "end_time": node_exec.end_time.isoformat()
                        if node_exec.end_time
                        else None,
                    }
                )

        return CheckpointStatusResponse(
            execution_id=execution_id,
            has_email_checkpoints=len(email_checkpoints) > 0,
            email_checkpoints=email_checkpoints,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email checkpoint status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
