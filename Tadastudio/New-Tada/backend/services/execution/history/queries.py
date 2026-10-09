"""Complex query methods for execution history.

This module handles more complex database queries including filtering,
user-based access control, and formatted dictionary returns.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.orm import joinedload

from backend.services.database import get_db
from backend.models import GraphExecution, NodeExecution, Workflow, WorkflowMembership
from backend.models.execution.execution_feedback import ExecutionFeedback
from backend.services.config import get_logger

from .formatters import format_graph_execution_to_dict, format_node_execution_to_dict
from .formatters.graph_formatter import format_graph_execution_basic


logger = get_logger("execution.history.queries")


def get_graph_execution_dict(execution_id: str) -> Optional[Dict[str, Any]]:
    """Get a graph execution by ID as a dictionary.

    Supports lookup by either database UUID or WebSocket execution ID.

    Args:
        execution_id: Either the database UUID or the WebSocket execution ID

    Returns:
        Dictionary representation of the graph execution, or None if not found
    """
    logger.info(
        f"[EXEC-HISTORY] Fetching graph execution from database: {execution_id}"
    )

    with get_db() as db:
        # Query by either database UUID or WebSocket execution ID
        execution = (
            db.query(GraphExecution)
            .options(
                joinedload(GraphExecution.node_executions),
                joinedload(GraphExecution.graph_definition_rel),
            )
            .filter(
                or_(
                    GraphExecution.id == execution_id,
                    GraphExecution.websocket_execution_id == execution_id,
                )
            )
            .first()
        )

        if not execution:
            logger.warning(
                f"[EXEC-HISTORY] No execution found for ID: {execution_id} "
                "(tried both UUID and WebSocket ID)"
            )
            return None

        logger.info(
            f"[EXEC-HISTORY] Graph execution {execution_id} status from DB: {execution.status}"
        )

        # Convert to dictionary while still in session
        exec_dict = format_graph_execution_to_dict(execution)
        return exec_dict


def get_graph_executions_dict(
    graph_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    graph_name: Optional[str] = None,
    status: Optional[str] = None,
    include_nodes: bool = True,
    trigger_type: Optional[str] = None,
    feedback_rating: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get graph executions as dictionaries with optional filtering.

    Includes user-based access control via workflow ownership/membership.

    Args:
        graph_id: Filter by specific graph ID (optional)
        user_id: Filter by user's accessible workflows (optional)
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)
        graph_name: Filter by graph name (partial, case-insensitive) (optional)
        status: Filter by execution status (optional)
        include_nodes: Whether to include node_executions (default: True)

    Returns:
        Tuple of (list of graph execution dictionaries, total count)
    """
    logger.info(
        f"[EXEC-HISTORY] Querying graph executions - graph_id: {graph_id}, "
        f"user_id: {user_id}, limit: {limit}, offset: {offset}, "
        f"graph_name: {graph_name}, status: {status}, include_nodes: {include_nodes}"
    )

    with get_db() as db:
        query = db.query(GraphExecution)

        if graph_id:
            query = query.filter(GraphExecution.graph_id == graph_id)

        # Filter by workflow UUID
        if workflow_id:
            query = query.filter(GraphExecution.workflow_id == workflow_id)

        # Filter by graph name (partial, case-insensitive)
        if graph_name:
            query = query.filter(GraphExecution.graph_name.ilike(f"%{graph_name}%"))

        # Filter by status
        if status:
            query = query.filter(GraphExecution.status == status)

        # Filter by trigger type
        if trigger_type:
            query = query.filter(GraphExecution.trigger_type == trigger_type)

        # Filter by feedback rating (positive/negative) - includes both
        # execution-level and node-level feedback
        if feedback_rating:
            query = query.filter(
                GraphExecution.id.in_(
                    db.query(ExecutionFeedback.graph_execution_id).filter(
                        ExecutionFeedback.rating == feedback_rating,
                    )
                )
            )

        # User-based filtering via workflow ownership/membership
        if user_id:
            query = _apply_user_filter(query, user_id, db)

        # Get total count before pagination
        total_count = query.count()

        # Eagerly load graph_definition_rel to avoid N+1 queries for version lookup
        query = query.options(joinedload(GraphExecution.graph_definition_rel))

        # Only eagerly load node_executions if requested
        if include_nodes:
            query = query.options(joinedload(GraphExecution.node_executions))

        executions = (
            query.order_by(desc(GraphExecution.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        logger.info(
            f"[EXEC-HISTORY] Found {len(executions)} graph executions (total: {total_count})"
        )

        # Convert to dictionaries while still in session
        result = []

        if include_nodes:
            # Full format with node executions
            for execution in executions:
                exec_dict = format_graph_execution_to_dict(execution)
                result.append(exec_dict)
        else:
            # Basic format - batch fetch node counts and feedback in bulk queries
            execution_ids = [e.id for e in executions]

            if execution_ids:
                # Single query for all node counts
                counts_query = (
                    db.query(
                        NodeExecution.graph_execution_id,
                        func.count(NodeExecution.id).label("total"),
                        func.sum(
                            case((NodeExecution.status == "completed", 1), else_=0)
                        ).label("completed"),
                    )
                    .filter(NodeExecution.graph_execution_id.in_(execution_ids))
                    .group_by(NodeExecution.graph_execution_id)
                    .all()
                )

                # Build lookup dict
                count_map = {
                    str(c.graph_execution_id): (c.total or 0, int(c.completed or 0))
                    for c in counts_query
                }

                # Single query for all feedback ratings (execution-level only)
                # Filter by user_id so each user sees only their own feedback
                feedback_query_builder = db.query(
                    ExecutionFeedback.graph_execution_id,
                    ExecutionFeedback.rating,
                ).filter(
                    ExecutionFeedback.graph_execution_id.in_(execution_ids),
                    ExecutionFeedback.node_execution_id.is_(None),
                )
                if user_id:
                    feedback_query_builder = feedback_query_builder.filter(
                        ExecutionFeedback.user_id == user_id
                    )
                feedback_query = feedback_query_builder.all()
                feedback_map = {
                    str(f.graph_execution_id): f.rating for f in feedback_query
                }

                logger.debug(
                    f"[EXEC-HISTORY] Batched node counts for {len(count_map)} executions, "
                    f"feedback for {len(feedback_map)} executions"
                )
            else:
                count_map = {}
                feedback_map = {}

            for execution in executions:
                node_count, completed_count = count_map.get(str(execution.id), (0, 0))
                exec_dict = format_graph_execution_basic(
                    execution, node_count, completed_count
                )
                exec_dict["feedback_rating"] = feedback_map.get(str(execution.id))
                result.append(exec_dict)

        logger.debug(f"[EXEC-HISTORY] Returning {len(result)} execution records")
        return result, total_count


def get_distinct_workflow_names(user_id: Optional[str] = None) -> List[str]:
    """Get distinct workflow names accessible to a user.

    Args:
        user_id: Filter by user's accessible workflows (optional)

    Returns:
        List of distinct workflow names, sorted alphabetically
    """
    logger.info(f"[EXEC-HISTORY] Getting distinct workflow names for user: {user_id}")

    with get_db() as db:
        query = db.query(GraphExecution.graph_name).distinct()

        if user_id:
            query = _apply_user_filter(query, user_id, db)

        results = query.order_by(GraphExecution.graph_name).all()

        workflow_names = [row[0] for row in results if row[0]]
        logger.info(
            f"[EXEC-HISTORY] Found {len(workflow_names)} distinct workflow names"
        )
        return workflow_names


def _apply_user_filter(query, user_id: str, db):
    """Apply user-based filtering to graph execution query.

    Args:
        query: SQLAlchemy query object
        user_id: User identifier (email or sub)
        db: Database session

    Returns:
        Filtered query
    """
    # Resolve user_id from email if needed
    from backend.services.graph.storage import resolve_user_id

    resolved_user_id = resolve_user_id(user_id, db)
    logger.info(f"[EXEC-HISTORY] Resolved user_id '{user_id}' -> '{resolved_user_id}'")

    if not resolved_user_id:
        logger.warning(f"[EXEC-HISTORY] Could not resolve user_id: {user_id}")
        return query

    # Get workflow IDs that user owns or is a member of (kept as subquery
    # so the DB can optimize it — avoids materializing into Python list)
    accessible_workflow_ids = (
        select(Workflow.id)
        .select_from(Workflow)
        .outerjoin(
            WorkflowMembership,
            WorkflowMembership.workflow_id == Workflow.id,
        )
        .where(
            or_(
                Workflow.created_by_user_id == resolved_user_id,
                WorkflowMembership.user_id == resolved_user_id,
            )
        )
    )

    # Filter executions by accessible workflows AND owned by the current user.
    # This ensures users only see their own executions, not executions by other
    # members of a shared workflow. Aligns with the per-execution ownership check
    # in the individual GET endpoint.
    return query.filter(
        GraphExecution.workflow_id.in_(accessible_workflow_ids),
        or_(
            GraphExecution.user_id == user_id,
            GraphExecution.user_id.is_(None),
        ),
    )


def get_node_execution(execution_id: str, node_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific node execution by execution_id and node_id.

    Supports execution_id as either WebSocket ID or database UUID.

    Args:
        execution_id: Graph execution ID (WebSocket or UUID)
        node_id: Node identifier

    Returns:
        Dictionary representation of the node execution, or None if not found
    """
    logger.debug(
        f"[EXEC-HISTORY] Querying node execution - execution_id: {execution_id}, "
        f"node_id: {node_id}"
    )

    with get_db() as db:
        # Determine if this is a WebSocket ID or UUID
        if execution_id.startswith("exec_"):
            logger.debug(
                "[EXEC-HISTORY] Detected WebSocket ID, looking up by websocket_execution_id"
            )
            # This is a WebSocket ID, look up the graph execution
            graph_execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.websocket_execution_id == execution_id)
                .first()
            )
        else:
            logger.debug("[EXEC-HISTORY] Detected UUID, looking up by id")
            # This is a UUID, look up directly
            graph_execution = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == execution_id)
                .first()
            )

        if not graph_execution:
            logger.warning(f"[EXEC-HISTORY] Graph execution not found: {execution_id}")
            return None

        logger.debug(
            f"[EXEC-HISTORY] Found graph execution with DB ID: {graph_execution.id}"
        )

        # Then find the node execution using the database ID
        node_execution = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == graph_execution.id,
                NodeExecution.node_id == node_id,
            )
            .first()
        )

        if not node_execution:
            logger.warning(
                f"[EXEC-HISTORY] Node execution not found: {execution_id}/{node_id}"
            )
            return None

        logger.debug(f"[EXEC-HISTORY] Found node execution: {node_execution.id}")
        logger.debug(f"[EXEC-HISTORY] Node type: {node_execution.node_type}")

        # Convert to dictionary
        node_dict = format_node_execution_to_dict(node_execution)
        return node_dict


def get_node_execution_by_id(node_exec_id: str) -> Optional[Dict[str, Any]]:
    """Get a node execution by its primary key ID.

    Args:
        node_exec_id: Node execution database ID

    Returns:
        Dictionary representation of the node execution, or None if not found
    """
    logger.debug(f"[EXEC-HISTORY] Querying node execution by ID: {node_exec_id}")

    with get_db() as db:
        node_execution = (
            db.query(NodeExecution).filter(NodeExecution.id == node_exec_id).first()
        )

        if not node_execution:
            logger.warning(f"[EXEC-HISTORY] Node execution not found: {node_exec_id}")
            return None

        logger.info(
            f"[EXEC-HISTORY] Found node execution: {node_execution.node_name} "
            f"with duration: {node_execution.duration_seconds}"
        )

        # Convert to dictionary
        node_dict = format_node_execution_to_dict(node_execution)
        return node_dict
