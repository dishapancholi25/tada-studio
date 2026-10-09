# Search Service

## Overview

The search service provides web search capabilities through multiple search providers (Tavily and DuckDuckGo) with
flexible result formatting options. It implements provider and formatter patterns for extensibility, allowing easy
integration of new search engines and output formats.

**Location:** [backend/services/search/](../../backend/services/search/)

**Primary Responsibilities:**

- Execute web searches using multiple providers (Tavily AI-optimised search, DuckDuckGo)
- Format search results in multiple formats (text, markdown)
- Handle provider-specific features (AI-generated answers, image search, relevance scoring)
- Provide fallback mechanisms when primary provider fails
- Abstract provider-specific APIs into consistent interfaces

**Key Use Cases:**

- Enabling agents to search the web for current information
- Retrieving image results from search queries
- Getting AI-generated answers from Tavily (optimised for LLM consumption)
- Formatting search results for different output contexts
- Performing searches without API keys using DuckDuckGo

## Architecture

### Module Structure

```
backend/services/search/
├── __init__.py                      # Public API exports
├── web_search_service.py            # Main orchestrator service
├── providers/                       # Search provider implementations
│   ├── __init__.py                  # Provider exports
│   ├── base.py                      # Abstract SearchProvider base class
│   ├── tavily.py                    # Tavily API provider (AI-optimised)
│   └── duckduckgo.py                # DuckDuckGo provider (no API key)
└── formatters/                      # Result formatting implementations
    ├── __init__.py                  # Formatter exports
    ├── base.py                      # Abstract ResultFormatter base class
    ├── text_formatter.py            # Plain text formatter
    └── markdown_formatter.py        # Markdown formatter
```

**File Purposes:**

- **web_search_service.py**: Main orchestrator that provides static methods for searching and formatting, plus a
  singleton instance for backward compatibility
- **providers/base.py**: Abstract base class defining the provider interface
- **providers/tavily.py**: Implements Tavily API with async context handling, AI answer support, and relevance scoring
- **providers/duckduckgo.py**: Implements DuckDuckGo search with text and image search capabilities
- **formatters/base.py**: Abstract base class for result formatters with common utilities
- **formatters/text_formatter.py**: Formats results as human-readable plain text
- **formatters/markdown_formatter.py**: Formats results as structured markdown with headers and links

### Design Patterns

**1. Strategy Pattern (Providers)**

- `SearchProvider` defines the interface for different search engines
- Each provider implements the same interface but with provider-specific behaviour
- Allows runtime selection of search provider without changing client code

**2. Strategy Pattern (Formatters)**

- `ResultFormatter` defines the interface for different output formats
- Each formatter implements the same interface but produces different output
- Supports multiple presentation formats for the same search results

**3. Facade Pattern**

- `WebSearchService` provides a simplified interface to complex provider and formatter subsystems
- Static methods hide the complexity of instantiating providers and formatters
- Singleton instance (`web_search_service`) provides convenient access point

**4. Template Method Pattern**

- Base classes define the structure (abstract `search()` and `format()` methods)
- Subclasses implement specific behaviour while following the template

**Component Relationships:**

```
┌────────────────────────────────────────────────────┐
│           WebSearchService                         │
│  (Orchestrator - Static Methods + Singleton)       │
└─────────────┬──────────────────────┬───────────────┘
              │                      │
      ┌───────▼─────────┐    ┌──────▼──────────┐
      │   Providers     │    │   Formatters    │
      │   Subsystem     │    │   Subsystem     │
      └───────┬─────────┘    └──────┬──────────┘
              │                      │
    ┌─────────┴─────────┐    ┌──────┴──────────┐
    │                   │    │                 │
┌───▼────────┐  ┌───────▼──┐ │  ┌──────────┐  │
│ Tavily     │  │DuckDuckGo│ │  │Text      │  │
│ Provider   │  │Provider  │ │  │Formatter │  │
└────────────┘  └──────────┘ │  └──────────┘  │
                              │  ┌──────────┐  │
                              │  │Markdown  │  │
                              │  │Formatter │  │
                              │  └──────────┘  │
                              └─────────────────┘

Integration Layer:
backend/tools/web_search/handlers.py
- Uses web_search_service singleton
- Adds execution metadata tracking
- Implements fallback logic
- Integrates with agent tools
```

### Dependencies

**Internal Dependencies:**

- None - This is a foundational service with no dependencies on other backend services

**External Dependencies:**

- `tavily-python`: Tavily API client for AI-optimised search (optional, gracefully degrades if not installed)
- `duckduckgo-search`: DuckDuckGo search client (optional, gracefully degrades if not installed)
- `asyncio`, `concurrent.futures`: For handling async contexts in synchronous code

**Database Dependencies:**

- None - This service is stateless and doesn't interact with databases

**Environment Variables:**

- `TAVILY_API_KEY`: API key for Tavily search (required for Tavily provider, optional otherwise)

**Integration Points:**

- [backend/tools/web_search/handlers.py](../../backend/tools/web_search/handlers.py): Tool layer that uses this service
  to implement agent web search tools

## Public API

### Exported Classes

- `WebSearchService` - Main orchestrator service providing search and formatting capabilities
- `web_search_service` - Singleton instance of WebSearchService for convenient access

### Exported Functions

All functionality is exposed through `WebSearchService` static methods:

- `search_duckduckgo()` - Search using DuckDuckGo (no API key required)
- `search_duckduckgo_images()` - Search for images using DuckDuckGo
- `search_tavily()` - Search using Tavily API (AI-optimised, requires API key)
- `format_results_as_text()` - Format results as plain text
- `format_results_as_markdown()` - Format results as markdown

### Constants and Configuration

No exported constants. Configuration is passed as method parameters.

### Exceptions

This service does not define custom exceptions. It returns error information in result dictionaries:

**Error Response Format:**

```python
{
    "error": "Error message describing what went wrong",
    "source": "provider_name"  # tavily or duckduckgo
}
```

**Common Error Scenarios:**

- Missing API key: `"Tavily API key is required"`
- Missing dependencies: `"Please install: pip install tavily-python"`
- Search failures: `"Search failed: {exception_message}"`

## Core Classes

### `WebSearchService`

Main orchestrator service that provides unified access to multiple search providers and result formatters through static
methods.

**Purpose:** Simplify web search operations by providing a consistent interface regardless of the underlying search
provider or output format.

**Responsibilities:**

- Instantiate and manage provider instances (Tavily, DuckDuckGo)
- Instantiate and manage formatter instances (text, markdown)
- Provide static methods for stateless search operations
- Delegate search requests to appropriate providers
- Delegate formatting requests to appropriate formatters
- Handle provider-specific parameter mappings

**Initialisation:**

```python
def __init__(self) -> None:
    """
    Initialise web search service with providers and formatters.

    Creates instances of all supported providers and formatters.
    Note: Static methods create their own instances, so this is
    only needed for the singleton instance.
    """
```

**Key Methods:**

#### `search_duckduckgo()`

```python
@staticmethod
def search_duckduckgo(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    safe_search: str = "moderate",
    time_range: str = "",
    timeout: int = 10,
) -> List[Dict[str, Any]]:
    """Search using DuckDuckGo (no API key required)."""
```

**Parameters:**

- `query` (str) - Search query string to execute
- `max_results` (int) - Maximum number of results to return (default: 5)
- `region` (str) - Region code for localised results. Common values: "wt-wt" (no region), "us-en" (US), "uk-en" (UK), "
  au-en" (Australia) (default: "wt-wt")
- `safe_search` (str) - Safe search filter setting: "off", "moderate", or "strict" (default: "moderate")
- `time_range` (str) - Time range filter: "d" (day), "w" (week), "m" (month), "y" (year), or "" (no filter) (
  default: "")
