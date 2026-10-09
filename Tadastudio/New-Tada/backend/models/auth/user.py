"""User authentication models."""

from sqlalchemy import JSON, Column, DateTime, String, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin
from .role import UserRole


class User(Base, TimestampMixin):
    """Authenticated user represented by Microsoft Entra ID claims.

    Manages user authentication via Microsoft Entra ID (Azure AD)
    with OAuth2/OIDC integration.

    Attributes:
        id: Azure AD subject identifier (primary key).
        tenant_id: Azure AD tenant ID.
        object_id: Azure AD object ID (oid claim).
        email: User email address.
        name: Full name.
        given_name: First name.
        family_name: Last name.
        role: User role (PENDING, USER, or ADMIN).
        last_login_at: Last login timestamp.
        last_claims: Last received claims (JSON).
        groups: List of group names from OAuth provider (JSON array).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=True, index=True)
    object_id = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    given_name = Column(String, nullable=True)
    family_name = Column(String, nullable=True)
    role = Column(
        String(20),
        nullable=False,
        default=UserRole.USER.value,
        server_default=UserRole.USER.value,
        index=True,
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_claims = Column(JSON, nullable=True)
    groups = Column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "role IN ('PENDING', 'USER', 'ADMIN', 'SYSTEM')",
            name="ck_users_role",
        ),
    )

    # Relationships
    workflow_memberships = relationship(
        "WorkflowMembership", back_populates="user", cascade="all, delete-orphan"
    )
    api_tokens = relationship(
        "UserAPIToken", back_populates="user", cascade="all, delete-orphan"
    )
    external_services = relationship(
        "UserExternalService", back_populates="user", cascade="all, delete-orphan"
    )
