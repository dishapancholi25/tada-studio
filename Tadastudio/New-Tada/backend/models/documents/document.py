"""Document metadata model."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class Document(Base, UUIDPrimaryKeyMixin):
    """Model for document metadata.

    Stores document information including file details, processing status,
    and full-text search capabilities.

    Attributes:
        id: Unique document identifier (UUID).
        collection_id: Parent collection ID.
        name: Document name.
        file_name: Original filename.
        file_type: File type (PDF, DOCX, TXT, etc.).
        file_size: File size in bytes.
        storage_path: Document storage path.
        employee_type: Employee type classification.
        uploaded_at: Upload timestamp.
        updated_at: Last update timestamp.
        status: Processing status (pending, processing, processed, failed).
        error_message: Error message if processing failed.
        search_vector: Full-text search vector.
        text_search_config: Text search configuration language.
        full_text_content: Full text content for searching.
    """

    __tablename__ = "documents"

    collection_id = Column(
        String,
        ForeignKey("document_collections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Document info
    name = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Additional fields from database
    storage_path = Column(Text, nullable=True)
    employee_type = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Processing info
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)

    # Embedding cost tracking
    embedding_tokens = Column(Integer, nullable=True)
    embedding_cost = Column(Float, nullable=True)
    embedding_model = Column(String(255), nullable=True)

    # Full-text search columns
    search_vector = Column(TSVECTOR, nullable=True)
    text_search_config = Column(String(50), nullable=False, default="english")
    full_text_content = Column(Text, nullable=True)

    # Relationships
    collection = relationship("DocumentCollection", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    # Compatibility properties
    @property
    def type(self) -> str | None:
        """Get file type (compatibility property).

        Returns:
            The file type.
        """
        return self.file_type

    @property
    def size(self) -> int | None:
        """Get file size (compatibility property).

        Returns:
            The file size in bytes.
        """
        return self.file_size

    @property
    def chunk_count(self) -> int:
        """Get number of chunks (compatibility property).

        Returns:
            The number of document chunks.
        """
        if hasattr(self, "chunks"):
            return len(self.chunks)
        return 0

    @property
    def loader_mode(self) -> str:
        """Get loader mode (compatibility property).

        Returns:
            The loader mode (always 'single').
        """
        return "single"

    @property
    def processing_metadata(self) -> dict:
        """Get processing metadata (compatibility property).

        Returns:
            Empty dictionary for processing metadata.
        """
        return {}

    @property
    def upload_date(self) -> DateTime | None:
        """Get upload date (compatibility property).

        Returns:
            The upload timestamp.
        """
        return self.uploaded_at