- `timeout` (int) - Request timeout in seconds (default: 10)

**Returns:**

- `List[Dict[str, Any]]` - List of search result dictionaries, each containing:
  - `title` (str): Result title
  - `url` (str): Result URL
  - `snippet` (str): Text snippet/description
  - `position` (int): Result position (1-indexed)
  - `source` (str): Provider name ("duckduckgo")

**Raises:**

- Does not raise exceptions - returns error dictionary in list if search fails

**Example:**

```python
from backend.services.search import WebSearchService

# Basic search
results = WebSearchService.search_duckduckgo(
    query="Python web scraping best practices"
)

# Advanced search with region and time filter
results = WebSearchService.search_duckduckgo(
    query="AI news",
    max_results=10,
    region="us-en",
    safe_search="strict",
    time_range="w",  # Last week
    timeout=15,
)

# Check for errors
if results and isinstance(results[0], dict) and "error" in results[0]:
    print(f"Search failed: {results[0]['error']}")
else:
    for result in results:
        print(f"{result['title']}: {result['url']}")
```

**Behaviour:**

- Creates a new `DuckDuckGoProvider` instance for each call
- Executes search through DuckDuckGo's API
- Returns standardised result format regardless of DuckDuckGo's native format
- Gracefully handles missing `duckduckgo-search` package by returning error in results
- Logs search execution and result count

**Use Cases:**

- Quick searches without requiring API key configuration
- Testing search functionality without API quota concerns
- Fallback when Tavily API is unavailable or rate-limited
- Regional content discovery with region parameter
- Recent content filtering with time_range parameter

#### `search_duckduckgo_images()`

```python
@staticmethod
def search_duckduckgo_images(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    safe_search: str = "moderate",
    size: str = "",
    timeout: int = 10,
) -> List[Dict[str, Any]]:
    """Search for images using DuckDuckGo."""
```

**Parameters:**

- `query` (str) - Image search query
- `max_results` (int) - Maximum number of image results (default: 5)
- `region` (str) - Region code (default: "wt-wt")
- `safe_search` (str) - Safe search setting (default: "moderate")
- `size` (str) - Size filter: "Small", "Medium", "Large", "Wallpaper", or "" (no filter) (default: "")
- `timeout` (int) - Request timeout in seconds (default: 10)

**Returns:**

- `List[Dict[str, Any]]` - List of image result dictionaries, each containing:
  - `title` (str): Image title
  - `url` (str): Source page URL
  - `image_url` (str): Direct image URL
  - `thumbnail` (str): Thumbnail image URL
  - `source` (str): Image source domain
  - `width` (int): Image width in pixels
  - `height` (int): Image height in pixels
  - `position` (int): Result position
  - `type` (str): Always "image"

**Raises:**

- Does not raise exceptions - returns empty list on error

**Example:**

```python
from backend.services.search import WebSearchService

# Search for images
images = WebSearchService.search_duckduckgo_images(
    query="Golden Gate Bridge",
    max_results=10,
    size="Large",
)

# Display image information
for img in images:
    print(f"Title: {img['title']}")
    print(f"Image URL: {img['image_url']}")
    print(f"Size: {img['width']}x{img['height']}")
    print(f"Source: {img['source']}\n")
```

**Behaviour:**

- Creates a new `DuckDuckGoProvider` instance
- Searches DuckDuckGo's image database
- Returns standardised image result format
- Returns empty list if `duckduckgo-search` package not installed
- Filters by size if specified

**Use Cases:**

- Finding images for agent responses
- Visual content discovery
- Wallpaper and high-resolution image searches
- Safe image search with content filtering

#### `search_tavily()`

```python
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
    """Search using Tavily API (optimised for LLMs)."""
```

**Parameters:**

- `query` (str) - Search query string
- `api_key` (str) - Tavily API key (required)
- `max_results` (int) - Maximum number of results (default: 5)
- `search_depth` (str) - Search depth: "basic" (faster) or "advanced" (more comprehensive) (default: "basic")
- `include_answer` (bool) - Include AI-generated answer optimised for LLM consumption (default: False)
- `include_raw_content` (bool) - Include raw page content for each result (default: False)
- `include_images` (bool) - Include related image results (default: False)
- `timeout` (int) - Request timeout in seconds (default: 10)

**Returns:**

- `Dict[str, Any]` - Dictionary containing:
  - `results` (List[Dict]): List of search results with:
    - `title` (str): Result title
    - `url` (str): Result URL
    - `snippet` (str): Content snippet
    - `score` (float): Relevance score (0-1)
    - `raw_content` (str): Full page content (if `include_raw_content=True`)
    - `position` (int): Result position
  - `answer` (str): AI-generated answer (if `include_answer=True`)
  - `images` (List[str]): Related image URLs (if `include_images=True`)
  - `query` (str): Original query
  - `search_depth` (str): Depth used
  - `source` (str): Provider name ("tavily")

**Raises:**

- Does not raise exceptions - returns error dictionary on failure

**Example:**

```python
from backend.services.search import WebSearchService
import os

# Basic Tavily search
results = WebSearchService.search_tavily(
    query="What is quantum computing?",
    api_key=os.environ.get("TAVILY_API_KEY"),
    max_results=5,
)

# Advanced search with AI answer
results = WebSearchService.search_tavily(
    query="Latest developments in quantum computing 2024",
    api_key=os.environ.get("TAVILY_API_KEY"),
    max_results=10,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=True,
)

# Check for AI answer
if "answer" in results:
    print(f"AI Answer: {results['answer']}\n")

# Process results
for result in results.get("results", []):
    print(f"{result['title']} (score: {result['score']:.2f})")
    print(f"URL: {result['url']}")
    print(f"Snippet: {result['snippet']}\n")

# Display related images
if "images" in results:
    print(f"\nRelated images: {len(results['images'])} found")
```

**Behaviour:**

- Creates a new `TavilyProvider` instance
- Handles async/sync context automatically using thread pool in async contexts
- Returns error dict if API key is missing or invalid
- Provides relevance scores for ranking results
- Optionally includes AI-generated summary optimised for LLM consumption
- Gracefully degrades if `tavily-python` package not installed

**Use Cases:**

- Getting AI-optimised search results for agent consumption
- Retrieving comprehensive answers with source citations
- Advanced research with deep search capability
- Obtaining relevance-scored results for ranking
- Getting raw content for further processing

#### `format_results_as_text()`

```python
@staticmethod
def format_results_as_text(
    results: Any,
    include_urls: bool = True,
    include_snippets: bool = True,
    max_snippet_length: int = 200,
) -> str:
    """Format search results as readable text."""
```

**Parameters:**

- `results` (Any) - Search results (list from DuckDuckGo or dict from Tavily)
- `include_urls` (bool) - Include URLs in formatted output (default: True)
- `include_snippets` (bool) - Include content snippets in output (default: True)
- `max_snippet_length` (int) - Maximum snippet length before truncation (default: 200)

**Returns:**

- `str` - Formatted plain text string with results

**Raises:**

- Does not raise exceptions - returns empty string on error

**Example:**

```python
from backend.services.search import WebSearchService

# Search and format
results = WebSearchService.search_duckduckgo(
    query="Python async programming"
)

formatted = WebSearchService.format_results_as_text(
    results=results,
    include_urls=True,
    include_snippets=True,
    max_snippet_length=150,
)

print(formatted)
# Output:
# Search Results (5 found):
#
# 1. Python Async Programming Guide
#    URL: https://example.com/python-async
#    Learn how to write asynchronous Python code using asyncio...
#
# 2. Understanding asyncio
#    URL: https://example.com/asyncio
#    A comprehensive guide to Python's asyncio library...
```

