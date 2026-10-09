"""Caching utilities for compiled agents.

This module provides caching functionality for compiled agents,
including TTL-based expiration and LRU eviction.
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

from backend.services.config import get_logger

from .config import CACHE_TTL_SECONDS, ENABLE_CACHE, MAX_CACHE_SIZE
from .models import CacheStats, CompiledAgent


logger = get_logger("agent.cache")


@dataclass
class CacheEntry:
    """Entry in the compilation cache.

    Attributes:
        agent: The compiled agent
        timestamp: When the entry was cached (Unix timestamp)
        access_count: Number of times this entry was accessed
    """

    agent: CompiledAgent
    timestamp: float
    access_count: int = 0


class CompilationCache:
    """Cache for compiled agents with TTL and LRU eviction.

    Manages a cache of compiled agents with configurable size limits
    and time-to-live expiration. Uses LRU (Least Recently Used) eviction
    when the cache reaches maximum size.
    """

    def __init__(
        self,
        max_size: int = MAX_CACHE_SIZE,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        enabled: bool = ENABLE_CACHE,
    ):
        """Initialize compilation cache.

        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cache entries in seconds
            enabled: Whether caching is enabled
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats(max_size=max_size)
        logger.info(
            f"Initialized compilation cache (max_size={max_size}, ttl={ttl_seconds}s, enabled={enabled})"
        )

    def get(self, cache_key: str) -> Optional[CompiledAgent]:
        """Get a compiled agent from cache.

        Args:
            cache_key: Cache key to look up

        Returns:
            Compiled agent if found and not expired, None otherwise
        """
        if not self.enabled:
            return None

        entry = self._cache.get(cache_key)
        if entry is None:
            self._stats.misses += 1
            logger.debug(f"Cache miss for key: {cache_key}")
            return None

        # Check if entry has expired
        if self._is_expired(entry):
            logger.debug(f"Cache entry expired for key: {cache_key}")
            self._evict(cache_key)
            self._stats.misses += 1
            self._stats.evictions += 1
            return None

        # Update access statistics
        entry.access_count += 1
        self._stats.hits += 1
        logger.debug(
            f"Cache hit for key: {cache_key} (access_count={entry.access_count})"
        )
        return entry.agent

    def set(self, cache_key: str, agent: CompiledAgent) -> None:
        """Store a compiled agent in cache.

        Args:
            cache_key: Cache key to store under
            agent: Compiled agent to cache
        """
        if not self.enabled:
            return

        # Evict entries if cache is full
        if len(self._cache) >= self.max_size and cache_key not in self._cache:
            self._evict_lru()

        # Store the entry
        entry = CacheEntry(agent=agent, timestamp=time.time(), access_count=0)
        self._cache[cache_key] = entry
        self._stats.size = len(self._cache)
        logger.debug(f"Cached agent with key: {cache_key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        entry_count = len(self._cache)
        self._cache.clear()
        self._stats.size = 0
        logger.info(f"Cleared {entry_count} entries from cache")

    def optimize(self) -> None:
        """Optimize cache by removing expired entries.

        This is called periodically to clean up expired entries
        without waiting for them to be accessed.
        """
        if not self.enabled:
            return

        expired_keys = [
            key for key, entry in self._cache.items() if self._is_expired(entry)
        ]

        for key in expired_keys:
            self._evict(key)
            self._stats.evictions += 1

        if expired_keys:
            logger.info(f"Optimized cache: removed {len(expired_keys)} expired entries")

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats object with current statistics
        """
        self._stats.size = len(self._cache)
        return self._stats

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired.

        Args:
            entry: Cache entry to check

        Returns:
            True if entry has expired
        """
        age = time.time() - entry.timestamp
        return age > self.ttl_seconds

    def _evict(self, cache_key: str) -> None:
        """Evict a specific cache entry.

        Args:
            cache_key: Key of entry to evict
        """
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._stats.size = len(self._cache)

    def _evict_lru(self) -> None:
        """Evict least recently used cache entry.

        Evicts the entry with the lowest access count. If multiple
        entries have the same access count, evicts the oldest.
        """
        if not self._cache:
            return

        # Find LRU entry (lowest access count, then oldest)
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].access_count, self._cache[k].timestamp),
        )

        logger.debug(
            f"Evicting LRU entry: {lru_key} "
            f"(access_count={self._cache[lru_key].access_count})"
        )
        self._evict(lru_key)
        self._stats.evictions += 1
