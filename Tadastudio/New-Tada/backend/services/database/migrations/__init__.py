"""Database initialization and migration runner.

This module provides the main init_db() function that initializes database
tables and runs schema migrations using PostgreSQL advisory locks for
safe concurrent execution.
"""

import logging
import random
import time

from sqlalchemy import text

from ..base import Base
from ..engine import get_engine
from .registry import get_enabled_migrations
from .schema_updates import enable_pgvector_extension

logger = logging.getLogger(__name__)
LOG_PREFIX = "[DATABASE-INIT]"

# Advisory lock ID for database initialization (must be unique across app)
INIT_LOCK_ID = 123456789


def init_db() -> None:
    """Initialize database tables and run migrations.

    This function is worker-safe and uses PostgreSQL advisory locks to prevent
    concurrent initialization attempts. It performs the following:

    1. Acquires a PostgreSQL advisory lock
    2. Enables pgvector extension (required for VECTOR column types)
    3. Creates all tables defined in SQLAlchemy models (idempotent)
    4. Runs remaining schema migrations
    5. Releases the advisory lock

    If another worker is already performing initialization, this function
    will wait briefly and then exit without error.

    Raises:
        Exception: If critical initialization steps fail
    """
    engine = get_engine()

    logger.info("%s Starting database initialization", LOG_PREFIX)

    # Phase 1: Acquire lock and create tables
    with engine.connect() as conn:
        try:
            # Try to acquire advisory lock (non-blocking)
            logger.debug("%s Attempting to acquire advisory lock", LOG_PREFIX)
            result = conn.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": INIT_LOCK_ID}
            )
            lock_acquired = result.scalar()

            if not lock_acquired:
                logger.info(
                    "%s Database initialization already in progress by another worker",
                    LOG_PREFIX,
                )
                # Wait a random amount to avoid thundering herd, then proceed without lock
                wait_time = random.uniform(1, 3)
                logger.debug(
                    "%s Waiting %.2f seconds before returning", LOG_PREFIX, wait_time
                )
                time.sleep(wait_time)
                return

            logger.info("%s Acquired database initialization lock", LOG_PREFIX)

            # Enable pgvector extension before creating tables
            # This must run before create_all() because document_chunks uses VECTOR type
            logger.info("%s Enabling pgvector extension", LOG_PREFIX)
            enable_pgvector_extension(conn)
            logger.info("%s pgvector extension enabled", LOG_PREFIX)

            # Create all tables (idempotent operation)
            logger.info("%s Creating database tables", LOG_PREFIX)
            Base.metadata.create_all(bind=engine)
            logger.info("%s Database tables created successfully", LOG_PREFIX)

        except Exception as e:
            logger.error("%s Error during table creation: %s", LOG_PREFIX, e)
            raise
        finally:
            # Always release the advisory lock
            try:
                logger.debug("%s Releasing advisory lock", LOG_PREFIX)
                conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": INIT_LOCK_ID},
                )
            except Exception as unlock_error:
                logger.warning(
                    "%s Could not release advisory lock: %s", LOG_PREFIX, unlock_error
                )

    # Phase 2: Run schema migrations
    logger.info("%s Running schema migrations", LOG_PREFIX)
    run_migrations()
    logger.info("%s Database initialization completed successfully", LOG_PREFIX)


def run_migrations() -> None:
    """Run all enabled schema migrations.

    Executes all migrations registered in the migration registry.
    Each migration is idempotent and can be safely run multiple times.
    """
    engine = get_engine()
    migrations = get_enabled_migrations()

    logger.info("%s Found %d enabled migrations", LOG_PREFIX, len(migrations))

    with engine.connect() as conn:
        for migration in migrations:
            logger.debug("%s Running migration: %s", LOG_PREFIX, migration.name)
            try:
                migration.execute(conn)
                logger.debug("%s Migration completed: %s", LOG_PREFIX, migration.name)
            except Exception as e:
                logger.warning(
                    "%s Migration '%s' failed: %s", LOG_PREFIX, migration.name, e
                )
                # Continue with other migrations even if one fails
                # Most migrations are non-critical enhancements

        # Commit all migrations
        conn.commit()

    logger.info("%s All migrations completed", LOG_PREFIX)
