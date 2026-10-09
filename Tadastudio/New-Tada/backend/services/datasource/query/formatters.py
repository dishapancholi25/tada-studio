"""Query result formatting functionality."""

import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.services.datasource.config import LOG_PREFIX


logger = logging.getLogger(__name__)


class ResultFormatter:
    """Formats query results in different output formats."""

    def format_results(
        self,
        results: List[Dict[str, Any]],
        columns: List[str],
        format_type: str = "json",
        include_schema: bool = True,
        schema_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format query results in the specified format.

        Args:
            results: List of result rows as dictionaries
            columns: List of column names
            format_type: Output format (json, csv, markdown)
            include_schema: Whether to include schema information
            schema_info: Column schema information

        Returns:
            Formatted results dictionary
        """
        formatted_output = {
            "success": True,
            "row_count": len(results),
            "columns": columns,
            "format": format_type,
        }

        if include_schema and schema_info:
            formatted_output["schema"] = schema_info

        if format_type == "json":
            formatted_output["data"] = results
        elif format_type == "csv":
            formatted_output["data"] = self._format_as_csv(results, columns)
        elif format_type == "markdown":
            formatted_output["data"] = self._format_as_markdown(results, columns)
        else:
            formatted_output["data"] = results

        logger.debug(f"{LOG_PREFIX} Formatted {len(results)} rows as {format_type}")

        return formatted_output

    def _format_as_csv(self, results: List[Dict[str, Any]], columns: List[str]) -> str:
        """Format results as CSV."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    def _format_as_markdown(
        self, results: List[Dict[str, Any]], columns: List[str]
    ) -> str:
        """Format results as Markdown table."""
        lines = []

        # Header
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join(["-" * len(col) for col in columns]) + " |")

        # Data rows
        for row in results:
            row_values = [str(row.get(col, "NULL")) for col in columns]
            lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)

    def normalize_value(self, value: Any) -> Any:
        """Normalize a value for JSON serialization.

        Args:
            value: Value to normalize

        Returns:
            Normalized value
        """
        if isinstance(value, datetime):
            return value.isoformat()
        elif value is None:
            return None
        else:
            return str(value)
