"""Statistics calculation service for trace executions.

Aggregates metrics across nodes and provides detailed breakdowns.
"""

from typing import Any, Dict, List, Optional

from ...services.config import get_logger
from .cost_calculator import CostCalculator


logger = get_logger("trace_statistics")


class StatisticsService:
    """Calculate aggregated statistics for trace executions."""

    @classmethod
    def calculate_execution_stats(cls, nodes: List[Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for an execution.

        Args:
            nodes: List of NodeExecution objects or dictionaries

        Returns:
            Dictionary containing aggregated statistics
        """
        if not nodes:
            return cls._empty_stats()

        stats = {
            "totalNodes": len(nodes),
            "completedNodes": cls._count_by_status(nodes, "completed"),
            "failedNodes": cls._count_by_status(nodes, "failed"),
            "runningNodes": cls._count_by_status(nodes, "running"),
            "totalTokens": cls._sum_tokens(nodes),
            "totalCost": cls._calculate_total_cost(nodes),
            "averageDuration": cls._calculate_average_duration(nodes),
            "tokensByType": cls._group_tokens_by_type(nodes),
            "costByType": cls._group_cost_by_type(nodes),
            "costByModel": cls._group_cost_by_model(nodes),
            "performanceMetrics": cls._calculate_performance_metrics(nodes),
        }

        return stats

    @classmethod
    def _empty_stats(cls) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            "totalNodes": 0,
            "completedNodes": 0,
            "failedNodes": 0,
            "runningNodes": 0,
            "totalTokens": 0,
            "totalCost": 0,
            "averageDuration": 0,
            "tokensByType": {},
            "costByType": {},
            "costByModel": {},
            "performanceMetrics": {
                "averageTokensPerSecond": None,
                "averageTimeToFirstToken": None,
            },
        }

    @classmethod
    def _count_by_status(cls, nodes: List[Any], status: str) -> int:
        """
        Count nodes with specific status.

        Args:
            nodes: List of nodes
            status: Status to count

        Returns:
            Number of nodes with given status
        """
        count = 0
        for node in nodes:
            node_status = cls._get_attribute(node, "status")
            if node_status == status:
                count += 1
        return count

    @classmethod
    def _sum_tokens(cls, nodes: List[Any]) -> int:
        """
        Sum total tokens across all nodes.

        Args:
            nodes: List of nodes

        Returns:
            Total token count
        """
        total = 0
        for node in nodes:
            tokens = cls._get_attribute(node, "total_tokens")
            if tokens is not None:
                total += tokens
        return total

    @classmethod
    def _calculate_total_cost(cls, nodes: List[Any]) -> float:
        """
        Calculate total cost across all nodes.

        Args:
            nodes: List of nodes

        Returns:
            Total cost
        """
        return CostCalculator.calculate_total_cost(nodes)

    @classmethod
    def _calculate_average_duration(cls, nodes: List[Any]) -> float:
        """
        Calculate average duration across all nodes.

        Args:
            nodes: List of nodes

        Returns:
            Average duration in seconds
        """
        if not nodes:
            return 0

        total_duration = 0
        for node in nodes:
            duration = cls._get_attribute(node, "duration_seconds")
            if duration:
                total_duration += duration

        return total_duration / len(nodes)

    @classmethod
    def _group_tokens_by_type(cls, nodes: List[Any]) -> Dict[str, int]:
        """
        Group token counts by node type.

        Args:
            nodes: List of nodes

        Returns:
            Dictionary mapping node types to token counts
        """
        tokens_by_type = {}
        for node in nodes:
            node_type = cls._get_attribute(node, "node_type")
            tokens = cls._get_attribute(node, "total_tokens")

            if tokens and node_type:
                tokens_by_type[node_type] = tokens_by_type.get(node_type, 0) + tokens

        return tokens_by_type

    @classmethod
    def _group_cost_by_type(cls, nodes: List[Any]) -> Dict[str, float]:
        """
        Group costs by node type.

        Args:
            nodes: List of nodes

        Returns:
            Dictionary mapping node types to costs
        """
        cost_by_type = {}

        for node in nodes:
            node_type = cls._get_attribute(node, "node_type")
            if not node_type:
                continue

            # Get existing cost or calculate from tokens
            node_cost = cls._get_attribute(node, "total_cost")

            if not node_cost:
                input_tokens = cls._get_attribute(node, "input_tokens")
                output_tokens = cls._get_attribute(node, "output_tokens")
                llm_metadata = cls._get_attribute(node, "llm_metadata")
                model = llm_metadata.get("model") if llm_metadata else None

                node_cost = CostCalculator.calculate_node_cost(
                    input_tokens, output_tokens, model
                )

            if node_cost:
                cost_by_type[node_type] = cost_by_type.get(node_type, 0) + node_cost

        return cost_by_type

    @classmethod
    def _group_cost_by_model(cls, nodes: List[Any]) -> Dict[str, float]:
        """
        Group costs by LLM model.

        Args:
            nodes: List of nodes

        Returns:
            Dictionary mapping model names to costs
        """
        cost_by_model = {}

        for node in nodes:
            llm_metadata = cls._get_attribute(node, "llm_metadata")
            if not llm_metadata:
                continue

            model = llm_metadata.get("model", "unknown")

            # Get existing cost or calculate from tokens
            node_cost = cls._get_attribute(node, "total_cost")

            if not node_cost:
                input_tokens = cls._get_attribute(node, "input_tokens")
                output_tokens = cls._get_attribute(node, "output_tokens")

                node_cost = CostCalculator.calculate_node_cost(
                    input_tokens, output_tokens, model
                )

            if node_cost:
                cost_by_model[model] = cost_by_model.get(model, 0) + node_cost

        return cost_by_model

    @classmethod
    def _calculate_performance_metrics(
        cls, nodes: List[Any]
    ) -> Dict[str, Optional[float]]:
        """
        Calculate performance metrics (tokens per second, time to first token).

        Args:
            nodes: List of nodes

        Returns:
            Dictionary with performance metrics
        """
        tps_values = []
        ttft_values = []

        for node in nodes:
            tps = cls._get_attribute(node, "tokens_per_second")
            if tps:
                tps_values.append(tps)

            ttft = cls._get_attribute(node, "time_to_first_token")
            if ttft:
                ttft_values.append(ttft)

        avg_tps = sum(tps_values) / len(tps_values) if tps_values else None
        avg_ttft = sum(ttft_values) / len(ttft_values) if ttft_values else None

        return {
            "averageTokensPerSecond": avg_tps,
            "averageTimeToFirstToken": avg_ttft,
        }

    @classmethod
    def _get_attribute(cls, obj: Any, attr_name: str) -> Any:
        """
        Get attribute from object (dict or SQLAlchemy model).

        Args:
            obj: Object to get attribute from
            attr_name: Attribute name

        Returns:
            Attribute value or None
        """
        if isinstance(obj, dict):
            return obj.get(attr_name)
        return getattr(obj, attr_name, None)
