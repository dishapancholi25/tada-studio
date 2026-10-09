"""
Checkpointer initialization for LangGraph execution.

This module provides functions for initializing checkpointers based on configuration,
supporting both PostgreSQL and in-memory checkpointing with proper fallback handling.
"""

import asyncio
import os
from typing import Optional
from urllib.parse import quote_plus

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from backend.services.config import get_logger


checkpointer_logger = get_logger("execution.checkpointer")

# Check if PostgreSQL checkpointing is available
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    AsyncPostgresSaver = None
    AsyncConnectionPool = None


def build_postgres_connection_string() -> Optional[str]:
    """
    Build PostgreSQL connection string from environment variables.

    Attempts to use DATABASE_URL first (standard for most deployments),
    then falls back to building from individual KEY_POSTGRES_* variables.

    The connection string includes TCP keepalive parameters to prevent
    connection timeouts during long-running checkpoint operations.

    Environment Variables:
        DATABASE_URL: Full PostgreSQL connection URL (preferred)
        KEY_POSTGRES_HOST: PostgreSQL host
        KEY_POSTGRES_DBNAME: Database name
        KEY_POSTGRES_USER: Database user
        KEY_POSTGRES_PASSWORD: Database password
        KEY_POSTGRES_PORT: Database port (default: 5432)
        KEY_POSTGRES_SSLMODE: SSL mode (default: require)

    Returns:
        PostgreSQL connection string with keepalive parameters, or None if
        required environment variables are not set

    Example:
        >>> conn_string = build_postgres_connection_string()
        >>> if conn_string:
        ...     print("PostgreSQL configured")
    """
    # Try DATABASE_URL first (standard for most deployments)
    conn_string = os.getenv("DATABASE_URL")
    if conn_string:
        # DATABASE_URL is stored in SQLAlchemy form (e.g.
        # "postgresql+psycopg2://..."). The LangGraph checkpointer uses
        # psycopg3's AsyncConnectionPool, which cannot parse the "+driver"
        # dialect suffix and raises "invalid connection option". Strip it so
        # psycopg3 receives a plain libpq URL. The main application DB keeps
        # using the original value via SQLAlchemy (the .env is left untouched).
        scheme, sep, rest = conn_string.partition("://")
        if sep and "+" in scheme:
            conn_string = f"{scheme.split('+', 1)[0]}{sep}{rest}"
        checkpointer_logger.debug("Using DATABASE_URL for PostgreSQL connection")
        return conn_string

    # Build from components
    pg_host = os.getenv("KEY_POSTGRES_HOST")
    pg_dbname = os.getenv("KEY_POSTGRES_DBNAME")
    pg_user = os.getenv("KEY_POSTGRES_USER")
    pg_password = os.getenv("KEY_POSTGRES_PASSWORD")
    pg_port = os.getenv("KEY_POSTGRES_PORT", "5432")
    pg_sslmode = os.getenv("KEY_POSTGRES_SSLMODE", "require")

    if all([pg_host, pg_dbname, pg_user, pg_password]):
        checkpointer_logger.debug(
            "Building PostgreSQL connection from KEY_POSTGRES_* variables"
        )
        return (
            f"postgresql://{quote_plus(pg_user)}:{quote_plus(pg_password)}@{pg_host}:{pg_port}/{pg_dbname}"
            f"?sslmode={pg_sslmode}&keepalives=1&keepalives_idle=30"
            f"&keepalives_interval=10&keepalives_count=5"
        )

    checkpointer_logger.debug("PostgreSQL configuration not found in environment")
    return None


