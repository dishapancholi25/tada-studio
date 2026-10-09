# Agent Service

## Overview

The Agent Service provides comprehensive agent compilation functionality for AgenticStudio's workflow system. It compiles
agents with all dependencies (LLM, tools, configuration) resolved at compile-time rather than runtime, resulting in
significant performance improvements and better error detection.

**Location:** [backend/services/agent/](../../backend/services/agent/)

**Primary Responsibilities:**

- Compile-time dependency resolution for agents (LLM, tools, configuration)
- Intelligent caching with TTL-based expiration and LRU eviction
- Configuration validation before compilation
- Performance analysis and optimization hints generation
- Detailed compilation statistics and monitoring
- Structured output schema compilation
- Tool binding and connection management

**Key Use Cases:**

- Compiling individual agents before execution
- Batch compilation of entire workflow graphs
- Validating agent configurations
- Analysing agent performance characteristics
- Caching compiled agents for repeated executions
- Generating performance optimization recommendations

## Architecture

### Module Structure

```
backend/services/agent/
├── __init__.py           # Module exports and public API
├── compiler.py           # Main AgentCompiler class (366 lines)
├── models.py             # Data models (CompiledAgent, CompilationResult, etc.)
├── cache.py              # CompilationCache with TTL and LRU eviction
├── exceptions.py         # Custom exception hierarchy
├── config.py             # Configuration constants
├── validators.py         # ConfigValidator for validation
├── performance.py        # PerformanceAnalyzer for optimization hints
└── utils.py              # Utility functions (cache keys, tool discovery)
```

**File Purposes:**

- **compiler.py** - Main compilation logic, orchestrates LLM creation, tool binding, validation
- **models.py** - Dataclasses representing compilation results and statistics
- **cache.py** - Advanced caching with time-based and size-based eviction
- **exceptions.py** - Structured error types for different compilation failures
- **config.py** - Centralised configuration constants (timeouts, cache settings, tool categories)
- **validators.py** - Configuration validation logic executed before compilation
- **performance.py** - Analyses agent configs to generate optimization recommendations
- **utils.py** - Helper functions for cache key generation and graph analysis

### Design Patterns

#### Singleton Pattern

The agent compiler uses a global singleton instance to maintain shared state across the application:

```python
# Global instance managed by module
_global_compiler: Optional[AgentCompiler] = None

def get_agent_compiler() -> AgentCompiler:
    """Get global compiler instance (Singleton)."""
    global _global_compiler
    if _global_compiler is None:
        _global_compiler = AgentCompiler()
    return _global_compiler
```

**Benefits:**

- Single cache shared across all compilation requests
- Consistent statistics tracking
- Reduced memory footprint
- Thread-safe compilation (single instance)

#### Factory Pattern

The compiler uses factories to create LLMs and tools:

```python
class AgentCompiler:
    def __init__(self):
        self.llm_factory = LLMFactory()  # Creates LLM instances
        self.tool_registry = get_tool_registry()  # Factory for tools
```

#### Cache with TTL and LRU Eviction

Sophisticated caching strategy combining time-based and size-based eviction:

```
Cache Strategy:
- TTL (Time-To-Live): Entries expire after configured time (default 1 hour)
- LRU (Least Recently Used): When cache is full, evict least accessed entry
- Access Tracking: Each cache hit updates access count
- Periodic Optimization: Remove expired entries proactively
```

#### Validation Before Compilation

Multi-stage validation ensures configuration correctness:

```
Compilation Pipeline:
1. Validate node configuration (ConfigValidator)
2. Check required fields (LLM config, agent config)
3. Compile LLM (with error handling)
4. Compile tools (with warnings for failures)
5. Analyse performance (PerformanceAnalyzer)
6. Create CompiledAgent
7. Cache result
```

### Dependencies

#### Internal Dependencies

```python
from backend.services.tools import ToolBinding, get_tool_registry
from backend.services.llm_models import LLMFactory
from backend.services.config import ExecutionConfig, get_logger
from backend.models.workflow import (
    AgentConfig, EnhancedNodeData, GraphData,
    LLMConfig, NodeType
)
```

**Service Dependencies:**

- **backend.services.tools** - Tool registry and binding
- **backend.services.llm_models** - LLM factory for creating language model instances
- **backend.services.config** - Configuration and logging
- **backend.models.workflow** - Workflow data models

#### External Dependencies

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
import asyncio
```

**External Libraries:**

- **langchain_core** - Base classes for LLMs and tools
- **asyncio** - Async compilation support

#### Dependency Flow Diagram

```
Agent Service
    ↓ uses
    ├─→ LLM Models Service (creates LLM instances)
    ├─→ Tools Service (binds tools to agents)
    ├─→ Config Service (logging, feature flags)
    └─→ Models (workflow data structures)

    ↑ used by
    └─→ Graph Service (compiles agents in workflows)
```

## Public API

### Exported Classes

- `AgentCompiler` - Main compiler class for compiling agents with dependencies
- `CompiledAgent` - Dataclass representing a fully compiled agent ready for execution
- `CompilationResult` - Result of a compilation operation (success/failure with details)
- `CompilationStats` - Statistics tracker for compilation operations
- `CacheStats` - Statistics for cache operations (hits, misses, evictions)
- `CompilationCache` - Advanced cache with TTL and LRU eviction
- `CacheEntry` - Individual cache entry with timestamp and access tracking
- `PerformanceAnalyzer` - Analyzes agents for optimization opportunities
- `ConfigValidator` - Validates agent configurations before compilation
- `ValidationResult` - Result of a validation operation

### Exported Functions

- `get_agent_compiler()` - Get the global singleton AgentCompiler instance
- `reset_agent_compiler()` - Reset the global compiler and clear caches
- `generate_cache_key()` - Generate unique cache key for agent configuration
- `find_connected_tools()` - Find tool nodes connected to an agent in graph
- `compile_structured_output()` - Extract structured output schema from config

### Constants and Configuration

**Cache Configuration:**

- `MAX_CACHE_SIZE: int = 100` - Maximum number of cached compiled agents
- `CACHE_TTL_SECONDS: int = 3600` - Cache entry time-to-live (1 hour)
- `ENABLE_CACHE: bool = True` - Master switch for caching

**Timeout Configuration:**

- `DEFAULT_TIMEOUT: int = 30` - Default agent execution timeout (seconds)
- `EXPENSIVE_TIMEOUT: int = 60` - Timeout for agents with expensive tools (seconds)

**Performance Configuration:**

- `PARALLEL_EXECUTION_THRESHOLD: int = 3` - Minimum tools to recommend parallel execution
- `ENABLE_PERFORMANCE_HINTS: bool = True` - Enable performance hint generation
- `USE_COMPILE_TIME_TOOLS: bool = True` - Use compile-time tool binding from graph

**Tool Categorization:**

- `EXPENSIVE_TOOLS: List[str]` - List of expensive tool names:
  `["database_query", "web_search", "http_request", "api_call", "file_system"]`

### Exceptions

```
Exception
└── CompilationError (Base exception for all agent compilation errors)
    ├── LLMCompilationError (LLM creation/configuration failures)
    ├── ToolBindingError (Tool binding failures)
    ├── ValidationError (Configuration validation failures)
    └── CacheError (Cache operation failures)
```

## Core Classes

### `AgentCompiler`

Main compiler class that compiles agents with all dependencies resolved at compile-time.

**Purpose:** Eliminate runtime lookups by resolving all agent dependencies (LLM, tools, configurations) during
compilation, resulting in better execution performance and earlier error detection.

**Responsibilities:**

- Validate agent configuration before compilation
- Create and configure LLM instances
- Bind tools to agents
- Analyse performance characteristics
- Cache compiled agents
- Track compilation statistics
- Generate optimization hints

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialize agent compiler with dependencies.

    Creates:
        - Tool registry for tool binding
        - LLM factory for creating language models
        - Compilation cache with TTL/LRU eviction
        - Performance analyzer
        - Configuration validator
        - Statistics tracker
    """
```

**Class Attributes:**

- `tool_registry: ToolRegistry` - Registry for binding tools
- `llm_factory: LLMFactory` - Factory for creating LLM instances
- `cache: CompilationCache` - Cache for compiled agents
- `performance_analyzer: PerformanceAnalyzer` - Performance analysis utility
- `validator: ConfigValidator` - Configuration validator
- `_stats: CompilationStats` - Compilation statistics tracker

**Key Methods:**

#### `compile_agent()`

Compile an agent with all dependencies resolved.

```python
async def compile_agent(
    self,
    node: EnhancedNodeData,
    graph: Optional[GraphData] = None,
) -> CompilationResult:
    """Compile an agent with all dependencies resolved.

    This is the main compilation entry point. It:
    1. Checks cache for existing compilation
    2. Validates configuration
    3. Compiles LLM
    4. Binds tools
    5. Analyses performance
    6. Caches result

    Args:
        node: Agent node to compile
        graph: Optional graph for context (enables finding connected tools)

    Returns:
        CompilationResult with compiled agent or errors
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - Agent node containing configuration
- `graph` (Optional[GraphData]) - Graph containing node connections (optional)

**Returns:**

- `CompilationResult` - Result object containing:
  - `success: bool` - Whether compilation succeeded
  - `agent: Optional[CompiledAgent]` - Compiled agent if successful
  - `errors: List[str]` - Error messages if failed
  - `warnings: List[str]` - Non-fatal warning messages
  - `compilation_time_ms: float` - Time taken to compile

**Raises:**

- Does not raise exceptions directly; returns errors in `CompilationResult`

**Example:**

```python
from backend.services.agent import get_agent_compiler
from backend.models.workflow import EnhancedNodeData, GraphData

