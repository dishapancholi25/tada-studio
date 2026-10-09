"""Database query utilities for paused executions."""

from typing import List, Optional, Tuple

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ....models import GraphExecution, NodeExecution
from ....services.config import get_logger


# Get logger
logger = get_logger(__name__)


def get_paused_executions_by_graph(
    db: Session, graph_name: str, skip: int = 0, limit: int = 20
) -> Tuple[List[GraphExecution], int]:
    """
    Query paused executions for a specific graph with pagination.

    Args:
        db: Database session
        graph_name: Name of the graph/workflow to filter by
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of GraphExecution objects, total count)
    """
    try:
        # Get total count first
        total_count = (
            db.query(GraphExecution)
            .filter(
                and_(
                    GraphExecution.graph_name == graph_name,
                    GraphExecution.status == "paused",
                )
            )
            .count()
        )

        # Query for paused executions with pagination
        executions = (
            db.query(GraphExecution)
            .filter(
                and_(
                    GraphExecution.graph_name == graph_name,
                    GraphExecution.status == "paused",
                )
            )
            .order_by(desc(GraphExecution.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

        logger.debug(
            f"[PAUSED-EXEC-QUERIES] Found {len(executions)} paused executions "
            f"(total: {total_count}) for graph '{graph_name}'"
        )

        return executions, total_count

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-QUERIES] Error querying paused executions "
            f"for graph '{graph_name}': {e}"
        )
        raise


def get_all_paused_executions(db: Session) -> List[GraphExecution]:
    """
    Query all paused executions across all graphs.

    Args:
        db: Database session

    Returns:
        List of all paused GraphExecution objects
    """
    try:
        executions = (
            db.query(GraphExecution)
            .filter(GraphExecution.status == "paused")
            .order_by(desc(GraphExecution.created_at))
            .all()
        )

        logger.info(
            f"[PAUSED-EXEC-QUERIES] Found {len(executions)} total paused executions"
        )

        return executions

    except Exception as e:
        logger.error(f"[PAUSED-EXEC-QUERIES] Error querying all paused executions: {e}")
        raise


def get_checkpoint_node(db: Session, execution_id: str) -> Optional[NodeExecution]:
    """
    Find the paused checkpoint node for an execution.

    Looks for either:
    - CHECKPOINT nodes (traditional manual checkpoints)
    - AGENT nodes with paused status (agent review checkpoints)

    Args:
        db: Database session
        execution_id: The database execution ID

    Returns:
        NodeExecution for the paused checkpoint/agent, or None if not found
    """
    from sqlalchemy import or_

    try:
        # Look for paused CHECKPOINT nodes or paused AGENT nodes (for agent review)
        checkpoint_node = (
            db.query(NodeExecution)
            .filter(
                and_(
                    NodeExecution.graph_execution_id == execution_id,
                    NodeExecution.status == "paused",
                    or_(
                        NodeExecution.node_type == "CHECKPOINT",
                        NodeExecution.node_type == "AGENT",
                    ),
                )
            )
            .order_by(
                NodeExecution.execution_order.desc()
            )  # Get the latest paused node
            .first()
        )

        # Note: Per-execution DEBUG logs removed to reduce verbosity
        # The service layer logs summary information for paused execution queries
        return checkpoint_node

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-QUERIES] Error querying checkpoint node "
            f"for execution {execution_id}: {e}"
        )
        raise


def get_execution_by_id(db: Session, execution_id: str) -> Optional[GraphExecution]:
    """
    Get a graph execution by ID.

    Args:
        db: Database session
        execution_id: The database execution ID

    Returns:
        GraphExecution object or None if not found
    """
    try:
        execution = (
            db.query(GraphExecution).filter(GraphExecution.id == execution_id).first()
        )

        if execution:
            logger.debug(
                f"[PAUSED-EXEC-QUERIES] Found execution {execution_id} "
                f"with status '{execution.status}'"
            )
        else:
            logger.warning(f"[PAUSED-EXEC-QUERIES] Execution {execution_id} not found")

        return execution

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-QUERIES] Error querying execution {execution_id}: {e}"
        )
        raise


def get_node_executions_by_execution_id(
    db: Session, execution_id: str
) -> List[NodeExecution]:
    """
    Get all node executions for a graph execution, ordered by execution order.

    Args:
        db: Database session
        execution_id: The database execution ID

    Returns:
        List of NodeExecution objects ordered by execution_order
    """
    try:
        node_executions = (
            db.query(NodeExecution)
            .filter(NodeExecution.graph_execution_id == execution_id)
            .order_by(NodeExecution.execution_order)
            .all()
        )

        logger.debug(
            f"[PAUSED-EXEC-QUERIES] Found {len(node_executions)} node executions "
            f"for execution {execution_id}"
        )

        return node_executions

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-QUERIES] Error querying node executions "
            f"for execution {execution_id}: {e}"
        )
        raise


def get_paused_nodes_by_execution_id(
    db: Session, execution_id: str
) -> List[NodeExecution]:
    """
    Get all paused nodes for an execution.

    Args:
        db: Database session
        execution_id: The database execution ID

    Returns:
        List of paused NodeExecution objects
    """
    try:
        paused_nodes = (
            db.query(NodeExecution)
            .filter(
                and_(
                    NodeExecution.graph_execution_id == execution_id,
                    NodeExecution.status == "paused",
                )
            )
            .all()
        )

        logger.debug(
            f"[PAUSED-EXEC-QUERIES] Found {len(paused_nodes)} paused nodes "
            f"for execution {execution_id}"
        )

        return paused_nodes

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-QUERIES] Error querying paused nodes "
            f"for execution {execution_id}: {e}"
        )
        raise


def get_previous_node(
    db: Session, execution_id: str, current_execution_order: int
) -> Optional[NodeExecution]:
    """
    Get the node that executed immediately before the current node.

    Args:
        db: Database session
        execution_id: The database execution ID
        current_execution_order: The execution order of the current node

    Returns:
        NodeExecution for the previous node, or None if not found
    """
    try:
        previous_node = (
            db.query(NodeExecution)
            .filter(
                and_(
                    NodeExecution.graph_execution_id == execution_id,
                    NodeExecution.execution_order == current_execution_order - 1,
                )
            )
            .first()
        )

        if previous_node:
            logger.debug(
                f"[PAUSED-EXEC-QUERIES] Found previous node "
                f"'{previous_node.node_name}' for execution {execution_id}"
            )
        else:
            logger.debug(
                f"[PAUSED-EXEC-QUERIES] No previous node found "
                f"for execution {execution_id} at order {current_execution_order - 1}"
            )

        return previous_node

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-QUERIES] Error querying previous node "
            f"for execution {execution_id}: {e}"
        )
        raise
