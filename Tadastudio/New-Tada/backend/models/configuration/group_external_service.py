"""Group-level external service configuration.

Stores admin-configured MCP tool configurations scoped to one or more groups,
sitting between personal (user-tier) and system-wide configurations.

Resolution order: personal → group → system
"""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin
from .system_external_service import ExternalServiceAuthType


class GroupExternalServiceConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Admin-managed group-scoped external service configuration.

    A single configuration can be assigned to one or more groups via
    GroupExternalServiceAssignment records.  Only admins may create, edit,
    or delete these records.  Group members can see which tools are
    provisioned for their groups but cannot view credentials.

    Attributes:
        id:                    UUID primary key.
        service_name:          Stable machine identifier matching the user/system tier
                               naming convention (e.g. ``mcp_preset_github``,
                               ``mcp_server_custom_name``).
        display_name:          Human-readable label shown in the UI.
        description:           Optional description.
        service_url:           Base URL / endpoint (non-sensitive, may be empty).
        auth_type:             How credentials are applied.
        encrypted_api_key:     Encrypted primary credential blob (JSON or single key).
        encrypted_credentials: Optional encrypted structured credentials dict.
        settings:              Non-sensitive config (connection params, metadata, etc.).
        is_active:             Whether this config is currently enabled.
        created_at:            Record creation timestamp.
        updated_at:            Record last-update timestamp.
    """

    __tablename__ = "group_external_service_configs"

    service_name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    service_url = Column(Text, nullable=True)
    auth_type = Column(
        SQLEnum(
            ExternalServiceAuthType,
            name="external_service_auth_type",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ExternalServiceAuthType.API_KEY_HEADER,
        server_default=ExternalServiceAuthType.API_KEY_HEADER.value,
    )

    # Sensitive credentials — encrypted, never exposed to API callers
    encrypted_api_key = Column(String, nullable=False, default="", server_default="")
    encrypted_credentials = Column(JSON, nullable=True)

    settings = Column(JSON, nullable=False, default=dict, server_default="{}")
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")

    assignments = relationship(
        "GroupExternalServiceAssignment",
        back_populates="config",
        cascade="all, delete-orphan",
    )


class GroupExternalServiceAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maps a GroupExternalServiceConfig to a group.

    A single config can be assigned to multiple groups; each row represents
    one (config, group) pair.

    Attributes:
        config_id: FK to GroupExternalServiceConfig.
        group_id:  FK to the groups table.
    """

    __tablename__ = "group_external_service_assignments"

    config_id = Column(
        String(36),
        ForeignKey("group_external_service_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id = Column(
        String(36),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    config = relationship("GroupExternalServiceConfig", back_populates="assignments")
    group = relationship("Group")
