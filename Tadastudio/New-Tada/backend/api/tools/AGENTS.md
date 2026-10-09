# Tools API Module

## Overview

The Tools API module provides REST endpoints for executing web searches and document searches without requiring workflow
integration. These endpoints allow direct access to AgenticStudio's search capabilities for testing, debugging, or
integration with external systems.

**Location:** [backend/api/tools/](../../backend/api/tools/)

**Base Paths:**

- `/api/tools/web-search` - Web search endpoints
- `/api/tools/document-search` - Document search endpoints

**Primary Responsibilities:**

- Execute web searches via DuckDuckGo or Tavily providers
- Search document collections using vector similarity or hybrid search
- Validate search configurations before execution
- Provide information about available search providers and capabilities
- Health monitoring for search services

## Architecture

### Module Structure

```
backend/api/tools/
├── __init__.py              # Module exports (web_search_router, document_search_router)
├── web_search.py            # Web search REST API endpoints (178 lines)
└── document_search.py       # Document search REST API endpoints (155 lines)

backend/tools/              # Underlying tool implementations
├── web_search/
│   ├── __init__.py         # Exports for web search tool
│   ├── schemas.py          # Pydantic models for requests/responses
│   ├── config.py           # Configuration validation and defaults
│   ├── handlers.py         # Search execution and result formatting
│   ├── execution.py        # Execution metadata tracking
│   └── factory.py          # Tool factory functions
└── document_search/
    ├── __init__.py         # Exports for document search tool
    ├── schemas.py          # Pydantic models for requests/responses
    ├── config/             # Configuration management
    │   ├── builders.py     # Description builders
    │   ├── validators.py   # Configuration validators
    │   ├── validation_rules.py # Validation rule implementations
    │   └── defaults.py     # Default configurations
    ├── handlers.py         # Search execution handlers
    ├── execution.py        # Execution metadata tracking
    ├── formatters/         # Result formatting
    │   ├── structured_formatter.py  # Structured output
    │   ├── inline_formatter.py      # Inline citations
    │   ├── footnote_formatter.py    # Footnote citations
    │   ├── plain_formatter.py       # Plain text output
    │   └── full_document_formatter.py # Full document retrieval
    └── factory.py          # Tool factory functions
```

### Design Pattern

The Tools API follows a **simple delegation pattern**:

```
HTTP Request
    ↓
Route Handler (web_search.py / document_search.py)
    ↓
Validation (ConfigValidator)
    ↓
Execution Handler (backend/tools/*/handlers.py)
    ↓
Search Provider (DuckDuckGo / Tavily / Vector DB)
    ↓
Result Formatting
    ↓
HTTP Response
```

**Benefits:**

- Thin API layer focuses purely on HTTP concerns
- Reuses same tool implementations as workflow nodes
- Consistent behaviour between API and workflow execution
- Easy to test search logic independently
- Simple to add new search providers

## Authentication & Authorisation

### Authentication

**All endpoints in this module are public and do not require authentication.**

This design choice allows:

- Easy testing and debugging of search capabilities
- Integration with external systems without OAuth setup
- Quick API exploration and development

**Security Note:** In production deployments, consider:

- Rate limiting these endpoints to prevent abuse
- Adding API key authentication for external integrations
- Monitoring usage patterns for anomalous activity

### Authorisation

**Document Search Scoping:**

While the web search endpoints are completely public, document search operates on user-specific document collections.
When using document search via this API:

- **Collection Access:** Only documents the user has access to are searchable
- **Document IDs:** Must provide valid collection names or document IDs
- **No Cross-User Access:** Cannot search other users' private documents

**Implementation Note:**

Currently, these endpoints do not extract user context from authentication headers. For user-scoped document searches in
production, integrate with `get_current_user` dependency:

```python
from ...auth.dependencies import get_current_user

@router.post("/search")
async def search_documents(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Filter collections by user_id
    user_collections = get_user_collections(current_user["id"])
    # ... execute search
```

## API Endpoints

### Web Search Endpoints

#### `POST /api/tools/web-search/search`

Execute a web search using DuckDuckGo or Tavily search providers.

**Authentication:** None

**Request Body:**

```json
{
  "query": "latest developments in quantum computing 2025",
  "config": {
    "search_provider": "duckduckgo",
    "max_results": 5,
    "region": "wt-wt",
    "safe_search": "moderate",
    "time_range": "m",
    "timeout_seconds": 10
  }
}
```

**Request Fields:**

- `query` (required, string, min_length=1) - The search query
- `config` (optional, object) - Search configuration (uses defaults if omitted)
  - `search_provider` (string, default: "duckduckgo") - Provider: "duckduckgo" or "tavily"
  - `api_key` (string, default: "") - API key for Tavily (required for Tavily provider)
  - `max_results` (integer, 1-20, default: 5) - Maximum number of results
  - `search_depth` (string, default: "basic") - Tavily only: "basic" or "advanced"
  - `include_answer` (boolean, default: false) - Tavily only: Include AI-generated answer
  - `include_raw_content` (boolean, default: false) - Tavily only: Include raw page content
  - `include_images` (boolean, default: false) - Include image results
  - `timeout_seconds` (integer, 1-60, default: 10) - Search timeout
  - `region` (string, default: "wt-wt") - DuckDuckGo only: Region code (e.g., "us-en", "uk-en")
  - `safe_search` (string, default: "moderate") - DuckDuckGo only: "off", "moderate", or "strict"
  - `time_range` (string, default: "") - DuckDuckGo only: "d" (day), "w" (week), "m" (month), "y" (year), or ""
  - `node_id` (string, default: "") - Optional node ID for execution tracking
  - `node_name` (string, default: "Web Search") - Display name for tracking

**Response (Success):**

```json
{
  "success": true,
  "results": "# Search Results for: latest developments in quantum computing 2025\n\n## Result 1\n**Title:** Quantum Computing Breakthrough 2025 - IBM Achieves 1000 Qubit Processor\n**URL:** https://example.com/quantum-breakthrough\n**Snippet:** IBM announced a major breakthrough in quantum computing with their new 1000-qubit processor, representing a significant leap in computational power...\n\n## Result 2\n**Title:** Google's Quantum AI Makes Progress on Error Correction\n**URL:** https://example.com/google-quantum\n**Snippet:** Google's Quantum AI division has demonstrated significant improvements in quantum error correction, bringing practical quantum computers closer to reality...\n\n[... more results ...]",
  "error": null,
  "metadata": null
}
```

**Response (No Results):**

```json
{
  "success": true,
  "results": "No results found for query: nonexistent search query xyz123",
  "error": null
}
```

**Response (Failure):**

```json
{
  "success": false,
  "results": null,
  "error": "Search failed: Connection timeout after 10 seconds"
}
```