**Behaviour:**

- Creates a new `TextFormatter` instance
- Handles both list and dict result formats
- Truncates long snippets to specified length
- Displays AI answers if present (Tavily results)
- Shows image URLs if present
- Numbers results sequentially

**Use Cases:**

- Displaying results in terminal or log output
- Creating human-readable summaries
- Generating plain text reports
- Testing and debugging search functionality

#### `format_results_as_markdown()`

```python
@staticmethod
def format_results_as_markdown(
    results: Any,
    include_urls: bool = True,
    include_snippets: bool = True,
) -> str:
    """Format search results as Markdown."""
```

**Parameters:**

- `results` (Any) - Search results (list or dict)
- `include_urls` (bool) - Include URLs in formatted output (default: True)
- `include_snippets` (bool) - Include content snippets in output (default: True)

**Returns:**

- `str` - Markdown formatted string with headers, links, and structured content

**Raises:**

- Does not raise exceptions

**Example:**

```python
from backend.services.search import WebSearchService

# Search with Tavily
results = WebSearchService.search_tavily(
    query="Machine learning best practices",
    api_key="your-api-key",
    include_answer=True,
)

# Format as markdown
markdown = WebSearchService.format_results_as_markdown(
    results=results,
    include_urls=True,
    include_snippets=True,
)

# Save to file or display
with open("search_results.md", "w") as f:
    f.write(markdown)

# Output structure:
# ## AI-Generated Answer
#
# Machine learning best practices include...
#
# ---
#
# ## Search Results
#
# ### [ML Best Practices](https://example.com)
#
# A comprehensive guide to machine learning...
#
# *Relevance: 0.95 | Source: tavily*
# ---
```

**Behaviour:**

- Creates a new `MarkdownFormatter` instance
- Structures output with headers and sections
- Formats titles as clickable links when URLs included
- Displays AI answers in dedicated section
- Shows metadata (relevance scores, source) in italics
- Separates results with horizontal rules

**Use Cases:**

- Generating documentation from search results
- Creating formatted agent responses
- Producing rich text output for web display
- Building knowledge base articles from searches

**Class Attributes:**

- `duckduckgo_provider: DuckDuckGoProvider` - Instance of DuckDuckGo provider
- `tavily_provider: TavilyProvider` - Instance of Tavily provider
- `text_formatter: TextFormatter` - Instance of text formatter
- `markdown_formatter: MarkdownFormatter` - Instance of markdown formatter

**Properties:**

- None - All functionality exposed through static methods

---

### Provider Classes (Not Exported)

The following classes are used internally by `WebSearchService` but are not part of the public API:

#### `SearchProvider` (Abstract Base Class)

Base interface for all search providers.

**Location:** [backend/services/search/providers/base.py](../../backend/services/search/providers/base.py)

```python
class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, **kwargs) -> Any:
        """Execute a search query."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass
```

#### `TavilyProvider`

Implements Tavily API integration with async context handling.

**Location:** [backend/services/search/providers/tavily.py](../../backend/services/search/providers/tavily.py)

**Key Features:**

- Automatic async/sync context detection
- Thread pool execution in async contexts to avoid event loop conflicts
- AI-generated answer support
- Relevance scoring
- Raw content retrieval
- Image search integration

#### `DuckDuckGoProvider`

Implements DuckDuckGo search without requiring API keys.

**Location:** [backend/services/search/providers/duckduckgo.py](../../backend/services/search/providers/duckduckgo.py)

**Key Features:**

- Text search with region and time filtering
- Image search with size filtering
- Safe search controls
- No API key required
- Result standardisation

---

### Formatter Classes (Not Exported)

#### `ResultFormatter` (Abstract Base Class)

Base interface for result formatters.

**Location:** [backend/services/search/formatters/base.py](../../backend/services/search/formatters/base.py)

```python
class ResultFormatter(ABC):
    @abstractmethod
    def format(self, results: Any, **kwargs) -> str:
        """Format search results into a string representation."""
        pass
```

#### `TextFormatter`

Formats results as plain text with optional URLs and snippets.

**Location:
** [backend/services/search/formatters/text_formatter.py](../../backend/services/search/formatters/text_formatter.py)

#### `MarkdownFormatter`

Formats results as structured markdown with headers and links.

**Location:
** [backend/services/search/formatters/markdown_formatter.py](../../backend/services/search/formatters/markdown_formatter.py)

## Configuration

### Configuration Classes

This service does not use configuration classes. All configuration is passed as method parameters.

### Environment Variables

- `TAVILY_API_KEY` - API key for Tavily search service
  - Required: Only if using Tavily provider
  - Default: None
  - Example: `tvly-abc123xyz456`
  - How to obtain: Sign up at <https://tavily.com>

### Initialisation Patterns

**Basic Initialisation (Using Static Methods):**

```python
from backend.services.search import WebSearchService

# No initialisation needed - use static methods directly
results = WebSearchService.search_duckduckgo(query="Python tutorials")
```

**Using Singleton Instance:**

```python
from backend.services.search import web_search_service

# Use pre-created singleton instance
results = web_search_service.search_duckduckgo(query="Python tutorials")
```

**Advanced Initialisation (Custom Instance):**

```python
from backend.services.search import WebSearchService

# Create custom instance (rarely needed)
service = WebSearchService()

# Use instance methods (note: internally creates provider instances)
# Same behaviour as static methods
results = WebSearchService.search_duckduckgo(query="Python tutorials")
```

**Dependency Injection (In Tool Layer):**

```python
# backend/tools/web_search/handlers.py
from backend.services.search import web_search_service

def execute_web_search(query: str, provider: str = "duckduckgo"):
    """Tool handler uses singleton instance."""
    if provider == "tavily":
        return web_search_service.search_tavily(
            query=query,
            api_key=os.environ.get("TAVILY_API_KEY"),
        )
    else:
        return web_search_service.search_duckduckgo(query=query)
```

## Error Handling

### Exception Hierarchy

This service does not raise custom exceptions. Instead, it uses error dictionaries for graceful degradation:

```
No Custom Exceptions
├── Returns error dictionaries in results
├── Logs errors via Python logging
└── Gracefully handles missing dependencies
```

### Error Response Formats

**DuckDuckGo Error (List Format):**

```python
[
    {
        "error": "DuckDuckGo search not available. Please install: pip install duckduckgo-search",
        "source": "duckduckgo"
    }
]
```

**Tavily Error (Dict Format):**

```python
{
    "error": "Tavily API key is required",
    "source": "tavily"
}
```

### Error Handling Patterns

**Pattern 1: Check for Errors in Results**

```python
from backend.services.search import WebSearchService

results = WebSearchService.search_duckduckgo(query="Python")

# Check for errors in list results
if results and isinstance(results, list):
    if "error" in results[0]:
        print(f"Search failed: {results[0]['error']}")
        # Handle error gracefully
    else:
        # Process successful results
        for result in results:
            print(result['title'])

# Check for errors in dict results (Tavily)
results = WebSearchService.search_tavily(
    query="Python",
    api_key="invalid",
)

if isinstance(results, dict) and "error" in results:
    print(f"Search failed: {results['error']}")
else:
    # Process successful results
    for result in results.get("results", []):
        print(result['title'])
```

**Pattern 2: Fallback Chain**

