"""
Email webhook handler.

DISABLED: This handler is temporarily disabled pending security review.
See: Email checkpoint webhook sender/approver validation issue

The email checkpoint feature requires:
1. Sender verification against authorized approver
2. Recipient verification against registered inbox
3. Webhook signature validation

All webhook processing is currently disabled. Webhooks will return 503 Service Unavailable.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from backend.models import GraphExecution, NodeExecution
from sqlalchemy.orm import Session
from backend.services.email.config import LOG_PREFIX_WEBHOOK

from .extraction import EmailExtractionHandler
from .resumption import WorkflowResumptionHandler


logger = logging.getLogger(__name__)


class EmailWebhookHandler:
    """Handles email webhook callbacks.
    
    DISABLED: All webhook processing currently returns Service Unavailable.
    """

    @staticmethod
    async def handle_mailgun_webhook(
        form_data: Dict[str, Any], db: Session
    ) -> Dict[str, Any]:
        """
        Handle Mailgun webhook callback.

        DISABLED: Returns 503 Service Unavailable due to security review.

        Args:
            form_data: Mailgun webhook form data
            db: Database session

        Returns:
            Response dict with status and message
        """
        logger.info(f"{LOG_PREFIX_WEBHOOK} Email webhook disabled (security review)")
        return {
            "status": "unavailable",
            "message": "Email checkpoint feature is temporarily disabled pending security review"
        }

        # NOTE: Previous implementation removed - see git history for reference
        # logger.info(f"{LOG_PREFIX_WEBHOOK} Received Mailgun webhook")

        # # Parse email data
        # email_data = EmailExtractionHandler.parse_mailgun_webhook(form_data)

        # # Extract execution ID
        # execution_id = EmailExtractionHandler.extract_execution_id(email_data)
        # if not execution_id:
        #     logger.warning(f"{LOG_PREFIX_WEBHOOK} No execution ID found")
        #     return {"status": "error", "message": "No execution ID found"}

        # Get execution and checkpoint
        execution, checkpoint_node = EmailWebhookHandler._get_execution_and_checkpoint(
            db, execution_id
        )

        if not execution or not checkpoint_node:
            # Return success to prevent webhook retries
            return {
                "status": "success",
                "message": "Execution or checkpoint not found, ignoring",
            }

        # Extract content
        node_metadata = checkpoint_node.node_metadata or {}
        email_config = node_metadata.get("email_config", {})

        extracted_content = EmailExtractionHandler.extract_content(
            email_data, email_config
        )

        # Update checkpoint node
        EmailWebhookHandler._update_checkpoint_node(
            checkpoint_node, email_data, extracted_content, db
        )

        # Resume workflow in background
        await EmailWebhookHandler._schedule_workflow_resume(
            execution_id,
            checkpoint_node.node_id,
            extracted_content,
            execution.id,
        )

        logger.info(
            f"{LOG_PREFIX_WEBHOOK} Webhook processed successfully for: {execution_id}"
        )

        return {
            "status": "success",
            "message": "Email received and workflow will resume",
        }

    @staticmethod
    def _get_execution_and_checkpoint(db: Session, execution_id: str):
        """Get execution and checkpoint from database."""
        # Get paused execution
        execution = (
            db.query(GraphExecution)
            .filter(
                GraphExecution.websocket_execution_id == execution_id,
                GraphExecution.status == "paused",
            )
            .first()
        )

        if not execution:
            logger.warning(
                f"{LOG_PREFIX_WEBHOOK} No paused execution found: {execution_id}"
            )
            return None, None

        # Find paused checkpoint node
        checkpoint_node = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == execution.id,
                NodeExecution.node_type == "CHECKPOINT",
                NodeExecution.status == "paused",
            )
            .first()
        )

        if not checkpoint_node:
            logger.warning(
                f"{LOG_PREFIX_WEBHOOK} No paused checkpoint found for: {execution_id}"
            )
            return execution, None

        logger.debug(
            f"{LOG_PREFIX_WEBHOOK} Found execution and checkpoint for: {execution_id}"
        )
        return execution, checkpoint_node

    @staticmethod
    def _update_checkpoint_node(
        checkpoint_node, email_data: Dict[str, Any], extracted_content: Any, db: Session
    ):
        """Update checkpoint node with email response."""
        checkpoint_node.output_data = {
            "email_response": {
                "from": email_data.get("from", email_data.get("sender", "")),
                "subject": email_data.get("subject", ""),
                "body": email_data.get("body-plain", ""),
                "stripped_text": email_data.get("stripped-text", ""),
                "extracted_content": extracted_content,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        checkpoint_node.status = "completed"
        checkpoint_node.end_time = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            f"{LOG_PREFIX_WEBHOOK} Updated checkpoint node: {checkpoint_node.node_id}"
        )

    @staticmethod
    async def _schedule_workflow_resume(
        execution_id: str,
        checkpoint_id: str,
        input_data: Any,
        db_execution_id: int,
    ):
        """Schedule workflow resume in background."""

        async def resume_with_error_handling():
            """Handle errors during workflow resumption."""
            try:
                await WorkflowResumptionHandler.resume_workflow(
                    execution_id=execution_id,
                    checkpoint_id=checkpoint_id,
                    input_data=input_data,
                    db_execution_id=db_execution_id,
                )
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX_WEBHOOK} Error in background resume task: {e}"
                )

        # Create background task
        task = asyncio.create_task(resume_with_error_handling())
        task.set_name(f"resume_workflow_{execution_id}")

        logger.debug(
            f"{LOG_PREFIX_WEBHOOK} Scheduled workflow resume task: {execution_id}"
        )
