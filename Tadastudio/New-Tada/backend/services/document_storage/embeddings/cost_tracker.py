"""Embedding cost tracking utilities.

Counts tokens via tiktoken and calculates embedding costs using the
same three-tier pricing resolution as LLM cost tracking
(deployment → LiteLLM → default).
"""

import logging
from typing import Any, Dict, List, Optional

from backend.services.token_counting.utils import EncodingCache
from backend.services.trace.cost_calculator import CostCalculator

logger = logging.getLogger(__name__)


def count_tokens(texts: List[str], model: str = "text-embedding-3-small") -> int:
    """Count tokens for a list of texts using tiktoken.

    Args:
        texts: List of text strings to count tokens for.
        model: Model name used to select the tokeniser.

    Returns:
        Total token count across all texts.
    """
    encoding = EncodingCache.get_encoding(model)
    total = 0
    for text in texts:
        total += len(encoding.encode(text))
    return total


def calculate_embedding_cost(
    token_count: int,
    model_name: str = "text-embedding-3-small",
    custom_input_cost: Optional[float] = None,
    custom_output_cost: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate the cost of an embedding operation.

    Uses CostCalculator._resolve_pricing() for the standard three-tier
    pricing chain (deployment → LiteLLM → default).

    Args:
        token_count: Number of input tokens.
        model_name: Model identifier for pricing lookup.
        custom_input_cost: Per-1M-token input cost override from a deployment.
        custom_output_cost: Per-1M-token output cost override from a deployment.

    Returns:
        Dict with keys: tokens, cost, model, pricing_source.
    """
    model_key = model_name.lower() if model_name else "text-embedding-3-small"
    costs, pricing_source = CostCalculator._resolve_pricing(
        model_key, custom_input_cost, custom_output_cost
    )

    cost = (token_count / 1_000_000) * costs["input"]

    return {
        "tokens": token_count,
        "cost": round(cost, 6),
        "model": model_name,
        "pricing_source": pricing_source,
    }
