"""Data models for agent compilation.

This module defines dataclasses and type definitions used throughout
the agent compilation process.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from backend.services.tools import ToolBinding


@dataclass
class CompiledAgent:
    """A fully compiled agent with all dependencies resolved.

    This represents an agent that is ready for execution without requiring
    any runtime lookups or configuration resolution.

    Attributes:
        agent_id: Unique identifier for the agent
        agent_name: Human-readable name of the agent
        agent_type: Type of agent (agent, orchestrator, etc.)
        llm: Compiled language model instance ready for use
        tools: List of compiled tool instances
        tool_bindings: List of tool binding metadata
        system_prompt: Optional system prompt for the agent
        structured_output_schema: Optional JSON schema for structured output
        memory_enabled: Whether memory is enabled for this agent
        delegation_enabled: Whether delegation is enabled (for orchestrators)
        compilation_time: ISO timestamp of when compilation completed
        cache_key: Cache key used to store this compiled agent
        performance_hints: Dictionary of performance optimization hints
    """

    agent_id: str
    agent_name: str
    agent_type: str
    llm: BaseChatModel
    tools: List[BaseTool]
    tool_bindings: List[ToolBinding]
    system_prompt: Optional[str]
    structured_output_schema: Optional[Dict[str, Any]]
    memory_enabled: bool
    delegation_enabled: bool
    compilation_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cache_key: str = ""
    performance_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompilationResult:
    """Result of an agent compilation operation.

    Attributes:
        success: Whether compilation was successful
        agent: The compiled agent (None if compilation failed)
        errors: List of error messages encountered during compilation
        warnings: List of warning messages (non-fatal issues)
        compilation_time_ms: Time taken to compile in milliseconds
    """

    success: bool
    agent: Optional[CompiledAgent]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    compilation_time_ms: float = 0.0


@dataclass
class CompilationStats:
    """Statistics about compilation operations.

    Tracks metrics across multiple compilation operations for monitoring
    and optimization purposes.

    Attributes:
        total_compilations: Total number of compilations attempted
        successful_compilations: Number of successful compilations
        failed_compilations: Number of failed compilations
        cache_hits: Number of times a cached agent was used
        cache_misses: Number of times compilation was required
        total_time_ms: Total time spent compiling (excluding cache hits)
        avg_compilation_time_ms: Average compilation time
        cache_hit_rate: Percentage of compilations served from cache
    """

    total_compilations: int = 0
    successful_compilations: int = 0
    failed_compilations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_time_ms: float = 0.0

    @property
    def avg_compilation_time_ms(self) -> float:
        """Calculate average compilation time."""
        if self.cache_misses == 0:
            return 0.0
        return self.total_time_ms / self.cache_misses

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        if self.total_compilations == 0:
            return 0.0
        return (self.cache_hits / self.total_compilations) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_compilations": self.total_compilations,
            "successful_compilations": self.successful_compilations,
            "failed_compilations": self.failed_compilations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_time_ms": self.total_time_ms,
            "avg_compilation_time_ms": self.avg_compilation_time_ms,
            "cache_hit_rate": self.cache_hit_rate,
        }


@dataclass
class CacheStats:
    """Statistics about cache operations.

    Attributes:
        size: Current number of entries in cache
        max_size: Maximum cache size
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of cache evictions (due to size/TTL)
        hit_rate: Cache hit rate as a percentage
    """

    size: int = 0
    max_size: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
        }
