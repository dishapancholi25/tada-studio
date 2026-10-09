"""Custom exceptions for rate limiting service."""

from typing import Optional


class RateLimitError(Exception):
    """Base exception for rate limiting errors."""

    pass


class RateLimitExceeded(RateLimitError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit_type: str,
        retry_after: int,
        reset_time: int,
        message: Optional[str] = None,
    ):
        """
        Initialize rate limit exceeded exception.

        Args:
            limit_type: Type of limit that was hit (e.g., 'per_minute')
            retry_after: Seconds until the client can retry
            reset_time: Unix timestamp when the limit resets
            message: Optional custom error message
        """
        self.limit_type = limit_type
        self.retry_after = retry_after
        self.reset_time = reset_time

        if message is None:
            message = (
                f"Rate limit exceeded for {limit_type}. "
                f"Retry after {retry_after} seconds."
            )

        super().__init__(message)


class InvalidRateLimitConfig(RateLimitError):
    """Raised when rate limit configuration is invalid."""

    def __init__(self, config_type: str, reason: str):
        """
        Initialize invalid config exception.

        Args:
            config_type: Type of config that's invalid
            reason: Reason why it's invalid
        """
        self.config_type = config_type
        self.reason = reason

        message = f"Invalid rate limit configuration for '{config_type}': {reason}"
        super().__init__(message)


class RateLimitStorageError(RateLimitError):
    """Raised when there's an error with rate limit storage backend."""

    pass