# Get global compiler instance
compiler = get_agent_compiler()

# Compile single agent
result = await compiler.compile_agent(agent_node)

if result.success:
    print(f"Compiled agent: {result.agent.agent_name}")
    print(f"Tools: {len(result.agent.tools)}")
    print(f"Compilation time: {result.compilation_time_ms:.2f}ms")

    # Check for warnings
    if result.warnings:
        print(f"Warnings: {result.warnings}")
else:
    print(f"Compilation failed: {result.errors}")
```

**Behaviour:**

- First checks cache using generated cache key
- Cache hit returns cached agent (very fast, <1ms)
- Cache miss triggers full compilation:
    1. Validates configuration (required fields, valid values)
    2. Creates LLM instance via LLMFactory
    3. Binds tools via ToolRegistry
    4. Analyses performance characteristics
    5. Creates CompiledAgent instance
    6. Stores in cache for future use
- Updates compilation statistics (hits, misses, timing)

**Performance:**

- Cache hit: <1ms (just cache lookup)
- Cache miss: 50-500ms depending on tool count and LLM initialization
- Async operation allows concurrent compilation of multiple agents

**Use Cases:**

- Compile agent before execution in workflow
- Validate agent configuration during workflow editing
- Pre-compile agents when workflow is saved
- Re-compile agent when configuration changes

#### `compile_graph()`

Compile all agents in a workflow graph.

```python
async def compile_graph(
    self,
    graph: GraphData,
) -> Dict[str, CompilationResult]:
    """Compile all agents in a graph.

    Compiles all agent nodes in parallel for best performance.
    Each agent is compiled independently with full graph context.

    Args:
        graph: Graph containing agents to compile

    Returns:
        Dictionary mapping agent_id to CompilationResult
    """
```

**Parameters:**

- `graph` (GraphData) - Workflow graph containing agent nodes

**Returns:**

- `Dict[str, CompilationResult]` - Map of agent_id to compilation result

**Example:**

```python
from backend.services.agent import get_agent_compiler

compiler = get_agent_compiler()

# Compile entire workflow graph
results = await compiler.compile_graph(workflow_graph)

# Check results
successful = sum(1 for r in results.values() if r.success)
failed = sum(1 for r in results.values() if not r.success)

print(f"Compiled {successful}/{len(results)} agents successfully")

# Process each result
for agent_id, result in results.items():
    if result.success:
        agent = result.agent
        print(f"✓ {agent.agent_name}: {len(agent.tools)} tools")
    else:
        print(f"✗ {agent_id}: {', '.join(result.errors)}")
```

**Behaviour:**

- Finds all agent nodes in graph (filters by NodeType.AGENT)
- Compiles agents in parallel using `asyncio.gather()`
- Each agent gets full graph context for tool discovery
- Logs success/failure for each agent
- Returns all results (both successful and failed)

**Performance:**

- Parallel compilation significantly faster than sequential
- Example: 10 agents compile in ~200ms vs ~2000ms sequential
- Limited by I/O (LLM provider API calls, database queries)

#### `get_compiled_agent()`

Retrieve a previously compiled agent from cache by agent ID.

```python
def get_compiled_agent(
    self,
    agent_id: str,
) -> Optional[CompiledAgent]:
    """Get a compiled agent by ID from cache.

    Args:
        agent_id: Agent identifier

    Returns:
        Compiled agent or None if not found
    """
```

**Parameters:**

- `agent_id` (str) - Unique agent identifier

**Returns:**

- `Optional[CompiledAgent]` - Compiled agent if found in cache, None otherwise

**Example:**

```python
compiler = get_agent_compiler()

# Try to get compiled agent
agent = compiler.get_compiled_agent("agent-123")

if agent:
    # Use pre-compiled agent
    print(f"Using cached agent: {agent.agent_name}")
    print(f"LLM: {agent.llm}")
    print(f"Tools: {len(agent.tools)}")
else:
    # Need to compile first
    print("Agent not in cache, compile it first")
```

**Use Cases:**

- Check if agent is already compiled before execution
- Retrieve compiled agent for immediate execution
- Verify cache status during debugging

#### `clear_cache()`

Clear all compilation caches.

```python
def clear_cache(self) -> None:
    """Clear all caches.

    Clears:
        - Compilation cache (compiled agents)
        - Tool factory cache (tool instances)
    """
```

**Example:**

```python
compiler = get_agent_compiler()

# Clear caches when configuration changes
compiler.clear_cache()
print("All caches cleared")

# Next compilation will be fresh
result = await compiler.compile_agent(agent_node)
```

**Use Cases:**

- Clear cache after configuration updates
- Free memory in long-running processes
- Force recompilation for debugging

#### `optimize_cache()`

Optimize cache by removing expired entries.

```python
def optimize_cache(self) -> None:
    """Optimize compilation cache by removing expired entries.

    Proactively removes entries that have exceeded their TTL
    without waiting for them to be accessed.
    """
```

**Example:**

```python
import asyncio
from backend.services.agent import get_agent_compiler

async def periodic_cache_optimization():
    """Background task to optimize cache periodically."""
    compiler = get_agent_compiler()

    while True:
        await asyncio.sleep(600)  # Every 10 minutes
        compiler.optimize_cache()
        print("Cache optimized")
```

**Use Cases:**

- Periodic background cleanup
- Before deployment/restart
- Memory management in constrained environments

#### `get_compilation_stats()`

Get comprehensive compilation statistics.

```python
def get_compilation_stats(self) -> Dict[str, Any]:
    """Get compilation statistics.

    Returns:
        Dictionary containing:
            - total_compilations: Total compilation attempts
            - successful_compilations: Successful compilations
            - failed_compilations: Failed compilations
            - cache_hits: Number of cache hits
            - cache_misses: Number of cache misses
            - total_time_ms: Total compilation time
            - avg_compilation_time_ms: Average compilation time
            - cache_hit_rate: Percentage of cache hits
            - cache: Cache statistics (size, evictions, etc.)
    """
```

**Returns:**

- `Dict[str, Any]` - Comprehensive statistics dictionary

**Example:**

```python
compiler = get_agent_compiler()

# Get statistics
stats = compiler.get_compilation_stats()

