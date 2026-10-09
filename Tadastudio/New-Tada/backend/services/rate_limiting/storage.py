"""
Storage backends for rate limiting service.

Provides abstract storage interface and concrete implementations
(in-memory, with potential for Redis or other backends).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Tuple

from ...services.config import get_logger


logger = get_logger(__name__)


@dataclass
class RateLimitBucket:
    """Rate limit bucket for tracking requests using sliding window algorithm."""

    max_requests: int
    window_seconds: int
    requests: List[float] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)

    def is_allowed(self, current_time: float) -> Tuple[bool, int]:
        """
        Check if request is allowed and return remaining count.

        Uses sliding window algorithm: removes expired requests and checks
        if we're under the limit.

        Args:
            current_time: Current timestamp in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        with self.lock:
            # Remove expired requests outside the time window
            cutoff_time = current_time - self.window_seconds
            self.requests = [
                req_time for req_time in self.requests if req_time > cutoff_time
            ]

            # Check if we can add another request
            if len(self.requests) < self.max_requests:
                self.requests.append(current_time)
                remaining = self.max_requests - len(self.requests)
                return True, remaining
            else:
                return False, 0

    def get_reset_time(self, current_time: float) -> float:
        """
        Get the time when the oldest request will expire.

        Args:
            current_time: Current timestamp in seconds

        Returns:
            Timestamp when the rate limit will reset
        """
        if not self.requests:
            return current_time
        return self.requests[0] + self.window_seconds

    def get_remaining_count(self, current_time: float) -> int:
        """
        Get the number of remaining requests without consuming one.

        Args:
            current_time: Current timestamp in seconds

        Returns:
            Number of remaining requests
        """
        with self.lock:
            # Clean up expired requests
            cutoff_time = current_time - self.window_seconds
            self.requests = [
                req_time for req_time in self.requests if req_time > cutoff_time
            ]

            return max(0, self.max_requests - len(self.requests))


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    def get_bucket(
        self, workflow_key: str, limit_type: str, max_requests: int, window_seconds: int
    ) -> RateLimitBucket:
        """
        Get or create a rate limit bucket.

        Args:
            workflow_key: Unique key for workflow:client combination
            limit_type: Type of rate limit (e.g., 'per_minute')
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            RateLimitBucket instance
        """
        pass

    @abstractmethod
    def cleanup_expired(self, current_time: float, max_age_seconds: int) -> int:
        """
        Clean up expired rate limit buckets.

        Args:
            current_time: Current timestamp
            max_age_seconds: Maximum age for unused buckets

        Returns:
            Number of buckets cleaned up
        """
        pass


class InMemoryRateLimitStorage(RateLimitStorage):
    """In-memory storage backend for rate limiting."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._buckets: Dict[str, Dict[str, RateLimitBucket]] = {}
        self._lock = Lock()
        logger.debug("[RATE-LIMITING] Initialized in-memory storage backend")

    def get_bucket(
        self, workflow_key: str, limit_type: str, max_requests: int, window_seconds: int
    ) -> RateLimitBucket:
        """
        Get or create a rate limit bucket.

        Thread-safe bucket creation with double-checked locking pattern.

        Args:
            workflow_key: Unique key for workflow:client combination
            limit_type: Type of rate limit (e.g., 'per_minute')
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            RateLimitBucket instance
        """
        # Ensure workflow buckets dict exists
        if workflow_key not in self._buckets:
            with self._lock:
                if workflow_key not in self._buckets:
                    self._buckets[workflow_key] = {}
                    logger.debug(
                        f"[RATE-LIMITING] Created bucket dict for key: {workflow_key}"
                    )

        buckets = self._buckets[workflow_key]

        # Ensure specific limit type bucket exists
        if limit_type not in buckets:
            with self._lock:
                if limit_type not in buckets:
                    buckets[limit_type] = RateLimitBucket(
                        max_requests=max_requests, window_seconds=window_seconds
                    )
                    logger.debug(
                        f"[RATE-LIMITING] Created bucket for {workflow_key}:{limit_type} "
                        f"(limit={max_requests}, window={window_seconds}s)"
                    )

        return buckets[limit_type]

    def cleanup_expired(self, current_time: float, max_age_seconds: int) -> int:
        """
        Clean up expired rate limit buckets to prevent memory leaks.

        Removes buckets that have no recent requests older than max_age_seconds.

        Args:
            current_time: Current timestamp
            max_age_seconds: Maximum age for unused buckets

        Returns:
            Number of workflow keys cleaned up
        """
        cutoff_time = current_time - max_age_seconds
        workflows_removed = 0

        with self._lock:
            workflows_to_remove = []

            for workflow_key, buckets in self._buckets.items():
                buckets_to_remove = []

                for limit_type, bucket in buckets.items():
                    with bucket.lock:
                        # Remove expired requests from bucket
                        bucket_cutoff = current_time - bucket.window_seconds
                        bucket.requests = [
                            req_time
                            for req_time in bucket.requests
                            if req_time > bucket_cutoff
                        ]

                        # If bucket is empty and old, mark for removal
                        if not bucket.requests or (
                            bucket.requests
                            and max(bucket.requests, default=0) < cutoff_time
                        ):
                            buckets_to_remove.append(limit_type)

                # Remove empty buckets for this workflow
                for limit_type in buckets_to_remove:
                    del buckets[limit_type]

                # If all buckets are gone, mark workflow for removal
                if not buckets:
                    workflows_to_remove.append(workflow_key)

            # Remove empty workflow entries
            for workflow_key in workflows_to_remove:
                del self._buckets[workflow_key]
                workflows_removed += 1

        if workflows_removed > 0:
            logger.info(
                f"[RATE-LIMITING] Cleaned up {workflows_removed} expired bucket entries"
            )

        return workflows_removed

    def get_stats(self) -> Dict[str, int]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats (workflow_keys, total_buckets)
        """
        with self._lock:
            total_buckets = sum(len(buckets) for buckets in self._buckets.values())
            return {
                "workflow_keys": len(self._buckets),
                "total_buckets": total_buckets,
            }
