"""
Client identification strategies for rate limiting.

Provides different strategies for generating unique identifiers
for rate limiting purposes (IP-based, token-based, hybrid).
"""

from abc import ABC, abstractmethod
from typing import Optional

from ...services.config import get_logger


logger = get_logger(__name__)


class ClientIdentifierStrategy(ABC):
    """Abstract base class for client identification strategies."""

    @abstractmethod
    def get_identifier(self, client_ip: Optional[str], token: Optional[str]) -> str:
        """
        Generate a unique identifier for rate limiting.

        Args:
            client_ip: Client IP address
            token: Authentication token (if any)

        Returns:
            Unique identifier string
        """
        pass


class HybridIdentifierStrategy(ClientIdentifierStrategy):
    """
    Hybrid client identification strategy.

    Prefers token-based identification for authenticated requests,
    falls back to IP-based for unauthenticated requests.
    """

    def get_identifier(self, client_ip: Optional[str], token: Optional[str]) -> str:
        """
        Generate a unique identifier preferring token over IP.

        Priority:
        1. Token (for authenticated requests)
        2. IP address (for unauthenticated requests)
        3. Default fallback (if neither available)

        Args:
            client_ip: Client IP address
            token: Authentication token (if any)

        Returns:
            Unique identifier string in format 'type:value'
        """
        if token:
            # Use token as primary identifier for authenticated requests
            # This allows per-user rate limiting
            return f"token:{token}"
        elif client_ip:
            # Fall back to IP for unauthenticated requests
            # This provides basic per-IP rate limiting
            return f"ip:{client_ip}"
        else:
            # Last resort - use a default identifier
            # This will rate limit all unidentified clients together
            logger.warning(
                "[RATE-LIMITING] No client identifier available, using default"
            )
            return "unknown:client"


class TokenOnlyIdentifierStrategy(ClientIdentifierStrategy):
    """
    Token-only identification strategy.

    Requires authentication token for rate limiting.
    Useful for APIs that require authentication.
    """

    def get_identifier(self, client_ip: Optional[str], token: Optional[str]) -> str:
        """
        Generate identifier based only on token.

        Args:
            client_ip: Client IP address (ignored)
            token: Authentication token

        Returns:
            Token-based identifier or default if no token

        Raises:
            ValueError: If no token provided
        """
        if not token:
            raise ValueError("Token required for rate limiting")

        return f"token:{token}"


class IPOnlyIdentifierStrategy(ClientIdentifierStrategy):
    """
    IP-only identification strategy.

    Uses client IP address for rate limiting.
    Useful for public APIs without authentication.
    """

    def get_identifier(self, client_ip: Optional[str], token: Optional[str]) -> str:
        """
        Generate identifier based only on IP.

        Args:
            client_ip: Client IP address
            token: Authentication token (ignored)

        Returns:
            IP-based identifier or default if no IP

        Raises:
            ValueError: If no IP provided
        """
        if not client_ip:
            raise ValueError("Client IP required for rate limiting")

        return f"ip:{client_ip}"
