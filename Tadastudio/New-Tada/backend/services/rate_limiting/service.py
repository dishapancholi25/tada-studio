"""
Main rate limiting service orchestrator.

Coordinates between storage, strategies, client identification,
and header generation to provide a unified rate limiting API.
"""

import time
from typing import Dict, Optional, Tuple

from ...services.config import get_logger
from .client_identifier import ClientIdentifierStrategy, HybridIdentifierStrategy
from .config import RateLimitSettings
from .headers import RateLimitHeaderGenerator
from .storage import InMemoryRateLimitStorage, RateLimitStorage
from .strategies import RateLimitStrategy, SlidingWindowStrategy


logger = get_logger(__name__)


class RateLimitingService:
    """
    Main service for enforcing rate limits on workflows.

    Orchestrates storage, strategy, client identification, and header generation
    to provide a complete rate limiting solution.
    """

    def __init__(
        self,
        storage: Optional[RateLimitStorage] = None,
        strategy: Optional[RateLimitStrategy] = None,
        client_identifier_strategy: Optional[ClientIdentifierStrategy] = None,
        settings: Optional[RateLimitSettings] = None,
    ):
        """
        Initialize rate limiting service.

        Args:
            storage: Storage backend (defaults to in-memory)
            strategy: Rate limiting strategy (defaults to sliding window)
            client_identifier_strategy: Client ID strategy (defaults to hybrid)
            settings: Rate limit settings (uses defaults if not provided)
        """
        self.settings = settings or RateLimitSettings()
        self.storage = storage or InMemoryRateLimitStorage()
        self.strategy = strategy or SlidingWindowStrategy(self.storage, self.settings)
        self.client_identifier_strategy = (
            client_identifier_strategy or HybridIdentifierStrategy()
        )
        self.header_generator = RateLimitHeaderGenerator(self.storage, self.settings)

        logger.info("[RATE-LIMITING] Service initialized successfully")

    def check_rate_limit(
        self,
        workflow_name: str,
        client_identifier: str,
        rate_limit_config: Optional[Dict[str, int]],
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limits.

        Args:
            workflow_name: Name of the workflow
            client_identifier: Unique identifier for the client (IP, token, etc.)
            rate_limit_config: Rate limit configuration from published workflow
                Example: {"requests_per_minute": 60, "requests_per_hour": 1000}

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            - is_allowed: True if request should be allowed, False if rate limited
            - rate_limit_info: Dictionary with details:
                - If allowed: Contains remaining counts (e.g., 'per_minute_remaining')
                - If denied: Contains 'limit_type_hit', 'remaining', 'reset_time', 'retry_after'

        Example:
            >>> service.check_rate_limit("my_workflow", "ip:1.2.3.4", {"per_minute": 10})
            (True, {"per_minute_remaining": 9})

            >>> # After limit exceeded:
            (False, {
                "limit_type_hit": "per_minute",
                "remaining": 0,
                "reset_time": 1234567890,
                "retry_after": 45
            })
        """
        return self.strategy.check_limit(
            workflow_name, client_identifier, rate_limit_config
        )

    def get_rate_limit_headers(
        self,
        workflow_name: str,
        client_identifier: str,
        rate_limit_config: Optional[Dict[str, int]],
    ) -> Dict[str, str]:
        """
        Get rate limit headers for HTTP responses.

        Args:
            workflow_name: Name of the workflow
            client_identifier: Unique identifier for the client
            rate_limit_config: Rate limit configuration

        Returns:
            Dictionary of HTTP headers in the format:
            {
                "X-RateLimit-Per-Minute-Limit": "60",
                "X-RateLimit-Per-Minute-Remaining": "59",
                "X-RateLimit-Per-Minute-Reset": "1234567890"
            }
        """
        return self.header_generator.generate_headers(
            workflow_name, client_identifier, rate_limit_config
        )

    def get_client_identifier(
        self, client_ip: Optional[str], token: Optional[str]
    ) -> str:
        """
        Generate a unique identifier for rate limiting.

        Uses the configured client identifier strategy to generate
        a unique identifier from available client information.

        Args:
            client_ip: Client IP address
            token: Authentication token (if any)

        Returns:
            Unique identifier string (e.g., 'token:abc123' or 'ip:1.2.3.4')
        """
        return self.client_identifier_strategy.get_identifier(client_ip, token)

    def cleanup_expired_buckets(self, max_age_seconds: Optional[int] = None):
        """
        Clean up expired rate limit buckets to prevent memory leaks.

        This should be called periodically (e.g., via background task)
        to remove old, unused rate limit buckets from memory.

        Args:
            max_age_seconds: Maximum age of unused buckets in seconds
                (uses setting default if not provided)
        """
        if max_age_seconds is None:
            max_age_seconds = self.settings.max_bucket_age_seconds

        current_time = time.time()
        cleaned = self.storage.cleanup_expired(current_time, max_age_seconds)

        if cleaned > 0:
            logger.info(f"[RATE-LIMITING] Cleaned up {cleaned} expired buckets")

    def get_storage_stats(self) -> Dict[str, int]:
        """
        Get statistics about the rate limiting storage.

        Returns:
            Dictionary with storage statistics (implementation-dependent)
        """
        if hasattr(self.storage, "get_stats"):
            return self.storage.get_stats()
        return {}

    def validate_config(self, rate_limit_config: Dict[str, int]) -> bool:
        """
        Validate a rate limit configuration.

        Args:
            rate_limit_config: Rate limit configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        return self.settings.validate_rate_limit_config(rate_limit_config)
