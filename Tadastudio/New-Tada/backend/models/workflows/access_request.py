"""Access request model for workflow edit access requests."""

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin
from ..enums import AccessRequestStatus, WorkflowRole


class AccessRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks requests from viewers to get edit access to workflows.

    Attributes:
        id: Unique request identifier (UUID).
        workflow_id: Workflow being requested access to.
        requester_id: User ID of the person requesting access.
        requester_email: Email of requester for display.
        requested_role: Role being requested (usually EDITOR).
        status: Current status (PENDING, APPROVED, REJECTED).
        message: Optional message from requester.
        resolved_at: When the request was approved/rejected.
        resolved_by: User ID who resolved the request.
        created_at: When request was created.
        updated_at: Last update timestamp.
    """

    __tablename__ = "access_requests"

    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_email = Column(String, nullable=True)
    requested_role = Column(
        Enum(WorkflowRole), nullable=False, default=WorkflowRole.EDITOR
    )
    status = Column(
        Enum(AccessRequestStatus),
        nullable=False,
        default=AccessRequestStatus.PENDING,
        index=True,
    )
    message = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)

    # Relationships
    workflow = relationship("Workflow")
    requester = relationship("User", foreign_keys=[requester_id])
