"""Service for storing and retrieving execution files from PostgreSQL."""

import logging
import mimetypes
import uuid
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ....models.execution.execution_file import ExecutionFile
from ....models.execution.graph_execution import GraphExecution
from ....models.execution.node_execution import NodeExecution
from ...database import get_db

logger = logging.getLogger(__name__)
LOG_PREFIX = "[EXECUTION-FILE-SERVICE]"

# Maximum file size (50MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class FileSizeLimitExceeded(Exception):
    """Raised when file exceeds the size limit."""

    pass


class ExecutionFileService:
    """Service for storing workflow-generated files in PostgreSQL.

    This service provides methods to store, retrieve, and manage files
    generated during workflow execution. Files are stored in PostgreSQL
    using BYTEA columns and are automatically deleted when the parent
    node execution is deleted.

    Attributes:
        MAX_FILE_SIZE_BYTES: Maximum allowed file size (50MB).
    """

    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_BYTES

    @staticmethod
    def get_mime_type(filename: str) -> str:
        """Determine MIME type from filename.

        Args:
            filename: The filename with extension.

        Returns:
            MIME type string, or "application/octet-stream" if unknown.
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    def store_file(
        self,
        node_execution_id: str,
        filename: str,
        content: bytes,
        subdirectory: Optional[str] = None,
        text_content: Optional[str] = None,
        db_session: Optional[Session] = None,
    ) -> ExecutionFile:
        """Store a file in PostgreSQL.

        Args:
            node_execution_id: Parent node execution ID.
            filename: Original filename with extension.
            content: Binary file content.
            subdirectory: Optional subdirectory path (metadata only).
            text_content: Optional searchable text content.
            db_session: Optional database session (uses new session if not provided).

        Returns:
            The created ExecutionFile record.

        Raises:
            FileSizeLimitExceeded: If file exceeds 50MB limit.
            ValueError: If required parameters are missing or invalid.
        """
        if not content:
            raise ValueError("File content cannot be empty")

        if not node_execution_id:
            raise ValueError("node_execution_id is required")

        if not filename:
            raise ValueError("filename is required")

        file_size = len(content)
        if file_size > MAX_FILE_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            raise FileSizeLimitExceeded(
                f"File size ({size_mb:.2f}MB) exceeds limit of 50MB"
            )

        mime_type = self.get_mime_type(filename)
        file_id = str(uuid.uuid4())

        logger.info(
            f"{LOG_PREFIX} Storing file: {filename} "
            f"(size={file_size}, mime={mime_type}, node={node_execution_id})"
        )

        def _store(session: Session) -> ExecutionFile:
            execution_file = ExecutionFile(
                id=file_id,
                node_execution_id=node_execution_id,
                filename=filename,
                mime_type=mime_type,
                file_size=file_size,
                content=content,
                text_content=text_content,
                status="stored",
                subdirectory=subdirectory,
            )
            session.add(execution_file)
            session.commit()
            session.refresh(execution_file)
            return execution_file

        if db_session:
            return _store(db_session)
        else:
            with get_db() as session:
                return _store(session)

    def get_file(
        self,
        file_id: str,
        db_session: Optional[Session] = None,
    ) -> Optional[ExecutionFile]:
        """Retrieve a file by ID.

        Args:
            file_id: The file UUID.
            db_session: Optional database session.

        Returns:
            ExecutionFile if found, None otherwise.
        """

        def _get(session: Session) -> Optional[ExecutionFile]:
            return (
                session.query(ExecutionFile).filter(ExecutionFile.id == file_id).first()
            )

        if db_session:
            return _get(db_session)
        else:
            with get_db() as session:
                return _get(session)

    def get_file_content(
        self,
        file_id: str,
        db_session: Optional[Session] = None,
    ) -> Optional[Tuple[bytes, str, str]]:
        """Retrieve file content, MIME type, and filename.

        Args:
            file_id: The file UUID.
            db_session: Optional database session.

        Returns:
            Tuple of (content, mime_type, filename) if found, None otherwise.
        """
        file = self.get_file(file_id, db_session)
        if file:
            return (file.content, file.mime_type, file.filename)
        return None

    def delete_file(
        self,
        file_id: str,
        db_session: Optional[Session] = None,
    ) -> bool:
        """Delete a file by ID.

        Note: Files are automatically deleted via CASCADE when their
        parent node_execution is deleted. This method is for manual deletion.

        Args:
            file_id: The file UUID.
            db_session: Optional database session.

        Returns:
            True if deleted, False if not found.
        """

        def _delete(session: Session) -> bool:
            file = (
                session.query(ExecutionFile).filter(ExecutionFile.id == file_id).first()
            )
            if file:
                session.delete(file)
                session.commit()
                logger.info(f"{LOG_PREFIX} Deleted file: {file_id}")
                return True
            return False

        if db_session:
            return _delete(db_session)
        else:
            with get_db() as session:
                return _delete(session)

    def list_files_by_node(
        self,
        node_execution_id: str,
        db_session: Optional[Session] = None,
    ) -> list[ExecutionFile]:
        """List all files for a node execution.

        Args:
            node_execution_id: The node execution UUID.
            db_session: Optional database session.

        Returns:
            List of ExecutionFile records.
        """

        def _list(session: Session) -> list[ExecutionFile]:
            return (
                session.query(ExecutionFile)
                .filter(ExecutionFile.node_execution_id == node_execution_id)
                .all()
            )

        if db_session:
            return _list(db_session)
        else:
            with get_db() as session:
                return _list(session)

    def get_file_metadata(
        self,
        file_id: str,
        db_session: Optional[Session] = None,
    ) -> Optional[dict]:
        """Get file metadata without loading content.

        Args:
            file_id: The file UUID.
            db_session: Optional database session.

        Returns:
            Dictionary with file metadata, or None if not found.
        """
        file = self.get_file(file_id, db_session)
        if not file:
            return None

        return {
            "id": file.id,
            "filename": file.filename,
            "mime_type": file.mime_type,
            "file_size": file.file_size,
            "status": file.status,
            "subdirectory": file.subdirectory,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "has_text_content": file.text_content is not None,
        }

    def verify_file_ownership(
        self,
        file_id: str,
        user_id: str,
        db_session: Optional[Session] = None,
    ) -> bool:
        """Verify that a user owns the file through the execution chain.

        Checks ownership by traversing: file → node_execution → graph_execution → user_id

        Args:
            file_id: The file UUID to check.
            user_id: The user ID to verify ownership against.
            db_session: Optional database session.

        Returns:
            True if user owns the file, False otherwise.
        """

        def _verify(session: Session) -> bool:
            # Join through the relationship chain to get the user_id
            result = (
                session.query(GraphExecution.user_id)
                .join(
                    NodeExecution, GraphExecution.id == NodeExecution.graph_execution_id
                )
                .join(
                    ExecutionFile, NodeExecution.id == ExecutionFile.node_execution_id
                )
                .filter(ExecutionFile.id == file_id)
                .first()
            )

            if not result:
                logger.warning(
                    f"{LOG_PREFIX} File not found or no execution chain: {file_id}"
                )
                return False

            execution_user_id = result[0]

            # Allow access if user_id matches or if execution has no user_id (legacy data)
            if execution_user_id is None:
                logger.warning(
                    f"{LOG_PREFIX} File {file_id} has no user_id in execution chain - "
                    "allowing access for backwards compatibility"
                )
                return True

            return execution_user_id == user_id

        if db_session:
            return _verify(db_session)
        else:
            with get_db() as session:
                return _verify(session)
