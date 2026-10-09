"""
Database Query Tool - Configuration and Validation.

This module provides configuration validation, tool name generation,
and description building for database query tools.
"""

from typing import List, Optional

from backend.services.datasource.config import ALL_OPERATIONS, DDL_OPERATIONS

from .schemas import DatabaseQueryConfig


def generate_tool_name(
    table_names: List[str], custom_name: Optional[str] = None
) -> str:
    """
    Generate a unique tool name based on table names.

    Args:
        table_names: List of table names the tool can query
        custom_name: Optional custom name to use instead

    Returns:
        Generated tool name suitable for use as a function name
    """
    if custom_name:
        return custom_name

    if not table_names:
        return "query_database"

    # Create a name based on the tables
    if len(table_names) <= 2:
        table_suffix = "_".join(table_names[:2])
    else:
        table_suffix = f"{table_names[0]}_and_more"

    tool_name = f"query_{table_suffix}".replace("-", "_").lower()
    return tool_name


def build_tool_description(table_names: List[str]) -> str:
    """
    Build a descriptive string for the tool.

    Args:
        table_names: List of table names the tool can query

    Returns:
        Tool description string
    """
    if not table_names:
        return "Execute SQL queries on the connected database."
    tables_str = ", ".join(table_names)
    return f"Execute SQL queries on the following database tables: {tables_str}."


def build_query_field_description(table_names: List[str]) -> str:
    """
    Build description for the query field based on available tables.

    Args:
        table_names: List of table names the tool can query

    Returns:
        Query field description
    """
    if not table_names:
        return "SQL query to execute on the connected database"
    tables_str = ", ".join(table_names)
    return f"SQL query to execute. Can reference any of these tables: {tables_str}"


def validate_config(config: DatabaseQueryConfig) -> DatabaseQueryConfig:
    """
    Validate and normalize configuration.

    Args:
        config: Database query configuration

    Returns:
        Validated and normalized configuration

    Raises:
        ValueError: If configuration is invalid
    """
    if not config.connection_id:
        raise ValueError("connection_id is required")

    # Set default allowed operations
    if config.allowed_operations is None:
        config.allowed_operations = ["SELECT"]

    # Handle backward compatibility - if table_name is provided but not table_names
    if config.table_name and not config.table_names:
        config.table_names = [config.table_name]

    has_ddl = config.allowed_operations and any(
        op in DDL_OPERATIONS for op in config.allowed_operations
    )
    if not config.table_names and not has_ddl:
        raise ValueError("table_names is required")

    if not config.table_names:
        config.table_names = []

    # Generate tool name if not provided
    if not config.tool_name:
        config.tool_name = generate_tool_name(config.table_names)

    return config


class ConfigValidator:
    """Validator for database query tool configuration."""

    @staticmethod
    def validate_return_format(return_format: str) -> None:
        """
        Validate the return format.

        Args:
            return_format: The format to validate

        Raises:
            ValueError: If format is not supported
        """
        valid_formats = ["json", "csv", "markdown"]
        if return_format not in valid_formats:
            raise ValueError(
                f"Invalid return_format: {return_format}. "
                f"Must be one of: {', '.join(valid_formats)}"
            )

    @staticmethod
    def validate_allowed_operations(operations: List[str]) -> None:
        """
        Validate allowed operations list.

        Args:
            operations: List of SQL operations to validate

        Raises:
            ValueError: If any operation is invalid
        """
        valid_operations = ALL_OPERATIONS
        for op in operations:
            if op.upper() not in valid_operations:
                raise ValueError(
                    f"Invalid operation: {op}. "
                    f"Must be one of: {', '.join(valid_operations)}"
                )


class ToolDescriptionBuilder:
    """Builder for creating tool descriptions with metadata."""

    def __init__(self, config: DatabaseQueryConfig):
        """
        Initialize builder with configuration.

        Args:
            config: Database query configuration
        """
        self.config = config

    def build_description(self, database_type: Optional[str] = None) -> str:
        """
        Build complete tool description.

        Args:
            database_type: Optional database type (e.g. 'postgres', 'mysql')

        Returns:
            Full tool description with metadata
        """
        base_desc = build_tool_description(self.config.table_names)

        # Add database type context
        if database_type:
            base_desc += f" Database type: {database_type}. Use {database_type}-compatible SQL syntax."

        # Add allowed operations with explicit constraint
        if self.config.allowed_operations:
            ops_str = ", ".join(self.config.allowed_operations)
            base_desc += f" ONLY these operations are permitted: {ops_str}. Do not use any other SQL commands."

        # Add read-only notice
        if self.config.enable_read_only:
            base_desc += " (Read-only mode enabled)"

        return base_desc

    def build_args_description(self) -> str:
        """
        Build description for the query argument.

        Returns:
            Query argument description
        """
        return build_query_field_description(self.config.table_names)
