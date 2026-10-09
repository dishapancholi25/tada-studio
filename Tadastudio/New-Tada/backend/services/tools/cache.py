"""
Tool cache management with TTL and size limits.

This module provides caching capabilities for tool instances and results
with automatic expiration and size management.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from ..config import get_logger


logger = get_logger("tool-cache")


@dataclass
class CacheEntry:
    """
    A single cache entry with metadata.

    Attributes:
        value: The cached value
        created_at: When the entry was created
        ttl: Time-to-live in seconds
        access_count: Number of times accessed
        last_accessed: Last access timestamp
    """

    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int = 300  # seconds
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def is_expired(self) -> bool:
        """
        Check if this cache entry has expired.

        Returns:
            True if expired, False otherwise
        """
        if self.ttl <= 0:
            return False  # No expiration

        expiry_time = self.created_at + timedelta(seconds=self.ttl)
        return datetime.now(timezone.utc) > expiry_time

    def mark_accessed(self) -> None:
        """Mark that this entry was accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


class ToolCache:
    """
    Cache for tool instances and results with TTL and size management.

    Features:
        - Automatic expiration based on TTL
        - LRU eviction when max size reached
        - Access tracking for statistics
        - Thread-safe operations
    """

    def __init__(self, max_size: int = 128, default_ttl: int = 300):
        """
        Initialize the tool cache.

        Args:
            max_size: Maximum number of entries (0 for unlimited)
            default_ttl: Default TTL in seconds (0 for no expiration)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        logger.info(
            f"[TOOL-CACHE] Initialized with max_size={max_size}, default_ttl={default_ttl}s"
        )

    def generate_key(
        self, tool_name: str, config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a cache key from tool name and configuration.

        Args:
            tool_name: Name of the tool
            config: Optional configuration dictionary

        Returns:
            Cache key string (MD5 hash)
        """
        config_str = json.dumps(config or {}, sort_keys=True)
        key_material = f"{tool_name}:{config_str}"
        return hashlib.md5(key_material.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.is_expired():
            logger.debug(f"[TOOL-CACHE] Expired entry for key: {key[:8]}...")
            del self._cache[key]
            self._stats["misses"] += 1
            self._stats["expirations"] += 1
            return None

        # Mark accessed and return
        entry.mark_accessed()
        self._stats["hits"] += 1
        logger.debug(
            f"[TOOL-CACHE] Cache hit for key: {key[:8]}... (accessed {entry.access_count} times)"
        )
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if not specified)
        """
        # Check if we need to evict entries
        if self._max_size > 0 and len(self._cache) >= self._max_size:
            if key not in self._cache:  # Only evict if adding new entry
                self._evict_lru()

        # Create and store entry
        entry = CacheEntry(
            value=value,
            ttl=ttl if ttl is not None else self._default_ttl,
        )
        self._cache[key] = entry
        logger.debug(
            f"[TOOL-CACHE] Cached value for key: {key[:8]}... (ttl={entry.ttl}s)"
        )

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].last_accessed or self._cache[k].created_at),
        )

        del self._cache[lru_key]
        self._stats["evictions"] += 1
        logger.debug(f"[TOOL-CACHE] Evicted LRU entry: {lru_key[:8]}...")

    def clear(self) -> None:
        """Clear all cache entries."""
        entry_count = len(self._cache)
        self._cache.clear()
        logger.info(f"[TOOL-CACHE] Cleared {entry_count} cache entries")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1

        if expired_keys:
            logger.info(f"[TOOL-CACHE] Cleaned up {len(expired_keys)} expired entries")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "expirations": self._stats["expirations"],
            "total_requests": total_requests,
        }

    def __len__(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key is in cache (doesn't count as access)."""
        return key in self._cache and not self._cache[key].is_expired()
