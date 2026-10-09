"""Document collection model."""

from sqlalchemy import BigInteger, Column, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentCollection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for document collections.

    Represents a logical grouping of documents with ownership tracking
    and group-based visibility control.

    Attributes:
        id: Unique collection identifier (UUID).
        name: Unique collection name.
        description: Collection description.
        user_id: Owner user ID.
        visible_to_groups: JSONB array of group names that can access
            this collection. Empty array means private (only creator).
            ["__all__"] means global (all users). Specific group names
            restrict access to members of those groups.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "document_collections"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String(255), nullable=True, index=True)
    embedding_deployment_id = Column(String(255), nullable=True)
    search_count = Column(BigInteger, nullable=False, server_default=text("0"))
    visible_to_groups = Column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_collection_user_name"),
        Index(
            "idx_document_collections_visible_to_groups",
            visible_to_groups,
            postgresql_using="gin",
        ),
    )

    # Relationships
    documents = relationship(
        "Document", back_populates="collection", cascade="all, delete-orphan"
    )
