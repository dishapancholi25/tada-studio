"""Execution tracking service for HTTP execution API.

This module provides functions to track and query execution status
for HTTP-triggered workflows.
"""

from typing import Optional

from backend.services.config import get_logger
from backend.services.dependency_injection import get_execution_engine

from ..models import ExecutionState, LatestExecutionResponse


logger = get_logger(__name__)


class ExecutionTracker:
    """Service for tracking and querying execution status.

    This service provides methods to find and retrieve information about
    active and completed executions.
    """

    @staticmethod
    def get_latest_execution(graph_name: str) -> LatestExecutionResponse:
        """Get the latest HTTP-triggered execution for a workflow.

        Searches through active executions to find the most recent one
        for the specified workflow.

        Args:
            graph_name: Name of the workflow

        Returns:
            LatestExecutionResponse with execution details if found

        Example:
            >>> response = ExecutionTracker.get_latest_execution("my-workflow")
            >>> if response.has_active_execution:
            ...     print(f"Execution {response.execution_id} is {response.status}")
        """
        logger.debug(f"[EXEC-TRACKER] Finding latest execution for '{graph_name}'")

        latest_execution: Optional[ExecutionState] = None
        latest_time: Optional[str] = None

        try:
            active_executions = get_execution_engine().active_executions

            for exec_id, exec_data in active_executions.items():
                if exec_data.get("graph_name") == graph_name:
                    exec_time = exec_data.get("start_time")

                    if latest_time is None or (exec_time and exec_time > latest_time):
                        latest_execution = exec_data  # type: ignore
                        latest_time = exec_time

            if latest_execution:
                logger.info(
                    f"[EXEC-TRACKER] Found latest execution for '{graph_name}': {latest_execution['execution_id']}"
                )
                return LatestExecutionResponse(
                    success=True,
                    has_active_execution=True,
                    execution_id=latest_execution["execution_id"],
                    status=latest_execution.get("status", "unknown"),
                    start_time=latest_execution.get("start_time"),
                    db_execution_id=latest_execution.get("db_execution_id"),
                )
            else:
                logger.debug(
                    f"[EXEC-TRACKER] No active execution found for '{graph_name}'"
                )
                return LatestExecutionResponse(success=True, has_active_execution=False)

        except Exception as e:
            logger.error(
                f"[EXEC-TRACKER] Error finding latest execution for '{graph_name}': {e}"
            )
            return LatestExecutionResponse(success=False, has_active_execution=False)

    @staticmethod
    def get_execution_state(execution_id: str) -> Optional[ExecutionState]:
        """Get the current state of an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            ExecutionState if found, None otherwise

        Example:
            >>> state = ExecutionTracker.get_execution_state("exec_123")
            >>> if state:
            ...     print(f"Status: {state['status']}")
        """
        try:
            active_executions = get_execution_engine().active_executions
            exec_data = active_executions.get(execution_id)

            if exec_data:
                logger.debug(
                    f"[EXEC-TRACKER] Found execution state for '{execution_id}'"
                )
                return exec_data  # type: ignore
            else:
                logger.debug(
                    f"[EXEC-TRACKER] No state found for execution '{execution_id}'"
                )
                return None

        except Exception as e:
            logger.error(
                f"[EXEC-TRACKER] Error getting execution state for '{execution_id}': {e}"
            )
            return None

    @staticmethod
    def is_execution_complete(execution_id: str) -> bool:
        """Check if an execution is complete (succeeded or failed).

        Args:
            execution_id: Execution identifier

        Returns:
            True if execution is complete, False otherwise

        Example:
            >>> if ExecutionTracker.is_execution_complete("exec_123"):
            ...     print("Execution finished!")
        """
        state = ExecutionTracker.get_execution_state(execution_id)

        if not state:
            logger.debug(
                f"[EXEC-TRACKER] Execution '{execution_id}' not found (assumed complete)"
            )
            return True  # If not in active executions, assume complete

        status = state.get("status")
        is_complete = status in ["completed", "failed"]

        logger.debug(
            f"[EXEC-TRACKER] Execution '{execution_id}' complete: {is_complete} (status: {status})"
        )

        return is_complete

    @staticmethod
    def get_execution_status(execution_id: str) -> Optional[str]:
        """Get the current status of an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Status string if found, None otherwise

        Example:
            >>> status = ExecutionTracker.get_execution_status("exec_123")
            >>> print(f"Status: {status}")  # "running", "completed", etc.
        """
        state = ExecutionTracker.get_execution_state(execution_id)

        if state:
            status = state.get("status")
            logger.debug(f"[EXEC-TRACKER] Execution '{execution_id}' status: {status}")
            return status
        else:
            logger.debug(
                f"[EXEC-TRACKER] No status found for execution '{execution_id}'"
            )
            return None


# Singleton instance
execution_tracker = ExecutionTracker()


def get_execution_tracker() -> ExecutionTracker:
    """Get the execution tracker service instance.

    Returns:
        ExecutionTracker instance

    Example:
        >>> from backend.api.http_execution.services.execution_tracker import get_execution_tracker
        >>> tracker = get_execution_tracker()
        >>> latest = tracker.get_latest_execution("my-workflow")
    """
    return execution_tracker
