"""Resource membership models for access control."""

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class DocumentCollectionMembership(Base, UUIDPrimaryKeyMixin):
    """Many-to-many relationship for document collection sharing.

    Manages user access to document collections with role-based permissions.

    Attributes:
        id: Unique membership identifier (UUID).
        collection_id: Associated collection ID.
        user_id: Associated OAuth user ID.
        role: User role (owner, editor, viewer).
        created_at: Record creation timestamp.
    """

    __tablename__ = "document_collection_memberships"

    collection_id = Column(
        String,
        ForeignKey("document_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String, nullable=False, index=True)
    role = Column(String(50), nullable=False, default="viewer")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "collection_id", "user_id", name="uq_collection_user_membership"
        ),
    )


class DataSourceConnectionMembership(Base, UUIDPrimaryKeyMixin):
    """Many-to-many relationship for datasource connection sharing.

    Manages user access to datasource connections with role-based permissions.

    Attributes:
        id: Unique membership identifier (UUID).
        connection_id: Associated connection ID.
        user_id: Associated user ID.
        role: User role (owner, editor, viewer).
        created_at: Record creation timestamp.
    """

    __tablename__ = "datasource_connection_memberships"

    connection_id = Column(
        String,
        ForeignKey("datasource_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String, nullable=False, index=True)
    role = Column(String(50), nullable=False, default="viewer")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "connection_id", "user_id", name="uq_connection_user_membership"
        ),
    )
