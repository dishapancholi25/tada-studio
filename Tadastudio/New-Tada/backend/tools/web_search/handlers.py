"""Business logic handlers for web search operations.

This module breaks down complex search logic into focused, testable functions
to reduce cyclomatic complexity and improve maintainability.
"""

import logging
from typing import Any, Dict, List, Union

from ...services.search import web_search_service
from ...services.streaming import streaming_emitter
from .execution import attach_execution_metadata
from .schemas import WebSearchConfig, WebSearchExecutionMetadata


logger = logging.getLogger(__name__)

# Tool name constant for streaming events
WEB_SEARCH_TOOL_NAME = "web_search"


def handle_tavily_search(
    query: str, config: WebSearchConfig
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Execute a Tavily search with the given configuration.

    Args:
        query: Search query string
        config: Search configuration

    Returns:
        Search results from Tavily API
    """
    logger.info(f"[WebSearch] Searching with Tavily: '{query}'")

    results = web_search_service.search_tavily(
        query=query,
        api_key=config.api_key,
        max_results=config.max_results,
        search_depth=config.search_depth,
        include_answer=config.include_answer,
        include_raw_content=config.include_raw_content,
        include_images=config.include_images,
        timeout=config.timeout_seconds,
    )

    return results


def handle_duckduckgo_search(
    query: str, config: WebSearchConfig
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Execute a DuckDuckGo search with the given configuration.

    Args:
        query: Search query string
        config: Search configuration

    Returns:
        Search results from DuckDuckGo
    """
    logger.info(f"[WebSearch] Searching with DuckDuckGo: '{query}'")

    results = web_search_service.search_duckduckgo(
        query=query,
        max_results=config.max_results,
        region=config.region,
        safe_search=config.safe_search,
        time_range=config.time_range,
        timeout=config.timeout_seconds,
    )

    # Add images if requested
    if config.include_images:
        image_results = web_search_service.search_duckduckgo_images(
            query=query,
            max_results=3,
            region=config.region,
            safe_search=config.safe_search,
            timeout=config.timeout_seconds,
        )
        if image_results:
            results = {"results": results, "images": image_results}

    return results


def handle_tavily_with_fallback(
    query: str, config: WebSearchConfig
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Execute Tavily search with automatic fallback to DuckDuckGo on error.

    Args:
        query: Search query string
        config: Search configuration

    Returns:
        Search results from Tavily or DuckDuckGo (fallback)
    """
    results = handle_tavily_search(query, config)

    # Check for errors
    if isinstance(results, dict) and "error" in results:
        error_msg = results["error"]
        logger.error(f"[WebSearch] Tavily error: {error_msg}")

        # Fallback to DuckDuckGo if not an API key error
        if "API key" not in error_msg:
            logger.info("[WebSearch] Falling back to DuckDuckGo")
            results = handle_duckduckgo_search(query, config)
        else:
            raise ValueError(f"{error_msg}. Please configure a valid Tavily API key.")

    return results


def execute_search(
    query: str, config: WebSearchConfig
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Execute search based on provider configuration.

    Args:
        query: Search query string
        config: Search configuration

    Returns:
        Search results from the configured provider
    """
    if config.search_provider == "tavily":
        return handle_tavily_with_fallback(query, config)
    else:
        return handle_duckduckgo_search(query, config)


def determine_actual_provider(
    results: Union[Dict[str, Any], List[Dict[str, Any]]], default_provider: str
) -> str:
    """Determine which provider was actually used based on results.

    Args:
        results: Search results
        default_provider: Default provider name

    Returns:
        Actual provider name used
    """
    # Check the source field in results
    if isinstance(results, dict) and "source" in results:
        return results.get("source", default_provider)
    elif isinstance(results, list) and len(results) > 0:
        if isinstance(results[0], dict) and results[0].get("source"):
            return results[0].get("source")

    return default_provider


def format_search_results(results: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
    """Format search results as readable text.

    Args:
        results: Raw search results

    Returns:
        Formatted text string
    """
    formatted = web_search_service.format_results_as_text(
        results,
        include_urls=True,
        include_snippets=True,
        max_snippet_length=200,
    )

    if not formatted or formatted.strip() == "":
        return ""

    return formatted


def create_execution_metadata(
    query: str,
    provider: str,
    results: Union[Dict[str, Any], List[Dict[str, Any]]],
    formatted_results: str,
    max_results: int,
) -> WebSearchExecutionMetadata:
    """Create execution metadata object.

    Args:
        query: Search query
        provider: Provider used
        results: Raw results
        formatted_results: Formatted results string
        max_results: Maximum results requested

    Returns:
        Execution metadata object
    """
    return WebSearchExecutionMetadata(
        query=query,
        provider=provider,
        raw_results=results,
        formatted_results=formatted_results,
        max_results=max_results,
    )


def handle_web_search_execution(
    query: str,
    config: WebSearchConfig,
    search_impl_func: Any,
    call_id: str = "",
) -> str:
    """Handle web search execution with metadata tracking.

    Args:
        query: Search query
        config: Search configuration
        search_impl_func: The function to attach metadata to (for backward compat)
        call_id: Optional call ID for streaming progress events

    Returns:
        Formatted search results string

    Raises:
        ValueError: If search fails with invalid configuration
        Exception: If unexpected error occurs during search
    """
    try:
        # Emit progress: starting search
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=WEB_SEARCH_TOOL_NAME,
            message=f"Searching with {config.search_provider}...",
            progress=20,
        )

        # Execute search
        results = execute_search(query, config)

        # Determine actual provider
        actual_provider = determine_actual_provider(results, config.search_provider)

        # Log provider info
        if actual_provider != config.search_provider:
            logger.info(
                f"[WebSearch] Fell back from {config.search_provider} to {actual_provider}"
            )

        # Emit progress: processing results
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=WEB_SEARCH_TOOL_NAME,
            message="Processing results...",
            progress=70,
        )

        # Format results
        formatted_results = format_search_results(results)

        if not formatted_results:
            return f"No results found for query: {query}"

        # Emit progress: formatting results
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=WEB_SEARCH_TOOL_NAME,
            message="Formatting results...",
            progress=90,
        )

        # Create and attach metadata
        metadata = create_execution_metadata(
            query=query,
            provider=actual_provider,
            results=results,
            formatted_results=formatted_results,
            max_results=config.max_results,
        )
        attach_execution_metadata(search_impl_func, metadata)

        logger.info(
            f"[WebSearch] Successfully searched for '{query}' using {actual_provider}"
        )

        return formatted_results

    except Exception as e:
        logger.error(f"[WebSearch] Error searching web: {str(e)}")
        raise


