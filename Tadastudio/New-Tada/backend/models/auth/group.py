"""Group and GroupMembership ORM models for RBAC and custom groups."""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin, TimestampMixin


class Group(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "groups"

    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False, index=True)
    created_by_user_id = Column(String(255), ForeignKey("users.id"), nullable=True)

    memberships = relationship(
        "GroupMembership", back_populates="group", cascade="all, delete-orphan"
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class GroupMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "group_memberships"

    group_id = Column(
        String(36),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=False, index=True)

    group = relationship("Group", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user_membership"),
    )
