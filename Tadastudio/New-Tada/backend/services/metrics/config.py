"""
Configuration constants for metrics collection.

This module centralizes all configuration values for the metrics system,
including collection intervals, thresholds, and limits.
"""

import os


# Collection Configuration
DEFAULT_MAX_HISTORY = int(os.getenv("METRICS_MAX_HISTORY", "10000"))
DEFAULT_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "30"))

# Alert Thresholds
CPU_WARNING_THRESHOLD = float(os.getenv("METRICS_CPU_WARNING", "80.0"))
MEMORY_CRITICAL_THRESHOLD = float(os.getenv("METRICS_MEMORY_CRITICAL", "90.0"))
ERROR_RATE_WARNING_COUNT = int(os.getenv("METRICS_ERROR_WARNING_COUNT", "10"))

# Time Windows (seconds)
DEFAULT_SUMMARY_WINDOW = 300  # 5 minutes
CACHE_HIT_RATE_WINDOW = 300  # 5 minutes
ERROR_RATE_WINDOW = 300  # 5 minutes

# Metric Name Validation
METRIC_NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_.]*$"
MAX_METRIC_NAME_LENGTH = 200
MAX_LABEL_COUNT = 20
MAX_LABEL_KEY_LENGTH = 50
MAX_LABEL_VALUE_LENGTH = 200

# Export Configuration
PROMETHEUS_TIMESTAMP_MULTIPLIER = 1000  # Convert to milliseconds

# Logging Configuration
LOG_PREFIX = "[METRICS]"
