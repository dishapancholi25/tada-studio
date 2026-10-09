"""Document chunk model with embeddings."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
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

from ...constants import EMBEDDING_DIMENSIONS
from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class DocumentChunk(Base, UUIDPrimaryKeyMixin):
    """Model for document chunks with embeddings.

    Stores individual chunks of documents with vector embeddings
    for semantic search.

    Attributes:
        id: Unique chunk identifier (UUID).
        document_id: Parent document ID.
        chunk_index: Sequential index of this chunk.
        content: Chunk text content.
        embedding: Vector embedding (configurable via EMBEDDING_DIMENSIONS env var).
        chunk_metadata: Additional chunk metadata (JSON).
        created_at: Record creation timestamp.
    """

    __tablename__ = "document_chunks"

    document_id = Column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    chunk_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="unique_document_chunk"),
    )
