"""
Node Notification Handler.

This module provides shared functionality for sending WebSocket notifications
during node execution. It's reusable across all node executor types.
"""

from typing import Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.websocket import notifier as ws_notifier
from backend.services.workflow.state import WorkflowState


notification_logger = get_logger("nodes.handlers.notification")


class NodeNotificationHandler:
    """
    Handles WebSocket notifications for node execution.

    Provides methods for sending start, progress, complete, and error notifications
    with proper error handling and logging.

    Example:
        >>> handler = NodeNotificationHandler()
        >>> await handler.notify_start(node, state, "AGENT", node_exec_id)
        >>> await handler.notify_complete(node, state, output, "AGENT", node_exec_id)
    """

    def __init__(self, ws_notifier_service: Optional[Any] = None):
        """
        Initialize notification handler.

        Args:
            ws_notifier_service: Optional notifier service (uses global if not provided)
        """
        self.ws_notifier = ws_notifier_service or ws_notifier

    async def notify_start(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_type: str,
        node_exec_id: Optional[int] = None,
        execution_order: Optional[int] = None,
        is_sub_agent: bool = False,
        parent_agent_id: Optional[str] = None,
        step: Optional[int] = None,
    ) -> bool:
        """
        Send WebSocket notification when node starts execution.

        Args:
            node: The node being executed
            state: Current workflow state
            node_type: Type of node (e.g., "AGENT", "HTTP_REQUEST")
            node_exec_id: Optional database node execution ID
            execution_order: Optional execution order
            is_sub_agent: Whether this is a sub-agent
            parent_agent_id: Parent agent ID if this is a sub-agent
            step: Optional LangGraph step for iteration discrimination

        Returns:
            True if notification sent successfully, False otherwise
        """
        ws_execution_id = state.get("execution_id")
        if not self.ws_notifier or not ws_execution_id:
            notification_logger.debug(
                f"WebSocket notifications disabled for {node.name}"
            )
            return False

        try:
            notification_logger.debug(
                f"Sending start notification for {node.name} (type={node_type})"
            )

            await self.ws_notifier.on_node_start(
                ws_execution_id,
                node.uniq_id,
                node.name,
                node_type,
                is_sub_agent,
                parent_agent_id,
                node_exec_id,
                execution_order,
                step,
            )

            notification_logger.info(
                f"[NODE-START-DEBUG] Sent start notification: node_name={node.name}, "
                f"node_id={node.uniq_id}, node_type={node_type}, "
                f"db_node_id={node_exec_id}, execution_order={execution_order}, step={step}"
            )
            return True

        except Exception as e:
            notification_logger.error(
                f"Failed to send start notification for {node.name}: {e}",
                exc_info=True,
            )
            return False

    async def notify_progress(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        progress_data: Dict[str, Any],
    ) -> bool:
        """
        Send WebSocket notification for progress updates.

        Args:
            node: The node being executed
            state: Current workflow state
            progress_data: Progress data to send

        Returns:
            True if notification sent successfully, False otherwise
        """
        ws_execution_id = state.get("execution_id")
        if not self.ws_notifier or not ws_execution_id:
            return False

        try:
            notification_logger.debug(f"Sending progress notification for {node.name}")

            # This would use a progress notification method
            # For now, we'll use the existing methods
            # Future enhancement: add on_node_progress method to ws_notifier
            return True

        except Exception as e:
            notification_logger.error(
                f"Failed to send progress notification for {node.name}: {e}",
                exc_info=True,
            )
            return False

    async def notify_complete(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        output: Dict[str, Any],
        node_type: str,
        node_exec_id: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        input_data: Optional[Dict[str, Any]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        token_counts: Optional[Dict[str, int]] = None,
        execution_order: Optional[int] = None,
        is_sub_agent: bool = False,
        parent_agent_id: Optional[str] = None,
        step: Optional[int] = None,
    ) -> bool:
        """
        Send WebSocket notification when node completes execution.

        Args:
            node: The node that completed
            state: Current workflow state
            output: Node output data
            node_type: Type of node
            node_exec_id: Optional database node execution ID
            duration_seconds: Optional execution duration
            input_data: Optional input data
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            token_counts: Optional token usage counts
            execution_order: Optional execution order
            is_sub_agent: Whether this is a sub-agent
            parent_agent_id: Parent agent ID if this is a sub-agent
            step: Optional LangGraph step for iteration discrimination

        Returns:
            True if notification sent successfully, False otherwise
        """
        ws_execution_id = state.get("execution_id")
        if not self.ws_notifier or not ws_execution_id:
            return False

        try:
            notification_logger.debug(
                f"Sending complete notification for {node.name} (type={node_type})"
            )

            # Extract token counts if available
            input_tokens = None
            output_tokens = None
            total_tokens = None
            if token_counts:
                input_tokens = token_counts.get("input_tokens")
                output_tokens = token_counts.get("output_tokens")
                total_tokens = token_counts.get("total_tokens")

            await self.ws_notifier.on_node_complete(
                ws_execution_id,
                node.uniq_id,
                node.name,
                output,
                node_type,
                duration_seconds,
                input_data,
                start_time,
                end_time,
                input_tokens,
                output_tokens,
                total_tokens,
                is_sub_agent,
                parent_agent_id,
                node_exec_id,
                execution_order,
                step,
            )

            notification_logger.info(
                f"[NODE-COMPLETE-DEBUG] Sent complete notification: node_name={node.name}, "
                f"node_id={node.uniq_id}, node_type={node_type}, "
                f"db_node_id={node_exec_id}, execution_order={execution_order}, step={step}"
            )
            return True

        except Exception as e:
            notification_logger.error(
                f"Failed to send complete notification for {node.name}: {e}",
                exc_info=True,
            )
            return False

    async def notify_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        error_message: str,
        node_type: str,
        node_exec_id: Optional[int] = None,
    ) -> bool:
        """
        Send WebSocket notification when node encounters an error.

        Args:
            node: The node that failed
            state: Current workflow state
            error_message: Error message
            node_type: Type of node
            node_exec_id: Optional database node execution ID

        Returns:
            True if notification sent successfully, False otherwise
        """
        ws_execution_id = state.get("execution_id")
        if not self.ws_notifier or not ws_execution_id:
            return False

        try:
            notification_logger.warning(
                f"Sending error notification for {node.name}: {error_message}"
            )

            await self.ws_notifier.on_node_error(
                ws_execution_id,
                node.uniq_id,
                node.name,
                error_message,
                node_type,
                node_exec_id,
            )

            notification_logger.info(
                f"Sent WebSocket error notification for {node.name}"
            )
            return True

        except Exception as e:
            notification_logger.error(
                f"Failed to send error notification for {node.name}: {e}",
                exc_info=True,
            )
            return False
