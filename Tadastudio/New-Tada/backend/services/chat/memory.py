"""Chat memory service for storing and loading chat conversation history.

This module provides chat-specific memory operations that store conversation turns
in the ConversationMemory table with chat_session_id for proper scoping and isolation.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.models import ConversationMemory
from backend.services.database import get_db
from backend.services.memory import get_memory_manager
from backend.services.memory.redaction import redact_memory_content
from backend.services.workflow.state.schemas import MemoryContext


logger = logging.getLogger("chat_memory")


class ChatMemoryService:
    """Service for chat-specific memory operations.

    Stores and loads chat conversation history using the existing ConversationMemory
    system with chat_session_id scoping for isolation between sessions.

    Provides both async methods (for API handlers) and sync methods (for use in
    executor threads where creating a new event loop is problematic).
    """

    def __init__(self):
        """Initialize with the memory manager singleton."""
        self._memory_manager = None

    @property
    def memory_manager(self):
        """Lazy-load memory manager to avoid circular imports."""
        if self._memory_manager is None:
            self._memory_manager = get_memory_manager()
        return self._memory_manager

    # ==================== Synchronous Methods (for executor threads) ====================

    def store_chat_turn_sync(
        self,
        chat_session_id: str,
        user_message: str,
        assistant_response: str,
        graph_execution_id: str,
        workflow_name: str,
    ) -> None:
        """Store a chat conversation turn synchronously.

        Uses direct DB operations to avoid async/event-loop issues
        when called from executor threads.

        Args:
            chat_session_id: Chat session identifier
            user_message: The user's message
            assistant_response: The workflow's response
            graph_execution_id: Associated execution ID
            workflow_name: Workflow name for the agent_name field
        """
        agent_id = f"chat_session_{chat_session_id}"

        try:
            now = datetime.now(timezone.utc)

            # Redact before persistence so raw PII never reaches this write path.
            redacted_user_content = redact_memory_content(
                json.dumps({"role": "user", "content": user_message})
            )
            redacted_assistant_content = redact_memory_content(
                json.dumps({"role": "assistant", "content": assistant_response})
            )

            with get_db() as db:
                # Store user message (explicit timestamp to guarantee ordering)
                user_memory = ConversationMemory(
                    agent_id=agent_id,
                    agent_name=workflow_name,
                    memory_type="chat_conversation",
                    content=redacted_user_content,
                    graph_execution_id=graph_execution_id,
                    chat_session_id=chat_session_id,
                    importance_score=0.5,
                    created_at=now,
                )
                db.add(user_memory)

                # Store assistant response (offset by 1μs so it sorts after user message)
                assistant_memory = ConversationMemory(
                    agent_id=agent_id,
                    agent_name=workflow_name,
                    memory_type="chat_conversation",
                    content=redacted_assistant_content,
                    graph_execution_id=graph_execution_id,
                    chat_session_id=chat_session_id,
                    importance_score=0.5,
                    created_at=now + timedelta(microseconds=1),
                )
                db.add(assistant_memory)

                db.commit()

            logger.info(
                f"Stored chat turn for session {chat_session_id} "
                f"(execution: {graph_execution_id})"
            )
        except Exception as e:
            logger.error(f"Failed to store chat turn: {e}", exc_info=True)

    def load_chat_history_sync(
        self,
        chat_session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Load chat history synchronously.

        Args:
            chat_session_id: Chat session identifier
            limit: Maximum number of memory entries to return

        Returns:
            List of message dicts with role, content, created_at, execution_id
        """
        agent_id = f"chat_session_{chat_session_id}"

        try:
            with get_db() as db:
                memories = (
                    db.query(ConversationMemory)
                    .filter(
                        ConversationMemory.agent_id == agent_id,
                        ConversationMemory.chat_session_id == chat_session_id,
                        ConversationMemory.memory_type == "chat_conversation",
                        ConversationMemory.is_active == True,  # noqa: E712
                    )
                    .order_by(ConversationMemory.created_at.asc())
                    .limit(limit)
                    .all()
                )

                messages = []
                for memory in memories:
                    try:
                        parsed = json.loads(memory.content)
                        messages.append({
                            "role": parsed.get("role", "unknown"),
                            "content": parsed.get("content", ""),
                            "execution_id": memory.graph_execution_id,
                            "created_at": memory.created_at,
                        })
                    except (json.JSONDecodeError, KeyError):
                        messages.append({
                            "role": "assistant",
                            "content": memory.content or "",
                            "execution_id": memory.graph_execution_id,
                            "created_at": memory.created_at,
                        })

                return messages

        except Exception as e:
            logger.error(
                f"Failed to load chat history for session {chat_session_id}: {e}",
                exc_info=True,
            )
            return []

    def build_memory_context_sync(
        self,
        chat_session_id: str,
        window_size: int = 20,
    ) -> Optional[MemoryContext]:
        """Build a MemoryContext synchronously for injection into workflow state.

        Args:
            chat_session_id: Chat session identifier
            window_size: Maximum number of message pairs to include

        Returns:
            MemoryContext if history exists, None otherwise
        """
        messages = self.load_chat_history_sync(
            chat_session_id=chat_session_id,
            limit=window_size * 2,
        )

        if not messages:
            return None

        context_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

        if len(context_messages) > window_size * 2:
            context_messages = context_messages[-(window_size * 2):]

        memory_context: MemoryContext = {
            "conversation_id": chat_session_id,
            "messages": context_messages,
            "summary": None,
            "metadata": {"source": "chat_session", "message_count": len(context_messages)},
        }

        logger.info(
            f"Built memory context for chat session {chat_session_id}: "
            f"{len(context_messages)} messages"
        )

        return memory_context

    # ==================== Async Methods (for API handlers) ====================

    async def store_chat_turn(
        self,
        chat_session_id: str,
        user_message: str,
        assistant_response: str,
        graph_execution_id: str,
        workflow_name: str,
    ) -> None:
        """Store a chat conversation turn in ConversationMemory.

        Stores both the user message and assistant response as separate
        memory entries with memory_type="chat_conversation" and the
        chat_session_id set for scoped retrieval.

        Args:
            chat_session_id: Chat session identifier
            user_message: The user's message
            assistant_response: The workflow's response
            graph_execution_id: Associated execution ID
            workflow_name: Workflow name for the agent_name field
        """
        agent_id = f"chat_session_{chat_session_id}"

        try:
            # Store user message
            await self.memory_manager.create_memory(
                agent_id=agent_id,
                agent_name=workflow_name,
                memory_type="chat_conversation",
                content=json.dumps({"role": "user", "content": user_message}),
                graph_execution_id=graph_execution_id,
                chat_session_id=chat_session_id,
                importance_score=0.5,
            )

            # Store assistant response
            await self.memory_manager.create_memory(
                agent_id=agent_id,
                agent_name=workflow_name,
                memory_type="chat_conversation",
                content=json.dumps({"role": "assistant", "content": assistant_response}),
                graph_execution_id=graph_execution_id,
                chat_session_id=chat_session_id,
                importance_score=0.5,
            )

            logger.info(
                f"Stored chat turn for session {chat_session_id} "
                f"(execution: {graph_execution_id})"
            )
        except Exception as e:
            logger.error(f"Failed to store chat turn: {e}", exc_info=True)

    async def load_chat_history(
        self,
        chat_session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Load chat history for display.

        Queries ConversationMemory entries scoped to the given chat session,
        ordered by creation time ascending.

        Args:
            chat_session_id: Chat session identifier
            limit: Maximum number of memory entries to return

        Returns:
            List of message dicts with role, content, created_at, execution_id
        """
        agent_id = f"chat_session_{chat_session_id}"

        try:
            memories = await self.memory_manager.get_agent_memories(
                agent_id=agent_id,
                memory_types=["chat_conversation"],
                chat_session_id=chat_session_id,
                limit=limit,
                only_active=True,
            )

            messages = []
            for memory in memories:
                try:
                    parsed = json.loads(memory["content"])
                    messages.append({
                        "role": parsed.get("role", "unknown"),
                        "content": parsed.get("content", ""),
                        "execution_id": memory.get("graph_execution_id"),
                        "created_at": memory.get("created_at"),
                    })
                except (json.JSONDecodeError, KeyError):
                    # Fallback for non-JSON content
                    messages.append({
                        "role": "assistant",
                        "content": memory.get("content", ""),
                        "execution_id": memory.get("graph_execution_id"),
                        "created_at": memory.get("created_at"),
                    })

            # Memories come back in descending order; reverse for chronological
            messages.reverse()
            return messages

        except Exception as e:
            logger.error(
                f"Failed to load chat history for session {chat_session_id}: {e}",
                exc_info=True,
            )
            return []

    async def build_memory_context(
        self,
        chat_session_id: str,
        window_size: int = 20,
    ) -> Optional[MemoryContext]:
        """Build a MemoryContext from chat history for injection into workflow state.

        Loads recent chat history and formats it as a MemoryContext TypedDict
        that can be set on WorkflowState.memory_context.

        Args:
            chat_session_id: Chat session identifier
            window_size: Maximum number of message pairs to include

        Returns:
            MemoryContext if history exists, None otherwise
        """
        # Load more than window_size to account for pairs (user + assistant = 2 entries)
        messages = await self.load_chat_history(
            chat_session_id=chat_session_id,
            limit=window_size * 2,
        )

        if not messages:
            return None

        # Format as MemoryContext messages
        context_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

        # Truncate to window_size pairs (window_size * 2 individual messages)
        if len(context_messages) > window_size * 2:
            context_messages = context_messages[-(window_size * 2):]

        memory_context: MemoryContext = {
            "conversation_id": chat_session_id,
            "messages": context_messages,
            "summary": None,
            "metadata": {"source": "chat_session", "message_count": len(context_messages)},
        }

        logger.info(
            f"Built memory context for chat session {chat_session_id}: "
            f"{len(context_messages)} messages"
        )

        return memory_context
