"""
Health check service for monitoring system components.

This module provides health check functionality for various system components,
including basic and detailed health checks with caching support.
"""

import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict

from ....services.config import ExecutionConfig, get_logger
from ....services.dependency_injection import get_execution_engine, get_graph_manager
from ....services.metrics import get_metrics_manager
from ..models import (
    Alert,
    AlertLevel,
    ApplicationMetrics,
    ComponentInfo,
    ConfigurationInfo,
    DetailedHealthCheckResponse,
    HealthCheckResponse,
    HealthStatus,
    SystemMetrics,
)


logger = get_logger("monitoring.health")

# Simple cache implementation
_cache: Dict[str, tuple[Any, float]] = {}
_cache_lock = Lock()
CACHE_TTL = 5.0  # 5 seconds TTL for health checks


def _get_cached(key: str, ttl: float = CACHE_TTL) -> Any | None:
    """
    Get cached value if not expired.

    Args:
        key: Cache key
        ttl: Time to live in seconds

    Returns:
        Cached value or None if expired/missing
    """
    with _cache_lock:
        if key in _cache:
            value, timestamp = _cache[key]
            if time.time() - timestamp < ttl:
                return value
            del _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    """
    Set cached value with timestamp.

    Args:
        key: Cache key
        value: Value to cache
    """
    with _cache_lock:
        _cache[key] = (value, time.time())


def get_component_status() -> ComponentInfo:
    """
    Get status of system components.

    Returns:
        ComponentInfo with component statuses
    """
    # Try cache first
    cached = _get_cached("component_status")
    if cached:
        return cached

    try:
        # Check if components are available
        get_graph_manager()
        get_execution_engine()

        component_info = ComponentInfo(
            graph_manager="ready", execution_engine="ready", database="connected"
        )

        _set_cached("component_status", component_info)
        return component_info

    except Exception as e:
        logger.error(f"[MONITORING-HEALTH] Error checking components: {e}")
        return ComponentInfo(
            graph_manager="error", execution_engine="error", database="unknown"
        )


def get_basic_health() -> HealthCheckResponse:
    """
    Perform basic health check.

    Returns:
        HealthCheckResponse with basic health status
    """
    try:
        components = get_component_status()

        # Determine overall status
        status = HealthStatus.HEALTHY
        if (
            components.graph_manager == "error"
            or components.execution_engine == "error"
        ):
            status = HealthStatus.UNHEALTHY
        elif components.database == "unknown":
            status = HealthStatus.DEGRADED

        return HealthCheckResponse(
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=components,
            warnings=[],
        )

    except Exception as e:
        logger.error(f"[MONITORING-HEALTH] Basic health check failed: {e}")
        return HealthCheckResponse(
            status=HealthStatus.UNHEALTHY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=ComponentInfo(
                graph_manager="error", execution_engine="error", database="error"
            ),
            warnings=[f"Health check error: {str(e)}"],
        )


def get_detailed_health() -> DetailedHealthCheckResponse:
    """
    Perform detailed health check with comprehensive information.

    Returns:
        DetailedHealthCheckResponse with detailed health data
    """
    try:
        # Get basic health
        basic_health = get_basic_health()

        # Get metrics
        metrics_manager = get_metrics_manager()
        dashboard_data = metrics_manager.get_dashboard_data()

        # Extract system metrics
        system_metrics = SystemMetrics(
            cpu_percent=dashboard_data.get("system", {}).get("cpu_percent", 0.0),
            memory_percent=dashboard_data.get("system", {}).get("memory_percent", 0.0),
            process_memory_mb=dashboard_data.get("system", {}).get(
                "process_memory_mb", 0.0
            ),
        )

        # Extract application metrics
        app_metrics_data = dashboard_data.get("application", {})
        application_metrics = ApplicationMetrics(
            agent_executions=app_metrics_data.get("agent_executions"),
            tool_executions=app_metrics_data.get("tool_executions"),
            avg_execution_time_ms=app_metrics_data.get("avg_execution_time_ms"),
            cache_hit_rate=app_metrics_data.get("cache_hit_rate", 0.0),
        )

        # Parse alerts
        alerts = []
        for alert_data in dashboard_data.get("alerts", []):
            try:
                alert = Alert(
                    level=AlertLevel(alert_data.get("level", "info")),
                    message=alert_data.get("message", ""),
                    timestamp=alert_data.get("timestamp", ""),
                )
                alerts.append(alert)
            except (ValueError, KeyError) as e:
                logger.warning(f"[MONITORING-HEALTH] Failed to parse alert: {e}")

        # Get configuration
        config = ConfigurationInfo(
            engine="langgraph",
            checkpointing_enabled=ExecutionConfig.use_checkpointing(),
            memory_enabled=ExecutionConfig.use_memory(),
        )

        return DetailedHealthCheckResponse(
            status=basic_health.status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=basic_health.components,
            configuration=config,
            system_metrics=system_metrics,
            application_metrics=application_metrics,
            cache_statistics={},
            migration_progress={},
            warnings=[],
            errors=[],
            alerts=alerts,
        )

    except Exception as e:
        logger.error(f"[MONITORING-HEALTH] Detailed health check failed: {e}")
        # Return minimal response on error
        return DetailedHealthCheckResponse(
            status=HealthStatus.UNHEALTHY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=ComponentInfo(
                graph_manager="error", execution_engine="error", database="error"
            ),
            configuration=ConfigurationInfo(
                engine="langgraph",
                checkpointing_enabled=False,
                memory_enabled=False,
            ),
            system_metrics=SystemMetrics(
                cpu_percent=0.0, memory_percent=0.0, process_memory_mb=0.0
            ),
            application_metrics=ApplicationMetrics(cache_hit_rate=0.0),
            errors=[f"Health check error: {str(e)}"],
        )
