"""Database configuration management.

This module handles all database configuration including environment variables,
connection pool settings, and connection parameters.
"""

import logging
import os
from dataclasses import dataclass
from urllib.parse import quote_plus
from typing import Optional

# Logging prefix for structured logging
LOG_PREFIX = "[DATABASE]"

logger = logging.getLogger(__name__)


def _get_int_env(var_name: str, default: int) -> int:
    """Read integer environment variables with safe fallback.

    Args:
        var_name: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Integer value from environment or default
    """
    value = os.getenv(var_name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(
            "%s Invalid integer for %s=%r. Falling back to %s.",
            LOG_PREFIX,
            var_name,
            value,
            default,
        )
        return default


def _get_bool_env(var_name: str, default: bool) -> bool:
    """Read boolean environment variables with safe fallback.

    Args:
        var_name: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value from environment or default
    """
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


@dataclass
class DatabaseConfig:
    """Database configuration with validation.

    Encapsulates all database connection and pool configuration settings.
    Loads from environment variables with sensible defaults.

    Attributes:
        connection_string: PostgreSQL connection string
        pool_size: Size of the connection pool
        max_overflow: Maximum overflow connections beyond pool_size
        pool_timeout: Timeout for getting connection from pool (seconds)
        pool_recycle: Connection recycle time (seconds)
        pool_use_lifo: Use LIFO for connection pool
        pool_pre_ping: Test connections before using them
        connect_timeout: Connection timeout (seconds)
        statement_timeout_ms: SQL statement timeout (milliseconds)
        keepalives_idle: TCP keepalive idle time (seconds)
        keepalives_interval: TCP keepalive interval (seconds)
        keepalives_count: TCP keepalive probe count
        application_name: Application name for PostgreSQL
    """

    connection_string: str
    pool_size: int = 5
    max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 180
    pool_use_lifo: bool = True
    pool_pre_ping: bool = True
    connect_timeout: int = 10
    statement_timeout_ms: int = 600000
    keepalives_idle: int = 30
    keepalives_interval: int = 10
    keepalives_count: int = 5
    application_name: Optional[str] = "langgraph-backend"

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create DatabaseConfig from environment variables.

        Reads database configuration from environment variables with fallback
        to sensible defaults. Supports both DATABASE_URL and component-based
        configuration.

        Returns:
            DatabaseConfig instance

        Raises:
            ValueError: If no database configuration is found
        """
        # Check for DATABASE_URL first (standard for deployments)
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            connection_string = database_url
            logger.info("%s Using DATABASE_URL for connection", LOG_PREFIX)
        else:
            # Fall back to building from components
            pg_host = os.getenv("KEY_POSTGRES_HOST", "localhost")
            pg_dbname = os.getenv("KEY_POSTGRES_DBNAME", "langgraph")
            pg_user = os.getenv("KEY_POSTGRES_USER", "postgres")
            pg_password = os.getenv("KEY_POSTGRES_PASSWORD", "postgres")
            pg_port = os.getenv("KEY_POSTGRES_PORT", "5432")
            pg_sslmode = os.getenv("KEY_POSTGRES_SSLMODE", "prefer")

            # Create connection string
            connection_string = (
                f"postgresql+psycopg2://{quote_plus(pg_user)}:{quote_plus(pg_password)}@{pg_host}:{pg_port}/"
                f"{pg_dbname}?sslmode={pg_sslmode}"
            )
            logger.info(
                "%s Built connection string from components (host=%s, db=%s)",
                LOG_PREFIX,
                pg_host,
                pg_dbname,
            )

        # Pool configuration (tunable per environment)
        pool_size = _get_int_env("DB_POOL_SIZE", 5)
        max_overflow = _get_int_env("DB_MAX_OVERFLOW", 5)
        pool_timeout = _get_int_env("DB_POOL_TIMEOUT", 30)
        pool_recycle = _get_int_env("DB_POOL_RECYCLE_SECONDS", 180)
        pool_use_lifo = _get_bool_env("DB_POOL_USE_LIFO", True)
        pool_pre_ping = _get_bool_env("DB_POOL_PRE_PING", True)

        # Connection specific settings
        connect_timeout = _get_int_env("DB_CONNECT_TIMEOUT", 10)
        statement_timeout_ms = _get_int_env("DB_STATEMENT_TIMEOUT_MS", 600000)
        keepalives_idle = _get_int_env("DB_KEEPALIVES_IDLE", 30)
        keepalives_interval = _get_int_env("DB_KEEPALIVES_INTERVAL", 10)
        keepalives_count = _get_int_env("DB_KEEPALIVES_COUNT", 5)
        application_name = os.getenv("DB_APPLICATION_NAME", "langgraph-backend")

        return cls(
            connection_string=connection_string,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_use_lifo=pool_use_lifo,
            pool_pre_ping=pool_pre_ping,
            connect_timeout=connect_timeout,
            statement_timeout_ms=statement_timeout_ms,
            keepalives_idle=keepalives_idle,
            keepalives_interval=keepalives_interval,
            keepalives_count=keepalives_count,
            application_name=application_name,
        )

    def get_connect_args(self) -> dict:
        """Get connection arguments for SQLAlchemy engine.

        Returns:
            Dictionary of connection arguments for psycopg2
        """
        connect_args = {
            "keepalives": 1,
            "keepalives_idle": self.keepalives_idle,
            "keepalives_interval": self.keepalives_interval,
            "keepalives_count": self.keepalives_count,
            "connect_timeout": self.connect_timeout,
            "options": f"-c statement_timeout={self.statement_timeout_ms}",
        }

        if self.application_name:
            connect_args["application_name"] = self.application_name

        return connect_args

    def log_configuration(self) -> None:
        """Log database configuration for debugging."""
        logger.info(
            "%s Configuration: pool_size=%s, max_overflow=%s, pool_timeout=%s, "
            "recycle=%s, lifo=%s, pre_ping=%s, app_name=%s",
            LOG_PREFIX,
            self.pool_size,
            self.max_overflow,
            self.pool_timeout,
            self.pool_recycle,
            self.pool_use_lifo,
            self.pool_pre_ping,
            self.application_name,
        )
