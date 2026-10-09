"""Email configuration for email sending nodes.

This module defines the configuration for email sending actions
with support for dynamic content from workflow state.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import Any, Dict, List, Optional


@dataclass
class EmailSendConfig:
    """Configuration for email send action nodes.

    Supports dynamic email content sourced from previous nodes with
    HTML support and template variables.

    Attributes:
        to_address: Recipient email address
        to_source_mode: Source mode for recipient (static, previous, specific, field)
        to_source_node_id: Source node ID for recipient
        to_source_field_path: Field path for recipient
        subject: Email subject line
        subject_source_mode: Source mode for subject
        subject_source_node_id: Source node ID for subject
        subject_source_field_path: Field path for subject
        body: Email body content
        body_source_mode: Source mode for body
        body_source_node_id: Source node ID for body
        body_source_field_path: Field path for body
        from_address: Sender email address (optional, uses default if empty)
        from_source_mode: Source mode for sender
        from_source_node_id: Source node ID for sender
        from_source_field_path: Field path for sender
        cc_addresses: CC recipients
        bcc_addresses: BCC recipients
        use_html: Enable HTML body
        html_body: HTML body content
        html_body_source_mode: Source mode for HTML body
        html_body_source_node_id: Source node ID for HTML body
        html_body_source_field_path: Field path for HTML body
        use_template: Enable template rendering
        template_variables: Variables for template rendering
        timeout_seconds: Execution timeout
        track_opens: Track email opens
        track_clicks: Track link clicks
        reply_to: Reply-to address
        reply_to_source_mode: Source mode for reply-to
        reply_to_source_node_id: Source node ID for reply-to
        reply_to_source_field_path: Field path for reply-to
    """

    to_address: str = ""
    to_source_mode: str = "static"
    to_source_node_id: Optional[str] = None
    to_source_field_path: Optional[str] = None
    subject: str = ""
    subject_source_mode: str = "static"
    subject_source_node_id: Optional[str] = None
    subject_source_field_path: Optional[str] = None
    body: str = ""
    body_source_mode: str = "static"
    body_source_node_id: Optional[str] = None
    body_source_field_path: Optional[str] = None
    from_address: str = ""
    from_source_mode: str = "static"
    from_source_node_id: Optional[str] = None
    from_source_field_path: Optional[str] = None
    cc_addresses: List[str] = field(default_factory=list)
    bcc_addresses: List[str] = field(default_factory=list)
    use_html: bool = False
    html_body: str = ""
    html_body_source_mode: str = "static"
    html_body_source_node_id: Optional[str] = None
    html_body_source_field_path: Optional[str] = None
    use_template: bool = False
    template_variables: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    track_opens: bool = False
    track_clicks: bool = False
    reply_to: str = ""
    reply_to_source_mode: str = "static"
    reply_to_source_node_id: Optional[str] = None
    reply_to_source_field_path: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None
