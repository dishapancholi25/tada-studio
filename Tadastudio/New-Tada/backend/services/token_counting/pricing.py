"""
Cost estimation and pricing data for token counting.

This module contains model pricing information and cost calculation functions.
"""

from typing import Any, Dict, Optional

from backend.services.token_counting.litellm_pricing import (
    get_pricing as litellm_get_pricing,
)


# Pricing per 1M tokens (as of late 2024)
# Updated regularly as model pricing changes
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Embedding models (input-only; output mirrors input for consistency)
    "text-embedding-3-small": {"input": 0.02, "output": 0.02},
    "text-embedding-3-large": {"input": 0.13, "output": 0.13},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.10},
}

# Default model for pricing when model not found
DEFAULT_PRICING_MODEL = "gpt-4o"


def estimate_cost(
    token_counts: Dict[str, int],
    model: str = "gpt-4o",
    custom_pricing: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Estimate cost based on token counts and model.

    Args:
        token_counts: Dictionary with input_tokens and output_tokens
        model: The model name for pricing
        custom_pricing: Optional dict with 'input' and 'output' keys
            (per 1M tokens). When provided, overrides MODEL_PRICING lookup.

    Returns:
        Dictionary with cost breakdown including:
        - input_cost: Cost for input tokens
        - output_cost: Cost for output tokens
        - total_cost: Total cost
        - model: Model used for pricing
        - currency: Currency (USD)
        - pricing_source: One of 'deployment', 'litellm', or 'default'
    """
    # Priority 1 — Custom deployment pricing (require both input and output)
    if (
        custom_pricing
        and custom_pricing.get("input") is not None
        and custom_pricing.get("output") is not None
    ):
        model_pricing = custom_pricing
        pricing_source = "deployment"
    else:
        # Priority 2 — LiteLLM automatic lookup
        litellm_result = litellm_get_pricing(model)
        if litellm_result:
            model_pricing = {
                "input": litellm_result["input"],
                "output": litellm_result["output"],
            }
            pricing_source = "litellm"
        else:
            # Priority 3 — Hardcoded defaults
            model_pricing = MODEL_PRICING.get(
                model, MODEL_PRICING[DEFAULT_PRICING_MODEL]
            )
            pricing_source = "default"

    # Calculate costs (pricing is per 1M tokens)
    input_tokens = token_counts.get("input_tokens", 0)
    output_tokens = token_counts.get("output_tokens", 0)

    input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6),
        "model": model,
        "currency": "USD",
        "pricing_source": pricing_source,
    }


def get_model_pricing(model: str) -> Dict[str, float]:
    """
    Get pricing information for a specific model.

    Args:
        model: Model name

    Returns:
        Dictionary with input and output pricing per 1M tokens
    """
    # Try LiteLLM first, then fall back to hardcoded
    litellm_result = litellm_get_pricing(model)
    if litellm_result:
        return {"input": litellm_result["input"], "output": litellm_result["output"]}
    return MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_PRICING_MODEL])
