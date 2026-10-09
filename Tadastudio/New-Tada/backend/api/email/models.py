"""
Pydantic models for email API requests and responses.

Defines request and response models for FastAPI endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateInboxRequest(BaseModel):
    """Request model for creating an email inbox."""

    expires_in_minutes: int = Field(
        default=60, ge=1, le=1440, description="Inbox expiry time in minutes"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class CreateInboxResponse(BaseModel):
    """Response model for inbox creation."""

    inbox_id: str = Field(..., description="Created inbox ID")
    email_address: str = Field(..., description="Email address for this inbox")
    expires_at: Optional[str] = Field(None, description="Expiry timestamp (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Inbox metadata")


class DeleteInboxResponse(BaseModel):
    """Response model for inbox deletion."""

    success: bool = Field(..., description="Whether deletion was successful")


class SendEmailRequest(BaseModel):
    """Request model for sending emails."""

    recipient: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text email body")
    html_body: Optional[str] = Field(None, description="Optional HTML body")
    reply_to: Optional[str] = Field(None, description="Optional reply-to address")
    inbox_id: Optional[str] = Field(
        None, description="Optional inbox ID to send from (for MailSlurp)"
    )


class SendEmailResponse(BaseModel):
    """Response model for email sending."""

    success: bool = Field(..., description="Whether email was sent successfully")
    result: Dict[str, Any] = Field(..., description="Provider-specific send result")


class RegisterWebhookRequest(BaseModel):
    """Request model for webhook registration."""

    inbox_id: str = Field(..., description="Inbox ID to monitor")
    execution_id: str = Field(..., description="Workflow execution ID")
    checkpoint_id: str = Field(..., description="Checkpoint node ID")
    webhook_base_url: Optional[str] = Field(
        None, description="Optional base URL for webhook"
    )


class RegisterWebhookResponse(BaseModel):
    """Response model for webhook registration."""

    webhook_id: str = Field(..., description="Registered webhook ID")
    inbox_id: str = Field(..., description="Inbox ID")
    webhook_url: str = Field(..., description="Webhook callback URL")
    event_types: List[str] = Field(..., description="Monitored event types")


class UnregisterWebhookResponse(BaseModel):
    """Response model for webhook unregistration."""

    success: bool = Field(..., description="Whether unregistration was successful")


class EmailData(BaseModel):
    """Model for email data in API responses."""

    id: str = Field(..., description="Email ID")
    from_address: str = Field(..., alias="from", description="Sender email address")
    to_addresses: List[str] = Field(..., alias="to", description="Recipient addresses")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    received_at: Optional[str] = Field(
        None, description="Received timestamp (ISO format)"
    )

    class Config:
        """Pydantic config."""

        populate_by_name = True


class GetEmailsResponse(BaseModel):
    """Response model for getting emails."""

    emails: List[EmailData] = Field(..., description="List of emails")


class CheckpointStatusResponse(BaseModel):
    """Response model for checkpoint status."""

    execution_id: str = Field(..., description="Workflow execution ID")
    has_email_checkpoints: bool = Field(
        ..., description="Whether execution has email checkpoints"
    )
    email_checkpoints: List[Dict[str, Any]] = Field(
        ..., description="List of email checkpoint details"
    )


class WebhookCallbackResponse(BaseModel):
    """Response model for webhook callbacks."""

    status: str = Field(..., description="Status of webhook processing")
    message: str = Field(..., description="Status message")
