"""
System information service.

This module provides system-level information including platform details,
resource usage, and process information. Consolidates system info logic
from config_api and monitoring_api.
"""

import os
import platform
import sys
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict

import psutil

from ....services.config import ExecutionConfig, get_logger
from ..models import SystemStatusResponse


logger = get_logger("monitoring.system_info")

# Simple cache for system info
_system_info_cache: tuple[Dict[str, Any], float] | None = None
_cache_lock = Lock()
SYSTEM_INFO_CACHE_TTL = 10.0  # 10 seconds


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information.

    Returns:
        Dictionary with platform, resources, and process information

    Note:
        Results are cached for 10 seconds to avoid excessive psutil calls.
    """
    global _system_info_cache

    # Check cache
    with _cache_lock:
        if _system_info_cache is not None:
            cached_data, cached_time = _system_info_cache
            if time.time() - cached_time < SYSTEM_INFO_CACHE_TTL:
                logger.debug("[MONITORING-SYSINFO] Returning cached system info")
                return cached_data

    logger.debug("[MONITORING-SYSINFO] Collecting fresh system info")

    try:
        # Get memory info
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version,
            },
            "resources": {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_percent": memory.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_percent": disk.percent,
            },
            "process": {
                "pid": os.getpid(),
                "memory_mb": round(psutil.Process().memory_info().rss / (1024**2), 2),
            },
        }

        # Update cache
        with _cache_lock:
            _system_info_cache = (info, time.time())

        return info

    except Exception as e:
        logger.error(f"[MONITORING-SYSINFO] Failed to get system info: {e}")
        # Return minimal info on error
        return {
            "platform": {
                "system": platform.system(),
                "python_version": sys.version,
            },
            "resources": {},
            "process": {"pid": os.getpid()},
            "error": "Failed to collect system info",
        }


def get_system_status() -> SystemStatusResponse:
    """
    Get current system status and configuration.

    Returns:
        SystemStatusResponse with status information
    """
    try:
        return SystemStatusResponse(
            engine="langgraph",
            implementation="standard",
            checkpointing_enabled=ExecutionConfig.use_checkpointing(),
            memory_enabled=ExecutionConfig.use_memory(),
            cleanup_status="complete",
            removed_files=26,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"[MONITORING-SYSINFO] Failed to get system status: {e}")
        # Return minimal status on error
        return SystemStatusResponse(
            engine="langgraph",
            implementation="standard",
            checkpointing_enabled=False,
            memory_enabled=False,
            cleanup_status="error",
            removed_files=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def clear_cache() -> None:
    """Clear the system info cache."""
    global _system_info_cache
    with _cache_lock:
        _system_info_cache = None
    logger.debug("[MONITORING-SYSINFO] Cache cleared")
