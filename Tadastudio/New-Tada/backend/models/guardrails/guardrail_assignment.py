"""GuardrailAssignment ORM model for linking policies to targets."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import UUIDPrimaryKeyMixin
from backend.services.database import Base


class GuardrailAssignment(Base, UUIDPrimaryKeyMixin):
    """Junction table linking a guardrail policy to a target.

    Targets can be agent nodes, models, tools, or workflows.
    Priority determines resolution order when multiple policies apply.
    """

    __tablename__ = "guardrail_assignments"

    policy_id = Column(
        String,
        ForeignKey("guardrail_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(String, nullable=False, index=True)
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    priority = Column(Integer, nullable=False, default=0)
    override_mode = Column(String(50), nullable=False, default="merge")
    assigned_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    policy = relationship("GuardrailPolicy", back_populates="assignments")

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "workflow_id": self.workflow_id,
            "priority": self.priority,
            "override_mode": self.override_mode,
            "assigned_by": self.assigned_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "policy_name": self.policy.name if self.policy else None,
        }
