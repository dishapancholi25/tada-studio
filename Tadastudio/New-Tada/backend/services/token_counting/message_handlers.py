"""
Message type handlers and classification for token counting.

This module handles message type classification and specialized token counting.
"""

import json
import logging
from typing import Callable, Dict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


logger = logging.getLogger(__name__)


class MessageClassifier:
    """Classifies messages and aggregates token counts by type."""

    @staticmethod
    def get_message_type(message: BaseMessage) -> str:
        """
        Get the type/role of a message.

        Args:
            message: LangChain message to classify

        Returns:
            Message type string (system, human, ai, tool, other)
        """
        if isinstance(message, SystemMessage):
            return "system"
        elif isinstance(message, HumanMessage):
            return "human"
        elif isinstance(message, AIMessage):
            return "ai"
        elif isinstance(message, ToolMessage):
            return "tool"
        else:
            return "other"

    @staticmethod
    def create_breakdown() -> Dict[str, int]:
        """
        Create an empty token breakdown dictionary.

        Returns:
            Dictionary with all message type keys initialized to 0
        """
        return {
            "system": 0,
            "human": 0,
            "ai": 0,
            "tool": 0,
            "other": 0,
            "message_count": 0,
        }

    @staticmethod
    def update_breakdown(
        breakdown: Dict[str, int], message_type: str, tokens: int
    ) -> None:
        """
        Update breakdown dictionary with token count for message type.

        Args:
            breakdown: The breakdown dictionary to update
            message_type: Type of message (system, human, ai, tool, other)
            tokens: Number of tokens to add
        """
        if message_type in breakdown:
            breakdown[message_type] += tokens


class ToolCallCounter:
    """Handles counting tokens in tool calls within AI messages."""

    def __init__(self, string_counter: Callable[[str], int]):
        """
        Initialize tool call counter.

        Args:
            string_counter: Function to count tokens in a string
        """
        self.count_string = string_counter

    def count_message_tool_calls(self, message: BaseMessage) -> int:
        """
        Count tokens in tool calls attached to a message.

        Args:
            message: Message to check for tool calls

        Returns:
            Number of tokens in tool calls
        """
        # Only AI messages have tool calls
        if not isinstance(message, AIMessage):
            return 0

        # Check if message has tool_calls attribute
        if not hasattr(message, "tool_calls"):
            return 0

        tool_calls = getattr(message, "tool_calls", [])
        if not tool_calls:
            return 0

        # Count tokens in each tool call
        total_tokens = 0
        for tool_call in tool_calls:
            tool_json = json.dumps(tool_call)
            total_tokens += self.count_string(tool_json)

        return total_tokens
