"""Base classes and mixins for SQLAlchemy models.

This module provides reusable base classes and mixins to reduce code
duplication across model definitions.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func


class UUIDPrimaryKeyMixin:
    """Mixin that provides a UUID primary key with automatic generation.

    Attributes:
        id: String primary key with UUID generation.
    """

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    """Mixin that provides created_at and updated_at timestamp columns.

    Attributes:
        created_at: Timestamp of record creation (auto-populated).
        updated_at: Timestamp of last update (auto-updated).
    """

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SoftDeleteMixin:
    """Mixin that provides soft delete functionality.

    Attributes:
        is_deleted: Boolean flag for soft deletion (default: False).
    """

    is_deleted = Column(Boolean, default=False, nullable=False)


def generate_uuid() -> str:
    """Generate a new UUID string.

    Returns:
        A new UUID as a string.
    """
    return str(uuid.uuid4())
