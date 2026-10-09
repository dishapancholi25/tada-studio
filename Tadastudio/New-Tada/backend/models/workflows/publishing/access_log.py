"""Workflow access logging model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ....services.database import Base
from ...base import UUIDPrimaryKeyMixin


class WorkflowAccessLog(Base, UUIDPrimaryKeyMixin):
    """Model for logging access to published workflows.

    Tracks all access attempts to published workflows including
    authentication, execution details, and rate limiting.

    Attributes:
        id: Unique log identifier (UUID).
        published_workflow_id: Associated published workflow ID.
        client_ip: Client IP address.
        user_agent: User agent string.
        request_method: HTTP request method (POST, GET, etc.).
        request_path: Request path.
        token_used: Token that was used (if any).
        authentication_status: Authentication result (success, failed, none).
        execution_id: Associated graph execution ID (if applicable).
        execution_status: Execution status (completed, failed, timeout).
        execution_duration_ms: Execution duration in milliseconds.
        response_status: HTTP response status code.
        response_size_bytes: Response size in bytes.
        error_message: Error message (if applicable).
        rate_limit_hit: Whether rate limit was hit.
        rate_limit_remaining: Remaining rate limit allowance.
        accessed_at: Access timestamp.
    """

    __tablename__ = "workflow_access_logs"

    published_workflow_id = Column(
        String, ForeignKey("published_workflows.id", ondelete="CASCADE"), nullable=False
    )

    # Request details
    client_ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=False)
    request_path = Column(String, nullable=False)

    # Authentication
    token_used = Column(String, nullable=True)
    authentication_status = Column(String(20), nullable=False)

    # Execution details
    execution_id = Column(String, nullable=True)
    execution_status = Column(String(20), nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)

    # Response details
    response_status = Column(Integer, nullable=False)
    response_size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Rate limiting
    rate_limit_hit = Column(Boolean, default=False, nullable=False)
    rate_limit_remaining = Column(Integer, nullable=True)

    # Timestamps
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    published_workflow = relationship("PublishedWorkflow", back_populates="access_logs")
