"""Configuration and type definitions for rate limiting service."""

from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, TypedDict


# Type aliases for better readability
RateLimitType = Literal[
    "per_second",
    "per_minute",
    "per_hour",
    "per_day",
    "requests_per_second",
    "requests_per_minute",
    "requests_per_hour",
    "requests_per_day",
]


class RateLimitConfig(TypedDict, total=False):
    """Type definition for rate limit configuration dictionary.

    Examples:
        {"requests_per_minute": 60, "requests_per_hour": 1000}
        {"per_second": 10, "per_day": 10000}
    """

    per_second: int
    per_minute: int
    per_hour: int
    per_day: int
    requests_per_second: int
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int


class RateLimitResult(TypedDict, total=False):
    """Type definition for rate limit check result."""

    is_allowed: bool
    remaining: int
    limit_type_hit: str
    reset_time: int
    retry_after: int
    message: str


class RateLimitHeaders(TypedDict, total=False):
    """Type definition for rate limit HTTP headers."""

    # Standard rate limit headers (per limit type)
    # Example: X-RateLimit-Per-Minute-Limit, X-RateLimit-Per-Minute-Remaining


@dataclass
class RateLimitSettings:
    """Configuration settings for rate limiting service."""

    # Maximum age (in seconds) for unused rate limit buckets before cleanup
    max_bucket_age_seconds: int = 3600

    # Enable debug logging for rate limit checks
    debug_logging: bool = False

    # Time window mappings (in seconds)
    time_windows: Dict[str, int] = field(
        default_factory=lambda: {
            "per_second": 1,
            "requests_per_second": 1,
            "per_minute": 60,
            "requests_per_minute": 60,
            "per_hour": 3600,
            "requests_per_hour": 3600,
            "per_day": 86400,
            "requests_per_day": 86400,
        }
    )

    def get_window_seconds(self, limit_type: str) -> Optional[int]:
        """
        Get the time window in seconds for a given limit type.

        Args:
            limit_type: The rate limit type (e.g., 'per_minute', 'requests_per_hour')

        Returns:
            Window duration in seconds, or None if not recognized
        """
        limit_type_lower = limit_type.lower()

        # Check predefined windows
        if limit_type_lower in self.time_windows:
            return self.time_windows[limit_type_lower]

        # Try to extract custom window from format like "per_300" (300 seconds)
        if limit_type_lower.startswith("per_"):
            try:
                return int(limit_type_lower[4:])
            except ValueError:
                pass

        return None

    def validate_rate_limit_config(self, config: Dict[str, int]) -> bool:
        """
        Validate a rate limit configuration dictionary.

        Args:
            config: Rate limit configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not config:
            raise ValueError("Rate limit config cannot be empty")

        for limit_type, max_requests in config.items():
            # Validate that we can parse the limit type
            window_seconds = self.get_window_seconds(limit_type)
            if window_seconds is None:
                raise ValueError(f"Unknown rate limit type: {limit_type}")

            # Validate that max_requests is positive
            if not isinstance(max_requests, int) or max_requests <= 0:
                raise ValueError(
                    f"Rate limit max_requests must be a positive integer, "
                    f"got {max_requests} for {limit_type}"
                )

        return True


# Default settings instance
DEFAULT_SETTINGS = RateLimitSettings()
