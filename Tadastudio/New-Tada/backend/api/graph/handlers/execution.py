"""Graph execution handlers.

This module provides handler functions for graph execution operations.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request

from backend.api.http_execution.utils.constants import sanitize_graph_name
from backend.services.auth import extract_token_from_request
from backend.services.authorization import require_workflow_access
from backend.services.config import get_logger
from backend.services.dependency_injection import (
    get_execution_engine,
    get_graph_manager,
)
from backend.services.execution.history import ExecutionHistoryService
from backend.services.websocket import manager as ws_manager

from ..constants import (
    EXECUTION_ID_DATE_FORMAT,
    EXECUTION_ID_PREFIX,
    LOG_PREFIX,
    MSG_EXECUTION_CANCELLED,
    MSG_EXECUTION_COMPLETED,
    MSG_EXECUTION_STARTED,
)
from ..dependencies import get_user_identifier
from ..exceptions import (
    ExecutionNotFoundError,
    GraphNotFoundError,
    GraphValidationError,
    InvalidRequestError,
)
from ..models import ChatRequest, GraphExecutionRequest
from ..services.execution_manager import (
    execution_manager,
    get_execution_status_with_nodes,
)

logger = get_logger(__name__)


async def handle_execute_graph(
    request: GraphExecutionRequest,
    current_user: Dict[str, Any],
    http_request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Execute a graph using the execution engine.

    Args:
        request: Graph execution request
        current_user: Current user from JWT token
        http_request: FastAPI Request object for extracting access token

    Returns:
        Dictionary with success status, message, execution ID, and status

    Raises:
        GraphNotFoundError: If graph not found
        GraphValidationError: If graph validation fails
    """
    user_identifier = get_user_identifier(current_user)

    # Extract user's access token for MCP servers with oauth2 auth_type
    user_access_token = None
    if http_request:
        user_access_token = extract_token_from_request(http_request)
        if user_access_token:
            logger.debug(
                f"{LOG_PREFIX} Extracted user access token (length: {len(user_access_token)})"
            )

    logger.info(f"{LOG_PREFIX} === EXECUTE GRAPH REQUEST ===")
    logger.info(f"{LOG_PREFIX} Graph name: {request.graph_name}")
    logger.info(f"{LOG_PREFIX} User: {user_identifier}")
    logger.info(f"{LOG_PREFIX} Initial input: {request.initial_input}")
    logger.info(f"{LOG_PREFIX} Async execution: {request.async_execution}")

    require_workflow_access(current_user, request.graph_name)

    graph = get_graph_manager().get_graph(request.graph_name)
    if not graph:
        logger.info(
            f"{LOG_PREFIX} Graph not in memory, attempting to load from disk..."
        )
        graph = get_graph_manager().load_graph(request.graph_name, user_identifier)

    if not graph:
        logger.error(
            f"{LOG_PREFIX} Graph '{request.graph_name}' not found for user '{user_identifier}'"
        )
        raise GraphNotFoundError(request.graph_name)

    # Get workflow_id and graph_definition_id for execution tracking
    workflow_id = getattr(graph, "workflow_id", None)
    graph_definition_id = getattr(graph, "definition_id", None)

    if workflow_id is None or graph_definition_id is None:
        logger.warning(
            f"{LOG_PREFIX} [EXEC TRACKING] Graph '{request.graph_name}' missing tracking IDs! "
            f"workflow_id={workflow_id}, definition_id={graph_definition_id}. "
            f"Execution will NOT be filterable by user access control."
        )
    else:
        logger.info(
            f"{LOG_PREFIX} [EXEC TRACKING] Execution will be tracked: workflow_id={workflow_id}, "
            f"definition_id={graph_definition_id}"
        )

    logger.info(f"{LOG_PREFIX} Graph loaded successfully: {graph.name}")
    logger.info(f"{LOG_PREFIX} Graph nodes: {[n.name for n in graph.nodes]}")
    logger.info(
        f"{LOG_PREFIX} Graph connections: {[(c.source_id, c.target_id) for c in graph.connections]}"
    )

    # Validate graph before execution
    validation_result = graph.validate()
    logger.info(f"{LOG_PREFIX} Validation result: {validation_result}")

    if not validation_result["is_valid"]:
        error_message = (
            f"Graph validation failed for '{request.graph_name}': "
            f"{validation_result['errors']}"
        )
        logger.error(f"{LOG_PREFIX} {error_message}")
        for error in validation_result.get("errors", []):
            logger.error(f"{LOG_PREFIX}   - Validation error: {error}")
        raise GraphValidationError(request.graph_name, validation_result["errors"])

    # Generate execution ID
    execution_id = f"{EXECUTION_ID_PREFIX}{datetime.now().strftime(EXECUTION_ID_DATE_FORMAT)}_{sanitize_graph_name(request.graph_name)}_{uuid.uuid4().hex[:6]}"

    # Add file info to initial input if provided
    if request.file_info:
        request.initial_input["file_info"] = request.file_info

    # Execute graph
    if request.async_execution:
        # Pre-register the execution
        get_execution_engine().active_executions[execution_id] = {
            "execution_id": execution_id,
            "status": "pending",
            "start_time": str(datetime.now()),
            "graph_name": graph.name,
            "current_node": None,
            "node_execution_map": {},
            "db_execution_id": None,
        }
        ws_manager.register_pending(execution_id, user_identifier, ttl=30)

        # Execute in thread pool
        execution_manager.submit_execution(
            graph,
            request.initial_input,
            execution_id,
            user_identifier,
            workflow_id,
            graph_definition_id,
            user_access_token=user_access_token,
            trigger_type="editor",
        )

        return {
            "success": True,
            "message": MSG_EXECUTION_STARTED.format(graph_name=request.graph_name),
            "execution_id": execution_id,
            "async": True,
            "status_endpoint": f"/api/graph/execution/{execution_id}/status",
        }
    else:
        # Execute synchronously
        await get_execution_engine().execute_graph(
            graph=graph,
            initial_input=request.initial_input,
            execution_id=execution_id,
            user_id=user_identifier,
            workflow_id=workflow_id,
            graph_definition_id=graph_definition_id,
            user_access_token=user_access_token,
            trigger_type="editor",
        )

        # Get final status
        status = get_execution_engine().get_execution_status(execution_id)

        return {
            "success": True,
            "message": MSG_EXECUTION_COMPLETED.format(graph_name=request.graph_name),
            "execution_id": execution_id,
            "async": False,
            "execution_result": status,
        }


