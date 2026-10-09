"""Execution file storage model.

This module provides the ExecutionFile model for storing workflow-generated
files in PostgreSQL instead of the filesystem.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ExecutionFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing workflow-generated files.

    Stores binary file content from FILE_WRITE tool executions
    in PostgreSQL instead of filesystem. Files are automatically
    deleted when their parent NodeExecution is deleted.

    Attributes:
        id: Unique file identifier (UUID).
        node_execution_id: Parent node execution ID (CASCADE delete).
        filename: Original filename with extension.
        mime_type: MIME type (e.g., "application/pdf", "text/plain").
        file_size: File size in bytes.
        content: Binary file content (BYTEA).
        text_content: Searchable text content (for text files and PDF source).
        status: Storage status (stored, failed).
        error_message: Error message if storage failed.
        subdirectory: Optional subdirectory path (metadata only).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "execution_files"
    __table_args__ = (
        Index("idx_execution_files_node_execution_id", "node_execution_id"),
        Index("idx_execution_files_filename", "filename"),
    )

    # Maximum file size (1GB) - enforced at service layer
    MAX_FILE_SIZE_BYTES = 1024 * 1024 * 1024

    # Relationship to parent node execution
    node_execution_id = Column(
        String,
        ForeignKey("node_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # File metadata
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)

    # File content
    content = Column(LargeBinary, nullable=False)
    text_content = Column(Text, nullable=True)  # For searchable text files

    # Status tracking
    status = Column(String(50), default="stored", nullable=False)
    error_message = Column(Text, nullable=True)

    # Optional metadata
    subdirectory = Column(String(255), nullable=True)

    # Relationships
    node_execution = relationship("NodeExecution", back_populates="files")

    def __repr__(self) -> str:
        """Return string representation of the file."""
        return (
            f"<ExecutionFile(id={self.id}, filename={self.filename}, "
            f"size={self.file_size}, mime={self.mime_type})>"
        )
