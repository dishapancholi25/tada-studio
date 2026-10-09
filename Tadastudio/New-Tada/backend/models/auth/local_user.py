"""Local user authentication model for non-Entra users."""

from sqlalchemy import Boolean, Column, String

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class LocalUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A locally-managed user account with email/password credentials.

    Used for external users who don't have a Microsoft Entra account.
    Passwords are stored as bcrypt hashes.

    Attributes:
        id: UUID primary key.
        email: Unique email address (used as login identifier).
        hashed_password: bcrypt hash of the user's password.
        is_active: Whether the account is enabled.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "local_users"

    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
