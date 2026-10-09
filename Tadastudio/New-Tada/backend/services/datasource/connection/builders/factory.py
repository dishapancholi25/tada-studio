"""Factory for creating connection string builders."""

import logging

from backend.encryption_utils import default_encryptor
from backend.models import DatabaseType, DataSourceConnection
from backend.services.datasource.exceptions import UnsupportedDatabaseTypeError

from .base import ConnectionStringBuilder
from .mssql import MSSQLConnectionStringBuilder
from .mongodb import MongoDBConnectionStringBuilder
from .mysql import MySQLConnectionStringBuilder
from .oracle import OracleConnectionStringBuilder
from .postgres import PostgreSQLConnectionStringBuilder
from .sqlite import SQLiteConnectionStringBuilder


logger = logging.getLogger(__name__)


class ConnectionStringBuilderFactory:
    """Factory for creating database-specific connection string builders.

    This factory uses the Strategy pattern to select the appropriate
    builder based on the database type, eliminating the need for a
    large if/elif chain.
    """

    # Map database types to their builder classes
    _builders = {
        DatabaseType.POSTGRES: PostgreSQLConnectionStringBuilder,
        DatabaseType.MYSQL: MySQLConnectionStringBuilder,
        DatabaseType.MSSQL: MSSQLConnectionStringBuilder,
        DatabaseType.SQLITE: SQLiteConnectionStringBuilder,
        DatabaseType.MONGODB: MongoDBConnectionStringBuilder,
        DatabaseType.ORACLE: OracleConnectionStringBuilder,
    }

    @classmethod
    def create_builder(cls, database_type: DatabaseType) -> ConnectionStringBuilder:
        """Create a connection string builder for the specified database type.

        Args:
            database_type: The type of database

        Returns:
            ConnectionStringBuilder instance for the database type

        Raises:
            UnsupportedDatabaseTypeError: If database type is not supported
        """
        builder_class = cls._builders.get(database_type)
        if not builder_class:
            raise UnsupportedDatabaseTypeError(str(database_type))

        return builder_class()

    @classmethod
    def build_connection_string(cls, connection: DataSourceConnection) -> str:
        """Build a connection string from the connection configuration.

        This is a convenience method that handles both encrypted connection
        strings and building from individual connection parameters.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Complete connection string

        Raises:
            UnsupportedDatabaseTypeError: If database type is not supported
        """
        # If we have an encrypted connection string, decrypt and return it
        if connection.encrypted_connection_string:
            return default_encryptor.decrypt_connection_string(
                connection.encrypted_connection_string
            )

        # Otherwise, build from individual fields using the appropriate builder
        builder = cls.create_builder(connection.database_type)
        return builder.build(connection)
