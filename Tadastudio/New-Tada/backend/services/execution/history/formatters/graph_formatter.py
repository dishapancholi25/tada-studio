"""Graph execution formatter.

Converts GraphExecution ORM objects to dictionary format for API responses.
"""

from typing import Any, Dict

from backend.models import GraphExecution

from .node_formatter import format_node_execution_to_dict


def format_graph_execution_to_dict(execution: GraphExecution) -> Dict[str, Any]:
    """Convert a GraphExecution ORM object to a dictionary.

    Includes all node executions as nested dictionaries.

    Args:
        execution: GraphExecution ORM object with node_executions loaded

    Returns:
        Dictionary representation of the graph execution with nested nodes

    Examples:
        >>> from backend.models import GraphExecution
        >>> exec_obj = GraphExecution(graph_id="g1", graph_name="Test Graph")
        >>> result = format_graph_execution_to_dict(exec_obj)
        >>> result["graph_id"]
        'g1'
    """
    # Resolve graph version from the linked graph definition
    graph_version = None
    if execution.graph_definition_id:
        try:
            gd_rel = execution.graph_definition_rel
            if gd_rel:
                graph_version = gd_rel.version
        except Exception:
            pass

    exec_dict = {
        "id": str(execution.id),
        "execution_id": execution.websocket_execution_id,
        "graph_id": execution.graph_id,
        "graph_name": execution.graph_name,
        "graph_definition": execution.graph_definition,
        "graph_definition_id": execution.graph_definition_id,
        "graph_version": graph_version,
        "status": execution.status,
        "start_time": execution.start_time.isoformat()
        if execution.start_time
        else None,
        "end_time": execution.end_time.isoformat() if execution.end_time else None,
        "duration_seconds": execution.duration_seconds,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "error_message": execution.error_message,
        "user_id": execution.user_id,
        "created_at": execution.created_at.isoformat()
        if execution.created_at
        else None,
        "node_executions": [],
        "trigger_type": execution.trigger_type,
    }

    # Convert node executions
    for node_exec in execution.node_executions:
        node_dict = format_node_execution_to_dict(node_exec)
        exec_dict["node_executions"].append(node_dict)

    return exec_dict


def format_graph_execution_basic(
    execution: GraphExecution,
    node_count: int = 0,
    completed_node_count: int = 0,
) -> Dict[str, Any]:
    """Convert a GraphExecution to a basic dictionary (without nodes).

    Used for list views where node details are not needed.
    Includes node count fields for UI display.

    Args:
        execution: GraphExecution ORM object
        node_count: Pre-computed total node count
        completed_node_count: Pre-computed completed node count

    Returns:
        Dictionary with essential graph execution fields (no node_executions)
    """
    graph_version = None
    if execution.graph_definition_id:
        try:
            gd_rel = execution.graph_definition_rel
            if gd_rel:
                graph_version = gd_rel.version
        except Exception:
            pass

    return {
        "id": str(execution.id),
        "execution_id": execution.websocket_execution_id,
        "graph_id": execution.graph_id,
        "graph_name": execution.graph_name,
        "workflow_id": execution.workflow_id,
        "graph_definition_id": execution.graph_definition_id,
        "graph_version": graph_version,
        "status": execution.status,
        "start_time": execution.start_time.isoformat()
        if execution.start_time
        else None,
        "end_time": execution.end_time.isoformat() if execution.end_time else None,
        "duration_seconds": execution.duration_seconds,
        "user_id": execution.user_id,
        "created_at": execution.created_at.isoformat()
        if execution.created_at
        else None,
        "trigger_type": execution.trigger_type,
        "node_count": node_count,
        "completed_node_count": completed_node_count,
    }