**Use Cases:**

- Testing search configurations before using in workflows
- Direct integration with external applications
- Debugging search provider behaviour
- Quick information retrieval without workflow overhead
- Comparing results between DuckDuckGo and Tavily

**Behaviour:**

1. Validates configuration using ConfigValidator
2. Returns HTTP 400 if configuration is invalid
3. Logs warnings for non-fatal configuration issues (e.g., missing API key for Tavily)
4. Executes search via selected provider
5. Formats results into markdown structure
6. Returns graceful error response on search failure (not HTTP error)
7. Tracks execution metadata if node_id provided

**Validation:**

Configuration validation checks:

- `search_provider` must be "duckduckgo" or "tavily"
- `max_results` must be between 1 and 20
- `timeout_seconds` must be between 1 and 60
- Tavily-specific:
  - `search_depth` must be "basic" or "advanced"
  - Warns if `api_key` is missing (falls back to DuckDuckGo)
- DuckDuckGo-specific:
  - `safe_search` must be "off", "moderate", or "strict"
  - `time_range` must be "d", "w", "m", "y", or empty string

**Errors:**

- **400 Bad Request** - Invalid configuration

  ```json
  {
    "detail": {
      "message": "Invalid configuration",
      "errors": [
        "Invalid search provider: bing. Must be 'duckduckgo' or 'tavily'",
        "max_results must be between 1 and 20"
      ]
    }
  }
  ```

- **400 Bad Request** - Validation error

  ```json
  {
    "detail": "query must be at least 1 character long"
  }
  ```

---

#### `GET /api/tools/web-search/providers`

List available search providers and their capabilities.

**Authentication:** None

**Response:**

```json
{
  "providers": [
    {
      "name": "duckduckgo",
      "requires_api_key": false,
      "features": [
        "Free to use",
        "No API key required",
        "Text search",
        "Image search",
        "Region filtering",
        "Safe search",
        "Time range filtering"
      ],
      "description": "Free web search provider with no API key requirements. Good for general purpose searches."
    },
    {
      "name": "tavily",
      "requires_api_key": true,
      "features": [
        "AI-optimised results",
        "AI-generated answers",
        "Raw content extraction",
        "Image search",
        "Basic and advanced search depth",
        "Optimised for LLMs"
      ],
      "description": "AI-optimised search provider designed for LLM applications. Requires API key but provides higher quality results and AI answers."
    }
  ]
}
```

**Use Cases:**

- Discovering available search providers
- Understanding provider capabilities and requirements
- Building dynamic UI for provider selection
- Determining which provider to use for specific use cases

**Behaviour:**

- Returns static list of supported providers
- Includes feature lists to help users choose appropriate provider
- Indicates API key requirements

---

#### `POST /api/tools/web-search/validate`

Validate a web search configuration without executing a search.

**Authentication:** None

**Request Body:**

```json
{
  "config": {
    "search_provider": "tavily",
    "max_results": 10,
    "search_depth": "advanced",
    "include_answer": true,
    "api_key": ""
  }
}
```

**Response (Valid with Warnings):**

```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "Tavily provider selected but no API key provided. Will fall back to DuckDuckGo."
  ]
}
```

**Response (Invalid):**

```json
{
  "valid": false,
  "errors": [
    "Invalid search provider: bing. Must be 'duckduckgo' or 'tavily'",
    "max_results must be between 1 and 20"
  ],
  "warnings": []
}
```

**Use Cases:**

- Pre-flight validation before executing expensive searches
- Building configuration UIs with real-time validation
- Testing configuration changes safely
- Workflow validation before deployment

**Behaviour:**

- Runs all configuration validation rules
- Returns detailed errors and warnings
- Does not execute actual search
- Useful for interactive configuration building

---

#### `GET /api/tools/web-search/health`

Health check endpoint for web search API.

**Authentication:** None

**Response:**

```json
{
  "status": "healthy",
  "service": "web-search",
  "providers": ["duckduckgo", "tavily"]
}
```

**Use Cases:**

- Monitoring and alerting
- Load balancer health checks
- Service discovery
- Deployment validation

**Behaviour:**

- Always returns 200 OK if service is running
- Lists available providers
- Lightweight endpoint suitable for frequent polling

---

### Document Search Endpoints

#### `POST /api/tools/document-search/search`

Execute a document search using vector similarity, keyword search, or hybrid search across document collections.

**Authentication:** None (but searches user-scoped collections in production)

**Request Body (Similarity Search):**

```json
{
  "query": "What are the benefits of renewable energy?",
  "config": {
    "collection_names": ["research-papers", "articles-2025"],
    "search_k": 6,
    "search_mode": "hybrid",
    "citation_format": "structured",
    "include_confidence_scores": true,
    "similarity_threshold": 0.6
  }
}
```

**Request Body (Specific Documents):**

```json
{
  "query": "executive summary",
  "config": {
    "document_ids": ["doc-abc-123", "doc-def-456"],
    "search_k": 3,
    "search_mode": "keyword",
    "citation_format": "inline"
  }
}
```

**Request Body (Full Document Retrieval):**

```json
{
  "query": "any query (ignored for full document retrieval)",
  "config": {
    "document_ids": ["doc-abc-123"],
    "return_full_document": true
  }
}
```

**Request Fields:**

- `query` (required, string, min_length=1) - The search query
- `config` (optional, object) - Search configuration (uses defaults if omitted)

**Configuration Fields:**

*Document Selection:*

- `collection_names` (array of strings, default: []) - Collection IDs to search
- `document_ids` (array of strings, default: []) - Specific document IDs to search

*Search Parameters:*

- `search_k` (integer, 1-50, default: 6) - Number of results to return
- `search_type` (string, default: "similarity") - "similarity", "mmr", or "similarity_score_threshold"
- `similarity_threshold` (float, 0.0-1.0, default: 0.55) - Minimum similarity score

*Search Mode:*

- `search_mode` (string, default: "hybrid") - "vector", "keyword", or "hybrid"
- `hybrid_search_enabled` (boolean, default: true) - Enable hybrid search
- `keyword_weight` (float, 0.0-1.0, default: 0.5) - Weight for keyword search in hybrid mode
- `rrf_k` (integer, default: 60) - Reciprocal Rank Fusion constant (typically 50-60)
- `text_config` (string, default: "english") - PostgreSQL text search configuration

*Output Formatting:*

- `citation_format` (string, default: "structured") - "structured", "inline", "footnote", or "none"
- `include_metadata` (boolean, default: true) - Include metadata in results
- `include_confidence_scores` (boolean, default: true) - Include confidence scores
- `prompt_template` (string, default: "structured") - Prompt template for formatting
- `max_context_tokens` (integer, default: 2000) - Maximum context tokens (not enforced)

