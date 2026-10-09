"""Pydantic schemas for web search tool."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class WebSearchArgs(BaseModel):
    """Arguments for web search tool execution."""

    query: str = Field(
        description="The search query - be specific and include relevant keywords"
    )


class WebSearchConfig(BaseModel):
    """Configuration for web search tool."""

    search_provider: str = Field(
        default="duckduckgo",
        description="Provider to use (duckduckgo or tavily)",
    )
    api_key: str = Field(default="", description="API key for Tavily")
    max_results: int = Field(
        default=5, ge=1, le=20, description="Maximum number of results to return"
    )
    search_depth: str = Field(
        default="basic", description="Search depth for Tavily (basic or advanced)"
    )
    include_answer: bool = Field(
        default=False, description="Include AI-generated answer (Tavily only)"
    )
    include_raw_content: bool = Field(
        default=False, description="Include raw page content (Tavily only)"
    )
    include_images: bool = Field(default=False, description="Include image results")
    timeout_seconds: int = Field(
        default=10, ge=1, le=60, description="Search timeout in seconds"
    )
    region: str = Field(default="wt-wt", description="Region for DuckDuckGo search")
    safe_search: str = Field(
        default="moderate", description="Safe search setting (off, moderate, strict)"
    )
    time_range: str = Field(
        default="", description="Time range filter for DuckDuckGo (d, w, m, y)"
    )
    node_id: str = Field(default="", description="Node ID for tracking")
    node_name: str = Field(default="Web Search", description="Node name for display")
    tool_name: Optional[str] = Field(
        None, description="Custom tool name (defaults to search_web)"
    )


class WebSearchExecutionMetadata(BaseModel):
    """Metadata captured during web search execution."""

    query: str
    provider: str
    raw_results: Any
    formatted_results: str
    max_results: int


class WebSearchResponse(BaseModel):
    """Response from web search API."""

    success: bool
    results: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[WebSearchExecutionMetadata] = None


class SearchProviderInfo(BaseModel):
    """Information about a search provider."""

    name: str
    requires_api_key: bool
    features: List[str]
    description: str


class SearchProvidersResponse(BaseModel):
    """Response listing available search providers."""

    providers: List[SearchProviderInfo]


class ValidateConfigRequest(BaseModel):
    """Request to validate search configuration."""

    config: WebSearchConfig


class ValidateConfigResponse(BaseModel):
    """Response from configuration validation."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
