"""Workflow container model."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class Workflow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical workflow container that groups graph definitions across versions.

    Represents a workflow with version management and access control.

    Attributes:
        id: Unique workflow identifier (UUID).
        name: Workflow name.
        description: Workflow description.
        created_by_user_id: User ID of workflow creator.
        latest_version: Latest version number.
        is_deleted: Soft delete flag.
        auto_eval_config: JSON auto-evaluation settings (enabled, dataset_id, etc.).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "workflows"
    __table_args__ = (
        Index(
            "uq_workflow_name_user_active",
            "name",
            "created_by_user_id",
            unique=True,
            postgresql_where=Column("is_deleted") == False,  # noqa: E712
        ),
    )

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by_user_id = Column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    latest_version = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    http_trigger_token = Column(String, nullable=True)
    auto_eval_config = Column(JSON, nullable=True)

    # Relationships
    creator = relationship("User", backref="created_workflows")
    graph_definitions = relationship(
        "GraphDefinition", back_populates="workflow", cascade="all, delete-orphan"
    )
    memberships = relationship(
        "WorkflowMembership", back_populates="workflow", cascade="all, delete-orphan"
    )
