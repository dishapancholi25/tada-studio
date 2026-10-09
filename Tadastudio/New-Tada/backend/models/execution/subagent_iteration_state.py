"""Subagent iteration state tracking model.

This module contains the model for tracking subagent execution iterations
across checkpoint boundaries, supporting resume/retry persistence.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class SubagentIterationState(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for persisting subagent iteration state across checkpoint boundaries.

    This model tracks which iteration a subagent is on when called multiple
    times by a parent agent, ensuring proper WebSocket routing and database
    record separation.

    Attributes:
        id: Unique iteration state identifier (UUID).
        graph_execution_id: Parent graph execution ID.
        parent_agent_id: ID of the orchestrator/parent agent calling the subagent.
        subagent_node_id: Node identifier of the subagent within the graph.
        thread_id: LangGraph thread ID.
        current_iteration: Current iteration number (1-indexed).
        status: Iteration status (active, completed).
        iteration_history: JSON array of previous iteration records.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "subagent_iteration_states"

    # Foreign keys
    graph_execution_id = Column(
        String,
        ForeignKey("graph_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Parent agent that is calling the subagent
    parent_agent_id = Column(String, nullable=False, index=True)

    # The subagent being called
    subagent_node_id = Column(String, nullable=False, index=True)

    # Thread for resume support
    thread_id = Column(String, nullable=False, index=True)

    # Iteration tracking
    current_iteration = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="active")

    # History of iterations with their node execution IDs
    iteration_history = Column(JSON, nullable=True, default=list)

    # Relationships
    graph_execution = relationship("GraphExecution")
