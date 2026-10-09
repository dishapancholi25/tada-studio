"""Checkpoint configuration for human-in-the-loop nodes.

This module defines configurations for checkpoint nodes that pause
workflow execution for human input or email-based responses.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EmailCheckpointConfig:
    """Configuration for email-based checkpoint.

    Enables workflow pause with email notification and response capture.

    Attributes:
        enabled: Enable email-based checkpoint
        email_provider: Email provider (mailslurp, resend, sendgrid)
        send_email: Send outbound email
        recipient_email: Recipient email address
        recipient_email_source_mode: Source mode (static, previous, specific, field)
        recipient_email_source_node_id: Source node ID for recipient
        recipient_email_field_path: Field path for recipient
        email_subject: Email subject line
        email_subject_source_mode: Source mode for subject
        email_subject_source_node_id: Source node ID for subject
        email_subject_field_path: Field path for subject
        email_body_template: Email body template with variables
        email_body_source_mode: Source mode for body
        email_body_source_node_id: Source node ID for body
        email_body_field_path: Field path for body
        inbox_id: MailSlurp inbox ID
        reply_to_address: Generated temporary email for replies
        await_reply: Wait for reply email
        extract_mode: Response extraction mode (full_body, regex, json)
        extraction_pattern: Pattern for regex/json modes
        timeout_minutes: Maximum wait time for response
        webhook_id: Webhook registration ID
        webhook_secret: Secret for webhook validation
    """

    enabled: bool = False
    email_provider: str = "mailslurp"
    send_email: bool = True
    recipient_email: str = ""
    recipient_email_source_mode: str = "static"
    recipient_email_source_node_id: Optional[str] = None
    recipient_email_field_path: Optional[str] = None
    email_subject: str = ""
    email_subject_source_mode: str = "static"
    email_subject_source_node_id: Optional[str] = None
    email_subject_field_path: Optional[str] = None
    email_body_template: str = ""
    email_body_source_mode: str = "static"
    email_body_source_node_id: Optional[str] = None
    email_body_field_path: Optional[str] = None
    inbox_id: str = ""
    reply_to_address: str = ""
    await_reply: bool = True
    extract_mode: str = "full_body"
    extraction_pattern: str = ""
    timeout_minutes: int = 60
    webhook_id: str = ""
    webhook_secret: str = ""


@dataclass
class CheckpointConfig:
    """Configuration for human-in-the-loop checkpoint nodes.

    Supports multiple checkpoint modes including manual input, email,
    webhook, and SMS-based pauses.

    Attributes:
        prompt: Prompt text for checkpoint
        require_input: Require user input to continue
        timeout_seconds: Timeout for checkpoint (None for no timeout)
        default_value: Default value if timeout occurs
        await_mode: Checkpoint mode (manual, email, webhook, sms)
        email_config: Email checkpoint configuration
        webhook_config: Webhook checkpoint configuration (future)
        advanced: Advanced configuration options
    """

    prompt: str = "Please review and provide input to continue."
    require_input: bool = True
    timeout_seconds: Optional[int] = None
    default_value: Optional[str] = None
    await_mode: str = "manual"
    email_config: Optional[EmailCheckpointConfig] = None
    webhook_config: Optional[Dict[str, Any]] = None
    advanced: Dict[str, Any] = field(default_factory=dict)