async def handle_get_execution_status(execution_id: str) -> Dict[str, Any]:
    """Get the status of a graph execution with node execution details.

    Args:
        execution_id: Unique execution identifier

    Returns:
        Dictionary with success status and execution status

    Raises:
        ExecutionNotFoundError: If execution not found
    """
    logger.info(f"{LOG_PREFIX} Getting execution status for '{execution_id}'")

    status = get_execution_status_with_nodes(execution_id)

    if not status:
        raise ExecutionNotFoundError(execution_id)

    return {"success": True, "execution_status": status}


async def handle_get_execution_history(execution_id: str) -> Dict[str, Any]:
    """Get detailed execution history for a graph execution.

    Args:
        execution_id: Unique execution identifier

    Returns:
        Dictionary with success status, execution ID, and history

    Raises:
        ExecutionNotFoundError: If execution not found
    """
    logger.info(f"{LOG_PREFIX} Getting execution history for '{execution_id}'")

    history = get_execution_engine().get_execution_history(execution_id)

    if history is None:
        raise ExecutionNotFoundError(execution_id)

    return {
        "success": True,
        "execution_id": execution_id,
        "execution_history": history,
    }


def _entry_field(entry: Any, name: str) -> Any:
    """Read a field from an execution record held in engine memory.

    Records are dictionaries, but tolerate objects so a future change of
    representation does not silently break scoping.

    Args:
        entry: Execution record from the engine
        name: Field name

    Returns:
        The field value, or None when absent
    """
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


def _accessible_graph_filter(current_user: Optional[Dict[str, Any]]):
    """Build a predicate deciding whether a caller may see an execution.

    Engine records carry a graph name but no owner, so entitlement is decided
    by workflow access. Results are memoised per graph name to keep the check
    to one query per distinct workflow.

    Admins keep the unscoped view. Without a caller, or for a record with no
    graph name, the predicate denies: this endpoint previously returned every
    tenant's executions (ISG F-40 row 7), so it fails closed.

    Args:
        current_user: JWT claims of the caller, if any

    Returns:
        Callable taking an execution record and returning True when visible
    """
    if not current_user:
        return lambda entry: False

    if current_user.get("is_admin", False):
        return lambda entry: True

    from fastapi import HTTPException

    from backend.services.authorization.helpers import verify_workflow_access

    user_identifier = get_user_identifier(current_user)
    decided: Dict[str, bool] = {}

    def _visible(entry: Any) -> bool:
        graph_name = _entry_field(entry, "graph_name")
        if not graph_name:
            return False
        if graph_name not in decided:
            try:
                verify_workflow_access(user_identifier, graph_name, False)
                decided[graph_name] = True
            except HTTPException:
                decided[graph_name] = False
        return decided[graph_name]

    return _visible