*Full Document Retrieval:*

- `return_full_document` (boolean, default: false) - Return full document instead of chunks (single document only)

**Response (Success - Structured Format):**

```json
{
  "success": true,
  "results": "# Search Results\n\n## Result 1: Renewable Energy Benefits Study\n**Document:** research-papers/renewable-energy-2024.pdf\n**Page:** 3\n**Confidence:** 0.87\n\nRenewable energy sources such as solar and wind power offer significant environmental and economic benefits. Key advantages include: reduced greenhouse gas emissions, decreased dependence on fossil fuels, job creation in green sectors, and long-term cost savings through decreased fuel expenses...\n\n## Result 2: Clean Energy Transition Report\n**Document:** articles-2025/clean-energy.pdf\n**Page:** 12\n**Confidence:** 0.82\n\nThe transition to renewable energy has demonstrated substantial benefits for both the environment and the economy. Studies show that renewable installations have created over 2 million jobs globally while reducing carbon emissions by 30% in participating regions...\n\n[... more results ...]",
  "metadata": {
    "query": "What are the benefits of renewable energy?",
    "collections_searched": ["research-papers", "articles-2025"],
    "documents_searched": [],
    "search_mode": "hybrid"
  }
}
```

**Response (No Results):**

```json
{
  "success": true,
  "results": "No relevant documents found for query: quantum entanglement in biological systems",
  "metadata": {
    "query": "quantum entanglement in biological systems",
    "result_count": 0
  }
}
```

**Response (Failure):**

```json
{
  "success": false,
  "error": "Search failed: Collection 'invalid-collection' not found"
}
```

**Use Cases:**

- Finding relevant information in document collections
- Question answering over uploaded documents
- Research across multiple document sets
- Extracting specific information from known documents
- Testing document search configurations
- Debugging vector embeddings and search behaviour

**Behaviour:**

1. Validates configuration using ConfigValidator
2. Returns HTTP 400 if configuration is invalid
3. Logs warnings for non-fatal configuration issues
4. Determines search mode (vector, keyword, or hybrid)
5. Executes search against specified collections or documents
6. Filters results by similarity threshold if using score threshold mode
7. Formats results according to citation_format
8. Returns metadata about search execution
9. Gracefully handles search failures (returns success: false, not HTTP error)

**Search Modes Explained:**

- **Vector Search (`search_mode: "vector"`)** - Pure semantic similarity using embeddings
  - Best for: Conceptual questions, finding similar content regardless of exact wording
  - Example: "machine learning algorithms" will find "neural networks" and "deep learning"

- **Keyword Search (`search_mode: "keyword"`)** - Traditional full-text search using PostgreSQL
  - Best for: Finding exact terms, names, specific phrases
  - Example: "John Smith" will find exact name matches

- **Hybrid Search (`search_mode: "hybrid"`)** - Combines vector and keyword with Reciprocal Rank Fusion
  - Best for: General purpose search, balancing semantic and exact matching
  - Controlled by `keyword_weight` parameter (0.5 = equal weighting)

**Citation Formats:**

- **Structured** - Markdown formatted with clear headings, metadata, and confidence scores
- **Inline** - Citations embedded within text as `[Source: document.pdf, p.5]`
- **Footnote** - References at the end with numbered footnotes
- **None** - Plain text without citations (just the content)

**Validation:**

Configuration validation checks:

- At least one of `collection_names` or `document_ids` must be provided
- `search_k` must be between 1 and 50
- `similarity_threshold` must be between 0.0 and 1.0
- `search_mode` must be "vector", "keyword", or "hybrid"
- `citation_format` must be "structured", "inline", "footnote", or "none"
- `keyword_weight` must be between 0.0 and 1.0
- `rrf_k` must be at least 1
- If `return_full_document` is true, must provide exactly one document_id

**Errors:**

- **400 Bad Request** - Invalid configuration

  ```json
  {
    "detail": {
      "message": "Invalid configuration",
      "errors": [
        "Must specify at least one collection_name or document_id",
        "search_k must be between 1 and 50"
      ]
    }
  }
  ```

- **400 Bad Request** - Validation error

  ```json
  {
    "detail": "query must be at least 1 character long"
  }
  ```

---

#### `POST /api/tools/document-search/validate`

Validate a document search configuration without executing a search.

**Authentication:** None

**Request Body:**

```json
{
  "config": {
    "collection_names": ["research-papers"],
    "search_k": 10,
    "search_mode": "hybrid",
    "similarity_threshold": 0.7,
    "citation_format": "structured"
  }
}
```

**Response (Valid):**

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

**Response (Invalid):**

```json
{
  "valid": false,
  "errors": [
    "Must specify at least one collection_name or document_id",
    "Invalid citation_format: 'custom'. Must be 'structured', 'inline', 'footnote', or 'none'"
  ],
  "warnings": [
    "similarity_threshold of 0.9 is very high and may return few results"
  ]
}
```

**Use Cases:**

- Pre-flight validation for search configurations
- Building configuration UIs with real-time feedback
- Workflow validation before deployment
- Testing configuration changes safely

**Behaviour:**

- Runs all configuration validation rules
- Returns detailed errors and warnings
- Does not execute actual search or database queries
- Checks logical consistency of parameters

---

#### `GET /api/tools/document-search/health`

Health check endpoint for document search API.

**Authentication:** None

**Response:**

```json
{
  "status": "healthy",
  "service": "document-search",
  "search_types": ["similarity", "hybrid", "keyword", "mmr"],
  "citation_formats": ["structured", "inline", "footnote", "none"]
}
```

**Use Cases:**

- Monitoring and alerting
- Load balancer health checks
- Service discovery
- Deployment validation

**Behaviour:**

- Always returns 200 OK if service is running
- Lists supported search types and citation formats
- Lightweight endpoint suitable for frequent polling

---

## Configuration Reference

### Web Search Configuration

Complete reference for `WebSearchConfig`:

```python
{
  # Provider selection
  "search_provider": "duckduckgo",  # "duckduckgo" or "tavily"
  "api_key": "",                    # Required for Tavily

  # Result limits
  "max_results": 5,                 # 1-20, number of results
  "timeout_seconds": 10,            # 1-60, search timeout

  # Tavily-specific options
  "search_depth": "basic",          # "basic" or "advanced"
  "include_answer": false,          # Include AI-generated answer
  "include_raw_content": false,     # Include raw page content

  # Common options
  "include_images": false,          # Include image results

  # DuckDuckGo-specific options
  "region": "wt-wt",               # Region code (e.g., "us-en", "uk-en")
  "safe_search": "moderate",       # "off", "moderate", "strict"
  "time_range": "",                # "d", "w", "m", "y", or ""

  # Tracking (optional)
  "node_id": "",                   # For execution tracking
  "node_name": "Web Search",       # Display name
  "tool_name": null                # Custom tool name
}
```

