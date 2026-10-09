"""
StatsD format exporter.

This module exports metrics in StatsD wire protocol format for sending
to StatsD-compatible metric aggregation services.
"""

from typing import List

from ..models import ExportError
from .base import MetricsExporter


class StatsDExporter(MetricsExporter):
    """
    Export metrics in StatsD format.

    StatsD uses a simple text protocol with format: metric_name:value|type
    where type is c (counter), g (gauge), or ms (timing/histogram).
    """

    def export(self) -> List[str]:
        """
        Export metrics as StatsD commands.

        Returns:
            List of StatsD command strings

        Raises:
            ExportError: If export fails
        """
        try:
            commands: List[str] = []
            metrics = self._get_metrics_data()

            for name, data in metrics.items():
                value = data.get("value", 0)
                metric_type = data.get("type", "gauge")

                # Map metric type to StatsD type
                if metric_type == "counter":
                    commands.append(f"{name}:{value}|c")
                elif metric_type == "gauge":
                    commands.append(f"{name}:{value}|g")
                elif metric_type in ["histogram", "summary"]:
                    commands.append(f"{name}:{value}|ms")

            return commands

        except Exception as e:
            raise ExportError(f"Failed to export StatsD metrics: {e}") from e
