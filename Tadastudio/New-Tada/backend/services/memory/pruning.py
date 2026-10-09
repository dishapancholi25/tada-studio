"""Memory pruning and cleanup utilities.

This module provides utilities for managing memory lifecycle, including
pruning old memories, managing retention policies, and cleaning up
inactive memories.
"""

from typing import Optional

from backend.services.config import get_logger

from .exceptions import MemoryDeletionError
from .repository import MemoryRepository


logger = get_logger("memory_pruning")


class MemoryPruning:
    """Manager for memory pruning and cleanup operations.

    Provides methods for managing memory lifecycle, enforcing retention
    policies, and cleaning up old or inactive memories.
    """

    def __init__(self, repository: MemoryRepository):
        """Initialize pruning manager.

        Args:
            repository: Memory repository instance
        """
        self.repository = repository

    async def prune_old_memories(
        self,
        agent_id: str,
        retention_days: int = 30,
        graph_execution_id: Optional[str] = None,
    ) -> int:
        """Prune old memories based on retention policy.

        Soft-deletes (deactivates) old conversation memories with low
        importance scores according to the retention policy.

        Args:
            agent_id: Agent identifier
            retention_days: Number of days to retain memories
            graph_execution_id: Optional execution ID filter. None means prune
                across all executions and should only be used by internal jobs.

        Returns:
            Number of memories pruned

        Raises:
            MemoryDeletionError: If pruning fails
        """
        try:
            count = await self.repository.deactivate_old_memories(
                agent_id=agent_id,
                retention_days=retention_days,
                graph_execution_id=graph_execution_id,
            )
            logger.info(
                f"[MEMORY-PRUNING] Pruned {count} old memories for agent {agent_id} "
                f"(retention: {retention_days} days, execution: {graph_execution_id})"
            )
            return count
        except Exception as e:
            logger.error(f"[MEMORY-PRUNING] Failed to prune memories: {e}")
            raise MemoryDeletionError(f"Pruning failed: {str(e)}") from e

    async def clear_agent_memories(
        self, agent_id: str, graph_execution_id: Optional[str] = None
    ) -> int:
        """Clear all memories for an agent.

        Permanently deletes memories for an agent, optionally filtered
        by execution ID.

        Args:
            agent_id: Agent identifier
            graph_execution_id: Optional execution ID filter

        Returns:
            Number of memories deleted

        Raises:
            MemoryDeletionError: If deletion fails
        """
        try:
            count = await self.repository.delete_agent_memories(
                agent_id=agent_id, graph_execution_id=graph_execution_id
            )

            if graph_execution_id:
                logger.info(
                    f"[MEMORY-PRUNING] Cleared {count} memories for agent {agent_id} "
                    f"(execution: {graph_execution_id})"
                )
            else:
                logger.info(
                    f"[MEMORY-PRUNING] Cleared all {count} memories for agent {agent_id}"
                )

            return count
        except Exception as e:
            logger.error(f"[MEMORY-PRUNING] Failed to clear memories: {e}")
            raise MemoryDeletionError(f"Clear failed: {str(e)}") from e

    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memories across all agents.

        Note: This is a placeholder for future implementation.
        Currently, expired memories are filtered out during retrieval.

        Returns:
            Number of expired memories cleaned up
        """
        # TODO: Implement batch cleanup of expired memories
        logger.debug("[MEMORY-PRUNING] Expired memory cleanup not yet implemented")
        return 0

    async def enforce_memory_limits(
        self, agent_id: str, max_memories: int = 1000
    ) -> int:
        """Enforce memory limits for an agent.

        Prunes oldest, least important memories to stay under the limit.

        Note: This is a placeholder for future implementation.

        Args:
            agent_id: Agent identifier
            max_memories: Maximum number of memories to keep

        Returns:
            Number of memories pruned
        """
        # TODO: Implement memory limit enforcement
        logger.debug(
            f"[MEMORY-PRUNING] Memory limit enforcement not yet implemented "
            f"for agent {agent_id}"
        )
        return 0
