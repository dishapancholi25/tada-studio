"""Database engine creation and connection pool management.

This module handles SQLAlchemy engine creation with optimized connection pool
settings for reliability and performance.
"""

import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import DatabaseConfig, LOG_PREFIX

logger = logging.getLogger(__name__)

# Module-level engine instance (created on first access)
_engine: Optional[Engine] = None
_config: Optional[DatabaseConfig] = None


def create_database_engine(config: Optional[DatabaseConfig] = None) -> Engine:
    """Create SQLAlchemy engine with connection pool settings.

    Creates a PostgreSQL engine with optimized connection pool settings
    for Azure/cloud deployments and reliability.

    Args:
        config: Database configuration. If None, loads from environment.

    Returns:
        SQLAlchemy Engine instance

    Raises:
        ValueError: If database configuration is invalid
    """
    if config is None:
        config = DatabaseConfig.from_env()

    logger.info("%s Creating database engine", LOG_PREFIX)
    config.log_configuration()

    # Create SQLAlchemy engine with connection pool settings for reliability
    # Azure-optimized settings to prevent timeout issues
    engine = create_engine(
        config.connection_string,
        pool_pre_ping=config.pool_pre_ping,  # Test connections before using them
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_recycle=config.pool_recycle,
        pool_timeout=config.pool_timeout,
        pool_use_lifo=config.pool_use_lifo,
        echo_pool=False,  # Set to True for debugging connection issues
        connect_args=config.get_connect_args(),
    )

    logger.info("%s Database engine created successfully", LOG_PREFIX)
    return engine


def get_engine(config: Optional[DatabaseConfig] = None) -> Engine:
    """Get or create the global database engine.

    Returns a singleton engine instance. Creates it on first call.

    Args:
        config: Database configuration. Only used on first call.

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine, _config

    if _engine is None:
        if config is None:
            config = DatabaseConfig.from_env()
        _config = config
        _engine = create_database_engine(config)

    return _engine


def reset_engine() -> None:
    """Reset the global engine instance.

    Useful for testing or reconfiguration. Disposes of the current engine
    and clears the global reference.
    """
    global _engine, _config

    if _engine is not None:
        logger.info("%s Disposing database engine", LOG_PREFIX)
        _engine.dispose()
        _engine = None
        _config = None
