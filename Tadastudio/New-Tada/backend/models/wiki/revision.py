"""Wiki revision history model."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class WikiRevision(Base, UUIDPrimaryKeyMixin):
    """Model for storing wiki page revision history.

    Tracks historical versions of wiki pages for audit and rollback.

    Attributes:
        id: Unique revision identifier (UUID).
        page_id: Associated page ID.
        title: Page title at this revision.
        content: Page content at this revision.
        version: Sequential version number.
        created_by: User who created this revision.
        change_summary: Optional summary of changes.
        created_at: Revision creation timestamp.
    """

    __tablename__ = "wiki_revisions"

    page_id = Column(
        String, ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False
    )

    # Revision content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)

    # Metadata
    created_by = Column(String, nullable=True)
    change_summary = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    page = relationship("WikiPage", back_populates="revisions")

    # Unique constraint for version per page
    __table_args__ = (
        UniqueConstraint("page_id", "version", name="unique_page_version"),
    )