async def handle_list_executions(
    limit: int = 50, current_user: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """List recent executions the caller is entitled to see.

    Args:
        limit: Maximum number of executions to return
        current_user: JWT claims of the caller, used to scope the results

    Returns:
        Dictionary with success status, active and recent executions
    """
    logger.info(f"{LOG_PREFIX} Listing executions (limit: {limit})")

    is_visible = _accessible_graph_filter(current_user)

    # Get recent executions from history, newest first, scoped to the caller
    history = get_execution_engine().execution_history or []
    recent_executions = [entry for entry in reversed(history) if is_visible(entry)][
        :limit
    ]

    # Get active executions
    active_executions = []
    for exec_id, entry in get_execution_engine().active_executions.items():
        if not is_visible(entry):
            continue
        active_executions.append(
            {
                "execution_id": exec_id,
                "status": _entry_field(entry, "status"),
                "start_time": _entry_field(entry, "start_time"),
                "graph_name": _entry_field(entry, "graph_name"),
                "current_node": _entry_field(entry, "current_node"),
                "current_node_name": _entry_field(entry, "current_node_name"),
            }
        )

    return {
        "success": True,
        "active_executions": active_executions,
        "recent_executions": recent_executions,
    }


async def handle_get_agent_tool_executions(
    execution_id: str, agent_id: str
) -> Dict[str, Any]:
    """Get all tool executions for a specific agent within an execution.

    Args:
        execution_id: Unique execution identifier
        agent_id: Agent node ID

    Returns:
        Dictionary with success status and tool executions

    Raises:
        ExecutionNotFoundError: If execution not found
    """
    logger.info(
        f"{LOG_PREFIX} Getting agent tool executions for agent '{agent_id}' "
        f"in execution '{execution_id}'"
    )

    # Get the execution data
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

    if not execution_data:
        raise ExecutionNotFoundError(execution_id)

    # Filter node executions for tools with this parent agent
    tool_executions = []
    for node_exec in execution_data.get("node_executions", []):
        parent_id = node_exec.get("parent_agent_id")
        if not parent_id and node_exec.get("node_metadata"):
            parent_id = node_exec["node_metadata"].get("parent_agent_id")

        if parent_id == agent_id:
            tool_executions.append(node_exec)

    # Group by tool type
    grouped_executions = {
        "DATABASE_QUERY": [],
        "DOCUMENT_SEARCH": [],
        "HTTP_REQUEST": [],
        "WEB_SEARCH": [],
    }

    for exec in tool_executions:
        node_type = exec.get("node_type", "")
        if node_type in grouped_executions:
            grouped_executions[node_type].append(exec)

    return {
        "success": True,
        "agent_id": agent_id,
        "execution_id": execution_id,
        "total_tool_executions": len(tool_executions),
        "grouped_executions": grouped_executions,
        "tool_executions": tool_executions,
    }


async def handle_cancel_execution(execution_id: str) -> Dict[str, Any]:
    """Cancel a running execution.

    Args:
        execution_id: Unique execution identifier

    Returns:
        Dictionary with success status and message

    Raises:
        ExecutionNotFoundError: If execution not found
        InvalidRequestError: If execution is not running
    """
    logger.info(f"{LOG_PREFIX} Cancelling execution '{execution_id}'")

    context = get_execution_engine().active_executions.get(execution_id)

    if not context:
        raise ExecutionNotFoundError(execution_id)

    if context.status != "running":
        raise InvalidRequestError(f"Execution '{execution_id}' is not running")

    # Mark as cancelled
    context.status = "cancelled"
    context.error = "Execution cancelled by user"
    context.end_time = datetime.now()

    # Move to history
    get_execution_engine().execution_history.append(
        {
            "execution_id": execution_id,
            "graph_name": getattr(context, "graph_name", "unknown"),
            "status": context.status,
            "start_time": context.start_time.isoformat(),
            "end_time": context.end_time.isoformat(),
            "error": context.error,
            "steps_count": len(context.history),
        }
    )

    # Remove from active
    del get_execution_engine().active_executions[execution_id]

    logger.info(f"{LOG_PREFIX} Execution '{execution_id}' cancelled successfully")
    return {
        "success": True,
        "message": MSG_EXECUTION_CANCELLED.format(execution_id=execution_id),
    }


async def handle_chat_with_agent(
    graph_name: str, agent_id: str, request: ChatRequest
) -> Dict[str, Any]:
    """Chat with an agent using LangChain.

    Args:
        graph_name: Name of the graph (URL-encoded)
        agent_id: Agent node ID
        request: Chat request

    Returns:
        Dictionary with success status, response, agent name, and tools used

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If agent not found
    """
    from urllib.parse import unquote

    from backend.models.workflow import NodeType

    from ..exceptions import NodeNotFoundError

    # URL decode the graph name
    graph_name = unquote(graph_name)
    logger.info(
        f"{LOG_PREFIX} Chatting with agent '{agent_id}' in graph '{graph_name}'"
    )

    graph = get_graph_manager().get_graph(graph_name)
    if not graph:
        raise GraphNotFoundError(graph_name)

    agent_node = graph.get_node_by_id(agent_id)
    if not agent_node or agent_node.type != NodeType.AGENT:
        raise NodeNotFoundError(agent_id, graph_name)

    # Use simple execution
    response = get_graph_manager().execute_simple_chat(agent_node, request.message)

    return {
        "success": True,
        "response": response.content,
        "agent_name": agent_node.name,
        "tools_used": agent_node.agent_config.tools if agent_node.agent_config else [],
    }
