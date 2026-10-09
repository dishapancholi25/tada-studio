"""
WebSocket notification helpers for subgraph execution.

This module provides reusable functions for sending WebSocket notifications
during subgraph execution (node start, complete, error).
"""

from typing import Any, Dict, Optional

from backend.services.config import get_logger
from backend.services.websocket import notifier as ws_notifier


notifier_logger = get_logger("common.websocket_notifier")


async def send_node_start_notification(
    execution_id: str,
    node_id: str,
    node_name: str,
    node_type: str,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[int] = None,
    step: Optional[int] = None,
) -> bool:
    """
    Send a WebSocket notification when a node starts execution.

    Args:
        execution_id: The parent execution ID
        node_id: The node's unique ID
        node_name: The node's display name
        node_type: The node type (e.g., "AGENT", "TOOL")
        is_sub_agent: Whether this is a sub-agent
        parent_agent_id: The parent agent's ID (if applicable)
        database_node_id: The database node execution ID (if available)
        step: Iteration/step number for distinguishing multiple invocations

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not execution_id or not ws_notifier:
        notifier_logger.debug(
            f"Skipping node start notification for {node_name}: "
            f"execution_id={execution_id is not None}, "
            f"ws_notifier={ws_notifier is not None}"
        )
        return False

    try:
        await ws_notifier.on_node_start(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
            database_node_id=database_node_id,
            step=step,
        )
        return True
    except Exception as e:
        notifier_logger.error(
            f"Failed to send WebSocket start notification for {node_name}: {e}"
        )
        return False


async def send_node_complete_notification(
    execution_id: str,
    node_id: str,
    node_name: str,
    output: Dict[str, Any],
    node_type: str,
    duration_seconds: Optional[float] = None,
    input_data: Optional[Dict[str, Any]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[int] = None,
    step: Optional[int] = None,
) -> bool:
    """
    Send a WebSocket notification when a node completes execution.

    Args:
        execution_id: The parent execution ID
        node_id: The node's unique ID
        node_name: The node's display name
        output: The node's output data
        node_type: The node type (e.g., "AGENT", "TOOL")
        duration_seconds: Execution duration in seconds
        input_data: Input data passed to the node
        start_time: ISO format start time
        end_time: ISO format end time
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        total_tokens: Total tokens used
        is_sub_agent: Whether this is a sub-agent
        parent_agent_id: The parent agent's ID (if applicable)
        database_node_id: The database node execution ID (if available)
        step: Iteration/step number for distinguishing multiple invocations

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not execution_id or not ws_notifier:
        notifier_logger.debug(
            f"Skipping node complete notification for {node_name}: "
            f"execution_id={execution_id is not None}, "
            f"ws_notifier={ws_notifier is not None}"
        )
        return False

    try:
        await ws_notifier.on_node_complete(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            output=output,
            node_type=node_type,
            duration_seconds=duration_seconds,
            input_data=input_data,
            start_time=start_time,
            end_time=end_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
            database_node_id=database_node_id,
            step=step,
        )
        notifier_logger.info(
            f"Sent WebSocket node complete notification for {node_name}"
        )
        return True
    except Exception as e:
        notifier_logger.error(
            f"Failed to send WebSocket complete notification for {node_name}: {e}"
        )
        return False


async def send_node_error_notification(
    execution_id: str,
    node_id: str,
    node_name: str,
    error: str,
) -> bool:
    """
    Send a WebSocket notification when a node encounters an error.

    Args:
        execution_id: The parent execution ID
        node_id: The node's unique ID
        node_name: The node's display name
        error: The error message

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not execution_id or not ws_notifier:
        notifier_logger.debug(
            f"Skipping node error notification for {node_name}: "
            f"execution_id={execution_id is not None}, "
            f"ws_notifier={ws_notifier is not None}"
        )
        return False

    try:
        await ws_notifier.on_node_error(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            error=error,
        )
        notifier_logger.info(f"Sent WebSocket node error notification for {node_name}")
        return True
    except Exception as e:
        notifier_logger.error(
            f"Failed to send WebSocket error notification for {node_name}: {e}"
        )
        return False
