"""Memory formatting utilities.

This module provides utilities for formatting memory data into context strings
that can be used by LLM agents during execution.
"""

import json
from typing import Any

from backend.services.config import get_logger


logger = get_logger("memory_formatter")


class MemoryFormatter:
    """Formatter for memory data.

    Provides methods to format various types of memories into context strings
    suitable for agent prompts and LLM input.
    """

    @staticmethod
    def format_memory_context(memories: list[dict[str, Any]]) -> str:
        """Format memories into a context string for the agent.

        Args:
            memories: List of memory dictionaries

        Returns:
            Formatted context string

        Examples:
            >>> memories = [
            ...     {"memory_type": "fact", "content": "User prefers Python"},
            ...     {"memory_type": "conversation", "content": "..."}
            ... ]
            >>> context = MemoryFormatter.format_memory_context(memories)
        """
        if not memories:
            return ""

        context_parts = []

        # Group by memory type
        conversation_memories = [
            m for m in memories if m.get("memory_type") == "conversation"
        ]
        summary_memories = [m for m in memories if m.get("memory_type") == "summary"]
        fact_memories = [m for m in memories if m.get("memory_type") == "fact"]

        # Format summaries
        if summary_memories:
            context_parts.append("Previous Conversation Summaries:")
            for memory in summary_memories[:3]:  # Limit summaries
                content = memory.get("content", "")
                context_parts.append(f"- {content}")

        # Format facts
        if fact_memories:
            context_parts.append("\nRemembered Facts:")
            for memory in fact_memories[:5]:  # Limit facts
                content = memory.get("content", "")
                context_parts.append(f"- {content}")

        # Format conversation history
        if conversation_memories:
            context_parts.append("\nRecent Conversation History:")
            # Reverse to show chronological order
            for memory in reversed(conversation_memories):
                formatted = MemoryFormatter._format_conversation_entry(memory)
                if formatted:
                    context_parts.append(formatted)

        return "\n".join(context_parts)

    @staticmethod
    def _format_conversation_entry(memory: dict[str, Any]) -> str:
        """Format a single conversation memory entry.

        Args:
            memory: Memory dictionary

        Returns:
            Formatted conversation entry
        """
        try:
            content = memory.get("content", "")

            # Try to parse as JSON
            if content.startswith("{"):
                content_data = json.loads(content)
                role = content_data.get("role", "assistant")
                message = content_data.get("content", content)
                return f"{role.title()}: {message}"
            else:
                return f"Assistant: {content}"

        except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as e:
            logger.debug(f"[MEMORY-FORMATTER] Failed to parse memory content: {e}")
            return f"Assistant: {memory.get('content', '')}"

    @staticmethod
    def format_conversation_history(
        memories: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Format conversation memories into structured history.

        Args:
            memories: List of conversation memory dictionaries

        Returns:
            List of formatted conversation history entries

        Examples:
            >>> memories = [{"content": '{"role": "user", "content": "Hello"}'}]
            >>> history = MemoryFormatter.format_conversation_history(memories)
            >>> history[0]["role"]
            'user'
        """
        history = []

        for memory in reversed(memories):  # Chronological order
            try:
                content = memory.get("content", "")
                created_at = memory.get("created_at")

                # Parse content
                if content.startswith("{"):
                    content_data = json.loads(content)
                else:
                    content_data = {"content": content}

                # Format timestamp
                timestamp_str = (
                    created_at.isoformat()
                    if hasattr(created_at, "isoformat")
                    else str(created_at)
                )

                history.append(
                    {
                        "timestamp": timestamp_str,
                        "type": content_data.get("type", "message"),
                        "content": content_data.get("content", content),
                        "role": content_data.get("role", "assistant"),
                    }
                )

            except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as e:
                logger.error(f"[MEMORY-FORMATTER] Error parsing memory content: {e}")
                # Fallback entry
                timestamp_str = (
                    memory["created_at"].isoformat()
                    if hasattr(memory.get("created_at"), "isoformat")
                    else str(memory.get("created_at", ""))
                )
                history.append(
                    {
                        "timestamp": timestamp_str,
                        "type": "message",
                        "content": memory.get("content", ""),
                        "role": "assistant",
                    }
                )

        return history

    @staticmethod
    def create_conversation_content(message_type: str, content: str, role: str) -> str:
        """Create properly formatted conversation content.

        Args:
            message_type: Type of message (user_message, agent_response)
            content: Message content
            role: Role (user, assistant)

        Returns:
            JSON-formatted content string

        Examples:
            >>> content = MemoryFormatter.create_conversation_content(
            ...     "user_message", "Hello", "user"
            ... )
            >>> "type" in content and "content" in content
            True
        """
        data = {
            "type": message_type,
            "content": content,
            "role": role,
        }
        return json.dumps(data)

    @staticmethod
    def extract_content_from_memory(memory_content: str) -> str:
        """Extract plain text content from memory.

        Args:
            memory_content: Memory content (may be JSON or plain text)

        Returns:
            Plain text content

        Examples:
            >>> json_content = '{"content": "Hello", "role": "user"}'
            >>> MemoryFormatter.extract_content_from_memory(json_content)
            'Hello'
            >>> MemoryFormatter.extract_content_from_memory("Plain text")
            'Plain text'
        """
        try:
            if memory_content.startswith("{"):
                data = json.loads(memory_content)
                return data.get("content", memory_content)
            return memory_content
        except (json.JSONDecodeError, AttributeError):
            return memory_content
