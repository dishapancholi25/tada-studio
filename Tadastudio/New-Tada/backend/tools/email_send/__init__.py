"""Email send tool for agents.

This module provides email sending capabilities for AI agents,
allowing dynamic or static email composition.
"""

from .factory import create_email_send_tool
from .schemas import EmailSendToolArgs, EmailSendToolConfig

__all__ = ["create_email_send_tool", "EmailSendToolArgs", "EmailSendToolConfig"]
