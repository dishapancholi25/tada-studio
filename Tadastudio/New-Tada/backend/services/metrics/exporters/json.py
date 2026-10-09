"""
JSON format exporter.

This module exports metrics as JSON for easy consumption by dashboards
and other tools.
"""

import json

from ..models import ExportError
from .base import MetricsExporter


class JSONExporter(MetricsExporter):
    """
    Export metrics in JSON format.

    Provides a simple JSON representation of all metrics with their
    current values, timestamps, and metadata.
    """

    def export(self) -> str:
        """
        Export metrics as JSON string.

        Returns:
            JSON-formatted metrics

        Raises:
            ExportError: If export fails
        """
        try:
            metrics = self._get_metrics_data()
            return json.dumps(metrics, indent=2)
        except Exception as e:
            raise ExportError(f"Failed to export JSON metrics: {e}") from e
