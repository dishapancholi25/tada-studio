"""
HTTP header generation for rate limiting.

Provides utilities for generating standard rate limit headers
for HTTP responses.
"""

import time
from typing import Dict, Optional

from ...services.config import get_logger
from .config import RateLimitSettings
from .storage import RateLimitStorage


logger = get_logger(__name__)


class RateLimitHeaderGenerator:
    """Generates rate limit HTTP headers for responses."""

    def __init__(
        self,
        storage: RateLimitStorage,
        settings: Optional[RateLimitSettings] = None,
    ):
        """
        Initialize header generator.

        Args:
            storage: Storage backend for rate limit data
            settings: Rate limit settings (uses defaults if not provided)
        """
        self.storage = storage
        self.settings = settings or RateLimitSettings()

    def generate_headers(
        self,
        workflow_name: str,
        client_identifier: str,
        rate_limit_config: Optional[Dict[str, int]],
    ) -> Dict[str, str]:
        """
        Generate rate limit headers for HTTP responses.

        Generates standard rate limit headers in the format:
        - X-RateLimit-{Type}-Limit: Maximum requests allowed
        - X-RateLimit-{Type}-Remaining: Remaining requests
        - X-RateLimit-{Type}-Reset: Unix timestamp when limit resets

        Args:
            workflow_name: Name of the workflow
            client_identifier: Unique identifier for the client
            rate_limit_config: Rate limit configuration

        Returns:
            Dictionary of HTTP headers
        """
        if not rate_limit_config:
            return {}

        headers = {}
        workflow_key = f"{workflow_name}:{client_identifier}"
        current_time = time.time()

        for limit_type, max_requests in rate_limit_config.items():
            window_seconds = self.settings.get_window_seconds(limit_type)

            if window_seconds is None:
                continue

            # Try to get existing bucket (don't create if doesn't exist)
            try:
                bucket = self.storage.get_bucket(
                    workflow_key, limit_type, max_requests, window_seconds
                )

                with bucket.lock:
                    # Clean up expired requests for accurate count
                    cutoff_time = current_time - bucket.window_seconds
                    bucket.requests = [
                        req_time
                        for req_time in bucket.requests
                        if req_time > cutoff_time
                    ]

                    remaining = max(0, bucket.max_requests - len(bucket.requests))
                    reset_time = int(bucket.get_reset_time(current_time))

                    # Generate standard header names
                    # Convert limit_type like "per_minute" to "Per-Minute"
                    limit_name = self._format_limit_name(limit_type)

                    headers[f"X-RateLimit-{limit_name}-Limit"] = str(max_requests)
                    headers[f"X-RateLimit-{limit_name}-Remaining"] = str(remaining)
                    headers[f"X-RateLimit-{limit_name}-Reset"] = str(reset_time)

            except Exception as e:
                logger.warning(
                    f"[RATE-LIMITING] Failed to generate headers for {limit_type}: {e}"
                )
                continue

        return headers

    def _format_limit_name(self, limit_type: str) -> str:
        """
        Format limit type for header names.

        Converts 'per_minute' to 'Per-Minute', 'requests_per_hour' to 'Requests-Per-Hour'

        Args:
            limit_type: The rate limit type

        Returns:
            Formatted name for headers
        """
        return limit_type.replace("_", "-").title()

    def generate_retry_after_headers(
        self, retry_after: int, reset_time: int
    ) -> Dict[str, str]:
        """
        Generate headers for rate limit exceeded responses.

        Args:
            retry_after: Seconds until client can retry
            reset_time: Unix timestamp when limit resets

        Returns:
            Dictionary with Retry-After and X-RateLimit-Reset headers
        """
        return {
            "Retry-After": str(retry_after),
            "X-RateLimit-Reset": str(reset_time),
        }
