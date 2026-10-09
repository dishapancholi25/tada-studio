"""
Rate limiting service for published workflows.

This service implements rate limiting based on configuration stored in published workflows.
Supports multiple storage backends (in-memory, Redis) and different rate limiting algorithms.

Usage:
    # Using the global singleton instance
    from backend.services.rate_limiting import rate_limiting_service

    is_allowed, info = rate_limiting_service.check_rate_limit(
        workflow_name="my_workflow",
        client_identifier="ip:1.2.3.4",
        rate_limit_config={"requests_per_minute": 60}
    )

    # Creating a custom instance
    from backend.services.rate_limiting import create_rate_limiting_service

    service = create_rate_limiting_service(debug_logging=True)
"""

from typing import Optional

from .client_identifier import (
    ClientIdentifierStrategy,
    HybridIdentifierStrategy,
    IPOnlyIdentifierStrategy,
    TokenOnlyIdentifierStrategy,
)
from .config import RateLimitConfig, RateLimitSettings
from .exceptions import (
    InvalidRateLimitConfig,
    RateLimitError,
    RateLimitExceeded,
    RateLimitStorageError,
)
from .headers import RateLimitHeaderGenerator
from .service import RateLimitingService
from .storage import InMemoryRateLimitStorage, RateLimitStorage
from .strategies import RateLimitStrategy, SlidingWindowStrategy


# Export public API
__all__ = [
    # Main service
    "RateLimitingService",
    "rate_limiting_service",
    "create_rate_limiting_service",
    # Configuration
    "RateLimitConfig",
    "RateLimitSettings",
    # Exceptions
    "RateLimitError",
    "RateLimitExceeded",
    "InvalidRateLimitConfig",
    "RateLimitStorageError",
    # Storage
    "RateLimitStorage",
    "InMemoryRateLimitStorage",
    # Strategies
    "RateLimitStrategy",
    "SlidingWindowStrategy",
    # Client identification
    "ClientIdentifierStrategy",
    "HybridIdentifierStrategy",
    "TokenOnlyIdentifierStrategy",
    "IPOnlyIdentifierStrategy",
    # Headers
    "RateLimitHeaderGenerator",
]


def create_rate_limiting_service(
    storage: Optional[RateLimitStorage] = None,
    strategy: Optional[RateLimitStrategy] = None,
    client_identifier_strategy: Optional[ClientIdentifierStrategy] = None,
    debug_logging: bool = False,
    max_bucket_age_seconds: int = 3600,
) -> RateLimitingService:
    """
    Create a rate limiting service instance.

    Args:
        storage: Storage backend (defaults to in-memory)
        strategy: Rate limiting strategy (defaults to sliding window)
        client_identifier_strategy: Client ID strategy (defaults to hybrid)
        debug_logging: Enable debug logging for rate limit checks
        max_bucket_age_seconds: Maximum age for unused buckets before cleanup

    Returns:
        Configured RateLimitingService instance

    Example:
        >>> service = create_rate_limiting_service(debug_logging=True)
        >>> is_allowed, info = service.check_rate_limit(
        ...     "workflow", "ip:1.2.3.4", {"per_minute": 10}
        ... )
    """
    settings = RateLimitSettings(
        debug_logging=debug_logging,
        max_bucket_age_seconds=max_bucket_age_seconds,
    )

    return RateLimitingService(
        storage=storage,
        strategy=strategy,
        client_identifier_strategy=client_identifier_strategy,
        settings=settings,
    )


# Global singleton instance for backward compatibility
# This maintains the same usage pattern as the old rate_limiting_service.py
rate_limiting_service = create_rate_limiting_service()
