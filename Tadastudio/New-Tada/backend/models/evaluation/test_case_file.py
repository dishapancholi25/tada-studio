"""Test case file attachment model.

Stores binary file content for evaluation test cases that require
file-based inputs (e.g. PDF processing workflows).
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class TestCaseFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Binary file attached to an evaluation test case.

    When the evaluation orchestrator executes a test case that has an
    attached file, it loads the binary content, base64-encodes it, and
    injects it as ``file_info`` in the workflow's initial state — the
    same format used by the ``/trigger-form`` HTTP execution endpoint.

    Files are cascade-deleted when their parent test case is removed.

    Attributes:
        id: Unique file identifier (UUID).
        test_case_id: Parent test case ID (CASCADE delete).
        filename: Original filename with extension.
        mime_type: MIME type (e.g. "application/pdf").
        file_size: File size in bytes.
        content: Binary file content (BYTEA).
    """

    __tablename__ = "test_case_files"
    __table_args__ = (Index("idx_test_case_files_test_case_id", "test_case_id"),)

    MAX_FILE_SIZE_BYTES = 1024 * 1024 * 1024  # 1 GB

    test_case_id = Column(
        String,
        ForeignKey("evaluation_test_cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    content = Column(LargeBinary, nullable=False)

    # Relationships
    test_case = relationship("EvaluationTestCase", back_populates="files")

    def __repr__(self) -> str:
        return (
            f"<TestCaseFile(id={self.id}, filename={self.filename}, "
            f"size={self.file_size}, mime={self.mime_type})>"
        )
