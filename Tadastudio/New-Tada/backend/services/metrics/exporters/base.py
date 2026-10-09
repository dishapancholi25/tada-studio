"""
Base exporter interface for metrics export.

This module defines the protocol/interface that all metric exporters
must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MetricsExporter(ABC):
    """
    Abstract base class for metrics exporters.

    Exporters convert internal metric format to various external formats
    like Prometheus, JSON, StatsD, etc.
    """

    def __init__(self, get_all_metrics_func):
        """
        Initialize exporter.

        Args:
            get_all_metrics_func: Callable that returns all metrics
        """
        self.get_all_metrics = get_all_metrics_func

    @abstractmethod
    def export(self) -> Any:
        """
        Export metrics in the target format.

        Returns:
            Metrics in the exporter's format
        """
        pass

    def _get_metrics_data(self) -> Dict[str, Any]:
        """
        Get current metrics data.

        Returns:
            Dictionary of all metrics
        """
        return self.get_all_metrics()
