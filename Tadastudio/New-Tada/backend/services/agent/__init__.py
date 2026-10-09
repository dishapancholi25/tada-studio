"""Agent compilation service - Compile-time tool binding and optimization.

This service provides comprehensive agent compilation functionality including:
- Compile-time dependency resolution (LLM, tools, configuration)
- Intelligent caching with TTL-based expiration
- Configuration validation before compilation
- Performance analysis and optimization hints
- Detailed compilation statistics

Main Components:
    - AgentCompiler: Main compiler class for compiling agents
    - CompiledAgent: Represents a fully compiled agent ready for execution
    - CompilationResult: Result of a compilation operation
    - CompilationCache: Advanced caching with TTL and LRU eviction
    - PerformanceAnalyzer: Analyzes agents for optimization opportunities
    - ConfigValidator: Validates agent configurations before compilation

Usage:
    Basic usage:
    >>> from backend.services.agent import get_agent_compiler
    >>> compiler = get_agent_compiler()
    >>> result = await compiler.compile_agent(agent_node, graph)
    >>> if result.success:
    ...     agent = result.agent
    ...     print(f"Compiled with {len(agent.tools)} tools")

    Compile entire graph:
    >>> results = await compiler.compile_graph(graph_data)
    >>> for agent_id, result in results.items():
    ...     if result.success:
    ...         print(f"Agent {result.agent.agent_name} compiled successfully")

    Get compilation statistics:
    >>> stats = compiler.get_compilation_stats()
    >>> print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
    >>> print(f"Avg compilation time: {stats['avg_compilation_time_ms']:.2f}ms")

    Advanced usage with validation:
    >>> from backend.services.agent import ConfigValidator
    >>> validator = ConfigValidator()
    >>> validation_result = validator.validate_node(agent_node)
    >>> if not validation_result.valid:
    ...     print(f"Validation errors: {validation_result.errors}")

    Custom cache configuration:
    >>> from backend.services.agent import CompilationCache
    >>> cache = CompilationCache(max_size=200, ttl_seconds=7200)
    >>> # Use custom cache in compiler
"""

# Cache management
from .cache import CacheEntry, CompilationCache

# Main compiler
from .compiler import AgentCompiler, get_agent_compiler, reset_agent_compiler

# Configuration
from .config import (
    CACHE_TTL_SECONDS,
    DEFAULT_TIMEOUT,
    ENABLE_CACHE,
    ENABLE_PERFORMANCE_HINTS,
    EXPENSIVE_TIMEOUT,
    EXPENSIVE_TOOLS,
    MAX_CACHE_SIZE,
    PARALLEL_EXECUTION_THRESHOLD,
    USE_COMPILE_TIME_TOOLS,
)

# Exceptions
from .exceptions import (
    CacheError,
    CompilationError,
    LLMCompilationError,
    ToolBindingError,
    ValidationError,
)

# Data models
from .models import CacheStats, CompiledAgent, CompilationResult, CompilationStats

# Performance analysis
from .performance import PerformanceAnalyzer

# Utility functions
from .utils import compile_structured_output, find_connected_tools, generate_cache_key

# Validation
from .validators import ConfigValidator, ValidationResult


__all__ = [
    # Main compiler interface
    "AgentCompiler",
    "get_agent_compiler",
    "reset_agent_compiler",
    # Data models
    "CompiledAgent",
    "CompilationResult",
    "CompilationStats",
    "CacheStats",
    # Cache management
    "CompilationCache",
    "CacheEntry",
    # Performance analysis
    "PerformanceAnalyzer",
    # Validation
    "ConfigValidator",
    "ValidationResult",
    # Exceptions
    "CompilationError",
    "LLMCompilationError",
    "ToolBindingError",
    "ValidationError",
    "CacheError",
    # Utility functions
    "generate_cache_key",
    "find_connected_tools",
    "compile_structured_output",
    # Configuration constants
    "MAX_CACHE_SIZE",
    "CACHE_TTL_SECONDS",
    "DEFAULT_TIMEOUT",
    "EXPENSIVE_TIMEOUT",
    "EXPENSIVE_TOOLS",
    "PARALLEL_EXECUTION_THRESHOLD",
    "ENABLE_CACHE",
    "ENABLE_PERFORMANCE_HINTS",
    "USE_COMPILE_TIME_TOOLS",
]
