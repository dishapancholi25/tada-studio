"""Memory management service.

This package provides comprehensive memory management capabilities for agents,
including conversation history tracking, memory storage, retrieval, and lifecycle
management.

Basic Usage:
    from backend.services.memory import get_memory_manager

    # Get manager instance
    manager = get_memory_manager()

    # Create memory
    memory = await manager.create_memory(
        agent_id="agent-1",
        agent_name="Assistant",
        memory_type="conversation",
        content="Hello, how can I help?"
    )

    # Retrieve memories
    memories = await manager.get_agent_memories(
        agent_id="agent-1",
        limit=10
    )

    # Format for agent context
    context = await manager.format_memory_context(memories)

Key Features:
- Async/await support throughout
- Type-safe operations with Pydantic schemas
- Custom exceptions for better error handling
- Modular architecture with separation of concerns
- Statistics tracking and memory pruning
- Memory formatting for LLM context

Architecture:
- manager: High-level interface for memory operations
- repository: Database CRUD operations
- formatter: Memory formatting for LLM context
- statistics: Agent interaction tracking
- pruning: Memory lifecycle management
- exceptions: Domain-specific errors
- schemas: Service-layer data models
"""

# Exceptions
from .exceptions import (
    AgentProfileNotFoundError,
    InvalidImportanceScoreError,
    InvalidMemoryTypeError,
    MemoryDeletionError,
    MemoryError,
    MemoryNotFoundError,
    MemoryRetrievalError,
    MemoryStorageError,
)
from .formatter import MemoryFormatter

# Main API
from .manager import MemoryManager, get_memory_manager, reset_memory_manager
from .pruning import MemoryPruning

# Core components (for advanced usage)
from .repository import MemoryRepository

# Schemas
from .schemas import (
    AgentProfileData,
    ConversationHistoryEntry,
    ConversationTurn,
    MemoryCreate,
    MemoryData,
    MemoryQuery,
)
from .schemas import MemoryStatistics as MemoryStatisticsSchema
from .statistics import MemoryStatistics

# PII redaction
from .redaction import (
    MEMORY_PII_ENTITY_TYPES,
    MemoryRedactor,
    get_memory_encryptor,
    get_memory_redactor,
    redact_memory_content,
)


__all__ = [
    # Main API
    "get_memory_manager",
    "reset_memory_manager",
    "MemoryManager",
    # Core components
    "MemoryRepository",
    "MemoryFormatter",
    "MemoryStatistics",
    "MemoryPruning",
    # Redaction
    "MEMORY_PII_ENTITY_TYPES",
    "MemoryRedactor",
    "get_memory_redactor",
    "get_memory_encryptor",
    "redact_memory_content",
    # Exceptions
    "MemoryError",
    "MemoryNotFoundError",
    "AgentProfileNotFoundError",
    "InvalidMemoryTypeError",
    "MemoryStorageError",
    "MemoryRetrievalError",
    "MemoryDeletionError",
    "InvalidImportanceScoreError",
    # Schemas
    "MemoryCreate",
    "MemoryData",
    "AgentProfileData",
    "ConversationTurn",
    "ConversationHistoryEntry",
    "MemoryQuery",
    "MemoryStatisticsSchema",
]
