"""Pydantic schemas and data models for document search tool."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentSearchArgs(BaseModel):
    """Input arguments for document search tool."""

    query: str = Field(
        description="The search query to find relevant documents",
        min_length=1,
    )


class DocumentSearchConfig(BaseModel):
    """Configuration for document search tool."""

    # Document selection
    collection_names: List[str] = Field(
        default_factory=list,
        description="List of collection IDs to search",
    )
    document_ids: List[str] = Field(
        default_factory=list,
        description="List of specific document IDs to search",
    )

    # Search parameters
    search_k: int = Field(
        default=6,
        description="Number of results to return",
        ge=1,
        le=50,
    )
    search_type: str = Field(
        default="similarity",
        description="Type of search: similarity, mmr, or similarity_score_threshold",
    )
    similarity_threshold: float = Field(
        default=0.5,
        description="Minimum similarity score for results (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Output formatting
    include_metadata: bool = Field(
        default=True,
        description="Whether to include metadata in results",
    )
    citation_format: str = Field(
        default="structured",
        description="Citation format: structured, inline, footnote, or none",
    )
    prompt_template: str = Field(
        default="structured",
        description="Prompt template to use for formatting",
    )
    include_confidence_scores: bool = Field(
        default=True,
        description="Whether to include confidence scores in output",
    )
    max_context_tokens: int = Field(
        default=2000,
        description="Maximum context tokens (not currently enforced)",
        ge=100,
    )

    # Hybrid search parameters
    hybrid_search_enabled: bool = Field(
        default=True,
        description="Enable hybrid (vector + keyword) search",
    )
    search_mode: str = Field(
        default="hybrid",
        description="Search mode: vector, keyword, or hybrid",
    )
    keyword_weight: float = Field(
        default=0.5,
        description="Weight for keyword search in hybrid mode (0-1)",
        ge=0.0,
        le=1.0,
    )
    rrf_k: int = Field(
        default=60,
        description="Reciprocal Rank Fusion constant (typically 50-60)",
        ge=1,
    )
    text_config: str = Field(
        default="english",
        description="PostgreSQL text search configuration",
    )

    # Full document retrieval
    return_full_document: bool = Field(
        default=False,
        description="Return full document instead of chunks (single document only)",
    )

    # Tool naming
    tool_name: Optional[str] = Field(
        default=None,
        description="Custom tool name (defaults to 'search_documents')",
    )


class SearchResultItem(BaseModel):
    """Individual search result item."""

    content: str = Field(description="Result content/excerpt")
    score: float = Field(description="Relevance score (0.0-1.0)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Result metadata (document name, page, etc.)",
    )


class DocumentSearchResponse(BaseModel):
    """Response model for document search API."""

    success: bool = Field(description="Whether search was successful")
    results: Optional[str] = Field(
        default=None,
        description="Formatted search results",
    )
    raw_results: Optional[List[SearchResultItem]] = Field(
        default=None,
        description="Raw search results (if requested)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if search failed",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (result count, search time, etc.)",
    )


class ValidateConfigRequest(BaseModel):
    """Request to validate a document search configuration."""

    config: DocumentSearchConfig = Field(description="Configuration to validate")


class ValidateConfigResponse(BaseModel):
    """Response from configuration validation."""

    valid: bool = Field(description="Whether configuration is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )


class DocumentSearchExecutionMetadata(BaseModel):
    """Metadata about document search execution."""

    query: str = Field(description="Search query used")
    config: DocumentSearchConfig = Field(description="Configuration used")
    result_count: int = Field(description="Number of results returned")
    search_time_ms: Optional[float] = Field(
        default=None,
        description="Search execution time in milliseconds",
    )
    collections_searched: List[str] = Field(
        default_factory=list,
        description="Collection IDs searched",
    )
    documents_searched: List[str] = Field(
        default_factory=list,
        description="Document IDs searched",
    )
    search_mode_used: str = Field(
        default="similarity",
        description="Actual search mode used",
    )
    embedding_tokens: int = Field(
        default=0,
        description="Tokens used for query embedding",
    )
    embedding_cost: float = Field(
        default=0.0,
        description="Cost of query embedding in USD",
    )
    embedding_model: str = Field(
        default="",
        description="Embedding model used for query vectorization",
    )
