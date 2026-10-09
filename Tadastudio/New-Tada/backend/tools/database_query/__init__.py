"""
Database Query Tool - Modular implementation.

This module provides database query capabilities with configurable options for
executing SQL queries against database connections with safety measures, validation,
and result formatting.

Main exports:
    - create_database_query_tool: Factory for creating database query tools

Example:
    Basic usage:
    >>> from backend.tools.database_query import create_database_query_tool
    >>> tool = create_database_query_tool(
    ...     connection_id="my-db-connection",
    ...     table_names=["users", "orders"],
    ...     allowed_operations=["SELECT"],
    ...     max_rows=100
    ... )

    With custom configuration:
    >>> tool = create_database_query_tool(
    ...     connection_id="my-db-connection",
    ...     table_names=["analytics"],
    ...     allowed_operations=["SELECT", "INSERT"],
    ...     return_format="markdown",
    ...     include_schema=True,
    ...     tool_name="query_analytics"
    ... )
"""

# Configuration
from .config import (
    ConfigValidator,
    ToolDescriptionBuilder,
    build_query_field_description,
    build_tool_description,
    generate_tool_name,
    validate_config,
)

# Execution
from .execution import (
    execute_in_executor,
    execute_in_new_loop,
    execute_query_async,
    execute_query_with_async_handling,
)

# Factory function (primary interface)
from .factory import create_database_query_tool

# Formatters
from .formatters import (
    format_csv_response,
    format_error_response,
    format_json_response,
    format_markdown_response,
    format_operation_response,
    format_query_result,
    get_formatter,
)

# Handlers (for advanced usage)
from .handlers import handle_query_execution

# Schemas
from .schemas import (
    DatabaseQueryArgs,
    DatabaseQueryConfig,
    DatabaseQueryExecutionMetadata,
    DatabaseQueryResponse,
)

# Validation utilities
from .validation import sanitize_table_names, validate_table_access


__all__ = [
    # Factory function (primary interface)
    "create_database_query_tool",
    # Schemas
    "DatabaseQueryArgs",
    "DatabaseQueryConfig",
    "DatabaseQueryResponse",
    "DatabaseQueryExecutionMetadata",
    # Configuration
    "generate_tool_name",
    "build_tool_description",
    "build_query_field_description",
    "validate_config",
    "ConfigValidator",
    "ToolDescriptionBuilder",
    # Formatters
    "format_json_response",
    "format_csv_response",
    "format_markdown_response",
    "format_operation_response",
    "format_error_response",
    "format_query_result",
    "get_formatter",
    # Execution
    "execute_in_new_loop",
    "execute_in_executor",
    "execute_query_async",
    "execute_query_with_async_handling",
    # Handlers
    "handle_query_execution",
    # Validation
    "validate_table_access",
    "sanitize_table_names",
]
