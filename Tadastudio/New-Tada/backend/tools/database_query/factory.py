"""
Database Query Tool - Factory Functions.

This module provides factory functions for creating database query tools
with specific configurations.
"""

import logging
from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import Field

from backend.services.database import SessionLocal
from .config import build_query_field_description, validate_config
from .handlers import handle_query_execution
from .schemas import DatabaseQueryArgs, DatabaseQueryConfig


logger = logging.getLogger(__name__)


def create_database_query_tool(
    connection_id: str,
    table_name: str = "",
    table_names: List[str] = None,
    allowed_operations: Optional[List[str]] = None,
    max_rows: int = 100,
    timeout_seconds: int = 30,
    enable_read_only: bool = False,
    return_format: str = "json",
    include_schema: bool = True,
    tool_name: str = None,
    description_prefix: str = None,
    database_type: Optional[str] = None,
):
    """
    Create a database query tool with specific configuration.

    Args:
        connection_id: ID of the database connection to use
        table_name: Name of the table to query (deprecated, use table_names)
        table_names: List of table names that can be queried
        allowed_operations: List of allowed SQL operations (SELECT, INSERT, etc.)
        max_rows: Maximum number of rows to return for SELECT queries
        timeout_seconds: Query execution timeout
        enable_read_only: Force read-only mode
        return_format: Output format (json, csv, markdown)
        include_schema: Whether to include schema information in results
        tool_name: Optional custom name for the tool (defaults to query_database)
        description_prefix: Optional prefix for the tool description

    Returns:
        Configured database query tool

    Raises:
        ValueError: If configuration is invalid
    """
    # Create and validate configuration
    config = DatabaseQueryConfig(
        connection_id=connection_id,
        table_name=table_name,
        table_names=table_names,
        allowed_operations=allowed_operations,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
        enable_read_only=enable_read_only,
        return_format=return_format,
        include_schema=include_schema,
        tool_name=tool_name,
    )

    config = validate_config(config)

    # Build tool description
    from .config import ToolDescriptionBuilder

    builder = ToolDescriptionBuilder(config)
    tool_description = builder.build_description(database_type=database_type)
    if description_prefix:
        tool_description = f"{description_prefix}. {tool_description}"

    # Create dynamic Pydantic model for arguments
    query_description = build_query_field_description(config.table_names)

    class DynamicDatabaseQueryArgs(DatabaseQueryArgs):
        """Dynamic args schema with table-specific description."""

        query: str = Field(description=query_description)

    def query_database_impl(query: str) -> str:
        """Execute the database query."""
        db = SessionLocal()
        try:
            return handle_query_execution(
                db=db,
                query=query,
                connection_id=config.connection_id,
                table_names=config.table_names,
                allowed_operations=config.allowed_operations,
                max_rows=config.max_rows,
                timeout_seconds=config.timeout_seconds,
                enable_read_only=config.enable_read_only,
                return_format=config.return_format,
                include_schema=config.include_schema,
            )
        finally:
            db.close()

    # Create the tool with a unique name
    database_tool = StructuredTool(
        name=config.tool_name,
        description=tool_description,
        func=query_database_impl,
        args_schema=DynamicDatabaseQueryArgs,
    )

    return database_tool
