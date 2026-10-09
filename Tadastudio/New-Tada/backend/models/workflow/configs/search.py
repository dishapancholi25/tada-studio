"""Search configuration for document and web search nodes.

This module defines configurations for document search and web search
tool nodes in workflows.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import List, Optional


@dataclass
class DocumentSearchConfig:
    """Configuration for document search tool nodes.

    Supports vector search, keyword search, and hybrid search with
    reranking capabilities for knowledge retrieval.

    Attributes:
        document_collections: Collections to search
        document_ids: Specific documents to search
        search_k: Number of documents to retrieve by default
        search_type: Search algorithm (similarity, mmr, similarity_score_threshold)
        similarity_threshold: Minimum similarity score for results
        distance_strategy: Distance metric (cosine, innerProduct, euclidean)
        include_metadata: Include document metadata in results
        citation_format: Citation style (inline, footnote, none, structured)
        hybrid_search_enabled: Enable hybrid vector + keyword search
        search_mode: Search mode (vector, keyword, hybrid)
        keyword_weight: Weight for keyword search (0-1)
        rrf_k: Reciprocal Rank Fusion constant
        full_text_config: PostgreSQL text search config
        min_keyword_relevance: Minimum relevance score for keyword results
        use_reranking: Enable cross-encoder reranking
        rerank_top_k: Number of documents to rerank
        prompt_template: Prompt template style (default, structured, minimal, custom)
        custom_prompt_template: Custom template if prompt_template is 'custom'
        include_confidence_scores: Include confidence scores in results
        max_context_tokens: Maximum tokens for context
        return_full_document: Return all text from document instead of top k chunks
        parent_agent_id: ID of the agent this tool belongs to
    """

    document_collections: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    search_k: int = 3
    search_type: str = "similarity"
    similarity_threshold: float = 0.5
    distance_strategy: str = "cosine"
    include_metadata: bool = True
    citation_format: str = "structured"
    hybrid_search_enabled: bool = True
    search_mode: str = "hybrid"
    keyword_weight: float = 0.5
    rrf_k: int = 60
    full_text_config: str = "english"
    min_keyword_relevance: float = 0.1
    use_reranking: bool = False
    rerank_top_k: int = 10
    prompt_template: str = "structured"
    custom_prompt_template: Optional[str] = None
    include_confidence_scores: bool = True
    max_context_tokens: int = 2000
    return_full_document: bool = False
    parent_agent_id: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None


@dataclass
class WebSearchConfig:
    """Configuration for web search tool nodes.

    Supports multiple search providers including DuckDuckGo and Tavily
    for web search capabilities.

    Attributes:
        search_provider: Search provider (duckduckgo, tavily)
        api_key: API key for provider (required for Tavily)
        max_results: Number of search results to return
        search_depth: Search depth (basic, advanced) for Tavily
        include_answer: Include AI-generated answer (Tavily only)
        include_raw_content: Include raw page content
        include_images: Include image results
        timeout_seconds: Search timeout
        region: Region for search (e.g., wt-wt=no region, us-en=US)
        safe_search: Safe search filter (off, moderate, strict)
        time_range: Time range filter (d=day, w=week, m=month, y=year)
        parent_agent_id: ID of the agent this tool belongs to
    """

    search_provider: str = "duckduckgo"
    api_key: str = ""
    max_results: int = 5
    search_depth: str = "basic"
    include_answer: bool = False
    include_raw_content: bool = False
    include_images: bool = False
    timeout_seconds: int = 10
    region: str = "wt-wt"
    safe_search: str = "moderate"
    time_range: str = ""
    parent_agent_id: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None