**Provider Comparison:**

| Feature                | DuckDuckGo                | Tavily                                |
|------------------------|---------------------------|---------------------------------------|
| API Key Required       | No                        | Yes                                   |
| Cost                   | Free                      | Paid                                  |
| Result Quality         | Good                      | Excellent (AI-optimised)              |
| AI-Generated Answers   | No                        | Yes                                   |
| Raw Content Extraction | No                        | Yes                                   |
| Search Depth Control   | No                        | Yes (basic/advanced)                  |
| Best For               | General searches, testing | LLM integration, high-quality results |

### Document Search Configuration

Complete reference for `DocumentSearchConfig`:

```python
{
  # Document selection (at least one required)
  "collection_names": [],          # List of collection IDs
  "document_ids": [],              # List of specific document IDs

  # Search parameters
  "search_k": 6,                   # 1-50, number of results
  "search_type": "similarity",     # "similarity", "mmr", "similarity_score_threshold"
  "similarity_threshold": 0.55,    # 0.0-1.0, minimum score

  # Search mode
  "search_mode": "hybrid",         # "vector", "keyword", "hybrid"
  "hybrid_search_enabled": true,   # Enable hybrid search
  "keyword_weight": 0.5,           # 0.0-1.0, weight for keywords in hybrid
  "rrf_k": 60,                     # Reciprocal Rank Fusion constant
  "text_config": "english",        # PostgreSQL text search config

  # Output formatting
  "citation_format": "structured", # "structured", "inline", "footnote", "none"
  "include_metadata": true,        # Include metadata in results
  "include_confidence_scores": true, # Include confidence scores
  "prompt_template": "structured", # Prompt template for formatting
  "max_context_tokens": 2000,      # Token limit (not enforced)

  # Full document retrieval
  "return_full_document": false,   # Return full doc instead of chunks

  # Tool naming (optional)
  "tool_name": null                # Custom tool name
}
```

**Search Mode Comparison:**

| Mode        | Speed     | Best For                              | Example Use Case            |
|-------------|-----------|---------------------------------------|-----------------------------|
| **Vector**  | Fast      | Semantic similarity, concept matching | "What are the main themes?" |
| **Keyword** | Very Fast | Exact terms, names, specific phrases  | "John Smith", "API-123"     |
| **Hybrid**  | Medium    | General purpose, balanced search      | "renewable energy benefits" |

**Citation Format Examples:**

**Structured:**

```
## Result 1: Document Title
**Document:** path/to/doc.pdf
**Page:** 5
**Confidence:** 0.87

Content excerpt here...
```

**Inline:**

```
The study found significant results [Source: research.pdf, p.12, confidence: 0.85]
which corroborate earlier findings [Source: previous-study.pdf, p.3, confidence: 0.79].
```

**Footnote:**

```
The research demonstrates clear benefits¹. Further analysis shows²...

---
References:
[1] Source: research.pdf, Page 5, Confidence: 0.87
[2] Source: analysis.pdf, Page 12, Confidence: 0.82
```

**None:**

```
The study found significant results which corroborate earlier findings.
```

---

## Validation Rules

### Web Search Validation

Validation rules enforced by `ConfigValidator`:

**Provider Validation:**

- `search_provider` must be exactly "duckduckgo" or "tavily"
- Invalid values trigger error: "Invalid search provider: {value}. Must be 'duckduckgo' or 'tavily'"

**Tavily-Specific:**

- If Tavily selected without `api_key`, warning issued: "Tavily provider selected but no API key provided. Will fall
  back to DuckDuckGo."
- `search_depth` must be "basic" or "advanced"

**DuckDuckGo-Specific:**

- `safe_search` must be "off", "moderate", or "strict"
- `time_range` must be "d", "w", "m", "y", or empty string

**Range Validation:**

- `max_results`: 1-20 (inclusive)
- `timeout_seconds`: 1-60 (inclusive)

**Common Validation Errors:**

```json
{
  "valid": false,
  "errors": [
    "Invalid search provider: google. Must be 'duckduckgo' or 'tavily'",
    "max_results must be between 1 and 20",
    "Invalid search depth: deep. Must be 'basic' or 'advanced'",
    "timeout_seconds must be between 1 and 60"
  ],
  "warnings": [
    "Tavily provider selected but no API key provided. Will fall back to DuckDuckGo."
  ]
}
```

### Document Search Validation

Validation rules enforced by `ConfigValidator`:

**Document Selection:**

- Must specify at least one of `collection_names` or `document_ids`
- Error if both are empty: "Must specify at least one collection_name or document_id"

**Search Parameters:**

- `search_k`: 1-50 (inclusive)
- `similarity_threshold`: 0.0-1.0 (inclusive)
- `keyword_weight`: 0.0-1.0 (inclusive)
- `rrf_k`: Must be ≥ 1

**Search Mode:**

- `search_mode` must be "vector", "keyword", or "hybrid"
- `search_type` must be "similarity", "mmr", or "similarity_score_threshold"

**Citation Format:**

- Must be "structured", "inline", "footnote", or "none"

**Full Document Retrieval:**

- If `return_full_document` is true:
  - Must provide exactly one `document_id`
  - Cannot specify `collection_names`
  - `search_k` is ignored

**Common Validation Errors:**

```json
{
  "valid": false,
  "errors": [
    "Must specify at least one collection_name or document_id",
    "search_k must be between 1 and 50",
    "Invalid search_mode: 'semantic'. Must be 'vector', 'keyword', or 'hybrid'",
    "Invalid citation_format: 'custom'. Must be 'structured', 'inline', 'footnote', or 'none'",
    "Full document retrieval requires exactly one document_id"
  ],
  "warnings": [
    "similarity_threshold of 0.9 is very high and may return few results",
    "search_k of 50 may result in very large responses"
  ]
}
```

---

## Error Handling

### Error Response Format

The Tools API uses two error response patterns:

**1. HTTP Errors (400 Bad Request)**

Used for validation failures and invalid requests:

```json
{
  "detail": {
    "message": "Invalid configuration",
    "errors": [
      "Invalid search provider: bing. Must be 'duckduckgo' or 'tavily'",
      "max_results must be between 1 and 20"
    ]
  }
}
```

Or simple string detail:

```json
{
  "detail": "query must be at least 1 character long"
}
```

**2. Graceful Error Response (200 OK)**

Used for search execution failures:

```json
{
  "success": false,
  "results": null,
  "error": "Search failed: Connection timeout after 10 seconds"
}
```

This design allows callers to distinguish between:

- **400 errors** - Fix your request and retry
- **200 with success: false** - Temporary failure, retry may succeed

