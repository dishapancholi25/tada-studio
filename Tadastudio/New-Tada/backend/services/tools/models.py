"""
Data models for the tool registry system.

This module defines all data structures used for tool management including
tool types, metadata, bindings, and configuration schemas.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolType(Enum):
    """
    Types of tools available in the system.

    Categories:
        - WEB_SEARCH: Web search and information retrieval tools
        - DATABASE: Database query and management tools
        - FILE_SYSTEM: File reading and writing tools
        - API_CALL: HTTP and API request tools
        - CALCULATION: Mathematical computation tools
        - DELEGATION: Agent delegation and subworkflow tools
        - MCP_SERVER: Model Context Protocol server tools
        - CUSTOM: User-defined custom tools
    """

    WEB_SEARCH = "web_search"
    DATABASE = "database_query"
    FILE_SYSTEM = "file_system"
    API_CALL = "api_call"
    CALCULATION = "calculation"
    DELEGATION = "delegation"
    MCP_SERVER = "mcp_server"
    CUSTOM = "custom"


@dataclass
class ToolMetadata:
    """
    Metadata for a registered tool.

    Attributes:
        tool_id: Unique identifier for the tool
        name: Display name of the tool
        description: Human-readable description of tool capabilities
        tool_type: Category of the tool (from ToolType enum)
        version: Tool version string (semantic versioning recommended)
        requires_auth: Whether the tool requires authentication
        auth_env_vars: List of required environment variable names for auth
        max_retries: Maximum number of retry attempts on failure
        timeout: Execution timeout in seconds
        cache_results: Whether tool results should be cached
        cache_ttl: Cache time-to-live in seconds
        performance_stats: Dictionary of performance metrics
        created_at: ISO timestamp of tool registration
    """

    tool_id: str
    name: str
    description: str
    tool_type: ToolType
    version: str = "1.0.0"
    requires_auth: bool = False
    auth_env_vars: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout: int = 30
    cache_results: bool = False
    cache_ttl: int = 300  # seconds
    performance_stats: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary format.

        Returns:
            Dictionary representation of metadata
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type.value,
            "version": self.version,
            "requires_auth": self.requires_auth,
            "auth_env_vars": self.auth_env_vars,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "cache_results": self.cache_results,
            "cache_ttl": self.cache_ttl,
            "performance_stats": self.performance_stats,
            "created_at": self.created_at,
        }


@dataclass
class ToolBinding:
    """
    Represents a tool bound to an agent at compile time.

    Bindings track the relationship between agents and their tools,
    including usage statistics and performance metrics.

    Attributes:
        agent_id: Unique identifier of the agent
        agent_name: Display name of the agent
        tool_id: Identifier of the bound tool
        tool_instance: The actual tool instance (BaseTool)
        metadata: Tool metadata object
        binding_time: ISO timestamp when binding was created
        execution_count: Number of times tool has been executed
        total_execution_time: Cumulative execution time in seconds
        error_count: Number of failed executions
        last_used: ISO timestamp of last execution (None if never used)
    """

    agent_id: str
    agent_name: str
    tool_id: str
    tool_instance: Any  # BaseTool from langchain_core.tools
    metadata: ToolMetadata
    binding_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    execution_count: int = 0
    total_execution_time: float = 0.0
    error_count: int = 0
    last_used: Optional[str] = None

    @property
    def average_execution_time(self) -> float:
        """
        Calculate average execution time per call.

        Returns:
            Average time in seconds, or 0.0 if never executed
        """
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time / self.execution_count

    @property
    def error_rate(self) -> float:
        """
        Calculate error rate as percentage.

        Returns:
            Error rate between 0.0 and 1.0
        """
        if self.execution_count == 0:
            return 0.0
        return self.error_count / self.execution_count

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert binding to dictionary format for export.

        Returns:
            Dictionary representation of binding
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "tool_id": self.tool_id,
            "binding_time": self.binding_time,
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "error_count": self.error_count,
            "last_used": self.last_used,
            "average_execution_time": self.average_execution_time,
            "error_rate": self.error_rate,
        }


@dataclass
class ToolCreationConfig:
    """
    Configuration for tool creation.

    This is a base configuration that specific tool creators can extend.

    Attributes:
        tool_name: Name of the tool to create
        config: Tool-specific configuration parameters
        node_id: Optional node ID for tracking
        node_name: Optional node name for display
    """

    tool_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    node_id: str = ""
    node_name: str = ""


@dataclass
class PerformanceStats:
    """
    Performance statistics for a tool.

    Tracks aggregated performance metrics across all executions.

    Attributes:
        tool_id: Tool identifier
        total_executions: Total number of executions
        total_time: Cumulative execution time in seconds
        error_count: Total number of errors
        avg_time: Average execution time
        min_time: Minimum execution time observed
        max_time: Maximum execution time observed
        last_updated: ISO timestamp of last update
    """

    tool_id: str
    total_executions: int = 0
    total_time: float = 0.0
    error_count: int = 0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def update(self, execution_time: float, success: bool = True) -> None:
        """
        Update statistics with a new execution.

        Args:
            execution_time: Time taken for this execution in seconds
            success: Whether the execution succeeded
        """
        self.total_executions += 1
        self.total_time += execution_time
        self.avg_time = self.total_time / self.total_executions

        if execution_time < self.min_time:
            self.min_time = execution_time
        if execution_time > self.max_time:
            self.max_time = execution_time

        if not success:
            self.error_count += 1

        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert stats to dictionary format.

        Returns:
            Dictionary representation of statistics
        """
        return {
            "tool_id": self.tool_id,
            "total_executions": self.total_executions,
            "total_time": self.total_time,
            "error_count": self.error_count,
            "avg_time": self.avg_time,
            "min_time": self.min_time if self.min_time != float("inf") else 0.0,
            "max_time": self.max_time,
            "error_rate": self.error_count / self.total_executions
            if self.total_executions > 0
            else 0.0,
            "last_updated": self.last_updated,
        }
