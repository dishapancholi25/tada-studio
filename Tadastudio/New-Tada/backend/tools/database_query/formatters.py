"""
Database Query Tool - Result Formatters.

This module provides formatters for database query results in various formats
(JSON, CSV, Markdown).
"""

import json
import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)


def format_json_response(
    result: Dict[str, Any], max_rows: int, include_schema: bool = True
) -> str:
    """
    Format SELECT query results as a JSON string.

    LangChain tools must return a string, so the structured payload is
    serialized with ``json.dumps``. The output is valid JSON that the UI's
    JSON viewer (and downstream agents) can parse back into an object.

    Args:
        result: Query result dictionary from the executor. Expected keys:
            ``row_count``, ``columns``, ``data``, and optionally
            ``has_more_rows``, ``message``, ``schema``, ``execution_time_ms``.
        max_rows: Maximum number of rows configured (echoed as ``max_rows``
            when the result was truncated).
        include_schema: Whether to include schema information in the payload.

    Returns:
        JSON-encoded string of the structured result payload.
    """
    payload: Dict[str, Any] = {
        "row_count": result.get("row_count", 0),
        "columns": result.get("columns", []),
        "data": result.get("data", []),
    }

    if result.get("has_more_rows"):
        payload["has_more_rows"] = True
        payload["max_rows"] = max_rows

    if result.get("message"):
        payload["message"] = result["message"]

    if include_schema and result.get("schema"):
        payload["schema"] = result["schema"]

    if "execution_time_ms" in result:
        payload["execution_time_ms"] = result["execution_time_ms"]

    return json.dumps(payload, default=str, ensure_ascii=False, indent=2)


def format_csv_response(result: Dict[str, Any]) -> str:
    """
    Format query results as CSV.

    Args:
        result: Query result dictionary

    Returns:
        Formatted CSV string
    """
    row_count = result.get("row_count", 0)
    data = result.get("data", "")
    return f"CSV Data ({row_count} rows):\n{data}"


def format_markdown_response(result: Dict[str, Any], max_rows: int) -> str:
    """
    Format query results as Markdown table.

    Args:
        result: Query result dictionary
        max_rows: Maximum number of rows configured

    Returns:
        Formatted Markdown string
    """
    row_count = result.get("row_count", 0)
    output = f"Query returned {row_count} rows\n\n"

    if result.get("has_more_rows"):
        output += f"*Showing first {max_rows} rows*\n\n"

    output += result.get("data", "")
    return output


def format_operation_response(result: Dict[str, Any]) -> str:
    """
    Format INSERT, UPDATE, DELETE operation results.

    Args:
        result: Query result dictionary

    Returns:
        Formatted operation result string
    """
    operation = result.get("operation", "Operation")
    message = result.get("message", "")
    
    # If RETURNING clause results are present, include them in the response
    if "data" in result and result.get("data"):
        # Build JSON response with data included
        response_dict = {
            "operation": operation,
            "rows_affected": result.get("rows_affected", 0),
            "message": message,
            "data": result["data"],
            "columns": result.get("columns", []),
        }
        if "execution_time_ms" in result:
            response_dict["execution_time_ms"] = result["execution_time_ms"]
        return json.dumps(response_dict, default=str, ensure_ascii=False, indent=2)
    
    # Standard response without RETURNING data
    return f"{operation} completed successfully. {message}"


def format_error_response(result: Dict[str, Any]) -> str:
    """
    Format error response from query execution.

    Args:
        result: Query result dictionary with error information

    Returns:
        Formatted error message
    """
    error = result.get("error", "Unknown error")
    error_type = result.get("error_type")

    if error_type == "validation":
        return f"Validation error: {error}"
    elif error_type == "connection":
        return f"Connection error: {error}"
    else:
        return f"Query failed: {error}"


def get_formatter(return_format: str):
    """
    Get the appropriate formatter function for the given format.

    Args:
        return_format: Format type (json, csv, markdown)

    Returns:
        Formatter function

    Raises:
        ValueError: If format is not supported
    """
    formatters = {
        "json": format_json_response,
        "csv": format_csv_response,
        "markdown": format_markdown_response,
    }

    if return_format not in formatters:
        raise ValueError(
            f"Unsupported format: {return_format}. "
            f"Must be one of: {', '.join(formatters.keys())}"
        )

    return formatters[return_format]


def format_query_result(
    result: Dict[str, Any],
    return_format: str,
    max_rows: int,
    include_schema: bool = True,
) -> str:
    """
    Format query result based on the specified format.

    Args:
        result: Query result dictionary
        return_format: Format type (json, csv, markdown)
        max_rows: Maximum number of rows configured
        include_schema: Whether to include schema information

    Returns:
        Formatted result string
    """
    # Handle errors
    if not result.get("success"):
        return format_error_response(result)

    # Handle operation results (INSERT, UPDATE, DELETE)
    if "operation" in result:
        return format_operation_response(result)

    # Handle SELECT results
    if return_format == "json":
        return format_json_response(result, max_rows, include_schema)
    elif return_format == "csv":
        return format_csv_response(result)
    elif return_format == "markdown":
        return format_markdown_response(result, max_rows)
    else:
        # Fallback for unknown formats
        row_count = result.get("row_count", 0)
        return f"Query successful. {row_count} rows returned."
