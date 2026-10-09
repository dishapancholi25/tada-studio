"""Memory management for agent execution.

This module handles loading conversation history and storing new conversations
for agents with memory enabled.
"""

import asyncio
import logging
from typing import Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.memory import get_memory_manager


logger = logging.getLogger("agent_execution")


class MemoryHandler:
    """Handles memory operations for agent execution."""

    @staticmethod
    async def load_memory_context(
        agent_node: EnhancedNodeData,
        db_execution_id: Optional[str] = None,
    ) -> str:
        """Load memory context for an agent.

        Args:
            agent_node: The agent node to load memory for
            db_execution_id: Optional database execution ID for filtering

        Returns:
            Formatted memory context string, or empty string if no memories
        """
        if not agent_node.agent_config or not agent_node.agent_config.memory_enabled:
            return ""

        try:
            memory_manager = get_memory_manager()

            # Get agent's memory profile
            profile = await memory_manager.get_or_create_agent_profile(
                agent_id=agent_node.uniq_id,
                agent_name=agent_node.name,
                graph_id="subagent_execution",
            )

            # Get recent memories
            # Only filter by execution ID if memory strategy is thread-scoped
            execution_filter = (
                db_execution_id
                if agent_node.agent_config.memory_strategy == "thread_scoped"
                else None
            )
            memories = await memory_manager.get_agent_memories(
                agent_id=agent_node.uniq_id,
                limit=profile.get("memory_window_size", 10) * 2,  # Get pairs
                graph_execution_id=execution_filter,
            )

            logger.info(
                f"Retrieved {len(memories)} memories for agent {agent_node.name} "
                f"(strategy: {agent_node.agent_config.memory_strategy}, "
                f"filter: {execution_filter})"
            )

            # Format memory context
            memory_context = await memory_manager.format_memory_context(memories)

            if memory_context:
                logger.info(f"Loaded memory context for agent {agent_node.name}")
                # Log memory details
                logger.info("===== MEMORY CONTEXT DETAILS =====")
                logger.info(f"Memory Context Size: {len(memory_context)} characters")
                logger.info("Memory Context Preview (first 500 chars):")
                logger.info(
                    memory_context[:500] + ("..." if len(memory_context) > 500 else "")
                )
                logger.info(
                    f"Estimated Memory Tokens: ~{len(memory_context) // 4} tokens"
                )
                logger.info("===== END MEMORY CONTEXT =====")

            return memory_context

        except Exception as e:
            logger.error(
                f"Failed to load memory for agent {agent_node.name}: {e}",
                exc_info=True,
            )
            return ""

    @staticmethod
    def load_memory_context_sync(
        agent_node: EnhancedNodeData,
        db_execution_id: Optional[str] = None,
    ) -> str:
        """Synchronous wrapper for load_memory_context.

        Args:
            agent_node: The agent node to load memory for
            db_execution_id: Optional database execution ID for filtering

        Returns:
            Formatted memory context string, or empty string if no memories
        """
        return asyncio.run(
            MemoryHandler.load_memory_context(agent_node, db_execution_id)
        )

    @staticmethod
    async def store_memory(
        agent_node: EnhancedNodeData,
        user_message: str,
        agent_response: str,
        db_execution_id: Optional[str] = None,
    ) -> None:
        """Store conversation in memory if enabled for the agent.

        Args:
            agent_node: The agent node
            user_message: Original user message (without memory context)
            agent_response: Agent's response
            db_execution_id: Database execution ID
        """
        if not agent_node.agent_config or not agent_node.agent_config.memory_enabled:
            return

        try:
            memory_manager = get_memory_manager()

            await memory_manager.store_conversation_turn(
                agent_id=agent_node.uniq_id,
                agent_name=agent_node.name,
                user_message=user_message,
                agent_response=agent_response,
                graph_execution_id=db_execution_id,
                node_execution_id=None,  # Not available in simple chat execution
            )

            logger.info(
                f"Stored conversation turn in memory for agent {agent_node.name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to store memory for agent {agent_node.name}: {e}",
                exc_info=True,
            )

    @staticmethod
    def store_memory_sync(
        agent_node: EnhancedNodeData,
        user_message: str,
        agent_response: str,
        db_execution_id: Optional[str] = None,
    ) -> None:
        """Synchronous wrapper for store_memory.

        Args:
            agent_node: The agent node
            user_message: Original user message (without memory context)
            agent_response: Agent's response
            db_execution_id: Database execution ID
        """
        asyncio.run(
            MemoryHandler.store_memory(
                agent_node, user_message, agent_response, db_execution_id
            )
        )
