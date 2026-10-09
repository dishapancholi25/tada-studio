"""LiteLLM-based model pricing service.

Fetches and caches model pricing data from the LiteLLM project's published
JSON file. Provides lookup with provider-prefix normalization and automatic
conversion from per-token to per-1M-token pricing.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

LITELLM_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/refs/heads/main/"
    "litellm/model_prices_and_context_window_backup.json"
)

REFRESH_INTERVAL_HOURS = int(os.getenv("LITELLM_PRICING_REFRESH_HOURS", "24"))

# Known provider prefixes that may appear before model names
_PROVIDER_PREFIXES = (
    "azure/",
    "bedrock/",
    "anthropic/",
    "anthropic.",
    "openai/",
    "google/",
    "vertex_ai/",
    "cohere/",
    "replicate/",
    "huggingface/",
    "together_ai/",
    "sagemaker/",
    "fireworks_ai/",
    "deepinfra/",
    "anyscale/",
    "mistral/",
    "groq/",
    "cerebras/",
    "ai21/",
    "voyage/",
)

_BACKUP_FILE = Path(__file__).parent / "litellm_model_prices_backup.json"


class LiteLLMPricingService:
    """Service that loads, caches, and looks up LiteLLM model pricing."""

    def __init__(self) -> None:
        self._pricing_cache: Dict[str, dict] = {}
        self._last_refreshed: Optional[datetime] = None
        self._load_bundled_snapshot()

    # ------------------------------------------------------------------
    # Startup – bundled fallback
    # ------------------------------------------------------------------

    def _load_bundled_snapshot(self) -> None:
        """Load the bundled JSON snapshot so the cache is never empty."""
        try:
            with open(_BACKUP_FILE, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._populate_cache(raw)
            self._last_refreshed = datetime.now(timezone.utc)
            logger.info(
                "LiteLLM pricing: loaded %d models from bundled snapshot",
                len(self._pricing_cache),
            )
        except Exception as exc:
            logger.warning("LiteLLM pricing: failed to load bundled snapshot: %s", exc)

    # ------------------------------------------------------------------
    # Fetch & refresh
    # ------------------------------------------------------------------

    async def refresh_pricing_data(self) -> None:
        """Fetch the latest pricing JSON from GitHub and update the cache."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(LITELLM_PRICING_URL)
                resp.raise_for_status()
                raw = resp.json()
            self._populate_cache(raw)
            self._last_refreshed = datetime.now(timezone.utc)
            logger.info(
                "LiteLLM pricing: refreshed %d models from remote",
                len(self._pricing_cache),
            )
        except Exception as exc:
            logger.warning(
                "LiteLLM pricing: remote refresh failed, keeping existing cache: %s",
                exc,
            )

    def refresh_pricing_data_sync(self) -> None:
        """Synchronous wrapper for scheduler use."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.refresh_pricing_data())
            else:
                loop.run_until_complete(self.refresh_pricing_data())
        except RuntimeError:
            asyncio.run(self.refresh_pricing_data())

    # ------------------------------------------------------------------
    # Cache population
    # ------------------------------------------------------------------

    def _populate_cache(self, raw: dict) -> None:
        """Parse the raw LiteLLM JSON into the internal cache."""
        cache: Dict[str, dict] = {}
        for model_name, info in raw.items():
            if not isinstance(info, dict):
                continue
            if (
                "input_cost_per_token" not in info
                and "output_cost_per_token" not in info
            ):
                continue
            cache[model_name.lower()] = info
        self._pricing_cache = cache

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_pricing(self, model_name: str) -> Optional[dict]:
        """Look up pricing for *model_name*.

        Returns a dict with keys ``input``, ``output`` (per 1M tokens),
        ``source_model_name``, and ``litellm_provider``; or ``None``.
        """
        if not model_name:
            return None

        key = model_name.lower()

        # 1. Exact match
        entry = self._pricing_cache.get(key)
        if entry:
            return self._to_result(key, entry)

        # 2. Strip known provider prefixes and retry exact match
        stripped = self._strip_prefix(key)
        if stripped != key:
            entry = self._pricing_cache.get(stripped)
            if entry:
                return self._to_result(stripped, entry)

        # 3. Substring match – find any cache key that contains the stripped name
        #    Prefer the shortest matching key to avoid overly broad matches.
        candidates = [k for k in self._pricing_cache if stripped in k]
        if candidates:
            best = min(candidates, key=len)
            return self._to_result(best, self._pricing_cache[best])

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_prefix(name: str) -> str:
        for prefix in _PROVIDER_PREFIXES:
            if name.startswith(prefix):
                return name[len(prefix) :]
        return name

    @staticmethod
    def _to_result(cache_key: str, entry: dict) -> dict:
        input_cpt = entry.get("input_cost_per_token", 0) or 0
        output_cpt = entry.get("output_cost_per_token", 0) or 0
        return {
            "input": float(input_cpt) * 1_000_000,
            "output": float(output_cpt) * 1_000_000,
            "source_model_name": cache_key,
            "litellm_provider": entry.get("litellm_provider"),
        }

    def get_model_limits(self, model_name: str) -> Optional[dict]:
        """Look up model parameter limits for *model_name*.

        Returns a dict with keys ``max_output_tokens``, ``max_input_tokens``,
        ``supports_reasoning``, and ``source_model_name``; or ``None``.
        """
        if not model_name:
            return None

        key = model_name.lower()

        # 1. Exact match
        entry = self._pricing_cache.get(key)
        if entry:
            return self._to_limits(key, entry)

        # 2. Strip provider prefix and retry
        stripped = self._strip_prefix(key)
        if stripped != key:
            entry = self._pricing_cache.get(stripped)
            if entry:
                return self._to_limits(stripped, entry)

        # 3. Substring match (shortest key wins)
        candidates = [k for k in self._pricing_cache if stripped in k]
        if candidates:
            best = min(candidates, key=len)
            return self._to_limits(best, self._pricing_cache[best])

        return None

    @staticmethod
    def _to_limits(cache_key: str, entry: dict) -> dict:
        return {
            "max_output_tokens": entry.get("max_output_tokens")
            or entry.get("max_tokens"),
            "max_input_tokens": entry.get("max_input_tokens"),
            "supports_reasoning": entry.get("supports_reasoning", False),
            "source_model_name": cache_key,
        }

    @property
    def last_refreshed(self) -> Optional[datetime]:
        return self._last_refreshed

    @property
    def cache_size(self) -> int:
        return len(self._pricing_cache)


# ------------------------------------------------------------------
# Module-level singleton & convenience function
# ------------------------------------------------------------------

litellm_pricing_service = LiteLLMPricingService()


def get_pricing(model_name: str) -> Optional[dict]:
    """Convenience wrapper around the singleton's lookup."""
    return litellm_pricing_service.get_pricing(model_name)


def get_model_limits(model_name: str) -> Optional[dict]:
    """Convenience wrapper around the singleton's model limits lookup."""
    return litellm_pricing_service.get_model_limits(model_name)