```python
from backend.services.search import WebSearchService
import os

def search_with_fallback(query: str) -> list:
    """Try Tavily first, fallback to DuckDuckGo."""
    api_key = os.environ.get("TAVILY_API_KEY")

    # Try Tavily if API key available
    if api_key:
        results = WebSearchService.search_tavily(
            query=query,
            api_key=api_key,
        )

        # Check for errors
        if isinstance(results, dict) and "error" not in results:
            return results.get("results", [])

    # Fallback to DuckDuckGo
    results = WebSearchService.search_duckduckgo(query=query)

    # Check for errors
    if results and isinstance(results, list) and "error" not in results[0]:
        return results

    # Both failed
    return []
```

**Pattern 3: Graceful Degradation**

```python
from backend.services.search import WebSearchService
import logging

logger = logging.getLogger(__name__)

def safe_search(query: str) -> str:
    """Perform search with comprehensive error handling."""
    try:
        # Attempt search
        results = WebSearchService.search_duckduckgo(query=query)

        # Check for errors
        if results and isinstance(results, list) and "error" in results[0]:
            logger.error(f"Search error: {results[0]['error']}")
            return f"Search unavailable: {results[0]['error']}"

        # Format results
        if results:
            formatted = WebSearchService.format_results_as_text(results)
            return formatted if formatted else "No results found"
        else:
            return "No results found"

    except Exception as e:
        logger.exception(f"Unexpected search error: {e}")
        return f"Search failed due to unexpected error: {str(e)}"
```

**Pattern 4: Provider-Specific Error Handling**

```python
from backend.services.search import WebSearchService

def handle_tavily_errors(results: dict) -> str:
    """Handle Tavily-specific error scenarios."""
    if "error" not in results:
        return "success"

    error_msg = results["error"]

    if "API key" in error_msg:
        return "api_key_missing"
    elif "not installed" in error_msg:
        return "package_missing"
    elif "rate limit" in error_msg.lower():
        return "rate_limited"
    else:
        return "unknown_error"

# Usage
results = WebSearchService.search_tavily(
    query="test",
    api_key="test-key",
)

error_type = handle_tavily_errors(results)
if error_type == "api_key_missing":
    print("Please configure TAVILY_API_KEY environment variable")
elif error_type == "package_missing":
    print("Run: pip install tavily-python")
elif error_type == "success":
    print("Search successful")
```

## Integration Patterns

### Integration with API Layer

The search service is not directly exposed through REST APIs. Instead, it's integrated through the tool layer.

### Integration with Tools Layer

The primary integration point is through the web search tools layer:

```python
# backend/tools/web_search/handlers.py
from backend.services.search import web_search_service
from .schemas import WebSearchConfig

def handle_web_search(query: str, config: WebSearchConfig) -> str:
    """
    Tool handler that uses search service.

    This layer adds:
    - Configuration management
    - Execution metadata tracking
    - Fallback logic
    - Result formatting
    """
    # Execute search using service
    if config.search_provider == "tavily":
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
    else:
        results = web_search_service.search_duckduckgo(
            query=query,
            max_results=config.max_results,
            region=config.region,
            safe_search=config.safe_search,
            time_range=config.time_range,
            timeout=config.timeout_seconds,
        )

    # Format results
    formatted = web_search_service.format_results_as_text(
        results=results,
        include_urls=True,
        include_snippets=True,
    )

    return formatted
```

### Integration with Other Services

This service is standalone and doesn't depend on other backend services. Other services can import and use it directly:

```python
from backend.services.search import WebSearchService

class ResearchAgent:
    """Example agent that uses search service."""

    def gather_information(self, topic: str) -> str:
        """Gather information about a topic using web search."""
        # Search for information
        results = WebSearchService.search_tavily(
            query=f"Latest research on {topic}",
            api_key=self.tavily_api_key,
            max_results=10,
            search_depth="advanced",
            include_answer=True,
        )

        # Extract AI answer if available
        if "answer" in results:
            return results["answer"]

        # Otherwise format results
        return WebSearchService.format_results_as_markdown(results)
```

### Dependency Flow

```
┌─────────────────────────────────────┐
│   Agent Execution Layer             │
│   (uses search results)             │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Tool Layer                        │
│   backend/tools/web_search/         │
│   - Adds metadata                   │
│   - Manages configuration           │
│   - Implements fallback             │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Search Service Layer              │
│   backend/services/search/          │
│   - WebSearchService                │
│   - Providers                       │
│   - Formatters                      │
└────────────────┬────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
┌─────▼──────┐      ┌───────▼────────┐
│  Tavily    │      │  DuckDuckGo    │
│  API       │      │  API           │
│  (External)│      │  (External)    │
└────────────┘      └────────────────┘
```

**Services that depend on search:**

- None directly at the service layer
- `backend/tools/web_search/`: Tool implementations
- Agent execution: Uses search tools indirectly

**Services this depends on:**

- None - completely standalone

### Common Integration Patterns

#### Pattern 1: Direct Service Usage

```python
from backend.services.search import WebSearchService

# Direct usage - simplest approach
results = WebSearchService.search_duckduckgo(
    query="machine learning",
    max_results=5,
)

formatted = WebSearchService.format_results_as_text(results)
print(formatted)
```

#### Pattern 2: Provider Fallback

```python
from backend.services.search import WebSearchService
import os

def search_with_automatic_fallback(query: str) -> dict:
    """
    Try Tavily first, automatically fallback to DuckDuckGo.
    Returns dict with 'results' and 'provider' keys.
    """
    api_key = os.environ.get("TAVILY_API_KEY")

    # Try Tavily if configured
    if api_key:
        results = WebSearchService.search_tavily(
            query=query,
            api_key=api_key,
            max_results=10,
        )

        if "error" not in results:
            return {
                "results": results,
                "provider": "tavily",
            }

    # Fallback to DuckDuckGo
    results = WebSearchService.search_duckduckgo(
        query=query,
        max_results=10,
    )

    return {
        "results": results,
        "provider": "duckduckgo",
    }
```

#### Pattern 3: Result Aggregation

```python
from backend.services.search import WebSearchService
import os

def aggregate_search_results(query: str) -> list:
    """
    Aggregate results from multiple providers.
    Deduplicates by URL.
    """
    all_results = []
    seen_urls = set()

    # Get DuckDuckGo results
    ddg_results = WebSearchService.search_duckduckgo(
        query=query,
        max_results=5,
    )

    for result in ddg_results:
        if "error" not in result:
            url = result.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(result)

    # Get Tavily results if available
    api_key = os.environ.get("TAVILY_API_KEY")
    if api_key:
        tavily_results = WebSearchService.search_tavily(
            query=query,
            api_key=api_key,
            max_results=5,
        )

        for result in tavily_results.get("results", []):
            url = result.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(result)

    return all_results
```

#### Pattern 4: Async Wrapper

```python
import asyncio
from typing import Any, Dict, List
from backend.services.search import WebSearchService

async def async_search_duckduckgo(
    query: str,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Async wrapper for DuckDuckGo search.
    Runs in thread pool to avoid blocking event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: WebSearchService.search_duckduckgo(query, **kwargs),
    )

async def async_search_tavily(
    query: str,
    api_key: str,
    **kwargs,
) -> Dict[str, Any]:
    """
    Async wrapper for Tavily search.
    Note: TavilyProvider already handles async contexts internally.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: WebSearchService.search_tavily(query, api_key, **kwargs),
    )

# Usage
async def main():
    results = await async_search_duckduckgo("Python asyncio")
    print(f"Found {len(results)} results")

asyncio.run(main())
```

## Usage Examples

### Example 1: Basic DuckDuckGo Search

Complete end-to-end example of basic web search:

