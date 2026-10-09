"""GuardrailPolicyVersion ORM model for immutable policy snapshots."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import UUIDPrimaryKeyMixin
from backend.services.database import Base


class GuardrailPolicyVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable snapshot of a guardrail policy at a point in time.

    A new row is inserted (never updated) on every call to PolicyService.save().
    The active version number is mirrored on guardrail_policies.version.

    Retention: indefinite (compliance requirement).
    """

    __tablename__ = "guardrail_policy_versions"

    policy_id = Column(
        String,
        ForeignKey("guardrail_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    config_snapshot = Column(JSONB, nullable=False)
    name_snapshot = Column(String(255), nullable=True)
    description_snapshot = Column(Text, nullable=True)
    changed_by = Column(String, nullable=True)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    policy = relationship("GuardrailPolicy", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_guardrail_policy_version"),
        Index("idx_gpv_policy_version", "policy_id", "version"),
    )

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "version": self.version,
            "version_number": self.version,
            "config_snapshot": self.config_snapshot or {},
            "name_snapshot": self.name_snapshot,
            "description_snapshot": self.description_snapshot,
            "changed_by": self.changed_by,
            "change_summary": self.change_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
