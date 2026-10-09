"""SQLAlchemy declarative base for ORM models.

This module provides the Base class that all SQLAlchemy models should inherit from.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create base class for all ORM models
Base = declarative_base()