```python
from backend.services.search import WebSearchService

# Step 1: Execute search
results = WebSearchService.search_duckduckgo(
    query="Best Python web frameworks 2024",
    max_results=5,
)

# Step 2: Check for errors
if results and "error" in results[0]:
    print(f"Error: {results[0]['error']}")
    exit(1)

# Step 3: Process results
print(f"Found {len(results)} results:\n")
for i, result in enumerate(results, 1):
    print(f"{i}. {result['title']}")
    print(f"   URL: {result['url']}")
    print(f"   {result['snippet'][:100]}...\n")

# Step 4: Format for display
formatted = WebSearchService.format_results_as_text(
    results=results,
    include_urls=True,
    include_snippets=True,
    max_snippet_length=150,
)

print("\n=== Formatted Output ===")
print(formatted)
```

### Example 2: Advanced Tavily Search with AI Answer

Complete example showing advanced Tavily features:

```python
import os
from backend.services.search import WebSearchService

# Step 1: Set up API key
api_key = os.environ.get("TAVILY_API_KEY")
if not api_key:
    print("Error: TAVILY_API_KEY not set")
    exit(1)

# Step 2: Execute advanced search
query = "What are the key differences between React and Vue.js?"
results = WebSearchService.search_tavily(
    query=query,
    api_key=api_key,
    max_results=10,
    search_depth="advanced",  # More comprehensive
    include_answer=True,      # Get AI summary
    include_raw_content=False,
    include_images=True,
    timeout=20,
)

# Step 3: Check for errors
if "error" in results:
    print(f"Error: {results['error']}")
    exit(1)

# Step 4: Display AI answer
if "answer" in results:
    print("=== AI-Generated Answer ===")
    print(results["answer"])
    print("\n")

# Step 5: Display top results with scores
print("=== Top Results ===")
for result in results.get("results", [])[:5]:
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"Relevance Score: {result['score']:.2f}")
    print(f"Snippet: {result['snippet'][:150]}...")
    print()

# Step 6: Display related images
if "images" in results and results["images"]:
    print(f"=== Related Images ({len(results['images'])} found) ===")
    for img_url in results["images"][:3]:
        print(f"- {img_url}")

# Step 7: Export as markdown
markdown_output = WebSearchService.format_results_as_markdown(
    results=results,
    include_urls=True,
    include_snippets=True,
)

with open("search_results.md", "w") as f:
    f.write(markdown_output)

print("\nResults saved to search_results.md")
```

### Example 3: Image Search Workflow

Show a realistic image search and processing workflow:

```python
from backend.services.search import WebSearchService
import requests
from pathlib import Path

def download_image(url: str, filename: str) -> bool:
    """Download image from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(filename, "wb") as f:
            f.write(response.content)

        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def search_and_download_images(query: str, output_dir: str, max_images: int = 5):
    """
    Search for images and download them.

    Args:
        query: Search query
        output_dir: Directory to save images
        max_images: Maximum number of images to download
    """
    # Step 1: Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 2: Search for images
    print(f"Searching for images: '{query}'")
    images = WebSearchService.search_duckduckgo_images(
        query=query,
        max_results=max_images * 2,  # Get more in case some fail
        size="Large",
        safe_search="strict",
    )

    if not images:
        print("No images found")
        return

    print(f"Found {len(images)} images")

    # Step 3: Download images
    downloaded = 0
    for i, img in enumerate(images):
        if downloaded >= max_images:
            break

        image_url = img.get("image_url")
        if not image_url:
            continue

        # Create filename from position and title
        title_slug = img.get("title", "image").replace(" ", "_")[:30]
        ext = image_url.split(".")[-1].split("?")[0][:4]
        filename = output_path / f"{i+1}_{title_slug}.{ext}"

        print(f"Downloading {i+1}/{max_images}: {img.get('title')}")
        print(f"  Size: {img.get('width')}x{img.get('height')}")
        print(f"  URL: {image_url}")

        if download_image(image_url, str(filename)):
            downloaded += 1
            print(f"  ✓ Saved to {filename}")
        else:
            print(f"  ✗ Download failed")

        print()

    print(f"\nDownloaded {downloaded} images to {output_dir}")

# Usage
search_and_download_images(
    query="Golden Gate Bridge sunset",
    output_dir="./images/golden_gate",
    max_images=5,
)
```

### Example 4: Multi-Provider Research Tool

Show how to build a research tool that leverages multiple providers:

```python
from backend.services.search import WebSearchService
from typing import Dict, List, Any
import os
import json

class ResearchTool:
    """Tool for comprehensive web research using multiple providers."""

    def __init__(self, tavily_api_key: str = None):
        """
        Initialise research tool.

        Args:
            tavily_api_key: Optional Tavily API key (uses env var if not provided)
        """
        self.tavily_api_key = tavily_api_key or os.environ.get("TAVILY_API_KEY")

    def research(
        self,
        query: str,
        use_tavily: bool = True,
        use_duckduckgo: bool = True,
        max_results_per_provider: int = 10,
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive research using available providers.

        Args:
            query: Research query
            use_tavily: Whether to use Tavily (requires API key)
            use_duckduckgo: Whether to use DuckDuckGo
            max_results_per_provider: Max results per provider

        Returns:
            Dictionary with research results and metadata
        """
        research_data = {
            "query": query,
            "providers_used": [],
            "ai_summary": None,
            "results": [],
            "images": [],
            "sources": [],
        }

        # Try Tavily if enabled and configured
        if use_tavily and self.tavily_api_key:
            print(f"Searching with Tavily (advanced mode)...")
            tavily_results = WebSearchService.search_tavily(
                query=query,
                api_key=self.tavily_api_key,
                max_results=max_results_per_provider,
                search_depth="advanced",
                include_answer=True,
                include_images=True,
            )

            if "error" not in tavily_results:
                research_data["providers_used"].append("tavily")
                research_data["ai_summary"] = tavily_results.get("answer")
                research_data["results"].extend(tavily_results.get("results", []))
                research_data["images"].extend(tavily_results.get("images", []))
                print(f"  ✓ Tavily: {len(tavily_results.get('results', []))} results")
            else:
                print(f"  ✗ Tavily failed: {tavily_results['error']}")

        # Try DuckDuckGo if enabled
        if use_duckduckgo:
            print(f"Searching with DuckDuckGo...")
            ddg_results = WebSearchService.search_duckduckgo(
                query=query,
                max_results=max_results_per_provider,
            )

            if ddg_results and "error" not in ddg_results[0]:
                research_data["providers_used"].append("duckduckgo")
                research_data["results"].extend(ddg_results)
                print(f"  ✓ DuckDuckGo: {len(ddg_results)} results")
            else:
                print(f"  ✗ DuckDuckGo failed")

        # Deduplicate results by URL
        seen_urls = set()
        unique_results = []
        for result in research_data["results"]:
            url = result.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
                research_data["sources"].append(url)

        research_data["results"] = unique_results

        return research_data

    def export_report(
        self,
        research_data: Dict[str, Any],
        output_file: str = "research_report.md",
    ):
        """
        Export research data as markdown report.

        Args:
            research_data: Research data from research() method
            output_file: Output file path
        """
        lines = []

        # Title
        lines.append(f"# Research Report: {research_data['query']}\n")

        # Metadata
        lines.append("## Metadata\n")
        lines.append(f"- **Query:** {research_data['query']}")
        lines.append(f"- **Providers:** {', '.join(research_data['providers_used'])}")
        lines.append(f"- **Total Results:** {len(research_data['results'])}")
        lines.append(f"- **Unique Sources:** {len(research_data['sources'])}\n")

        # AI Summary
        if research_data['ai_summary']:
            lines.append("## AI-Generated Summary\n")
            lines.append(research_data['ai_summary'])
            lines.append("\n")

        # Results
        lines.append("## Search Results\n")
        for i, result in enumerate(research_data['results'], 1):
            title = result.get('title', 'No title')
            url = result.get('url', '')
            snippet = result.get('snippet', '')
            score = result.get('score')
            source = result.get('source', 'unknown')

            lines.append(f"### {i}. [{title}]({url})\n")
            if snippet:
                lines.append(f"{snippet}\n")
            lines.append(f"*Source: {source}", end="")
            if score:
                lines.append(f" | Relevance: {score:.2f}", end="")
            lines.append("*\n")
            lines.append("---\n")

        # Images
        if research_data['images']:
            lines.append("## Related Images\n")
            for img_url in research_data['images'][:10]:
                lines.append(f"- {img_url}\n")

        # Write to file
        with open(output_file, "w") as f:
            f.write("\n".join(lines))

        print(f"\nReport exported to {output_file}")

# Usage Example
def main():
    # Initialise research tool
    tool = ResearchTool()

    # Conduct research
    results = tool.research(
        query="Latest advances in quantum computing 2024",
        use_tavily=True,
        use_duckduckgo=True,
        max_results_per_provider=10,
    )

    # Display summary
    print(f"\n=== Research Summary ===")
    print(f"Query: {results['query']}")
    print(f"Providers: {', '.join(results['providers_used'])}")
    print(f"Total unique results: {len(results['results'])}")

    if results['ai_summary']:
        print(f"\n=== AI Summary ===")
        print(results['ai_summary'])

    # Export report
    tool.export_report(results, "quantum_computing_research.md")

    # Save raw data as JSON
    with open("research_data.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nRaw data saved to research_data.json")

if __name__ == "__main__":
    main()
```