### Common Error Scenarios

**Web Search Errors:**

| Error                     | Cause                                    | HTTP Status   | Solution                              |
|---------------------------|------------------------------------------|---------------|---------------------------------------|
| Invalid search provider   | Provider not "duckduckgo" or "tavily"    | 400           | Use valid provider name               |
| Invalid max_results       | Value outside 1-20 range                 | 400           | Use value between 1-20                |
| Missing API key (warning) | Tavily selected without key              | 200 (warning) | Provide API key or use DuckDuckGo     |
| Connection timeout        | Network issue or timeout_seconds too low | 200 (error)   | Increase timeout or retry             |
| Rate limit exceeded       | Too many requests to provider            | 200 (error)   | Wait and retry with backoff           |
| Invalid region code       | DuckDuckGo region not recognised         | 200 (error)   | Use valid region code (e.g., "us-en") |

**Document Search Errors:**

| Error                            | Cause                             | HTTP Status   | Solution                                 |
|----------------------------------|-----------------------------------|---------------|------------------------------------------|
| No collection/document specified | Both arrays empty                 | 400           | Provide collection_names or document_ids |
| Invalid search_k                 | Value outside 1-50 range          | 400           | Use value between 1-50                   |
| Invalid search_mode              | Mode not vector/keyword/hybrid    | 400           | Use valid search mode                    |
| Collection not found             | Collection doesn't exist          | 200 (error)   | Check collection name/ID                 |
| Document not found               | Document doesn't exist            | 200 (error)   | Check document ID                        |
| No results found                 | Query doesn't match any documents | 200 (success) | Adjust query or similarity threshold     |
| Embedding service unavailable    | Vector DB connection issue        | 200 (error)   | Retry or check service status            |
| Full document retrieval error    | Multiple docs specified           | 400           | Provide exactly one document_id          |

### Error Handling Examples

**Python Example:**

```python
import requests

def search_web(query: str, provider: str = "duckduckgo"):
    """Execute web search with proper error handling."""

    url = "http://localhost:8000/api/tools/web-search/search"
    payload = {
        "query": query,
        "config": {
            "search_provider": provider,
            "max_results": 5
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        # Check for HTTP errors (400)
        if response.status_code == 400:
            error_detail = response.json().get("detail", {})
            if isinstance(error_detail, dict):
                print(f"Validation errors: {error_detail.get('errors', [])}")
            else:
                print(f"Validation error: {error_detail}")
            return None

        # Check response status
        response.raise_for_status()

        # Parse response
        data = response.json()

        # Check for search execution errors
        if not data.get("success", False):
            print(f"Search failed: {data.get('error', 'Unknown error')}")
            return None

        # Check for no results
        results = data.get("results", "")
        if "No results found" in results:
            print(f"No results for query: {query}")
            return []

        return results

    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Usage
results = search_web("quantum computing 2025")
if results:
    print(results)
```

**JavaScript Example:**

```javascript
async function searchDocuments(query, collectionNames) {
  const url = 'http://localhost:8000/api/tools/document-search/search';

  const payload = {
    query: query,
    config: {
      collection_names: collectionNames,
      search_k: 6,
      search_mode: 'hybrid',
      citation_format: 'structured'
    }
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    // Check for HTTP errors
    if (response.status === 400) {
      const error = await response.json();
      console.error('Validation errors:', error.detail);
      return null;
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Parse response
    const data = await response.json();

    // Check for search execution errors
    if (!data.success) {
      console.error('Search failed:', data.error);
      return null;
    }

    // Check for no results
    if (data.results && data.results.includes('No relevant documents')) {
      console.log('No results found for query:', query);
      return [];
    }

    return data.results;

  } catch (error) {
    console.error('Request failed:', error);
    return null;
  }
}

// Usage
const results = await searchDocuments(
  'What are the benefits of renewable energy?',
  ['research-papers', 'articles-2025']
);

if (results) {
  console.log(results);
}
```

---

## Integration with Workflow Tools

### Architecture Integration

The Tools API endpoints use the **exact same implementation** as workflow tool nodes:

```
Workflow Node (Tool Type)
    ↓
Tool Factory (create_web_search_tool, create_document_search_tool)
    ↓
Tool Handlers (backend/tools/*/handlers.py)
    ↑
REST API Endpoints (backend/api/tools/*.py)
```

**This means:**

- Results from API are identical to workflow execution results
- Configuration tested via API will work identically in workflows
- Bug fixes benefit both API and workflows
- Same validation logic ensures consistency

### From API to Workflow

**Example: Testing Web Search Configuration**

1. **Test via API:**

```python
# Test configuration via API
response = requests.post(
    "http://localhost:8000/api/tools/web-search/search",
    json={
        "query": "climate change impacts 2025",
        "config": {
            "search_provider": "duckduckgo",
            "max_results": 5,
            "time_range": "m"
        }
    }
)

results = response.json()
print(results["results"])
```

1. **Use same config in workflow:**

```json
{
  "id": "node-web-search-1",
  "type": "WEB_SEARCH",
  "name": "Search Latest Climate News",
  "config": {
    "search_provider": "duckduckgo",
    "max_results": 5,
    "time_range": "m"
  }
}
```

**Example: Testing Document Search Before Workflow Creation**

```python
# 1. Validate configuration
validate_response = requests.post(
    "http://localhost:8000/api/tools/document-search/validate",
    json={
        "config": {
            "collection_names": ["company-docs"],
            "search_k": 8,
            "search_mode": "hybrid",
            "similarity_threshold": 0.65
        }
    }
)

validation = validate_response.json()
if not validation["valid"]:
    print("Errors:", validation["errors"])
    exit(1)

# 2. Test actual search
search_response = requests.post(
    "http://localhost:8000/api/tools/document-search/search",
    json={
        "query": "company revenue Q4 2024",
        "config": {
            "collection_names": ["company-docs"],
            "search_k": 8,
            "search_mode": "hybrid",
            "similarity_threshold": 0.65
        }
    }
)

results = search_response.json()
if results["success"]:
    print("Preview:", results["results"][:500])
else:
    print("Error:", results["error"])

# 3. Create workflow node with validated config
# ... create workflow with identical configuration
```

### Services Used

**Web Search Services:**

- **DuckDuckGo Service** ([backend/tools/web_search/execution.py](../../tools/web_search/execution.py))
  - Free web search via duckduckgo_search library
  - No authentication required
  - Rate limiting handled by provider

- **Tavily Service** ([backend/tools/web_search/execution.py](../../tools/web_search/execution.py))
  - AI-optimised search via Tavily API
  - Requires API key (environment variable or config)
  - Provides AI-generated answers and raw content

