"""
Metrics manager for coordinating metric collection and export.

This module provides the main MetricsManager class that coordinates
collectors, exporters, and background collection.
"""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import get_logger
from .collector import MetricCollector
from .collectors import ApplicationMetricsCollector, SystemMetricsCollector
from .config import (
    CPU_WARNING_THRESHOLD,
    DEFAULT_COLLECTION_INTERVAL,
    ERROR_RATE_WARNING_COUNT,
    ERROR_RATE_WINDOW,
    MEMORY_CRITICAL_THRESHOLD,
)
from .exporters import JSONExporter, PrometheusExporter, StatsDExporter


logger = get_logger("metrics.manager")


class MetricsManager:
    """
    Main metrics management class.

    Singleton manager that coordinates metric collection, aggregation,
    and export. Manages background system metric collection and provides
    unified access to all metrics functionality.
    """

    _instance: Optional["MetricsManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize metrics manager (only once due to singleton)."""
        if not hasattr(self, "initialized"):
            # Core collector
            self.collector = MetricCollector()

            # Specialized collectors
            self.system_metrics = SystemMetricsCollector(self.collector)
            self.app_metrics = ApplicationMetricsCollector(self.collector)

            # Exporters
            self.prometheus_exporter = PrometheusExporter(
                self.collector.get_all_metrics
            )
            self.json_exporter = JSONExporter(self.collector.get_all_metrics)
            self.statsd_exporter = StatsDExporter(self.collector.get_all_metrics)

            # Background collection
            self.collection_thread: Optional[threading.Thread] = None
            self._stop_event = threading.Event()

            self.initialized = True
            logger.info("[METRICS-MANAGER] Metrics manager initialized")

    def start_collection(self, interval: int = DEFAULT_COLLECTION_INTERVAL) -> None:
        """
        Start background system metrics collection.

        Args:
            interval: Collection interval in seconds
        """
        if self.collection_thread and self.collection_thread.is_alive():
            logger.warning("[METRICS-MANAGER] Collection already running")
            return

        def collect_loop():
            while not self._stop_event.is_set():
                try:
                    self.system_metrics.collect()
                except Exception as e:
                    logger.error(
                        f"[METRICS-MANAGER] Error collecting system metrics: {e}"
                    )

                self._stop_event.wait(interval)

        self.collection_thread = threading.Thread(target=collect_loop, daemon=True)
        self.collection_thread.start()
        logger.info(f"[METRICS-MANAGER] Started collection with {interval}s interval")

    def stop_collection(self) -> None:
        """Stop background metrics collection."""
        self._stop_event.set()
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("[METRICS-MANAGER] Stopped metrics collection")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get metrics formatted for dashboard display.

        Returns:
            Dashboard-ready metrics data including system, application,
            and alert information
        """
        # Collect current system metrics
        self.system_metrics.collect()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": self.collector.get_all_metrics()
                .get("system.cpu.percent", {})
                .get("value", 0),
                "memory_percent": self.collector.get_all_metrics()
                .get("system.memory.percent", {})
                .get("value", 0),
                "process_memory_mb": self.collector.get_all_metrics()
                .get("process.memory.rss_mb", {})
                .get("value", 0),
            },
            "application": {
                "agent_executions": self.collector.get_summary(
                    "agent.execution.count", window_seconds=300
                ),
                "tool_executions": self.collector.get_summary(
                    "tool.execution.count", window_seconds=300
                ),
                "avg_execution_time_ms": self.collector.get_summary(
                    "agent.execution.duration_ms", window_seconds=300
                ),
                "cache_hit_rate": self._calculate_cache_hit_rate(),
            },
            "alerts": self._check_alerts(),
        }

    def _calculate_cache_hit_rate(self) -> float:
        """
        Calculate overall cache hit rate.

        Returns:
            Cache hit rate as a float between 0 and 1
        """
        hits_summary = self.collector.get_summary("tool.cache.hits", window_seconds=300)
        misses_summary = self.collector.get_summary(
            "tool.cache.misses", window_seconds=300
        )

        if not hits_summary or not misses_summary:
            return 0.0

        total_hits = hits_summary.sum
        total_misses = misses_summary.sum

        if total_hits + total_misses == 0:
            return 0.0

        return total_hits / (total_hits + total_misses)

    def _check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions.

        Returns:
            List of alert dictionaries with level, message, and timestamp
        """
        alerts = []

        # Check CPU usage
        cpu_metric = self.collector.get_all_metrics().get("system.cpu.percent", {})
        if cpu_metric and cpu_metric.get("value", 0) > CPU_WARNING_THRESHOLD:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"High CPU usage: {cpu_metric['value']:.1f}%",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Check memory usage
        memory_metric = self.collector.get_all_metrics().get(
            "system.memory.percent", {}
        )
        if memory_metric and memory_metric.get("value", 0) > MEMORY_CRITICAL_THRESHOLD:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"Critical memory usage: {memory_metric['value']:.1f}%",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Check error rate
        error_summary = self.collector.get_summary(
            "agent.execution.errors", window_seconds=ERROR_RATE_WINDOW
        )
        if error_summary and error_summary.count > ERROR_RATE_WARNING_COUNT:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"High error rate: {error_summary.count} errors in last 5 minutes",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        return alerts

    def export(self, export_format: str = "json") -> Any:
        """
        Export metrics in specified format.

        Args:
            export_format: Export format (json, prometheus, statsd)

        Returns:
            Formatted metrics in requested format
        """
        if export_format == "prometheus":
            return self.prometheus_exporter.export()
        elif export_format == "statsd":
            return self.statsd_exporter.export()
        else:
            return self.json_exporter.export()


# Global metrics manager instance
_metrics_manager: Optional[MetricsManager] = None


def get_metrics_manager() -> MetricsManager:
    """
    Get the global metrics manager instance.

    Returns:
        Singleton MetricsManager instance
    """
    global _metrics_manager
    if _metrics_manager is None:
        _metrics_manager = MetricsManager()
        _metrics_manager.start_collection()
    return _metrics_manager


def reset_metrics() -> None:
    """
    Reset metrics (mainly for testing).

    Stops collection and clears the global manager instance.
    """
    global _metrics_manager
    if _metrics_manager:
        _metrics_manager.stop_collection()
    _metrics_manager = None
    logger.info("[METRICS-MANAGER] Metrics reset")
