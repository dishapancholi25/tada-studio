"""GuardrailViolationFeedback ORM model for user feedback on violations."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import UUIDPrimaryKeyMixin
from backend.services.database import Base


class GuardrailViolationFeedback(Base, UUIDPrimaryKeyMixin):
    """User thumbs-up/down feedback on an individual violation event.

    One feedback record per (violation_id, user_id) pair -- upsert semantics.
    Supports both GuardrailViolation and GuardrailViolationEvent references.
    """

    __tablename__ = "guardrail_violation_feedback"

    violation_id = Column(
        String,
        ForeignKey("guardrail_violations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    violation_event_id = Column(
        String,
        ForeignKey("guardrail_violation_events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(String, nullable=False, index=True)
    rating = Column(String(20), nullable=False)  # "positive" (legitimate) | "negative" (false positive)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    violation = relationship("GuardrailViolation", back_populates="feedbacks", foreign_keys=[violation_id])
    violation_event = relationship(
        "GuardrailViolationEvent",
        back_populates="feedback",
        foreign_keys=[violation_event_id],
    )

    __table_args__ = (
        UniqueConstraint("violation_id", "user_id", name="uq_violation_user_feedback"),
    )

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "violation_id": self.violation_id,
            "violation_event_id": self.violation_event_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
