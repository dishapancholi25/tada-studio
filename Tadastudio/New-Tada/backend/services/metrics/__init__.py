"""
Metrics collection and monitoring system.

This package provides comprehensive metrics collection, aggregation,
and export capabilities for monitoring application and system performance.

Basic Usage:
    from backend.services.metrics import get_metrics_manager

    metrics = get_metrics_manager()

    # Record application metrics
    metrics.app_metrics.record_execution(
        graph_name="my_graph",
        agent_name="my_agent",
        duration_ms=150.0,
        success=True,
        token_count=500
    )

    # Export metrics
    prometheus_data = metrics.export("prometheus")
    json_data = metrics.export("json")
"""

# Core components (for advanced usage)
from .collector import MetricCollector
from .collectors import (
    ApplicationMetricsCollector,
    MetricCollectorInterface,
    SystemMetricsCollector,
)
from .exporters import JSONExporter, MetricsExporter, PrometheusExporter, StatsDExporter

# Main API
from .manager import MetricsManager, get_metrics_manager, reset_metrics

# Models and types
from .models import (
    ExportError,
    InvalidMetricError,
    MetricPoint,
    MetricsError,
    MetricSummary,
    MetricType,
)


__all__ = [
    # Main API
    "get_metrics_manager",
    "reset_metrics",
    "MetricsManager",
    # Models
    "MetricType",
    "MetricPoint",
    "MetricSummary",
    "MetricsError",
    "InvalidMetricError",
    "ExportError",
    # Core components
    "MetricCollector",
    "MetricCollectorInterface",
    "SystemMetricsCollector",
    "ApplicationMetricsCollector",
    "MetricsExporter",
    "PrometheusExporter",
    "JSONExporter",
    "StatsDExporter",
]
