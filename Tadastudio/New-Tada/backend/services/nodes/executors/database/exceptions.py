"""
Database Node Executor Exceptions.

This module defines custom exception types for database node execution,
providing specific error types for better error handling and debugging.
"""


class DatabaseNodeError(Exception):
    """
    Base exception for database node errors.

    All database node-specific exceptions inherit from this class,
    allowing for catch-all error handling when needed.
    """

    pass


class DatabaseConnectionError(DatabaseNodeError):
    """
    Failed to connect to database.

    Raised when:
    - Connection details are invalid
    - Database server is unreachable
    - Authentication fails
    - SSL/TLS connection fails
    """

    def __init__(self, connection_id: str, message: str):
        """
        Initialize database connection error.

        Args:
            connection_id: ID of the connection that failed
            message: Detailed error message
        """
        self.connection_id = connection_id
        super().__init__(f"Database connection failed (ID: {connection_id}): {message}")


class QueryBuildError(DatabaseNodeError):
    """
    Failed to build database query.

    Raised when:
    - Query configuration is invalid
    - Column mappings are malformed
    - Value extraction fails
    - SQL syntax errors in expressions
    """

    def __init__(self, table_name: str, message: str):
        """
        Initialize query build error.

        Args:
            table_name: Name of the table for the query
            message: Detailed error message
        """
        self.table_name = table_name
        super().__init__(f"Query build failed for table '{table_name}': {message}")


class QueryExecutionError(DatabaseNodeError):
    """
    Failed to execute database query.

    Raised when:
    - Query syntax is invalid
    - Constraint violations occur
    - Data type mismatches
    - Permission issues
    """

    def __init__(self, query: str, message: str):
        """
        Initialize query execution error.

        Args:
            query: The SQL query that failed
            message: Detailed error message
        """
        self.query = query
        # Truncate query in error message if too long
        query_preview = query[:100] + "..." if len(query) > 100 else query
        super().__init__(f"Query execution failed: {message}\nQuery: {query_preview}")


class ConfigurationError(DatabaseNodeError):
    """
    Invalid database node configuration.

    Raised when:
    - Required configuration fields are missing
    - Configuration values are invalid
    - Configuration format is incorrect
    """

    def __init__(self, field_name: str, message: str):
        """
        Initialize configuration error.

        Args:
            field_name: Name of the invalid configuration field
            message: Detailed error message
        """
        self.field_name = field_name
        super().__init__(f"Configuration error in '{field_name}': {message}")
