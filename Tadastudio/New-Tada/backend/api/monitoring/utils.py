"""
Shared utilities for monitoring API.

This module provides common functionality including error handling,
response formatting, and cache management operations.
"""

from datetime import datetime, timezone
from functools import wraps
from typing import Any

from fastapi import HTTPException

from ...services.config import get_logger
from ...services.dependency_injection import get_graph_manager
from ...services.metrics import get_metrics_manager
from .models import CacheClearResponse, ErrorResponse, OptimizationResponse


logger = get_logger("monitoring.utils")


def handle_monitoring_errors(endpoint_name: str):
    """
    Handle errors in monitoring endpoints.

    Args:
        endpoint_name: Name of the endpoint for logging

    Returns:
        Decorated function with error handling
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as e:
                logger.error(f"[MONITORING-{endpoint_name.upper()}] Error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"{endpoint_name} failed: {str(e)}",
                )

        return wrapper

    return decorator


def create_error_response(
    error_type: str, message: str, detail: str | None = None
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        error_type: Type of error
        message: Error message
        detail: Additional error details

    Returns:
        ErrorResponse model
    """
    return ErrorResponse(
        error=error_type,
        message=message,
        detail=detail,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def clear_system_caches() -> CacheClearResponse:
    """
    Clear all system caches.

    Returns:
        CacheClearResponse with operation status
    """
    cleared_caches = []

    try:
        # Clear graph manager caches
        graph_manager = get_graph_manager()
        if hasattr(graph_manager, "clear_caches"):
            graph_manager.clear_caches()
            cleared_caches.append("graph_manager")
            logger.info("[MONITORING-CACHE] Cleared graph manager caches")

    except Exception as e:
        logger.warning(f"[MONITORING-CACHE] Failed to clear graph manager cache: {e}")

    # Clear monitoring internal caches
    try:
        from .services.health import _cache, _cache_lock
        from .services.system_info import clear_cache as clear_sysinfo_cache

        clear_sysinfo_cache()
        cleared_caches.append("system_info")

        with _cache_lock:
            _cache.clear()
            cleared_caches.append("health_checks")

        logger.info("[MONITORING-CACHE] Cleared monitoring caches")

    except Exception as e:
        logger.warning(f"[MONITORING-CACHE] Failed to clear monitoring caches: {e}")

    return CacheClearResponse(
        status="success",
        message=f"Cleared {len(cleared_caches)} cache(s)",
        timestamp=datetime.now(timezone.utc).isoformat(),
        caches_cleared=cleared_caches,
    )


def optimize_system_performance() -> OptimizationResponse:
    """
    Trigger system performance optimizations.

    Returns:
        OptimizationResponse with operation status
    """
    optimizations_applied = []

    try:
        # Optimize graph manager
        graph_manager = get_graph_manager()
        if hasattr(graph_manager, "optimize_performance"):
            graph_manager.optimize_performance()
            optimizations_applied.append("graph_manager_optimization")
            logger.info("[MONITORING-OPTIMIZE] Applied graph manager optimizations")

    except Exception as e:
        logger.warning(f"[MONITORING-OPTIMIZE] Failed to optimize graph manager: {e}")

    # Could add more optimization operations here
    # e.g., garbage collection, memory cleanup, etc.

    return OptimizationResponse(
        status="success",
        message=f"Applied {len(optimizations_applied)} optimization(s)",
        timestamp=datetime.now(timezone.utc).isoformat(),
        optimizations_applied=optimizations_applied,
    )


def validate_export_format(format_type: str) -> bool:
    """
    Validate metrics export format.

    Args:
        format_type: Format to validate (json, prometheus, statsd)

    Returns:
        True if valid, False otherwise
    """
    valid_formats = {"json", "prometheus", "statsd"}
    return format_type.lower() in valid_formats


def get_metrics_export(format_type: str) -> Any:
    """
    Export metrics in requested format.

    Args:
        format_type: Export format (json, prometheus, statsd)

    Returns:
        Metrics in requested format

    Raises:
        ValueError: If format is invalid
    """
    if not validate_export_format(format_type):
        raise ValueError(
            f"Invalid format: {format_type}. Must be json, prometheus, or statsd"
        )

    metrics_manager = get_metrics_manager()

    if format_type == "prometheus":
        return metrics_manager.export("prometheus")
    elif format_type == "statsd":
        return {"commands": metrics_manager.statsd_exporter.export()}
    else:
        return metrics_manager.collector.get_all_metrics()
