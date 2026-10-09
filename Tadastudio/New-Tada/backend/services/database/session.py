"""Database session management and context managers.

This module provides session factory creation and context managers for
database transactions.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy.orm import Session, sessionmaker

from .config import LOG_PREFIX
from .engine import get_engine

logger = logging.getLogger(__name__)

# Module-level session factory (created on first access)
_SessionLocal: Optional[sessionmaker] = None


def create_session_factory() -> sessionmaker:
    """Create SQLAlchemy session factory.

    Creates a session factory bound to the database engine with
    recommended settings for transactional safety.

    Returns:
        SQLAlchemy sessionmaker instance
    """
    engine = get_engine()

    logger.debug("%s Creating session factory", LOG_PREFIX)

    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )

    return session_factory


def get_session_factory() -> sessionmaker:
    """Get or create the global session factory.

    Returns a singleton session factory instance. Creates it on first call.

    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionLocal

    if _SessionLocal is None:
        _SessionLocal = create_session_factory()

    return _SessionLocal


# Public session factory (for backward compatibility)
SessionLocal = get_session_factory()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Provides a database session with automatic transaction management:
    - Commits on success
    - Rolls back on exception
    - Always closes the session

    Yields:
        SQLAlchemy Session instance

    Example:
        >>> with get_db() as db:
        ...     user = db.query(User).first()
        ...     user.name = "New Name"
        ...     # Automatically commits on success

    Raises:
        Exception: Re-raises any exception after rollback
    """
    session_factory = get_session_factory()
    db = session_factory()

    try:
        yield db

        # Always commit - SQLAlchemy 2.0 auto-begins transactions on first operation
        # in_transaction() may return False even when pending changes exist
        db.commit()

    except Exception as e:
        # Rollback on any exception
        logger.warning(
            "%s Rolling back transaction due to error: %s", LOG_PREFIX, e
        )
        db.rollback()
        raise

    finally:
        # Always close the session
        db.close()


def reset_session_factory() -> None:
    """Reset the global session factory.

    Useful for testing or reconfiguration.
    """
    global _SessionLocal
    _SessionLocal = None
    logger.info("%s Session factory reset", LOG_PREFIX)
