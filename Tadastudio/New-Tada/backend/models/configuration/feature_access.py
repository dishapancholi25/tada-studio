"""Feature access control model for admin settings."""

from sqlalchemy import Boolean, Column, String
from ...services.database import Base
from ..base import TimestampMixin
import uuid


class FeatureAccess(Base, TimestampMixin):
    """Model for storing feature access control settings.

    Controls which features require admin privileges and which are available
    to all authenticated users.
    """

    __tablename__ = "feature_access"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    feature_name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    admin_only = Column(Boolean, default=True, nullable=False)
    description = Column(String, nullable=True)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "feature_name": self.feature_name,
            "display_name": self.display_name,
            "admin_only": self.admin_only,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
