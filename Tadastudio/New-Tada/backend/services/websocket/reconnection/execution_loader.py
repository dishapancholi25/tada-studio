"""Database execution loading for reconnection."""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ....models import GraphExecution, NodeExecution
from ....services.config import get_logger


logger = get_logger("websocket_reconnection")


def load_execution_from_db(
    db: Session, db_execution_id: str
) -> Optional[Tuple[GraphExecution, List[NodeExecution]]]:
    """
    Load execution and node executions from database.

    Args:
        db: Database session
        db_execution_id: Database execution ID

    Returns:
        Tuple of (execution, node_executions) or None if not found
    """
    execution = (
        db.query(GraphExecution).filter(GraphExecution.id == db_execution_id).first()
    )

    if not execution:
        logger.warning(
            f"[RECONNECT] Execution not found in database: {db_execution_id}"
        )
        return None

    # Get all node executions
    node_executions = (
        db.query(NodeExecution)
        .filter(NodeExecution.graph_execution_id == db_execution_id)
        .order_by(NodeExecution.execution_order)
        .all()
    )

    return execution, node_executions
