"""Memory manager - main service interface.

This module provides the primary interface for memory operations,
coordinating between the repository, formatter, statistics, and pruning modules.
"""

import asyncio
from typing import Optional

from backend.models import ConversationMemory
from backend.services.config import get_logger

from .formatter import MemoryFormatter
from .pruning import MemoryPruning
from .redaction import redact_memory_content
from .repository import MemoryRepository
from .schemas import MemoryCreate
from .statistics import MemoryStatistics


logger = get_logger("memory_manager")


class MemoryManager:
    """Main interface for memory management operations.

    Provides high-level methods for managing agent memories, coordinating
    between repository, formatting, statistics, and pruning operations.

    Example:
        >>> manager = get_memory_manager()
        >>> memory = await manager.create_memory(
        ...     agent_id="agent-1",
        ...     agent_name="Assistant",
        ...     memory_type="conversation",
        ...     content="Hello, how can I help?"
        ... )
    """

    def __init__(self):
        """Initialize memory manager with dependencies."""
        self.repository = MemoryRepository()
        self.formatter = MemoryFormatter()
        self.statistics = MemoryStatistics(self.repository)
        self.pruning = MemoryPruning(self.repository)

    async def create_memory(
        self,
        agent_id: str,
        agent_name: str,
        memory_type: str,
        content: str,
        graph_execution_id: Optional[str] = None,
        node_execution_id: Optional[str] = None,
        importance_score: float = 0.5,
        chat_session_id: Optional[str] = None,
    ) -> ConversationMemory:
        """Create a new memory entry.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            memory_type: Type of memory (conversation, summary, fact, instruction, chat_conversation)
            content: Memory content
            graph_execution_id: Optional graph execution ID
            node_execution_id: Optional node execution ID
            importance_score: Memory importance (0-1, default: 0.5)
            chat_session_id: Optional chat session ID for chat-scoped memory

        Returns:
            Created memory entry

        Raises:
            MemoryStorageError: If creation fails
        """
        # Redact PII before persistence so plaintext never reaches the DB or
        # logs. Presidio detection is CPU-bound, so run it off the event loop.
        redacted_content = await asyncio.get_running_loop().run_in_executor(
            None, redact_memory_content, content
        )

        memory_data = MemoryCreate(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type=memory_type,
            content=redacted_content,
            graph_execution_id=graph_execution_id,
            node_execution_id=node_execution_id,
            importance_score=importance_score,
            chat_session_id=chat_session_id,
            redacted=True,
        )

        memory = await self.repository.create_memory(memory_data)
        logger.info(
            f"[MEMORY-MANAGER] Created {memory_type} memory for agent "
            f"{agent_name} ({agent_id})"
        )
        return memory

    async def get_agent_memories(
        self,
        agent_id: str,
        memory_types: Optional[list[str]] = None,
        limit: int = 10,
        only_active: bool = True,
        graph_execution_id: Optional[str] = None,
        chat_session_id: Optional[str] = None,
    ) -> list[dict]:
        """Get memories for a specific agent.

        Args:
            agent_id: Agent identifier
            memory_types: Optional list of memory types to filter
            limit: Maximum number of memories to return
            only_active: Whether to only return active memories
            graph_execution_id: Optional execution ID filter
            chat_session_id: Optional chat session ID filter

        Returns:
            List of memory dictionaries

        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        memories = await self.repository.get_memories(
            agent_id=agent_id,
            memory_types=memory_types,
            limit=limit,
            only_active=only_active,
            graph_execution_id=graph_execution_id,
            chat_session_id=chat_session_id,
        )

        # Update access tracking
        memory_ids = [str(m.id) for m in memories]
        if memory_ids:
            await self.repository.update_memory_access(memory_ids)

        # Convert to dictionaries
        memory_dicts = [
            {
                "id": str(memory.id),
                "agent_id": memory.agent_id,
                "agent_name": memory.agent_name,
                "memory_type": memory.memory_type,
                "content": memory.content,
                "importance_score": memory.importance_score,
                "access_count": memory.access_count,
                "is_active": memory.is_active,
                "created_at": memory.created_at,
                "graph_execution_id": memory.graph_execution_id,
                "node_execution_id": memory.node_execution_id,
                "last_accessed": memory.last_accessed,
            }
            for memory in memories
        ]

        logger.debug(
            f"[MEMORY-MANAGER] Retrieved {len(memory_dicts)} memories "
            f"for agent {agent_id}"
        )
        return memory_dicts

    async def get_conversation_history(
        self,
        agent_id: str,
        graph_execution_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get conversation history for an agent.

        Args:
            agent_id: Agent identifier
            graph_execution_id: Optional execution ID filter
            limit: Maximum number of history entries

        Returns:
            List of formatted conversation history entries
        """
        memories = await self.get_agent_memories(
            agent_id=agent_id,
            memory_types=["conversation"],
            limit=limit,
            graph_execution_id=graph_execution_id,
        )

        history = self.formatter.format_conversation_history(memories)
        logger.debug(
            f"[MEMORY-MANAGER] Retrieved conversation history with "
            f"{len(history)} entries for agent {agent_id}"
        )
        return history

    async def store_conversation_turn(
        self,
        agent_id: str,
        agent_name: str,
        user_message: str,
        agent_response: str,
        graph_execution_id: Optional[str] = None,
        node_execution_id: Optional[str] = None,
        chat_session_id: Optional[str] = None,
    ) -> None:
        """Store a complete conversation turn (user message + agent response).

        Args:
            agent_id: Agent identifier
            agent_name: Agent name
            user_message: User's message
            agent_response: Agent's response
            graph_execution_id: Optional graph execution ID
            node_execution_id: Optional node execution ID
            chat_session_id: Optional chat session ID for chat-scoped memory
        """
        # Store user message
        user_content = self.formatter.create_conversation_content(
            message_type="user_message", content=user_message, role="user"
        )
        await self.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="conversation",
            content=user_content,
            graph_execution_id=graph_execution_id,
            node_execution_id=node_execution_id,
            importance_score=0.5,
            chat_session_id=chat_session_id,
        )

        # Store agent response
        agent_content = self.formatter.create_conversation_content(
            message_type="agent_response", content=agent_response, role="assistant"
        )
        await self.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="conversation",
            content=agent_content,
            graph_execution_id=graph_execution_id,
            node_execution_id=node_execution_id,
            importance_score=0.5,
            chat_session_id=chat_session_id,
        )

        # Update statistics
        await self.statistics.record_conversation_turn(agent_id, message_count=2)

        logger.info(f"[MEMORY-MANAGER] Stored conversation turn for agent {agent_name}")

    async def get_or_create_agent_profile(
        self, agent_id: str, agent_name: str, graph_id: str
    ) -> dict:
        """Get or create an agent memory profile.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            graph_id: Graph that this agent belongs to

        Returns:
            Dictionary with profile configuration
        """
        profile = await self.repository.get_or_create_agent_profile(
            agent_id=agent_id, agent_name=agent_name, graph_id=graph_id
        )

        return {
            "id": str(profile.id),
            "agent_id": profile.agent_id,
            "agent_name": profile.agent_name,
            "graph_id": profile.graph_id,
            "memory_window_size": profile.memory_window_size,
            "summarization_threshold": profile.summarization_threshold,
            "memory_retention_days": profile.memory_retention_days,
            "total_conversations": profile.total_conversations,
            "total_messages": profile.total_messages,
            "last_interaction": profile.last_interaction,
        }

    async def get_agent_profile(self, agent_id: str) -> Optional[dict]:
        """Get an existing agent memory profile.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Dictionary with profile configuration, or None if no profile exists
        """
        profile = await self.repository.get_agent_profile(agent_id=agent_id)
        if not profile:
            return None

        return {
            "id": str(profile.id),
            "agent_id": profile.agent_id,
            "agent_name": profile.agent_name,
            "graph_id": profile.graph_id,
            "memory_window_size": profile.memory_window_size,
            "summarization_threshold": profile.summarization_threshold,
            "memory_retention_days": profile.memory_retention_days,
            "total_conversations": profile.total_conversations,
            "total_messages": profile.total_messages,
            "last_interaction": profile.last_interaction,
        }

    async def update_agent_statistics(
        self,
        agent_id: str,
        increment_conversations: bool = False,
        increment_messages: int = 0,
    ) -> None:
        """Update agent interaction statistics.

        Args:
            agent_id: Agent identifier
            increment_conversations: Whether to increment conversation count
            increment_messages: Number of messages to add
        """
        await self.repository.update_agent_statistics(
            agent_id=agent_id,
            increment_conversations=increment_conversations,
            increment_messages=increment_messages,
        )

    async def format_memory_context(self, memories: list[dict]) -> str:
        """Format memories into a context string for the agent.

        Args:
            memories: List of memory dictionaries

        Returns:
            Formatted context string
        """
        return self.formatter.format_memory_context(memories)

    async def prune_old_memories(
        self,
        agent_id: str,
        retention_days: int = 30,
        graph_execution_id: Optional[str] = None,
    ) -> int:
        """Prune old memories for an agent.

        Args:
            agent_id: Agent identifier
            retention_days: Number of days to retain memories
            graph_execution_id: Optional execution ID filter. None means prune
                across all executions and should only be used by internal jobs.

        Returns:
            Number of memories pruned
        """
        return await self.pruning.prune_old_memories(
            agent_id,
            retention_days,
            graph_execution_id,
        )

    async def clear_agent_memory(
        self, agent_id: str, graph_execution_id: Optional[str] = None
    ) -> int:
        """Clear all memories for an agent.

        Args:
            agent_id: Agent identifier
            graph_execution_id: Optional execution ID filter

        Returns:
            Number of memories cleared
        """
        return await self.pruning.clear_agent_memories(agent_id, graph_execution_id)

    async def summarize_conversation(
        self,
        agent_id: str,
        agent_name: str,
        conversation_memory_ids: list[str],
        graph_execution_id: Optional[str] = None,
    ) -> Optional[str]:
        """Create a summary of a conversation.

        Note: This is a placeholder. In production, this would use an LLM
        to create a proper summary.

        Args:
            agent_id: Agent identifier
            agent_name: Agent name
            conversation_memory_ids: IDs of memories to summarize
            graph_execution_id: Optional graph execution ID

        Returns:
            Summary text or None if no memories
        """
        if not conversation_memory_ids:
            return None

        # Get memories
        all_memories = await self.get_agent_memories(
            agent_id=agent_id,
            memory_types=["conversation"],
            limit=100,
            graph_execution_id=graph_execution_id,
        )

        # Filter to requested IDs
        memories_to_summarize = [
            m for m in all_memories if m["id"] in conversation_memory_ids
        ]

        if not memories_to_summarize:
            return None

        # Simple summary (placeholder)
        messages = []
        for memory in memories_to_summarize:
            content = self.formatter.extract_content_from_memory(memory["content"])
            messages.append(content)

        summary = (
            f"Conversation with {len(messages)} messages. "
            f"Topics discussed: {', '.join(messages[:3])}"
        )

        # Store the summary
        await self.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="summary",
            content=summary,
            graph_execution_id=graph_execution_id,
            importance_score=0.7,
        )

        # Mark original memories as less important
        await self.repository.update_importance_scores(
            memory_ids=conversation_memory_ids, new_score=0.3
        )

        logger.info(
            f"[MEMORY-MANAGER] Created conversation summary for agent {agent_name}"
        )
        return summary


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the singleton memory manager instance.

    Returns:
        MemoryManager instance

    Example:
        >>> manager = get_memory_manager()
        >>> memories = await manager.get_agent_memories("agent-1")
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def reset_memory_manager() -> None:
    """Reset the singleton memory manager instance.

    Useful for testing or reinitialization.
    """
    global _memory_manager
    _memory_manager = None
