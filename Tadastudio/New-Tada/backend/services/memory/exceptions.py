"""Custom exceptions for memory service operations.

This module defines domain-specific exceptions for memory management operations,
providing better error handling and debugging capabilities.
"""


class MemoryError(Exception):
    """Base exception for all memory-related errors."""

    pass


class MemoryNotFoundError(MemoryError):
    """Raised when a requested memory entry cannot be found."""

    def __init__(self, memory_id: str):
        """Initialize memory not found error."""
        self.memory_id = memory_id
        super().__init__(f"Memory with ID {memory_id} not found")


class AgentProfileNotFoundError(MemoryError):
    """Raised when an agent profile cannot be found."""

    def __init__(self, agent_id: str):
        """Initialize agent profile not found error."""
        self.agent_id = agent_id
        super().__init__(f"Agent profile for {agent_id} not found")


class InvalidMemoryTypeError(MemoryError):
    """Raised when an invalid memory type is specified."""

    def __init__(self, memory_type: str, valid_types: list[str]):
        """Initialize invalid memory type error."""
        self.memory_type = memory_type
        self.valid_types = valid_types
        super().__init__(
            f"Invalid memory type '{memory_type}'. "
            f"Valid types: {', '.join(valid_types)}"
        )


class MemoryStorageError(MemoryError):
    """Raised when memory cannot be stored in the database."""

    def __init__(self, details: str):
        """Initialize memory storage error."""
        super().__init__(f"Failed to store memory: {details}")


class MemoryRetrievalError(MemoryError):
    """Raised when memory retrieval fails."""

    def __init__(self, details: str):
        """Initialize memory retrieval error."""
        super().__init__(f"Failed to retrieve memory: {details}")


class MemoryDeletionError(MemoryError):
    """Raised when memory deletion fails."""

    def __init__(self, details: str):
        """Initialize memory deletion error."""
        super().__init__(f"Failed to delete memory: {details}")


class InvalidImportanceScoreError(MemoryError):
    """Raised when an invalid importance score is provided."""

    def __init__(self, score: float):
        """Initialize invalid importance score error."""
        self.score = score
        super().__init__(
            f"Invalid importance score {score}. Must be between 0.0 and 1.0"
        )
