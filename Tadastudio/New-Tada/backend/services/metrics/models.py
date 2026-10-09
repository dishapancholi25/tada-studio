"""
Data models for metrics collection.

This module defines enums, dataclasses, and type definitions used across
the metrics system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class MetricType(Enum):
    """Types of metrics we collect."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """
    Single metric data point.

    Attributes:
        timestamp: Unix timestamp when metric was recorded
        value: Numeric value of the metric
        labels: Optional key-value labels for metric dimensions
    """

    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """
    Summary statistics for a metric.

    Provides aggregated statistics including count, sum, min, max,
    average, and percentiles for a collection of metric values.

    Attributes:
        count: Number of data points
        sum: Sum of all values
        min: Minimum value
        max: Maximum value
        avg: Average value
        p50: 50th percentile (median)
        p95: 95th percentile
        p99: 99th percentile
    """

    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float


class MetricsError(Exception):
    """Base exception for metrics-related errors."""

    pass


class InvalidMetricError(MetricsError):
    """Raised when metric name or value is invalid."""

    pass


class ExportError(MetricsError):
    """Raised when metric export fails."""

    pass
