"""Execution summary statistics model."""

from sqlalchemy import Column, DateTime, Float, Integer, String

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ExecutionSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing aggregated execution statistics.

    Provides summary statistics for graph executions including success rates,
    execution counts, and timing metrics.

    Attributes:
        id: Unique summary identifier (UUID).
        graph_id: Graph identifier for these statistics.
        total_executions: Total number of executions.
        successful_executions: Number of successful executions.
        failed_executions: Number of failed executions.
        average_duration_seconds: Average execution duration.
        min_duration_seconds: Minimum execution duration.
        max_duration_seconds: Maximum execution duration.
        last_execution_time: Timestamp of last execution.
        last_execution_status: Status of last execution.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "execution_summaries"

    graph_id = Column(String, nullable=False, index=True)

    # Aggregated statistics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    average_duration_seconds = Column(Float, nullable=True)
    min_duration_seconds = Column(Float, nullable=True)
    max_duration_seconds = Column(Float, nullable=True)

    # Last execution info
    last_execution_time = Column(DateTime(timezone=True), nullable=True)
    last_execution_status = Column(String, nullable=True)
