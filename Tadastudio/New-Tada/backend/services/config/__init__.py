"""
Configuration utilities for the backend application.

This module consolidates all configuration-related utilities including:
- URL configuration for API endpoints
- Execution engine configuration
- Logging system configuration
"""

# Execution Configuration
from .execution import ExecutionConfig, create_execution_engine

# Logging Configuration
from .logging import get_logger, setup_logging

# URL Configuration
from .url import get_api_base_url, get_endpoint_url


__all__ = [
    # URL utilities
    "get_api_base_url",
    "get_endpoint_url",
    # Execution utilities
    "ExecutionConfig",
    "create_execution_engine",
    # Logging utilities
    "setup_logging",
    "get_logger",
]
