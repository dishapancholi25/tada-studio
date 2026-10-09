"""
FastAPI dependencies for email API.

Provides dependency injection for database sessions and services.
"""

from typing import Generator

from backend.services.database import SessionLocal
from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
