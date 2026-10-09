"""Graph execution tracking model."""

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class GraphExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing graph execution history.

    Tracks the execution of LangGraph workflows including status, timing,
    input/output data, and relationships to nodes and workflows.

    Attributes:
        id: Unique execution identifier (UUID).
        graph_id: Identifier of the graph being executed.
        graph_name: Name of the graph.
        graph_definition: JSON structure of the graph.
        websocket_execution_id: Legacy WebSocket execution ID for compatibility.
        thread_id: LangGraph thread ID for checkpoint-based memory.
        status: Execution status (running, completed, failed).
        start_time: When execution started.
        end_time: When execution completed.
        duration_seconds: Total execution time in seconds.
        input_data: JSON input data for the execution.
        output_data: JSON output data from the execution.
        error_message: Error message if execution failed.
        user_id: User who initiated the execution.
        workflow_id: Associated workflow ID.
        graph_definition_id: Associated graph definition ID.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "graph_executions"

    # Core identification
    graph_id = Column(String, nullable=False, index=True)
    graph_name = Column(String, nullable=False, index=True)
    graph_definition = Column(JSON, nullable=False)

    # WebSocket execution ID for backwards compatibility (format: exec_TIMESTAMP_GRAPHNAME)
    websocket_execution_id = Column(String, nullable=True, unique=True, index=True)

    # LangGraph thread ID for checkpoint-based memory
    thread_id = Column(String, nullable=True, index=True)

    # Execution metadata
    status = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Input/Output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # User tracking
    user_id = Column(String, nullable=True, index=True)

    # Workflow and graph definition links for user-based access control
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    graph_definition_id = Column(
        String,
        ForeignKey("graph_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evaluation_run_id = Column(
        String,
        ForeignKey("evaluation_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Execution trigger type tracking (editor, api, evaluation, scheduler, chat)
    trigger_type = Column(String, nullable=True, index=True)

    # Chat session link for chat-triggered executions
    chat_session_id = Column(
        String,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    node_executions = relationship(
        "NodeExecution", back_populates="graph_execution", cascade="all, delete-orphan"
    )
    workflow = relationship("Workflow")
    graph_definition_rel = relationship("GraphDefinition")
    evaluation_run = relationship("EvaluationRun", foreign_keys=[evaluation_run_id])

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_graph_executions_workflow_user", "workflow_id", "user_id"),
        Index("idx_graph_executions_status_created", "status", "created_at"),
        Index("idx_graph_executions_chat_session", "chat_session_id", "created_at"),
    )
