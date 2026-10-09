"""Base provider interface for web search providers."""

from abc import ABC, abstractmethod
from typing import Any


class SearchProvider(ABC):
    """Base class for search providers."""

    @abstractmethod
    def search(self, query: str, **kwargs) -> Any:
        """
        Execute a search query.

        Args:
            query: Search query string
            **kwargs: Provider-specific parameters

        Returns:
            Search results in provider-specific format
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass
