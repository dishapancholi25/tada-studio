"""Custom exceptions for datasource service."""


class DatasourceError(Exception):
    """Base exception for datasource-related errors."""

    pass


class ConnectionNotFoundError(DatasourceError):
    """Raised when a datasource connection is not found."""

    def __init__(self, connection_id: str):
        """Initialize with connection ID.

        Args:
            connection_id: The connection ID that was not found
        """
        self.connection_id = connection_id
        super().__init__(f"Connection not found: {connection_id}")


class ConnectionAlreadyExistsError(DatasourceError):
    """Raised when attempting to create a connection with a name that already exists."""

    def __init__(self, name: str):
        """Initialize with connection name.

        Args:
            name: The connection name that already exists
        """
        self.name = name
        super().__init__(f"Connection with name '{name}' already exists")


class ConnectionTestFailedError(DatasourceError):
    """Raised when a connection test fails."""

    def __init__(self, connection_id: str, error_message: str):
        """Initialize with connection ID and error message.

        Args:
            connection_id: The connection ID that failed testing
            error_message: The underlying error message
        """
        self.connection_id = connection_id
        self.error_message = error_message
        super().__init__(f"Connection test failed for {connection_id}: {error_message}")


class UnsupportedDatabaseTypeError(DatasourceError):
    """Raised when an unsupported database type is encountered."""

    def __init__(self, database_type: str):
        """Initialize with database type.

        Args:
            database_type: The unsupported database type
        """
        self.database_type = database_type
        super().__init__(f"Unsupported database type: {database_type}")


class SchemaInspectionError(DatasourceError):
    """Raised when schema inspection fails."""

    def __init__(self, connection_id: str, error_message: str):
        """Initialize with connection ID and error message.

        Args:
            connection_id: The connection ID where inspection failed
            error_message: The underlying error message
        """
        self.connection_id = connection_id
        self.error_message = error_message
        super().__init__(
            f"Schema inspection failed for {connection_id}: {error_message}"
        )


class InvalidQueryError(DatasourceError):
    """Raised when a query fails validation."""

    def __init__(self, query: str, reason: str):
        """Initialize with query and reason.

        Args:
            query: The invalid query
            reason: The reason why the query is invalid
        """
        self.query = query
        self.reason = reason
        super().__init__(f"Invalid query: {reason}")


class QueryExecutionError(DatasourceError):
    """Raised when query execution fails."""

    def __init__(self, query: str, error_message: str):
        """Initialize with query and error message.

        Args:
            query: The query that failed
            error_message: The underlying error message
        """
        self.query = query
        self.error_message = error_message
        super().__init__(f"Query execution failed: {error_message}")


class ReadOnlyViolationError(DatasourceError):
    """Raised when attempting to modify data on a read-only connection."""

    def __init__(self, connection_id: str, operation: str):
        """Initialize with connection ID and operation.

        Args:
            connection_id: The read-only connection ID
            operation: The write operation that was attempted
        """
        self.connection_id = connection_id
        self.operation = operation
        super().__init__(
            f"Connection {connection_id} is read-only, cannot perform {operation}"
        )
