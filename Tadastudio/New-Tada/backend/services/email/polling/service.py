"""
Email polling service for checkpoint resumption.

Polls email inbox for new messages when webhooks aren't available.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..config import (
    DEFAULT_POLLING_INTERVAL_SECONDS,
    DEFAULT_POLLING_TIMEOUT_MINUTES,
    LOG_PREFIX_POLLING,
)
from ..manager import get_email_manager
from ..schemas import EmailPollingConfig
from .processor import EmailResponseProcessor


logger = logging.getLogger(__name__)


class EmailPollingService:
    """Service to poll for email responses when webhooks aren't available."""

    def __init__(self):
        """Initialize email polling service."""
        self.polling_tasks: Dict[str, asyncio.Task] = {}
        self.polling_configs: Dict[str, EmailPollingConfig] = {}

        logger.info(f"{LOG_PREFIX_POLLING} Email polling service initialized")

    async def start_polling(
        self,
        execution_id: str,
        checkpoint_id: str,
        inbox_id: str,
        db_execution_id: int,
        interval_seconds: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        timeout_minutes: int = DEFAULT_POLLING_TIMEOUT_MINUTES,
    ):
        """
        Start polling for email responses.

        Args:
            execution_id: Workflow execution ID
            checkpoint_id: Checkpoint node ID
            inbox_id: Email inbox ID
            db_execution_id: Database execution ID
            interval_seconds: Polling interval
            timeout_minutes: Timeout duration
        """
        config = EmailPollingConfig(
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            inbox_id=inbox_id,
            db_execution_id=db_execution_id,
            interval_seconds=interval_seconds,
            timeout_minutes=timeout_minutes,
        )

        logger.info(
            f"{LOG_PREFIX_POLLING} Starting polling for execution: {execution_id}, "
            f"inbox: {inbox_id}"
        )

        # Cancel any existing polling for this execution
        if execution_id in self.polling_tasks:
            self.polling_tasks[execution_id].cancel()

        # Create polling task
        task = asyncio.create_task(self._poll_for_email(config))
        self.polling_tasks[execution_id] = task
        self.polling_configs[execution_id] = config

    async def _poll_for_email(self, config: EmailPollingConfig):
        """
        Poll for email responses until received or timeout.

        Args:
            config: Polling configuration
        """
        email_manager = get_email_manager()
        start_time = datetime.utcnow()
        timeout = timedelta(minutes=config.timeout_minutes)
        last_email_id = None

        logger.info(f"{LOG_PREFIX_POLLING} Polling started for: {config.execution_id}")

        try:
            while datetime.utcnow() - start_time < timeout:
                try:
                    # Check for new emails
                    emails = await email_manager.get_emails(config.inbox_id, limit=10)

                    if emails:
                        newest_email = emails[0]

                        # Check if it's a new email we haven't processed
                        if newest_email.id != last_email_id:
                            logger.info(
                                f"{LOG_PREFIX_POLLING} New email received for: {config.execution_id}"
                            )

                            # Process the email
                            success = (
                                await EmailResponseProcessor.process_email_response(
                                    config.execution_id,
                                    config.checkpoint_id,
                                    config.db_execution_id,
                                    newest_email,
                                )
                            )

                            if success:
                                logger.info(
                                    f"{LOG_PREFIX_POLLING} Email processed successfully, stopping poll"
                                )
                                break

                        last_email_id = newest_email.id

                    # Wait before next poll
                    await asyncio.sleep(config.interval_seconds)

                except asyncio.CancelledError:
                    logger.info(
                        f"{LOG_PREFIX_POLLING} Polling cancelled for: {config.execution_id}"
                    )
                    raise

                except Exception as e:
                    logger.error(f"{LOG_PREFIX_POLLING} Error polling for email: {e}")
                    await asyncio.sleep(config.interval_seconds)

            else:
                # Timeout reached
                logger.warning(
                    f"{LOG_PREFIX_POLLING} Polling timeout for: {config.execution_id}"
                )
                await EmailResponseProcessor.handle_polling_timeout(
                    config.execution_id,
                    config.db_execution_id,
                    config.timeout_minutes,
                )

        finally:
            # Clean up
            self._cleanup_polling(config.execution_id)

    def _cleanup_polling(self, execution_id: str):
        """Clean up polling resources."""
        if execution_id in self.polling_tasks:
            del self.polling_tasks[execution_id]
        if execution_id in self.polling_configs:
            del self.polling_configs[execution_id]

        logger.debug(f"{LOG_PREFIX_POLLING} Cleaned up polling for: {execution_id}")

    def stop_polling(self, execution_id: str):
        """
        Stop polling for a specific execution.

        Args:
            execution_id: Workflow execution ID
        """
        if execution_id in self.polling_tasks:
            self.polling_tasks[execution_id].cancel()
            logger.info(f"{LOG_PREFIX_POLLING} Stopped polling for: {execution_id}")

    def stop_all_polling(self):
        """Stop all polling tasks."""
        logger.info(f"{LOG_PREFIX_POLLING} Stopping all polling tasks")

        for task in self.polling_tasks.values():
            task.cancel()

        self.polling_tasks.clear()
        self.polling_configs.clear()

    def get_active_polls(self) -> Dict[str, EmailPollingConfig]:
        """
        Get currently active polling configurations.

        Returns:
            Dict of execution_id -> EmailPollingConfig
        """
        return self.polling_configs.copy()

    def is_polling(self, execution_id: str) -> bool:
        """
        Check if polling is active for an execution.

        Args:
            execution_id: Workflow execution ID

        Returns:
            True if polling is active
        """
        return execution_id in self.polling_tasks


# Singleton instance
_email_polling_service: Optional[EmailPollingService] = None


def get_email_polling_service() -> EmailPollingService:
    """
    Get the email polling service instance (singleton).

    Returns:
        EmailPollingService instance
    """
    global _email_polling_service

    if _email_polling_service is None:
        _email_polling_service = EmailPollingService()
        logger.info(f"{LOG_PREFIX_POLLING} Email polling service singleton created")

    return _email_polling_service


# Backwards compatibility
email_polling_service = get_email_polling_service()
