"""Statistics tracking for agent memory.

This module provides utilities for tracking and managing agent interaction
statistics and memory usage metrics.
"""

from backend.services.config import get_logger

from .repository import MemoryRepository


logger = get_logger("memory_statistics")


class MemoryStatistics:
    """Manager for memory statistics.

    Provides methods for tracking agent interactions, updating statistics,
    and retrieving memory usage metrics.
    """

    def __init__(self, repository: MemoryRepository):
        """Initialize statistics manager.

        Args:
            repository: Memory repository instance
        """
        self.repository = repository

    async def increment_conversation_count(self, agent_id: str) -> None:
        """Increment conversation count for an agent.

        Args:
            agent_id: Agent identifier
        """
        try:
            await self.repository.update_agent_statistics(
                agent_id=agent_id,
                increment_conversations=True,
                increment_messages=0,
            )
            logger.debug(
                f"[MEMORY-STATS] Incremented conversation count for agent {agent_id}"
            )
        except Exception as e:
            logger.error(f"[MEMORY-STATS] Failed to increment conversation count: {e}")

    async def increment_message_count(
        self, agent_id: str, message_count: int = 1
    ) -> None:
        """Increment message count for an agent.

        Args:
            agent_id: Agent identifier
            message_count: Number of messages to add
        """
        try:
            await self.repository.update_agent_statistics(
                agent_id=agent_id,
                increment_conversations=False,
                increment_messages=message_count,
            )
            logger.debug(
                f"[MEMORY-STATS] Incremented message count by {message_count} "
                f"for agent {agent_id}"
            )
        except Exception as e:
            logger.error(f"[MEMORY-STATS] Failed to increment message count: {e}")

    async def record_conversation_turn(
        self, agent_id: str, message_count: int = 2
    ) -> None:
        """Record a complete conversation turn.

        Args:
            agent_id: Agent identifier
            message_count: Number of messages in the turn (default: 2)
        """
        try:
            await self.repository.update_agent_statistics(
                agent_id=agent_id,
                increment_conversations=False,
                increment_messages=message_count,
            )
            logger.debug(
                f"[MEMORY-STATS] Recorded conversation turn for agent {agent_id}"
            )
        except Exception as e:
            logger.error(f"[MEMORY-STATS] Failed to record conversation turn: {e}")

    async def get_agent_statistics(self, agent_id: str) -> dict:
        """Get comprehensive statistics for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with agent statistics including:
            - total_memories: Total number of memories
            - active_memories: Number of active memories
            - memory_by_type: Count of memories by type
            - average_importance: Average importance score
        """
        try:
            stats = await self.repository.get_memory_statistics(agent_id)
            logger.debug(f"[MEMORY-STATS] Retrieved statistics for agent {agent_id}")
            return stats
        except Exception as e:
            logger.error(f"[MEMORY-STATS] Failed to get agent statistics: {e}")
            return {
                "total_memories": 0,
                "active_memories": 0,
                "memory_by_type": {},
                "average_importance": 0.0,
            }
