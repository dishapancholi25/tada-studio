"""API endpoints for workflow execution history.

This module provides REST endpoints for querying and managing workflow execution history,
including graph executions, node executions, and execution statistics.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models.execution.execution_feedback import ExecutionFeedback
from backend.models.execution.graph_execution import GraphExecution
from backend.models.guardrails.violation_event import GuardrailViolationEvent
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization import require_execution_access

from ...services.config import get_logger
from ...services.database import get_db
from ...services.execution.history import ExecutionHistoryService
from .dependencies import get_user_identifier
from .models import (
    ExecutionFeedbackResponse,
    ExecutionSummaryResponse,
    SubmitFeedbackRequest,
)

# Get API logger with consistent prefix
logger = get_logger("execution_history_api")

# Create router
router = APIRouter(
    prefix="/api/execution-history",
    tags=["execution-history"],
    dependencies=[Depends(require_active_user), Depends(require_scope("execution:*:read"))],
)


@router.get("/executions")
async def get_executions(
    graph_id: Optional[str] = Query(None, description="Filter by graph ID"),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow UUID"),
    graph_name: Optional[str] = Query(
        None, description="Filter by workflow name (partial, case-insensitive)"
    ),
    status: Optional[str] = Query(
        None, description="Filter by execution status (completed, failed, running)"
    ),
    trigger_type: Optional[str] = Query(
        None, description="Filter by trigger type (editor, api, evaluation, scheduler)"
    ),
    feedback_rating: Optional[str] = Query(
        None, description="Filter by feedback rating (positive, negative)"
    ),
    include_nodes: bool = Query(
        False, description="Include node executions in response"
    ),
    limit: int = Query(20, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user_id: str = Depends(get_user_identifier),
):
    """Get execution history with optional filtering.

    Returns a list of graph executions scoped to the authenticated user's
    accessible workflows. Supports pagination and filtering by graph ID,
    workflow name, and status.

    Args:
        graph_id: Optional filter by specific graph ID
        graph_name: Optional filter by workflow name (partial, case-insensitive)
        status: Optional filter by execution status
        include_nodes: Whether to include node executions (default: False)
        limit: Maximum number of results to return (1-1000)
        offset: Number of results to skip for pagination
        user_id: Authenticated user identifier (injected)

    Returns:
        Dictionary with 'executions', 'total_count', and 'has_more' fields

    Raises:
        HTTPException: 500 error if query fails

    Examples:
        GET /api/execution-history/executions?limit=20
        GET /api/execution-history/executions?graph_name=my_workflow&status=completed
    """
    logger.info(
        f"[EXECUTION-HISTORY-API] GET /executions - user: {user_id}, "
        f"graph_id: {graph_id}, graph_name: {graph_name}, status: {status}, "
        f"trigger_type: {trigger_type}, "
        f"include_nodes: {include_nodes}, limit: {limit}, offset: {offset}"
    )

    try:
        # Get executions filtered by user's accessible workflows
        result = ExecutionHistoryService.get_graph_executions_dict(
            graph_id=graph_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            graph_name=graph_name,
            status=status,
            include_nodes=include_nodes,
            trigger_type=trigger_type,
            feedback_rating=feedback_rating,
            workflow_id=workflow_id,
        )

        logger.info(
            f"[EXECUTION-HISTORY-API] Returning {len(result['executions'])} execution "
            f"records for user {user_id} (total: {result['total_count']})"
        )
        return result

    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get executions for user {user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow-names")
async def get_workflow_names(
    user_id: str = Depends(get_user_identifier),
):
    """Get distinct workflow names accessible to the user.

    Returns a list of unique workflow names for populating filter dropdowns.

    Args:
        user_id: Authenticated user identifier (injected)

    Returns:
        List of workflow name strings, sorted alphabetically

    Raises:
        HTTPException: 500 error if query fails

    Examples:
        GET /api/execution-history/workflow-names
    """
    logger.info(f"[EXECUTION-HISTORY-API] GET /workflow-names - user: {user_id}")

    try:
        workflow_names = ExecutionHistoryService.get_distinct_workflow_names(
            user_id=user_id
        )

        logger.info(
            f"[EXECUTION-HISTORY-API] Returning {len(workflow_names)} workflow names "
            f"for user {user_id}"
        )
        return workflow_names

    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get workflow names for user {user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, user_id: str = Depends(get_user_identifier)):
    """Get a specific execution by ID.

    Retrieves detailed execution information including all node executions.
    Supports lookup by either database UUID or WebSocket execution ID.

    Args:
        execution_id: Database UUID or WebSocket execution ID (e.g., 'exec_12345')
        user_id: Authenticated user identifier (injected)

    Returns:
        Graph execution dictionary with nested node executions

    Raises:
        HTTPException: 403 if user is not authorized, 404 if execution not found, 500 on other errors

    Examples:
        GET /api/execution-history/executions/550e8400-e29b-41d4-a716-446655440000
        GET /api/execution-history/executions/exec_12345
    """
    logger.info(
        f"[EXECUTION-HISTORY-API] GET /executions/{execution_id} - user: {user_id}"
    )

    # Log ID type for debugging
    if execution_id.startswith("exec_"):
        logger.debug(
            f"[EXECUTION-HISTORY-API] Querying by WebSocket ID: {execution_id}"
        )
    else:
        logger.debug(
            f"[EXECUTION-HISTORY-API] Querying by database UUID: {execution_id}"
        )

    try:
        execution = ExecutionHistoryService.get_graph_execution_dict(execution_id)

        if not execution:
            id_type = "WebSocket ID" if execution_id.startswith("exec_") else "UUID"
            logger.warning(
                f"[EXECUTION-HISTORY-API] Execution not found: {execution_id} "
                f"(searched by {id_type})"
            )
            raise HTTPException(status_code=404, detail="Execution not found")

        # Verify the authenticated user owns this execution
        exec_user_id = execution.get("user_id")
        if exec_user_id and exec_user_id != user_id:
            logger.warning(
                f"[EXECUTION-HISTORY-API] Unauthorized access attempt: user {user_id} "
                f"tried to access execution {execution_id} owned by {exec_user_id}"
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to access this execution"
            )

        logger.info(
            f"[EXECUTION-HISTORY-API] Found execution: DB ID={execution.get('id')}, "
            f"Status={execution.get('status')}"
        )

        # Log MCP node information if present
        _log_mcp_nodes(execution, execution_id)

        logger.info(
            f"[EXECUTION-HISTORY-API] Returning execution {execution_id} with "
            f"{len(execution.get('node_executions', []))} node executions"
        )
        return execution

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get execution {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/guardrail-violations")
async def get_execution_guardrail_violations(
    execution_id: str,
    user_id: str = Depends(get_user_identifier),
):
    """Get guardrail violations for a specific execution.

    Args:
        execution_id: Graph execution ID
        user_id: Authenticated user identifier (injected)

    Returns:
        List of violation events for the execution

    Raises:
        HTTPException: 403 if not authorized, 404 if execution not found
    """
    logger.info(
        f"[EXECUTION-HISTORY-API] GET /executions/{execution_id}/guardrail-violations - user: {user_id}"
    )

    try:
        with get_db() as db:
            execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == execution_id)
                .first()
            )
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")

            exec_user_id = execution.user_id
            if exec_user_id and exec_user_id != user_id:
                raise HTTPException(
                    status_code=403, detail="Not authorized to access this execution"
                )

            violations = (
                db.query(GuardrailViolationEvent)
                .filter(GuardrailViolationEvent.graph_execution_id == execution_id)
                .order_by(GuardrailViolationEvent.created_at.asc())
                .all()
            )

            return {
                "success": True,
                "violations": [v.to_dict() for v in violations],
                "count": len(violations),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get guardrail violations for {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/nodes/{node_id}")
async def get_node_execution(
    execution_id: str,
    node_id: str,
    user_id: str = Depends(get_user_identifier),
):
    """Get a specific node execution.

    Retrieves detailed information about a single node execution within a graph execution.

    Args:
        execution_id: Graph execution ID (UUID or WebSocket ID)
        node_id: Node identifier from the graph definition
        user_id: Authenticated user identifier (injected)

    Returns:
        Node execution dictionary with all metadata

    Raises:
        HTTPException: 403 if user is not authorized, 404 if node execution not found, 500 on other errors

    Examples:
        GET /api/execution-history/executions/exec_12345/nodes/agent_1
    """
    logger.info(
        f"[EXECUTION-HISTORY-API] GET /executions/{execution_id}/nodes/{node_id} - user: {user_id}"
    )

    try:
        # Verify the authenticated user owns the parent execution before
        # exposing any node-level data.
        parent_execution = ExecutionHistoryService.get_graph_execution_dict(
            execution_id
        )
        if not parent_execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        exec_user_id = parent_execution.get("user_id")
        if exec_user_id and exec_user_id != user_id:
            logger.warning(
                f"[EXECUTION-HISTORY-API] Unauthorized access attempt: user {user_id} "
                f"tried to access node execution {execution_id}/{node_id} owned by {exec_user_id}"
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to access this execution"
            )

        node_execution = ExecutionHistoryService.get_node_execution(
            execution_id, node_id
        )

        if not node_execution:
            logger.warning(
                f"[EXECUTION-HISTORY-API] Node execution not found: "
                f"{execution_id}/{node_id}"
            )
            raise HTTPException(status_code=404, detail="Node execution not found")

        # Log database query node details if applicable
        _log_database_query_node(node_execution, execution_id, node_id)

        logger.info(
            f"[EXECUTION-HISTORY-API] Returning node execution: "
            f"{execution_id}/{node_id}"
        )
        return node_execution

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get node execution "
            f"{execution_id}/{node_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graphs/{graph_id}/summary", response_model=ExecutionSummaryResponse)
async def get_graph_summary(graph_id: str, user_id: str = Depends(get_user_identifier)):
    """Get execution summary statistics for a graph.

    Provides aggregated statistics including total executions, success/failure counts,
    duration statistics, and information about the most recent execution.

    Args:
        graph_id: Graph identifier
        user_id: Authenticated user identifier (injected)

    Returns:
        ExecutionSummaryResponse with statistics (or empty summary if no executions exist)

    Raises:
        HTTPException: 403 if user has no access to this graph's executions, 500 on database errors

    Examples:
        GET /api/execution-history/graphs/my_workflow/summary
    """
    logger.info(
        f"[EXECUTION-HISTORY-API] GET /graphs/{graph_id}/summary - user: {user_id}"
    )

    try:
        summary = ExecutionHistoryService.get_execution_summary(graph_id)

        if not summary:
            # Return empty summary if none exists
            logger.info(
                f"[EXECUTION-HISTORY-API] No executions found for graph {graph_id}, "
                "returning empty summary"
            )
            return ExecutionSummaryResponse(
                graph_id=graph_id,
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                average_duration_seconds=None,
                min_duration_seconds=None,
                max_duration_seconds=None,
                last_execution_time=None,
                last_execution_status=None,
            )

        # Verify user has access to at least one execution for this graph
        accessible = ExecutionHistoryService.get_graph_executions_dict(
            graph_id=graph_id,
            user_id=user_id,
            limit=1,
            include_nodes=False,
        )
        if not accessible["executions"]:
            logger.warning(
                f"[EXECUTION-HISTORY-API] Unauthorized summary access: user {user_id} "
                f"has no accessible executions for graph {graph_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this graph's execution summary",
            )

        logger.info(
            f"[EXECUTION-HISTORY-API] Returning summary for graph {graph_id}: "
            f"{summary.total_executions} total executions"
        )
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get summary for graph {graph_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/executions/{execution_id}")
async def delete_execution(
    execution_id: str, user_id: str = Depends(get_user_identifier)
):
    """Delete an execution and all its associated data.

    Permanently removes a graph execution and all related records (node executions,
    execution files, subagent states, review states) via cascade deletion.

    Args:
        execution_id: Execution ID to delete
        user_id: Authenticated user identifier (injected)

    Returns:
        Success message if deleted

    Raises:
        HTTPException: 403 if user is not authorized, 404 if execution not found, 500 on other errors
    """
    logger.info(
        f"[EXECUTION-HISTORY-API] DELETE /executions/{execution_id} - user: {user_id}"
    )

    try:
        # Fetch first to verify ownership before deleting
        execution = ExecutionHistoryService.get_graph_execution_dict(execution_id)

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Verify the authenticated user owns this execution
        exec_user_id = execution.get("user_id")
        if exec_user_id and exec_user_id != user_id:
            logger.warning(
                f"[EXECUTION-HISTORY-API] Unauthorized delete attempt: user {user_id} "
                f"tried to delete execution {execution_id} owned by {exec_user_id}"
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this execution"
            )

        deleted = ExecutionHistoryService.delete_graph_execution(execution_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Execution not found")

        logger.info(f"[EXECUTION-HISTORY-API] Deleted execution {execution_id}")
        return {"success": True, "message": "Execution deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to delete execution {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Feedback Endpoints ====================


@router.post(
    "/executions/{execution_id}/feedback",
    response_model=ExecutionFeedbackResponse,
    status_code=201,
)
async def submit_feedback(
    execution_id: str,
    body: SubmitFeedbackRequest,
    user_id: str = Depends(get_user_identifier),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Submit thumbs up/down feedback on an execution run.

    Creates or updates feedback for the given execution by the current user.
    Each user can have one rating per execution (upsert semantics).
    """
    if body.rating not in ("positive", "negative"):
        raise HTTPException(
            status_code=422, detail="rating must be 'positive' or 'negative'"
        )

    require_execution_access(current_user, execution_id)

    logger.info(
        f"[EXECUTION-HISTORY-API] POST feedback for {execution_id} - "
        f"user: {user_id}, rating: {body.rating}, node: {body.node_execution_id}"
    )

    try:
        with get_db() as db:
            # Verify execution exists
            execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == execution_id)
                .first()
            )
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")

            # Upsert: update if user already rated this execution+node, otherwise create
            query = db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id == execution_id,
                ExecutionFeedback.user_id == user_id,
            )
            if body.node_execution_id:
                query = query.filter(
                    ExecutionFeedback.node_execution_id == body.node_execution_id
                )
            else:
                query = query.filter(ExecutionFeedback.node_execution_id.is_(None))
            existing = query.first()

            # Resolve graph_definition_id from the execution for version tracking
            graph_definition_id = execution.graph_definition_id

            if existing:
                existing.rating = body.rating
                existing.comment = body.comment
                if not existing.graph_definition_id and graph_definition_id:
                    existing.graph_definition_id = graph_definition_id
                db.commit()
                db.refresh(existing)
                feedback = existing
            else:
                feedback = ExecutionFeedback(
                    id=str(uuid.uuid4()),
                    graph_execution_id=execution_id,
                    node_execution_id=body.node_execution_id,
                    rating=body.rating,
                    comment=body.comment,
                    user_id=user_id,
                    graph_definition_id=graph_definition_id,
                )
                db.add(feedback)
                db.commit()
                db.refresh(feedback)

            return _feedback_to_dict(feedback)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to submit feedback for {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/executions/{execution_id}/feedback",
    response_model=List[ExecutionFeedbackResponse],
)
async def get_execution_feedback(
    execution_id: str,
    node_execution_id: Optional[str] = Query(
        None, description="Filter by node execution ID"
    ),
    user_id: str = Depends(get_user_identifier),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get feedback for a specific execution, optionally filtered by node."""
    try:
        require_execution_access(current_user, execution_id)

        with get_db() as db:
            execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == execution_id)
                .first()
            )
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")

            exec_user_id = execution.user_id
            if exec_user_id and exec_user_id != user_id:
                raise HTTPException(
                    status_code=403, detail="Not authorized to access this execution"
                )

            query = db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id == execution_id
            )
            if node_execution_id is not None:
                query = query.filter(
                    ExecutionFeedback.node_execution_id == node_execution_id
                )
            feedbacks = query.order_by(ExecutionFeedback.created_at.desc()).all()
            return [_feedback_to_dict(f) for f in feedbacks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to get feedback for {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/executions/{execution_id}/feedback", status_code=204)
async def delete_feedback(
    execution_id: str,
    node_execution_id: Optional[str] = Query(
        None, description="Node execution ID to delete feedback for"
    ),
    user_id: str = Depends(get_user_identifier),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> None:
    """Remove the current user's feedback on an execution (or specific node)."""
    try:
        require_execution_access(current_user, execution_id)

        with get_db() as db:
            query = db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id == execution_id,
                ExecutionFeedback.user_id == user_id,
            )
            if node_execution_id:
                query = query.filter(
                    ExecutionFeedback.node_execution_id == node_execution_id
                )
            else:
                query = query.filter(ExecutionFeedback.node_execution_id.is_(None))
            feedback = query.first()
            if not feedback:
                raise HTTPException(status_code=404, detail="Feedback not found")
            db.delete(feedback)
            db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to delete feedback for {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback", response_model=List[ExecutionFeedbackResponse])
async def list_feedback(
    rating: Optional[str] = Query(None, pattern="^(positive|negative)$"),
    workflow_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_user_identifier),
) -> List[Dict[str, Any]]:
    """List rated executions accessible to the authenticated user, with optional filters."""
    try:
        with get_db() as db:
            # Scope to executions owned by the authenticated user to prevent
            # cross-tenant disclosure of other users' feedback/comments.
            query = db.query(ExecutionFeedback).join(
                GraphExecution,
                ExecutionFeedback.graph_execution_id == GraphExecution.id,
            ).filter(GraphExecution.user_id == user_id)

            if rating:
                query = query.filter(ExecutionFeedback.rating == rating)

            if workflow_id:
                query = query.filter(GraphExecution.workflow_id == workflow_id)

            feedbacks = (
                query.order_by(ExecutionFeedback.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [_feedback_to_dict(f) for f in feedbacks]
    except Exception as e:
        logger.error(
            f"[EXECUTION-HISTORY-API] Failed to list feedback: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================


def _feedback_to_dict(f: ExecutionFeedback) -> Dict[str, Any]:
    """Convert an ExecutionFeedback ORM instance to a response dict."""
    return {
        "id": str(f.id),
        "graph_execution_id": str(f.graph_execution_id),
        "node_execution_id": str(f.node_execution_id) if f.node_execution_id else None,
        "rating": f.rating,
        "comment": f.comment,
        "user_id": f.user_id,
        "graph_definition_id": str(f.graph_definition_id)
        if f.graph_definition_id
        else None,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _log_mcp_nodes(execution: dict, execution_id: str) -> None:
    """Log information about MCP_SERVER nodes in an execution.

    Args:
        execution: Graph execution dictionary
        execution_id: Execution identifier for logging
    """
    if "node_executions" not in execution:
        return

    mcp_nodes = [
        n for n in execution["node_executions"] if n.get("node_type") == "MCP_SERVER"
    ]

    if not mcp_nodes:
        logger.debug(f"[EXECUTION-HISTORY-API] No MCP_SERVER nodes in {execution_id}")
        return

    logger.info(
        f"[EXECUTION-HISTORY-API] Found {len(mcp_nodes)} MCP_SERVER node "
        f"executions in {execution_id}"
    )

    for mcp_node in mcp_nodes:
        logger.debug(
            f"[EXECUTION-HISTORY-API] MCP Node: {mcp_node.get('node_name')} - "
            f"Status: {mcp_node.get('status')}"
        )
        output_data = mcp_node.get("output_data")
        if output_data and "tool_executions" in output_data:
            tools = list(output_data["tool_executions"].keys())
            logger.debug(f"[EXECUTION-HISTORY-API] Tool executions: {tools}")


def _log_database_query_node(
    node_execution: dict, execution_id: str, node_id: str
) -> None:
    """Log detailed information about DATABASE_QUERY nodes.

    Args:
        node_execution: Node execution dictionary
        execution_id: Graph execution identifier
        node_id: Node identifier
    """
    if node_execution.get("node_type") != "DATABASE_QUERY":
        return

    logger.debug("[EXECUTION-HISTORY-API] DATABASE_QUERY node details:")
    logger.debug(f"  - node_id: {node_execution.get('node_id')}")
    logger.debug(f"  - node_name: {node_execution.get('node_name')}")
    logger.debug(f"  - input_data type: {type(node_execution.get('input_data'))}")

    input_data_str = str(node_execution.get("input_data"))[:200]
    logger.debug(f"  - input_data preview: {input_data_str}")

    logger.debug(f"  - output_data type: {type(node_execution.get('output_data'))}")

    output_data = node_execution.get("output_data")
    if isinstance(output_data, dict):
        logger.debug(f"  - output_data keys: {list(output_data.keys())}")
    else:
        logger.debug("  - output_data: Not a dict")

    metadata = node_execution.get("node_metadata")
    has_parent = bool(metadata.get("parent_agent_id")) if metadata else False
    logger.debug(f"  - has parent_agent_id: {has_parent}")