- **Result Formatting** ([backend/tools/web_search/handlers.py](../../tools/web_search/handlers.py))
  - Converts raw search results to markdown
  - Consistent format across providers
  - Includes titles, URLs, snippets

**Document Search Services:**

- **Vector Store Service
  ** ([backend/services/database/vector_store.py](../../backend/services/database/vector_store.py))
  - pgvector-based similarity search
  - Embedding generation via LLM service
  - Hybrid search with keyword fusion

- **Document Service** ([backend/services/documents/](../../backend/services/documents/))
  - Document retrieval and metadata
  - Collection management
  - Access control (user-scoping)

- **Formatting Services** ([backend/tools/document_search/formatters/](../../backend/tools/document_search/formatters/))
  - StructuredFormatter - Rich markdown with metadata
  - InlineFormatter - Citations within text
  - FootnoteFormatter - References at end
  - PlainFormatter - Text only, no citations
  - FullDocumentFormatter - Complete document retrieval

---

## Usage Examples

### Complete Web Search Workflow

```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

def complete_web_search_example():
    """Complete example of web search workflow."""

    # 1. Check available providers
    print("=== Checking Available Providers ===")
    providers_response = requests.get(f"{BASE_URL}/api/tools/web-search/providers")
    providers = providers_response.json()

    for provider in providers["providers"]:
        print(f"\nProvider: {provider['name']}")
        print(f"Requires API Key: {provider['requires_api_key']}")
        print(f"Features: {', '.join(provider['features'][:3])}...")

    # 2. Validate configuration before search
    print("\n\n=== Validating Configuration ===")
    config = {
        "search_provider": "duckduckgo",
        "max_results": 5,
        "region": "us-en",
        "safe_search": "moderate",
        "time_range": "m"  # Last month
    }

    validate_response = requests.post(
        f"{BASE_URL}/api/tools/web-search/validate",
        json={"config": config}
    )
    validation = validate_response.json()

    if validation["valid"]:
        print("✓ Configuration is valid")
        if validation["warnings"]:
            print(f"Warnings: {validation['warnings']}")
    else:
        print(f"✗ Configuration errors: {validation['errors']}")
        return

    # 3. Execute search
    print("\n\n=== Executing Search ===")
    search_response = requests.post(
        f"{BASE_URL}/api/tools/web-search/search",
        json={
            "query": "artificial intelligence breakthroughs 2025",
            "config": config
        }
    )

    search_data = search_response.json()

    if search_data["success"]:
        print("✓ Search successful")
        print("\nResults:")
        print(search_data["results"])
    else:
        print(f"✗ Search failed: {search_data['error']}")

    # 4. Compare with different provider (Tavily)
    print("\n\n=== Comparing with Tavily (with AI answer) ===")

    tavily_config = {
        "search_provider": "tavily",
        "api_key": "your-tavily-api-key",  # Replace with actual key
        "max_results": 5,
        "search_depth": "advanced",
        "include_answer": True
    }

    # Validate Tavily config
    tavily_validate = requests.post(
        f"{BASE_URL}/api/tools/web-search/validate",
        json={"config": tavily_config}
    )

    tavily_validation = tavily_validate.json()
    if tavily_validation["warnings"]:
        print(f"Warnings: {tavily_validation['warnings']}")
        # Will likely warn about missing API key and fall back to DuckDuckGo

    # Execute Tavily search (or fallback)
    tavily_search = requests.post(
        f"{BASE_URL}/api/tools/web-search/search",
        json={
            "query": "artificial intelligence breakthroughs 2025",
            "config": tavily_config
        }
    )

    tavily_data = tavily_search.json()
    if tavily_data["success"]:
        print("Results from Tavily:")
        print(tavily_data["results"][:500] + "...")

    # 5. Health check
    print("\n\n=== Health Check ===")
    health_response = requests.get(f"{BASE_URL}/api/tools/web-search/health")
    health = health_response.json()
    print(f"Status: {health['status']}")
    print(f"Available providers: {', '.join(health['providers'])}")


if __name__ == "__main__":
    complete_web_search_example()
```

### Complete Document Search Workflow

```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

def complete_document_search_example():
    """Complete example of document search workflow."""

    # 1. Health check
    print("=== Document Search Health Check ===")
    health_response = requests.get(f"{BASE_URL}/api/tools/document-search/health")
    health = health_response.json()
    print(f"Status: {health['status']}")
    print(f"Search types: {', '.join(health['search_types'])}")
    print(f"Citation formats: {', '.join(health['citation_formats'])}")

    # 2. Validate configuration for hybrid search
    print("\n\n=== Validating Hybrid Search Configuration ===")
    hybrid_config = {
        "collection_names": ["research-papers", "technical-docs"],
        "search_k": 8,
        "search_mode": "hybrid",
        "keyword_weight": 0.5,
        "similarity_threshold": 0.6,
        "citation_format": "structured",
        "include_confidence_scores": True
    }

    validate_response = requests.post(
        f"{BASE_URL}/api/tools/document-search/validate",
        json={"config": hybrid_config}
    )
    validation = validate_response.json()

    if validation["valid"]:
        print("✓ Configuration is valid")
    else:
        print(f"✗ Errors: {validation['errors']}")
        return

    # 3. Execute hybrid search
    print("\n\n=== Executing Hybrid Search ===")
    search_response = requests.post(
        f"{BASE_URL}/api/tools/document-search/search",
        json={
            "query": "What are the performance optimisations for database queries?",
            "config": hybrid_config
        }
    )

    search_data = search_response.json()

    if search_data["success"]:
        print("✓ Search successful")
        print(f"\nMetadata:")
        print(f"  Collections searched: {search_data['metadata']['collections_searched']}")
        print(f"  Search mode: {search_data['metadata']['search_mode']}")
        print("\nResults (first 800 chars):")
        print(search_data["results"][:800] + "...")
    else:
        print(f"✗ Search failed: {search_data['error']}")

    # 4. Compare with pure vector search
    print("\n\n=== Comparing with Pure Vector Search ===")
    vector_config = {
        "collection_names": ["research-papers", "technical-docs"],
        "search_k": 8,
        "search_mode": "vector",
        "similarity_threshold": 0.6,
        "citation_format": "inline"
    }

    vector_search = requests.post(
        f"{BASE_URL}/api/tools/document-search/search",
        json={
            "query": "What are the performance optimisations for database queries?",
            "config": vector_config
        }
    )

    vector_data = vector_search.json()
    if vector_data["success"]:
        print("✓ Vector search results (first 500 chars):")
        print(vector_data["results"][:500] + "...")

    # 5. Search specific documents with keyword search
    print("\n\n=== Searching Specific Documents (Keyword Mode) ===")
    keyword_config = {
        "document_ids": ["doc-technical-manual-123"],
        "search_k": 5,
        "search_mode": "keyword",
        "citation_format": "footnote"
    }

    keyword_search = requests.post(
        f"{BASE_URL}/api/tools/document-search/search",
        json={
            "query": "API authentication",
            "config": keyword_config
        }
    )

    keyword_data = keyword_search.json()
    if keyword_data["success"]:
        print("✓ Keyword search results:")
        print(keyword_data["results"])
    else:
        print(f"Note: {keyword_data.get('error', 'Document may not exist')}")

    # 6. Retrieve full document
    print("\n\n=== Retrieving Full Document ===")
    full_doc_config = {
        "document_ids": ["doc-readme-456"],
        "return_full_document": True
    }

    # Validate full document config
    full_validate = requests.post(
        f"{BASE_URL}/api/tools/document-search/validate",
        json={"config": full_doc_config}
    )

    if full_validate.json()["valid"]:
        full_doc_search = requests.post(
            f"{BASE_URL}/api/tools/document-search/search",
            json={
                "query": "",  # Query ignored for full document retrieval
                "config": full_doc_config
            }
        )

        full_doc_data = full_doc_search.json()
        if full_doc_data["success"]:
            print("✓ Full document retrieved (first 500 chars):")
            print(full_doc_data["results"][:500] + "...")
        else:
            print(f"Note: {full_doc_data.get('error', 'Document may not exist')}")

    # 7. Test configuration with high threshold
    print("\n\n=== Testing High Similarity Threshold ===")
    high_threshold_config = {
        "collection_names": ["research-papers"],
        "search_k": 10,
        "search_mode": "vector",
        "similarity_threshold": 0.9,  # Very high threshold
        "citation_format": "none"
    }

    # This should trigger a warning
    high_validate = requests.post(
        f"{BASE_URL}/api/tools/document-search/validate",
        json={"config": high_threshold_config}
    )

    high_validation = high_validate.json()
    if high_validation["warnings"]:
        print(f"Warnings: {high_validation['warnings']}")

    # Execute anyway to see results
    high_search = requests.post(
        f"{BASE_URL}/api/tools/document-search/search",
        json={
            "query": "machine learning algorithms",
            "config": high_threshold_config
        }
    )

    high_data = high_search.json()
    if "No relevant" in high_data.get("results", ""):
        print("As expected: High threshold returned no results")
    else:
        print("Found some highly relevant results")


if __name__ == "__main__":
    complete_document_search_example()
```

