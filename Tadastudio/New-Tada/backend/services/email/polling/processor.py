"""
Email response processor for polling service.

Handles processing of received emails and updating workflow state.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from ..config import LOG_PREFIX_POLLING
from ..exceptions import EmailExtractionError
from ..schemas import EmailMessage
from ..utils import extract_email_content


logger = logging.getLogger(__name__)


class EmailResponseProcessor:
    """Processes email responses for workflow resumption."""

    @staticmethod
    async def process_email_response(
        execution_id: str,
        checkpoint_id: str,
        db_execution_id: int,
        email: EmailMessage,
        extraction_config: dict = None,
    ) -> bool:
        """
        Process received email and update workflow state.

        Args:
            execution_id: Workflow execution ID
            checkpoint_id: Checkpoint node ID
            db_execution_id: Database execution ID
            email: EmailMessage to process
            extraction_config: Configuration for content extraction

        Returns:
            True if processing successful

        Raises:
            EmailExtractionError: If content extraction fails
        """
        from backend.services.database import SessionLocal
        from backend.models import NodeExecution

        logger.info(
            f"{LOG_PREFIX_POLLING} Processing email response for execution: {execution_id}"
        )

        db = SessionLocal()
        try:
            # Find the checkpoint node
            checkpoint_node = (
                db.query(NodeExecution)
                .filter(
                    NodeExecution.graph_execution_id == db_execution_id,
                    NodeExecution.node_id == checkpoint_id,
                    NodeExecution.status == "paused",
                )
                .first()
            )

            if not checkpoint_node:
                logger.error(
                    f"{LOG_PREFIX_POLLING} Checkpoint node not found: {checkpoint_id}"
                )
                return False

            # Extract email content
            extracted_content = EmailResponseProcessor._extract_content(
                email, checkpoint_node, extraction_config
            )

            # Update checkpoint node
            EmailResponseProcessor._update_checkpoint_node(
                checkpoint_node, email, extracted_content, db
            )

            # Send WebSocket notification
            await EmailResponseProcessor._send_notification(
                execution_id, checkpoint_id, extracted_content
            )

            logger.info(
                f"{LOG_PREFIX_POLLING} Email processed successfully for: {execution_id}"
            )
            return True

        finally:
            db.close()

    @staticmethod
    def _extract_content(
        email: EmailMessage, checkpoint_node, extraction_config: dict = None
    ) -> Any:
        """Extract content from email based on configuration."""
        node_metadata = checkpoint_node.node_metadata or {}
        email_config = node_metadata.get("email_config", {})

        # Use provided config or fall back to node metadata
        config = extraction_config or email_config

        extract_mode = config.get("extract_mode", "full_body")
        extraction_pattern = config.get("extraction_pattern")

        try:
            return extract_email_content(
                email.body,
                extract_mode=extract_mode,
                extraction_pattern=extraction_pattern,
            )
        except EmailExtractionError as e:
            logger.warning(
                f"{LOG_PREFIX_POLLING} Content extraction failed, using full body: {e}"
            )
            return email.body

    @staticmethod
    def _update_checkpoint_node(checkpoint_node, email, extracted_content, db):
        """Update checkpoint node with email response data."""
        checkpoint_node.output_data = {
            "email_response": {
                "from": email.from_address,
                "subject": email.subject,
                "body": email.body,
                "extracted_content": extracted_content,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        checkpoint_node.status = "completed"
        checkpoint_node.end_time = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            f"{LOG_PREFIX_POLLING} Updated checkpoint node: {checkpoint_node.node_id}"
        )

    @staticmethod
    async def _send_notification(
        execution_id: str, checkpoint_id: str, extracted_content: Any
    ):
        """Send WebSocket notification about email response."""
        try:
            from backend.services.websocket import notifier as ws_notifier

            if ws_notifier:
                import json

                await ws_notifier.send_message(
                    execution_id=execution_id,
                    message={
                        "type": "checkpoint_resumed",
                        "checkpoint_id": checkpoint_id,
                        "resumed_via": "email_polling",
                        "input": extracted_content
                        if isinstance(extracted_content, str)
                        else json.dumps(extracted_content),
                    },
                )
                logger.debug(
                    f"{LOG_PREFIX_POLLING} WebSocket notification sent for: {execution_id}"
                )
        except Exception as e:
            logger.debug(f"{LOG_PREFIX_POLLING} WebSocket notification skipped: {e}")

    @staticmethod
    async def handle_polling_timeout(
        execution_id: str, db_execution_id: int, timeout_minutes: int
    ):
        """
        Handle polling timeout.

        Args:
            execution_id: Workflow execution ID
            db_execution_id: Database execution ID
            timeout_minutes: Timeout duration
        """
        from backend.services.database import SessionLocal
        from backend.models import GraphExecution

        logger.warning(
            f"{LOG_PREFIX_POLLING} Email polling timeout for execution: {execution_id}"
        )

        db = SessionLocal()
        try:
            execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == db_execution_id)
                .first()
            )

            if execution and execution.status == "paused":
                # Send timeout notification
                try:
                    from backend.services.websocket import notifier as ws_notifier

                    if ws_notifier:
                        await ws_notifier.send_message(
                            execution_id=execution_id,
                            message={
                                "type": "checkpoint_timeout",
                                "message": "Email response timeout. Please resume manually.",
                                "timeout_minutes": timeout_minutes,
                            },
                        )
                        logger.debug(
                            f"{LOG_PREFIX_POLLING} Timeout notification sent for: {execution_id}"
                        )
                except Exception as e:
                    logger.debug(
                        f"{LOG_PREFIX_POLLING} Timeout notification skipped: {e}"
                    )
        finally:
            db.close()
