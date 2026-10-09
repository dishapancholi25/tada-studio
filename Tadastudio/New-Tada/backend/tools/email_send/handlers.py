"""Business logic handlers for email send tool operations."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .schemas import EmailFieldMode, EmailSendToolConfig


logger = logging.getLogger(__name__)


def handle_email_send_execution(
    kwargs: Dict[str, Any],
    config: EmailSendToolConfig,
    user_id: Optional[str] = None,
) -> str:
    """Execute email send with merged AI and static values.

    Args:
        kwargs: AI-provided values from tool invocation
        config: Tool configuration with static values
        user_id: User ID for email provider configuration

    Returns:
        JSON string with send result
    """
    # Merge AI-provided values with static config
    to_address = _get_field_value("to_address", kwargs, config.to_address)
    subject = _get_field_value("subject", kwargs, config.subject)
    body = _get_field_value("body", kwargs, config.body)

    # Extract attachment file IDs (always AI-provided)
    attachment_file_ids: List[str] = kwargs.get("attachment_file_ids", [])

    # Validate required fields
    if not to_address:
        return json.dumps(
            {
                "success": False,
                "error": "Recipient email address (to_address) is required",
            }
        )

    if not subject:
        subject = "No Subject"

    if not body:
        body = ""

    logger.info(
        f"[EmailSendTool] Sending email to {to_address} with subject: {subject}"
        f" ({len(attachment_file_ids)} attachments)"
    )

    try:
        # Run async send in sync context
        result = asyncio.run(
            _send_email_async(to_address, subject, body, user_id, attachment_file_ids)
        )

        return json.dumps(
            {
                "success": True,
                "message_id": result.get("id", ""),
                "to_address": to_address,
                "subject": subject,
                "status": "sent",
                "attachments_sent": len(attachment_file_ids),
            }
        )
    except Exception as e:
        logger.error(f"[EmailSendTool] Error sending email: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "to_address": to_address,
                "subject": subject,
            }
        )


def _get_field_value(
    field_name: str,
    kwargs: Dict[str, Any],
    field_config: Any,
) -> str:
    """Get field value from AI kwargs or static config.

    Args:
        field_name: Name of the field
        kwargs: AI-provided values
        field_config: Field configuration

    Returns:
        Field value
    """
    # If AI provided the value, use it
    if field_name in kwargs:
        return str(kwargs[field_name])

    # Otherwise use static value
    if field_config.mode == EmailFieldMode.STATIC:
        return field_config.static_value

    return ""


def _resolve_attachments(file_ids: List[str]):
    """Resolve file IDs to EmailAttachment objects.

    Args:
        file_ids: List of execution file UUIDs

    Returns:
        List of EmailAttachment objects
    """
    from backend.services.email.providers.base import EmailAttachment
    from backend.services.execution.files.service import ExecutionFileService

    file_service = ExecutionFileService()
    attachments = []

    for file_id in file_ids:
        result = file_service.get_file_content(file_id)
        if result is None:
            logger.warning(f"[EmailSendTool] Attachment file not found: {file_id}")
            continue
        content, mime_type, filename = result
        attachments.append(
            EmailAttachment(filename=filename, content=content, mime_type=mime_type)
        )
        logger.info(f"[EmailSendTool] Resolved attachment: {filename} ({mime_type})")

    return attachments


async def _send_email_async(
    to_address: str,
    subject: str,
    body: str,
    user_id: Optional[str] = None,
    attachment_file_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Send email using the email provider infrastructure.

    Args:
        to_address: Recipient email address
        subject: Email subject
        body: Email body
        user_id: User ID for email provider configuration
        attachment_file_ids: Optional list of file IDs to attach

    Returns:
        Provider response dictionary
    """
    from backend.services.email.credential_resolver import resolve_email_provider_config
    from backend.services.email.providers.factory import EmailServiceFactory

    # Resolve provider config from user-tier, then system-tier, then env vars
    provider_name, provider_kwargs = resolve_email_provider_config(user_id)

    # Create provider
    email_provider = EmailServiceFactory.create_provider(
        provider_name, **provider_kwargs
    )

    # Set from address
    from_address = None
    if hasattr(email_provider, "sender_email") and email_provider.sender_email:
        from_address = email_provider.sender_email
    elif hasattr(email_provider, "domain"):
        from_address = f"AgenticStudio <noreply@{email_provider.domain}>"
    else:
        raise ValueError("No sender email configured for email provider")

    # Resolve attachments from file IDs
    attachments = None
    if attachment_file_ids:
        attachments = _resolve_attachments(attachment_file_ids)

    # Send email
    result = await email_provider.send_email(
        from_address=from_address,
        to_address=to_address,
        subject=subject,
        body=body,
        attachments=attachments,
    )

    logger.info(f"[EmailSendTool] Email sent successfully to {to_address}")
    return result
