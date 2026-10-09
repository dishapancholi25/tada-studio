"""DuckDuckGo search provider."""

import logging
from typing import Any, Dict, List

from .base import SearchProvider


logger = logging.getLogger(__name__)


class DuckDuckGoProvider(SearchProvider):
    """Provider for DuckDuckGo search (no API key required)."""

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "duckduckgo"

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
        safe_search: str = "moderate",
        time_range: str = "",
        timeout: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search using DuckDuckGo (no API key required).

        Args:
            query: Search query
            max_results: Maximum number of results to return
            region: Region code (wt-wt=no region, us-en=US, uk-en=UK, etc.)
            safe_search: Safe search setting (off, moderate, strict)
            time_range: Time range filter (d=day, w=week, m=month, y=year)
            timeout: Request timeout in seconds

        Returns:
            List of search results
        """
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                logger.info(
                    f"DuckDuckGo text search with region: {region} for query: '{query}'"
                )

                # Prepare search parameters
                search_params = {
                    "keywords": query,
                    "max_results": max_results,
                    "region": region,
                    "safesearch": safe_search,
                }

                # Add time range if specified
                if time_range:
                    search_params["timelimit"] = time_range

                # Perform search
                results = list(ddgs.text(**search_params))

                # Format results
                formatted_results = self._format_text_results(results, max_results)

                logger.info(
                    f"DuckDuckGo search for '{query}' returned {len(formatted_results)} results"
                )
                return formatted_results

        except ImportError:
            logger.error(
                "duckduckgo-search package not installed. Install with: pip install duckduckgo-search"
            )
            return [
                {
                    "error": "DuckDuckGo search not available. Please install: pip install duckduckgo-search",
                    "source": self.provider_name,
                }
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return [{"error": f"Search failed: {str(e)}", "source": self.provider_name}]

    def search_images(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
        safe_search: str = "moderate",
        size: str = "",
        timeout: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for images using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code
            safe_search: Safe search setting
            size: Size filter (Small, Medium, Large, Wallpaper)
            timeout: Request timeout

        Returns:
            List of image results
        """
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                # Prepare search parameters
                search_params = {
                    "keywords": query,
                    "max_results": max_results,
                    "region": region,
                    "safesearch": safe_search,
                }

                if size:
                    search_params["size"] = size

                # Perform image search
                results = list(ddgs.images(**search_params))

                # Format results
                formatted_results = self._format_image_results(results, max_results)

                logger.info(
                    f"DuckDuckGo image search for '{query}' returned {len(formatted_results)} results"
                )
                return formatted_results

        except ImportError:
            logger.error("duckduckgo-search package not installed")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo image search error: {str(e)}")
            return []

    def _format_text_results(
        self, results: List[Dict], max_results: int
    ) -> List[Dict[str, Any]]:
        """Format text search results into standardized format."""
        formatted_results = []
        for idx, result in enumerate(results[:max_results]):
            formatted_results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "position": idx + 1,
                    "source": self.provider_name,
                }
            )
        return formatted_results

    def _format_image_results(
        self, results: List[Dict], max_results: int
    ) -> List[Dict[str, Any]]:
        """Format image search results into standardized format."""
        formatted_results = []
        for idx, result in enumerate(results[:max_results]):
            formatted_results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "image_url": result.get("image", ""),
                    "thumbnail": result.get("thumbnail", ""),
                    "source": result.get("source", ""),
                    "width": result.get("width", 0),
                    "height": result.get("height", 0),
                    "position": idx + 1,
                    "type": "image",
                }
            )
        return formatted_results
