"""
Caching mechanism for compiled LangGraph subgraphs.

This module provides a cache for storing and retrieving compiled subgraphs
to avoid redundant compilation of the same subgraph configurations.
"""

import hashlib
import json
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph
from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger


cache_logger = get_logger("subgraph.cache")


def _get_config_hash(node: EnhancedNodeData) -> str:
    """Generate a hash of the node's configuration for cache invalidation.

    This ensures the cache is invalidated when the node config changes,
    particularly for fields like review_config.
    """
    config_data: Dict[str, Any] = {}

    if node.agent_config:
        # Include key config fields that affect execution behavior
        config_data["agent_config"] = {
            "system_prompt": getattr(node.agent_config, "system_prompt", ""),
            "is_orchestrator": getattr(node.agent_config, "is_orchestrator", False),
            "delegated_agents": getattr(node.agent_config, "delegated_agents", []),
        }
        # Include review_config if present (critical for review behavior)
        review_config = getattr(node.agent_config, "review_config", None)
        if review_config:
            if hasattr(review_config, "__dict__"):
                config_data["review_config"] = review_config.__dict__
            elif isinstance(review_config, dict):
                config_data["review_config"] = review_config

    try:
        config_str = json.dumps(config_data, sort_keys=True, default=str)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    except Exception:
        return "no_hash"


class SubgraphCache:
    """
    Cache for compiled LangGraph subgraphs.

    This cache stores compiled subgraphs keyed by node ID, version, and config hash,
    reducing compilation overhead for frequently used subgraphs while ensuring
    cache invalidation when node configuration changes.
    """

    def __init__(self):
        """Initialize an empty subgraph cache."""
        self._cache: Dict[str, StateGraph] = {}

    def get_cache_key(self, node: EnhancedNodeData, prefix: str = "") -> str:
        """
        Generate a cache key for a node.

        Args:
            node: The node to generate a key for
            prefix: Optional prefix for the cache key (e.g., "agent_", "workflow_")

        Returns:
            A unique cache key string including config hash for invalidation
        """
        version = getattr(node, "version", "v1")
        config_hash = _get_config_hash(node)
        return f"{prefix}{node.uniq_id}_{version}_{config_hash}"

    def get(self, node: EnhancedNodeData, prefix: str = "") -> Optional[StateGraph]:
        """
        Retrieve a cached subgraph if it exists.

        Args:
            node: The node to look up
            prefix: Optional prefix for the cache key

        Returns:
            The cached StateGraph, or None if not found
        """
        cache_key = self.get_cache_key(node, prefix)
        subgraph = self._cache.get(cache_key)

        if subgraph:
            cache_logger.debug(f"Cache hit for {node.name} (key: {cache_key})")
        else:
            cache_logger.debug(f"Cache miss for {node.name} (key: {cache_key})")

        return subgraph

    def put(
        self, node: EnhancedNodeData, subgraph: StateGraph, prefix: str = ""
    ) -> None:
        """
        Store a compiled subgraph in the cache.

        Args:
            node: The node the subgraph was created for
            subgraph: The compiled StateGraph to cache
            prefix: Optional prefix for the cache key
        """
        cache_key = self.get_cache_key(node, prefix)
        self._cache[cache_key] = subgraph
        cache_logger.info(f"Cached subgraph for {node.name} (key: {cache_key})")

    def clear(self) -> None:
        """Clear all cached subgraphs."""
        count = len(self._cache)
        self._cache.clear()
        cache_logger.info(f"Cleared {count} cached subgraphs")

    def size(self) -> int:
        """
        Get the number of cached subgraphs.

        Returns:
            The number of items in the cache
        """
        return len(self._cache)

    def has(self, node: EnhancedNodeData, prefix: str = "") -> bool:
        """
        Check if a subgraph is cached.

        Args:
            node: The node to check
            prefix: Optional prefix for the cache key

        Returns:
            True if the subgraph is cached, False otherwise
        """
        cache_key = self.get_cache_key(node, prefix)
        return cache_key in self._cache