def build_summary_from_results(
    query: str, results: Union[Dict[str, Any], List[Dict[str, Any]]]
) -> str:
    """Build a summary from search results.

    Args:
        query: Search query
        results: Search results

    Returns:
        Summary text
    """
    # Extract result list
    if isinstance(results, dict):
        result_list = results.get("results", [])
    else:
        result_list = results if isinstance(results, list) else []

    if not result_list:
        return f"No results found for: {query}"

    # Build summary
    summary_parts = [f"Based on web search results for '{query}':\n"]

    for i, result in enumerate(result_list[:3], 1):
        if "error" in result:
            continue

        snippet = result.get("snippet", "")
        url = result.get("url", "")

        if snippet:
            summary_parts.append(f"{i}. {snippet[:150]}...")
            if url:
                summary_parts.append(f"   Source: {url}")
            summary_parts.append("")

    return "\n".join(summary_parts)


def handle_search_and_summarize(query: str, config: WebSearchConfig) -> str:
    """Handle search with summarization.

    Args:
        query: Search query
        config: Search configuration

    Returns:
        Summarized search results

    Raises:
        Exception: If search fails
    """
    try:
        logger.info(f"[WebSearchSummarize] Searching and summarizing: '{query}'")

        # Try Tavily with AI answer if configured
        if config.search_provider == "tavily" and config.api_key:
            results = handle_tavily_search(query, config)

            # Check for errors
            if isinstance(results, dict) and "error" in results:
                return f"Search error: {results['error']}"

            # Return AI answer if available
            if isinstance(results, dict) and "answer" in results:
                answer = results["answer"]

                # Add source citations
                if "results" in results and results["results"]:
                    sources = [r["url"] for r in results["results"][:3] if "url" in r]

                    if sources:
                        answer += "\n\nSources:\n" + "\n".join(
                            f"- {url}" for url in sources
                        )

                return answer

        # Fallback to regular search with formatted results
        results = execute_search(query, config)

        # Build summary
        return build_summary_from_results(query, results)

    except Exception as e:
        logger.error(f"[WebSearchSummarize] Error: {str(e)}")
        raise
