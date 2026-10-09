"""Graph definition model for workflow versions."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class GraphDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing graph definitions in database.

    Represents a versioned graph definition with change tracking
    and workspace management.

    Attributes:
        id: Unique graph definition identifier (UUID).
        name: Graph definition name.
        workspace_id: Workspace identifier.
        workflow_id: Associated workflow ID.
        definition_json: The actual graph structure (JSON).
        description: Graph definition description.
        version: Version number.
        is_latest: Whether this is the latest version.
        parent_version_id: Parent version ID for version tracking.
        created_by: User who created this version.
        file_hash: SHA256 hash for change detection.
        size_bytes: Definition size in bytes.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "graph_definitions"

    name = Column(String(255), nullable=False, index=True)
    workspace_id = Column(String(255), nullable=False, default="default", index=True)
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Graph content
    definition_json = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True, index=True)
    parent_version_id = Column(
        String, ForeignKey("graph_definitions.id"), nullable=True
    )

    # Metadata
    created_by = Column(String(255), nullable=True)
    file_hash = Column(String(64), nullable=True)
    size_bytes = Column(Integer, nullable=True)

    # Relationships
    parent_version = relationship(
        "GraphDefinition",
        foreign_keys=[parent_version_id],
        remote_side=lambda: GraphDefinition.id,
        backref="child_versions",
    )
    workflow = relationship("Workflow", back_populates="graph_definitions")

    # Unique constraint for latest version per workspace
    __table_args__ = (
        UniqueConstraint(
            "name", "workspace_id", "version", name="_graph_workspace_version_uc"
        ),
    )
