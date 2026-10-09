"""
Email content extraction handler.

Handles extracting workflow IDs and content from email webhooks.
"""

import logging
import re
from typing import Any, Dict, Optional

from backend.services.email.config import LOG_PREFIX_WEBHOOK
from backend.services.email.utils import extract_email_content


logger = logging.getLogger(__name__)


class EmailExtractionHandler:
    """Handles extraction of workflow data from emails."""

    @staticmethod
    def extract_execution_id(email_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract execution ID from email data.

        Args:
            email_data: Email webhook payload

        Returns:
            Execution ID or None if not found
        """
        # Try recipient address first
        recipient = email_data.get("recipient", "")
        if recipient.startswith("workflow-") and "@" in recipient:
            execution_id = recipient.split("workflow-")[1].split("@")[0]
            logger.info(
                f"{LOG_PREFIX_WEBHOOK} Extracted execution ID from recipient: {execution_id}"
            )
            return execution_id

        # Try subject line reference
        subject = email_data.get("subject", "")
        ref_match = re.search(r"\[REF:([a-zA-Z0-9_-]+)\]", subject)
        if ref_match:
            execution_id = ref_match.group(1)
            logger.info(
                f"{LOG_PREFIX_WEBHOOK} Extracted execution ID from subject: {execution_id}"
            )
            return execution_id

        logger.warning(
            f"{LOG_PREFIX_WEBHOOK} Could not extract execution ID from email"
        )
        return None

    @staticmethod
    def extract_content(
        email_data: Dict[str, Any], email_config: Dict[str, Any]
    ) -> Any:
        """
        Extract content from email based on configuration.

        Args:
            email_data: Email webhook payload
            email_config: Extraction configuration

        Returns:
            Extracted content
        """
        extract_mode = email_config.get("extract_mode", "full_body")
        extraction_pattern = email_config.get("extraction_pattern")

        # Get email body (prefer stripped text)
        body_plain = email_data.get("body-plain", "")
        stripped_text = email_data.get("stripped-text", body_plain)

        try:
            extracted = extract_email_content(
                body_plain,
                extract_mode=extract_mode,
                extraction_pattern=extraction_pattern,
                stripped_text=stripped_text,
            )

            logger.info(
                f"{LOG_PREFIX_WEBHOOK} Extracted content using mode: {extract_mode}"
            )
            return extracted

        except Exception as e:
            logger.error(f"{LOG_PREFIX_WEBHOOK} Content extraction failed: {e}")
            # Fallback to stripped text
            return stripped_text or body_plain

    @staticmethod
    def parse_mailgun_webhook(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Mailgun webhook form data into standard format.

        Args:
            form_data: Raw Mailgun form data

        Returns:
            Parsed email data
        """
        logger.debug(f"{LOG_PREFIX_WEBHOOK} Parsing Mailgun webhook payload")

        return {
            "recipient": form_data.get("recipient", ""),
            "sender": form_data.get("sender", ""),
            "from": form_data.get("from", ""),
            "subject": form_data.get("subject", ""),
            "body-plain": form_data.get("body-plain", ""),
            "stripped-text": form_data.get("stripped-text", ""),
            "message-headers": form_data.get("message-headers", []),
        }
