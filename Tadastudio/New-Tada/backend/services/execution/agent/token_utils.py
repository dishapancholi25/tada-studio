"""Token counting utilities for agent execution.

This module provides helpers for extracting and counting tokens from LLM responses.
"""

import logging
from typing import Any, Dict

from backend.services.token_counting import get_token_counter


logger = logging.getLogger("agent_execution")


def extract_token_counts(response: Any, prefix: str = "") -> Dict[str, int]:
    """Extract token counts from LLM response metadata.

    Args:
        response: LLM response object
        prefix: Optional prefix for logging

    Returns:
        Dictionary with input_tokens, output_tokens, and total_tokens
    """
    counts = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        # Prefer usage_metadata as it has the cleaner format
        logger.info(
            f"{prefix}Got token usage from usage_metadata: {response.usage_metadata}"
        )
        counts["input_tokens"] = response.usage_metadata.get("input_tokens", 0)
        counts["output_tokens"] = response.usage_metadata.get("output_tokens", 0)
        counts["total_tokens"] = response.usage_metadata.get("total_tokens", 0)
    elif hasattr(response, "response_metadata") and response.response_metadata:
        # Fall back to response_metadata token_usage
        usage = response.response_metadata.get("token_usage", {})
        if usage:
            logger.info(f"{prefix}Got token usage from response_metadata: {usage}")
            counts["input_tokens"] = usage.get("prompt_tokens", 0)
            counts["output_tokens"] = usage.get("completion_tokens", 0)
            counts["total_tokens"] = usage.get("total_tokens", 0)

    return counts


def count_string_tokens(text: str) -> int:
    """Count tokens in a string.

    Args:
        text: Text to count tokens for

    Returns:
        Estimated token count
    """
    token_counter = get_token_counter()
    return token_counter.count_string(text)


def count_message_tokens(messages: list) -> Dict[str, int]:
    """Count tokens in messages.

    Args:
        messages: List of messages

    Returns:
        Dictionary with token counts
    """
    token_counter = get_token_counter()
    return token_counter.count_messages(messages)
