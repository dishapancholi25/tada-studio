"""FastAPI dependencies for memory API.

This module provides dependency injection functions for the memory API,
enabling easy testing and service instance management.
"""

from typing import Annotated

from fastapi import Depends
from backend.services.memory import MemoryManager, get_memory_manager


def get_memory_service() -> MemoryManager:
    """Get memory manager instance.

    This dependency provides the memory manager for API endpoints,
    enabling proper dependency injection and testing.

    Returns:
        MemoryManager instance

    Example:
        @router.get("/memories")
        async def get_memories(
            memory_service: Annotated[MemoryManager, Depends(get_memory_service)]
        ):
            return await memory_service.get_agent_memories("agent-1")
    """
    return get_memory_manager()


# Type alias for cleaner endpoint signatures
MemoryService = Annotated[MemoryManager, Depends(get_memory_service)]
