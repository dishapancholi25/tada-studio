"""Email send tool configuration for AI agent tools.

This module defines the configuration for email send tools that AI agents
can invoke, with support for AI-populated or static field values.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig


@dataclass
class EmailSendToolFieldConfig:
    """Configuration for a single email field in the tool.

    Attributes:
        mode: Field mode - "ai" for AI-populated or "static" for fixed value
        static_value: Value used when mode is "static"
        ai_description: Description for AI when mode is "ai"
    """

    mode: str = "ai"
    static_value: str = ""
    ai_description: str = ""


@dataclass
class EmailSendToolConfig:
    """Configuration for email send tool nodes.

    Unlike EmailSendConfig (action node), this supports AI-populated fields
    where the AI determines values based on context and descriptions.

    Attributes:
        to_address: Configuration for recipient email field
        subject: Configuration for subject line field
        body: Configuration for email body field
        guardrails_config: Optional guardrails configuration
    """

    to_address: EmailSendToolFieldConfig = field(
        default_factory=EmailSendToolFieldConfig
    )
    subject: EmailSendToolFieldConfig = field(default_factory=EmailSendToolFieldConfig)
    body: EmailSendToolFieldConfig = field(default_factory=EmailSendToolFieldConfig)
    guardrails_config: Optional["GuardrailsConfig"] = None
