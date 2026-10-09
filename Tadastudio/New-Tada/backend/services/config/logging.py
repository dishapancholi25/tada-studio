"""Logging configuration and setup."""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


# Global flag to prevent multiple setup calls
_logging_initialized = False


def setup_logging(log_level=None):
    """Set up comprehensive logging configuration for the application.

    Args:
        log_level: Logging level to use. If None, reads from LOG_LEVEL env var (defaults to INFO)
    """
    global _logging_initialized

    # Prevent duplicate initialization
    if _logging_initialized:
        return logging.getLogger()

    # If log_level not provided, read from environment variable
    if log_level is None:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

    # Use absolute path for logs directory to avoid issues with different working directories
    working_dir = Path(os.getenv("WORKING_DIR", Path.cwd()))
    log_dir = working_dir / "logs"
    log_dir.mkdir(exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # File handler for all logs (rotate daily, keep 7 backups)
    file_handler = TimedRotatingFileHandler(
        log_dir / "app.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Console handler with UTF-8 encoding for Windows
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    # Set encoding for console handler to handle Unicode characters
    if hasattr(console_handler.stream, "reconfigure"):
        console_handler.stream.reconfigure(encoding="utf-8")
    root_logger.addHandler(console_handler)

    # Execution-specific file handler
    execution_handler = TimedRotatingFileHandler(
        log_dir / "execution.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    execution_handler.setLevel(logging.DEBUG)
    execution_handler.setFormatter(detailed_formatter)

    # API-specific file handler
    api_handler = TimedRotatingFileHandler(
        log_dir / "api.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(detailed_formatter)

    # Configure specific loggers
    execution_logger = logging.getLogger("execution")
    execution_logger.handlers.clear()  # Clear any existing handlers
    execution_logger.addHandler(execution_handler)
    execution_logger.setLevel(logging.DEBUG)
    execution_logger.propagate = False  # Prevent duplicate logging

    api_logger = logging.getLogger("api")
    api_logger.handlers.clear()  # Clear any existing handlers
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.DEBUG)
    api_logger.propagate = False  # Prevent duplicate logging

    # Database logger
    db_logger = logging.getLogger("database")
    db_logger.setLevel(logging.INFO)

    # Mark as initialized
    _logging_initialized = True

    logging.info(
        f"Logging system initialized successfully with level: {logging.getLevelName(log_level)}"
    )
    return root_logger


def get_logger(name: str):
    """Get a logger with the specified name."""
    return logging.getLogger(name)
