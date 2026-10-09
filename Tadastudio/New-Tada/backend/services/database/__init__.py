"""Database service - connection management, sessions, and migrations.

This module provides the public API for database operations including:
- Database configuration and engine creation
- Session management and context managers
- SQLAlchemy Base class for models
- Database initialization and migrations

Example:
    >>> from backend.services.database import get_db, Base, init_db
    >>>
    >>> # Use in FastAPI dependency injection
    >>> @app.get("/users")
    >>> def list_users(db: Session = Depends(get_db)):
    ...     return db.query(User).all()
    >>>
    >>> # Initialize database on application startup
    >>> init_db()
"""

# Core database components
from .base import Base
from .config import DatabaseConfig
from .engine import create_database_engine, get_engine, reset_engine
from .migrations import init_db
from .session import SessionLocal, get_db, get_session_factory, reset_session_factory

__all__ = [
    # Most commonly used - backward compatible with backend.database
    "Base",
    "get_db",
    "SessionLocal",
    "init_db",
    # Engine management
    "get_engine",
    "create_database_engine",
    "reset_engine",
    # Session management
    "get_session_factory",
    "reset_session_factory",
    # Configuration
    "DatabaseConfig",
]
