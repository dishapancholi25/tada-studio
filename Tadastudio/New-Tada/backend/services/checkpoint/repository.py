"""Database repository for checkpoint metadata.

This module provides a repository layer for checkpoint metadata database operations,
following the repository pattern for clean separation of data access logic.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models import CheckpointMetadata
from backend.services.config import get_logger
from backend.services.database import SessionLocal

from .types import CheckpointStatusType, MetadataDict


logger = get_logger("checkpoint.repository")


class CheckpointMetadataRepository:
    """Repository for checkpoint metadata database operations.

    This class encapsulates all database operations for checkpoint metadata,
    providing a clean interface for data access with proper error handling
    and transaction management.

    Example:
        >>> repo = CheckpointMetadataRepository()
        >>> metadata = repo.get_by_checkpoint_id("cp_123")
        >>> repo.create(checkpoint_id="cp_456", thread_id="thread_789", ...)
    """

    @staticmethod
    def get_by_checkpoint_id(
        checkpoint_id: str, status: Optional[str] = None
    ) -> Optional[CheckpointMetadata]:
        """Retrieve checkpoint metadata by checkpoint ID.

        Args:
            checkpoint_id: The checkpoint ID to look up.
            status: Optional status filter (e.g., "active", "completed").

        Returns:
            CheckpointMetadata model instance if found, None otherwise.

        Example:
            >>> metadata = repo.get_by_checkpoint_id("cp_123", status="active")
        """
        try:
            with SessionLocal() as db:
                query = db.query(CheckpointMetadata).filter_by(
                    checkpoint_id=checkpoint_id
                )

                if status:
                    query = query.filter_by(status=status)

                checkpoint_meta = query.first()

                if checkpoint_meta:
                    logger.debug(
                        f"[CHECKPOINT-REPO] Found checkpoint metadata: {checkpoint_id}"
                    )
                else:
                    logger.debug(
                        f"[CHECKPOINT-REPO] No checkpoint metadata found: {checkpoint_id}"
                    )

                return checkpoint_meta

        except SQLAlchemyError as e:
            logger.error(
                f"[CHECKPOINT-REPO] Database error retrieving checkpoint {checkpoint_id}: {e}",
                exc_info=True,
            )
            return None

    @staticmethod
    def create(
        checkpoint_id: str,
        thread_id: str,
        metadata: Dict[str, Any],
    ) -> Optional[CheckpointMetadata]:
        """Create a new checkpoint metadata record.

        Args:
            checkpoint_id: Unique checkpoint identifier.
            thread_id: Thread identifier.
            metadata: Dictionary containing checkpoint metadata.

        Returns:
            Created CheckpointMetadata instance if successful, None otherwise.

        Example:
            >>> metadata = repo.create(
            ...     checkpoint_id="cp_123",
            ...     thread_id="thread_456",
            ...     metadata={"subworkflow_checkpoint": True, ...}
            ... )
        """
        try:
            # Extract metadata fields
            is_subworkflow = metadata.get("subworkflow_checkpoint", False)
            subworkflow_name = metadata.get("subworkflow_name")
            subworkflow_thread_id = metadata.get("subworkflow_thread_id")
            checkpoint_node_exec_id = metadata.get("checkpoint_node_exec_id")
            parent_execution_id = metadata.get("parent_execution_id")
            parent_tool_call = metadata.get("parent_tool_call")

            logger.info(
                f"[CHECKPOINT-REPO] Creating checkpoint metadata: {checkpoint_id}"
            )

            with SessionLocal() as db:
                checkpoint_meta = CheckpointMetadata(
                    checkpoint_id=checkpoint_id,
                    thread_id=thread_id,
                    is_subworkflow=is_subworkflow,
                    subworkflow_name=subworkflow_name,
                    subworkflow_thread_id=subworkflow_thread_id,
                    checkpoint_node_exec_id=checkpoint_node_exec_id,
                    parent_execution_id=parent_execution_id,
                    parent_tool_call=parent_tool_call,
                    interrupt_data=metadata,
                    status=CheckpointStatusType.ACTIVE,
                )

                db.add(checkpoint_meta)
                db.commit()
                db.refresh(checkpoint_meta)

                logger.info(
                    f"[CHECKPOINT-REPO] ✓ Created checkpoint metadata: {checkpoint_id}"
                )
                return checkpoint_meta

        except IntegrityError as e:
            logger.error(
                f"[CHECKPOINT-REPO] Integrity error creating checkpoint {checkpoint_id}: {e}"
            )
            return None
        except SQLAlchemyError as e:
            logger.error(
                f"[CHECKPOINT-REPO] Database error creating checkpoint {checkpoint_id}: {e}",
                exc_info=True,
            )
            return None

    @staticmethod
    def update(
        checkpoint_id: str,
        thread_id: str,
        metadata: Dict[str, Any],
    ) -> Optional[CheckpointMetadata]:
        """Update an existing checkpoint metadata record.

        Args:
            checkpoint_id: Checkpoint identifier to update.
            thread_id: Thread identifier.
            metadata: Updated metadata dictionary.

        Returns:
            Updated CheckpointMetadata instance if successful, None otherwise.

        Example:
            >>> updated = repo.update(
            ...     checkpoint_id="cp_123",
            ...     thread_id="thread_456",
            ...     metadata={"subworkflow_checkpoint": False, ...}
            ... )
        """
        try:
            # Extract metadata fields
            is_subworkflow = metadata.get("subworkflow_checkpoint", False)
            subworkflow_name = metadata.get("subworkflow_name")
            subworkflow_thread_id = metadata.get("subworkflow_thread_id")
            checkpoint_node_exec_id = metadata.get("checkpoint_node_exec_id")
            parent_execution_id = metadata.get("parent_execution_id")
            parent_tool_call = metadata.get("parent_tool_call")

            logger.info(
                f"[CHECKPOINT-REPO] Updating checkpoint metadata: {checkpoint_id}"
            )

            with SessionLocal() as db:
                checkpoint_meta = (
                    db.query(CheckpointMetadata)
                    .filter_by(checkpoint_id=checkpoint_id)
                    .first()
                )

                if not checkpoint_meta:
                    logger.warning(
                        f"[CHECKPOINT-REPO] Checkpoint not found for update: {checkpoint_id}"
                    )
                    return None

                # Update fields
                checkpoint_meta.thread_id = thread_id
                checkpoint_meta.is_subworkflow = is_subworkflow
                checkpoint_meta.subworkflow_name = subworkflow_name
                checkpoint_meta.subworkflow_thread_id = subworkflow_thread_id
                checkpoint_meta.checkpoint_node_exec_id = checkpoint_node_exec_id
                checkpoint_meta.parent_execution_id = parent_execution_id
                checkpoint_meta.parent_tool_call = parent_tool_call
                checkpoint_meta.interrupt_data = metadata
                checkpoint_meta.status = CheckpointStatusType.ACTIVE
                checkpoint_meta.updated_at = datetime.now(timezone.utc)

                db.commit()
                db.refresh(checkpoint_meta)

                logger.info(
                    f"[CHECKPOINT-REPO] ✓ Updated checkpoint metadata: {checkpoint_id}"
                )
                return checkpoint_meta

        except SQLAlchemyError as e:
            logger.error(
                f"[CHECKPOINT-REPO] Database error updating checkpoint {checkpoint_id}: {e}",
                exc_info=True,
            )
            return None

    @staticmethod
    def update_status(checkpoint_id: str, status: str) -> bool:
        """Update the status of a checkpoint.

        Args:
            checkpoint_id: The checkpoint ID.
            status: New status value (e.g., "active", "resumed", "completed").

        Returns:
            True if updated successfully, False otherwise.

        Example:
            >>> success = repo.update_status("cp_123", CheckpointStatusType.COMPLETED)
        """
        try:
            with SessionLocal() as db:
                checkpoint_meta = (
                    db.query(CheckpointMetadata)
                    .filter_by(checkpoint_id=checkpoint_id)
                    .first()
                )

                if not checkpoint_meta:
                    logger.warning(
                        f"[CHECKPOINT-REPO] Checkpoint not found for status update: {checkpoint_id}"
                    )
                    return False

                checkpoint_meta.status = status
                checkpoint_meta.updated_at = datetime.now(timezone.utc)

                db.commit()

                logger.info(
                    f"[CHECKPOINT-REPO] ✓ Updated status to '{status}' for checkpoint: {checkpoint_id}"
                )
                return True

        except SQLAlchemyError as e:
            logger.error(
                f"[CHECKPOINT-REPO] Database error updating status for checkpoint {checkpoint_id}: {e}",
                exc_info=True,
            )
            return False

    @staticmethod
    def get_active_checkpoints(
        thread_id: Optional[str] = None,
    ) -> List[CheckpointMetadata]:
        """Get all active checkpoints, optionally filtered by thread ID.

        Args:
            thread_id: Optional thread ID to filter by.

        Returns:
            List of active CheckpointMetadata instances.

        Example:
            >>> active = repo.get_active_checkpoints(thread_id="thread_456")
            >>> for checkpoint in active:
            ...     print(checkpoint.checkpoint_id)
        """
        try:
            with SessionLocal() as db:
                query = db.query(CheckpointMetadata).filter_by(
                    status=CheckpointStatusType.ACTIVE
                )

                if thread_id:
                    query = query.filter_by(thread_id=thread_id)

                checkpoints = query.all()

                logger.info(
                    f"[CHECKPOINT-REPO] Found {len(checkpoints)} active checkpoints"
                )
                return checkpoints

        except SQLAlchemyError as e:
            logger.error(
                f"[CHECKPOINT-REPO] Database error getting active checkpoints: {e}",
                exc_info=True,
            )
            return []

    @staticmethod
    def to_metadata_dict(checkpoint_meta: CheckpointMetadata) -> MetadataDict:
        """Convert CheckpointMetadata model to metadata dictionary.

        Args:
            checkpoint_meta: CheckpointMetadata model instance.

        Returns:
            Dictionary containing checkpoint metadata.

        Example:
            >>> model = repo.get_by_checkpoint_id("cp_123")
            >>> metadata_dict = repo.to_metadata_dict(model)
        """
        metadata = checkpoint_meta.interrupt_data or {}

        # Ensure key fields are present
        metadata.update(
            {
                "checkpoint_id": checkpoint_meta.checkpoint_id,
                "thread_id": checkpoint_meta.thread_id,
                "subworkflow_checkpoint": checkpoint_meta.is_subworkflow,
                "subworkflow_name": checkpoint_meta.subworkflow_name,
                "subworkflow_thread_id": checkpoint_meta.subworkflow_thread_id,
                "checkpoint_node_exec_id": checkpoint_meta.checkpoint_node_exec_id,
                "parent_execution_id": checkpoint_meta.parent_execution_id,
                "parent_tool_call": checkpoint_meta.parent_tool_call,
            }
        )

        return metadata
