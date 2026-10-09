# Tools Service Documentation

## Overview

The Tools Service provides comprehensive tool management for the AgenticStudio backend, handling tool creation, lifecycle
management, agent-tool bindings, performance tracking, and caching. It serves as the centralised system for all
tool-related operations in the platform.

**Location:** `backend/services/tools/`

**Primary Responsibilities:**

- Creating and managing tool instances for LLM agents
- Binding tools to agents at compile time for optimal performance
- Tracking tool execution performance and statistics
- Caching tool instances and managing cache lifecycle
- Validating tool configurations before creation
- Extracting input/output data from tool executions

**Key Use Cases:**

- Compile-time tool binding for agent execution
- Dynamic tool creation from configuration
- Performance monitoring and optimisation
- Tool usage analytics and statistics
- Custom tool registration and management

## Architecture

### Module Structure

```
backend/services/tools/
├── __init__.py                 # Public API exports
├── registry.py                 # Central tool registry (primary interface)
├── factory.py                  # Tool factory with caching
├── models.py                   # Data models (ToolMetadata, ToolBinding, etc.)
├── performance.py              # Performance tracking
├── cache.py                    # Tool instance caching
├── validation.py               # Configuration validation
├── extraction_models.py        # Type definitions for extraction
├── creators/                   # Tool creator implementations (Strategy pattern)
│   ├── __init__.py
│   ├── base.py                 # BaseToolCreator and ToolCreator protocol
│   ├── web_search.py           # Web search tool creator
│   ├── database.py             # Database query tool creator
│   ├── file_system.py          # File system tool creator
│   ├── calculation.py          # Calculation tool creator
│   ├── http_request.py         # HTTP request tool creator
│   └── custom.py               # Custom tool creator
└── extractors/                 # Tool execution data extractors
    ├── __init__.py
    ├── base.py                 # BaseExtractor and ExtractionError
    ├── registry.py             # Extractor registry
    ├── structured.py           # Structured tool extractor
    ├── query_based.py          # Query-based tool extractor
    ├── http_request.py         # HTTP request extractor
    └── fallback.py             # Fallback extractor
```

**File Descriptions:**

- **registry.py**: Central registry managing tool metadata, lifecycle, and agent bindings. Main entry point for tool
  operations.
- **factory.py**: Factory for creating tool instances using registered creators, with automatic caching and validation.
- **models.py**: Data models including ToolType enum, ToolMetadata, ToolBinding, ToolCreationConfig, and
  PerformanceStats.
