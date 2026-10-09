"""Tavily search provider (AI-optimized search)."""

import logging
from typing import Any, Dict

from .base import SearchProvider


logger = logging.getLogger(__name__)


class TavilyProvider(SearchProvider):
    """Provider for Tavily API (optimized for LLMs)."""

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "tavily"

    def search(
        self,
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
        try:
            if not api_key:
                return {
                    "error": "Tavily API key is required",
                    "source": self.provider_name,
                }

            # Perform the search with async handling
            response = self._execute_search(
                query=query,
                api_key=api_key,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
                include_images=include_images,
                timeout=timeout,
            )

            # Format results
            formatted_results = self._format_response(
                response, query, search_depth, include_answer, include_raw_content
            )

            logger.info(
                f"Tavily search for '{query}' returned {len(formatted_results.get('results', []))} results"
            )
            return formatted_results

        except ImportError:
            logger.error(
                "tavily-python package not installed. Install with: pip install tavily-python"
            )
            return {
                "error": "Tavily search not available. Please install: pip install tavily-python",
                "source": self.provider_name,
            }
        except Exception as e:
            logger.error(f"Tavily search error: {str(e)}")
            return {"error": f"Search failed: {str(e)}", "source": self.provider_name}

    def _execute_search(
        self,
        query: str,
        api_key: str,
        max_results: int,
        search_depth: str,
        include_answer: bool,
        include_raw_content: bool,
        include_images: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Execute Tavily search with proper async context handling.

        Complexity reduced by extracting async handling logic
        """

        # Try async-aware execution first
        try:
            return self._execute_in_async_context(
                query=query,
                api_key=api_key,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
                include_images=include_images,
                timeout=timeout,
            )
        except RuntimeError:
            # No running loop, use client directly
            return self._execute_sync(
                query=query,
                api_key=api_key,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
                include_images=include_images,
            )

    def _execute_in_async_context(
        self,
        query: str,
        api_key: str,
        max_results: int,
        search_depth: str,
        include_answer: bool,
        include_raw_content: bool,
        include_images: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        """Execute search in async context using thread pool."""
        import asyncio
        import concurrent.futures

        from tavily import TavilyClient

        try:
            asyncio.get_running_loop()
            # We're in an async context, run in a thread to avoid event loop issues

            def run_search():
                thread_client = TavilyClient(api_key=api_key)
                return thread_client.search(
                    query=query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_answer=include_answer,
                    include_raw_content=include_raw_content,
                    include_images=include_images,
                )

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_search)
                return future.result(timeout=timeout)

        except Exception as e:
            # Fallback to direct client usage if thread approach fails
            logger.warning(f"Thread execution failed, using direct client: {e}")
            return self._execute_sync(
                query=query,
                api_key=api_key,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
                include_images=include_images,
            )

    def _execute_sync(
        self,
        query: str,
        api_key: str,
        max_results: int,
        search_depth: str,
        include_answer: bool,
        include_raw_content: bool,
        include_images: bool,
    ) -> Dict[str, Any]:
        """Execute search synchronously."""
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        return client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
        )

    def _format_response(
        self,
        response: Dict[str, Any],
        query: str,
        search_depth: str,
        include_answer: bool,
        include_raw_content: bool,
    ) -> Dict[str, Any]:
        """Format Tavily API response into standardized format."""
        formatted_results = {"results": [], "source": self.provider_name}

        # Add search results
        for idx, result in enumerate(response.get("results", [])):
            formatted_results["results"].append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", ""),
                    "score": result.get("score", 0),
                    "raw_content": result.get("raw_content", "")
                    if include_raw_content
                    else "",
                    "position": idx + 1,
                }
            )

        # Add AI-generated answer if available
        if include_answer and "answer" in response:
            formatted_results["answer"] = response["answer"]

        # Add images if available
        if "images" in response:
            formatted_results["images"] = response["images"]

        # Add query information
        formatted_results["query"] = query
        formatted_results["search_depth"] = search_depth

        return formatted_results
