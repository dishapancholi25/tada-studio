"""Workflow membership and access control models."""

from sqlalchemy import Column, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin
from ..enums import WorkflowRole


class WorkflowMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Join table linking users to workflows with role-based access.

    Manages user permissions and access to workflows.

    Attributes:
        id: Unique membership identifier (UUID).
        workflow_id: Associated workflow ID.
        user_id: Associated user ID.
        role: User's role (OWNER, EDITOR, VIEWER).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "workflow_memberships"

    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(Enum(WorkflowRole), nullable=False, default=WorkflowRole.OWNER)

    # Relationships
    workflow = relationship("Workflow", back_populates="memberships")
    user = relationship("User", back_populates="workflow_memberships")

    __table_args__ = (
        UniqueConstraint("workflow_id", "user_id", name="uq_workflow_user_membership"),
    )
