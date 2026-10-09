"""
Caching mechanism for compiled LangGraph StateGraphs.

This module provides a cache for storing and retrieving compiled graphs
to avoid redundant compilation of the same graph definitions.
"""

from typing import Dict, Optional

from langgraph.graph import StateGraph
from backend.models.workflow import GraphData
from backend.services.config import get_logger


graph_cache_logger = get_logger("graph.cache")


class GraphCache:
    """
    Cache for compiled LangGraph StateGraphs.

    This cache stores compiled graphs keyed by graph ID and version,
    reducing compilation overhead for frequently executed graphs.
    """

    def __init__(self):
        """Initialize an empty graph cache."""
        self._cache: Dict[str, StateGraph] = {}

    def get_cache_key(self, graph: GraphData) -> str:
        """
        Generate a cache key for a graph.

        Args:
            graph: The graph definition to generate a key for

        Returns:
            A unique cache key string
        """
        version = getattr(graph, "version", "v1")
        return f"graph_{graph.id}_{version}"

    def get(self, graph: GraphData) -> Optional[StateGraph]:
        """
        Retrieve a cached compiled graph if it exists.

        Args:
            graph: The graph definition to look up

        Returns:
            The cached compiled StateGraph, or None if not found
        """
        cache_key = self.get_cache_key(graph)
        compiled_graph = self._cache.get(cache_key)

        if compiled_graph:
            graph_cache_logger.debug(
                f"Cache hit for graph '{graph.name}' (key: {cache_key})"
            )
        else:
            graph_cache_logger.debug(
                f"Cache miss for graph '{graph.name}' (key: {cache_key})"
            )

        return compiled_graph

    def put(self, graph: GraphData, compiled_graph: StateGraph) -> None:
        """
        Store a compiled graph in the cache.

        Args:
            graph: The graph definition
            compiled_graph: The compiled StateGraph to cache
        """
        cache_key = self.get_cache_key(graph)
        self._cache[cache_key] = compiled_graph
        graph_cache_logger.info(
            f"Cached compiled graph for '{graph.name}' (key: {cache_key})"
        )

    def clear(self) -> None:
        """Clear all cached compiled graphs."""
        count = len(self._cache)
        self._cache.clear()
        graph_cache_logger.info(f"Cleared {count} cached graphs")

    def size(self) -> int:
        """
        Get the number of cached graphs.

        Returns:
            The number of items in the cache
        """
        return len(self._cache)

    def has(self, graph: GraphData) -> bool:
        """
        Check if a graph is cached.

        Args:
            graph: The graph definition to check

        Returns:
            True if the graph is cached, False otherwise
        """
        cache_key = self.get_cache_key(graph)
        return cache_key in self._cache

    def invalidate(self, graph: GraphData) -> bool:
        """
        Invalidate (remove) a specific graph from the cache.

        Args:
            graph: The graph definition to invalidate

        Returns:
            True if graph was in cache and removed, False otherwise
        """
        cache_key = self.get_cache_key(graph)
        if cache_key in self._cache:
            del self._cache[cache_key]
            graph_cache_logger.info(
                f"Invalidated cache for graph '{graph.name}' (key: {cache_key})"
            )
            return True
        return False
