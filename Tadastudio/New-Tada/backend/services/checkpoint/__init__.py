"""Checkpoint metadata service package.

This package provides services for managing checkpoint metadata storage and retrieval,
including database operations, caching, and business logic for checkpoint management.

Modules:
    - metadata_manager: Main service for checkpoint metadata management
    - repository: Database operations layer
    - cache: In-memory caching utility
    - types: Type definitions and constants

Usage:
    >>> from backend.services.checkpoint import get_checkpoint_metadata_manager
    >>> manager = get_checkpoint_metadata_manager()
    >>> manager.store_checkpoint_metadata("cp_123", "thread_456", {...})
"""

from .cache import CheckpointMetadataCache
from .metadata_manager import (
    CheckpointMetadataManager,
    checkpoint_metadata_manager,
    get_checkpoint_metadata_manager,
)
from .repository import CheckpointMetadataRepository
from .types import CheckpointMetadataDict, CheckpointStatusType


__all__ = [
    "CheckpointMetadataManager",
    "CheckpointMetadataRepository",
    "CheckpointMetadataCache",
    "CheckpointMetadataDict",
    "CheckpointStatusType",
    "get_checkpoint_metadata_manager",
    "checkpoint_metadata_manager",
]
