"""SQLite connection string builder."""

import logging

from backend.models import DataSourceConnection

from .base import ConnectionStringBuilder


logger = logging.getLogger(__name__)


class SQLiteConnectionStringBuilder(ConnectionStringBuilder):
    """Build connection strings for SQLite databases.

    SQLite is a file-based database and does not support SSL or
    network connections.
    """

    def build(self, connection: DataSourceConnection) -> str:
        """Build SQLite connection string.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            SQLite connection string

        Example:
            sqlite:///path/to/database.db
        """
        # SQLite uses the database_name as the file path
        return f"sqlite:///{connection.database_name}"