## Performance Considerations

### Performance Characteristics

**Search Operations:**

- **DuckDuckGo Search:** O(1) per query - HTTP request time dominates (typically 1-3 seconds)
- **Tavily Search:** O(1) per query - HTTP request time dominates (typically 2-5 seconds for basic, 5-10 seconds for
  advanced)
- **Image Search:** O(1) per query - similar to text search
- **Complexity:** Network-bound, not CPU-bound

**Formatting Operations:**

- **Text Formatting:** O(n) where n is number of results - linear iteration through results
- **Markdown Formatting:** O(n) where n is number of results
- **Memory:** O(n) - stores all results in memory before formatting
- **Complexity:** CPU-bound but typically very fast (<1ms for typical result sets)

**Memory Usage:**

- Minimal - each search result is typically <1KB
- Typical search (5-10 results): <10KB memory
- Advanced search with raw content: Can be 50-500KB depending on page sizes
- No caching - each search makes fresh network requests

**I/O Characteristics:**

- Network-bound for search operations
- CPU-bound for formatting operations
- No disk I/O unless saving formatted results to files

### Optimisation Tips

#### Tip 1: Parallel Multi-Provider Searches

**Problem:**

```python
# Sequential searches - slow
results1 = WebSearchService.search_tavily(query="AI", api_key=key)
results2 = WebSearchService.search_duckduckgo(query="AI")
# Takes: tavily_time + duckduckgo_time
```

**Solution:**

```python
import concurrent.futures

# Parallel searches - fast
def search_all_providers(query: str, api_key: str):
    """Search all providers in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both searches
        tavily_future = executor.submit(
            WebSearchService.search_tavily,
            query=query,
            api_key=api_key,
        )
        ddg_future = executor.submit(
            WebSearchService.search_duckduckgo,
            query=query,
        )

        # Get results
        tavily_results = tavily_future.result()
        ddg_results = ddg_future.result()

    return tavily_results, ddg_results

# Takes: max(tavily_time, duckduckgo_time) - much faster!
```

#### Tip 2: Limit Results Appropriately

**Problem:**

```python
# Requesting too many results
results = WebSearchService.search_tavily(
    query="AI",
    api_key=key,
    max_results=50,  # Often unnecessary
)
# Slower API response, more data to process
```

**Solution:**

```python
# Request only what you need
results = WebSearchService.search_tavily(
    query="AI",
    api_key=key,
    max_results=5,  # Usually sufficient
    search_depth="basic",  # Use basic unless you need advanced
)
# Faster response, less processing
```

#### Tip 3: Conditional Content Fetching

**Problem:**

```python
# Always fetching raw content
results = WebSearchService.search_tavily(
    query="AI",
    api_key=key,
    include_raw_content=True,  # Large payload
    include_images=True,       # More data
    include_answer=True,       # Additional processing
)
# Slower, uses more bandwidth
```

**Solution:**

```python
# Fetch only what you need for the use case
def search_for_quick_answer(query: str, api_key: str):
    """Optimised for quick answers."""
    return WebSearchService.search_tavily(
        query=query,
        api_key=api_key,
        max_results=3,
        search_depth="basic",
        include_answer=True,      # Just the answer
        include_raw_content=False,  # Skip raw content
        include_images=False,     # Skip images
    )

def search_for_deep_research(query: str, api_key: str):
    """Optimised for deep research."""
    return WebSearchService.search_tavily(
        query=query,
        api_key=api_key,
        max_results=10,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,   # Need full content
        include_images=True,
    )
```

#### Tip 4: Efficient Result Formatting

**Problem:**

```python
# Formatting results multiple times
for result in results:
    # Format each result individually - inefficient
    text = WebSearchService.format_results_as_text([result])
    print(text)
```

**Solution:**

```python
# Format all results at once
formatted = WebSearchService.format_results_as_text(
    results=results,
    include_urls=True,
    include_snippets=True,
    max_snippet_length=200,
)
print(formatted)  # Single formatting pass
```

#### Tip 5: Timeout Configuration

**Problem:**

```python
# Default timeout may be too long for time-sensitive operations
results = WebSearchService.search_duckduckgo(
    query="urgent query",
    timeout=10,  # May wait too long
)
```

**Solution:**

```python
# Adjust timeout based on use case
def quick_search(query: str) -> list:
    """Quick search with short timeout."""
    return WebSearchService.search_duckduckgo(
        query=query,
        max_results=3,
        timeout=5,  # Fail fast
    )

def thorough_search(query: str) -> list:
    """Thorough search with longer timeout."""
    return WebSearchService.search_duckduckgo(
        query=query,
        max_results=20,
        timeout=20,  # Allow more time
    )
```

### Async/Await Support

The service uses synchronous methods but handles async contexts internally (Tavily provider):

```python
import asyncio
from backend.services.search import WebSearchService

async def async_example():
    """
    Search service can be called from async contexts.

    Tavily provider automatically detects async context and uses
    thread pool execution to avoid blocking the event loop.
    """
    # This works in async context - Tavily handles it internally
    results = WebSearchService.search_tavily(
        query="async search",
        api_key="your-key",
    )

    return results

# For optimal async performance, wrap in executor
async def optimised_async_search(query: str, api_key: str):
    """Explicitly run in thread pool for async compatibility."""
    loop = asyncio.get_event_loop()

    # Run search in thread pool
    results = await loop.run_in_executor(
        None,
        lambda: WebSearchService.search_tavily(
            query=query,
            api_key=api_key,
        ),
    )

    return results

# Usage
async def main():
    results = await optimised_async_search(
        query="Python asyncio",
        api_key="your-key",
    )
    print(f"Found {len(results.get('results', []))} results")

asyncio.run(main())
```

### Batch Operations

The service doesn't provide built-in batch operations, but you can implement them:

