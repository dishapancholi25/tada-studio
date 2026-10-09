"""
Database Node Executor Package.

This package provides a modular, service-oriented implementation of the
DATABASE_INSERT node executor with proper separation of concerns.

Main Components:
- DatabaseNodeExecutor: Main executor class
- DatabaseConnectionManager: Handles database connections
- DatabaseQueryBuilder: Builds SQL queries
- DatabaseInsertConfig: Type-safe configuration
- Custom exceptions for specific error handling

Example:
    >>> from backend.services.nodes.executors.database import DatabaseNodeExecutor
    >>> executor = DatabaseNodeExecutor()
    >>> result = await executor.execute(node, state, graph, execution_id)
"""

from .config import (
    ColumnMappingConfig,
    DatabaseConnectionDetails,
    DatabaseInsertConfig,
)
from .connection_manager import DatabaseConnectionManager
from .exceptions import (
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseNodeError,
    QueryBuildError,
    QueryExecutionError,
)
from .executor import DatabaseNodeExecutor
from .query_action_executor import DatabaseQueryActionNodeExecutor
from .query_builder import DatabaseQueryBuilder


__all__ = [
    # Main executors
    "DatabaseNodeExecutor",
    "DatabaseQueryActionNodeExecutor",
    # Services
    "DatabaseConnectionManager",
    "DatabaseQueryBuilder",
    # Configuration
    "DatabaseInsertConfig",
    "ColumnMappingConfig",
    "DatabaseConnectionDetails",
    # Exceptions
    "DatabaseNodeError",
    "DatabaseConnectionError",
    "QueryBuildError",
    "QueryExecutionError",
    "ConfigurationError",
]
