"""
Tool Registry Service - Centralized tool management for the system.

This service provides comprehensive tool management including:
- Tool creation and lifecycle management
- Agent-tool binding at compile time
- Performance tracking and optimization
- Caching and validation

Main Components:
    - ToolRegistry: Central registry for managing tools and bindings
    - ToolFactory: Factory for creating tool instances
    - ToolMetadata, ToolBinding: Data models for tool information
    - PerformanceTracker: Tool execution performance monitoring

Usage:
    Basic usage:
    >>> from backend.services.tools import get_tool_registry
    >>> registry = get_tool_registry()
    >>> bindings = registry.bind_tools_for_agent(
    ...     agent_id="agent-1",
    ...     agent_name="Research Agent",
    ...     tool_configs=["web_search", "arxiv", "calculator"]
    ... )
    >>> tools = registry.get_agent_tools("agent-1")

    Performance tracking:
    >>> registry.track_tool_execution(
    ...     agent_id="agent-1",
    ...     tool_id="web_search",
    ...     execution_time=1.5,
    ...     success=True
    ... )
    >>> stats = registry.get_performance_stats("web_search")

    Advanced usage:
    >>> from backend.services.tools import ToolFactory, ToolMetadata, ToolType
    >>> factory = ToolFactory()
    >>> tool = factory.create_tool("web_search", {"max_results": 10})
    >>> metadata = ToolMetadata(
    ...     tool_id="custom_tool",
    ...     name="Custom Tool",
    ...     description="A custom tool",
    ...     tool_type=ToolType.CUSTOM
    ... )
    >>> registry.register_tool(metadata)
"""

# Cache management
from .cache import CacheEntry, ToolCache

# Tool creators (for advanced usage)
from .creators import (
    BaseToolCreator,
    CalculationCreator,
    CustomToolCreator,
    DatabaseCreator,
    FileSystemCreator,
    HttpRequestCreator,
    ToolCreator,
    WebSearchCreator,
)

# Tool execution data extractors
from .extractors import (
    BaseExtractor,
    ExtractionError,
    extract_tool_input,
    extract_tool_output,
)
from .factory import ToolFactory

# Data models
from .models import (
    PerformanceStats,
    ToolBinding,
    ToolCreationConfig,
    ToolMetadata,
    ToolType,
)

# Performance tracking
from .performance import PerformanceTracker

# Registry and factory (primary interfaces)
from .registry import ToolRegistry, get_tool_registry, reset_tool_registry

# Validation
from .validation import ConfigValidator, ValidationError


__all__ = [
    # Primary interfaces
    "ToolRegistry",
    "get_tool_registry",
    "reset_tool_registry",
    "ToolFactory",
    # Data models
    "ToolType",
    "ToolMetadata",
    "ToolBinding",
    "ToolCreationConfig",
    "PerformanceStats",
    # Performance tracking
    "PerformanceTracker",
    # Cache management
    "ToolCache",
    "CacheEntry",
    # Validation
    "ConfigValidator",
    "ValidationError",
    # Creators (advanced)
    "ToolCreator",
    "BaseToolCreator",
    "WebSearchCreator",
    "DatabaseCreator",
    "FileSystemCreator",
    "CalculationCreator",
    "HttpRequestCreator",
    "CustomToolCreator",
    # Extractors
    "extract_tool_input",
    "extract_tool_output",
    "BaseExtractor",
    "ExtractionError",
]