print(f"Total compilations: {stats['total_compilations']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
print(f"Average compilation time: {stats['avg_compilation_time_ms']:.2f}ms")
print(f"Cache size: {stats['cache']['size']}/{stats['cache']['max_size']}")
print(f"Cache evictions: {stats['cache']['evictions']}")
```

**Use Cases:**

- Performance monitoring
- Cache effectiveness analysis
- Debugging compilation issues
- Capacity planning

### `CompiledAgent`

Dataclass representing a fully compiled agent ready for execution.

**Purpose:** Encapsulates all resolved dependencies (LLM, tools, configuration) so that agent execution requires no
runtime lookups or configuration resolution.

**Attributes:**

```python
@dataclass
class CompiledAgent:
    agent_id: str                                   # Unique identifier
    agent_name: str                                 # Human-readable name
    agent_type: str                                 # "agent" or "orchestrator"
    llm: BaseChatModel                              # Compiled LLM instance
    tools: List[BaseTool]                           # Compiled tool instances
    tool_bindings: List[ToolBinding]                # Tool binding metadata
    system_prompt: Optional[str]                    # System prompt
    structured_output_schema: Optional[Dict[str, Any]]  # JSON schema for output
    memory_enabled: bool                            # Memory enabled flag
    delegation_enabled: bool                        # Delegation enabled flag
    compilation_time: str                           # ISO timestamp
    cache_key: str                                  # Cache key
    performance_hints: Dict[str, Any]               # Performance optimization hints
```

**Properties:**

- All attributes are read-only after initialisation (dataclass with frozen=False)
- `llm` is a ready-to-use LangChain language model
- `tools` are ready-to-use LangChain tool instances
- `performance_hints` contains analyzer recommendations

**Example:**

```python
from backend.services.agent import get_agent_compiler

compiler = get_agent_compiler()
result = await compiler.compile_agent(agent_node)

if result.success:
    agent = result.agent

    # Use compiled agent
    print(f"Agent: {agent.agent_name} ({agent.agent_type})")
    print(f"LLM: {type(agent.llm).__name__}")
    print(f"Tools: {[t.name for t in agent.tools]}")
    print(f"Memory: {agent.memory_enabled}")
    print(f"Compiled: {agent.compilation_time}")

    # Check performance hints
    hints = agent.performance_hints
    if hints.get('has_expensive_tools'):
        print(f"⚠ Agent has expensive tools, recommended timeout: {hints['recommended_timeout']}s")

    # Execute agent (LLM and tools are ready)
    response = await agent.llm.ainvoke(
        "Hello",
        tools=agent.tools,
    )
```

**Use Cases:**

- Immediate agent execution without setup
- Passing compiled agents to execution engine
- Analysing agent configuration
- Performance optimization based on hints

### `CompilationCache`

Advanced cache for compiled agents with TTL and LRU eviction.

**Purpose:** Improve compilation performance by caching compiled agents and intelligently managing cache size and entry
freshness.

**Initialisation:**

```python
def __init__(
    self,
    max_size: int = MAX_CACHE_SIZE,           # Default: 100
    ttl_seconds: int = CACHE_TTL_SECONDS,     # Default: 3600 (1 hour)
    enabled: bool = ENABLE_CACHE,             # Default: True
) -> None:
    """Initialize compilation cache.

    Args:
        max_size: Maximum number of entries to cache
        ttl_seconds: Time-to-live for cache entries in seconds
        enabled: Whether caching is enabled
    """
```

**Class Attributes:**

- `max_size: int` - Maximum cache capacity
- `ttl_seconds: int` - Time-to-live for entries
- `enabled: bool` - Whether cache is active
- `_cache: Dict[str, CacheEntry]` - Internal cache storage
- `_stats: CacheStats` - Cache statistics tracker

**Key Methods:**

#### `get()`

Get a compiled agent from cache.

```python
def get(
    self,
    cache_key: str,
) -> Optional[CompiledAgent]:
    """Get a compiled agent from cache.

    Checks if entry exists and hasn't expired.
    Updates access statistics.

    Args:
        cache_key: Cache key to look up

    Returns:
        Compiled agent if found and not expired, None otherwise
    """
```

**Parameters:**

- `cache_key` (str) - Cache key (typically MD5 hash of configuration)

**Returns:**

- `Optional[CompiledAgent]` - Cached agent if found and valid, None otherwise

**Behaviour:**

- Returns None if cache is disabled
- Returns None if key not found (cache miss)
- Checks entry expiration (current_time - timestamp > ttl)
- Evicts expired entries automatically
- Updates access count and hit statistics
- Returns cached agent if valid

**Example:**

```python
from backend.services.agent import CompilationCache
from backend.services.agent.utils import generate_cache_key

# Create custom cache
cache = CompilationCache(max_size=50, ttl_seconds=1800)

# Generate cache key
key = generate_cache_key(agent_node)

# Try to get from cache
agent = cache.get(key)

if agent:
    print(f"Cache hit: {agent.agent_name}")
else:
    print("Cache miss, need to compile")
```

#### `set()`

Store a compiled agent in cache.

```python
def set(
    self,
    cache_key: str,
    agent: CompiledAgent,
) -> None:
    """Store a compiled agent in cache.

    Evicts LRU entry if cache is full.

    Args:
        cache_key: Cache key to store under
        agent: Compiled agent to cache
    """
```

**Parameters:**

- `cache_key` (str) - Cache key
- `agent` (CompiledAgent) - Compiled agent to store

**Behaviour:**

- Does nothing if cache is disabled
- Evicts LRU entry if cache is full
- Creates cache entry with current timestamp
- Updates cache size statistics

**Example:**

```python
cache = CompilationCache()

# Store compiled agent
cache.set(cache_key, compiled_agent)
print(f"Cached agent: {compiled_agent.agent_name}")
```

#### `clear()`

Clear all cache entries.

```python
def clear(self) -> None:
    """Clear all cache entries."""
```

**Example:**

```python
cache = CompilationCache()

# Clear cache
cache.clear()
print("Cache cleared")

# Get statistics
stats = cache.get_stats()
assert stats.size == 0
```

#### `optimize()`

Proactively remove expired entries.

```python
def optimize(self) -> None:
    """Optimize cache by removing expired entries.

    Removes entries that have exceeded their TTL without
    waiting for them to be accessed.
    """
```

**Example:**

```python
cache = CompilationCache()

# Periodic optimization
cache.optimize()
stats = cache.get_stats()
print(f"Removed {stats.evictions} expired entries")
```

#### `get_stats()`

Get cache statistics.

```python
def get_stats(self) -> CacheStats:
    """Get cache statistics.

    Returns:
        CacheStats object with current statistics:
            - size: Current number of entries
            - max_size: Maximum cache size
            - hits: Number of cache hits
            - misses: Number of cache misses
            - evictions: Number of evictions
            - hit_rate: Cache hit rate percentage
    """
```

**Returns:**

- `CacheStats` - Statistics dataclass

**Example:**

```python
cache = CompilationCache()

stats = cache.get_stats()
print(f"Cache: {stats.size}/{stats.max_size} entries")
print(f"Hit rate: {stats.hit_rate:.1f}%")
print(f"Evictions: {stats.evictions}")
```

### `PerformanceAnalyzer`

Analyzes agent configurations and generates performance optimization hints.

**Purpose:** Provide actionable recommendations for agent timeout values, parallel execution, and other
performance-related settings based on agent configuration.

**Key Methods:**

#### `analyze_agent()`

Analyze agent and generate performance hints.

```python
@staticmethod
def analyze_agent(
    node: EnhancedNodeData,
    tools: List[BaseTool],
) -> Dict[str, Any]:
    """Analyze agent and generate performance hints.

    Analyses:
        - Tool count
        - Presence of expensive tools (DB, API, web search)
        - Presence of cached tools
        - Parallel execution opportunities

    Args:
        node: Agent node to analyze
        tools: List of compiled tools for the agent

    Returns:
        Dictionary containing performance hints:
            - tool_count: Number of tools
            - has_expensive_tools: Whether expensive tools present
            - has_cached_tools: Whether cached tools present
            - recommended_timeout: Recommended timeout in seconds
            - parallel_tool_execution: Whether to recommend parallel execution
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - Agent node configuration
- `tools` (List[BaseTool]) - Compiled tools

**Returns:**

- `Dict[str, Any]` - Performance hints dictionary

**Example:**

```python
from backend.services.agent import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()

# Analyze agent
hints = analyzer.analyze_agent(agent_node, compiled_tools)

print(f"Tool count: {hints['tool_count']}")
print(f"Expensive tools: {hints['has_expensive_tools']}")
print(f"Recommended timeout: {hints['recommended_timeout']}s")

if hints['parallel_tool_execution']:
    print("⚡ Consider enabling parallel tool execution")

# Use hints in execution
timeout = hints['recommended_timeout']
result = await execute_agent(agent, timeout=timeout)
```

**Use Cases:**

- Generate execution recommendations
- Adjust timeouts based on tool characteristics
- Identify performance optimization opportunities
- Inform users about agent performance characteristics

### `ConfigValidator`

Validates agent configurations before compilation.

**Purpose:** Ensure all required fields are present and valid before attempting compilation, providing early error
detection and clear error messages.

**Key Methods:**

#### `validate_node()`

Validate an agent node for compilation.

```python
@staticmethod
def validate_node(
    node: EnhancedNodeData,
) -> ValidationResult:
    """Validate an agent node for compilation.

    Checks:
        - Agent config exists
        - LLM config is valid
        - Required fields are present

    Args:
        node: Agent node to validate

    Returns:
        ValidationResult indicating if the node is valid
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - Agent node to validate

**Returns:**

- `ValidationResult` - Validation result with errors and warnings

**Example:**

```python
from backend.services.agent import ConfigValidator

validator = ConfigValidator()

# Validate before compilation
validation = validator.validate_node(agent_node)

if validation.valid:
    print("✓ Configuration is valid")
    # Proceed with compilation
    result = await compiler.compile_agent(agent_node)
else:
    print("✗ Validation failed:")
    for error in validation.errors:
        print(f"  - {error}")

# Check warnings
if validation.warnings:
    print("⚠ Warnings:")
    for warning in validation.warnings:
        print(f"  - {warning}")
```

**Use Cases:**

- Validate configuration during workflow editing
- Pre-flight checks before compilation
- Provide user feedback on configuration issues

#### `validate_agent_config()`

Validate agent configuration structure.

```python
@staticmethod
def validate_agent_config(
    config: AgentConfig,
) -> ValidationResult:
    """Validate agent configuration.

    Validates:
        - LLM configuration exists and is valid
        - System prompt (warning if missing)
        - Tool configurations

    Args:
        config: Agent configuration to validate

    Returns:
        ValidationResult indicating if config is valid
    """
```

**Example:**

```python
validator = ConfigValidator()

# Validate just the config
result = validator.validate_agent_config(agent_config)

if not result.valid:
    print(f"Config errors: {result.errors}")
```

#### `validate_llm_config()`

Validate LLM configuration.

```python
@staticmethod
def validate_llm_config(
    config: LLMConfig,
) -> ValidationResult:
    """Validate LLM configuration.

    Checks:
        - Provider is specified
        - Model name is specified

    Args:
        config: LLM configuration to validate

    Returns:
        ValidationResult indicating if config is valid
    """
```

**Example:**

```python
validator = ConfigValidator()

# Validate LLM config
llm_config = LLMConfig(provider="openai", model_name="gpt-4")
result = validator.validate_llm_config(llm_config)

assert result.valid
```

## Functions

### `get_agent_compiler()`

Get the global singleton AgentCompiler instance.

**Signature:**

```python
def get_agent_compiler() -> AgentCompiler:
    """Get the global agent compiler instance.

    Creates the compiler on first call (Singleton pattern).
    Subsequent calls return the same instance.

    Returns:
        Global AgentCompiler instance
    """
```

**Returns:**

- `AgentCompiler` - Global compiler instance (always the same object)

**Example:**

```python
from backend.services.agent import get_agent_compiler

# Get compiler (creates on first call)
compiler1 = get_agent_compiler()

# Get compiler again (returns same instance)
compiler2 = get_agent_compiler()

assert compiler1 is compiler2  # Same object

# Compile agent
result = await compiler1.compile_agent(agent_node)
```

**Use Cases:**

- Primary way to access the compiler in application code
- Ensures single cache instance across application
- Thread-safe (single instance)

### `reset_agent_compiler()`

Reset the global agent compiler instance.

**Signature:**

```python
def reset_agent_compiler() -> None:
    """Reset the global agent compiler.

    Clears the cache and creates a new compiler instance
    on next call to get_agent_compiler().
    """
```

**Example:**

```python
from backend.services.agent import get_agent_compiler, reset_agent_compiler

# Use compiler
compiler = get_agent_compiler()
await compiler.compile_agent(agent_node)

# Reset (clears cache, resets statistics)
reset_agent_compiler()

# Next call creates fresh instance
new_compiler = get_agent_compiler()
```

**Use Cases:**

- Testing (ensure clean state between tests)
- Configuration changes require cache clear
- Memory management (clear caches periodically)

### `generate_cache_key()`

Generate unique cache key for agent configuration.

**Signature:**

```python
def generate_cache_key(
    node: EnhancedNodeData,
) -> str:
    """Generate a unique cache key for a compiled agent.

    The cache key is based on configuration that affects compilation:
        - Agent ID
        - Agent name
        - Version
        - Is orchestrator flag
        - LLM provider and model
        - Tools configuration
        - System prompt hash

    Args:
        node: Agent node to generate cache key for

    Returns:
        MD5 hash string representing the cache key
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - Agent node

**Returns:**

- `str` - MD5 hash (32 character hex string)

**Example:**

```python
from backend.services.agent.utils import generate_cache_key

# Generate cache key
key1 = generate_cache_key(agent_node)
print(f"Cache key: {key1}")  # e.g., "a3f5c8d1e9b2..."

# Same config produces same key
key2 = generate_cache_key(agent_node)
assert key1 == key2

# Different config produces different key
modified_node = copy.deepcopy(agent_node)
modified_node.agent_config.system_prompt = "Different prompt"
key3 = generate_cache_key(modified_node)
assert key1 != key3
```

**Use Cases:**

- Generate cache keys before cache lookup
- Detect configuration changes
- Debugging cache behavior

### `find_connected_tools()`

Find tool nodes connected to an agent in the workflow graph.

**Signature:**

```python
def find_connected_tools(
    node: EnhancedNodeData,
    graph: GraphData,
) -> List[EnhancedNodeData]:
    """Find tool nodes connected to an agent in the graph.

    Searches graph for tool nodes connected via TOOL connection type.

    Args:
        node: Agent node to find connected tools for
        graph: Graph containing nodes and connections

    Returns:
        List of tool nodes connected to the agent
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - Agent node
- `graph` (GraphData) - Workflow graph

**Returns:**

- `List[EnhancedNodeData]` - Connected tool nodes

**Example:**

```python
from backend.services.agent.utils import find_connected_tools

# Find tools connected to agent
connected_tools = find_connected_tools(agent_node, workflow_graph)

print(f"Found {len(connected_tools)} connected tools:")
for tool in connected_tools:
    print(f"  - {tool.name} ({tool.type})")

# Use connected tools in compilation
# (AgentCompiler does this automatically if graph is provided)
```

**Use Cases:**

- Discover tools connected in workflow graph
- Compile-time tool binding
- Workflow analysis

### `compile_structured_output()`

Extract structured output schema from agent configuration.

**Signature:**

```python
def compile_structured_output(
    config: AgentConfig,
) -> Optional[Dict[str, Any]]:
    """Compile structured output schema from agent configuration.

    Extracts the structured output schema if configured.
    Currently returns the first schema if multiple are defined.

    Args:
        config: Agent configuration

    Returns:
        Structured output schema dictionary, or None if not configured
    """
```

**Parameters:**

- `config` (AgentConfig) - Agent configuration

**Returns:**

- `Optional[Dict[str, Any]]` - JSON schema or None

**Example:**

```python
from backend.services.agent.utils import compile_structured_output

# Extract structured output schema
schema = compile_structured_output(agent_config)

if schema:
    print(f"Agent uses structured output: {schema}")
    # Use schema with LLM
    llm_with_schema = llm.with_structured_output(schema)
else:
    print("Agent uses free-form output")
```

**Use Cases:**

- Extract schema for LLM configuration
- Validate agent output structure
- Display schema to users

## Configuration

### Configuration Classes

The agent service uses configuration constants defined in [config.py](../../../backend/services/agent/config.py):

```python
# Tool Performance Categories
EXPENSIVE_TOOLS: List[str] = [
    "database_query",
    "web_search",
    "http_request",
    "api_call",
    "file_system",
]

# Timeout Configuration (seconds)
DEFAULT_TIMEOUT: int = 30
EXPENSIVE_TIMEOUT: int = 60
PARALLEL_EXECUTION_THRESHOLD: int = 3

# Cache Configuration
MAX_CACHE_SIZE: int = 100
CACHE_TTL_SECONDS: int = 3600  # 1 hour

# Compilation Configuration
ENABLE_CACHE: bool = True
ENABLE_PERFORMANCE_HINTS: bool = True
USE_COMPILE_TIME_TOOLS: bool = True
```

**Fields:**

- `EXPENSIVE_TOOLS` - Tool names considered expensive (high latency/resources)
- `DEFAULT_TIMEOUT` - Default agent execution timeout in seconds (default: 30)
- `EXPENSIVE_TIMEOUT` - Timeout for agents with expensive tools (default: 60)
- `PARALLEL_EXECUTION_THRESHOLD` - Min tools to recommend parallel execution (default: 3)
- `MAX_CACHE_SIZE` - Maximum cached compiled agents (default: 100)
- `CACHE_TTL_SECONDS` - Cache entry time-to-live (default: 3600)
- `ENABLE_CACHE` - Master cache enable switch (default: True)
- `ENABLE_PERFORMANCE_HINTS` - Enable hint generation (default: True)
- `USE_COMPILE_TIME_TOOLS` - Use compile-time tool binding (default: True)

### Environment Variables

The agent service uses feature flags from ExecutionConfig:

- `USE_COMPILE_TIME_TOOLS` - Accessed via `ExecutionConfig.get_features().use_compile_time_tools`

**Example:**

```python
from backend.services.config import ExecutionConfig

# Check if compile-time tools are enabled
features = ExecutionConfig.get_features()
if features.use_compile_time_tools:
    print("Compile-time tools enabled")
```

### Initialisation Patterns

#### Basic Initialisation

```python
from backend.services.agent import get_agent_compiler

# Get global compiler instance (recommended)
compiler = get_agent_compiler()

# Compile agent
result = await compiler.compile_agent(agent_node)
```

#### Custom Cache Configuration

```python
from backend.services.agent import AgentCompiler, CompilationCache

# Create custom cache
custom_cache = CompilationCache(
    max_size=200,        # Double the default
    ttl_seconds=7200,    # 2 hours
    enabled=True,
)

# Create compiler with custom cache
compiler = AgentCompiler()
compiler.cache = custom_cache

# Use compiler
result = await compiler.compile_agent(agent_node)
```

#### Disable Caching

```python
from backend.services.agent import CompilationCache

# Create disabled cache
no_cache = CompilationCache(enabled=False)

compiler = AgentCompiler()
compiler.cache = no_cache

# All compilations will be fresh (no cache)
result = await compiler.compile_agent(agent_node)
```

## Error Handling

### Exception Hierarchy

```
Exception
└── CompilationError
    ├── LLMCompilationError
    ├── ToolBindingError
    ├── ValidationError
    └── CacheError
```

**Base Class:**

- `CompilationError` - Base for all agent compilation errors

**Specialized Exceptions:**

- `LLMCompilationError` - LLM creation/configuration failed
- `ToolBindingError` - Tool binding failed
- `ValidationError` - Configuration validation failed
- `CacheError` - Cache operation failed

### Exception Details

#### `CompilationError`

Base exception for all agent compilation errors.

**Attributes:**

- `message: str` - Error message
- `agent_id: Optional[str]` - Agent identifier
- `context: Dict[str, Any]` - Additional error context

**When raised:**

- Base class, typically not raised directly
- Subclasses are raised for specific error types

**Example:**

```python
from backend.services.agent.exceptions import CompilationError

try:
    result = await compiler.compile_agent(node)
    if not result.success:
        # Compilation errors are in result, not raised
        print(f"Errors: {result.errors}")
except Exception as e:
    # Unexpected errors during compilation
    logger.error(f"Unexpected error: {e}")
```

#### `LLMCompilationError`

LLM creation or configuration failed.

**Inherits from:** `CompilationError`

**Additional Context:**

- `provider: str` - LLM provider name (e.g., "openai")
- `model: str` - Model name (e.g., "gpt-4")

**When raised:**

- LLM provider not found
- Model not available
- Invalid LLM configuration
- API key missing/invalid
- LLM initialisation failed

**Example:**

```python
from backend.services.agent.exceptions import LLMCompilationError

try:
    # Attempt to compile with invalid LLM config
    result = await compiler.compile_agent(node)
    if not result.success:
        for error in result.errors:
            if "LLM compilation error" in error:
                print(f"LLM error: {error}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

**Error Messages:**

```
"LLM compilation error (openai/gpt-4): API key not configured"
"Failed to create LLM: openai/invalid-model"
```

#### `ToolBindingError`

Tool binding failed.

**Inherits from:** `CompilationError`

**Additional Context:**

- `failed_tools: str` - Comma-separated list of failed tool names

**When raised:**

- Tool not found in registry
- Tool initialisation failed
- Invalid tool configuration

**Example:**

```python
from backend.services.agent.exceptions import ToolBindingError

# Tool binding errors appear as warnings in CompilationResult
result = await compiler.compile_agent(node)

if result.warnings:
    for warning in result.warnings:
        if "tools could not be bound" in warning:
            print(f"Tool binding warning: {warning}")
```

#### `ValidationError`

Configuration validation failed.

**Inherits from:** `CompilationError`

**Additional Context:**

- `field: str` - Field name that failed validation
- `value: str` - Invalid value

**When raised:**

- Required field missing
- Invalid field value
- Configuration structure incorrect

**Example:**

```python
from backend.services.agent.exceptions import ValidationError
from backend.services.agent import ConfigValidator

validator = ConfigValidator()

# Validate configuration
validation = validator.validate_node(node)

if not validation.valid:
    # Errors are returned in ValidationResult, not raised
    for error in validation.errors:
        print(f"Validation error: {error}")

    # Can raise manually if needed
    if validation.errors:
        raise ValidationError(
            message="; ".join(validation.errors),
            agent_id=node.uniq_id,
        )
```

#### `CacheError`

Cache operation failed.

**Inherits from:** `CompilationError`

**Additional Context:**

- `operation: str` - Cache operation that failed ("get", "set", "clear")
- `cache_key: str` - Cache key involved

**When raised:**

- Cache storage error
- Cache corruption
- Memory allocation failed

**Example:**

```python
from backend.services.agent.exceptions import CacheError

try:
    agent = cache.get(cache_key)
except CacheError as e:
    logger.error(f"Cache error: {e}")
    # Fall back to compilation without cache
    result = await compiler.compile_agent(node)
```

### Error Handling Patterns

#### Recommended Pattern

```python
from backend.services.agent import get_agent_compiler
from backend.services.config import get_logger

logger = get_logger(__name__)

async def compile_and_execute_agent(node: EnhancedNodeData):
    """Compile and execute agent with proper error handling."""
    compiler = get_agent_compiler()

    # Compile agent
    result = await compiler.compile_agent(node)

    # Check compilation result
    if not result.success:
        logger.error(f"Agent compilation failed: {result.errors}")
        return {
            "success": False,
            "error": "Compilation failed",
            "details": result.errors,
        }

    # Log warnings if any
    if result.warnings:
        logger.warning(f"Compilation warnings: {result.warnings}")

    # Use compiled agent
    agent = result.agent
    logger.info(
        f"Compiled {agent.agent_name} with {len(agent.tools)} tools "
        f"in {result.compilation_time_ms:.2f}ms"
    )

    # Execute agent
    try:
        response = await execute_agent(agent)
        return {"success": True, "response": response}
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

#### Validation Before Compilation

```python
from backend.services.agent import ConfigValidator, get_agent_compiler

async def safe_compile(node: EnhancedNodeData):
    """Validate before compilation for early error detection."""

    # Validate first
    validator = ConfigValidator()
    validation = validator.validate_node(node)

    if not validation.valid:
        return {
            "success": False,
            "errors": validation.errors,
            "stage": "validation",
        }

    # Proceed with compilation
    compiler = get_agent_compiler()
    result = await compiler.compile_agent(node)

    return {
        "success": result.success,
        "agent": result.agent,
        "errors": result.errors,
        "warnings": validation.warnings + result.warnings,
        "stage": "compilation" if result.success else "compilation_failed",
    }
```

#### Handle Specific Errors

```python
from backend.services.agent import get_agent_compiler

async def compile_with_fallback(node: EnhancedNodeData):
    """Compile with fallback for specific error types."""
    compiler = get_agent_compiler()
    result = await compiler.compile_agent(node)

    if not result.success:
        # Check for specific error types
        for error in result.errors:
            if "LLM compilation error" in error:
                logger.error(f"LLM error: {error}")
                # Try fallback LLM
                node.agent_config.llm_config = get_fallback_llm_config()
                result = await compiler.compile_agent(node)
                if result.success:
                    logger.info("Successfully compiled with fallback LLM")
                    return result

            elif "tools could not be bound" in error:
                logger.warning(f"Tool binding issue: {error}")
                # Continue without all tools
                return result

        # Unrecoverable errors
        logger.error(f"Compilation failed: {result.errors}")
        raise CompilationError(
            message="; ".join(result.errors),
            agent_id=node.uniq_id,
        )

    return result
```

## Integration Patterns

### Integration with Graph Service

The agent service is primarily used by the graph service for compiling workflows.

**File:** [backend/services/graph/compilation.py](../../../backend/services/graph/compilation.py)

```python
from backend.services.agent import get_agent_compiler
from backend.services.tools import get_tool_registry

class CompilationService:
    """Service for compiling graphs with their tool bindings."""

    def __init__(self, use_compile_time_tools: bool = True):
        self.use_compile_time_tools = use_compile_time_tools
        self.agent_compiler = None

        if use_compile_time_tools:
            self.initialize()

    def initialize(self) -> bool:
        """Initialize compile-time tool binding components."""
        try:
            # Get agent compiler singleton
            self.agent_compiler = get_agent_compiler()
            self.tool_registry = get_tool_registry()
            return True
        except ImportError as e:
            logger.warning(f"Could not initialize: {e}")
            return False

    async def compile_graph(self, graph: GraphData) -> Dict[str, Any]:
        """Compile all agents in a graph."""
        if not self.agent_compiler:
            return {}

        # Compile all agents
        compilation_results = await self.agent_compiler.compile_graph(graph)

        # Cache compiled agents
        compiled_agents = {}
        for agent_id, result in compilation_results.items():
            if result.success and result.agent:
                compiled_agents[agent_id] = result.agent
                logger.info(
                    f"Compiled agent {result.agent.agent_name} "
                    f"with {len(result.agent.tools)} tools"
                )

        return compiled_agents
```

### Integration with API Layer

While not directly exposed, the agent service is used through the graph API.

**File:** backend/api/graph/services/execution_manager.py

```python
from backend.services.graph.compilation import CompilationService

class ExecutionManager:
    """Manages workflow execution with compilation support."""

    def __init__(self):
        self.compilation_service = CompilationService()

    async def execute_workflow(self, graph: GraphData):
        """Execute workflow with compiled agents."""
        # Compile agents
        compiled_agents = await self.compilation_service.compile_graph(graph)

        # Execute using compiled agents
        for agent_id, agent in compiled_agents.items():
            # Agent is pre-compiled with LLM and tools
            response = await self._execute_agent(agent)
```

### Dependency Flow

```
┌─────────────────────────────────────────────┐
│           API Layer                         │
│  backend/api/graph/handlers/execution.py    │
└──────────────────┬──────────────────────────┘
                   ↓ uses
┌─────────────────────────────────────────────┐
│         Graph Service                       │
│  backend/services/graph/compilation.py      │
└──────────────────┬──────────────────────────┘
                   ↓ uses
┌─────────────────────────────────────────────┐
│         Agent Service (THIS MODULE)         │
│  backend/services/agent/compiler.py         │
└──────┬──────────────────┬──────────────────┘
       ↓ uses             ↓ uses
┌──────────────┐    ┌──────────────┐
│ Tools Service│    │ LLM Service  │
│              │    │              │
└──────────────┘    └──────────────┘
```

### Common Integration Patterns

#### Pattern 1: Workflow Compilation on Save

```python
from backend.services.agent import get_agent_compiler
from backend.services.graph import GraphStorageService

async def save_workflow_with_compilation(
    graph: GraphData,
    user_id: str,
):
    """Save workflow and compile agents."""
    # Save workflow
    storage = GraphStorageService()
    await storage.save_graph(graph, user_id)

    # Compile agents
    compiler = get_agent_compiler()
    results = await compiler.compile_graph(graph)

    # Log compilation status
    successful = sum(1 for r in results.values() if r.success)
    logger.info(f"Compiled {successful}/{len(results)} agents")

    # Return save result with compilation status
    return {
        "saved": True,
        "compiled_agents": successful,
        "total_agents": len(results),
        "compilation_errors": [
            {"agent_id": aid, "errors": r.errors}
            for aid, r in results.items()
            if not r.success
        ],
    }
```

#### Pattern 2: Just-In-Time Compilation

```python
from backend.services.agent import get_agent_compiler

async def execute_agent_with_jit_compilation(
    agent_node: EnhancedNodeData,
    graph: GraphData,
):
    """Execute agent with just-in-time compilation."""
    compiler = get_agent_compiler()

    # Check if already compiled
    cached_agent = compiler.get_compiled_agent(agent_node.uniq_id)

    if cached_agent:
        logger.info(f"Using cached agent: {cached_agent.agent_name}")
        agent = cached_agent
    else:
        # Compile on demand
        logger.info(f"Compiling agent: {agent_node.name}")
        result = await compiler.compile_agent(agent_node, graph)

        if not result.success:
            raise RuntimeError(f"Compilation failed: {result.errors}")

        agent = result.agent

    # Execute agent
    return await execute_agent(agent)
```

#### Pattern 3: Batch Compilation with Progress

```python
from backend.services.agent import get_agent_compiler
from typing import Callable

async def compile_graph_with_progress(
    graph: GraphData,
    progress_callback: Callable[[int, int, str], None],
):
    """Compile graph with progress reporting."""
    compiler = get_agent_compiler()

    # Get agent nodes
    agent_nodes = [n for n in graph.nodes if n.type == NodeType.AGENT]
    total = len(agent_nodes)

    # Compile one by one with progress
    results = {}
    for i, node in enumerate(agent_nodes, 1):
        progress_callback(i, total, f"Compiling {node.name}...")

        result = await compiler.compile_agent(node, graph)
        results[node.uniq_id] = result

        if result.success:
            progress_callback(i, total, f"✓ {node.name}")
        else:
            progress_callback(i, total, f"✗ {node.name}: {result.errors[0]}")

    return results
```

## Usage Examples

### Example 1: Basic Usage

Complete end-to-end example of basic usage:

```python
from backend.services.agent import get_agent_compiler
from backend.models.workflow import EnhancedNodeData, AgentConfig, LLMConfig

# Create agent configuration
llm_config = LLMConfig(
    provider="openai",
    model_name="gpt-4",
    temperature=0.7,
)

agent_config = AgentConfig(
    llm_config=llm_config,
    system_prompt="You are a helpful assistant.",
    memory_enabled=True,
    tools=[
        {"name": "web_search", "description": "Search the web"},
        {"name": "calculator", "description": "Perform calculations"},
    ],
)

agent_node = EnhancedNodeData(
    uniq_id="agent-123",
    name="Research Assistant",
    type=NodeType.AGENT,
    agent_config=agent_config,
)

# Step 1: Get compiler instance
compiler = get_agent_compiler()

# Step 2: Compile agent
result = await compiler.compile_agent(agent_node)

# Step 3: Check result
if result.success:
    agent = result.agent
    print(f"✓ Compiled: {agent.agent_name}")
    print(f"  LLM: {type(agent.llm).__name__}")
    print(f"  Tools: {len(agent.tools)}")
    print(f"  Time: {result.compilation_time_ms:.2f}ms")

    # Agent is ready to use
    # Execute with compiled LLM and tools
    response = await agent.llm.ainvoke("What is quantum computing?")
    print(f"  Response: {response.content}")
else:
    print(f"✗ Compilation failed:")
    for error in result.errors:
        print(f"  - {error}")
```

### Example 2: Advanced Usage with Validation

Complete example showing advanced features:

```python
from backend.services.agent import (
    get_agent_compiler,
    ConfigValidator,
    CompilationCache,
)
from backend.services.config import get_logger

logger = get_logger(__name__)

async def compile_agent_with_validation(
    agent_node: EnhancedNodeData,
    graph: GraphData,
):
    """Compile agent with comprehensive validation and error handling."""

    # Step 1: Validate configuration
    validator = ConfigValidator()
    validation = validator.validate_node(agent_node)

    if not validation.valid:
        logger.error(f"Validation failed for {agent_node.name}")
        for error in validation.errors:
            logger.error(f"  - {error}")
        return None

    # Log warnings
    if validation.warnings:
        logger.warning(f"Validation warnings for {agent_node.name}")
        for warning in validation.warnings:
            logger.warning(f"  - {warning}")

    # Step 2: Get compiler with custom cache
    compiler = get_agent_compiler()

    # Optional: Configure custom cache
    compiler.cache = CompilationCache(
        max_size=200,
        ttl_seconds=7200,  # 2 hours
        enabled=True,
    )

    # Step 3: Compile with graph context
    logger.info(f"Compiling agent: {agent_node.name}")
    result = await compiler.compile_agent(agent_node, graph)

    if not result.success:
        logger.error(f"Compilation failed: {result.errors}")
        return None

    # Step 4: Analyze compiled agent
    agent = result.agent
    logger.info(f"Compiled successfully in {result.compilation_time_ms:.2f}ms")
    logger.info(f"  Agent: {agent.agent_name} ({agent.agent_type})")
    logger.info(f"  LLM: {type(agent.llm).__name__}")
    logger.info(f"  Tools: {len(agent.tools)}")
    logger.info(f"  Memory: {agent.memory_enabled}")

    # Step 5: Check performance hints
    hints = agent.performance_hints
    if hints.get('has_expensive_tools'):
        timeout = hints.get('recommended_timeout', 30)
        logger.warning(
            f"  ⚠ Agent has expensive tools, "
            f"recommended timeout: {timeout}s"
        )

    if hints.get('parallel_tool_execution'):
        logger.info("  ⚡ Consider enabling parallel tool execution")

    # Step 6: Get compilation statistics
    stats = compiler.get_compilation_stats()
    logger.info(f"Compiler stats:")
    logger.info(f"  Cache hit rate: {stats['cache_hit_rate']:.1f}%")
    logger.info(f"  Avg compilation time: {stats['avg_compilation_time_ms']:.2f}ms")

    return agent
```

### Example 3: Complete Workflow Compilation

Show a realistic, complete workflow:

```python
from backend.services.agent import get_agent_compiler, reset_agent_compiler
from backend.services.graph import GraphStorageService
from backend.models.workflow import GraphData, NodeType
from typing import Dict, List

async def compile_and_deploy_workflow(
    workflow_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Complete workflow: fetch, compile, deploy."""

    # Step 1: Fetch workflow from database
    storage = GraphStorageService()
    graph = await storage.get_graph(workflow_id, user_id)

    if not graph:
        return {
            "success": False,
            "error": "Workflow not found",
        }

    # Step 2: Get compiler and clear cache for fresh compilation
    compiler = get_agent_compiler()
    compiler.clear_cache()

    # Step 3: Compile all agents in workflow
    logger.info(f"Compiling workflow: {graph.name}")
    results = await compiler.compile_graph(graph)

    # Step 4: Analyze compilation results
    successful_agents: List[str] = []
    failed_agents: List[Dict[str, Any]] = []

    for agent_id, result in results.items():
        if result.success:
            successful_agents.append(result.agent.agent_name)
            logger.info(
                f"✓ {result.agent.agent_name}: "
                f"{len(result.agent.tools)} tools, "
                f"{result.compilation_time_ms:.0f}ms"
            )
        else:
            failed_agents.append({
                "agent_id": agent_id,
                "errors": result.errors,
            })
            logger.error(f"✗ {agent_id}: {', '.join(result.errors)}")

    # Step 5: Check if workflow can be deployed
    total_agents = len(results)
    compiled_count = len(successful_agents)

    can_deploy = compiled_count == total_agents

    if can_deploy:
        logger.info(
            f"✓ Workflow '{graph.name}' fully compiled "
            f"({compiled_count}/{total_agents} agents)"
        )
    else:
        logger.error(
            f"✗ Workflow '{graph.name}' partially compiled "
            f"({compiled_count}/{total_agents} agents)"
        )

    # Step 6: Get compilation statistics
    stats = compiler.get_compilation_stats()

    # Step 7: Return deployment result
    return {
        "success": can_deploy,
        "workflow_id": workflow_id,
        "workflow_name": graph.name,
        "total_agents": total_agents,
        "compiled_agents": compiled_count,
        "failed_agents": failed_agents,
        "can_deploy": can_deploy,
        "statistics": {
            "cache_hit_rate": stats['cache_hit_rate'],
            "avg_compilation_time_ms": stats['avg_compilation_time_ms'],
            "total_compilations": stats['total_compilations'],
        },
    }
```

### Example 4: Testing Usage

Show how to use this service in tests:

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from backend.services.agent import (
    get_agent_compiler,
    reset_agent_compiler,
    CompilationCache,
)
from backend.models.workflow import EnhancedNodeData, AgentConfig, LLMConfig

@pytest.fixture
def agent_node():
    """Create test agent node."""
    llm_config = LLMConfig(
        provider="openai",
        model_name="gpt-4",
    )

    agent_config = AgentConfig(
        llm_config=llm_config,
        system_prompt="Test prompt",
        memory_enabled=True,
        tools=[],
    )

    return EnhancedNodeData(
        uniq_id="test-agent",
        name="Test Agent",
        type=NodeType.AGENT,
        agent_config=agent_config,
    )

@pytest.fixture(autouse=True)
def reset_compiler():
    """Reset compiler before each test."""
    reset_agent_compiler()
    yield
    reset_agent_compiler()

@pytest.mark.asyncio
async def test_compile_agent_basic(agent_node):
    """Test basic agent compilation."""
    compiler = get_agent_compiler()

    # Compile agent
    result = await compiler.compile_agent(agent_node)

    # Verify successful compilation
    assert result.success is True
    assert result.agent is not None
    assert result.agent.agent_name == "Test Agent"
    assert len(result.errors) == 0

@pytest.mark.asyncio
async def test_compile_agent_caching(agent_node):
    """Test that compilation results are cached."""
    compiler = get_agent_compiler()

    # First compilation
    result1 = await compiler.compile_agent(agent_node)
    assert result1.success is True

    # Second compilation should use cache
    result2 = await compiler.compile_agent(agent_node)
    assert result2.success is True

    # Check statistics
    stats = compiler.get_compilation_stats()
    assert stats['total_compilations'] == 2
    assert stats['cache_hits'] == 1
    assert stats['cache_misses'] == 1
    assert stats['cache_hit_rate'] == 50.0

@pytest.mark.asyncio
async def test_compile_agent_validation_error():
    """Test compilation with invalid configuration."""
    # Create agent with missing LLM config
    agent_config = AgentConfig(
        llm_config=None,  # Invalid: no LLM
        system_prompt="Test",
    )

    node = EnhancedNodeData(
        uniq_id="test-agent",
        name="Invalid Agent",
        type=NodeType.AGENT,
        agent_config=agent_config,
    )

    compiler = get_agent_compiler()
    result = await compiler.compile_agent(node)

    # Verify compilation failed
    assert result.success is False
    assert len(result.errors) > 0
    assert "LLM configuration" in result.errors[0]

@pytest.mark.asyncio
async def test_compile_agent_with_mocked_llm(agent_node):
    """Test compilation with mocked LLM factory."""
    mock_llm = Mock()
    mock_llm_instance = Mock()
    mock_llm_instance.llm = mock_llm

    compiler = get_agent_compiler()

    with patch.object(
        compiler.llm_factory,
        'create_llm_instance',
        return_value=mock_llm_instance
    ):
        result = await compiler.compile_agent(agent_node)

        assert result.success is True
        assert result.agent.llm == mock_llm

@pytest.mark.asyncio
async def test_cache_expiration():
    """Test that cache entries expire after TTL."""
    import time

    # Create cache with short TTL
    cache = CompilationCache(
        max_size=10,
        ttl_seconds=1,  # 1 second TTL
    )

    compiler = get_agent_compiler()
    compiler.cache = cache

    # Create and compile agent
    llm_config = LLMConfig(provider="openai", model_name="gpt-4")
    agent_config = AgentConfig(llm_config=llm_config, system_prompt="Test")
    node = EnhancedNodeData(
        uniq_id="test", name="Test", type=NodeType.AGENT,
        agent_config=agent_config
    )

    # First compilation
    result1 = await compiler.compile_agent(node)
    assert result1.success is True

    # Immediate second compilation uses cache
    result2 = await compiler.compile_agent(node)
    stats = compiler.get_compilation_stats()
    assert stats['cache_hits'] == 1

    # Wait for TTL expiration
    time.sleep(1.1)

    # Third compilation should miss cache (expired)
    result3 = await compiler.compile_agent(node)
    stats = compiler.get_compilation_stats()
    # Cache miss count should increase
    assert stats['cache_misses'] == 2  # First miss + expired miss
```

## Performance Considerations

### Performance Characteristics

**Compilation Performance:**

| Operation                                | Time Complexity | Typical Time | Notes                    |
|------------------------------------------|-----------------|--------------|--------------------------|
| Cache hit                                | O(1)            | <1ms         | Hash lookup only         |
| Cache miss (simple agent)                | O(n)            | 50-200ms     | n = tool count           |
| Cache miss (complex agent)               | O(n)            | 200-500ms    | Multiple tools, LLM init |
| Graph compilation (10 agents)            | O(n) parallel   | 200-500ms    | Parallel compilation     |
| Graph compilation (10 agents) sequential | O(n²)           | 2000-5000ms  | Not recommended          |

**Memory Usage:**

- Each cached agent: ~10-50KB (depends on tool count)
- Default cache (100 agents): ~1-5MB total
- LLM instances: Shared across compilations (singleton in LLMFactory)
- Tool instances: Reused from tool registry

**I/O Characteristics:**

- **CPU-bound:** Cache key generation, validation
- **I/O-bound:** LLM provider API calls (if credentials need verification)
- **Network-bound:** External tool initialisation (rare)

### Optimisation Tips

#### Tip 1: Use Graph Compilation for Multiple Agents

**Problem:**

```python
# Inefficient: Sequential compilation
for agent_node in agent_nodes:
    result = await compiler.compile_agent(agent_node)
```

**Solution:**

```python
# Efficient: Parallel compilation via compile_graph
results = await compiler.compile_graph(graph)
# 5-10x faster for graphs with multiple agents
```

**Benefits:**

- Parallel compilation utilizes asyncio concurrency
- Shared graph context reduces redundant lookups
- Better resource utilization

#### Tip 2: Leverage Cache for Repeated Compilations

**Problem:**

```python
# Inefficient: Clearing cache unnecessarily
compiler.clear_cache()
result = await compiler.compile_agent(agent_node)  # Always compiles from scratch
```

**Solution:**

```python
# Efficient: Let cache work
result = await compiler.compile_agent(agent_node)  # Uses cache if available

# Only clear cache when configuration actually changes
if config_changed:
    compiler.clear_cache()
```

**Benefits:**

- Cache hit: <1ms vs 200ms compilation
- Reduced LLM provider API calls
- Lower CPU usage

#### Tip 3: Optimize Cache Configuration for Your Workload

```python
from backend.services.agent import CompilationCache

# For high-volume, low-memory environments
cache = CompilationCache(
    max_size=50,          # Smaller cache
    ttl_seconds=1800,     # 30 minutes
)

# For development with frequent changes
cache = CompilationCache(
    max_size=200,         # Larger cache
    ttl_seconds=300,      # 5 minutes (shorter TTL)
)

# For production with stable configurations
cache = CompilationCache(
    max_size=500,         # Very large cache
    ttl_seconds=14400,    # 4 hours
)

compiler = get_agent_compiler()
compiler.cache = cache
```

#### Tip 4: Pre-compile Workflows on Save

```python
async def save_workflow_optimized(graph: GraphData, user_id: str):
    """Save and pre-compile workflow for faster execution."""
    # Save workflow
    await storage.save_graph(graph, user_id)

    # Pre-compile in background (don't block save)
    asyncio.create_task(precompile_workflow(graph))

    return {"saved": True}

async def precompile_workflow(graph: GraphData):
    """Background compilation task."""
    compiler = get_agent_compiler()
    await compiler.compile_graph(graph)
    logger.info(f"Pre-compiled workflow: {graph.name}")
```

**Benefits:**

- First execution is fast (already compiled)
- Compilation errors detected early
- Better user experience

### Async/Await Support

The agent service fully supports async/await patterns:

```python
from backend.services.agent import get_agent_compiler

async def compile_multiple_agents_concurrently(nodes: List[EnhancedNodeData]):
    """Compile multiple agents concurrently."""
    compiler = get_agent_compiler()

    # Create compilation tasks
    tasks = [
        compiler.compile_agent(node)
        for node in nodes
    ]

    # Execute concurrently
    results = await asyncio.gather(*tasks)

    return results

# Usage
results = await compile_multiple_agents_concurrently(agent_nodes)
```

**Benefits:**

- Non-blocking compilation
- Concurrent I/O operations
- Better performance in async applications

### Batch Operations

For optimal performance when compiling multiple agents:

```python
# ✓ RECOMMENDED: Use compile_graph for batch compilation
compiler = get_agent_compiler()
results = await compiler.compile_graph(workflow_graph)
# Compiles all agents in parallel

# ✗ NOT RECOMMENDED: Sequential compilation
for node in agent_nodes:
    result = await compiler.compile_agent(node)
# Much slower for multiple agents
```

## Testing Patterns

### Unit Testing

```python
import pytest
from backend.services.agent import get_agent_compiler, reset_agent_compiler

@pytest.fixture(autouse=True)
def reset_compiler_fixture():
    """Reset compiler before and after each test."""
    reset_agent_compiler()
    yield
    reset_agent_compiler()

@pytest.mark.asyncio
async def test_compile_agent_success():
    """Test successful agent compilation."""
    compiler = get_agent_compiler()

    # Create test node
    node = create_test_agent_node()

    # Compile
    result = await compiler.compile_agent(node)

    # Assert success
    assert result.success is True
    assert result.agent is not None
    assert result.agent.agent_name == node.name
    assert len(result.errors) == 0

@pytest.mark.asyncio
async def test_compile_agent_validation_failure():
    """Test compilation with invalid configuration."""
    compiler = get_agent_compiler()

    # Create invalid node (no LLM config)
    node = create_invalid_agent_node()

    # Compile
    result = await compiler.compile_agent(node)

    # Assert failure
    assert result.success is False
    assert result.agent is None
    assert len(result.errors) > 0
    assert "LLM" in result.errors[0]
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_compile_with_mocked_llm_factory():
    """Test compilation with mocked LLM factory."""
    # Create mock LLM
    mock_llm = Mock()
    mock_llm_instance = Mock()
    mock_llm_instance.llm = mock_llm

    compiler = get_agent_compiler()

    # Mock LLM factory
    with patch.object(
        compiler.llm_factory,
        'create_llm_instance',
        return_value=mock_llm_instance
    ):
        node = create_test_agent_node()
        result = await compiler.compile_agent(node)

        # Verify mock was used
        assert result.success is True
        assert result.agent.llm == mock_llm
        compiler.llm_factory.create_llm_instance.assert_called_once()

@pytest.mark.asyncio
async def test_compile_with_mocked_tool_registry():
    """Test compilation with mocked tool registry."""
    # Create mock tools
    mock_tool = Mock()
    mock_tool.name = "test_tool"

    mock_binding = Mock()
    mock_binding.tool_instance = mock_tool

    compiler = get_agent_compiler()

    # Mock tool registry
    with patch.object(
        compiler.tool_registry,
        'bind_tools_for_agent',
        return_value=[mock_binding]
    ):
        node = create_test_agent_node()
        result = await compiler.compile_agent(node)

        # Verify mock was used
        assert result.success is True
        assert len(result.agent.tools) == 1
        assert result.agent.tools[0].name == "test_tool"
```

### Integration Testing

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_compilation_integration():
    """Integration test with real dependencies."""
    compiler = get_agent_compiler()

    # Create realistic agent configuration
    llm_config = LLMConfig(
        provider="openai",
        model_name="gpt-4",
    )

    agent_config = AgentConfig(
        llm_config=llm_config,
        system_prompt="You are a test assistant",
        memory_enabled=True,
        tools=[
            {"name": "calculator", "description": "Calculate"},
        ],
    )

    node = EnhancedNodeData(
        uniq_id="integration-test",
        name="Integration Test Agent",
        type=NodeType.AGENT,
        agent_config=agent_config,
    )

    # Compile with real services
    result = await compiler.compile_agent(node)

    # Verify compilation
    assert result.success is True

    # Verify LLM is real instance
    from langchain_core.language_models import BaseChatModel
    assert isinstance(result.agent.llm, BaseChatModel)

    # Verify tools are bound
    assert len(result.agent.tools) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_compilation_integration(workflow_graph):
    """Integration test for graph compilation."""
    compiler = get_agent_compiler()

    # Compile entire graph
    results = await compiler.compile_graph(workflow_graph)

    # Verify all agents compiled
    assert len(results) > 0

    for agent_id, result in results.items():
        assert result.success is True
        assert result.agent is not None
```

## Best Practices

### Do's

#### ✅ Use the Global Singleton Compiler

```python
from backend.services.agent import get_agent_compiler

# RECOMMENDED: Use global singleton
compiler = get_agent_compiler()
result = await compiler.compile_agent(node)

# WHY: Shares cache across application, consistent statistics
```

#### ✅ Compile Entire Graphs in Parallel

```python
# RECOMMENDED: Parallel graph compilation
compiler = get_agent_compiler()
results = await compiler.compile_graph(workflow_graph)

# WHY: 5-10x faster than sequential compilation
# WHY: Better resource utilization
```

#### ✅ Validate Before Compilation

```python
from backend.services.agent import ConfigValidator, get_agent_compiler

# RECOMMENDED: Validate first
validator = ConfigValidator()
validation = validator.validate_node(node)

if not validation.valid:
    return {"error": "Invalid configuration", "details": validation.errors}

# Then compile
compiler = get_agent_compiler()
result = await compiler.compile_agent(node)

# WHY: Faster failure, clearer error messages
# WHY: Avoid wasting resources on invalid configs
```

#### ✅ Check Compilation Result Before Use

```python
# RECOMMENDED: Always check result
result = await compiler.compile_agent(node)

if result.success:
    agent = result.agent
    # Use agent
else:
    logger.error(f"Compilation failed: {result.errors}")
    # Handle error appropriately

# WHY: Compilation can fail for various reasons
# WHY: Errors are returned, not raised
```

#### ✅ Use Performance Hints

```python
# RECOMMENDED: Use performance hints
result = await compiler.compile_agent(node)

if result.success:
    hints = result.agent.performance_hints
    timeout = hints.get('recommended_timeout', 30)

    # Adjust execution based on hints
    response = await execute_agent(result.agent, timeout=timeout)

# WHY: Optimizes execution based on agent characteristics
# WHY: Prevents timeouts on expensive operations
```

### Don'ts

#### ❌ Don't Create Multiple Compiler Instances

```python
# WRONG: Creating new compiler instances
compiler1 = AgentCompiler()  # Creates new cache
compiler2 = AgentCompiler()  # Creates another new cache

# WHY: Each instance has separate cache (wasted memory)
# WHY: Statistics are fragmented
# WHY: No benefit over singleton

# RIGHT: Use singleton
from backend.services.agent import get_agent_compiler
compiler = get_agent_compiler()
```

#### ❌ Don't Clear Cache Unnecessarily

```python
# WRONG: Clearing cache on every compilation
compiler.clear_cache()
result = await compiler.compile_agent(node)

# WHY: Defeats the purpose of caching
# WHY: Every compilation is slow
# WHY: Wastes CPU and I/O resources

# RIGHT: Let cache work, only clear when needed
result = await compiler.compile_agent(node)  # Uses cache if available

# Only clear when configuration actually changes
if config_changed:
    compiler.clear_cache()
```

#### ❌ Don't Compile Agents Sequentially in Loops

```python
# WRONG: Sequential compilation in loop
for agent_node in agent_nodes:
    result = await compiler.compile_agent(agent_node)
    # Process result

# WHY: Very slow for multiple agents
# WHY: No concurrency, wastes time

# RIGHT: Use compile_graph or gather
results = await compiler.compile_graph(graph)
# OR
tasks = [compiler.compile_agent(n) for n in agent_nodes]
results = await asyncio.gather(*tasks)
```

#### ❌ Don't Ignore Compilation Warnings

```python
# WRONG: Ignoring warnings
result = await compiler.compile_agent(node)
if result.success:
    agent = result.agent
    # Use agent without checking warnings

# WHY: Warnings indicate potential issues
# WHY: May cause runtime failures
# WHY: Tool binding failures appear as warnings

# RIGHT: Check and log warnings
if result.success:
    if result.warnings:
        logger.warning(f"Compilation warnings: {result.warnings}")
        # Decide if warnings are acceptable
    agent = result.agent
```

#### ❌ Don't Assume Compilation Always Succeeds

```python
# WRONG: Assuming success without checking
result = await compiler.compile_agent(node)
agent = result.agent  # May be None!
response = await agent.llm.ainvoke("Hello")  # AttributeError!

# WHY: Compilation can fail for many reasons
# WHY: Agent is None when compilation fails
# WHY: Causes runtime errors

# RIGHT: Always check success
result = await compiler.compile_agent(node)
if not result.success:
    raise RuntimeError(f"Compilation failed: {result.errors}")

agent = result.agent
response = await agent.llm.ainvoke("Hello")
```

## Related Documentation

### Related Services

- [Graph Service](graph.md) - Uses agent service for workflow compilation
- [Tools Service](tools.md) - Provides tool binding for agents
- [LLM Models Service](llm_models.md) - Provides LLM instances for agents
- [Execution Service](execution.md) - Executes compiled agents

### Related API Modules

- [Graph API](../../../backend/api/graph/graph.md) - API endpoints that trigger agent compilation
- [Execution API](../../../backend/api/execution/execution.md) - Executes workflows using compiled agents

### Architecture Documentation

- [Compilation Architecture](../architecture/compilation.md) - Overall compilation architecture
- [Service Layer Architecture](../architecture/services.md) - Service layer design patterns

## Summary

The Agent Service is a critical component of AgenticStudio's workflow execution system, providing compile-time dependency
resolution and caching for agents. It eliminates runtime lookups and configuration resolution, resulting in faster
execution and earlier error detection.

**Key Features:**

- **Compile-time dependency resolution** - Resolves LLM, tools, and configuration during compilation rather than
  execution
- **Intelligent caching** - TTL and LRU-based cache reduces compilation overhead
- **Validation before compilation** - Detects configuration errors early with clear messages
- **Performance analysis** - Generates optimization hints based on agent characteristics
- **Detailed statistics** - Tracks compilation metrics for monitoring and optimization
- **Async/await support** - Fully async for optimal performance in concurrent environments
- **Graph compilation** - Compiles entire workflows in parallel for best performance

**Primary Use Cases:**

- Compiling agents before workflow execution
- Validating agent configurations during workflow editing
- Pre-compiling workflows when saved for faster first execution
- Analysing agent performance characteristics
- Monitoring compilation performance and cache effectiveness

**When to Use This Service:**

- ✅ Before executing any agent in a workflow
- ✅ When validating workflow configurations
- ✅ When saving workflows (pre-compile for faster execution)
- ✅ When analysing workflow performance
- ✅ When monitoring system health (compilation statistics)

**When NOT to Use This Service:**

- ❌ For simple LLM calls without workflow context
- ❌ For one-off script execution (overhead not worth it)
- ❌ When you need complete runtime flexibility (rare)

The agent service is designed for high-performance, production workflow execution where agents are compiled once and
executed many times, significantly reducing execution latency and improving reliability through early error detection.