def initialize_checkpointer() -> BaseCheckpointSaver:
    """
    Initialize the checkpointer based on configuration.

    This function:
    1. Checks if PostgreSQL checkpointing is enabled (default: true)
    2. Attempts to initialize AsyncPostgresSaver using AsyncConnectionPool
    3. Falls back to MemorySaver if PostgreSQL is unavailable or fails

    Environment Variables:
        ENABLE_POSTGRES_CHECKPOINTING: Enable PostgreSQL checkpointing (default: true)
        See build_postgres_connection_string() for database configuration

    Returns:
        Initialized checkpointer (AsyncPostgresSaver or MemorySaver as fallback)

    Example:
        >>> checkpointer = initialize_checkpointer()
        >>> # Use with LangGraph StateGraph
        >>> graph = StateGraph(WorkflowState, checkpointer=checkpointer)
    """
    use_postgres = os.getenv("ENABLE_POSTGRES_CHECKPOINTING", "true").lower() == "true"

    if use_postgres and POSTGRES_AVAILABLE:
        conn_string = build_postgres_connection_string()
        if not conn_string:
            checkpointer_logger.warning(
                "PostgreSQL checkpointing enabled but no connection string configured. "
                "Set DATABASE_URL or KEY_POSTGRES_* environment variables."
            )
        else:
            try:
                checkpointer_logger.info(
                    "Initializing async PostgreSQL checkpointer..."
                )

                async def _create_checkpointer():
                    """Create and setup the async checkpointer using connection pool.

                    langgraph-checkpoint-postgres v3.x requires using AsyncConnectionPool
                    instead of from_conn_string() for long-lived checkpointer instances.

                    Best practices require:
                    - autocommit=True: Required for .setup() to commit checkpoint tables
                    - row_factory=dict_row: Required for dict-style row access
                    - max_size: Controls pool concurrency
                    """
                    # Create connection pool with best practice configuration
                    pool = AsyncConnectionPool(
                        conninfo=conn_string,
                        max_size=10,
                        open=False,
                        kwargs={"autocommit": True, "row_factory": dict_row},
                    )
                    try:
                        await pool.open()

                        # Create checkpointer from pool
                        checkpointer = AsyncPostgresSaver(pool)
                        await checkpointer.setup()

                        checkpointer_logger.debug("PostgreSQL connection pool opened")
                        return checkpointer
                    except Exception as e:
                        # Ensure pool is closed on any failure to prevent resource leaks
                        checkpointer_logger.warning(
                            f"Checkpointer creation failed, closing pool: {e}"
                        )
                        try:
                            await pool.close()
                        except Exception as close_error:
                            checkpointer_logger.warning(
                                f"Error closing pool during cleanup: {close_error}"
                            )
                        raise

                # Handle both running loop (FastAPI startup) and no loop scenarios
                try:
                    # Check if there's already a running event loop
                    asyncio.get_running_loop()
                    # We're inside an async context - run in a separate thread
                    checkpointer_logger.debug(
                        "Running loop detected, creating checkpointer in new thread"
                    )
                    import concurrent.futures

                    def _run_in_new_loop():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        # Don't close the loop - pool needs it for background tasks
                        return new_loop.run_until_complete(_create_checkpointer())

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(_run_in_new_loop)
                        postgres_checkpointer = future.result(timeout=30)

                except RuntimeError:
                    # No running loop - create and use a new one
                    checkpointer_logger.debug(
                        "No running loop, creating new event loop"
                    )
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # Don't close the loop - pool needs it for background tasks
                    postgres_checkpointer = loop.run_until_complete(
                        _create_checkpointer()
                    )

                checkpointer_logger.info(
                    "Async PostgreSQL checkpointer initialized successfully"
                )
                return postgres_checkpointer

            except Exception as e:
                checkpointer_logger.error(
                    f"Failed to initialize PostgreSQL checkpointer: {e}", exc_info=True
                )

        checkpointer_logger.info("Falling back to in-memory checkpointer")

    elif use_postgres and not POSTGRES_AVAILABLE:
        checkpointer_logger.warning(
            "PostgreSQL checkpointing enabled but langgraph-checkpoint-postgres not installed. "
            "Install with: pip install langgraph-checkpoint-postgres"
        )
        checkpointer_logger.info("Falling back to in-memory checkpointer")

    checkpointer_logger.info("Initialized in-memory checkpointer")
    return MemorySaver()
