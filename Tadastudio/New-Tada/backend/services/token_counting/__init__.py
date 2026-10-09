"""
Token counting service for accurate token estimation using tiktoken.

This package provides token counting functionality for LangChain messages,
tool calls, and cost estimation for various LLM models.

Example usage:
    from backend.services.token_counting import get_token_counter, estimate_cost

    # Get a token counter instance
    counter = get_token_counter(model="gpt-4o")

    # Count tokens in messages
    result = counter.count_messages(messages)
    print(f"Total tokens: {result['total']}")

    # Estimate cost
    cost = estimate_cost({"input_tokens": 1000, "output_tokens": 500}, model="gpt-4o")
    print(f"Estimated cost: ${cost['total_cost']}")
"""

from .base import BaseTokenCounter
from .pricing import MODEL_PRICING, estimate_cost, get_model_pricing
from .token_counter import TokenCounter
from .utils import EncodingCache


# Singleton instance for easy import
_default_counter = None


def get_token_counter(model: str = "gpt-4o") -> TokenCounter:
    """
    Get or create a token counter instance.

    This function implements the singleton pattern to avoid re-initializing
    the tiktoken encoding unnecessarily.

    Args:
        model: The model to use for tokenization (default: gpt-4o)

    Returns:
        TokenCounter instance configured for the specified model
    """
    global _default_counter
    if _default_counter is None:
        _default_counter = TokenCounter(model)
    return _default_counter


__all__ = [
    # Main classes
    "TokenCounter",
    "BaseTokenCounter",
    # Factory function
    "get_token_counter",
    # Pricing utilities
    "estimate_cost",
    "get_model_pricing",
    "MODEL_PRICING",
    # Utilities
    "EncodingCache",
]