- **performance.py**: Performance tracker for monitoring tool execution metrics and identifying bottlenecks.
- **cache.py**: LRU cache with TTL support for tool instances and results.
- **validation.py**: Configuration validator ensuring tool configs are valid before creation.
- **extraction_models.py**: TypedDict definitions for tool execution data structures.
- **creators/**: Strategy pattern implementation for creating different tool types.
- **extractors/**: Modular system for extracting input/output from tool executions.

### Design Patterns

**1. Singleton Pattern**
The global tool registry ensures a single source of truth for all tool metadata and bindings:

```python
# Global registry instance
_global_registry: Optional[ToolRegistry] = None

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
```

**2. Factory Pattern**
ToolFactory creates tool instances using registered creators:

```python
class ToolFactory:
    def __init__(self):
        self._creators: Dict[str, Any] = {}
        self._register_default_creators()

    def create_tool(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        creator = self._creators[tool_name]
        return creator.create(tool_name, config)
```

**3. Strategy Pattern**
Different creator classes handle different tool types:

```python
class ToolCreator(Protocol):
    def create(self, config: Dict[str, Any]) -> BaseTool: ...
    def get_tool_names(self) -> list[str]: ...

# Implementations: WebSearchCreator, DatabaseCreator, FileSystemCreator, etc.
```

**4. Registry Pattern**
Central registries manage tools and extractors:

```python
class ToolRegistry:
    def __init__(self):
        self._registry: Dict[str, ToolMetadata] = {}
        self._bindings: Dict[str, List[ToolBinding]] = {}

    def register_tool(self, metadata: ToolMetadata) -> None:
        self._registry[metadata.tool_id] = metadata
```

**Component Relationships:**

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Compiler                        │
│                (backend/services/agent)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ uses
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   ToolRegistry                           │
│              (Singleton - Global Instance)               │
├─────────────────────────────────────────────────────────┤
│  • Manages tool metadata                                 │
│  • Binds tools to agents                                 │
│  • Tracks performance                                    │
└──────────┬─────────────────────┬────────────────────────┘
           │ uses                │ uses
           ▼                     ▼
┌──────────────────┐   ┌──────────────────────┐
│   ToolFactory    │   │  PerformanceTracker  │
├──────────────────┤   ├──────────────────────┤
│ • Creates tools  │   │ • Tracks executions  │
│ • Caches tools   │   │ • Collects stats     │
│ • Validates      │   │ • Identifies slow    │
└──────┬───────────┘   └──────────────────────┘
       │ uses
       ▼
┌──────────────────┐   ┌──────────────────┐
│    ToolCache     │   │  Tool Creators   │
├──────────────────┤   ├──────────────────┤
│ • LRU eviction   │◄──│ • WebSearch      │
│ • TTL expiry     │   │ • Database       │
│ • Hit/miss stats │   │ • FileSystem     │
└──────────────────┘   │ • HTTP Request   │
                       │ • Calculation    │
                       │ • Custom         │
                       └──────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.config` - Logger configuration
- `backend.services.llm_models` - LLM model management (indirect, through agent compiler)
- `backend.models.workflow` - Workflow and node data models (indirect)

**External Dependencies:**

- `langchain_core.tools` - BaseTool interface for all tools
- `langchain_core.language_models` - Chat model interfaces
- Standard library: `hashlib`, `json`, `datetime`, `dataclasses`, `enum`, `typing`

**Database Dependencies:**

- None directly (tools may connect to databases via configuration)

**Environment Variables:**
Tool-specific environment variables are documented in tool metadata:

- `DATABASE_URL` - For database query tools (when `requires_auth=True`)
- Tool creators may require additional environment variables based on their implementation

**Configuration:**

- No global configuration file required
- Configuration is done programmatically through ToolMetadata and ToolCreationConfig
- Cache settings configured via ToolFactory constructor parameters

## Public API

### Exported Classes

- `ToolRegistry` - Central registry for managing tools and agent bindings
- `ToolFactory` - Factory for creating tool instances with caching
- `PerformanceTracker` - Performance monitoring for tool executions
- `ToolCache` - LRU cache with TTL for tool instances
- `ConfigValidator` - Configuration validation utilities
- `ToolCreator` - Protocol defining tool creator interface
- `BaseToolCreator` - Base class for tool creator implementations
- `WebSearchCreator` - Creates web search tools (arXiv, Wikipedia, web search)
- `DatabaseCreator` - Creates database query tools
- `FileSystemCreator` - Creates file system tools (read/write)
- `CalculationCreator` - Creates calculation/mathematical tools
- `HttpRequestCreator` - Creates HTTP request tools
- `CustomToolCreator` - Creates custom/user-defined tools
- `BaseExtractor` - Base class for tool data extractors

### Exported Functions

- `get_tool_registry()` - Get the global tool registry singleton instance
- `reset_tool_registry()` - Reset the global tool registry (testing/cleanup)
- `extract_tool_input()` - Extract input data from tool execution
- `extract_tool_output()` - Extract output data from tool execution

### Constants and Configuration

- `ToolType` - Enum of available tool types:
  - `WEB_SEARCH` - Web search and information retrieval tools
  - `DATABASE` - Database query and management tools
  - `FILE_SYSTEM` - File reading and writing tools
  - `API_CALL` - HTTP and API request tools
  - `CALCULATION` - Mathematical computation tools
  - `DELEGATION` - Agent delegation and subworkflow tools
  - `MCP_SERVER` - Model Context Protocol server tools
  - `CUSTOM` - User-defined custom tools

### Data Models

- `ToolMetadata` - Metadata for registered tools (ID, name, type, auth, caching, etc.)
- `ToolBinding` - Agent-tool binding with usage statistics
- `ToolCreationConfig` - Configuration for tool creation
- `PerformanceStats` - Performance statistics for a tool
- `CacheEntry` - Cache entry with TTL and access tracking

### Exceptions

```
Exception
└── ValidationError (tool configuration validation failures)

BaseExtractor defines:
└── ExtractionError (tool data extraction failures)
```

## Core Classes

### `ToolRegistry`

Central registry for all tools in the system, managing tool metadata, lifecycle, agent bindings, and performance
tracking.

**Purpose:** Provide a centralised point for tool management and agent-tool binding at compile time.

**Responsibilities:**

- Register and manage tool metadata
- Bind tools to agents during compilation
- Track tool execution performance
- Manage tool lifecycle and cleanup
- Provide registry-wide statistics

**Initialisation:**

```python
def __init__(self) -> None:
    """
    Initialises the tool registry with:
    - ToolFactory for creating tool instances
    - PerformanceTracker for monitoring executions
    - Empty registries for tools and bindings
    - Pre-registered default tools (web search, database, file system, etc.)
    """
```

**Key Methods:**

#### `register_tool()`

```python
def register_tool(
    self,
    metadata: ToolMetadata,
) -> None:
    """Register a tool in the registry."""
```

**Parameters:**

- `metadata` (ToolMetadata) - Complete tool metadata including ID, name, type, auth requirements, caching settings

**Returns:**

- None

**Example:**

```python
from backend.services.tools import ToolRegistry, ToolMetadata, ToolType

registry = ToolRegistry()
metadata = ToolMetadata(
    tool_id="custom_search",
    name="Custom Search Engine",
    description="Search a custom database",
    tool_type=ToolType.WEB_SEARCH,
    cache_results=True,
    cache_ttl=600,
)
registry.register_tool(metadata)
```

**Behaviour:**

- Stores metadata in internal registry dictionary
- Logs registration event
- Metadata is immutable after registration

#### `bind_tools_for_agent()`

```python
def bind_tools_for_agent(
    self,
    agent_id: str,
    agent_name: str,
    tool_configs: List[Union[str, Any]],
    agent_config: Optional[Any] = None,
) -> List[ToolBinding]:
    """Bind tools to an agent at compile time."""
```

**Parameters:**

- `agent_id` (str) - Unique agent identifier
- `agent_name` (str) - Human-readable agent name
- `tool_configs` (List[Union[str, Any]]) - List of tool names (strings) or ToolConfig objects
- `agent_config` (Optional[Any]) - Optional agent configuration for context

**Returns:**

- `List[ToolBinding]` - List of created tool bindings with metadata

**Raises:**

- Logs warnings if tool creation fails (does not raise)

**Example:**

```python
from backend.services.tools import get_tool_registry

registry = get_tool_registry()
bindings = registry.bind_tools_for_agent(
    agent_id="research-agent-001",
    agent_name="Research Assistant",
    tool_configs=["web_search", "arxiv", "calculator"],
)

# Returns list of ToolBinding objects
for binding in bindings:
    print(f"Bound {binding.tool_id} to {binding.agent_name}")
```

**Behaviour:**

- Creates tool instances using ToolFactory
- Registers metadata if not already present
- Stores bindings in internal dictionary keyed by agent_id
- Initialises performance tracking counters
- Logs each successful binding

**Use Cases:**

- Agent compilation: Bind tools to agents during compile-time
- Dynamic agent creation: Add tools to agents based on configuration
- Testing: Set up agents with specific tool configurations

#### `get_agent_tools()`

```python
def get_agent_tools(
    self,
    agent_id: str,
) -> List[BaseTool]:
    """Get tool instances for an agent."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier

**Returns:**

- `List[BaseTool]` - List of LangChain BaseTool instances ready for use

**Example:**

```python
registry = get_tool_registry()
tools = registry.get_agent_tools("research-agent-001")

# Use tools with LangChain agent
from langchain.agents import create_react_agent
agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
```

**Behaviour:**

- Retrieves bindings for the specified agent
- Extracts tool instances from bindings
- Returns empty list if agent has no bindings

**Use Cases:**

- Agent execution: Retrieve tools for runtime execution
- Inspection: Check which tools an agent has access to
- Debugging: Verify tool bindings are correct

#### `track_tool_execution()`

```python
def track_tool_execution(
    self,
    agent_id: str,
    tool_id: str,
    execution_time: float,
    success: bool = True,
) -> None:
    """Track tool execution for performance monitoring."""
```

**Parameters:**

- `agent_id` (str) - Agent that executed the tool
- `tool_id` (str) - Tool that was executed
- `execution_time` (float) - Time taken in seconds
- `success` (bool) - Whether execution succeeded (default: True)

**Returns:**

- None

**Example:**

```python
import time
from backend.services.tools import get_tool_registry

registry = get_tool_registry()

# Execute tool and track performance
start_time = time.time()
try:
    result = tool.invoke({"query": "machine learning"})
    execution_time = time.time() - start_time
    registry.track_tool_execution(
        agent_id="research-agent-001",
        tool_id="web_search",
        execution_time=execution_time,
        success=True,
    )
except Exception as e:
    execution_time = time.time() - start_time
    registry.track_tool_execution(
        agent_id="research-agent-001",
        tool_id="web_search",
        execution_time=execution_time,
        success=False,
    )
```

**Behaviour:**

- Updates binding-level statistics (execution count, total time, error count)
- Updates global performance statistics via PerformanceTracker
- Logs slow executions (> 5 seconds) and failures

**Use Cases:**

- Performance monitoring: Track how long tools take to execute
- Error tracking: Identify tools with high failure rates
- Optimisation: Find bottlenecks in agent execution

#### `get_performance_stats()`

```python
def get_performance_stats(
    self,
    tool_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get performance statistics for tools."""
```

**Parameters:**

- `tool_id` (Optional[str]) - Specific tool ID, or None for all tools

**Returns:**

- `Dict[str, Any]` - Performance statistics dictionary

**Example:**

```python
from backend.services.tools import get_tool_registry

registry = get_tool_registry()

# Get stats for specific tool
web_search_stats = registry.get_performance_stats("web_search")
print(f"Average execution time: {web_search_stats['avg_time']:.2f}s")
print(f"Total executions: {web_search_stats['total_executions']}")
print(f"Error rate: {web_search_stats['error_rate']:.2%}")

# Get all statistics
all_stats = registry.get_performance_stats()
for tool_id, stats in all_stats.items():
    print(f"{tool_id}: {stats['avg_time']:.2f}s avg")
```

**Behaviour:**

- Delegates to PerformanceTracker
- Returns aggregated statistics across all executions
- Returns empty dict if tool not found

**Use Cases:**

- Monitoring dashboards: Display tool performance metrics
- Optimisation: Identify slow or error-prone tools
- Reporting: Generate performance reports

#### `optimize_bindings()`

```python
def optimize_bindings(
    self,
    agent_id: str,
) -> None:
    """Optimise tool bindings based on usage patterns."""
```

**Parameters:**

- `agent_id` (str) - Agent to optimise

**Returns:**

- None

**Example:**

```python
from backend.services.tools import get_tool_registry

registry = get_tool_registry()

# After agent has executed for a while
registry.optimize_bindings("research-agent-001")

# Now tools are reordered by execution frequency for better performance
```

**Behaviour:**

- Reorders bindings by execution count (most used first)
- Improves performance by putting frequently used tools at the front
- Logs optimisation event

**Use Cases:**

- Runtime optimisation: Periodically optimise long-running agents
- Performance tuning: Ensure most-used tools are checked first

#### `get_registry_stats()`

```python
def get_registry_stats(self) -> Dict[str, Any]:
    """Get overall registry statistics."""
```

**Parameters:**

- None

**Returns:**

- `Dict[str, Any]` - Dictionary containing:
  - `total_tools`: Number of registered tools
  - `total_bindings`: Total bindings across all agents
  - `total_agents`: Number of agents with bindings
  - `total_executions`: Total tool executions tracked
  - `cache_stats`: Cache hit rate and statistics
  - `performance_summary`: Aggregated performance metrics

**Example:**

```python
from backend.services.tools import get_tool_registry

registry = get_tool_registry()
stats = registry.get_registry_stats()

print(f"Total tools: {stats['total_tools']}")
print(f"Total agents: {stats['total_agents']}")
print(f"Cache hit rate: {stats['cache_stats']['hit_rate']:.2%}")
print(f"Average execution time: {stats['performance_summary']['average_execution_time']:.2f}s")
```

**Behaviour:**

- Aggregates data from registry, factory, and performance tracker
- Provides comprehensive overview of system state
- Useful for monitoring and debugging

**Use Cases:**

- System health monitoring: Check overall tool system status
- Debugging: Verify registry state during development
- Metrics: Export for monitoring dashboards

**Class Attributes:**

- `factory: ToolFactory` - Factory instance for creating tools
- `performance_tracker: PerformanceTracker` - Tracker for performance metrics

### `ToolFactory`

Factory for creating tool instances with caching, validation, and support for multiple creator strategies.

**Purpose:** Centralised tool creation with automatic caching and validation to improve performance and ensure
consistency.

**Responsibilities:**

- Create tool instances from configuration
- Cache created tools to avoid redundant instantiation
- Validate configurations before tool creation
- Manage tool creator registrations
- Provide cache statistics

**Initialisation:**

```python
def __init__(
    self,
    enable_cache: bool = True,
    cache_ttl: int = 300,
) -> None:
    """
    Args:
        enable_cache: Whether to enable tool instance caching (default: True)
        cache_ttl: Cache time-to-live in seconds (default: 300)
    """
```

**Key Methods:**

#### `create_tool()`

```python
def create_tool(
    self,
    tool_name: str,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[BaseTool]:
    """Create a tool instance with caching and validation."""
```

**Parameters:**

- `tool_name` (str) - Name of the tool to create (e.g., "web_search", "calculator")
- `config` (Optional[Dict[str, Any]]) - Tool-specific configuration parameters

**Returns:**

- `Optional[BaseTool]` - Tool instance, or None if creation fails

**Example:**

```python
from backend.services.tools import ToolFactory

factory = ToolFactory()

# Create simple tool without config
calculator = factory.create_tool("calculator")

# Create tool with configuration
web_search = factory.create_tool(
    "web_search",
    config={"max_results": 10, "timeout": 30},
)

# Create database tool
database_tool = factory.create_tool(
    "database_query",
    config={
        "connection_string": "postgresql://localhost/mydb",
        "max_retries": 3,
    },
)
```

**Behaviour:**

- Checks cache first using hash of tool_name + config
- Validates configuration using ConfigValidator
- Attempts creation using registered creator for tool_name
- Falls back to custom creation function if registered
- Falls back to custom tool creator for connected nodes
- Caches successful creations
- Logs all creation attempts and failures

**Use Cases:**

- Agent compilation: Create tools during agent compilation
- Dynamic tool creation: Create tools on-demand from user configuration
- Testing: Create tool instances for testing

#### `register_custom_tool()`

```python
def register_custom_tool(
    self,
    name: str,
    creation_func: Callable,
) -> None:
    """Register a custom tool creation function."""
```

**Parameters:**

- `name` (str) - Tool name for registration
- `creation_func` (Callable) - Function that creates the tool from config

**Returns:**

- None

**Example:**

```python
from backend.services.tools import ToolFactory
from langchain_core.tools import Tool

def create_my_custom_tool(config: Dict[str, Any]) -> Tool:
    """Custom tool creation function."""
    return Tool(
        name="my_custom_tool",
        description=config.get("description", "My custom tool"),
        func=lambda x: f"Processed: {x}",
    )

factory = ToolFactory()
factory.register_custom_tool("my_custom_tool", create_my_custom_tool)

# Now can create using factory
tool = factory.create_tool("my_custom_tool", {"description": "Custom processor"})
```

**Behaviour:**

- Stores creation function in internal dictionary
- Logs registration event
- Function is called during create_tool if tool_name matches

**Use Cases:**

- Plugin systems: Allow plugins to register custom tools
- Testing: Register mock tools for testing
- Extensions: Add domain-specific tools without modifying core code

#### `clear_cache()`

```python
def clear_cache(self) -> None:
    """Clear the tool cache."""
```

**Parameters:**

- None

**Returns:**

- None

**Example:**

```python
from backend.services.tools import ToolFactory

factory = ToolFactory()

# After configuration changes or for testing
factory.clear_cache()

# Next create_tool call will rebuild from scratch
```

**Behaviour:**

- Clears all cached tool instances
- Logs cache clear event
- Does nothing if caching is disabled

**Use Cases:**

- Testing: Clear cache between tests
- Configuration updates: Force recreation after config changes
- Memory management: Free cached tool instances

#### `get_cache_stats()`

```python
def get_cache_stats(self) -> Optional[Dict[str, Any]]:
    """Get cache statistics."""
```

**Parameters:**

- None

**Returns:**

- `Optional[Dict[str, Any]]` - Cache statistics or None if caching disabled

**Example:**

```python
from backend.services.tools import ToolFactory

factory = ToolFactory()
stats = factory.get_cache_stats()

if stats:
    print(f"Cache size: {stats['size']}/{stats['max_size']}")
    print(f"Hit rate: {stats['hit_rate']:.2%}")
    print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
    print(f"Evictions: {stats['evictions']}")
```

**Behaviour:**

- Returns statistics from ToolCache
- Returns None if caching is disabled

**Use Cases:**

- Performance monitoring: Track cache effectiveness
- Tuning: Adjust cache size based on hit rates
- Debugging: Verify cache behaviour

#### `get_supported_tools()`

```python
def get_supported_tools(self) -> list[str]:
    """Get list of all supported tool names."""
```

**Parameters:**

- None

**Returns:**

- `list[str]` - Sorted list of all supported tool names

**Example:**

```python
from backend.services.tools import ToolFactory

factory = ToolFactory()
supported = factory.get_supported_tools()

print("Supported tools:")
for tool_name in supported:
    print(f"  - {tool_name}")
```

**Behaviour:**

- Combines tool names from all registered creators
- Includes custom registered tools
- Returns sorted, deduplicated list

**Use Cases:**

- UI generation: Display available tools to users
- Validation: Check if a tool name is valid
- Documentation: List available tools

**Properties:**

- None

### `PerformanceTracker`

Tracks performance metrics for tool executions across the system.

**Purpose:** Monitor tool execution performance to identify slow tools, bottlenecks, and error-prone operations.

**Responsibilities:**

- Track individual tool executions
- Maintain aggregated statistics per tool
- Identify performance outliers
- Provide performance summaries and reports

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the performance tracker with empty statistics."""
```

**Key Methods:**

#### `track_execution()`

```python
def track_execution(
    self,
    tool_id: str,
    execution_time: float,
    success: bool = True,
) -> None:
    """Track a single tool execution."""
```

**Parameters:**

- `tool_id` (str) - Tool identifier
- `execution_time` (float) - Execution time in seconds
- `success` (bool) - Whether execution succeeded (default: True)

**Returns:**

- None

**Example:**

```python
from backend.services.tools import PerformanceTracker
import time

tracker = PerformanceTracker()

# Track successful execution
start = time.time()
# ... tool execution ...
elapsed = time.time() - start
tracker.track_execution("web_search", elapsed, success=True)

# Track failed execution
tracker.track_execution("database_query", 0.5, success=False)
```

**Behaviour:**

- Initialises PerformanceStats if first execution for tool
- Updates min/max/average execution time
- Increments error count if failed
- Logs warnings for slow executions (> 5 seconds) or failures

#### `get_summary()`

```python
def get_summary(self) -> Dict[str, Any]:
    """Get overall performance summary."""
```

**Parameters:**

- None

**Returns:**

- `Dict[str, Any]` - Summary containing:
  - `total_tools_tracked`: Number of tools with statistics
  - `total_executions`: Total executions across all tools
  - `total_errors`: Total errors across all tools
  - `error_rate`: Overall error rate (0.0 to 1.0)
  - `average_execution_time`: Average time across all executions
  - `total_execution_time`: Cumulative execution time

**Example:**

```python
from backend.services.tools import PerformanceTracker

tracker = PerformanceTracker()
# ... after tracking many executions ...

summary = tracker.get_summary()
print(f"Tracked {summary['total_tools_tracked']} tools")
print(f"Total executions: {summary['total_executions']}")
print(f"Error rate: {summary['error_rate']:.2%}")
print(f"Average time: {summary['average_execution_time']:.2f}s")
```

**Behaviour:**

- Aggregates data from all tracked tools
- Returns zeroed summary if no executions tracked

**Use Cases:**

- Monitoring dashboards: Display system-wide performance
- Health checks: Verify system performance is acceptable
- Reports: Generate performance reports

#### `get_top_performers()`

```python
def get_top_performers(
    self,
    limit: int = 10,
) -> list[Dict[str, Any]]:
    """Get top performing tools by execution count."""
```

**Parameters:**

- `limit` (int) - Maximum number of tools to return (default: 10)

**Returns:**

- `list[Dict[str, Any]]` - List of tool statistics, sorted by execution count descending

**Example:**

```python
from backend.services.tools import PerformanceTracker

tracker = PerformanceTracker()
top_tools = tracker.get_top_performers(limit=5)

print("Most used tools:")
for i, stats in enumerate(top_tools, 1):
    print(f"{i}. {stats['tool_id']}: {stats['total_executions']} executions")
```

**Behaviour:**

- Sorts tools by total executions
- Returns top N tools
- Each entry includes full PerformanceStats data

**Use Cases:**

- Optimisation: Focus on optimising most-used tools
- Analytics: Understand which tools are most popular
- Capacity planning: Identify high-traffic tools

#### `get_slowest_tools()`

```python
def get_slowest_tools(
    self,
    limit: int = 10,
) -> list[Dict[str, Any]]:
    """Get slowest tools by average execution time."""
```

**Parameters:**

- `limit` (int) - Maximum number of tools to return (default: 10)

**Returns:**

- `list[Dict[str, Any]]` - List of tool statistics, sorted by average time descending

**Example:**

```python
from backend.services.tools import PerformanceTracker

tracker = PerformanceTracker()
slow_tools = tracker.get_slowest_tools(limit=5)

print("Slowest tools:")
for stats in slow_tools:
    print(f"{stats['tool_id']}: {stats['avg_time']:.2f}s average")
```

**Behaviour:**

- Sorts tools by average execution time
- Returns slowest N tools
- Useful for identifying performance bottlenecks

**Use Cases:**

- Performance tuning: Identify tools that need optimisation
- Debugging: Find unexpected slow operations
- Monitoring: Alert on slow tools

#### `get_error_prone_tools()`

```python
def get_error_prone_tools(
    self,
    limit: int = 10,
) -> list[Dict[str, Any]]:
    """Get tools with highest error rates."""
```

**Parameters:**

- `limit` (int) - Maximum number of tools to return (default: 10)

**Returns:**

- `list[Dict[str, Any]]` - List of tool statistics, sorted by error count descending

**Example:**

```python
from backend.services.tools import PerformanceTracker

tracker = PerformanceTracker()
error_prone = tracker.get_error_prone_tools(limit=5)

print("Tools with most errors:")
for stats in error_prone:
    error_rate = stats['error_count'] / stats['total_executions']
    print(f"{stats['tool_id']}: {stats['error_count']} errors ({error_rate:.1%})")
```

**Behaviour:**

- Filters to tools with at least one error
- Sorts by error count
- Returns top N error-prone tools

**Use Cases:**

- Reliability monitoring: Identify unreliable tools
- Debugging: Find tools that frequently fail
- Alerting: Trigger alerts for high error rates

**Properties:**

- None

### `ToolCache`

LRU cache with TTL support for tool instances and results.

**Purpose:** Improve performance by caching tool instances and avoiding redundant creation.

**Responsibilities:**

- Cache tool instances with configurable TTL
- Implement LRU eviction when cache is full
- Track cache hit/miss statistics
- Clean up expired entries automatically

**Initialisation:**

```python
def __init__(
    self,
    max_size: int = 128,
    default_ttl: int = 300,
) -> None:
    """
    Args:
        max_size: Maximum number of entries (0 for unlimited) (default: 128)
        default_ttl: Default TTL in seconds (0 for no expiration) (default: 300)
    """
```

**Key Methods:**

#### `generate_key()`

```python
def generate_key(
    self,
    tool_name: str,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a cache key from tool name and configuration."""
```

**Parameters:**

- `tool_name` (str) - Name of the tool
- `config` (Optional[Dict[str, Any]]) - Optional configuration dictionary

**Returns:**

- `str` - MD5 hash of tool_name + config (as cache key)

**Example:**

```python
from backend.services.tools import ToolCache

cache = ToolCache()

# Generate cache keys
key1 = cache.generate_key("web_search", {"max_results": 10})
key2 = cache.generate_key("web_search", {"max_results": 20})
# key1 != key2 because configs differ

key3 = cache.generate_key("calculator")
# Different tool = different key
```

**Behaviour:**

- Serialises config to sorted JSON for consistency
- Computes MD5 hash for compact key
- Same tool_name + config always produces same key

**Use Cases:**

- Internal caching: Used internally by get/set
- Testing: Verify cache key generation
- Debugging: Understand cache behaviour

#### `get()`

```python
def get(
    self,
    key: str,
) -> Optional[Any]:
    """Get a value from the cache."""
```

**Parameters:**

- `key` (str) - Cache key

**Returns:**

- `Optional[Any]` - Cached value, or None if not found or expired

**Example:**

```python
from backend.services.tools import ToolCache

cache = ToolCache()
key = cache.generate_key("web_search", {"max_results": 10})

# Try to get from cache
tool = cache.get(key)
if tool is None:
    # Cache miss - create tool
    tool = create_web_search_tool({"max_results": 10})
    cache.set(key, tool)
```

**Behaviour:**

- Returns None if key not in cache (miss)
- Checks expiration and removes if expired (miss)
- Marks entry as accessed (updates LRU)
- Increments hit/miss counters
- Logs cache events at debug level

**Use Cases:**

- Tool creation: Check cache before creating tool
- Testing: Verify caching behaviour
- Debugging: Understand cache hits/misses

#### `set()`

```python
def set(
    self,
    key: str,
    value: Any,
    ttl: Optional[int] = None,
) -> None:
    """Set a value in the cache."""
```

**Parameters:**

- `key` (str) - Cache key
- `value` (Any) - Value to cache
- `ttl` (Optional[int]) - Optional TTL override (uses default if not specified)

**Returns:**

- None

**Example:**

```python
from backend.services.tools import ToolCache

cache = ToolCache(default_ttl=300)

# Cache with default TTL (300s)
cache.set(key, tool)

# Cache with custom TTL (600s)
cache.set(key, tool, ttl=600)

# Cache with no expiration
cache.set(key, tool, ttl=0)
```

**Behaviour:**

- Evicts LRU entry if cache is full
- Creates new CacheEntry with specified TTL
- Stores in internal dictionary
- Logs cache events at debug level

**Use Cases:**

- Tool creation: Cache newly created tools
- Testing: Populate cache for tests
- Performance: Store expensive-to-create objects

#### `cleanup_expired()`

```python
def cleanup_expired(self) -> int:
    """Remove all expired entries."""
```

**Parameters:**

- None

**Returns:**

- `int` - Number of entries removed

**Example:**

```python
from backend.services.tools import ToolCache

cache = ToolCache()

# Periodically clean up expired entries
removed = cache.cleanup_expired()
print(f"Removed {removed} expired entries")
```

**Behaviour:**

- Iterates through all entries
- Removes expired entries
- Updates expiration statistics
- Logs cleanup event

**Use Cases:**

- Maintenance: Periodic cleanup of expired entries
- Memory management: Free expired entries
- Testing: Verify expiration behaviour

#### `get_stats()`

```python
def get_stats(self) -> Dict[str, Any]:
    """Get cache statistics."""
```

**Parameters:**

- None

**Returns:**

- `Dict[str, Any]` - Statistics dictionary containing:
  - `size`: Current number of cached entries
  - `max_size`: Maximum cache size
  - `hits`: Number of cache hits
  - `misses`: Number of cache misses
  - `hit_rate`: Hit rate (0.0 to 1.0)
  - `evictions`: Number of LRU evictions
  - `expirations`: Number of expired entries removed
  - `total_requests`: Total get requests

**Example:**

```python
from backend.services.tools import ToolCache

cache = ToolCache()
stats = cache.get_stats()

print(f"Cache size: {stats['size']}/{stats['max_size']}")
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Evictions: {stats['evictions']}")
```

**Behaviour:**

- Computes statistics from internal counters
- Calculates hit rate on-demand
- Returns current state

**Use Cases:**

- Monitoring: Track cache effectiveness
- Tuning: Adjust cache size based on metrics
- Debugging: Understand cache behaviour

**Properties:**

- None

### `ConfigValidator`

Validates tool configurations before creation to ensure correctness and prevent errors.

**Purpose:** Provide robust validation of tool configurations to catch errors early and improve error messages.

**Responsibilities:**

- Validate required configuration keys
- Validate value types
- Validate numeric ranges
- Validate allowed choices
- Provide clear error messages

**Initialisation:**
Static class - no initialisation required.

**Key Methods:**

All methods are static and can be called without instantiating the class.

#### `validate_config()`

```python
@staticmethod
def validate_config(
    tool_name: str,
    config: Dict[str, Any],
) -> bool:
    """Perform general validation on tool configuration."""
```

**Parameters:**

- `tool_name` (str) - Name of the tool (for error messages)
- `config` (Dict[str, Any]) - Configuration to validate

**Returns:**

- `bool` - True if valid

**Raises:**

- `ValidationError` - If configuration is invalid

**Example:**

```python
from backend.services.tools import ConfigValidator, ValidationError

try:
    ConfigValidator.validate_config("web_search", {
        "max_results": 10,
        "timeout": 30,
    })
    # Valid - proceed with creation
except ValidationError as e:
    print(f"Invalid configuration: {e}")
```

**Behaviour:**

- Validates config is a dictionary
- Validates common parameters (timeout, max_retries)
- Logs validation events

**Use Cases:**

- Tool creation: Validate before attempting creation
- API validation: Validate user-provided configurations
- Testing: Verify configuration validity

#### `validate_required_keys()`

```python
@staticmethod
def validate_required_keys(
    config: Dict[str, Any],
    required_keys: List[str],
    tool_name: str,
) -> None:
    """Validate that all required keys are present in configuration."""
```

**Parameters:**

- `config` (Dict[str, Any]) - Configuration dictionary to validate
- `required_keys` (List[str]) - List of required key names
- `tool_name` (str) - Name of the tool (for error messages)

**Returns:**

- None

**Raises:**

- `ValidationError` - If any required keys are missing

**Example:**

```python
from backend.services.tools import ConfigValidator, ValidationError

config = {"url": "https://api.example.com"}

try:
    ConfigValidator.validate_required_keys(
        config,
        required_keys=["url", "api_key"],
        tool_name="api_client",
    )
except ValidationError as e:
    print(e)  # "Tool 'api_client' missing required configuration keys: api_key"
```

**Behaviour:**

- Checks each required key is present
- Collects all missing keys
- Raises single error with all missing keys listed

**Use Cases:**

- Custom tool creation: Validate required parameters
- Configuration validation: Ensure completeness
- Error prevention: Catch missing params early

#### `validate_type()`

```python
@staticmethod
def validate_type(
    config: Dict[str, Any],
    key: str,
    expected_type: type,
    tool_name: str,
) -> None:
    """Validate that a configuration value has the expected type."""
```

**Parameters:**

- `config` (Dict[str, Any]) - Configuration dictionary
- `key` (str) - Key to validate
- `expected_type` (type) - Expected Python type
- `tool_name` (str) - Name of the tool (for error messages)

**Returns:**

- None

**Raises:**

- `ValidationError` - If type doesn't match

**Example:**

```python
from backend.services.tools import ConfigValidator, ValidationError

config = {"max_results": "10"}  # Wrong type (string instead of int)

try:
    ConfigValidator.validate_type(
        config,
        key="max_results",
        expected_type=int,
        tool_name="web_search",
    )
except ValidationError as e:
    print(e)  # "Tool 'web_search' config key 'max_results' must be int, got str"
```

**Behaviour:**

- Skips validation if key not present
- Checks type using isinstance
- Raises error with clear message including actual and expected types

**Use Cases:**

- Type safety: Ensure configuration values have correct types
- Error prevention: Catch type errors before tool creation
- Testing: Verify type constraints

#### `validate_range()`

```python
@staticmethod
def validate_range(
    config: Dict[str, Any],
    key: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    tool_name: str = "",
) -> None:
    """Validate that a numeric value is within a specified range."""
```

**Parameters:**

- `config` (Dict[str, Any]) - Configuration dictionary
- `key` (str) - Key to validate
- `min_value` (Optional[float]) - Minimum allowed value (inclusive)
- `max_value` (Optional[float]) - Maximum allowed value (inclusive)
- `tool_name` (str) - Name of the tool (for error messages)

**Returns:**

- None

**Raises:**

- `ValidationError` - If value is out of range or not numeric

**Example:**

```python
from backend.services.tools import ConfigValidator, ValidationError

config = {"timeout": 700}

try:
    ConfigValidator.validate_range(
        config,
        key="timeout",
        min_value=1,
        max_value=600,
        tool_name="http_request",
    )
except ValidationError as e:
    print(e)  # "Tool 'http_request' config key 'timeout' must be <= 600, got 700"
```

**Behaviour:**

- Skips validation if key not present
- Validates value is numeric (int or float)
- Validates min_value if specified
- Validates max_value if specified

**Use Cases:**

- Parameter validation: Ensure values are in acceptable ranges
- Safety: Prevent unreasonable values (e.g., negative timeouts)
- API validation: Validate user input

#### `validate_choices()`

```python
@staticmethod
def validate_choices(
    config: Dict[str, Any],
    key: str,
    choices: List[Any],
    tool_name: str = "",
) -> None:
    """Validate that a value is one of a set of allowed choices."""
```

**Parameters:**

- `config` (Dict[str, Any]) - Configuration dictionary
- `key` (str) - Key to validate
- `choices` (List[Any]) - List of allowed values
- `tool_name` (str) - Name of the tool (for error messages)

**Returns:**

- None

**Raises:**

- `ValidationError` - If value is not in choices

**Example:**

```python
from backend.services.tools import ConfigValidator, ValidationError

config = {"method": "PATCH"}

try:
    ConfigValidator.validate_choices(
        config,
        key="method",
        choices=["GET", "POST", "PUT", "DELETE"],
        tool_name="http_request",
    )
except ValidationError as e:
    print(e)  # "Tool 'http_request' config key 'method' must be one of ['GET', 'POST', 'PUT', 'DELETE'], got 'PATCH'"
```

**Behaviour:**

- Skips validation if key not present
- Checks value is in allowed choices
- Raises error with clear message showing allowed values

**Use Cases:**

- Enum validation: Validate enum-like parameters
- API validation: Ensure valid parameter values
- Error prevention: Catch invalid choices early

**Properties:**

- None (static class)

## Functions

### `get_tool_registry()`

Get the global tool registry singleton instance.

**Signature:**

```python
def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Creates the registry on first call and returns the same
    instance on subsequent calls (Singleton pattern).
    """
```

**Parameters:**

- None

**Returns:**

- `ToolRegistry` - Global registry instance

**Example:**

```python
from backend.services.tools import get_tool_registry

# Get registry anywhere in the application
registry = get_tool_registry()

# Always returns the same instance
registry2 = get_tool_registry()
assert registry is registry2  # True
```

**Use Cases:**

- Application initialisation: Get registry to bind tools
- Agent compilation: Access registry during compilation
- Tool management: Register or query tools globally

### `reset_tool_registry()`

Reset the global tool registry, clearing all bindings and cache.

**Signature:**

```python
def reset_tool_registry() -> None:
    """
    Reset the global tool registry.

    Clears all tool bindings and factory cache.
    Next call to get_tool_registry() will create a fresh instance.
    """
```

**Parameters:**

- None

**Returns:**

- None

**Example:**

```python
from backend.services.tools import get_tool_registry, reset_tool_registry

# Use registry
registry = get_tool_registry()
registry.bind_tools_for_agent("agent-1", "Agent", ["web_search"])

# Reset for testing or cleanup
reset_tool_registry()

# Next call creates new instance
new_registry = get_tool_registry()
# Bindings from previous instance are gone
```

**Use Cases:**

- Testing: Reset state between tests
- Cleanup: Clear registry during shutdown
- Debugging: Start fresh during development

### `extract_tool_input()`

Extract input data from a tool execution based on the tool name.

**Signature:**

```python
def extract_tool_input(
    tool_name: str,
    tool_exec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract input data from a tool execution.

    Uses the extractor registry to find the appropriate extractor
    for the given tool name and delegates extraction.

    Returns empty dict on any error (safe fallback).
    """
```

**Parameters:**

- `tool_name` (str) - The name of the tool being executed
- `tool_exec` (Dict[str, Any]) - The tool execution data dictionary

**Returns:**

- `Dict[str, Any]` - Dictionary containing extracted input data (empty dict if extraction fails)

**Raises:**

- Does not raise (returns empty dict on error)

**Example:**

```python
from backend.services.tools import extract_tool_input

# Extract from web search execution
tool_exec = {
    "tool": "web_search",
    "kwargs": {"query": "machine learning tutorials", "max_results": 5},
}
input_data = extract_tool_input("web_search", tool_exec)
# Returns: {"query": "machine learning tutorials", "max_results": 5}

# Extract from HTTP request
tool_exec = {
    "tool": "http_request",
    "request": {
        "url": "https://api.example.com/data",
        "method": "GET",
        "headers": {"Authorization": "Bearer token"},
    },
}
input_data = extract_tool_input("http_request", tool_exec)
# Returns: {"url": "https://api.example.com/data", "method": "GET", ...}
```

**Use Cases:**

- Execution logging: Extract inputs for logging tool executions
- Debugging: Inspect what inputs were passed to tools
- Analytics: Track what queries/parameters users are using
- UI display: Show tool inputs in execution panels

### `extract_tool_output()`

Extract output data from a tool execution.

**Signature:**

```python
def extract_tool_output(
    tool_exec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract output data from a tool execution.

    Determines the tool type from tool_exec and uses the
    appropriate extractor. Returns minimal structure on error.
    """
```

**Parameters:**

- `tool_exec` (Dict[str, Any]) - The tool execution data dictionary

**Returns:**

- `Dict[str, Any]` - Dictionary containing extracted output data with fields:
  - `result`: The tool's output/result
  - `execution_time`: Time taken to execute
  - `tool_call_id`: Unique identifier for this call
  - `timestamp`: ISO timestamp of execution
  - (Additional fields depending on tool type)

**Raises:**

- Does not raise (returns minimal structure on error)

**Example:**

```python
from backend.services.tools import extract_tool_output

# Extract from tool execution
tool_exec = {
    "tool": "web_search",
    "output": "Search results here...",
    "execution_time": 1.5,
    "timestamp": "2025-10-27T10:30:00Z",
    "call_id": "call_abc123",
}
output_data = extract_tool_output(tool_exec)
# Returns: {
#     "result": "Search results here...",
#     "execution_time": 1.5,
#     "tool_call_id": "call_abc123",
#     "timestamp": "2025-10-27T10:30:00Z",
#     ...
# }

# Extract from HTTP request (returns full metadata)
tool_exec = {
    "tool": "http_request",
    "request": {...},
    "response": {"status_code": 200, "body": {...}},
    "duration": 0.8,
}
output_data = extract_tool_output(tool_exec)
# Returns full HTTP metadata structure
```

**Use Cases:**

- Execution logging: Log tool outputs
- Debugging: Inspect tool results
- UI display: Show tool outputs in execution panels
- Analytics: Track tool performance and results

## Configuration

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.tools import get_tool_registry

# Get global registry (most common usage)
registry = get_tool_registry()

# Registry is ready to use with default tools pre-registered
tools = registry.get_agent_tools("agent-id")
```

**Factory Initialisation:**

```python
from backend.services.tools import ToolFactory

# Default factory with caching enabled
factory = ToolFactory()

# Factory with custom cache settings
factory = ToolFactory(
    enable_cache=True,
    cache_ttl=600,  # 10 minutes
)

# Factory with caching disabled
factory = ToolFactory(enable_cache=False)
```

**Cache Initialisation:**

```python
from backend.services.tools import ToolCache

# Default cache (128 entries, 5-minute TTL)
cache = ToolCache()

# Custom cache settings
cache = ToolCache(
    max_size=256,      # More entries
    default_ttl=1800,  # 30-minute TTL
)

# Unlimited cache with no expiration
cache = ToolCache(
    max_size=0,   # Unlimited
    default_ttl=0,  # No expiration
)
```

**Performance Tracker Initialisation:**

```python
from backend.services.tools import PerformanceTracker

# Simple initialisation
tracker = PerformanceTracker()

# Tracker is ready to track executions
tracker.track_execution("web_search", 1.5, success=True)
```

### Default Tool Configurations

The registry pre-registers these default tools on initialisation:

```python
# Web search tools
{
    "tool_id": "web_search",
    "name": "Web Search",
    "tool_type": ToolType.WEB_SEARCH,
    "cache_results": True,
    "cache_ttl": 300,
}

{
    "tool_id": "arxiv",
    "name": "arXiv Search",
    "tool_type": ToolType.WEB_SEARCH,
    "cache_results": True,
    "cache_ttl": 3600,
}

{
    "tool_id": "wikipedia",
    "name": "Wikipedia Search",
    "tool_type": ToolType.WEB_SEARCH,
    "cache_results": True,
    "cache_ttl": 3600,
}

# Database tools
{
    "tool_id": "database_query",
    "name": "Database Query",
    "tool_type": ToolType.DATABASE,
    "requires_auth": True,
    "auth_env_vars": ["DATABASE_URL"],
}

# Calculation tools
{
    "tool_id": "calculator",
    "name": "Calculator",
    "tool_type": ToolType.CALCULATION,
    "cache_results": False,
}

# File system tools
{
    "tool_id": "file_read",
    "name": "File Read",
    "tool_type": ToolType.FILE_SYSTEM,
}

{
    "tool_id": "file_write",
    "name": "File Write",
    "tool_type": ToolType.FILE_SYSTEM,
}

# HTTP tools
{
    "tool_id": "http_request",
    "name": "HTTP Request",
    "tool_type": ToolType.API_CALL,
    "timeout": 30,
    "max_retries": 3,
}
```

## Error Handling

### Exception Hierarchy

```
Exception
└── ValidationError (backend.services.tools.validation)
    └── Raised when tool configuration validation fails

BaseExtractor defines:
└── ExtractionError (backend.services.tools.extractors.base)
    └── Raised when tool data extraction fails
```

### Exception Details

#### `ValidationError`

Raised when tool configuration validation fails.

**Inherits from:** `Exception`

**When raised:**

- Required configuration keys are missing
- Configuration value has wrong type
- Numeric value is out of allowed range
- Value is not in allowed choices
- Configuration is not a dictionary

**Example:**

```python
from backend.services.tools import ConfigValidator, ValidationError

try:
    ConfigValidator.validate_required_keys(
        config={"url": "https://example.com"},
        required_keys=["url", "api_key"],
        tool_name="api_client",
    )
except ValidationError as e:
    logger.error(f"Configuration validation failed: {e}")
    # Log error and return error response to user
    return {"error": str(e)}
```

#### `ExtractionError`

Raised when tool execution data extraction fails.

**Inherits from:** `Exception`

**When raised:**

- Tool execution data has unexpected format
- Required fields are missing from execution data
- Data type conversion fails
- Extractor encounters invalid data structure

**Attributes:**

- `message` (str) - Error description
- `original_error` (Optional[Exception]) - Original exception if extraction failed due to another error

**Example:**

```python
from backend.services.tools.extractors import extract_tool_input, ExtractionError

try:
    input_data = extract_tool_input("web_search", tool_exec)
except ExtractionError as e:
    logger.error(f"Failed to extract tool input: {e.message}")
    if e.original_error:
        logger.error(f"Original error: {e.original_error}")
    # Use fallback or default data
    input_data = {}
```

**Note:** The public `extract_tool_input()` and `extract_tool_output()` functions catch `ExtractionError` internally and
return safe fallback values, so this exception is primarily for internal use and testing.

### Error Handling Patterns

**Recommended Pattern for Tool Creation:**

```python
from backend.services.tools import (
    get_tool_registry,
    ToolMetadata,
    ToolType,
    ValidationError,
)
from backend.services.config import get_logger

logger = get_logger(__name__)

def create_and_bind_tools(
    agent_id: str,
    agent_name: str,
    tool_configs: list,
) -> tuple[list, list]:
    """
    Create and bind tools with comprehensive error handling.

    Returns:
        tuple: (successful_bindings, errors)
    """
    registry = get_tool_registry()
    successful_bindings = []
    errors = []

    try:
        # Bind tools - registry handles tool creation errors gracefully
        bindings = registry.bind_tools_for_agent(
            agent_id=agent_id,
            agent_name=agent_name,
            tool_configs=tool_configs,
        )

        if not bindings:
            errors.append(f"No tools could be bound to agent '{agent_name}'")
            logger.warning(f"Failed to bind any tools to agent {agent_id}")
        else:
            successful_bindings = bindings
            logger.info(f"Bound {len(bindings)} tools to agent {agent_id}")

    except Exception as e:
        error_msg = f"Unexpected error binding tools to agent '{agent_name}': {e}"
        errors.append(error_msg)
        logger.error(error_msg, exc_info=True)

    return successful_bindings, errors
```

**Pattern for Custom Tool Registration:**

```python
from backend.services.tools import (
    get_tool_registry,
    ToolFactory,
    ValidationError,
)
from backend.services.config import get_logger

logger = get_logger(__name__)

def register_custom_tool_safely(
    factory: ToolFactory,
    tool_name: str,
    creation_func,
) -> bool:
    """
    Safely register a custom tool with error handling.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        factory.register_custom_tool(tool_name, creation_func)
        logger.info(f"Successfully registered custom tool: {tool_name}")
        return True

    except Exception as e:
        logger.error(
            f"Failed to register custom tool '{tool_name}': {e}",
            exc_info=True,
        )
        return False
```

**Pattern for Performance Tracking:**

```python
import time
from backend.services.tools import get_tool_registry
from backend.services.config import get_logger

logger = get_logger(__name__)

def execute_tool_with_tracking(
    agent_id: str,
    tool,
    tool_id: str,
    input_data: dict,
):
    """Execute tool and track performance with error handling."""
    registry = get_tool_registry()
    start_time = time.time()
    success = False
    result = None

    try:
        result = tool.invoke(input_data)
        success = True
        return result

    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        raise

    finally:
        execution_time = time.time() - start_time
        try:
            registry.track_tool_execution(
                agent_id=agent_id,
                tool_id=tool_id,
                execution_time=execution_time,
                success=success,
            )
        except Exception as e:
            # Don't fail the tool execution if tracking fails
            logger.error(f"Failed to track tool execution: {e}")
```

## Integration Patterns

### Integration with Agent Compiler

The tools service integrates tightly with the agent compiler for compile-time tool binding:

```python
# From backend/services/agent/compiler.py
from backend.services.tools import ToolBinding, get_tool_registry

class AgentCompiler:
    def __init__(self):
        self.tool_registry = get_tool_registry()
        # ... other initialisation

    async def compile_agent(
        self,
        node: EnhancedNodeData,
        graph: Optional[GraphData] = None,
    ) -> CompilationResult:
        """Compile an agent with all dependencies resolved."""

        # ... validation and LLM compilation ...

        # Compile tools at compile-time
        tool_bindings = self._compile_tools(node, graph, errors, warnings)

        # Create compiled agent with bound tools
        compiled_agent = CompiledAgent(
            agent_id=node.id,
            agent_name=node.name,
            llm=llm,
            tools=[b.tool_instance for b in tool_bindings],
            tool_bindings=tool_bindings,
            # ... other fields
        )

        return CompilationResult(
            success=True,
            agent=compiled_agent,
            compilation_time_ms=compilation_time,
        )

    def _compile_tools(
        self,
        node: EnhancedNodeData,
        graph: Optional[GraphData],
        errors: List[str],
        warnings: List[str],
    ) -> List[ToolBinding]:
        """Compile tools for agent."""

        # Get tool configurations from node
        tool_configs = node.agent_config.tools or []

        # Find connected custom tools from graph
        if graph:
            connected_tools = find_connected_tools(node, graph)
            tool_configs.extend(connected_tools)

        # Bind tools via registry
        bindings = self.tool_registry.bind_tools_for_agent(
            agent_id=node.id,
            agent_name=node.name,
            tool_configs=tool_configs,
            agent_config=node.agent_config,
        )

        if not bindings and tool_configs:
            warnings.append(
                f"No tools could be bound to agent '{node.name}'"
            )

        return bindings
```

### Integration with Graph Service

The graph service uses tool metadata during graph compilation:

```python
# From backend/services/graph/compilation.py
from backend.services.tools import get_tool_registry

async def compile_graph(graph_data: GraphData) -> CompiledGraph:
    """Compile a workflow graph."""

    tool_registry = get_tool_registry()

    # For each agent node in the graph
    for node in graph_data.nodes:
        if node.type == NodeType.AGENT:
            # Get tool configurations
            tool_configs = extract_tool_configs(node, graph_data)

            # Pre-validate tools exist
            for tool_config in tool_configs:
                tool_name = get_tool_name(tool_config)
                metadata = tool_registry.get_tool_metadata(tool_name)
                if not metadata:
                    # Log warning about unknown tool
                    logger.warning(f"Unknown tool: {tool_name}")

    # ... continue compilation
```

### Integration with Execution Layer

Tool executions are tracked for performance monitoring:

```python
# Example execution handler pattern
from backend.services.tools import get_tool_registry
import time

class ToolExecutionHandler:
    def __init__(self):
        self.registry = get_tool_registry()

    async def execute_tool(
        self,
        agent_id: str,
        tool_id: str,
        tool,
        input_data: dict,
    ):
        """Execute a tool and track performance."""

        start_time = time.time()
        success = False

        try:
            # Execute tool
            result = await tool.ainvoke(input_data)
            success = True
            return result

        finally:
            # Track execution
            execution_time = time.time() - start_time
            self.registry.track_tool_execution(
                agent_id=agent_id,
                tool_id=tool_id,
                execution_time=execution_time,
                success=success,
            )
```

### Dependency Flow

```
┌─────────────────────────┐
│   API Layer             │
│  (FastAPI Routes)       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Graph Compilation      │
│  Service                │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Agent Compiler         │◄──────────────┐
│  Service                │               │
└──────────┬──────────────┘               │
           │                              │
           │ uses                         │
           ▼                              │
┌─────────────────────────┐               │
│  Tools Service          │               │
│  (ToolRegistry)         │               │
└──────────┬──────────────┘               │
           │                              │
           │ creates tools                │
           ▼                              │
┌─────────────────────────┐               │
│  ToolFactory            │───────────────┘
│  (with creators)        │  provides tools
└─────────────────────────┘
```

**Data Flow:**

1. API receives workflow with agent configurations
2. Graph compilation service validates structure
3. Agent compiler compiles each agent node
4. Agent compiler uses ToolRegistry to bind tools
5. ToolRegistry uses ToolFactory to create tool instances
6. ToolFactory uses appropriate creator based on tool type
7. Created tools are bound to agent and cached
8. Compiled agent with tools returned to graph compiler
9. During execution, tool usage is tracked back to registry

### Common Integration Patterns

#### Pattern 1: Compile-Time Tool Binding

```python
from backend.services.tools import get_tool_registry
from backend.services.agent import AgentCompiler

async def compile_agent_with_tools(node_data):
    """Compile an agent with tools at compile-time."""

    # Get registry
    registry = get_tool_registry()

    # Bind tools during compilation
    tool_bindings = registry.bind_tools_for_agent(
        agent_id=node_data.id,
        agent_name=node_data.name,
        tool_configs=node_data.agent_config.tools,
    )

    # Create agent with pre-bound tools
    agent = create_agent(
        llm=llm,
        tools=[binding.tool_instance for binding in tool_bindings],
    )

    return agent, tool_bindings
```

#### Pattern 2: Runtime Tool Execution Tracking

```python
from backend.services.tools import get_tool_registry
import time

async def execute_agent_step(agent_id: str, tool, tool_id: str, input_data: dict):
    """Execute a tool and track performance."""

    registry = get_tool_registry()
    start = time.time()
    success = False

    try:
        result = await tool.ainvoke(input_data)
        success = True
        return result
    finally:
        elapsed = time.time() - start
        registry.track_tool_execution(
            agent_id=agent_id,
            tool_id=tool_id,
            execution_time=elapsed,
            success=success,
        )
```

#### Pattern 3: Custom Tool Registration

```python
from backend.services.tools import ToolFactory, get_tool_registry, ToolMetadata, ToolType
from langchain_core.tools import Tool

def register_domain_specific_tools():
    """Register custom domain-specific tools."""

    factory = ToolFactory()
    registry = get_tool_registry()

    # Register custom creation function
    def create_domain_tool(config):
        return Tool(
            name="domain_analyzer",
            description="Analyzes domain-specific data",
            func=lambda x: analyze_domain_data(x, config),
        )

    factory.register_custom_tool("domain_analyzer", create_domain_tool)

    # Register metadata
    metadata = ToolMetadata(
        tool_id="domain_analyzer",
        name="Domain Analyzer",
        description="Analyzes domain-specific data",
        tool_type=ToolType.CUSTOM,
    )
    registry.register_tool(metadata)
```

## Usage Examples

### Example 1: Basic Usage

Complete end-to-end example of basic tool registry usage:

```python
from backend.services.tools import get_tool_registry

# Step 1: Get the global registry
registry = get_tool_registry()

# Step 2: Bind tools to an agent
tool_bindings = registry.bind_tools_for_agent(
    agent_id="research-agent-001",
    agent_name="Research Assistant",
    tool_configs=["web_search", "arxiv", "calculator"],
)

# Step 3: Get the bound tools
tools = registry.get_agent_tools("research-agent-001")

# Step 4: Use the tools with an agent
from langchain.agents import create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm=llm, tools=tools, prompt=prompt_template)

# Step 5: View binding information
for binding in tool_bindings:
    print(f"Bound {binding.tool_id} to {binding.agent_name}")
    print(f"  Metadata: {binding.metadata.to_dict()}")
```

### Example 2: Advanced Usage with Performance Tracking

Complete example showing advanced features including performance tracking:

```python
from backend.services.tools import (
    get_tool_registry,
    ToolMetadata,
    ToolType,
)
import time

# Step 1: Get registry
registry = get_tool_registry()

# Step 2: Register custom tool
custom_metadata = ToolMetadata(
    tool_id="custom_analyzer",
    name="Custom Data Analyzer",
    description="Analyzes custom business data",
    tool_type=ToolType.CUSTOM,
    cache_results=True,
    cache_ttl=600,
)
registry.register_tool(custom_metadata)

# Step 3: Bind tools with custom configuration
tool_bindings = registry.bind_tools_for_agent(
    agent_id="analytics-agent-001",
    agent_name="Analytics Agent",
    tool_configs=[
        "web_search",
        "custom_analyzer",
        {"name": "database_query", "config": {"connection_string": "..."}},
    ],
)

# Step 4: Execute tools and track performance
tools = registry.get_agent_tools("analytics-agent-001")

for tool in tools:
    start_time = time.time()

    try:
        # Execute tool
        result = tool.invoke({"query": "test query"})
        success = True
    except Exception as e:
        success = False
        print(f"Tool execution failed: {e}")

    # Track execution
    execution_time = time.time() - start_time
    registry.track_tool_execution(
        agent_id="analytics-agent-001",
        tool_id=tool.name,
        execution_time=execution_time,
        success=success,
    )

# Step 5: Get performance statistics
stats = registry.get_performance_stats("web_search")
print(f"Web Search Performance:")
print(f"  Average time: {stats['avg_time']:.2f}s")
print(f"  Total executions: {stats['total_executions']}")
print(f"  Error rate: {stats['error_rate']:.2%}")

# Step 6: Optimise bindings based on usage
registry.optimize_bindings("analytics-agent-001")

# Step 7: Get overall statistics
overall_stats = registry.get_registry_stats()
print(f"\nOverall Statistics:")
print(f"  Total tools: {overall_stats['total_tools']}")
print(f"  Total agents: {overall_stats['total_agents']}")
print(f"  Cache hit rate: {overall_stats['cache_stats']['hit_rate']:.2%}")
```

### Example 3: Complete Workflow with Agent Compilation

Show a realistic, complete workflow integrating with agent compilation:

```python
from backend.services.tools import (
    get_tool_registry,
    ToolMetadata,
    ToolType,
)
from backend.services.agent import AgentCompiler
from backend.models.workflow import AgentConfig, EnhancedNodeData, NodeType
import asyncio

async def complete_agent_compilation_workflow():
    """
    Complete workflow showing tool integration with agent compilation.

    This example demonstrates:
    - Custom tool registration
    - Agent compilation with tools
    - Tool execution and tracking
    - Performance monitoring
    """

    # Step 1: Get registry and register custom tools
    registry = get_tool_registry()

    custom_tool_metadata = ToolMetadata(
        tool_id="sentiment_analyzer",
        name="Sentiment Analyzer",
        description="Analyzes sentiment of text",
        tool_type=ToolType.CUSTOM,
        cache_results=True,
        cache_ttl=300,
    )
    registry.register_tool(custom_tool_metadata)

    # Step 2: Create agent configuration with tools
    agent_config = AgentConfig(
        type="react",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.7,
        tools=[
            "web_search",
            "sentiment_analyzer",
            "calculator",
        ],
    )

    # Step 3: Create enhanced node data
    node_data = EnhancedNodeData(
        id="agent-node-001",
        name="Research & Analysis Agent",
        type=NodeType.AGENT,
        agent_config=agent_config,
    )

    # Step 4: Compile agent (this binds tools internally)
    compiler = AgentCompiler()
    compilation_result = await compiler.compile_agent(node_data)

    if not compilation_result.success:
        print(f"Compilation failed: {compilation_result.errors}")
        return

    compiled_agent = compilation_result.agent

    # Step 5: Inspect tool bindings
    print(f"Compiled agent '{compiled_agent.agent_name}' with tools:")
    for binding in compiled_agent.tool_bindings:
        print(f"  - {binding.tool_id} ({binding.metadata.tool_type.value})")

    # Step 6: Execute agent with tools
    # (This would normally be done by the execution service)
    import time

    for tool in compiled_agent.tools:
        print(f"\nExecuting tool: {tool.name}")

        start_time = time.time()
        success = False

        try:
            # Execute tool
            result = tool.invoke({"query": "test"})
            success = True
            print(f"  Result: {result[:100]}...")
        except Exception as e:
            print(f"  Error: {e}")

        # Track execution
        execution_time = time.time() - start_time
        registry.track_tool_execution(
            agent_id=compiled_agent.agent_id,
            tool_id=tool.name,
            execution_time=execution_time,
            success=success,
        )

    # Step 7: Get performance statistics
    print("\n=== Performance Statistics ===")

    for binding in compiled_agent.tool_bindings:
        print(f"\n{binding.tool_id}:")
        print(f"  Executions: {binding.execution_count}")
        print(f"  Average time: {binding.average_execution_time:.3f}s")
        print(f"  Error rate: {binding.error_rate:.2%}")

    # Step 8: Get registry-wide statistics
    registry_stats = registry.get_registry_stats()
    print(f"\n=== Registry Statistics ===")
    print(f"Total tools registered: {registry_stats['total_tools']}")
    print(f"Total agents: {registry_stats['total_agents']}")
    print(f"Total executions: {registry_stats['total_executions']}")
    print(f"Cache hit rate: {registry_stats['cache_stats']['hit_rate']:.2%}")

    # Step 9: Optimise bindings for future executions
    registry.optimize_bindings(compiled_agent.agent_id)
    print(f"\nOptimised tool bindings for {compiled_agent.agent_name}")

    return {
        "success": True,
        "agent": compiled_agent,
        "stats": registry_stats,
    }


# Run the workflow
if __name__ == "__main__":
    result = asyncio.run(complete_agent_compilation_workflow())
```

### Example 4: Testing Usage

Show how to use this service in tests:

```python
import pytest
from backend.services.tools import (
    get_tool_registry,
    reset_tool_registry,
    ToolFactory,
    ToolMetadata,
    ToolType,
    ValidationError,
)

@pytest.fixture
def clean_registry():
    """Fixture to ensure clean registry for each test."""
    reset_tool_registry()
    yield get_tool_registry()
    reset_tool_registry()


def test_basic_tool_binding(clean_registry):
    """Test basic tool binding to an agent."""
    registry = clean_registry

    # Bind tools
    bindings = registry.bind_tools_for_agent(
        agent_id="test-agent",
        agent_name="Test Agent",
        tool_configs=["web_search", "calculator"],
    )

    # Verify bindings
    assert len(bindings) == 2
    assert bindings[0].agent_id == "test-agent"
    assert bindings[0].tool_id in ["web_search", "calculator"]

    # Verify tools can be retrieved
    tools = registry.get_agent_tools("test-agent")
    assert len(tools) == 2


def test_tool_factory_caching():
    """Test tool factory caching behaviour."""
    factory = ToolFactory(enable_cache=True, cache_ttl=60)

    # Create tool first time (cache miss)
    tool1 = factory.create_tool("calculator")
    assert tool1 is not None

    # Create same tool again (cache hit)
    tool2 = factory.create_tool("calculator")
    assert tool2 is tool1  # Same instance from cache

    # Check cache stats
    stats = factory.get_cache_stats()
    assert stats['hits'] >= 1
    assert stats['hit_rate'] > 0


def test_performance_tracking(clean_registry):
    """Test performance tracking functionality."""
    registry = clean_registry

    # Bind tool
    registry.bind_tools_for_agent(
        agent_id="test-agent",
        agent_name="Test Agent",
        tool_configs=["web_search"],
    )

    # Track executions
    registry.track_tool_execution(
        agent_id="test-agent",
        tool_id="web_search",
        execution_time=1.5,
        success=True,
    )

    registry.track_tool_execution(
        agent_id="test-agent",
        tool_id="web_search",
        execution_time=2.0,
        success=True,
    )

    # Get bindings and check stats
    bindings = registry.get_agent_bindings("test-agent")
    assert bindings[0].execution_count == 2
    assert bindings[0].average_execution_time == 1.75


def test_config_validation():
    """Test configuration validation."""
    from backend.services.tools import ConfigValidator

    # Test required keys validation
    with pytest.raises(ValidationError) as exc_info:
        ConfigValidator.validate_required_keys(
            config={"url": "https://example.com"},
            required_keys=["url", "api_key"],
            tool_name="test_tool",
        )
    assert "api_key" in str(exc_info.value)

    # Test type validation
    with pytest.raises(ValidationError):
        ConfigValidator.validate_type(
            config={"timeout": "30"},  # Wrong type
            key="timeout",
            expected_type=int,
            tool_name="test_tool",
        )

    # Test range validation
    with pytest.raises(ValidationError):
        ConfigValidator.validate_range(
            config={"timeout": 700},
            key="timeout",
            min_value=1,
            max_value=600,
            tool_name="test_tool",
        )


def test_custom_tool_registration():
    """Test custom tool registration."""
    factory = ToolFactory()

    # Define custom creation function
    def create_mock_tool(config):
        from langchain_core.tools import Tool
        return Tool(
            name="mock_tool",
            description="Mock tool for testing",
            func=lambda x: f"Mock result: {x}",
        )

    # Register custom tool
    factory.register_custom_tool("mock_tool", create_mock_tool)

    # Create tool using factory
    tool = factory.create_tool("mock_tool", {})
    assert tool is not None
    assert tool.name == "mock_tool"

    # Test tool execution
    result = tool.invoke("test input")
    assert "Mock result" in result


@pytest.mark.integration
async def test_tool_extraction():
    """Test tool input/output extraction."""
    from backend.services.tools import extract_tool_input, extract_tool_output

    # Test input extraction
    tool_exec = {
        "tool": "web_search",
        "kwargs": {
            "query": "machine learning",
            "max_results": 10,
        },
    }

    input_data = extract_tool_input("web_search", tool_exec)
    assert input_data["query"] == "machine learning"
    assert input_data["max_results"] == 10

    # Test output extraction
    tool_exec = {
        "tool": "web_search",
        "output": "Search results here",
        "execution_time": 1.5,
        "timestamp": "2025-10-27T10:00:00Z",
        "call_id": "call_123",
    }

    output_data = extract_tool_output(tool_exec)
    assert output_data["result"] == "Search results here"
    assert output_data["execution_time"] == 1.5
    assert output_data["tool_call_id"] == "call_123"
```

## Performance Considerations

### Performance Characteristics

**ToolRegistry Operations:**

- `bind_tools_for_agent`: O(n) where n = number of tools to bind
  - Includes tool creation (may be cached) + binding storage
  - First binding for a tool type: ~50-200ms (includes creation)
  - Subsequent bindings (cached): ~1-5ms per tool
- `get_agent_tools`: O(n) where n = number of bindings for agent
  - Simple list extraction, typically <1ms
- `track_tool_execution`: O(1)
  - Direct dictionary lookup and update, <1ms
- `get_performance_stats`: O(1) for specific tool, O(n) for all tools
  - Dictionary lookup or iteration, <1ms typically

**ToolFactory Operations:**

- `create_tool` (cache miss): O(1) creation + validation time
  - Varies by tool type: 10-200ms depending on complexity
  - Database tools: 50-200ms (connection setup)
  - HTTP tools: 10-50ms (minimal setup)
  - Simple tools (calculator): 1-10ms
- `create_tool` (cache hit): O(1)
  - Hash lookup + access tracking, <1ms
  - 95%+ cache hit rate achievable in production

**ToolCache Operations:**

- `get`: O(1) average
  - Hash table lookup, <1ms
  - Includes expiration check
- `set`: O(1) average, O(n) worst case
  - Hash table insert, <1ms
  - O(n) when cache full (LRU eviction scan)
- `cleanup_expired`: O(n)
  - Full iteration over cache entries
  - Typically <10ms for 128 entries

**Memory Usage:**

- ToolMetadata: ~1-2 KB per tool
- ToolBinding: ~2-5 KB per binding (includes tool instance reference)
- Tool instance: Varies by type, typically 5-50 KB
- Cache with 128 entries: ~1-5 MB depending on tool types

**I/O Characteristics:**

- CPU-bound: Tool creation, validation, cache operations
- I/O-bound: Database tool creation (network), file system tool creation (disk)
- Network-bound: HTTP tool creation (minimal), tool execution (when tools make network calls)

### Optimisation Tips

#### Tip 1: Use Tool Caching

**Problem:**

```python
# Inefficient: Creating tools repeatedly for each agent
for agent_id in agent_ids:
    factory = ToolFactory(enable_cache=False)  # No caching!
    tool = factory.create_tool("database_query", config)
    # Tool created from scratch each time (expensive)
```

**Solution:**

```python
# Efficient: Reuse factory with caching enabled
factory = ToolFactory(enable_cache=True, cache_ttl=600)

for agent_id in agent_ids:
    tool = factory.create_tool("database_query", config)
    # First call creates, subsequent calls use cache (fast)
```

**Impact:** 50-100x speedup for cached tool retrieval (200ms → 2ms)

#### Tip 2: Batch Tool Binding

**Problem:**

```python
# Inefficient: Binding tools one at a time
registry = get_tool_registry()
for tool_name in ["web_search", "arxiv", "calculator"]:
    registry.bind_tools_for_agent(
        agent_id="agent-1",
        agent_name="Agent",
        tool_configs=[tool_name],  # Single tool
    )
# Multiple registry operations
```

**Solution:**

```python
# Efficient: Bind all tools at once
registry = get_tool_registry()
registry.bind_tools_for_agent(
    agent_id="agent-1",
    agent_name="Agent",
    tool_configs=["web_search", "arxiv", "calculator"],  # All tools
)
# Single registry operation
```

**Impact:** Reduces overhead, cleaner code, better logging

#### Tip 3: Optimise Tool Ordering

**Problem:**

```python
# Inefficient: Tools in arbitrary order
tool_configs = ["rarely_used_tool", "sometimes_used", "frequently_used"]
registry.bind_tools_for_agent(agent_id, agent_name, tool_configs)

# Frequently used tools checked last during agent execution
```

**Solution:**

```python
# Efficient: Put frequently used tools first
tool_configs = ["frequently_used", "sometimes_used", "rarely_used_tool"]
registry.bind_tools_for_agent(agent_id, agent_name, tool_configs)

# Or use automatic optimisation after some executions
registry.optimize_bindings(agent_id)
# Reorders by execution count automatically
```

**Impact:** Faster tool selection during agent execution

#### Tip 4: Minimise Registry Resets

**Problem:**

```python
# Inefficient: Resetting registry frequently
for test in tests:
    reset_tool_registry()  # Clears all bindings and cache
    registry = get_tool_registry()
    # Must recreate all tools from scratch
    run_test(test, registry)
```

**Solution:**

```python
# Efficient: Reset only when necessary
@pytest.fixture(scope="module")  # Module-level fixture
def shared_registry():
    registry = get_tool_registry()
    yield registry
    # Cleanup only at end of module
    reset_tool_registry()

# Or use clear_bindings for specific agents
registry.clear_bindings(agent_id="test-agent-1")
# Keeps other bindings and cache intact
```

**Impact:** Faster test execution, preserved cache across tests

#### Tip 5: Use Appropriate Cache TTL

**Problem:**

```python
# Inefficient: Too short TTL causes frequent recreations
factory = ToolFactory(cache_ttl=10)  # 10 seconds
# Tools expire quickly and must be recreated

# Or: Too long TTL wastes memory
factory = ToolFactory(cache_ttl=86400)  # 24 hours
# Stale tools stay in memory unnecessarily
```

**Solution:**

```python
# Efficient: Match TTL to usage patterns

# For frequently changing tools (config updates)
factory = ToolFactory(cache_ttl=60)  # 1 minute

# For stable tools (production)
factory = ToolFactory(cache_ttl=600)  # 10 minutes (default)

# For static tools (testing, development)
factory = ToolFactory(cache_ttl=3600)  # 1 hour
```

**Impact:** Balances cache hit rate with memory usage and freshness

### Async/Await Support

The tools service does not currently provide native async methods. Tool execution is synchronous, but tools can be used
in async contexts:

```python
from backend.services.tools import get_tool_registry
import asyncio

async def execute_tools_concurrently(agent_id: str):
    """Execute multiple tools concurrently using async."""

    registry = get_tool_registry()
    tools = registry.get_agent_tools(agent_id)

    # Create async tasks for concurrent execution
    async def execute_tool_async(tool, input_data):
        """Wrap synchronous tool execution in async."""
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,  # Use default executor
            tool.invoke,
            input_data,
        )

    # Execute tools concurrently
    tasks = [
        execute_tool_async(tool, {"query": f"query for {tool.name}"})
        for tool in tools
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Usage
results = await execute_tools_concurrently("agent-1")
```

**Note:** Some LangChain tools provide native async methods via `ainvoke()`:

```python
async def execute_with_native_async(tool, input_data):
    """Use native async if available."""
    if hasattr(tool, 'ainvoke'):
        # Use native async method
        return await tool.ainvoke(input_data)
    else:
        # Fall back to executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, tool.invoke, input_data)
```

### Batch Operations

Batch tool creation for multiple agents:

```python
from backend.services.tools import get_tool_registry

def bind_tools_to_multiple_agents(agent_configs: list) -> dict:
    """
    Efficiently bind tools to multiple agents.

    Args:
        agent_configs: List of (agent_id, agent_name, tool_configs) tuples

    Returns:
        dict: Map of agent_id to bindings
    """
    registry = get_tool_registry()
    all_bindings = {}

    # Single registry instance, factory reuses cache
    for agent_id, agent_name, tool_configs in agent_configs:
        bindings = registry.bind_tools_for_agent(
            agent_id=agent_id,
            agent_name=agent_name,
            tool_configs=tool_configs,
        )
        all_bindings[agent_id] = bindings

    return all_bindings

# Usage
configs = [
    ("agent-1", "Agent 1", ["web_search", "calculator"]),
    ("agent-2", "Agent 2", ["web_search", "arxiv"]),
    ("agent-3", "Agent 3", ["database_query", "calculator"]),
]

bindings = bind_tools_to_multiple_agents(configs)
# Factory cache prevents redundant tool creation
# "web_search" and "calculator" created once, reused for other agents
```

## Best Practices

### Do's

✅ **Use the global registry for tool management**

```python
from backend.services.tools import get_tool_registry

# Always use the global registry
registry = get_tool_registry()

# Don't create multiple ToolRegistry instances
# registry = ToolRegistry()  # ❌ Avoid this
```

**Why:** The singleton pattern ensures consistent state and prevents duplicate tool registrations.

---

✅ **Bind tools at compile-time, not runtime**

```python
# Good: Bind during agent compilation
async def compile_agent(node):
    registry = get_tool_registry()

    # Bind all tools at once during compilation
    bindings = registry.bind_tools_for_agent(
        agent_id=node.id,
        agent_name=node.name,
        tool_configs=node.agent_config.tools,
    )

    return CompiledAgent(
        tools=[b.tool_instance for b in bindings],
        tool_bindings=bindings,
    )

# Avoid: Creating tools during execution
# def execute_step(tool_name):
#     tool = factory.create_tool(tool_name)  # ❌ Too late
```

**Why:** Compile-time binding eliminates runtime lookups, improves performance, and catches configuration errors early.

---

✅ **Track tool executions for performance monitoring**

```python
import time
from backend.services.tools import get_tool_registry

registry = get_tool_registry()

start = time.time()
try:
    result = tool.invoke(input_data)
    success = True
except Exception as e:
    success = False
    raise
finally:
    # Always track, even on failure
    elapsed = time.time() - start
    registry.track_tool_execution(
        agent_id=agent_id,
        tool_id=tool_id,
        execution_time=elapsed,
        success=success,
    )
```

**Why:** Performance tracking helps identify slow tools, monitor error rates, and optimise agent performance.

---

✅ **Validate tool configurations before creation**

```python
from backend.services.tools import ConfigValidator, ValidationError

# Validate before attempting creation
try:
    ConfigValidator.validate_config("database_query", config)
    tool = factory.create_tool("database_query", config)
except ValidationError as e:
    # Handle validation error with clear message
    logger.error(f"Invalid tool configuration: {e}")
    return {"error": str(e)}
```

**Why:** Early validation provides clear error messages and prevents wasted resources on invalid configurations.

---

✅ **Use appropriate cache TTL based on tool characteristics**

```python
from backend.services.tools import ToolFactory

# Short TTL for frequently changing configs
dev_factory = ToolFactory(cache_ttl=60)

# Standard TTL for production
prod_factory = ToolFactory(cache_ttl=600)

# No expiration for static tools
test_factory = ToolFactory(cache_ttl=0)
```

**Why:** Matching TTL to usage patterns balances cache effectiveness with memory usage and config freshness.

---

✅ **Reset registry in test teardown**

```python
import pytest
from backend.services.tools import reset_tool_registry

@pytest.fixture
def clean_registry():
    """Ensure clean state for each test."""
    reset_tool_registry()  # Clean before test
    yield
    reset_tool_registry()  # Clean after test
```

**Why:** Prevents test pollution and ensures each test starts with clean state.

### Don'ts

❌ **Don't create multiple ToolRegistry instances**

```python
# Bad: Creating multiple registries
registry1 = ToolRegistry()
registry2 = ToolRegistry()
# They have different state - confusing and error-prone

# Good: Use global singleton
from backend.services.tools import get_tool_registry
registry = get_tool_registry()
```

**Why:** Multiple registries lead to inconsistent state, duplicate tool creation, and confusion about which registry is
authoritative.

---

❌ **Don't ignore tool creation failures silently**

```python
# Bad: Ignoring failures
tool = factory.create_tool("database_query", config)
if tool:
    use_tool(tool)
# If creation failed, silently continues with None

# Good: Handle failures explicitly
tool = factory.create_tool("database_query", config)
if tool is None:
    logger.error(f"Failed to create database_query tool")
    raise ValueError("Required tool could not be created")
```

**Why:** Silent failures lead to confusing runtime errors and make debugging difficult.

---

❌ **Don't create tools during agent execution**

```python
# Bad: Creating tools on every execution
def execute_agent_step(tool_name, input_data):
    factory = ToolFactory()
    tool = factory.create_tool(tool_name, config)  # Created every time!
    return tool.invoke(input_data)

# Good: Use pre-bound tools from compilation
def execute_agent_step(compiled_agent, tool_id, input_data):
    # Tools already bound during compilation
    tool = next(t for t in compiled_agent.tools if t.name == tool_id)
    return tool.invoke(input_data)
```

**Why:** Runtime tool creation adds latency, bypasses caching benefits, and can fail during execution.

---

❌ **Don't disable caching without good reason**

```python
# Bad: Disabling cache unnecessarily
factory = ToolFactory(enable_cache=False)
for i in range(100):
    tool = factory.create_tool("web_search", config)
    # Creates tool from scratch 100 times!

# Good: Use caching (default)
factory = ToolFactory()  # Caching enabled by default
for i in range(100):
    tool = factory.create_tool("web_search", config)
    # First call creates, rest use cache
```

**Why:** Caching dramatically improves performance. Disable only when you need guaranteed fresh instances (e.g., testing
config changes).

---

❌ **Don't forget to track failed executions**

```python
# Bad: Only tracking successes
try:
    result = tool.invoke(input_data)
    registry.track_tool_execution(agent_id, tool_id, elapsed, success=True)
except Exception as e:
    # Error not tracked!
    raise

# Good: Track both success and failure
try:
    result = tool.invoke(input_data)
    success = True
except Exception as e:
    success = False
    raise
finally:
    registry.track_tool_execution(agent_id, tool_id, elapsed, success=success)
```

**Why:** Tracking failures is crucial for identifying unreliable tools and monitoring error rates.

---

❌ **Don't modify tool bindings during execution**

```python
# Bad: Modifying bindings during execution
def execute_agent(agent_id):
    # Agent is executing...
    registry.bind_tools_for_agent(agent_id, "Agent", new_tools)
    # This modifies bindings while agent is running!

# Good: Bindings are immutable after compilation
def execute_agent(compiled_agent):
    # Use pre-compiled agent with fixed tool bindings
    # No runtime modifications
    pass
```

**Why:** Modifying bindings during execution can cause race conditions and inconsistent agent behaviour. Bindings should
be immutable after compilation.

## Related Documentation

### Related Services

- [Agent Service](agent.md) - Uses tools service for agent-tool binding during compilation
- [Graph Service](graph.md) - Integrates tools service during graph compilation
- [Execution Service](execution.md) - Executes tools and tracks performance

### Related API Modules

- [Graph API](../../../backend/api/graph/graph.md) - Exposes graph compilation endpoints that trigger tool binding
- [Agent API](../agents-guide/api/agent.md) - Agent management endpoints that use tool registry

### Architecture Documentation

- [Service Layer Architecture](../architecture/services.md) - Overview of service layer patterns
- [Compilation Pipeline](../architecture/compilation.md) - Details on compile-time tool binding

### External Documentation

- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/agents/tools/) - LangChain BaseTool
  interface
- [LangChain Agent Documentation](https://python.langchain.com/docs/modules/agents/) - Using tools with agents

## Summary

The Tools Service is a comprehensive tool management system for AgenticStudio, providing centralised tool registration,
compile-time binding, performance tracking, and intelligent caching. It serves as the foundation for all tool-related
operations in the platform.

The service implements several key design patterns including Singleton (global registry), Factory (tool creation),
Strategy (tool creators), and Registry (tool and extractor management). This architecture ensures consistent tool
management, optimal performance through caching, and extensibility through custom tool registration.

At the core of the service is the ToolRegistry, which manages tool metadata and agent-tool bindings. Tools are created
by the ToolFactory using specialised creator classes for different tool types (web search, database, file system, HTTP,
calculation, and custom tools). The factory includes intelligent caching with TTL support to avoid redundant tool
creation.

Performance tracking is built into the system via PerformanceTracker, which monitors tool execution times, error rates,
and usage patterns. This data enables performance optimisation, identification of slow or unreliable tools, and runtime
binding optimisation based on actual usage.

The service integrates tightly with the agent compilation pipeline, enabling compile-time tool binding that eliminates
runtime lookups and catches configuration errors early. Tool extractors provide a standardised way to extract input and
output data from tool executions for logging, debugging, and analytics.

**Key Features:**

- Compile-time tool binding for optimal runtime performance
- Intelligent caching with configurable TTL and LRU eviction
- Comprehensive performance tracking and statistics
- Extensible creator system supporting custom tool types
- Robust configuration validation with clear error messages
- Tool execution data extraction for logging and analytics
- Global singleton registry ensuring consistent state

**Primary Use Cases:**

- Agent compilation: Bind tools to agents during compile-time
- Performance monitoring: Track tool execution metrics
- Tool management: Register and manage tool metadata
- Custom tools: Register domain-specific or user-defined tools
- Analytics: Extract and analyse tool usage patterns

**When to Use This Service:**

- During agent compilation to bind tools to agents
- When creating custom tools for specific domains
- When monitoring tool performance and reliability
- When implementing tool-based features in agents
- When analysing agent tool usage patterns

The Tools Service provides a robust, performant, and extensible foundation for tool management in AgenticStudio, supporting
both built-in and custom tools while maintaining high performance through intelligent caching and compile-time
optimisation.
