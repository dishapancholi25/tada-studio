"""
Database Query Tool - Query Execution with Async Handling.

This module handles database query execution with proper async/sync event loop
handling for compatibility with LangGraph and other async frameworks.
"""

import asyncio
import concurrent.futures
import logging
from typing import Any, Coroutine, Dict

from sqlalchemy.orm import Session

from backend.services.database_query_service import database_query_service


logger = logging.getLogger(__name__)


def execute_in_new_loop(coro: Coroutine) -> Any:
    """
    Execute a coroutine in a new event loop.

    Args:
        coro: Coroutine to execute

    Returns:
        Result of the coroutine

    Raises:
        Exception: Any exception raised by the coroutine
    """
    return asyncio.run(coro)


def execute_in_executor(coro: Coroutine, timeout: int) -> Any:
    """
    Execute a coroutine in a thread pool executor.

    Used when there's already an event loop running.

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds

    Returns:
        Result of the coroutine

    Raises:
        TimeoutError: If execution exceeds timeout
        Exception: Any exception raised by the coroutine
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result(timeout=timeout)


async def execute_query_async(
    db: Session,
    connection_id: str,
    query: str,
    table_names: list,
    allowed_operations: list,
    max_rows: int,
    timeout_seconds: int,
    enable_read_only: bool,
    return_format: str,
    include_schema: bool,
) -> Dict[str, Any]:
    """
    Execute database query asynchronously.

    Args:
        db: Database session
        connection_id: Database connection ID
        query: SQL query to execute
        table_names: List of allowed table names
        allowed_operations: List of allowed SQL operations
        max_rows: Maximum rows to return
        timeout_seconds: Query timeout
        enable_read_only: Whether to force read-only mode
        return_format: Output format
        include_schema: Whether to include schema info

    Returns:
        Query execution result dictionary
    """
    # Use first table name for backward compatibility
    table_name = table_names[0] if table_names else ""

    result = await database_query_service.execute_query(
        db=db,
        connection_id=connection_id,
        query=query,
        table_name=table_name,
        table_names=table_names,
        allowed_operations=allowed_operations,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
        enable_read_only=enable_read_only,
        return_format=return_format,
        include_schema=include_schema,
    )
    return result


def execute_query_with_async_handling(
    db: Session,
    connection_id: str,
    query: str,
    table_names: list,
    allowed_operations: list,
    max_rows: int,
    timeout_seconds: int,
    enable_read_only: bool,
    return_format: str,
    include_schema: bool,
) -> Dict[str, Any]:
    """
    Execute database query with proper async/sync event loop handling.

    This function handles the complexity of executing async code from both
    sync and async contexts, including nested event loops.

    Args:
        db: Database session
        connection_id: Database connection ID
        query: SQL query to execute
        table_names: List of allowed table names
        allowed_operations: List of allowed SQL operations
        max_rows: Maximum rows to return
        timeout_seconds: Query timeout
        enable_read_only: Whether to force read-only mode
        return_format: Output format
        include_schema: Whether to include schema info

    Returns:
        Query execution result dictionary

    Raises:
        Exception: Any exception from query execution
    """
    # Create the coroutine
    coro = execute_query_async(
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

    try:
        # Try to get the existing event loop
        asyncio.get_running_loop()

        # If we're in an async context, create a task in a separate thread
        logger.debug("Executing query in executor (nested event loop)")
        result = execute_in_executor(coro, timeout_seconds)

    except RuntimeError:
        # No event loop running, we can safely use asyncio.run
        logger.debug("Executing query in new event loop")
        result = execute_in_new_loop(coro)

    return result
