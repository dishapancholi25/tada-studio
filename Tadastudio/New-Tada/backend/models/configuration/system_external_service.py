"""System-level (admin-managed) external service configuration.

Stores admin-configured external services — e.g. Azure Document Intelligence,
Apache Tika — whose credentials are managed centrally and never exposed to
end users.  Follows the schema proposed in issue #217.

Scope:      System / organisation-wide (no user_id)
Who writes: Admin only
API prefix: /api/admin/settings/external-services/{service_name}
"""

import enum

from sqlalchemy import JSON, Boolean, Column, String, Text
from sqlalchemy import Enum as SQLEnum

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ExternalServiceAuthType(enum.Enum):
    """How credentials are applied when calling the external service."""

    API_KEY_HEADER = "api_key_header"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    QUERY_PARAM = "query_param"
    NONE = "none"


class SystemExternalService(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Admin-managed external service configuration (system / org tier).

    Stores structured configuration for external services that are shared
    across all users.  Credentials are encrypted at rest using
    ``CredentialEncryption`` and are **never** returned to API callers.

    Attributes:
        id:                    UUID primary key.
        service_name:          Stable machine identifier (e.g. ``tavily``,
                               ``azure_document_intelligence``, ``tika``).
        display_name:          Human-readable label shown in the UI.
        service_url:           Base URL / endpoint of the service (may be empty).
        auth_type:             How credentials are applied.
        encrypted_credentials: Encrypted JSON blob containing sensitive fields
                               (``api_key``, ``secret``, ``password``, …).
                               Shape varies per service.
        settings:              Non-sensitive config (headers, timeout, region …).
                               Shape varies per service.
        is_active:             Whether the service is enabled for use.
        created_at:            Record creation timestamp (from TimestampMixin).
        updated_at:            Record last-update timestamp (from TimestampMixin).
    """

    __tablename__ = "system_external_services"

    # Service identification
    service_name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Connection details (non-sensitive)
    service_url = Column(Text, nullable=True)
    auth_type = Column(
        SQLEnum(
            ExternalServiceAuthType,
            name="external_service_auth_type",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ExternalServiceAuthType.API_KEY_HEADER,
        server_default=ExternalServiceAuthType.API_KEY_HEADER.value,
    )

    # Sensitive credentials — encrypted JSON blob (never exposed via API)
    # Shape: {"api_key": "...", "secret": "...", ...} — varies per service
    encrypted_credentials = Column(JSON, nullable=True)

    # Non-sensitive configuration (headers, timeout, region, options …)
    settings = Column(JSON, nullable=False, default=dict, server_default="{}")

    # Status
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")
