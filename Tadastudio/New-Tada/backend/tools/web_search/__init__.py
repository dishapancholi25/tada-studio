"""
Web Search Tool - Modular implementation.

This module provides web search capabilities through multiple providers
(DuckDuckGo and Tavily) with configurable options and automatic fallback.

Main exports:
    - create_web_search_tool: Factory for standard web search tool
    - create_web_search_and_summarize_tool: Factory for search with summarization
"""

from .config import (
    DEFAULT_DUCKDUCKGO_CONFIG,
    DEFAULT_TAVILY_CONFIG,
    ConfigValidator,
    ToolDescriptionBuilder,
)
from .execution import (
    ExecutionStorage,
    attach_execution_metadata,
    get_execution_storage,
    get_function_execution_metadata,
)
from .factory import create_web_search_and_summarize_tool, create_web_search_tool
from .handlers import (
    execute_search,
    format_search_results,
    handle_search_and_summarize,
    handle_web_search_execution,
)
from .schemas import (
    SearchProviderInfo,
    SearchProvidersResponse,
    ValidateConfigRequest,
    ValidateConfigResponse,
    WebSearchArgs,
    WebSearchConfig,
    WebSearchExecutionMetadata,
    WebSearchResponse,
)


__all__ = [
    # Factory functions (primary interface)
    "create_web_search_tool",
    "create_web_search_and_summarize_tool",
    # Schemas
    "WebSearchArgs",
    "WebSearchConfig",
    "WebSearchExecutionMetadata",
    "WebSearchResponse",
    "SearchProviderInfo",
    "SearchProvidersResponse",
    "ValidateConfigRequest",
    "ValidateConfigResponse",
    # Configuration
    "ToolDescriptionBuilder",
    "ConfigValidator",
    "DEFAULT_DUCKDUCKGO_CONFIG",
    "DEFAULT_TAVILY_CONFIG",
    # Handlers (for advanced usage)
    "handle_web_search_execution",
    "handle_search_and_summarize",
    "execute_search",
    "format_search_results",
    # Execution tracking
    "ExecutionStorage",
    "get_execution_storage",
    "attach_execution_metadata",
    "get_function_execution_metadata",
]
