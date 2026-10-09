"""Node execution formatter.

Converts NodeExecution ORM objects to dictionary format for API responses.
"""

from typing import Any, Dict

from backend.models import NodeExecution


def format_node_execution_to_dict(node_exec: NodeExecution) -> Dict[str, Any]:
    """Convert a NodeExecution ORM object to a dictionary.

    Handles optional fields using getattr() with appropriate defaults
    to support backward compatibility with older database records.

    Args:
        node_exec: NodeExecution ORM object

    Returns:
        Dictionary representation of the node execution with all fields

    Examples:
        >>> from backend.models import NodeExecution
        >>> node = NodeExecution(node_id="n1", node_name="Test", node_type="AGENT")
        >>> result = format_node_execution_to_dict(node)
        >>> result["node_id"]
        'n1'
    """
    return {
        "id": str(node_exec.id),
        "node_id": node_exec.node_id,
        "node_name": node_exec.node_name,
        "node_type": node_exec.node_type,
        "execution_order": node_exec.execution_order,
        "status": node_exec.status,
        "start_time": node_exec.start_time.isoformat()
        if node_exec.start_time
        else None,
        "end_time": node_exec.end_time.isoformat() if node_exec.end_time else None,
        "duration_seconds": node_exec.duration_seconds,
        "input_data": node_exec.input_data,
        "output_data": node_exec.output_data,
        "error_message": node_exec.error_message,
        "node_metadata": node_exec.node_metadata,
        # Optional fields - use getattr for backward compatibility
        "is_sub_agent": getattr(node_exec, "is_sub_agent", False),
        "parent_agent_id": getattr(node_exec, "parent_agent_id", None),
        # Review iteration for agent review tracking
        "review_iteration": getattr(node_exec, "review_iteration", None),
        # Token counting fields
        "input_tokens": getattr(node_exec, "input_tokens", None),
        "output_tokens": getattr(node_exec, "output_tokens", None),
        "total_tokens": getattr(node_exec, "total_tokens", None),
        "token_metadata": getattr(node_exec, "token_metadata", None),
        # Enhanced metadata for trace viewer
        "llm_metadata": getattr(node_exec, "llm_metadata", None),
        "message_structure": getattr(node_exec, "message_structure", None),
        "tool_metadata": getattr(node_exec, "tool_metadata", None),
        "orchestration_metadata": getattr(node_exec, "orchestration_metadata", None),
        "memory_metadata": getattr(node_exec, "memory_metadata", None),
        "environment_metadata": getattr(node_exec, "environment_metadata", None),
        # Cost tracking
        "prompt_cost": getattr(node_exec, "prompt_cost", None),
        "completion_cost": getattr(node_exec, "completion_cost", None),
        "total_cost": getattr(node_exec, "total_cost", None),
        # Performance metrics
        "time_to_first_token": getattr(node_exec, "time_to_first_token", None),
        "tokens_per_second": getattr(node_exec, "tokens_per_second", None),
        # Timestamps
        "created_at": node_exec.created_at.isoformat()
        if node_exec.created_at
        else None,
    }


def format_node_execution_basic(node_exec: NodeExecution) -> Dict[str, Any]:
    """Convert a NodeExecution to a basic dictionary (minimal fields).

    Used for list views where full detail is not needed.

    Args:
        node_exec: NodeExecution ORM object

    Returns:
        Dictionary with essential node execution fields
    """
    return {
        "id": str(node_exec.id),
        "node_id": node_exec.node_id,
        "node_name": node_exec.node_name,
        "node_type": node_exec.node_type,
        "execution_order": node_exec.execution_order,
        "status": node_exec.status,
        "start_time": node_exec.start_time.isoformat()
        if node_exec.start_time
        else None,
        "end_time": node_exec.end_time.isoformat() if node_exec.end_time else None,
        "duration_seconds": node_exec.duration_seconds,
        "error_message": node_exec.error_message,
        "is_sub_agent": getattr(node_exec, "is_sub_agent", False),
        "review_iteration": getattr(node_exec, "review_iteration", None),
        "created_at": node_exec.created_at.isoformat()
        if node_exec.created_at
        else None,
    }
