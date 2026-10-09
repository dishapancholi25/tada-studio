"""
Pydantic schemas for email service operations.

These schemas provide type-safe data models for email operations,
validation, and serialization.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


@dataclass
class EmailInbox:
    """Represents an email inbox for receiving responses."""

    inbox_id: str
    email_address: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    webhook_id: Optional[str] = None
    owner_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmailMessage:
    """Represents an email message."""

    id: str
    from_address: str
    to_addresses: List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    received_at: Optional[datetime] = None
    attachments: Optional[List[Dict[str, Any]]] = None


@dataclass
class EmailWebhook:
    """Represents a webhook registration for email notifications."""

    webhook_id: str
    inbox_id: str
    url: str
    event_types: List[str]
    created_at: datetime
    secret: Optional[str] = None
    owner_id: Optional[str] = None


class EmailSendRequest(BaseModel):
    """Request model for sending emails."""

    from_address: str = Field(..., description="Sender email address")
    to_address: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text email body")
    html_body: Optional[str] = Field(None, description="HTML email body")
    reply_to: Optional[str] = Field(None, description="Reply-to email address")

    @field_validator("from_address", "to_address")
    @classmethod
    def validate_email(cls, v):
        """Validate email address."""
        if "@" not in v or "." not in v:
            raise ValueError(f"Invalid email address: {v}")
        return v


class WorkflowEmailRequest(BaseModel):
    """Request model for sending workflow-tracked emails."""

    workflow_id: str = Field(..., description="Workflow ID")
    execution_id: str = Field(..., description="Execution ID")
    to_address: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text email body")
    html_body: Optional[str] = Field(None, description="HTML email body")


class EmailExtractionConfig(BaseModel):
    """Configuration for extracting content from email responses."""

    extract_mode: str = Field(
        default="full_body",
        description="Extraction mode: full_body, regex, json, or stripped_text",
    )
    extraction_pattern: Optional[str] = Field(
        None, description="Regex pattern for extraction (if mode=regex)"
    )


class WebhookPayload(BaseModel):
    """Generic webhook payload structure."""

    provider: str = Field(..., description="Email provider name")
    event_type: str = Field(..., description="Webhook event type")
    data: Dict[str, Any] = Field(..., description="Webhook data payload")
    signature: Optional[str] = Field(
        None, description="Webhook signature for validation"
    )
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class EmailPollingConfig(BaseModel):
    """Configuration for email polling operations."""

    execution_id: str
    checkpoint_id: str
    inbox_id: str
    db_execution_id: int
    interval_seconds: int = Field(default=30, ge=10, le=300)
    timeout_minutes: int = Field(default=60, ge=1, le=1440)


class EmailProviderConfig(BaseModel):
    """Base configuration for email providers."""

    provider_name: str = Field(
        ..., description="Email provider name (mailgun, mailslurp)"
    )
    api_key: Optional[str] = Field(None, description="API key for the provider")
    domain: Optional[str] = Field(None, description="Domain for email operations")