```python
import concurrent.futures
from typing import List, Dict, Any
from backend.services.search import WebSearchService

def batch_search_duckduckgo(
    queries: List[str],
    max_workers: int = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Execute multiple searches in parallel.

    Args:
        queries: List of search queries
        max_workers: Maximum concurrent searches

    Returns:
        Dictionary mapping queries to their results
    """
    results = {}

    def search_single(query: str):
        return query, WebSearchService.search_duckduckgo(
            query=query,
            max_results=5,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(search_single, q) for q in queries]

        for future in concurrent.futures.as_completed(futures):
            query, search_results = future.result()
            results[query] = search_results

    return results

# Usage
queries = [
    "Python web frameworks",
    "JavaScript frameworks",
    "Rust programming",
    "Go programming",
    "TypeScript benefits",
]

batch_results = batch_search_duckduckgo(queries)

for query, results in batch_results.items():
    print(f"\n{query}: {len(results)} results")
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.search import WebSearchService

@pytest.fixture
def mock_ddg_results():
    """Fixture providing mock DuckDuckGo results."""
    return [
        {
            "title": "Test Result 1",
            "url": "https://example.com/1",
            "snippet": "Test snippet 1",
            "position": 1,
            "source": "duckduckgo",
        },
        {
            "title": "Test Result 2",
            "url": "https://example.com/2",
            "snippet": "Test snippet 2",
            "position": 2,
            "source": "duckduckgo",
        },
    ]

@pytest.fixture
def mock_tavily_results():
    """Fixture providing mock Tavily results."""
    return {
        "results": [
            {
                "title": "Tavily Result 1",
                "url": "https://example.com/tavily/1",
                "snippet": "Tavily snippet 1",
                "score": 0.95,
                "position": 1,
            }
        ],
        "answer": "This is an AI-generated answer.",
        "query": "test query",
        "search_depth": "basic",
        "source": "tavily",
    }

def test_search_duckduckgo_success(mock_ddg_results):
    """Test successful DuckDuckGo search."""
    with patch('backend.services.search.providers.duckduckgo.DDGS') as mock_ddgs:
        # Configure mock
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value.text.return_value = [
            {"title": "Test", "href": "https://example.com", "body": "Snippet"}
        ]
        mock_ddgs.return_value = mock_instance

        # Execute search
        results = WebSearchService.search_duckduckgo(
            query="test query",
            max_results=5,
        )

        # Assertions
        assert isinstance(results, list)
        assert len(results) > 0
        assert "title" in results[0]
        assert "url" in results[0]
        assert "snippet" in results[0]

def test_search_tavily_success(mock_tavily_results):
    """Test successful Tavily search."""
    with patch('backend.services.search.providers.tavily.TavilyClient') as mock_client:
        # Configure mock
        mock_instance = mock_client.return_value
        mock_instance.search.return_value = {
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.95,
                }
            ],
            "answer": "AI answer",
        }

        # Execute search
        results = WebSearchService.search_tavily(
            query="test query",
            api_key="test-key",
            include_answer=True,
        )

        # Assertions
        assert isinstance(results, dict)
        assert "results" in results
        assert "answer" in results
        assert results["answer"] == "AI answer"

def test_format_results_as_text(mock_ddg_results):
    """Test text formatting."""
    formatted = WebSearchService.format_results_as_text(
        results=mock_ddg_results,
        include_urls=True,
        include_snippets=True,
    )

    assert isinstance(formatted, str)
    assert "Test Result 1" in formatted
    assert "https://example.com/1" in formatted
    assert "Test snippet 1" in formatted

def test_format_results_as_markdown(mock_tavily_results):
    """Test markdown formatting."""
    formatted = WebSearchService.format_results_as_markdown(
        results=mock_tavily_results,
        include_urls=True,
        include_snippets=True,
    )

    assert isinstance(formatted, str)
    assert "##" in formatted  # Headers
    assert "[" in formatted   # Links
    assert "AI-Generated Answer" in formatted
```

### Mocking Dependencies

```python
from unittest.mock import patch, MagicMock
import pytest
from backend.services.search import WebSearchService

@patch('backend.services.search.providers.duckduckgo.DDGS')
def test_duckduckgo_with_mock(mock_ddgs):
    """Test with mocked DDGS dependency."""
    # Setup mock
    mock_instance = MagicMock()
    mock_instance.__enter__.return_value.text.return_value = [
        {
            "title": "Mocked Result",
            "href": "https://mocked.com",
            "body": "Mocked snippet",
        }
    ]
    mock_ddgs.return_value = mock_instance

    # Execute
    results = WebSearchService.search_duckduckgo(query="test")

    # Verify
    assert len(results) == 1
    assert results[0]["title"] == "Mocked Result"

    # Verify mock was called correctly
    mock_instance.__enter__.return_value.text.assert_called_once()

@patch('backend.services.search.providers.tavily.TavilyClient')
def test_tavily_with_mock(mock_client):
    """Test with mocked Tavily client."""
    # Setup mock
    mock_instance = mock_client.return_value
    mock_instance.search.return_value = {
        "results": [{"title": "Test", "url": "https://test.com", "content": "Test"}],
        "answer": "Mocked answer",
    }

    # Execute
    results = WebSearchService.search_tavily(
        query="test",
        api_key="test-key",
        include_answer=True,
    )

    # Verify
    assert results["answer"] == "Mocked answer"
    mock_instance.search.assert_called_once()

def test_error_handling_missing_api_key():
    """Test error handling when API key is missing."""
    results = WebSearchService.search_tavily(
        query="test",
        api_key="",  # Empty API key
    )

    assert "error" in results
    assert "API key" in results["error"]

@patch('backend.services.search.providers.duckduckgo.DDGS')
def test_error_handling_import_error(mock_ddgs):
    """Test graceful handling of missing duckduckgo-search package."""
    mock_ddgs.side_effect = ImportError("No module named 'duckduckgo_search'")

    results = WebSearchService.search_duckduckgo(query="test")

    assert isinstance(results, list)
    assert "error" in results[0]
    assert "not installed" in results[0]["error"]
```

### Integration Testing

```python
import pytest
import os
from backend.services.search import WebSearchService

@pytest.mark.integration
def test_duckduckgo_integration():
    """Integration test with real DuckDuckGo API."""
    results = WebSearchService.search_duckduckgo(
        query="Python programming",
        max_results=3,
    )

    # Verify real results
    assert isinstance(results, list)
    assert len(results) > 0

    # Check structure
    for result in results:
        assert "title" in result
        assert "url" in result
        assert "snippet" in result
        assert result["source"] == "duckduckgo"

@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("TAVILY_API_KEY"),
    reason="TAVILY_API_KEY not set"
)
def test_tavily_integration():
    """Integration test with real Tavily API."""
    api_key = os.environ.get("TAVILY_API_KEY")

    results = WebSearchService.search_tavily(
        query="Artificial intelligence",
        api_key=api_key,
        max_results=3,
        include_answer=True,
    )

    # Verify real results
    assert isinstance(results, dict)
    assert "results" in results
    assert len(results["results"]) > 0

    # Check for AI answer
    if "answer" in results:
        assert isinstance(results["answer"], str)
        assert len(results["answer"]) > 0

@pytest.mark.integration
def test_formatting_integration():
    """Test formatting with real search results."""
    # Get real results
    results = WebSearchService.search_duckduckgo(
        query="Web development",
        max_results=3,
    )

    # Test text formatting
    text_formatted = WebSearchService.format_results_as_text(results)
    assert isinstance(text_formatted, str)
    assert len(text_formatted) > 0
    assert "Search Results" in text_formatted

    # Test markdown formatting
    md_formatted = WebSearchService.format_results_as_markdown(results)
    assert isinstance(md_formatted, str)
    assert "##" in md_formatted
    assert "[" in md_formatted

@pytest.mark.integration
def test_image_search_integration():
    """Integration test for image search."""
    results = WebSearchService.search_duckduckgo_images(
        query="Python logo",
        max_results=3,
    )

    assert isinstance(results, list)
    if len(results) > 0:  # May return empty in some cases
        for img in results:
            assert "image_url" in img
            assert "title" in img
            assert img["type"] == "image"
```

