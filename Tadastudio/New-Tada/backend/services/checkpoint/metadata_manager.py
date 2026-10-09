"""Checkpoint Metadata Manager for handling checkpoint storage.

This module provides a service for managing checkpoint metadata that persists
across checkpoint boundaries, solving the issue where LangGraph's checkpoint
storage doesn't preserve custom interrupt metadata.
"""

from typing import Any, Dict, List, Optional

from backend.services.config import get_logger

from .cache import CheckpointMetadataCache
from .repository import CheckpointMetadataRepository
from .types import CheckpointStatusType, MetadataDict


logger = get_logger("checkpoint.metadata_manager")


class CheckpointMetadataManager:
    """Manager for storing and retrieving checkpoint metadata.

    This class provides a service layer for checkpoint metadata management,
    combining caching and database operations for optimal performance.

    Attributes:
        repository: Database repository for checkpoint metadata.
        cache: In-memory cache for fast access.

    Example:
        >>> manager = CheckpointMetadataManager()
        >>> manager.store_checkpoint_metadata("cp_123", "thread_456", {...})
        >>> metadata = manager.get_checkpoint_metadata("cp_123")
    """

    def __init__(
        self,
        repository: Optional[CheckpointMetadataRepository] = None,
        cache: Optional[CheckpointMetadataCache] = None,
    ):
        """Initialize the checkpoint metadata manager.

        Args:
            repository: Optional repository instance (creates default if None).
            cache: Optional cache instance (creates default if None).
        """
        self.repository = repository or CheckpointMetadataRepository()
        self.cache = cache or CheckpointMetadataCache()
        logger.info("[CHECKPOINT-META] CheckpointMetadataManager initialized")

    def store_checkpoint_metadata(
        self, checkpoint_id: str, thread_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """Store checkpoint metadata in database and cache.

        Args:
            checkpoint_id: The checkpoint ID.
            thread_id: The thread ID.
            metadata: Dictionary containing checkpoint metadata.

        Returns:
            True if stored successfully, False otherwise.

        Example:
            >>> success = manager.store_checkpoint_metadata(
            ...     "cp_123", "thread_456",
            ...     {"subworkflow_checkpoint": True, "subworkflow_name": "email-handler"}
            ... )
        """
        logger.info(
            f"[CHECKPOINT-META] Storing metadata for checkpoint: {checkpoint_id}"
        )
        logger.debug(
            f"[CHECKPOINT-META]   Thread ID: {thread_id}, "
            f"Is Subworkflow: {metadata.get('subworkflow_checkpoint', False)}, "
            f"Subworkflow Name: {metadata.get('subworkflow_name')}"
        )

        # Check if already exists
        existing = self.repository.get_by_checkpoint_id(checkpoint_id)

        if existing:
            # Update existing record
            logger.info(
                f"[CHECKPOINT-META] Updating existing metadata for: {checkpoint_id}"
            )
            result = self.repository.update(checkpoint_id, thread_id, metadata)
        else:
            # Create new record
            logger.info(f"[CHECKPOINT-META] Creating new metadata for: {checkpoint_id}")
            result = self.repository.create(checkpoint_id, thread_id, metadata)

        if result:
            # Update cache
            self.cache.set(checkpoint_id, metadata)
            logger.info(
                f"[CHECKPOINT-META] ✓ Successfully stored metadata for: {checkpoint_id}"
            )
            return True

        logger.error(f"[CHECKPOINT-META] Failed to store metadata for: {checkpoint_id}")
        return False

    def get_checkpoint_metadata(self, checkpoint_id: str) -> Optional[MetadataDict]:
        """Retrieve checkpoint metadata from cache or database.

        Args:
            checkpoint_id: The checkpoint ID to look up.

        Returns:
            Metadata dictionary if found, None otherwise.

        Example:
            >>> metadata = manager.get_checkpoint_metadata("cp_123")
            >>> if metadata:
            ...     print(f"Thread: {metadata['thread_id']}")
        """
        logger.debug(f"[CHECKPOINT-META] Retrieving metadata for: {checkpoint_id}")

        # Check cache first
        cached_metadata = self.cache.get(checkpoint_id)
        if cached_metadata:
            logger.info(
                f"[CHECKPOINT-META] Found metadata in cache for: {checkpoint_id}"
            )
            return cached_metadata

        # Check database
        checkpoint_meta = self.repository.get_by_checkpoint_id(
            checkpoint_id, status=CheckpointStatusType.ACTIVE
        )

        if checkpoint_meta:
            # Convert to dictionary
            metadata = self.repository.to_metadata_dict(checkpoint_meta)

            # Update cache
            self.cache.set(checkpoint_id, metadata)

            logger.info(
                f"[CHECKPOINT-META] Found metadata in database for: {checkpoint_id}"
            )
            logger.debug(
                f"[CHECKPOINT-META]   Is Subworkflow: {metadata.get('subworkflow_checkpoint')}, "
                f"Subworkflow Name: {metadata.get('subworkflow_name')}"
            )

            return metadata

        logger.info(f"[CHECKPOINT-META] No metadata found for: {checkpoint_id}")
        return None

    def update_checkpoint_status(self, checkpoint_id: str, status: str) -> bool:
        """Update the status of a checkpoint.

        Args:
            checkpoint_id: The checkpoint ID.
            status: New status (use CheckpointStatusType constants).

        Returns:
            True if updated successfully, False otherwise.

        Example:
            >>> manager.update_checkpoint_status("cp_123", CheckpointStatusType.COMPLETED)
        """
        logger.info(
            f"[CHECKPOINT-META] Updating status to '{status}' for: {checkpoint_id}"
        )

        success = self.repository.update_status(checkpoint_id, status)

        if success:
            logger.info(f"[CHECKPOINT-META] ✓ Updated status for: {checkpoint_id}")
        else:
            logger.warning(
                f"[CHECKPOINT-META] Failed to update status for: {checkpoint_id}"
            )

        return success

    def clear_checkpoint_metadata(self, checkpoint_id: str) -> bool:
        """Clear checkpoint metadata from cache and mark as completed in database.

        Args:
            checkpoint_id: The checkpoint ID to clear.

        Returns:
            True if cleared successfully, False otherwise.

        Example:
            >>> manager.clear_checkpoint_metadata("cp_123")
        """
        logger.info(f"[CHECKPOINT-META] Clearing metadata for: {checkpoint_id}")

        # Remove from cache
        self.cache.delete(checkpoint_id)
        logger.debug(f"[CHECKPOINT-META] Removed from cache: {checkpoint_id}")

        # Mark as completed in database
        success = self.update_checkpoint_status(
            checkpoint_id, CheckpointStatusType.COMPLETED
        )

        if success:
            logger.info(f"[CHECKPOINT-META] ✓ Cleared metadata for: {checkpoint_id}")

        return success

    def get_active_checkpoints(
        self, thread_id: Optional[str] = None
    ) -> List[MetadataDict]:
        """Get all active checkpoints, optionally filtered by thread ID.

        Args:
            thread_id: Optional thread ID to filter by.

        Returns:
            List of checkpoint metadata dictionaries.

        Example:
            >>> active_checkpoints = manager.get_active_checkpoints("thread_456")
            >>> for checkpoint in active_checkpoints:
            ...     print(checkpoint["checkpoint_id"])
        """
        logger.debug(
            "[CHECKPOINT-META] Getting active checkpoints"
            + (f" for thread: {thread_id}" if thread_id else "")
        )

        checkpoints = self.repository.get_active_checkpoints(thread_id)

        result = []
        for cp in checkpoints:
            metadata = self.repository.to_metadata_dict(cp)
            # Add created_at timestamp if available
            if cp.created_at:
                metadata["created_at"] = cp.created_at.isoformat()
            result.append(metadata)

        logger.info(f"[CHECKPOINT-META] Found {len(result)} active checkpoint(s)")
        return result


# Global instance for backward compatibility
# Note: In new code, prefer dependency injection using get_checkpoint_metadata_manager()
_checkpoint_metadata_manager_instance: Optional[CheckpointMetadataManager] = None


def get_checkpoint_metadata_manager() -> CheckpointMetadataManager:
    """Get the checkpoint metadata manager instance.

    This function provides a singleton-like access pattern while allowing
    for dependency injection and testing flexibility.

    Returns:
        CheckpointMetadataManager: The manager instance.

    Example:
        >>> from backend.services.checkpoint import get_checkpoint_metadata_manager
        >>> manager = get_checkpoint_metadata_manager()
        >>> manager.store_checkpoint_metadata(...)
    """
    global _checkpoint_metadata_manager_instance

    if _checkpoint_metadata_manager_instance is None:
        _checkpoint_metadata_manager_instance = CheckpointMetadataManager()

    return _checkpoint_metadata_manager_instance


# Legacy alias for backward compatibility
checkpoint_metadata_manager = get_checkpoint_metadata_manager()
