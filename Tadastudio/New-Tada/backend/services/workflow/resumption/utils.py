"""
Utility functions and constants for subworkflow resumption.

This module provides shared utilities used across the resumption service.
"""

import logging
from typing import Optional


# Logger configuration
logger = logging.getLogger(__name__)

# Constants
LOG_PREFIX = "[SUBWF-RESUME]"
DEFAULT_RECURSION_LIMIT = 50


def parse_parent_graph_name(parent_thread_id: str) -> str:
    """
    Parse the parent graph name from a thread ID.

    Args:
        parent_thread_id: The parent workflow's thread ID

    Returns:
        The parsed graph name, or "SubCheckpoint" as fallback
    """
    if "_" in parent_thread_id:
        return parent_thread_id.split("_")[-1]
    return "SubCheckpoint"


def log_section_header(title: str) -> None:
    """
    Log a section header for better log readability.

    Args:
        title: The section title
    """
    logger.info(f"{LOG_PREFIX} {'=' * 50}")
    logger.info(f"{LOG_PREFIX} {title}")
    logger.info(f"{LOG_PREFIX} {'=' * 50}")


def log_info(message: str, **kwargs) -> None:
    """
    Log an info message with the standard prefix.

    Args:
        message: The message to log
        **kwargs: Additional key-value pairs to include in the log
    """
    if kwargs:
        formatted_kwargs = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"{LOG_PREFIX} {message} | {formatted_kwargs}")
    else:
        logger.info(f"{LOG_PREFIX} {message}")


def log_error(message: str, exc: Optional[Exception] = None) -> None:
    """
    Log an error message with the standard prefix.

    Args:
        message: The error message to log
        exc: Optional exception to include in the log
    """
    logger.error(f"{LOG_PREFIX} {message}", exc_info=exc is not None)
