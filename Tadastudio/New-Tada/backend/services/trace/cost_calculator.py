"""Cost calculation utilities for trace nodes.

Handles token-based cost estimation for various LLM models.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from backend.services.token_counting.litellm_pricing import get_pricing

logger = logging.getLogger(__name__)


class CostCalculator:
    """Calculate costs for LLM operations based on token usage."""

    # AUD pricing per 1M tokens
    TOKEN_COSTS = {
        "gpt-4o": {"input": 3.85446, "output": 15.4179},
        "gpt-4o-latest": {"input": 3.85446, "output": 15.4179},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},  # USD for now
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},  # USD for now
        "gpt-4": {"input": 30.0, "output": 60.0},  # USD for now
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},  # USD for now
        "claude-3-opus": {"input": 15.0, "output": 75.0},  # USD for now
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},  # USD for now
        "claude-3-haiku": {"input": 0.25, "output": 1.25},  # USD for now
        # Embedding models (input-only; output mirrors input for consistency)
        "text-embedding-3-small": {"input": 0.02, "output": 0.02},
        "text-embedding-3-large": {"input": 0.13, "output": 0.13},
        "text-embedding-ada-002": {"input": 0.10, "output": 0.10},
    }

    @classmethod
    def _resolve_pricing(
        cls,
        model_key: str,
        custom_input_cost: Optional[float] = None,
        custom_output_cost: Optional[float] = None,
    ) -> Tuple[Dict[str, float], str]:
        """Resolve pricing using the three-tier priority chain.

        Returns:
            Tuple of (cost_dict with 'input'/'output' keys, source_label).
            source_label is one of 'deployment', 'litellm', or 'default'.
        """
        # Priority 1 — Custom deployment pricing
        if custom_input_cost is not None and custom_output_cost is not None:
            return {
                "input": custom_input_cost,
                "output": custom_output_cost,
            }, "deployment"

        # Priority 2 — LiteLLM automatic lookup
        litellm_result = get_pricing(model_key)
        if litellm_result:
            return {
                "input": litellm_result["input"],
                "output": litellm_result["output"],
            }, "litellm"

        # Priority 3 — Hardcoded defaults
        costs = cls.TOKEN_COSTS.get(model_key, cls.TOKEN_COSTS["gpt-4o"])
        return costs, "default"

    @classmethod
    def calculate_node_cost(
        cls,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
        model: Optional[str] = None,
        custom_input_cost: Optional[float] = None,
        custom_output_cost: Optional[float] = None,
    ) -> Optional[float]:
        """
        Calculate cost for a single node based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name for model-specific pricing (defaults to gpt-4o)
            custom_input_cost: Custom USD cost per 1M input tokens (overrides lookup)
            custom_output_cost: Custom USD cost per 1M output tokens (overrides lookup)

        Returns:
            Total cost in the currency of the pricing table, or None if no tokens
        """
        if not input_tokens and not output_tokens:
            return None

        input_tokens = input_tokens or 0
        output_tokens = output_tokens or 0

        if input_tokens == 0 and output_tokens == 0:
            return None

        model_key = model.lower() if model else "gpt-4o"
        costs, _source = cls._resolve_pricing(
            model_key, custom_input_cost, custom_output_cost
        )

        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return input_cost + output_cost

    @classmethod
    def calculate_total_cost(cls, nodes: list) -> float:
        """
        Calculate total cost across multiple nodes.

        Args:
            nodes: List of node dictionaries with token and cost information

        Returns:
            Total cost across all nodes
        """
        total_cost = 0.0

        for node in nodes:
            # Use existing cost if available
            if isinstance(node, dict):
                node_cost = node.get("total_cost")
                if node_cost:
                    total_cost += node_cost
                    continue

                # Fallback to token-based calculation
                input_tokens = node.get("input_tokens")
                output_tokens = node.get("output_tokens")
                model = None
                if node.get("llm_metadata"):
                    model = node["llm_metadata"].get("model")
            else:
                # SQLAlchemy model
                node_cost = getattr(node, "total_cost", None)
                if node_cost:
                    total_cost += node_cost
                    continue

                input_tokens = getattr(node, "input_tokens", None)
                output_tokens = getattr(node, "output_tokens", None)
                model = None
                llm_metadata = getattr(node, "llm_metadata", None)
                if llm_metadata:
                    model = llm_metadata.get("model")

            calculated_cost = cls.calculate_node_cost(
                input_tokens, output_tokens, model
            )
            if calculated_cost:
                total_cost += calculated_cost

        return total_cost

    @classmethod
    def enrich_node_with_cost(cls, node: Dict) -> Dict:
        """
        Add calculated cost to node if not present.

        Args:
            node: Node dictionary

        Returns:
            Node dictionary with cost metadata added
        """
        if node.get("total_cost"):
            return node

        if not node.get("total_tokens"):
            return node

        input_tokens = node.get("input_tokens")
        output_tokens = node.get("output_tokens")
        model = None
        custom_input_cost = None
        custom_output_cost = None
        if node.get("llm_metadata"):
            model = node["llm_metadata"].get("model")
            custom_input_cost = node["llm_metadata"].get("custom_input_cost")
            custom_output_cost = node["llm_metadata"].get("custom_output_cost")

        model_key = model.lower() if model else "gpt-4o"
        _costs, pricing_source = cls._resolve_pricing(
            model_key, custom_input_cost, custom_output_cost
        )

        calculated_cost = cls.calculate_node_cost(
            input_tokens, output_tokens, model, custom_input_cost, custom_output_cost
        )
        if calculated_cost:
            if "metadata" not in node:
                node["metadata"] = {}
            node["metadata"]["cost"] = calculated_cost
            node["metadata"]["cost_estimated"] = True
            node["metadata"]["pricing_source"] = pricing_source

            # Also propagate into llm metadata if present
            if node.get("llm_metadata") is not None:
                node["llm_metadata"]["pricing_source"] = pricing_source
                node["llm_metadata"]["cost_estimated"] = True

        return node


def build_llm_metadata(
    node: Any,
    token_counts: Optional[Dict[str, int]],
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build LLM metadata with cost calculation for any agent node.

    Extracts model info from node.config.llm_config and calculates costs
    using deployment pricing or hardcoded rates.

    Args:
        node: The agent node (has config.llm_config with model info)
        token_counts: Token usage counts from execution
        start_time: Execution start time as unix timestamp (time.time())
        end_time: Execution end time as unix timestamp (time.time())

    Returns:
        LLM metadata dict with model info and cost fields, or None if no tokens
    """
    if not token_counts:
        return None

    input_tokens = token_counts.get("input_tokens", 0)
    output_tokens = token_counts.get("output_tokens", 0)
    if not input_tokens and not output_tokens:
        return None

    model_name = None
    custom_input_cost = None
    custom_output_cost = None

    agent_config = getattr(node, "agent_config", None) or getattr(node, "config", None)
    llm_config = getattr(agent_config, "llm_config", None)

    if llm_config and getattr(llm_config, "model_deployment_id", None):
        try:
            from backend.services.model_deployment import ModelDeploymentService

            service = ModelDeploymentService()
            deployment = service.get_deployment(llm_config.model_deployment_id)
            if deployment:
                custom_input_cost = deployment.get("input_cost_per_million")
                custom_output_cost = deployment.get("output_cost_per_million")
                model_name = deployment.get("model_name")
        except Exception as e:
            logger.debug(f"Could not look up deployment pricing: {e}")

    if not model_name and llm_config:
        model_name = getattr(llm_config, "model_name", None)

    total_cost = CostCalculator.calculate_node_cost(
        input_tokens,
        output_tokens,
        model_name,
        custom_input_cost=custom_input_cost,
        custom_output_cost=custom_output_cost,
    )

    if total_cost is None:
        return None

    model_key = model_name.lower() if model_name else "gpt-4o"
    rates, _pricing_source = CostCalculator._resolve_pricing(
        model_key, custom_input_cost, custom_output_cost
    )

    prompt_cost = (input_tokens / 1_000_000) * rates["input"]
    completion_cost = (output_tokens / 1_000_000) * rates["output"]

    # Performance metrics from timing data
    total_latency_ms = None
    tokens_per_second = None
    if start_time and end_time and end_time > start_time:
        total_latency_ms = (end_time - start_time) * 1000
        if output_tokens and total_latency_ms > 0:
            tokens_per_second = output_tokens / (total_latency_ms / 1000)

    # Extract LLM response metadata (finish_reason, model_version, etc.)
    response_meta = token_counts.get("metadata", {}) if token_counts else {}

    metadata: Dict[str, Any] = {
        "model": model_name,
        "provider": getattr(llm_config, "provider", None) if llm_config else None,
        "deployment_name": getattr(llm_config, "deployment_name", None)
        if llm_config
        else None,
        "temperature": getattr(llm_config, "temperature", None) if llm_config else None,
        "max_tokens": getattr(llm_config, "max_tokens", None) if llm_config else None,
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost,
        "total_cost": total_cost,
        "tokens_per_second": tokens_per_second,
        "total_latency_ms": total_latency_ms,
        "request_start": start_time,
        "request_end": end_time,
    }

    # Merge in response metadata fields if available
    if response_meta:
        if response_meta.get("finish_reason"):
            metadata["finish_reason"] = response_meta["finish_reason"]
        if response_meta.get("model_version"):
            metadata["model_version"] = response_meta["model_version"]
        if response_meta.get("system_fingerprint"):
            metadata["system_fingerprint"] = response_meta["system_fingerprint"]
        if response_meta.get("time_to_first_token") is not None:
            metadata["time_to_first_token"] = response_meta["time_to_first_token"]

    return metadata
