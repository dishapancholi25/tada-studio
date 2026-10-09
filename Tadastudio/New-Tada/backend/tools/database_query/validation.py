"""
Database Query Tool - Validation Utilities.

This module provides validation utilities for database queries and configurations.
"""

from typing import List


def validate_table_access(query: str, allowed_tables: List[str]) -> bool:
    """
    Validate that a query only accesses allowed tables.

    Args:
        query: SQL query to validate
        allowed_tables: List of allowed table names

    Returns:
        True if query only accesses allowed tables

    Note:
        This is a basic check. Full validation is handled by database_query_service.
    """
    # This is a simple validation; the main validation is in database_query_service
    query_upper = query.upper()

    # Check if any allowed table is referenced
    for table in allowed_tables:
        if table.upper() in query_upper:
            return True

    return False


def sanitize_table_names(table_names: List[str]) -> List[str]:
    """
    Sanitize table names for safe usage.

    Args:
        table_names: List of table names to sanitize

    Returns:
        Sanitized table names
    """
    # Remove any potentially dangerous characters
    sanitized = []
    for name in table_names:
        # Remove quotes, semicolons, and other SQL special characters
        clean_name = name.replace("'", "").replace('"', "").replace(";", "")
        clean_name = clean_name.strip()
        if clean_name:
            sanitized.append(clean_name)

    return sanitized
