"""Pydantic schemas for email send tool."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EmailFieldMode(str, Enum):
    """Mode for email field value source."""

    AI = "ai"
    STATIC = "static"


class EmailFieldConfig(BaseModel):
    """Configuration for a single email field."""

    mode: EmailFieldMode = Field(
        default=EmailFieldMode.AI,
        description="Whether the field is AI-populated or static",
    )
    static_value: str = Field(
        default="", description="Static value when mode is STATIC"
    )
    ai_description: str = Field(
        default="", description="Description for AI when mode is AI"
    )


class EmailSendToolConfig(BaseModel):
    """Configuration for email send tool."""

    to_address: EmailFieldConfig = Field(
        default_factory=EmailFieldConfig,
        description="Configuration for recipient email address",
    )
    subject: EmailFieldConfig = Field(
        default_factory=EmailFieldConfig,
        description="Configuration for email subject",
    )
    body: EmailFieldConfig = Field(
        default_factory=EmailFieldConfig,
        description="Configuration for email body",
    )
    node_id: str = Field(default="", description="Node ID for tracking")
    node_name: str = Field(default="Email Send Tool", description="Node display name")


class EmailSendToolArgs(BaseModel):
    """Base arguments for email send tool execution.

    Note: The actual schema is built dynamically based on which fields
    are in AI mode. This base class is used when all fields are static.
    """

    pass


class EmailSendExecutionMetadata(BaseModel):
    """Metadata captured during email send execution."""

    to_address: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject")
    body_preview: str = Field(description="First 100 chars of body")
    message_id: Optional[str] = Field(default=None, description="Provider message ID")
    status: str = Field(description="Send status (sent, failed)")
    provider: Optional[str] = Field(default=None, description="Email provider used")


class EmailSendResponse(BaseModel):
    """Response from email send execution."""

    success: bool = Field(description="Whether email was sent successfully")
    message_id: Optional[str] = Field(default=None, description="Provider message ID")
    to_address: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )
