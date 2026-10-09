"""
Database tracking for agent subgraph execution.

This module handles creating and updating database execution records
for sub-agents during subgraph execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.execution.history import ExecutionHistoryService
from backend.services.config import get_logger


db_tracker_logger = get_logger("subgraph.agent.db_tracker")


async def create_agent_execution_record(
    agent_node: EnhancedNodeData,
    parent_db_execution_id: Optional[str],
    parent_node_id: str,
    parent_node_execution_id: Optional[str],
    execution_order: int,
    task_description: str,
    invocation_index: Optional[int] = None,
) -> Optional[int]:
    """
    Create a database execution record for a sub-agent.

    Args:
        agent_node: The agent node being executed
        parent_db_execution_id: Parent graph's database execution ID
        parent_node_id: Parent orchestrator's node ID (for logging)
        parent_node_execution_id: Parent's database node execution record ID
        execution_order: Current execution order
        task_description: The task being performed
        invocation_index: Which invocation of this subagent (1st, 2nd, etc.)

    Returns:
        The database node execution ID, or None if creation failed
    """
    if not parent_db_execution_id:
        db_tracker_logger.debug(
            f"No parent DB execution ID, skipping record creation for {agent_node.name}"
        )
        return None

    try:
        db_tracker_logger.info(
            f"[SUB-AGENT DB] Creating sub-agent execution for {agent_node.name}"
        )
        db_tracker_logger.info(
            f"[SUB-AGENT DB] parent_node_id from state: {parent_node_id}"
        )
        db_tracker_logger.info(
            f"[SUB-AGENT DB] parent_node_execution_id: {parent_node_execution_id}"
        )
        db_tracker_logger.info(
            f"[SUB-AGENT DB] agent_node.uniq_id: {agent_node.uniq_id}"
        )
        db_tracker_logger.info("[SUB-AGENT DB] is_sub_agent: True")

        node_exec = ExecutionHistoryService.create_node_execution(
            graph_execution_id=parent_db_execution_id,
            node_id=agent_node.uniq_id,
            node_name=agent_node.name,
            node_type=NodeType.AGENT.value,
            execution_order=execution_order,
            input_data={"task": task_description},
            is_sub_agent=True,
            parent_agent_id=parent_node_execution_id,
            invocation_index=invocation_index,
        )

        node_exec_id = node_exec["id"]
        ExecutionHistoryService.start_node_execution(node_exec_id)

        db_tracker_logger.info(f"Created sub-agent execution record: {node_exec_id}")
        return node_exec_id

    except Exception as e:
        db_tracker_logger.error(f"Failed to create sub-agent execution record: {e}")
        return None


async def complete_agent_execution_record(
    node_exec_id: Optional[int],
    agent_node: EnhancedNodeData,
    response_content: str,
    tool_execution_tracker: list,
    token_counts: Optional[Dict[str, int]],
    start_time: datetime,
    end_time: datetime,
    input_message: Optional[str] = None,
    message_structure: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Complete a database execution record for a sub-agent.

    Args:
        node_exec_id: The database node execution ID
        agent_node: The agent node that was executed
        response_content: The agent's response
        tool_execution_tracker: List of tool executions
        token_counts: Token usage information
        start_time: Execution start time
        end_time: Execution end time
        input_message: The input message sent to the agent (for message structure)
        message_structure: Full conversation message structure from async executor

    Returns:
        Complete node execution data from database, or None if update failed
    """
    if not node_exec_id:
        db_tracker_logger.debug(
            f"No node execution ID, skipping completion for {agent_node.name}"
        )
        return None

    try:
        from backend.services.trace.cost_calculator import build_llm_metadata

        llm_metadata = build_llm_metadata(
            agent_node,
            token_counts,
            start_time=start_time.timestamp(),
            end_time=end_time.timestamp(),
        )

        # Use full conversation message_structure from async executor, or build a
        # minimal fallback from available data
        if not message_structure:
            message_structure = _build_message_structure(
                input_message or "",
                response_content,
                token_counts,
                tool_execution_tracker,
            )

        ExecutionHistoryService.complete_node_execution(
            node_execution_id=node_exec_id,
            status="completed",
            output_data={
                "response": response_content,
                "tool_executions": tool_execution_tracker,
            },
            token_counts=token_counts,
            llm_metadata=llm_metadata,
            message_structure=message_structure,
        )

        db_tracker_logger.info(f"Completed sub-agent execution record: {node_exec_id}")

        if token_counts:
            db_tracker_logger.info(
                f"Sub-agent token usage - Input: {token_counts.get('input_tokens', 0)}, "
                f"Output: {token_counts.get('output_tokens', 0)}"
            )

        # Retrieve complete node execution data
        return _get_complete_node_data(node_exec_id, agent_node.name)

    except Exception as e:
        db_tracker_logger.error(f"Failed to complete sub-agent execution record: {e}")
        return None


async def fail_agent_execution_record(
    node_exec_id: Optional[int],
    agent_node: EnhancedNodeData,
    error: str,
) -> bool:
    """
    Mark a database execution record as failed for a sub-agent.

    Args:
        node_exec_id: The database node execution ID
        agent_node: The agent node that failed
        error: The error message

    Returns:
        True if update succeeded, False otherwise
    """
    if not node_exec_id:
        db_tracker_logger.debug(
            f"No node execution ID, skipping failure for {agent_node.name}"
        )
        return False

    try:
        ExecutionHistoryService.complete_node_execution(
            node_execution_id=node_exec_id,
            status="failed",
            output_data={"error": error},
        )
        db_tracker_logger.info(f"Marked sub-agent execution as failed: {node_exec_id}")
        return True

    except Exception as e:
        db_tracker_logger.error(
            f"Failed to update error status for {agent_node.name}: {e}"
        )
        return False


def _get_complete_node_data(
    node_exec_id: int, node_name: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve complete node execution data from database.

    Args:
        node_exec_id: The database node execution ID
        node_name: The node name (for logging)

    Returns:
        Complete node execution data, or None if retrieval failed
    """
    try:
        node_exec_data = ExecutionHistoryService.get_node_execution_by_id(node_exec_id)

        if node_exec_data and isinstance(node_exec_data, dict):
            db_tracker_logger.info(
                f"Retrieved complete data for {node_name}: "
                f"duration={node_exec_data.get('duration_seconds')}s, "
                f"tokens={node_exec_data.get('total_tokens')}, "
                f"has_input_data={node_exec_data.get('input_data') is not None}"
            )
            return node_exec_data
        else:
            db_tracker_logger.warning(
                f"No data returned for node execution {node_exec_id}"
            )
            return None

    except Exception as e:
        db_tracker_logger.warning(
            f"Failed to get complete node data for {node_name}: {e}"
        )
        return None


def _build_message_structure(
    input_message: str,
    response_content: str,
    token_counts: Optional[Dict[str, int]],
    tool_execution_tracker: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Build message structure for trace viewer from available execution data."""
    messages = []

    input_tokens = token_counts.get("input_tokens", 0) if token_counts else 0
    messages.append(
        {
            "role": "human",
            "content": input_message[:1000] if input_message else "",
            "token_count": input_tokens,
        }
    )

    tool_calls = []
    if tool_execution_tracker:
        for tool_exec in tool_execution_tracker:
            tool_name = tool_exec.get("tool") or tool_exec.get("tool_name") or "unknown"
            tool_calls.append({"name": tool_name})

    output_tokens = token_counts.get("output_tokens", 0) if token_counts else 0
    assistant_msg: Dict[str, Any] = {
        "role": "assistant",
        "content": response_content[:1000] if response_content else "",
        "token_count": output_tokens,
    }
    if tool_calls:
        assistant_msg["tool_calls"] = tool_calls

    messages.append(assistant_msg)

    return {
        "messages": messages,
        "message_count": len(messages),
    }
