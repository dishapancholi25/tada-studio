"""Memory repository for database operations.

This module handles all database CRUD operations for memory management,
providing an async interface for memory and agent profile storage.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, desc, func
from backend.services.database import get_db
from backend.models import AgentMemoryProfile, ConversationMemory
from backend.services.config import get_logger

from .exceptions import MemoryDeletionError, MemoryRetrievalError, MemoryStorageError
from .schemas import MemoryCreate


logger = get_logger("memory_repository")


class MemoryRepository:
    """Repository for memory database operations.

    Provides async methods for creating, reading, updating, and deleting
    memory entries and agent profiles in the database.
    """

    @staticmethod
    async def create_memory(memory_data: MemoryCreate) -> ConversationMemory:
        """Create a new memory entry in the database.

        Args:
            memory_data: Memory creation data

        Returns:
            Created memory entry

        Raises:
            MemoryStorageError: If memory creation fails
        """
        # Never persist content that wasn't redacted by the manager hook.
        # Cheap marker check — not a second PII scan.
        if not getattr(memory_data, "redacted", False):
            raise MemoryStorageError(
                "Refusing to persist memory content that was not redacted"
            )
        try:
            with get_db() as db:
                memory = ConversationMemory(
                    agent_id=memory_data.agent_id,
                    agent_name=memory_data.agent_name,
                    memory_type=memory_data.memory_type,
                    content=memory_data.content,
                    graph_execution_id=memory_data.graph_execution_id,
                    node_execution_id=memory_data.node_execution_id,
                    importance_score=memory_data.importance_score,
                    chat_session_id=memory_data.chat_session_id,
                )
                db.add(memory)
                db.commit()
                db.refresh(memory)

                logger.info(
                    f"[MEMORY-REPO] Created {memory_data.memory_type} memory "
                    f"for agent {memory_data.agent_name} ({memory_data.agent_id})"
                )
                return memory
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to create memory: {e}")
            raise MemoryStorageError(str(e)) from e

    @staticmethod
    async def get_memories(
        agent_id: str,
        memory_types: Optional[list[str]] = None,
        limit: int = 10,
        only_active: bool = True,
        graph_execution_id: Optional[str] = None,
        chat_session_id: Optional[str] = None,
    ) -> list[ConversationMemory]:
        """Retrieve memories for an agent.

        Args:
            agent_id: Agent identifier
            memory_types: Optional list of memory types to filter by
            limit: Maximum number of memories to return
            only_active: Whether to only return active memories
            graph_execution_id: Optional execution ID filter
            chat_session_id: Optional chat session ID filter

        Returns:
            List of memory entries

        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            with get_db() as db:
                query = db.query(ConversationMemory).filter(
                    ConversationMemory.agent_id == agent_id
                )

                if only_active:
                    query = query.filter(ConversationMemory.is_active)

                if memory_types:
                    query = query.filter(
                        ConversationMemory.memory_type.in_(memory_types)
                    )

                if graph_execution_id:
                    query = query.filter(
                        ConversationMemory.graph_execution_id == graph_execution_id
                    )

                if chat_session_id:
                    query = query.filter(
                        ConversationMemory.chat_session_id == chat_session_id
                    )

                # Filter out expired memories
                query = query.filter(
                    (ConversationMemory.expires_at.is_(None))
                    | (ConversationMemory.expires_at > datetime.now(timezone.utc))
                )

                memories = (
                    query.order_by(desc(ConversationMemory.created_at))
                    .limit(limit)
                    .all()
                )

                logger.debug(
                    f"[MEMORY-REPO] Retrieved {len(memories)} memories for agent {agent_id}"
                )
                return memories
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to retrieve memories: {e}")
            raise MemoryRetrievalError(str(e)) from e

    @staticmethod
    async def update_memory_access(memory_ids: list[str]) -> None:
        """Update access count and timestamp for memories.

        Args:
            memory_ids: List of memory IDs to update

        Raises:
            MemoryStorageError: If update fails
        """
        try:
            with get_db() as db:
                for memory_id in memory_ids:
                    memory = (
                        db.query(ConversationMemory)
                        .filter(ConversationMemory.id == memory_id)
                        .first()
                    )
                    if memory:
                        memory.access_count += 1
                        memory.last_accessed = datetime.now(timezone.utc)
                db.commit()
                logger.debug(
                    f"[MEMORY-REPO] Updated access for {len(memory_ids)} memories"
                )
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to update memory access: {e}")
            raise MemoryStorageError(str(e)) from e

    @staticmethod
    async def get_or_create_agent_profile(
        agent_id: str, agent_name: str, graph_id: str
    ) -> AgentMemoryProfile:
        """Get or create an agent memory profile.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            graph_id: Graph that this agent belongs to

        Returns:
            Agent memory profile

        Raises:
            MemoryStorageError: If profile creation fails
        """
        try:
            with get_db() as db:
                profile = (
                    db.query(AgentMemoryProfile)
                    .filter(AgentMemoryProfile.agent_id == agent_id)
                    .first()
                )

                if not profile:
                    profile = AgentMemoryProfile(
                        agent_id=agent_id, agent_name=agent_name, graph_id=graph_id
                    )
                    db.add(profile)
                    db.commit()
                    db.refresh(profile)
                    logger.info(
                        f"[MEMORY-REPO] Created memory profile for agent "
                        f"{agent_name} ({agent_id})"
                    )

                return profile
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to get/create agent profile: {e}")
            raise MemoryStorageError(str(e)) from e

    @staticmethod
    async def get_agent_profile(agent_id: str) -> Optional[AgentMemoryProfile]:
        """Get an existing agent memory profile by agent ID.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Agent memory profile if found, otherwise None

        Raises:
            MemoryRetrievalError: If profile retrieval fails
        """
        try:
            with get_db() as db:
                return (
                    db.query(AgentMemoryProfile)
                    .filter(AgentMemoryProfile.agent_id == agent_id)
                    .first()
                )
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to get agent profile: {e}")
            raise MemoryRetrievalError(str(e)) from e

    @staticmethod
    async def update_agent_statistics(
        agent_id: str,
        increment_conversations: bool = False,
        increment_messages: int = 0,
    ) -> None:
        """Update agent interaction statistics.

        Args:
            agent_id: Agent identifier
            increment_conversations: Whether to increment conversation count
            increment_messages: Number of messages to add to count

        Raises:
            MemoryStorageError: If update fails
        """
        try:
            with get_db() as db:
                profile = (
                    db.query(AgentMemoryProfile)
                    .filter(AgentMemoryProfile.agent_id == agent_id)
                    .first()
                )

                if profile:
                    if increment_conversations:
                        profile.total_conversations += 1
                    profile.total_messages += increment_messages
                    profile.last_interaction = datetime.now(timezone.utc)
                    db.commit()
                    logger.debug(
                        f"[MEMORY-REPO] Updated statistics for agent {agent_id}"
                    )
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to update agent statistics: {e}")
            raise MemoryStorageError(str(e)) from e

    @staticmethod
    async def update_importance_scores(memory_ids: list[str], new_score: float) -> None:
        """Update importance scores for multiple memories.

        Args:
            memory_ids: List of memory IDs to update
            new_score: New importance score (0-1)

        Raises:
            MemoryStorageError: If update fails
        """
        try:
            with get_db() as db:
                for memory_id in memory_ids:
                    memory = (
                        db.query(ConversationMemory)
                        .filter(ConversationMemory.id == memory_id)
                        .first()
                    )
                    if memory:
                        memory.importance_score = new_score
                db.commit()
                logger.debug(
                    f"[MEMORY-REPO] Updated importance for {len(memory_ids)} memories"
                )
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to update importance scores: {e}")
            raise MemoryStorageError(str(e)) from e

    @staticmethod
    async def deactivate_old_memories(
        agent_id: str,
        retention_days: int,
        graph_execution_id: Optional[str] = None,
    ) -> int:
        """Soft delete old memories based on retention policy.

        Args:
            agent_id: Agent identifier
            retention_days: Number of days to retain memories
            graph_execution_id: Optional execution ID filter. When provided,
                only memories with the same non-null execution ID are pruned.

        Returns:
            Number of memories deactivated

        Raises:
            MemoryDeletionError: If deactivation fails
        """
        try:
            with get_db() as db:
                cutoff_date = datetime.now(timezone.utc) - timedelta(
                    days=retention_days
                )

                old_memories = (
                    db.query(ConversationMemory)
                    .filter(
                        and_(
                            ConversationMemory.agent_id == agent_id,
                            ConversationMemory.created_at < cutoff_date,
                            ConversationMemory.importance_score < 0.5,
                            ConversationMemory.memory_type == "conversation",
                        )
                    )
                )

                if graph_execution_id is not None:
                    old_memories = old_memories.filter(
                        ConversationMemory.graph_execution_id == graph_execution_id
                    )

                old_memories = old_memories.all()

                for memory in old_memories:
                    memory.is_active = False

                db.commit()

                logger.info(
                    f"[MEMORY-REPO] Deactivated {len(old_memories)} old memories "
                    f"for agent {agent_id}"
                )
                return len(old_memories)
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to deactivate old memories: {e}")
            raise MemoryDeletionError(str(e)) from e

    @staticmethod
    async def delete_agent_memories(
        agent_id: str, graph_execution_id: Optional[str] = None
    ) -> int:
        """Permanently delete memories for an agent.

        Args:
            agent_id: Agent identifier
            graph_execution_id: Optional execution ID filter

        Returns:
            Number of memories deleted

        Raises:
            MemoryDeletionError: If deletion fails
        """
        try:
            with get_db() as db:
                query = db.query(ConversationMemory).filter(
                    ConversationMemory.agent_id == agent_id
                )

                if graph_execution_id:
                    query = query.filter(
                        ConversationMemory.graph_execution_id == graph_execution_id
                    )

                count = query.count()
                query.delete()
                db.commit()

                logger.info(
                    f"[MEMORY-REPO] Deleted {count} memories for agent {agent_id}"
                )
                return count
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to delete memories: {e}")
            raise MemoryDeletionError(str(e)) from e

    @staticmethod
    async def get_memory_statistics(agent_id: str) -> dict:
        """Get statistics about an agent's memories.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with memory statistics

        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            with get_db() as db:
                # Total and active counts
                total = (
                    db.query(func.count(ConversationMemory.id))
                    .filter(ConversationMemory.agent_id == agent_id)
                    .scalar()
                )
                active = (
                    db.query(func.count(ConversationMemory.id))
                    .filter(
                        ConversationMemory.agent_id == agent_id,
                        ConversationMemory.is_active,
                    )
                    .scalar()
                )

                # Average importance
                avg_importance = (
                    db.query(func.avg(ConversationMemory.importance_score))
                    .filter(
                        ConversationMemory.agent_id == agent_id,
                        ConversationMemory.is_active,
                    )
                    .scalar()
                ) or 0.0

                # Memory by type
                type_counts = {}
                results = (
                    db.query(
                        ConversationMemory.memory_type,
                        func.count(ConversationMemory.id),
                    )
                    .filter(
                        ConversationMemory.agent_id == agent_id,
                        ConversationMemory.is_active,
                    )
                    .group_by(ConversationMemory.memory_type)
                    .all()
                )
                for memory_type, count in results:
                    type_counts[memory_type] = count

                return {
                    "total_memories": total or 0,
                    "active_memories": active or 0,
                    "memory_by_type": type_counts,
                    "average_importance": float(avg_importance),
                }
        except Exception as e:
            logger.error(f"[MEMORY-REPO] Failed to get memory statistics: {e}")
            raise MemoryRetrievalError(str(e)) from e
