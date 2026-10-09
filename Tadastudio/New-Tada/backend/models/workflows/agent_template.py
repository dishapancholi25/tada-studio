"""Agent template model for standalone agent library entries."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class AgentTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for agent templates in the global library.

    Stores agent-centric exports that can be discovered, previewed,
    and cloned independently of full workflow templates.
    """

    __tablename__ = "agent_templates"

    # Relationships back to workflow + graph artifacts
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
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

    # Agent specific metadata
    primary_agent_node_id = Column(String, nullable=True, index=True)
    primary_agent_label = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    complexity = Column(String(50), nullable=True)
    icon_color = Column(String(50), nullable=True)
    agent_metadata = Column(JSON, nullable=True, default=dict)

    # Usage + version tracking
    usage_count = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)
    parent_template_id = Column(
        String,
        ForeignKey("agent_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_latest_version = Column(Boolean, nullable=False, default=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Relationships
    workflow = relationship("Workflow", backref="agent_templates")
    graph_definition = relationship("GraphDefinition", backref="agent_templates")
    creator = relationship("User", backref="created_agent_templates")
    parent_template = relationship(
        "AgentTemplate",
        foreign_keys=[parent_template_id],
        remote_side=lambda: AgentTemplate.id,
        backref="child_versions",
    )
