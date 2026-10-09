"""Node version index model for tracking individual node versions across graph definitions."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class NodeVersionIndex(Base, UUIDPrimaryKeyMixin):
    """Tracks individual node config versions across graph definition versions.

    When a graph definition is saved, each node's configuration is hashed.
    If the hash differs from the previous graph version, the node_version
    is incremented. This enables associating feedback and evaluation results
    with a specific node configuration.

    Attributes:
        id: Unique identifier (UUID).
        graph_definition_id: The graph definition this entry belongs to.
        workflow_id: Parent workflow for convenient querying.
        node_id: Node identifier within the graph definition JSON.
        node_type: Type of the node (AGENT, CONDITION, etc.).
        node_name: Human-readable node name.
        config_hash: SHA256 hash of the node's configuration JSON.
        config_json: Snapshot of the node's configuration at this version.
        node_version: Auto-incremented version per node_id when config changes.
        created_at: Record creation timestamp.
    """

    __tablename__ = "node_version_index"

    graph_definition_id = Column(
        String,
        ForeignKey("graph_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    node_id = Column(String, nullable=False, index=True)
    node_type = Column(String, nullable=False)
    node_name = Column(String, nullable=False)
    config_hash = Column(String(64), nullable=False, index=True)
    config_json = Column(JSON, nullable=False)
    node_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    graph_definition = relationship(
        "GraphDefinition", foreign_keys=[graph_definition_id]
    )
    workflow = relationship("Workflow", foreign_keys=[workflow_id])

    __table_args__ = (
        UniqueConstraint(
            "graph_definition_id", "node_id", name="_node_version_graph_def_uc"
        ),
    )
