"""Configuration constants for agent compilation.

This module defines constants used throughout the agent compilation process,
including performance optimization settings, cache configuration, and tool
categorization.
"""

from typing import List


# Tool Performance Categories
EXPENSIVE_TOOLS: List[str] = [
    "database_query",
    "web_search",
    "http_request",
    "api_call",
    "file_system",
]
"""List of tool names that are considered expensive (high latency/resources)."""

# Timeout Configuration (seconds)
DEFAULT_TIMEOUT: int = 30
"""Default timeout for agent execution in seconds."""

EXPENSIVE_TIMEOUT: int = 60
"""Timeout for agents with expensive tools in seconds."""

PARALLEL_EXECUTION_THRESHOLD: int = 3
"""Minimum number of tools to recommend parallel execution."""

# Cache Configuration
MAX_CACHE_SIZE: int = 100
"""Maximum number of compiled agents to cache."""

CACHE_TTL_SECONDS: int = 3600
"""Time-to-live for cached compiled agents in seconds (1 hour)."""

# Compilation Configuration
ENABLE_CACHE: bool = True
"""Enable compilation result caching."""

ENABLE_PERFORMANCE_HINTS: bool = True
"""Enable performance hint generation during compilation."""

# Tool Connection Configuration
USE_COMPILE_TIME_TOOLS: bool = True
"""Use compile-time tool binding from graph connections."""
