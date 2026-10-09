"""Workflow asset storage model.

This module provides the WorkflowAsset model for storing design-time
assets (e.g., custom Word templates) associated with workflow nodes.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing design-time assets attached to workflow nodes.

    Unlike ExecutionFile (which stores runtime outputs tied to executions),
    WorkflowAsset stores design-time assets like custom document templates
    that persist across executions and graph definition versions.

    Attributes:
        id: Unique asset identifier (UUID).
        workflow_id: Parent workflow ID (CASCADE delete).
        node_id: The node's uniq_id within the graph definition.
        asset_type: Type of asset (e.g., "docx_template").
        filename: Original filename.
        mime_type: MIME type of the asset.
        file_size: File size in bytes.
        content: Binary file content (BYTEA).
        metadata_json: Structured metadata (e.g., extracted template variables).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "workflow_assets"
    __table_args__ = (
        Index("idx_workflow_assets_workflow_id", "workflow_id"),
        Index("idx_workflow_assets_node_id", "node_id"),
        Index(
            "idx_workflow_assets_workflow_node",
            "workflow_id",
            "node_id",
            "asset_type",
        ),
    )

    # Maximum file size (1GB) - enforced at service layer
    MAX_FILE_SIZE_BYTES = 1024 * 1024 * 1024

    # Relationship to parent workflow
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Node reference (not a FK - nodes live in JSON graph definition)
    node_id = Column(String(255), nullable=False)

    # Asset metadata
    asset_type = Column(String(50), nullable=False)  # e.g., "docx_template"
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)

    # Asset content
    content = Column(LargeBinary, nullable=False)

    # Structured metadata (e.g., {"variables": ["client_name", "items"]})
    metadata_json = Column(JSON, nullable=True)

    # Relationships
    workflow = relationship("Workflow", backref="assets")

    def __repr__(self) -> str:
        """Return string representation of the asset."""
        return (
            f"<WorkflowAsset(id={self.id}, workflow_id={self.workflow_id}, "
            f"node_id={self.node_id}, type={self.asset_type}, "
            f"filename={self.filename})>"
        )
