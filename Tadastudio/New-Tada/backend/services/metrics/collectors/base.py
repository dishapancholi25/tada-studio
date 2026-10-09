"""
Base collector interface for specialized metric collectors.

This module defines the protocol/interface for metric collectors that
gather specific types of metrics (system, application, etc.).
"""

from abc import ABC, abstractmethod


class MetricCollectorInterface(ABC):
    """
    Abstract base class for metric collectors.

    Collectors are responsible for gathering specific categories of metrics
    (e.g., system metrics, application metrics) and recording them using
    the core MetricCollector.
    """

    def __init__(self, collector):
        """
        Initialize collector.

        Args:
            collector: Core MetricCollector instance for recording metrics
        """
        self.collector = collector

    @abstractmethod
    def collect(self) -> None:
        """
        Collect and record metrics.

        This method should gather all relevant metrics for this collector's
        domain and record them using self.collector.
        """
        pass
