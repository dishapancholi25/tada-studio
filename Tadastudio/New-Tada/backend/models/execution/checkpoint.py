"""Checkpoint metadata model for subworkflow resumption."""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class CheckpointMetadata(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing checkpoint metadata for subworkflow resumption.

    Tracks checkpoint state for paused workflows and subworkflow execution,
    enabling resumption and context preservation.

    Attributes:
        id: Unique checkpoint identifier (UUID).
        checkpoint_id: LangGraph checkpoint identifier.
        thread_id: Thread identifier for this checkpoint.
        is_subworkflow: Whether this is a subworkflow checkpoint.
        subworkflow_name: Name of the subworkflow (if applicable).
        subworkflow_thread_id: Thread ID for the subworkflow.
        checkpoint_node_exec_id: Associated node execution ID.
        parent_execution_id: Parent execution identifier.
        parent_tool_call: JSON tool call details from parent.
        interrupt_data: Full interrupt value storage.
        status: Checkpoint status (active, resumed, completed).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "checkpoint_metadata"

    # Checkpoint identification
    checkpoint_id = Column(String, nullable=False, unique=True, index=True)
    thread_id = Column(String, nullable=False, index=True)

    # Subworkflow information
    is_subworkflow = Column(Boolean, default=False, nullable=False)
    subworkflow_name = Column(String, nullable=True)
    subworkflow_thread_id = Column(String, nullable=True)
    checkpoint_node_exec_id = Column(
        String, ForeignKey("node_executions.id", ondelete="SET NULL"), nullable=True
    )

    # Parent context
    parent_execution_id = Column(String, nullable=True)
    parent_tool_call = Column(JSON, nullable=True)

    # Additional metadata
    interrupt_data = Column(JSON, nullable=True)
    status = Column(String, default="active")

    # Relationships
    checkpoint_node = relationship(
        "NodeExecution",
        backref="checkpoint_metadata",
        foreign_keys=[checkpoint_node_exec_id],
    )
