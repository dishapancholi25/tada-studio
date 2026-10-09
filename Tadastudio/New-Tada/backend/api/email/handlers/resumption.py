"""
Workflow resumption handler for email responses.

Handles resuming workflows when email responses are received.
"""

import logging
import time
from typing import Any

from backend.services.database import SessionLocal
from backend.models import GraphExecution
from backend.services.dependency_injection import get_execution_engine
from backend.services.email.config import LOG_PREFIX_WEBHOOK


logger = logging.getLogger(__name__)


class WorkflowResumptionHandler:
    """Handles resuming workflows from email responses."""

    @staticmethod
    async def resume_workflow(
        execution_id: str,
        checkpoint_id: str,
        input_data: Any,
        db_execution_id: int,
    ) -> bool:
        """
        Resume a workflow from an email response.

        Args:
            execution_id: The workflow execution ID
            checkpoint_id: The checkpoint node ID
            input_data: The extracted email content to use as input
            db_execution_id: Database execution ID

        Returns:
            True if resumption successful

        Raises:
            Exception: If resumption fails
        """
        resume_start = time.time()
        logger.info(
            f"{LOG_PREFIX_WEBHOOK} Resuming workflow for execution: {execution_id}"
        )

        db = SessionLocal()
        try:
            # Get execution details
            execution = await WorkflowResumptionHandler._get_execution(
                db, db_execution_id
            )
            if not execution:
                return False

            # Update status to running
            WorkflowResumptionHandler._update_execution_status(db, execution, "running")

            # Get checkpoint ID for resume
            checkpoint_id_for_resume = (
                await WorkflowResumptionHandler._get_checkpoint_id(
                    execution.thread_id, resume_start
                )
            )

            # Resume the workflow
            success = await WorkflowResumptionHandler._execute_resume(
                execution.graph_name,
                execution.thread_id,
                checkpoint_id_for_resume,
                input_data,
                resume_start,
            )

            if success:
                # Send completion notification
                await WorkflowResumptionHandler._send_completion_notification(
                    execution.thread_id, success
                )
            else:
                # Mark as failed
                WorkflowResumptionHandler._update_execution_status(
                    db, execution, "failed", error_message="Resume failed"
                )

            return success

        except Exception as e:
            logger.error(f"{LOG_PREFIX_WEBHOOK} Failed to resume workflow: {e}")
            raise

        finally:
            db.close()

    @staticmethod
    async def _get_execution(db, db_execution_id: int):
        """Get execution from database."""
        execution = (
            db.query(GraphExecution)
            .filter(GraphExecution.id == db_execution_id)
            .first()
        )

        if not execution:
            logger.error(f"{LOG_PREFIX_WEBHOOK} Execution not found: {db_execution_id}")
            return None

        logger.debug(
            f"{LOG_PREFIX_WEBHOOK} Found execution: {execution.graph_name} (thread: {execution.thread_id})"
        )
        return execution

    @staticmethod
    def _update_execution_status(db, execution, status: str, error_message: str = None):
        """Update execution status in database."""
        execution.status = status
        if error_message:
            execution.error_message = error_message
        db.commit()

        logger.info(f"{LOG_PREFIX_WEBHOOK} Updated execution status to: {status}")

    @staticmethod
    async def _get_checkpoint_id(thread_id: str, resume_start: float) -> str:
        """Get the latest checkpoint ID for resumption."""
        checkpoint_id = None

        try:
            execution_engine = get_execution_engine()
            if hasattr(execution_engine, "get_checkpoints"):
                checkpoints = execution_engine.get_checkpoints(thread_id)
                if checkpoints:
                    checkpoint_id = checkpoints[0].get("checkpoint_id")
                    logger.info(
                        f"{LOG_PREFIX_WEBHOOK} Found checkpoint ID: {checkpoint_id} "
                        f"at T+{time.time() - resume_start:.3f}s"
                    )
        except Exception as e:
            logger.warning(f"{LOG_PREFIX_WEBHOOK} Failed to get checkpoint ID: {e}")

        return checkpoint_id

    @staticmethod
    async def _execute_resume(
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        input_data: Any,
        resume_start: float,
    ) -> Any:
        """Execute the workflow resumption."""
        try:
            execution_engine = get_execution_engine()

            logger.info(
                f"{LOG_PREFIX_WEBHOOK} Calling resume_from_checkpoint "
                f"at T+{time.time() - resume_start:.3f}s"
            )

            result = await execution_engine.resume_from_checkpoint(
                graph_name=graph_name,
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                new_input={"answer": input_data},
            )

            logger.info(
                f"{LOG_PREFIX_WEBHOOK} Workflow resumed successfully "
                f"at T+{time.time() - resume_start:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX_WEBHOOK} Failed to execute resume: {e}")
            raise

    @staticmethod
    async def _send_completion_notification(execution_id: str, result: Any):
        """Send WebSocket notification about workflow completion."""
        try:
            from backend.services.websocket import notifier as ws_notifier

            if ws_notifier:
                await ws_notifier.on_execution_complete(execution_id, result)
                logger.debug(
                    f"{LOG_PREFIX_WEBHOOK} Sent completion notification for: {execution_id}"
                )
        except Exception as e:
            logger.debug(f"{LOG_PREFIX_WEBHOOK} WebSocket notification error: {e}")
