"""Factory functions for creating web search tools.

Simplified factories that delegate complexity to handlers and config modules.
"""

from langchain_core.tools import StructuredTool, tool

from .config import ToolDescriptionBuilder
from .handlers import handle_search_and_summarize, handle_web_search_execution
from .schemas import WebSearchArgs, WebSearchConfig


def create_web_search_tool(
    search_provider: str = "duckduckgo",
    api_key: str = "",
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = False,
    include_raw_content: bool = False,
    include_images: bool = False,
    timeout_seconds: int = 10,
    region: str = "wt-wt",
    safe_search: str = "moderate",
    time_range: str = "",
    node_id: str = "",
    node_name: str = "Web Search",
    tool_name: str = None,
    description_prefix: str = None,
):
    """Create a web search tool with the given configuration.

    Args:
        search_provider: Provider to use (duckduckgo or tavily)
        api_key: API key for Tavily (optional for DuckDuckGo)
        max_results: Maximum number of results to return
        search_depth: Search depth for Tavily (basic or advanced)
        include_answer: Include AI-generated answer (Tavily only)
        include_raw_content: Include raw page content (Tavily only)
        include_images: Include image results
        timeout_seconds: Search timeout
        region: Region for DuckDuckGo search
        safe_search: Safe search setting
        time_range: Time range filter for DuckDuckGo
        node_id: Node ID for tracking
        node_name: Node name for display
        tool_name: Optional custom tool name
        description_prefix: Optional prefix for the tool description

    Returns:
        StructuredTool instance for web search
    """
    # Build configuration
    config = WebSearchConfig(
        search_provider=search_provider,
        api_key=api_key,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=include_answer,
        include_raw_content=include_raw_content,
        include_images=include_images,
        timeout_seconds=timeout_seconds,
        region=region,
        safe_search=safe_search,
        time_range=time_range,
        node_id=node_id,
        node_name=node_name,
        tool_name=tool_name,
    )

    # Build tool description
    tool_description = ToolDescriptionBuilder.build_description(config)
    if description_prefix:
        tool_description = f"{description_prefix}. {tool_description}"

    def search_web_impl(query: str) -> str:
        """Search the web for current information about any topic.

        USE THIS TOOL when you need:
        - Current, up-to-date information
        - Facts about recent events or latest developments
        - Information beyond your knowledge cutoff
        - To verify or update your knowledge

        Example usage: search_web("OpenAI GPT-5 release date 2024")

        Args:
            query: The search query - be specific and include relevant keywords

        Returns:
            Formatted search results with titles, snippets, and URLs
        """
        return handle_web_search_execution(query, config, search_web_impl)

    # Generate tool name
    final_tool_name = tool_name or "search_web"

    # Create and return the tool
    return StructuredTool(
        name=final_tool_name,
        description=tool_description,
        func=search_web_impl,
        args_schema=WebSearchArgs,
    )


def create_web_search_and_summarize_tool(
    search_provider: str = "duckduckgo",
    api_key: str = "",
    max_results: int = 5,
    search_depth: str = "advanced",
    node_id: str = "",
    node_name: str = "Web Search & Summarize",
):
    """Create a web search tool that also summarizes the results.

    This is particularly useful when using Tavily with include_answer=True.

    Args:
        search_provider: Provider to use (duckduckgo or tavily)
        api_key: API key for Tavily
        max_results: Maximum number of results
        search_depth: Search depth for Tavily
        node_id: Node ID for tracking
        node_name: Node name for display

    Returns:
        Tool instance for search and summarize
    """
    # Build configuration
    config = WebSearchConfig(
        search_provider=search_provider,
        api_key=api_key,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=True,  # Always include answer for summarization
        node_id=node_id,
        node_name=node_name,
    )

    @tool
    def search_and_summarize(query: str) -> str:
        """Search the web and provide a summarized answer.

        Args:
            query: The search query or question

        Returns:
            Summarized answer based on search results
        """
        return handle_search_and_summarize(query, config)

    # Set tool metadata
    search_and_summarize.name = (
        f"search_and_summarize_{node_id}" if node_id else "search_and_summarize"
    )
    search_and_summarize.description = (
        "Search the web and provide a summarized answer. "
        "Best for questions that need current information."
    )

    return search_and_summarize
