"""Token counting service using tiktoken for accurate token estimation.

Based on GPT-4o tokenization.

This is the main TokenCounter class that coordinates all token counting operations.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import BaseMessage

from .base import BaseTokenCounter
from .content_handlers import ContentTokenCounter
from .message_handlers import MessageClassifier, ToolCallCounter
from .utils import (
    CHARS_PER_TOKEN_FALLBACK,
    CONVERSATION_END_TOKENS,
    TOKENS_PER_MESSAGE,
    EncodingCache,
)


logger = logging.getLogger(__name__)


class TokenCounter(BaseTokenCounter):
    """Service for counting tokens in messages and content using tiktoken."""

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize token counter with specified model encoding.

        Args:
            model: The model to use for tokenization (default: gpt-4o)
        """
        self.model = model
        self.encoding = EncodingCache.get_encoding(model)
        self.content_counter = ContentTokenCounter(self.count_string)
        self.tool_call_counter = ToolCallCounter(self.count_string)

    def count_string(self, text: str) -> int:
        """
        Count tokens in a string.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens in string: {e}")
            # Fallback to character-based estimation
            return len(text) // CHARS_PER_TOKEN_FALLBACK

    def count_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        Count tokens in a list of messages.

        Args:
            messages: List of LangChain messages

        Returns:
            Dictionary with token counts and breakdown
        """
        total_tokens = 0
        breakdown = MessageClassifier.create_breakdown()
        breakdown["message_count"] = len(messages)

        for message in messages:
            # Count tokens for this message
            message_tokens = self._count_single_message(message)
            total_tokens += message_tokens

            # Update breakdown by message type
            message_type = MessageClassifier.get_message_type(message)
            MessageClassifier.update_breakdown(breakdown, message_type, message_tokens)

        # Add conversation structure overhead
        total_tokens += CONVERSATION_END_TOKENS

        return {
            "total": total_tokens,
            "breakdown": breakdown,
            "messages": len(messages),
        }

    def _count_single_message(self, message: BaseMessage) -> int:
        """
        Count tokens for a single message.

        Args:
            message: Message to count

        Returns:
            Number of tokens
        """
        # Count role tokens
        role = getattr(message, "role", None) or message.__class__.__name__.lower()
        role_tokens = self.count_string(role)

        # Count content tokens using content handler
        content_tokens = self.content_counter.count_content(message.content)

        # Count tool call tokens if present
        tool_call_tokens = self.tool_call_counter.count_message_tool_calls(message)

        # Calculate total with message overhead
        return role_tokens + content_tokens + tool_call_tokens + TOKENS_PER_MESSAGE

    def count_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> int:
        """
        Count tokens in tool calls.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            Number of tokens
        """
        if not tool_calls:
            return 0

        import json

        total = 0
        for tool_call in tool_calls:
            # Serialize the tool call to count tokens
            tool_json = json.dumps(tool_call)
            total += self.count_string(tool_json)

        return total

    def count_input_output(
        self,
        input_messages: Optional[List[BaseMessage]] = None,
        output_content: Optional[Union[str, BaseMessage]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Count tokens for both input and output of an LLM call.

        Args:
            input_messages: Input messages sent to the LLM
            output_content: Output from the LLM (string or message)
            tool_calls: Any tool calls made by the LLM

        Returns:
            Dictionary with input, output, and total token counts
        """
        result = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }

        # Count input tokens
        if input_messages:
            input_count = self.count_messages(input_messages)
            result["input_tokens"] = input_count["total"]
            result["metadata"]["input_breakdown"] = input_count["breakdown"]

        # Count output tokens
        if output_content:
            if isinstance(output_content, str):
                result["output_tokens"] = self.count_string(output_content)
            elif isinstance(output_content, BaseMessage):
                output_count = self.count_messages([output_content])
                result["output_tokens"] = output_count["total"]
                result["metadata"]["output_breakdown"] = output_count["breakdown"]

        # Add tool call tokens to output
        if tool_calls:
            tool_tokens = self.count_tool_calls(tool_calls)
            result["output_tokens"] += tool_tokens
            result["metadata"]["tool_tokens"] = tool_tokens

        # Calculate total
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]

        return result
