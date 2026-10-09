"""GuardrailPolicy ORM model for shared guardrail policies."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


from backend.models.base import UUIDPrimaryKeyMixin
from backend.services.database import Base


class GuardrailPolicy(Base, UUIDPrimaryKeyMixin):
    """A standalone, reusable guardrail policy.

    Stores a full GuardrailsConfig as JSONB along with metadata
    for sharing, scoping, and admin enforcement.

    Visibility is controlled by ``visible_to_groups``:
      - ``[]``            → private (only the creator can see it)
      - ``["__all__"]``   → visible to everyone
      - ``["group1", …]`` → visible to members of the listed groups
    """

    __tablename__ = "guardrail_policies"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    config = Column(JSONB, nullable=False, default=dict)
    scope = Column(String(50), nullable=False, default="user", index=True)
    is_compulsory = Column(Boolean, nullable=False, default=False, index=True)
    applies_to = Column(JSONB, nullable=False, default=list)
    created_by = Column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    visible_to_groups = Column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    # Legacy column – kept for backwards-compat reads; new code uses visible_to_groups
    shared_with = Column(JSONB, nullable=True, default=list)
    is_template = Column(Boolean, nullable=False, default=False, index=True)
    is_builtin = Column(Boolean, nullable=False, default=False, index=True)
    tags = Column(JSONB, nullable=True, default=list)
    version = Column(Integer, nullable=False, default=1)
    current_version = Column(Integer, nullable=False, default=1)
    version_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", backref="guardrail_policies", foreign_keys=[created_by])
    assignments = relationship(
        "GuardrailAssignment",
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "GuardrailPolicyVersion",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="GuardrailPolicyVersion.version",
    )

    def to_dict(self):
        """Serialize to dictionary."""
        visible = self.visible_to_groups or self.shared_with or []
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "config": self.config or {},
            "scope": self.scope,
            "is_compulsory": self.is_compulsory,
            "applies_to": self.applies_to or [],
            "created_by": self.created_by,
            "visible_to_groups": visible,
            # Legacy field kept for backwards compat
            "shared_with": visible,
            "is_template": self.is_template,
            "is_builtin": self.is_builtin,
            "tags": self.tags or [],
            "version": self.version,
            "current_version": self.current_version,
            "version_count": self.version_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "creator_name": (
                self.creator.name
                or self.creator.email
                or self.creator.given_name
            ) if self.creator else ("System" if self.is_builtin else None),
        }