### JavaScript/TypeScript Example

```typescript
// tools-api-client.ts

interface WebSearchConfig {
  search_provider?: 'duckduckgo' | 'tavily';
  api_key?: string;
  max_results?: number;
  search_depth?: 'basic' | 'advanced';
  include_answer?: boolean;
  include_raw_content?: boolean;
  include_images?: boolean;
  timeout_seconds?: number;
  region?: string;
  safe_search?: 'off' | 'moderate' | 'strict';
  time_range?: 'd' | 'w' | 'm' | 'y' | '';
}

interface DocumentSearchConfig {
  collection_names?: string[];
  document_ids?: string[];
  search_k?: number;
  search_type?: 'similarity' | 'mmr' | 'similarity_score_threshold';
  similarity_threshold?: number;
  search_mode?: 'vector' | 'keyword' | 'hybrid';
  keyword_weight?: number;
  citation_format?: 'structured' | 'inline' | 'footnote' | 'none';
  include_metadata?: boolean;
  include_confidence_scores?: boolean;
  return_full_document?: boolean;
}

class ToolsAPIClient {
  constructor(private baseURL: string = 'http://localhost:8000') {}

  // Web Search Methods
  async searchWeb(query: string, config?: WebSearchConfig) {
    const response = await fetch(`${this.baseURL}/api/tools/web-search/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, config: config || {} })
    });

    if (response.status === 400) {
      const error = await response.json();
      throw new Error(`Validation error: ${JSON.stringify(error.detail)}`);
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error);
    }

    return data.results;
  }

  async getWebSearchProviders() {
    const response = await fetch(`${this.baseURL}/api/tools/web-search/providers`);
    return await response.json();
  }

  async validateWebSearchConfig(config: WebSearchConfig) {
    const response = await fetch(`${this.baseURL}/api/tools/web-search/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config })
    });
    return await response.json();
  }

  // Document Search Methods
  async searchDocuments(query: string, config?: DocumentSearchConfig) {
    const response = await fetch(`${this.baseURL}/api/tools/document-search/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, config: config || {} })
    });

    if (response.status === 400) {
      const error = await response.json();
      throw new Error(`Validation error: ${JSON.stringify(error.detail)}`);
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error);
    }

    return {
      results: data.results,
      metadata: data.metadata
    };
  }

  async validateDocumentSearchConfig(config: DocumentSearchConfig) {
    const response = await fetch(`${this.baseURL}/api/tools/document-search/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config })
    });
    return await response.json();
  }
}

// Usage examples
async function main() {
  const client = new ToolsAPIClient();

  // Web search example
  try {
    console.log('=== Web Search ===');
    const webResults = await client.searchWeb(
      'TypeScript best practices 2025',
      {
        search_provider: 'duckduckgo',
        max_results: 5,
        time_range: 'm'
      }
    );
    console.log(webResults);
  } catch (error) {
    console.error('Web search failed:', error.message);
  }

  // Document search example
  try {
    console.log('\n=== Document Search ===');
    const { results, metadata } = await client.searchDocuments(
      'How to implement authentication?',
      {
        collection_names: ['technical-docs'],
        search_k: 6,
        search_mode: 'hybrid',
        citation_format: 'structured'
      }
    );
    console.log('Results:', results.substring(0, 500) + '...');
    console.log('Metadata:', metadata);
  } catch (error) {
    console.error('Document search failed:', error.message);
  }

  // Validate configuration example
  console.log('\n=== Configuration Validation ===');
  const validation = await client.validateDocumentSearchConfig({
    collection_names: ['docs'],
    search_k: 10,
    search_mode: 'hybrid'
  });
  console.log('Valid:', validation.valid);
  if (validation.errors.length > 0) {
    console.log('Errors:', validation.errors);
  }
  if (validation.warnings.length > 0) {
    console.log('Warnings:', validation.warnings);
  }
}

main();
```

---

## Performance Considerations

### Endpoint Performance

**Fast Endpoints** (< 100ms typical):

- `GET /api/tools/web-search/health`
- `GET /api/tools/web-search/providers`
- `POST /api/tools/web-search/validate`
- `GET /api/tools/document-search/health`
- `POST /api/tools/document-search/validate`

These endpoints perform no external calls or database queries and can handle high request rates.

**Medium Endpoints** (100ms - 2s typical):

- `POST /api/tools/document-search/search` (vector/keyword mode, small collections)
  - Performance depends on:
    - Number of documents in collection
    - `search_k` value (higher = slower)
    - Search mode (keyword fastest, hybrid medium, vector with large k slowest)

**Slow Endpoints** (2s - 10s typical):

- `POST /api/tools/web-search/search`
  - Performance depends on:
    - Search provider (DuckDuckGo usually faster than Tavily)
    - Network latency
    - Provider rate limiting
    - `max_results` value
    - `timeout_seconds` setting (acts as upper bound)

- `POST /api/tools/document-search/search` (hybrid mode, large collections)
  - Performance depends on:
    - Collection size (1000+ documents can be slow)
    - Embedding generation time
    - Database query complexity

**Very Slow Endpoints** (10s+ possible):

- `POST /api/tools/document-search/search` with `return_full_document: true`
  - Retrieves entire document content
  - Can be slow for large PDFs (100+ pages)

### Optimisation Tips

**Web Search Optimisations:**

**Good Practice:**

```python
# Set reasonable timeout and result limits
config = {
    "search_provider": "duckduckgo",
    "max_results": 5,  # 5-10 is usually sufficient
    "timeout_seconds": 10  # Fail fast
}
```

**Bad Practice:**

```python
# Excessive results and timeout
config = {
    "max_results": 20,  # Too many results
    "timeout_seconds": 60  # Too long timeout
}
```

**Document Search Optimisations:**

**Good Practice - Hybrid Search:**

```python
# Balanced configuration
config = {
    "collection_names": ["specific-collection"],  # Limit scope
    "search_k": 6,  # Reasonable result count
    "search_mode": "hybrid",
    "keyword_weight": 0.5,  # Balanced weighting
    "similarity_threshold": 0.6  # Filter low-quality results
}
```

**Bad Practice - Over-Fetching:**

```python
# Slow configuration
config = {
    "collection_names": ["all-docs", "archive", "old-files"],  # Too broad
    "search_k": 50,  # Too many results
    "search_mode": "hybrid",
    "similarity_threshold": 0.1  # Too low, many irrelevant results
}
```

**Good Practice - Specific Document Search:**

```python
# Fast, targeted search
config = {
    "document_ids": ["doc-abc-123"],  # Specific documents
    "search_k": 3,  # Few results needed
    "search_mode": "keyword"  # Fastest mode for exact matches
}
```

**Good Practice - Use Appropriate Search Mode:**

```python
# For exact terms/names → keyword search (fastest)
keyword_config = {
    "search_mode": "keyword",
    "search_k": 5
}

# For semantic/conceptual → vector search
vector_config = {
    "search_mode": "vector",
    "search_k": 6
}

# For balanced/general → hybrid search
hybrid_config = {
    "search_mode": "hybrid",
    "keyword_weight": 0.5
}
```

### Caching Strategies

**Application-Level Caching:**

```python
from functools import lru_cache
import hashlib
import json

class CachedToolsClient:
    def __init__(self):
        self._cache = {}

    def _cache_key(self, query: str, config: dict) -> str:
        """Generate cache key from query and config."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(f"{query}:{config_str}".encode()).hexdigest()

    def search_web_cached(self, query: str, config: dict, ttl_seconds: int = 300):
        """Web search with 5-minute cache."""
        cache_key = self._cache_key(query, config)

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if time.time() - cached_time < ttl_seconds:
                print("Cache hit!")
                return cached_result

        # Execute search
        result = requests.post(
            "http://localhost:8000/api/tools/web-search/search",
            json={"query": query, "config": config}
        ).json()

        # Store in cache
        self._cache[cache_key] = (time.time(), result)

        return result
```

**Redis Caching for Production:**

```python
import redis
import json

class RedisToolsCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def search_documents_cached(self, query: str, config: dict):
        """Document search with Redis caching."""
        cache_key = f"doc_search:{hashlib.md5(f'{query}:{json.dumps(config, sort_keys=True)}'.encode()).hexdigest()}"

        # Try cache
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Execute search
        response = requests.post(
            "http://localhost:8000/api/tools/document-search/search",
            json={"query": query, "config": config}
        )
        result = response.json()

        # Cache for 10 minutes
        self.redis.setex(cache_key, 600, json.dumps(result))

        return result
```

---

## Related Documentation

### Architecture Documentation

- [System Architecture Overview](../architecture/system-overview.md) - Overall AgenticStudio architecture
- [Tool System Design](../architecture/tool-system.md) - How tools work in AgenticStudio
- [Services Layer](../architecture/services-layer.md) - Service layer architecture

### API Module Documentation

- [Graph API Module](../../../backend/api/graph/graph.md) - Workflow and graph management API (includes tool node configuration)
- [Execution API Module](../../../backend/api/execution/execution.md) - Workflow execution endpoints
- [Documents API Module](../../../backend/api/documents/documents.md) - Document upload and management (feeds document search)

### Tool Implementation Documentation

- [Web Search Tool Implementation](../tools/web-search.md) - Detailed web search tool documentation
- [Document Search Tool Implementation](../tools/document-search.md) - Detailed document search tool documentation
- [Tool Development Guide](../guides/tool-development.md) - Creating custom tools

### Integration Guides

- [Workflow Builder Guide](../guides/workflow-builder.md) - Building workflows with tool nodes
- [API Integration Guide](../guides/api-integration.md) - Integrating with AgenticStudio APIs
- [Testing Guide](../guides/testing.md) - Testing tool configurations

---

## Summary

The Tools API module provides **direct REST access** to AgenticStudio's web search and document search capabilities,
enabling testing, debugging, and external integrations without requiring workflow creation.

### Key Features

**Web Search:**

- Multiple providers (DuckDuckGo free, Tavily AI-optimised)
- Configurable result limits, timeouts, and filtering
- Provider comparison endpoint
- Configuration validation
- Automatic fallback handling

**Document Search:**

- Vector similarity, keyword, and hybrid search modes
- Flexible citation formats (structured, inline, footnote, none)
- Collection and document-specific searches
- Full document retrieval option
- Advanced configuration with similarity thresholds and weighting

**Common Features:**

- Pre-flight configuration validation
- Comprehensive error handling
- Health check endpoints
- Identical behaviour to workflow tools
- Detailed response metadata

### Primary Use Cases

1. **Testing & Debugging** - Validate search configurations before using in workflows
2. **Direct Integration** - Access search capabilities from external systems
3. **API Exploration** - Experiment with search parameters and providers
4. **Configuration Development** - Fine-tune search settings iteratively
5. **Quality Assurance** - Compare search results across different configurations
6. **Monitoring** - Health checks for search service availability

The Tools API serves as both a **standalone search interface** and a **testing ground for workflow tool configurations
**, ensuring consistency between direct API usage and workflow-based search execution.
