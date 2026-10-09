"""
Rate limiting strategy implementations.

Provides different algorithms for rate limiting enforcement.
Currently implements sliding window algorithm.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

from ...services.config import get_logger
from .config import RateLimitSettings
from .storage import RateLimitStorage


logger = get_logger(__name__)


class RateLimitStrategy(ABC):
    """Abstract base class for rate limiting strategies."""

    @abstractmethod
    def check_limit(
        self,
        workflow_name: str,
        client_identifier: str,
        rate_limit_config: Dict[str, int],
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limits.

        Args:
            workflow_name: Name of the workflow
            client_identifier: Unique identifier for the client
            rate_limit_config: Rate limit configuration

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        pass


class SlidingWindowStrategy(RateLimitStrategy):
    """
    Sliding window rate limiting strategy.

    Tracks requests in a time-based sliding window and enforces limits
    based on request count within that window.
    """

    def __init__(
        self,
        storage: RateLimitStorage,
        settings: Optional[RateLimitSettings] = None,
    ):
        """
        Initialize sliding window strategy.

        Args:
            storage: Storage backend for rate limit data
            settings: Rate limit settings (uses defaults if not provided)
        """
        self.storage = storage
        self.settings = settings or RateLimitSettings()
        logger.debug("[RATE-LIMITING] Initialized sliding window strategy")

    def check_limit(
        self,
        workflow_name: str,
        client_identifier: str,
        rate_limit_config: Dict[str, int],
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limits using sliding window algorithm.

        Args:
            workflow_name: Name of the workflow
            client_identifier: Unique identifier for the client
            rate_limit_config: Rate limit configuration (e.g., {'per_minute': 60})

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            - is_allowed: True if request is allowed, False if rate limit exceeded
            - rate_limit_info: Dict with limit details (remaining, reset_time, etc.)
        """
        if not rate_limit_config:
            return True, {"message": "No rate limits configured"}

        current_time = time.time()
        workflow_key = f"{workflow_name}:{client_identifier}"
        rate_limit_info = {}

        if self.settings.debug_logging:
            logger.debug(
                f"[RATE-LIMITING] Checking limits for {workflow_key}: {rate_limit_config}"
            )

        # Check each rate limit type
        for limit_type, max_requests in rate_limit_config.items():
            window_seconds = self.settings.get_window_seconds(limit_type)

            if window_seconds is None:
                logger.warning(f"[RATE-LIMITING] Unknown rate limit type: {limit_type}")
                continue

            # Get or create bucket for this limit type
            bucket = self.storage.get_bucket(
                workflow_key, limit_type, max_requests, window_seconds
            )

            # Check if request is allowed
            is_allowed, remaining = bucket.is_allowed(current_time)

            if not is_allowed:
                reset_time = int(bucket.get_reset_time(current_time))
                retry_after = reset_time - int(current_time)

                logger.info(
                    f"[RATE-LIMITING] Rate limit exceeded for {workflow_key} "
                    f"(type={limit_type}, retry_after={retry_after}s)"
                )

                return False, {
                    "limit_type_hit": limit_type,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "retry_after": retry_after,
                }

            # Track remaining count for this limit type
            rate_limit_info[f"{limit_type}_remaining"] = remaining

            if self.settings.debug_logging:
                logger.debug(
                    f"[RATE-LIMITING] {workflow_key} {limit_type}: "
                    f"{remaining}/{max_requests} remaining"
                )

        return True, rate_limit_info

    def get_rate_limit_status(
        self,
        workflow_name: str,
        client_identifier: str,
        rate_limit_config: Dict[str, int],
    ) -> Dict[str, Dict[str, int]]:
        """
        Get current rate limit status without consuming a request.

        Args:
            workflow_name: Name of the workflow
            client_identifier: Unique identifier for the client
            rate_limit_config: Rate limit configuration

        Returns:
            Dictionary mapping limit_type to status info (remaining, reset_time)
        """
        if not rate_limit_config:
            return {}

        current_time = time.time()
        workflow_key = f"{workflow_name}:{client_identifier}"
        status = {}

        for limit_type, max_requests in rate_limit_config.items():
            window_seconds = self.settings.get_window_seconds(limit_type)

            if window_seconds is None:
                continue

            # Get bucket (creates if doesn't exist, but won't consume a request)
            bucket = self.storage.get_bucket(
                workflow_key, limit_type, max_requests, window_seconds
            )

            remaining = bucket.get_remaining_count(current_time)
            reset_time = int(bucket.get_reset_time(current_time))

            status[limit_type] = {
                "limit": max_requests,
                "remaining": remaining,
                "reset_time": reset_time,
            }

        return status
