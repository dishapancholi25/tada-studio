"""GuardrailViolationEvent ORM model for tracking guardrail violations during execution."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import UUIDPrimaryKeyMixin
from backend.services.database import Base


class GuardrailViolationEvent(Base, UUIDPrimaryKeyMixin):
    """Records a single guardrail policy violation that occurred during workflow execution.

    Captures which policy/rule was violated, the severity, what action was taken,
    and links back to the execution, node, workflow, and policy involved.
    """

    __tablename__ = "guardrail_violation_events"

    graph_execution_id = Column(
        String,
        ForeignKey("graph_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_execution_id = Column(
        String,
        ForeignKey("node_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    policy_id = Column(
        String,
        ForeignKey("guardrail_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    policy_name = Column(String, nullable=True)
    rule_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    action_taken = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_node_id = Column(String, nullable=True)
    agent_node_name = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    is_compulsory_policy = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    policy = relationship("GuardrailPolicy", backref="violation_events", foreign_keys=[policy_id])
    feedback = relationship(
        "GuardrailViolationFeedback",
        back_populates="violation_event",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "graph_execution_id": self.graph_execution_id,
            "node_execution_id": self.node_execution_id,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "rule_name": self.rule_name,
            "category": self.category,
            "severity": self.severity,
            "action_taken": self.action_taken,
            "message": self.message,
            "details": self.details,
            "workflow_id": self.workflow_id,
            "agent_node_id": self.agent_node_id,
            "agent_node_name": self.agent_node_name,
            "user_id": self.user_id,
            "is_compulsory_policy": self.is_compulsory_policy,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
