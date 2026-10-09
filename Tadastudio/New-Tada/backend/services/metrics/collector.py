"""
Core metric collector.

This module provides the main MetricCollector class that stores and
aggregates metric data points.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Dict, Optional

from ..config import get_logger
from .config import DEFAULT_MAX_HISTORY
from .models import MetricPoint, MetricSummary, MetricType
from .utils import (
    calculate_percentile,
    validate_labels,
    validate_metric_name,
    validate_metric_value,
)


logger = get_logger("metrics.collector")


class MetricCollector:
    """
    Collects and aggregates metrics.

    Thread-safe collector that stores metric data points with configurable
    history limits. Provides methods for recording different metric types
    and calculating summary statistics.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY):
        """
        Initialize metric collector.

        Args:
            max_history: Maximum number of data points to keep per metric
        """
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.metric_types: Dict[str, MetricType] = {}
        self.lock = threading.Lock()
        logger.info(f"[METRICS-COLLECTOR] Initialized with max_history={max_history}")

    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels for metric dimensions

        Raises:
            InvalidMetricError: If metric name, value, or labels are invalid
        """
        # Validate inputs
        validate_metric_name(name)
        validate_metric_value(value)
        if labels:
            validate_labels(labels)

        with self.lock:
            self.metric_types[name] = metric_type
            self.metrics[name].append(
                MetricPoint(timestamp=time.time(), value=value, labels=labels or {})
            )

        logger.debug(f"[METRICS-COLLECTOR] Recorded {metric_type.value} {name}={value}")

    def increment(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            value: Increment value (default 1.0)
            labels: Optional labels
        """
        self.record(name, value, MetricType.COUNTER, labels)

    def gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Set a gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels
        """
        self.record(name, value, MetricType.GAUGE, labels)

    def histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a histogram value.

        Args:
            name: Metric name
            value: Value to record
            labels: Optional labels
        """
        self.record(name, value, MetricType.HISTOGRAM, labels)

    def get_summary(
        self, name: str, window_seconds: Optional[int] = None
    ) -> Optional[MetricSummary]:
        """
        Get summary statistics for a metric.

        Args:
            name: Metric name
            window_seconds: Time window for summary (None for all data)

        Returns:
            Summary statistics or None if metric not found
        """
        with self.lock:
            if name not in self.metrics:
                return None

            points = list(self.metrics[name])
            if not points:
                return None

            # Filter by time window if specified
            if window_seconds:
                cutoff = time.time() - window_seconds
                points = [p for p in points if p.timestamp >= cutoff]

            if not points:
                return None

            values = [p.value for p in points]
            values.sort()

            return MetricSummary(
                count=len(values),
                sum=sum(values),
                min=min(values),
                max=max(values),
                avg=sum(values) / len(values),
                p50=calculate_percentile(values, 0.50),
                p95=calculate_percentile(values, 0.95),
                p99=calculate_percentile(values, 0.99),
            )

    def get_all_metrics(self) -> Dict[str, dict]:
        """
        Get all metrics and their current values.

        Returns:
            Dictionary mapping metric names to their latest data
        """
        with self.lock:
            result = {}
            for name, points in self.metrics.items():
                if points:
                    latest = points[-1]
                    result[name] = {
                        "value": latest.value,
                        "timestamp": latest.timestamp,
                        "type": self.metric_types.get(name, MetricType.GAUGE).value,
                        "labels": latest.labels,
                    }
            return result

    def clear(self) -> None:
        """Clear all metrics (primarily for testing)."""
        with self.lock:
            self.metrics.clear()
            self.metric_types.clear()
        logger.info("[METRICS-COLLECTOR] All metrics cleared")
