"""
Pydantic models for monitoring API responses.

This module defines type-safe response models for all monitoring endpoints,
providing better documentation and validation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentStatus(str, Enum):
    """Component status enumeration."""

    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# Health Check Models
class ComponentInfo(BaseModel):
    """Information about a system component."""

    graph_manager: str = Field(description="Graph manager status")
    execution_engine: str = Field(description="Execution engine status")
    database: str = Field(description="Database connection status")


class HealthCheckResponse(BaseModel):
    """Basic health check response."""

    status: HealthStatus = Field(description="Overall health status")
    timestamp: str = Field(description="ISO 8601 timestamp")
    components: ComponentInfo = Field(description="Component status information")
    warnings: List[str] = Field(
        default_factory=list, description="List of warning messages"
    )


class ConfigurationInfo(BaseModel):
    """System configuration information."""

    engine: str = Field(description="Execution engine type")
    checkpointing_enabled: bool = Field(description="Checkpointing feature status")
    memory_enabled: bool = Field(description="Memory feature status")


class SystemMetrics(BaseModel):
    """System-level metrics."""

    cpu_percent: float = Field(description="CPU usage percentage")
    memory_percent: float = Field(description="Memory usage percentage")
    process_memory_mb: float = Field(description="Process memory in MB")


class ApplicationMetrics(BaseModel):
    """Application-level metrics."""

    agent_executions: Optional[Dict[str, Any]] = Field(
        None, description="Agent execution summary"
    )
    tool_executions: Optional[Dict[str, Any]] = Field(
        None, description="Tool execution summary"
    )
    avg_execution_time_ms: Optional[Dict[str, Any]] = Field(
        None, description="Average execution time"
    )
    cache_hit_rate: float = Field(description="Cache hit rate")


class Alert(BaseModel):
    """System alert information."""

    level: AlertLevel = Field(description="Alert severity level")
    message: str = Field(description="Alert message")
    timestamp: str = Field(description="ISO 8601 timestamp")


class DetailedHealthCheckResponse(BaseModel):
    """Detailed health check with comprehensive information."""

    status: HealthStatus = Field(description="Overall health status")
    timestamp: str = Field(description="ISO 8601 timestamp")
    components: ComponentInfo = Field(description="Component status information")
    configuration: ConfigurationInfo = Field(description="System configuration")
    system_metrics: SystemMetrics = Field(description="System-level metrics")
    application_metrics: ApplicationMetrics = Field(
        description="Application-level metrics"
    )
    cache_statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Cache statistics"
    )
    migration_progress: Dict[str, Any] = Field(
        default_factory=dict, description="Migration progress"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of warning messages"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )
    alerts: List[Alert] = Field(default_factory=list, description="Active alerts")


# Metrics Models
class MetricExportResponse(BaseModel):
    """Response for metrics export in various formats."""

    format: str = Field(description="Export format (json, prometheus, statsd)")
    data: Any = Field(description="Metrics data in requested format")
    timestamp: str = Field(description="ISO 8601 timestamp")


class DashboardMetricsResponse(BaseModel):
    """Metrics formatted for dashboard display."""

    timestamp: str = Field(description="ISO 8601 timestamp")
    system: SystemMetrics = Field(description="System-level metrics")
    application: ApplicationMetrics = Field(description="Application-level metrics")
    alerts: List[Alert] = Field(default_factory=list, description="Active alerts")


# Status Models
class SystemStatusResponse(BaseModel):
    """System status and configuration."""

    engine: str = Field(description="Execution engine type")
    implementation: str = Field(description="Implementation type")
    checkpointing_enabled: bool = Field(description="Checkpointing feature status")
    memory_enabled: bool = Field(description="Memory feature status")
    cleanup_status: str = Field(description="Cleanup status")
    removed_files: int = Field(description="Number of removed files")
    timestamp: str = Field(description="ISO 8601 timestamp")


# Diagnostics Models
class DiagnosticCheck(BaseModel):
    """Single diagnostic check result."""

    status: str = Field(description="Check status (ok, error, warning)")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class GraphManagerCheck(DiagnosticCheck):
    """Graph manager diagnostic check."""

    graphs_loaded: Optional[int] = Field(None, description="Number of graphs loaded")
    graphs: Optional[List[str]] = Field(None, description="List of graph names")


class ExecutionEngineCheck(DiagnosticCheck):
    """Execution engine diagnostic check."""

    type: Optional[str] = Field(None, description="Engine type name")


class IntegrationCheck(DiagnosticCheck):
    """Integration status check."""

    engine: Optional[str] = Field(None, description="Engine type")
    implementation: Optional[str] = Field(None, description="Implementation type")
    cleanup: Optional[str] = Field(None, description="Cleanup status")


class MetricsCheck(DiagnosticCheck):
    """Metrics system check."""

    metrics_count: Optional[int] = Field(None, description="Number of metrics")
    collection_active: Optional[bool] = Field(
        None, description="Collection thread status"
    )


class DiagnosticsResponse(BaseModel):
    """System diagnostics response."""

    timestamp: str = Field(description="ISO 8601 timestamp")
    overall_status: HealthStatus = Field(description="Overall diagnostic status")
    checks: Dict[str, DiagnosticCheck] = Field(
        description="Individual diagnostic checks"
    )


# Cache Models
class CacheClearResponse(BaseModel):
    """Cache clear operation response."""

    status: str = Field(description="Operation status")
    message: str = Field(description="Status message")
    timestamp: str = Field(description="ISO 8601 timestamp")
    caches_cleared: List[str] = Field(
        default_factory=list, description="List of cleared caches"
    )


# Optimization Models
class OptimizationResponse(BaseModel):
    """Performance optimization response."""

    status: str = Field(description="Operation status")
    message: str = Field(description="Status message")
    timestamp: str = Field(description="ISO 8601 timestamp")
    optimizations_applied: List[str] = Field(
        default_factory=list, description="List of optimizations applied"
    )


# Feature Flags Models
class FeatureFlagsResponse(BaseModel):
    """Feature flags configuration."""

    use_unified_state: bool = Field(description="Unified state feature")
    use_compile_time_tools: bool = Field(description="Compile-time tools feature")
    cache_subgraphs: bool = Field(description="Subgraph caching feature")
    enable_performance_tracking: bool = Field(
        description="Performance tracking feature"
    )
    parallel_tool_execution: bool = Field(description="Parallel tool execution feature")
    use_memory: bool = Field(description="Memory feature")
    timestamp: str = Field(description="ISO 8601 timestamp")


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: str = Field(description="ISO 8601 timestamp")
