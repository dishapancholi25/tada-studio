"""
Prometheus format exporter.

This module exports metrics in Prometheus text exposition format.
"""

from typing import List

from ..config import PROMETHEUS_TIMESTAMP_MULTIPLIER
from ..models import ExportError
from ..utils import sanitize_metric_name_for_prometheus
from .base import MetricsExporter


class PrometheusExporter(MetricsExporter):
    """
    Export metrics in Prometheus format.

    Prometheus uses a simple text-based exposition format with type hints
    and optional labels. Metric names are sanitized to use underscores.
    """

    def export(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics as string

        Raises:
            ExportError: If export fails
        """
        try:
            lines: List[str] = []
            metrics = self._get_metrics_data()

            for name, data in metrics.items():
                # Convert metric name to Prometheus format
                prom_name = sanitize_metric_name_for_prometheus(name)

                # Add type annotation
                metric_type = data.get("type", "gauge")
                lines.append(f"# TYPE {prom_name} {metric_type}")

                # Format with labels if present
                labels = data.get("labels", {})
                value = data.get("value", 0)
                timestamp = int(
                    data.get("timestamp", 0) * PROMETHEUS_TIMESTAMP_MULTIPLIER
                )

                if labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                    lines.append(f"{prom_name}{{{label_str}}} {value} {timestamp}")
                else:
                    lines.append(f"{prom_name} {value} {timestamp}")

            return "\n".join(lines)

        except Exception as e:
            raise ExportError(f"Failed to export Prometheus metrics: {e}") from e
