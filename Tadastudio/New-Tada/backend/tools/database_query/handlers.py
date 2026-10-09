"""
Database Query Tool - Query Execution Handlers.

This module provides high-level handlers for orchestrating database query
execution, validation, and formatting.
"""

import logging

from sqlalchemy.orm import Session

from ...services.streaming import streaming_emitter
from .execution import execute_query_with_async_handling
from .formatters import format_query_result


logger = logging.getLogger(__name__)

# Tool name constant for streaming events
DATABASE_QUERY_TOOL_NAME = "database_query"


def handle_query_execution(
    db: Session,
    query: str,
    connection_id: str,
    table_names: list,
    allowed_operations: list,
    max_rows: int,
    timeout_seconds: int,
    enable_read_only: bool,
    return_format: str,
    include_schema: bool,
    call_id: str = "",
) -> str:
    """
    Handle complete query execution flow.

    Orchestrates query execution, error handling, and result formatting.

    Args:
        db: Database session
        query: SQL query to execute
        connection_id: Database connection ID
        table_names: List of allowed table names
        allowed_operations: List of allowed SQL operations
        max_rows: Maximum rows to return
        timeout_seconds: Query timeout
        enable_read_only: Whether to force read-only mode
        return_format: Output format (json, csv, markdown)
        include_schema: Whether to include schema info
        call_id: Optional call ID for streaming progress events

    Returns:
        Formatted query result string

    Raises:
        Exception: Re-raises exceptions after logging
    """
    try:
        # Emit progress: executing query
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=DATABASE_QUERY_TOOL_NAME,
            message="Executing query...",
            progress=20,
        )

        # Execute the query with async handling
        result = execute_query_with_async_handling(
            db=db,
            connection_id=connection_id,
            query=query,
            table_names=table_names,
            allowed_operations=allowed_operations,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
            enable_read_only=enable_read_only,
            return_format=return_format,
            include_schema=include_schema,
        )

        # Emit progress: formatting results
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=DATABASE_QUERY_TOOL_NAME,
            message="Query complete, formatting results...",
            progress=70,
        )

        # Format the result based on the return format
        formatted_result = format_query_result(
            result=result,
            return_format=return_format,
            max_rows=max_rows,
            include_schema=include_schema,
        )

        return formatted_result

    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        logger.error(f"Error in database query handler: {str(e)}")
        return error_msg
