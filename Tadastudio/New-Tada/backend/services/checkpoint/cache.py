"""In-memory cache for checkpoint metadata.

This module provides a simple in-memory cache for checkpoint metadata,
reducing database queries and improving performance for frequently accessed checkpoints.
"""

from typing import Dict, Optional

from backend.services.config import get_logger

from .types import MetadataDict


logger = get_logger("checkpoint.cache")


class CheckpointMetadataCache:
    """In-memory cache for checkpoint metadata.

    This class provides a simple dictionary-based cache for storing and retrieving
    checkpoint metadata, improving performance by reducing database queries.

    Attributes:
        _cache: Internal dictionary storing checkpoint metadata by checkpoint_id.

    Example:
        >>> cache = CheckpointMetadataCache()
        >>> cache.set("cp_123", {"thread_id": "thread_456", ...})
        >>> metadata = cache.get("cp_123")
        >>> cache.delete("cp_123")
    """

    def __init__(self):
        """Initialize the checkpoint metadata cache."""
        self._cache: Dict[str, MetadataDict] = {}
        logger.debug("[CHECKPOINT-CACHE] Cache initialized")

    def get(self, checkpoint_id: str) -> Optional[MetadataDict]:
        """Retrieve checkpoint metadata from cache.

        Args:
            checkpoint_id: The checkpoint ID to look up.

        Returns:
            Metadata dictionary if found in cache, None otherwise.

        Example:
            >>> metadata = cache.get("cp_123")
            >>> if metadata:
            ...     print(f"Thread: {metadata['thread_id']}")
        """
        metadata = self._cache.get(checkpoint_id)

        if metadata:
            logger.debug(
                f"[CHECKPOINT-CACHE] Cache hit for checkpoint: {checkpoint_id}"
            )
        else:
            logger.debug(
                f"[CHECKPOINT-CACHE] Cache miss for checkpoint: {checkpoint_id}"
            )

        return metadata

    def set(self, checkpoint_id: str, metadata: MetadataDict) -> None:
        """Store checkpoint metadata in cache.

        Args:
            checkpoint_id: The checkpoint ID.
            metadata: Metadata dictionary to cache.

        Example:
            >>> cache.set("cp_123", {"thread_id": "thread_456", ...})
        """
        self._cache[checkpoint_id] = metadata
        logger.debug(
            f"[CHECKPOINT-CACHE] Cached metadata for checkpoint: {checkpoint_id}"
        )

    def delete(self, checkpoint_id: str) -> bool:
        """Remove checkpoint metadata from cache.

        Args:
            checkpoint_id: The checkpoint ID to remove.

        Returns:
            True if item was in cache and removed, False otherwise.

        Example:
            >>> was_cached = cache.delete("cp_123")
        """
        if checkpoint_id in self._cache:
            del self._cache[checkpoint_id]
            logger.debug(
                f"[CHECKPOINT-CACHE] Removed checkpoint from cache: {checkpoint_id}"
            )
            return True

        logger.debug(f"[CHECKPOINT-CACHE] Checkpoint not in cache: {checkpoint_id}")
        return False

    def clear(self) -> None:
        """Clear all cached checkpoint metadata.

        Example:
            >>> cache.clear()
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[CHECKPOINT-CACHE] Cleared {count} cached items")

    def size(self) -> int:
        """Get the number of cached items.

        Returns:
            Number of checkpoints currently in cache.

        Example:
            >>> num_cached = cache.size()
        """
        return len(self._cache)