## Best Practices

### Do's

✅ **Use appropriate provider for the use case**

```python
# For quick, free searches without configuration
results = WebSearchService.search_duckduckgo(query="quick search")

# For AI-optimised results with relevance scoring
results = WebSearchService.search_tavily(
    query="research topic",
    api_key=api_key,
    search_depth="advanced",
    include_answer=True,
)
```

✅ **Always check for errors in results**

```python
results = WebSearchService.search_duckduckgo(query="test")

# Check for errors before processing
if results and isinstance(results, list):
    if "error" in results[0]:
        print(f"Search failed: {results[0]['error']}")
        return

    # Process successful results
    for result in results:
        print(result['title'])
```

✅ **Use appropriate formatting for output context**

```python
# For terminal/log output
text_output = WebSearchService.format_results_as_text(
    results=results,
    include_urls=True,
    max_snippet_length=150,
)
print(text_output)

# For documentation or web display
markdown_output = WebSearchService.format_results_as_markdown(
    results=results,
    include_urls=True,
    include_snippets=True,
)
save_to_file(markdown_output)
```

✅ **Configure timeout based on use case**

```python
# Quick searches - short timeout
quick_results = WebSearchService.search_duckduckgo(
    query="urgent query",
    max_results=3,
    timeout=5,
)

# Deep research - longer timeout
research_results = WebSearchService.search_tavily(
    query="comprehensive research",
    api_key=api_key,
    search_depth="advanced",
    timeout=20,
)
```

✅ **Implement fallback mechanisms**

```python
def search_with_fallback(query: str, api_key: str) -> list:
    """Try Tavily, fallback to DuckDuckGo."""
    if api_key:
        results = WebSearchService.search_tavily(
            query=query,
            api_key=api_key,
        )
        if "error" not in results:
            return results.get("results", [])

    # Fallback
    return WebSearchService.search_duckduckgo(query=query)
```

✅ **Limit results to what you actually need**

```python
# Good - reasonable limit
results = WebSearchService.search_duckduckgo(
    query="topic",
    max_results=5,  # Usually sufficient
)

# Better - adjust based on use case
def quick_lookup(query: str):
    return WebSearchService.search_duckduckgo(
        query=query,
        max_results=3,  # Just need top results
    )

def deep_research(query: str):
    return WebSearchService.search_tavily(
        query=query,
        api_key=api_key,
        max_results=20,  # Need comprehensive results
        search_depth="advanced",
    )
```

### Don'ts

❌ **Don't ignore errors - they're returned in results, not raised**

```python
# Bad - assumes success
results = WebSearchService.search_duckduckgo(query="test")
for result in results:
    print(result['title'])  # May fail if results contain error

# Good - checks for errors
results = WebSearchService.search_duckduckgo(query="test")
if results and "error" not in results[0]:
    for result in results:
        print(result['title'])
else:
    print("Search failed")
```

❌ **Don't hardcode API keys**

```python
# Bad - hardcoded API key
results = WebSearchService.search_tavily(
    query="test",
    api_key="tvly-abc123xyz",  # Security risk!
)

# Good - use environment variables
import os
results = WebSearchService.search_tavily(
    query="test",
    api_key=os.environ.get("TAVILY_API_KEY"),
)
```

❌ **Don't fetch more data than needed**

```python
# Bad - fetching unnecessary data
results = WebSearchService.search_tavily(
    query="quick question",
    api_key=api_key,
    max_results=50,            # Too many
    search_depth="advanced",   # Unnecessary
    include_raw_content=True,  # Not needed
    include_images=True,       # Not needed
)

# Good - only fetch what you need
results = WebSearchService.search_tavily(
    query="quick question",
    api_key=api_key,
    max_results=3,
    search_depth="basic",
    include_answer=True,  # Just the answer
)
```

❌ **Don't perform searches sequentially when they can be parallel**

```python
# Bad - sequential searches
results1 = WebSearchService.search_duckduckgo(query="topic 1")
results2 = WebSearchService.search_duckduckgo(query="topic 2")
results3 = WebSearchService.search_duckduckgo(query="topic 3")

# Good - parallel searches
import concurrent.futures

def parallel_search(queries: list):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(WebSearchService.search_duckduckgo, q)
            for q in queries
        ]
        return [f.result() for f in futures]

results = parallel_search(["topic 1", "topic 2", "topic 3"])
```

❌ **Don't assume result structure without checking**

```python
# Bad - assumes Tavily format for all results
results = some_search_function()
answer = results["answer"]  # May not exist

# Good - check structure
if isinstance(results, dict) and "answer" in results:
    answer = results["answer"]
elif isinstance(results, list) and len(results) > 0:
    # Handle list format
    pass
```

❌ **Don't create service instances unnecessarily**

```python
# Bad - creating instances when not needed
service1 = WebSearchService()
service2 = WebSearchService()
results1 = service1.search_duckduckgo(query="test")
results2 = service2.search_duckduckgo(query="test")

# Good - use static methods or singleton
results1 = WebSearchService.search_duckduckgo(query="test")
results2 = WebSearchService.search_duckduckgo(query="test")

# Or use singleton
from backend.services.search import web_search_service
results1 = web_search_service.search_duckduckgo(query="test")
```

## Related Documentation

### Related Services

- [LLM Models Service](./llm_models.md) - May use search results as context for LLM queries
- [Agent Service](./agent.md) - Agents use search service through tools layer
- [Tools Service](./tools.md) - Wraps search service for agent tool usage

### Related API Modules

- No direct API endpoints - search is integrated through tools layer

### Related Tools

- [Web Search Tool](../../backend/tools/web_search/) - Tool layer implementation that wraps this service

### External Documentation

- [Tavily API Documentation](https://docs.tavily.com) - Tavily search API reference
- [DuckDuckGo Search Documentation](https://github.com/deedy5/duckduckgo_search) - DuckDuckGo search library docs
- [AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html) - Python async/await reference

## Summary

The search service provides a flexible, provider-agnostic interface for web search operations in the AgenticStudio backend.
It abstracts away the complexity of multiple search providers (Tavily AI-optimised search and DuckDuckGo) while offering
flexible formatting options for different output contexts.

The service implements clean separation of concerns through the Strategy pattern for both providers and formatters,
making it easy to add new search engines or output formats without modifying existing code. Error handling is graceful,
with missing dependencies and API failures returning error dictionaries rather than raising exceptions, allowing calling
code to implement appropriate fallback strategies.

**Key Features:**

- **Multiple provider support**: Tavily (AI-optimised, relevance-scored) and DuckDuckGo (free, no API key)
- **Flexible formatting**: Text and markdown formatters for different output contexts
- **AI-generated answers**: Tavily provider can generate LLM-optimised summaries
- **Image search**: Support for image search through DuckDuckGo
- **Async-safe**: Tavily provider automatically handles async contexts
- **Graceful degradation**: Missing dependencies don't crash, they return helpful error messages
- **Static method design**: No instance state, making it thread-safe and simple to use

**Primary Use Cases:**

- Enabling AI agents to search the web for current information
- Research and fact-checking during workflow execution
- Retrieving images and visual content
- Getting AI-generated summaries of search results
- Providing agents with up-to-date information beyond their training data

**When to Use This Service:**

- When agents need to access current web information
- When you need AI-optimised search results with relevance scoring (Tavily)
- When you need free search without API key requirements (DuckDuckGo)
- When you need formatted search results for different output contexts
- When building tools that require web search capabilities
