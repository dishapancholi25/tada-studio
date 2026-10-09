"""
Application metrics collector.

This module provides application-specific metrics collection for agent
executions, tool usage, graph compilation, and cache statistics.
"""

from typing import Optional

from ...config import get_logger
from .base import MetricCollectorInterface


logger = get_logger("metrics.application")


class ApplicationMetricsCollector(MetricCollectorInterface):
    """
    Collects application-specific metrics.

    Provides methods for recording metrics about agent executions,
    tool usage, graph compilation, and cache performance.
    """

    def collect(self) -> None:
        """
        Collect application metrics.

        Note: Application metrics are primarily event-driven and recorded
        via the record_* methods below, rather than periodic collection.
        This method is provided for interface compliance but does nothing.
        """
        pass

    def record_execution(
        self,
        graph_name: str,
        agent_name: str,
        duration_ms: float,
        success: bool,
        token_count: Optional[int] = None,
    ) -> None:
        """
        Record agent execution metrics.

        Args:
            graph_name: Name of the graph
            agent_name: Name of the agent
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            token_count: Optional token usage count
        """
        try:
            labels = {
                "graph": graph_name,
                "agent": agent_name,
                "success": str(success).lower(),
            }

            self.collector.histogram("agent.execution.duration_ms", duration_ms, labels)
            self.collector.increment("agent.execution.count", labels=labels)

            if not success:
                self.collector.increment("agent.execution.errors", labels=labels)

            if token_count:
                self.collector.histogram("agent.tokens.used", token_count, labels)

            logger.debug(
                f"[METRICS-APP] Recorded execution: {agent_name} "
                f"({duration_ms:.2f}ms, success={success})"
            )

        except Exception as e:
            logger.error(f"[METRICS-APP] Failed to record execution metrics: {e}")

    def record_tool_execution(
        self, tool_name: str, duration_ms: float, success: bool, cached: bool = False
    ) -> None:
        """
        Record tool execution metrics.

        Args:
            tool_name: Name of the tool
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            cached: Whether result was from cache
        """
        try:
            labels = {
                "tool": tool_name,
                "success": str(success).lower(),
                "cached": str(cached).lower(),
            }

            self.collector.histogram("tool.execution.duration_ms", duration_ms, labels)
            self.collector.increment("tool.execution.count", labels=labels)

            if cached:
                self.collector.increment("tool.cache.hits", labels={"tool": tool_name})
            else:
                self.collector.increment(
                    "tool.cache.misses", labels={"tool": tool_name}
                )

            logger.debug(
                f"[METRICS-APP] Recorded tool execution: {tool_name} "
                f"({duration_ms:.2f}ms, cached={cached})"
            )

        except Exception as e:
            logger.error(f"[METRICS-APP] Failed to record tool metrics: {e}")

    def record_compilation(
        self, graph_name: str, agent_count: int, duration_ms: float, success: bool
    ) -> None:
        """
        Record graph compilation metrics.

        Args:
            graph_name: Name of the graph
            agent_count: Number of agents in graph
            duration_ms: Compilation duration in milliseconds
            success: Whether compilation succeeded
        """
        try:
            labels = {"graph": graph_name, "success": str(success).lower()}

            self.collector.histogram(
                "graph.compilation.duration_ms", duration_ms, labels
            )
            self.collector.gauge("graph.compilation.agent_count", agent_count, labels)
            self.collector.increment("graph.compilation.count", labels=labels)

            logger.debug(
                f"[METRICS-APP] Recorded compilation: {graph_name} "
                f"({agent_count} agents, {duration_ms:.2f}ms)"
            )

        except Exception as e:
            logger.error(f"[METRICS-APP] Failed to record compilation metrics: {e}")

    def record_cache_stats(
        self, cache_name: str, hits: int, misses: int, size: int, evictions: int
    ) -> None:
        """
        Record cache statistics.

        Args:
            cache_name: Name of the cache
            hits: Number of cache hits
            misses: Number of cache misses
            size: Current cache size
            evictions: Number of evictions
        """
        try:
            labels = {"cache": cache_name}

            self.collector.gauge("cache.hits", hits, labels)
            self.collector.gauge("cache.misses", misses, labels)
            self.collector.gauge("cache.size", size, labels)
            self.collector.gauge("cache.evictions", evictions, labels)

            # Calculate and record hit rate
            hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
            self.collector.gauge("cache.hit_rate", hit_rate, labels)

            logger.debug(
                f"[METRICS-APP] Recorded cache stats: {cache_name} "
                f"(hit_rate={hit_rate:.2%})"
            )

        except Exception as e:
            logger.error(f"[METRICS-APP] Failed to record cache stats: {e}")
