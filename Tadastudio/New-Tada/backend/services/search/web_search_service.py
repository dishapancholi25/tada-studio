"""
Service for executing web searches using various providers.

Refactored into modular architecture with provider and formatter patterns.
"""

import logging
from typing import Any, Dict, List

from .formatters import MarkdownFormatter, TextFormatter
from .providers import DuckDuckGoProvider, TavilyProvider


logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for executing web searches with multiple provider support.

    Acts as an orchestrator that delegates to specialized providers and formatters.
    """

    def __init__(self):
        """Initialize web search service with providers and formatters."""
        self.duckduckgo_provider = DuckDuckGoProvider()
        self.tavily_provider = TavilyProvider()
        self.text_formatter = TextFormatter()
        self.markdown_formatter = MarkdownFormatter()

    @staticmethod
    def search_duckduckgo(
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
        provider = DuckDuckGoProvider()
        return provider.search(
            query=query,
            max_results=max_results,
            region=region,
            safe_search=safe_search,
            time_range=time_range,
            timeout=timeout,
        )

    @staticmethod
    def search_duckduckgo_images(
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
        provider = DuckDuckGoProvider()
        return provider.search_images(
            query=query,
            max_results=max_results,
            region=region,
            safe_search=safe_search,
            size=size,
            timeout=timeout,
        )

    @staticmethod
    def search_tavily(
        query: str,
        api_key: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        Search using Tavily API (optimized for LLMs).

        Args:
            query: Search query
            api_key: Tavily API key
            max_results: Maximum number of results
            search_depth: Search depth (basic or advanced)
            include_answer: Include AI-generated answer
            include_raw_content: Include raw page content
            include_images: Include image results
            timeout: Request timeout

        Returns:
            Dictionary with search results and optional answer
        """
        provider = TavilyProvider()
        return provider.search(
            query=query,
            api_key=api_key,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            timeout=timeout,
        )

    @staticmethod
    def format_results_as_text(
        results: Any,
        include_urls: bool = True,
        include_snippets: bool = True,
        max_snippet_length: int = 200,
    ) -> str:
        """
        Format search results as readable text.

        Args:
            results: Search results (list or dict)
            include_urls: Include URLs in output
            include_snippets: Include snippets in output
            max_snippet_length: Maximum snippet length

        Returns:
            Formatted text string
        """
        formatter = TextFormatter()
        return formatter.format(
            results=results,
            include_urls=include_urls,
            include_snippets=include_snippets,
            max_snippet_length=max_snippet_length,
        )

    @staticmethod
    def format_results_as_markdown(
        results: Any, include_urls: bool = True, include_snippets: bool = True
    ) -> str:
        """
        Format search results as Markdown.

        Args:
            results: Search results
            include_urls: Include URLs in output
            include_snippets: Include snippets in output

        Returns:
            Markdown formatted string
        """
        formatter = MarkdownFormatter()
        return formatter.format(
            results=results,
            include_urls=include_urls,
            include_snippets=include_snippets,
        )


# Create a singleton instance for backward compatibility
web_search_service = WebSearchService()
