"""Wiki page model."""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class WikiPage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing wiki pages with hierarchical structure.

    Manages wiki pages with parent-child relationships, full-text search,
    and publication control.

    Attributes:
        id: Unique page identifier (UUID).
        slug: Unique URL slug.
        title: Page title.
        content: Page content (markdown/HTML).
        parent_id: Parent page ID for hierarchy.
        order_index: Manual ordering within parent.
        is_published: Whether page is published.
        tags: Page tags (JSON array).
        search_vector: Full-text search vector.
        created_by: User who created the page.
        updated_by: User who last updated the page.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "wiki_pages"

    slug = Column(String(500), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    # Hierarchical structure
    parent_id = Column(
        String, ForeignKey("wiki_pages.id", ondelete="SET NULL"), nullable=True
    )
    order_index = Column(Integer, default=0)

    # Publishing and categorization
    is_published = Column(Boolean, default=True, nullable=False, index=True)
    tags = Column(JSON, nullable=True)

    # Full-text search
    search_vector = Column(TSVECTOR, nullable=True)

    # User tracking
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    # Relationships
    parent = relationship(
        "WikiPage",
        foreign_keys=[parent_id],
        remote_side=lambda: WikiPage.id,
        backref="children",
    )
    revisions = relationship(
        "WikiRevision", back_populates="page", cascade="all, delete-orphan"
    )
