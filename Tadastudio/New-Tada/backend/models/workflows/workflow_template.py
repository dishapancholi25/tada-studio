"""Workflow template model for library functionality."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import backref, relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for workflow templates in the global library.

    Represents a workflow template that has been added to the public library,
    with metadata for categorization, search, and discovery.

    Attributes:
        id: Unique template identifier (UUID).
        workflow_id: Associated workflow ID.
        graph_definition_id: Specific graph definition version used as template.
        name: Display name for the template in the library.
        description: Detailed template description.
        category: List of template categories (e.g., ["Sales", "Customer Service"]).
        tags: List of tags for search and filtering (JSON array).
        complexity: Difficulty level (beginner/intermediate/advanced).
        icon_color: Display color for the template icon.
        created_by_user_id: User who created this template.
        usage_count: Number of times this template has been cloned.
        version: Template version number for versioning.
        parent_template_id: Parent template ID for version tracking.
        is_latest_version: Whether this is the latest version.
        is_active: Whether template is active (soft delete flag).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "workflow_templates"

    # Core relationships
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    graph_definition_id = Column(
        String,
        ForeignKey("graph_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Template metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(JSON, nullable=False, default=list)  # Array of category strings
    tags = Column(JSON, nullable=False, default=list)  # Array of strings
    complexity = Column(String(50), nullable=True)  # beginner/intermediate/advanced
    icon_color = Column(String(50), nullable=True)

    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    parent_template_id = Column(
        String,
        ForeignKey("workflow_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_latest_version = Column(Boolean, nullable=False, default=True, index=True)

    # Soft delete
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Relationships
    workflow = relationship(
        "Workflow",
        backref=backref("templates", passive_deletes=True),
        passive_deletes=True,
    )
    graph_definition = relationship(
        "GraphDefinition",
        backref=backref("templates", passive_deletes=True),
        passive_deletes=True,
    )
    creator = relationship("User", backref="created_templates")
    parent_template = relationship(
        "WorkflowTemplate",
        foreign_keys=[parent_template_id],
        remote_side=lambda: WorkflowTemplate.id,
        backref="child_versions",
    )
