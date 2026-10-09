"""
Utility functions for email service operations.

Provides common utilities for email extraction, validation, and formatting.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from .config import (
    EXTRACT_MODE_FULL_BODY,
    EXTRACT_MODE_JSON,
    EXTRACT_MODE_REGEX,
    EXTRACT_MODE_STRIPPED_TEXT,
)
from .exceptions import EmailExtractionError


logger = logging.getLogger(__name__)


def extract_email_content(
    email_body: str,
    extract_mode: str = EXTRACT_MODE_FULL_BODY,
    extraction_pattern: Optional[str] = None,
    stripped_text: Optional[str] = None,
) -> Any:
    """
    Extract content from email based on configuration.

    Args:
        email_body: The raw email body text
        extract_mode: How to extract content (full_body, stripped_text, regex, json)
        extraction_pattern: Regex pattern for regex mode
        stripped_text: Pre-stripped text (without signatures/quotes)

    Returns:
        Extracted content (str or dict for JSON mode)

    Raises:
        EmailExtractionError: If extraction fails
    """
    try:
        if extract_mode == EXTRACT_MODE_STRIPPED_TEXT and stripped_text:
            return stripped_text

        if extract_mode == EXTRACT_MODE_REGEX and extraction_pattern:
            match = re.search(extraction_pattern, email_body)
            if match:
                # Return first group if available, otherwise full match
                return match.group(1) if match.groups() else match.group(0)
            logger.warning(
                f"Regex pattern '{extraction_pattern}' did not match, using full body"
            )
            return email_body

        if extract_mode == EXTRACT_MODE_JSON:
            return _extract_json_from_text(email_body)

        # Default: return full body
        return stripped_text if stripped_text else email_body

    except Exception as e:
        logger.error(f"Failed to extract email content: {e}")
        raise EmailExtractionError(f"Content extraction failed: {e}") from e


def _extract_json_from_text(text: str) -> Any:
    """
    Extract and parse JSON from text.

    Uses string indexing instead of regex to avoid ReDoS on untrusted input.

    Args:
        text: Text containing JSON

    Returns:
        Parsed JSON object or original text if extraction fails
    """
    try:
        # Try to find JSON object: locate first { and last }
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        if obj_start != -1 and obj_end > obj_start:
            try:
                return json.loads(text[obj_start : obj_end + 1])
            except json.JSONDecodeError:
                pass

        # Try to find JSON array: locate first [ and last ]
        arr_start = text.find("[")
        arr_end = text.rfind("]")
        if arr_start != -1 and arr_end > arr_start:
            try:
                return json.loads(text[arr_start : arr_end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("No JSON found in text, returning original text")
        return text

    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"Failed to parse JSON from email body: {e}")
        return text


def extract_workflow_id_from_email(email_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract workflow/execution ID from email data.

    Tries multiple methods:
    1. Recipient address (workflow-{id}@domain)
    2. Subject line reference ([REF:{id}])
    3. Custom headers (X-Workflow-ID)

    Args:
        email_data: Email data dictionary

    Returns:
        Extracted execution ID or None
    """
    execution_id = None

    # Method 1: Check recipient/reply-to address
    recipient = email_data.get("recipient", "")
    if recipient.startswith("workflow-") and "@" in recipient:
        execution_id = recipient.split("workflow-")[1].split("@")[0]
        logger.info(f"Extracted execution ID from recipient: {execution_id}")
        return execution_id

    # Method 2: Check subject line for reference
    subject = email_data.get("subject", "")
    match = re.search(r"\[REF:([a-zA-Z0-9_-]+)\]", subject)
    if match:
        execution_id = match.group(1)
        logger.info(f"Extracted execution ID from subject: {execution_id}")
        return execution_id

    # Method 3: Check custom headers
    headers = email_data.get("message-headers", [])
    for header in headers:
        if isinstance(header, list) and len(header) == 2:
            if header[0] == "X-Workflow-ID":
                execution_id = header[1]
                logger.info(f"Extracted execution ID from headers: {execution_id}")
                return execution_id

    return execution_id


def validate_email_address(email: str) -> bool:
    """
    Validate email address.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # Basic pattern check
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def format_email_address(name: str, email: str) -> str:
    """
    Format email address with name.

    Args:
        name: Display name
        email: Email address

    Returns:
        Formatted address like "Name <email@domain.com>"
    """
    if not name:
        return email
    return f"{name} <{email}>"


def sanitize_subject(subject: str, max_length: int = 200) -> str:
    """
    Sanitize email subject line.

    Args:
        subject: Original subject
        max_length: Maximum length

    Returns:
        Sanitized subject
    """
    if not subject:
        return ""

    # Remove control characters
    subject = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", subject)

    # Truncate if too long
    if len(subject) > max_length:
        subject = subject[: max_length - 3] + "..."

    return subject
