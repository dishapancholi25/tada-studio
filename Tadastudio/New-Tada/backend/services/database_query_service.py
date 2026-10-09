"""
Database Query Service - Wrapper for database query tool functionality.

This service provides a simplified interface for database query execution,
wrapping the datasource service for use by the database query tool.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.datasource import get_datasource_service
from backend.services.datasource.config import (
    DEFAULT_QUERY_ROW_LIMIT,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
)


logger = logging.getLogger(__name__)


class DatabaseQueryService:
    """Service for executing database queries via tools.

    This wraps the DataSourceService to provide a simpler interface
    for the database query tool system.
    """

    def __init__(self):
        """Initialize the database query service."""
        self.datasource_service = get_datasource_service()
        logger.debug("[DATABASE-QUERY-SERVICE] Service initialized")

    async def execute_query(
        self,
        db: Session,
        connection_id: str,
        query: str,
        table_name: str = "",
        table_names: Optional[List[str]] = None,
        allowed_operations: Optional[List[str]] = None,
        max_rows: int = DEFAULT_QUERY_ROW_LIMIT,
        timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS,
        enable_read_only: bool = False,
        return_format: str = "json",
        include_schema: bool = True,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a database query with safety measures.

        Args:
            db: Database session
            connection_id: ID of the datasource connection
            query: SQL query to execute
            table_name: Legacy single table name (for backward compatibility)
            table_names: List of allowed table names
            allowed_operations: List of allowed SQL operations (SELECT, INSERT, etc.)
            max_rows: Maximum number of rows to return
            timeout_seconds: Query timeout in seconds
            enable_read_only: Whether to enforce read-only mode
            return_format: Output format (json/csv/markdown)
            include_schema: Whether to include schema information
            user_id: User ID executing the query

        Returns:
            Dictionary with query results or error information

        Raises:
            Exception: If connection not found or query execution fails
        """
        logger.debug(
            f"[DATABASE-QUERY-SERVICE] Executing query on connection {connection_id}"
        )

        try:
            # Get the connection
            connection = self.datasource_service.get_connection(db, connection_id)
            if not connection:
                logger.error(
                    f"[DATABASE-QUERY-SERVICE] Connection not found: {connection_id}"
                )
                return {
                    "success": False,
                    "error": f"Connection not found: {connection_id}",
                }

            # Check if connection is active
            if not connection.is_active:
                logger.error(
                    f"[DATABASE-QUERY-SERVICE] Connection is not active: {connection_id}"
                )
                return {
                    "success": False,
                    "error": f"Connection is not active: {connection_id}",
                }

            # Prepare table names list
            if table_names is None:
                table_names = [table_name] if table_name else []

            # Default allowed operations if not specified
            if allowed_operations is None:
                allowed_operations = ["SELECT"]

            # Execute the query using the query executor
            result = await self.datasource_service.query_executor.execute_query(
                db=db,
                connection=connection,
                query=query,
                allowed_operations=allowed_operations,
                table_names=table_names if table_names else None,
                max_rows=max_rows,
                timeout_seconds=timeout_seconds,
                enable_read_only=enable_read_only,
                return_format=return_format,
                include_schema=include_schema,
                user_id=user_id,
                context={"connection_id": connection_id},
            )

            logger.debug(
                f"[DATABASE-QUERY-SERVICE] Query executed successfully on {connection_id}"
            )
            return result

        except Exception as e:
            logger.error(
                f"[DATABASE-QUERY-SERVICE] Query execution failed: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
            }


# Create singleton instance
_database_query_service = None


def get_database_query_service() -> DatabaseQueryService:
    """Get or create the singleton database query service instance.

    Returns:
        DatabaseQueryService instance
    """
    global _database_query_service
    if _database_query_service is None:
        _database_query_service = DatabaseQueryService()
    return _database_query_service


# For backward compatibility - create instance
database_query_service = get_database_query_service()


__all__ = [
    "DatabaseQueryService",
    "get_database_query_service",
    "database_query_service",
]
