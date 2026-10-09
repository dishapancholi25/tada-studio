"""Graph execution CRUD operations.

This module handles creating, updating, and retrieving graph execution records
in the execution history database.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import joinedload

from backend.services.database import get_db
from backend.models import ExecutionSummary, GraphExecution
from backend.services.config import get_logger

from .serialization import make_json_serializable


logger = get_logger("execution.history.graph")


def create_graph_execution(
    graph_id: str,
    graph_name: str,
    graph_definition: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    websocket_execution_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    graph_definition_id: Optional[str] = None,
    evaluation_run_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    chat_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new graph execution record and return its data.

    Args:
        graph_id: Unique identifier for the graph
        graph_name: Human-readable graph name
        graph_definition: Graph structure definition
        input_data: Initial input data for execution
        user_id: User executing the graph
        thread_id: Thread ID for checkpoint tracking
        websocket_execution_id: WebSocket execution identifier
        workflow_id: Associated workflow UUID
        graph_definition_id: Graph definition UUID
        evaluation_run_id: Associated evaluation run UUID
        chat_session_id: Optional chat session ID for chat-triggered executions

    Returns:
        Dictionary with key execution fields (id, graph_id, status, etc.)

    Raises:
        Exception: If database operation fails
    """
    with get_db() as db:
        execution = GraphExecution(
            graph_id=graph_id,
            graph_name=graph_name,
            graph_definition=graph_definition,
            status="running",
            input_data=input_data,
            user_id=user_id,
            thread_id=thread_id,
            websocket_execution_id=websocket_execution_id,
            workflow_id=workflow_id,
            graph_definition_id=graph_definition_id,
            evaluation_run_id=evaluation_run_id,
            trigger_type=trigger_type,
            chat_session_id=chat_session_id,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        logger.info(
            f"[EXEC-HISTORY] Created graph execution: id={execution.id}, "
            f"workflow_id={execution.workflow_id}, graph_definition_id={execution.graph_definition_id}"
        )

        # Return a dictionary with the key fields we need
        return {
            "id": str(execution.id),
            "graph_id": execution.graph_id,
            "graph_name": execution.graph_name,
            "status": execution.status,
            "start_time": execution.start_time,
            "thread_id": execution.thread_id,
            "websocket_execution_id": execution.websocket_execution_id,
            "workflow_id": execution.workflow_id,
            "graph_definition_id": execution.graph_definition_id,
        }


def update_graph_execution(
    execution_id: str,
    status: Optional[str] = None,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    end_time: Optional[datetime] = None,
) -> Optional[GraphExecution]:
    """Update a graph execution record.

    Args:
        execution_id: Graph execution ID
        status: New status (e.g., "completed", "failed")
        output_data: Final output data
        error_message: Error message if execution failed
        end_time: Execution end time

    Returns:
        Updated GraphExecution object, or None if not found

    Raises:
        Exception: If database operation fails
    """
    with get_db() as db:
        execution = (
            db.query(GraphExecution).filter(GraphExecution.id == execution_id).first()
        )
        if not execution:
            logger.warning(f"[EXEC-HISTORY] Graph execution not found: {execution_id}")
            return None

        if status:
            execution.status = status
        if output_data is not None:
            # Ensure output data is JSON serializable
            execution.output_data = make_json_serializable(output_data)
        if error_message:
            execution.error_message = error_message
        if end_time:
            execution.end_time = end_time
            # Calculate duration
            if execution.start_time:
                duration = (end_time - execution.start_time).total_seconds()
                execution.duration_seconds = duration

        db.commit()
        db.refresh(execution)

        logger.info(
            f"[EXEC-HISTORY] Updated graph execution {execution_id}: status={status}"
        )
        return execution


def get_graph_execution(execution_id: str) -> Optional[GraphExecution]:
    """Get a graph execution by ID with eagerly loaded node executions.

    Args:
        execution_id: Graph execution ID

    Returns:
        GraphExecution object with node_executions loaded, or None if not found
    """
    with get_db() as db:
        # Eagerly load node_executions relationship
        execution = (
            db.query(GraphExecution)
            .options(joinedload(GraphExecution.node_executions))
            .filter(GraphExecution.id == execution_id)
            .first()
        )

        if execution:
            logger.debug(f"[EXEC-HISTORY] Retrieved graph execution: {execution_id}")
        else:
            logger.warning(f"[EXEC-HISTORY] Graph execution not found: {execution_id}")

        return execution


def get_graph_executions(
    graph_id: Optional[str] = None, limit: int = 100, offset: int = 0
):
    """Get graph executions with optional filtering.

    Args:
        graph_id: Filter by specific graph ID (optional)
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)

    Returns:
        List of GraphExecution objects with node_executions eagerly loaded
    """
    with get_db() as db:
        query = db.query(GraphExecution)

        if graph_id:
            query = query.filter(GraphExecution.graph_id == graph_id)

        # Eagerly load node_executions relationship
        query = query.options(joinedload(GraphExecution.node_executions))

        from sqlalchemy import desc

        executions = (
            query.order_by(desc(GraphExecution.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        logger.debug(
            f"[EXEC-HISTORY] Retrieved {len(executions)} graph executions "
            f"(graph_id={graph_id}, limit={limit}, offset={offset})"
        )

        return executions


def delete_graph_execution(execution_id: str) -> bool:
    """Delete a graph execution and all associated data.

    SQLAlchemy cascade relationships handle deletion of:
    - node_executions (cascade from GraphExecution)
    - execution_files (cascade from NodeExecution)
    - subagent_iteration_states (DB-level ondelete CASCADE)
    - agent_review_states (DB-level ondelete CASCADE)

    Args:
        execution_id: Graph execution ID

    Returns:
        True if execution was found and deleted, False if not found
    """
    with get_db() as db:
        execution = (
            db.query(GraphExecution).filter(GraphExecution.id == execution_id).first()
        )
        if not execution:
            logger.warning(
                f"[EXEC-HISTORY] Graph execution not found for deletion: {execution_id}"
            )
            return False

        db.delete(execution)
        db.commit()

        logger.info(f"[EXEC-HISTORY] Deleted graph execution: {execution_id}")
        return True


def get_execution_summary(graph_id: str) -> Optional[ExecutionSummary]:
    """Get execution summary statistics for a graph.

    Args:
        graph_id: Graph ID

    Returns:
        ExecutionSummary object, or None if not found
    """
    with get_db() as db:
        summary = (
            db.query(ExecutionSummary)
            .filter(ExecutionSummary.graph_id == graph_id)
            .first()
        )

        if summary:
            logger.debug(
                f"[EXEC-HISTORY] Retrieved summary for graph {graph_id}: "
                f"total={summary.total_executions}, success={summary.successful_executions}"
            )
        else:
            logger.debug(f"[EXEC-HISTORY] No summary found for graph: {graph_id}")

        return summary


def update_execution_summary(graph_id: str, execution_id: str) -> None:
    """Update execution summary statistics.

    Args:
        graph_id: Graph ID
        execution_id: Execution ID to include in statistics

    Raises:
        Exception: If database operation fails
    """
    with get_db() as db:
        # Get the execution
        execution = (
            db.query(GraphExecution).filter(GraphExecution.id == execution_id).first()
        )
        if not execution:
            logger.warning(
                f"[EXEC-HISTORY] Cannot update summary - execution not found: {execution_id}"
            )
            return

        summary = (
            db.query(ExecutionSummary)
            .filter(ExecutionSummary.graph_id == graph_id)
            .first()
        )

        if not summary:
            summary = ExecutionSummary(
                graph_id=graph_id,
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
            )
            db.add(summary)

        # Update statistics
        summary.total_executions += 1

        if execution.status == "completed":
            summary.successful_executions += 1
        elif execution.status == "failed":
            summary.failed_executions += 1

        summary.last_execution_time = execution.created_at
        summary.last_execution_status = execution.status

        # Update duration statistics
        if execution.duration_seconds is not None:
            if summary.average_duration_seconds is None:
                summary.average_duration_seconds = execution.duration_seconds
                summary.min_duration_seconds = execution.duration_seconds
                summary.max_duration_seconds = execution.duration_seconds
            else:
                # Update average
                total_duration = summary.average_duration_seconds * (
                    summary.total_executions - 1
                )
                summary.average_duration_seconds = (
                    total_duration + execution.duration_seconds
                ) / summary.total_executions

                # Update min/max
                summary.min_duration_seconds = min(
                    summary.min_duration_seconds or float("inf"),
                    execution.duration_seconds,
                )
                summary.max_duration_seconds = max(
                    summary.max_duration_seconds or 0, execution.duration_seconds
                )

        db.commit()
        logger.info(
            f"[EXEC-HISTORY] Updated summary for graph {graph_id}: "
            f"total={summary.total_executions}"
        )
