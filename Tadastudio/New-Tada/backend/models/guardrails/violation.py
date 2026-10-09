"""GuardrailViolation ORM model for persisting violation events."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import UUIDPrimaryKeyMixin
from backend.services.database import Base


class GuardrailViolation(Base, UUIDPrimaryKeyMixin):
    """Persistent record of a guardrail violation event.

    Violations are emitted transiently via WebSocket; this table backs
    the violation dashboard and feedback features.

    Retention: rows with created_at older than 1 year are purged by
    the scheduled cleanup job in ViolationRetentionService.
    """

    __tablename__ = "guardrail_violations"

    # Policy and rule context
    policy_id = Column(
        String,
        ForeignKey("guardrail_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    policy_name = Column(String(255), nullable=True)  # denormalised — policy may be deleted
    rule_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # input | output | tool_call | token_budget | behavioral | custom_filter
    severity = Column(String(20), nullable=False, index=True)  # block | warn | info
    action_taken = Column(String(20), nullable=False)  # blocked | redacted | warned | none
    message = Column(Text, nullable=True)

    # Execution context
    execution_id = Column(String, nullable=False, index=True)
    node_execution_id = Column(String, nullable=True, index=True)
    workflow_id = Column(String, nullable=True, index=True)
    agent_node_id = Column(String, nullable=True)
    agent_node_name = Column(String(255), nullable=True)
    tool_name = Column(String(255), nullable=True)

    # User context (for scoped access control on the dashboard)
    user_id = Column(String, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    policy = relationship("GuardrailPolicy", foreign_keys=[policy_id])
    feedbacks = relationship(
        "GuardrailViolationFeedback",
        back_populates="violation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_gv_policy_severity_created", "policy_id", "severity", "created_at"),
        Index("idx_gv_workflow_created", "workflow_id", "created_at"),
        Index("idx_gv_execution_created", "execution_id", "created_at"),
        Index("idx_gv_user_created", "user_id", "created_at"),
    )

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "rule_name": self.rule_name,
            "category": self.category,
            "severity": self.severity,
            "action_taken": self.action_taken,
            "message": self.message,
            "execution_id": self.execution_id,
            "node_execution_id": self.node_execution_id,
            "workflow_id": self.workflow_id,
            "agent_node_id": self.agent_node_id,
            "agent_node_name": self.agent_node_name,
            "tool_name": self.tool_name,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
