"""Memory handler for async agent execution.

This module manages memory operations (retrieval and storage) for agents,
including graceful handling of memory failures.
"""

from typing import Optional

from backend.services.config import get_logger
from backend.services.memory import get_memory_manager


# Get logger for this module
memory_handler_logger = get_logger("async_agent.memory_handler")


class AsyncMemoryHandler:
    """Handles async memory operations for agent execution.

    This class manages retrieval and storage of agent memories,
    providing graceful degradation when memory operations fail.
    Memory failures are logged but don't halt execution.
    """

    def __init__(self):
        """Initialize the memory handler."""
        self.logger = memory_handler_logger
        self.memory_manager = None

    def _get_memory_manager(self):
        """Lazy load memory manager.

        Returns:
            Memory manager instance
        """
        if self.memory_manager is None:
            self.memory_manager = get_memory_manager()
        return self.memory_manager

    async def get_memory_context(
        self,
        node_id: str,
        db_execution_id: Optional[str] = None,
        limit: int = 10,
        memory_strategy: str = "thread_scoped",
        memory_window_size: Optional[int] = None,
    ) -> Optional[str]:
        """Retrieve memory context for an agent.

        Gets recent conversation history for the agent and formats it
        as context to include in the prompt.

        Args:
            node_id: Node/agent identifier
            db_execution_id: Database execution ID for scoping memories
            limit: Maximum number of memory entries to retrieve (fallback)
            memory_strategy: Memory scoping strategy (thread_scoped, cross_thread, etc.)
            memory_window_size: Optional window size to determine retrieval count

        Returns:
            Formatted memory context string, or None if no memories or error

        Note:
            This method does not raise exceptions. Memory failures are logged
            but allow execution to continue without memory.
        """
        try:
            memory_limit = (memory_window_size * 2) if memory_window_size else limit
            execution_filter = (
                db_execution_id if memory_strategy == "thread_scoped" else None
            )

            self.logger.info(
                f"[MEMORY] Retrieving memory context for node {node_id} "
                f"(execution: {execution_filter}, limit: {memory_limit}, "
                f"strategy: {memory_strategy})"
            )

            memory_manager = self._get_memory_manager()

            # Get memories for this agent
            memories = await memory_manager.get_agent_memories(
                agent_id=node_id,
                graph_execution_id=execution_filter,
                limit=memory_limit,
            )

            if not memories:
                self.logger.debug(f"[MEMORY] No memories found for node {node_id}")
                return None

            # Format memories into context string
            context = await memory_manager.format_memory_context(memories)

            if context:
                self.logger.info(
                    f"[MEMORY] Retrieved {len(memories)} memories for node {node_id}"
                )
            else:
                self.logger.debug(
                    f"[MEMORY] No formatted context from {len(memories)} memories"
                )

            return context

        except Exception as e:
            # Log error but don't raise - memory is optional
            self.logger.warning(
                f"[MEMORY] Failed to get memory context for node {node_id}: {str(e)}",
                exc_info=True,
            )
            return None

    async def store_conversation(
        self,
        node_id: str,
        node_name: str,
        user_message: str,
        assistant_message: str,
        db_execution_id: Optional[str] = None,
        node_execution_id: Optional[str] = None,
    ) -> bool:
        """Store a conversation turn in memory.

        Saves the user message and agent response for future context.

        Args:
            node_id: Node/agent identifier
            node_name: Human-readable agent name
            user_message: User's input message
            assistant_message: Agent's response
            db_execution_id: Database execution ID
            node_execution_id: Node execution ID

        Returns:
            True if storage succeeded, False otherwise

        Note:
            This method does not raise exceptions. Storage failures are logged
            but don't prevent execution from completing.
        """
        try:
            self.logger.info(
                f"[MEMORY] Storing conversation for node {node_id} "
                f"(execution: {db_execution_id})"
            )

            memory_manager = self._get_memory_manager()

            # Store the conversation turn
            await memory_manager.store_conversation_turn(
                agent_id=node_id,
                agent_name=node_name,
                user_message=user_message,
                agent_response=assistant_message,
                graph_execution_id=db_execution_id,
                node_execution_id=node_execution_id,
            )

            self.logger.info(
                f"[MEMORY] Successfully stored conversation for node {node_id}"
            )
            return True

        except Exception as e:
            # Log error but don't raise - memory storage is optional
            self.logger.warning(
                f"[MEMORY] Failed to store conversation for node {node_id}: {str(e)}",
                exc_info=True,
            )
            return False

    async def check_memory_enabled(
        self,
        agent_config,
        use_memory_config: bool = True,
    ) -> bool:
        """Check if memory should be used for this agent.

        Args:
            agent_config: Agent configuration
            use_memory_config: Global memory configuration flag

        Returns:
            True if memory should be used, False otherwise
        """
        # Check if agent has memory enabled
        if (
            not hasattr(agent_config, "memory_enabled")
            or not agent_config.memory_enabled
        ):
            return False

        # Check global memory config (from ExecutionConfig)
        if not use_memory_config:
            return False

        return True
