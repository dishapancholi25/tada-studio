"""
Database Query Tool - Schemas and Data Models.

This module defines Pydantic models for database query tool configuration,
input arguments, and execution results.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DatabaseQueryArgs(BaseModel):
    """Input arguments for database query tool."""

    query: str = Field(description="SQL query to execute")


class DatabaseQueryConfig(BaseModel):
    """Configuration for database query tool."""

    connection_id: str = Field(description="ID of the database connection to use")
    table_name: str = Field(
        default="",
        description="Name of the table to query (deprecated, use table_names)",
    )
    table_names: Optional[List[str]] = Field(
        default=None, description="List of table names that can be queried"
    )
    allowed_operations: Optional[List[str]] = Field(
        default=None,
        description="List of allowed SQL operations (SELECT, INSERT, etc.)",
    )
    max_rows: int = Field(
        default=100, description="Maximum number of rows to return for SELECT queries"
    )
    timeout_seconds: int = Field(
        default=30, description="Query execution timeout in seconds"
    )
    enable_read_only: bool = Field(default=False, description="Force read-only mode")
    return_format: str = Field(
        default="json", description="Output format (json, csv, markdown)"
    )
    include_schema: bool = Field(
        default=True, description="Whether to include schema information in results"
    )
    tool_name: Optional[str] = Field(
        default=None, description="Optional custom name for the tool"
    )


class DatabaseQueryResponse(BaseModel):
    """Response from database query execution."""

    success: bool = Field(description="Whether the query executed successfully")
    operation: Optional[str] = Field(
        default=None, description="SQL operation type (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE)"
    )
    row_count: Optional[int] = Field(
        default=None, description="Number of rows affected or returned"
    )
    columns: Optional[List[str]] = Field(
        default=None, description="Column names for SELECT queries"
    )
    data: Optional[Any] = Field(default=None, description="Query result data")
    has_more_rows: Optional[bool] = Field(
        default=None, description="Whether more rows exist beyond max_rows limit"
    )
    schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Table schema information"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if query failed"
    )
    error_type: Optional[str] = Field(
        default=None, description="Type of error (validation, connection, execution)"
    )
    message: Optional[str] = Field(
        default=None, description="Additional message about the operation"
    )


class DatabaseQueryExecutionMetadata(BaseModel):
    """Metadata about a database query execution."""

    query: str = Field(description="The SQL query that was executed")
    connection_id: str = Field(description="Database connection ID used")
    table_names: List[str] = Field(description="Tables involved in the query")
    operation: str = Field(description="SQL operation type")
    row_count: int = Field(description="Number of rows affected or returned")
    execution_time: float = Field(description="Query execution time in seconds")
    success: bool = Field(description="Whether execution was successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")
