"""Connection testing functionality."""

import logging
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.models import DatabaseType, DataSourceConnection
from backend.services.datasource.config import (
    DEFAULT_CONNECTION_TIMEOUT_SECONDS,
    LOG_PREFIX,
)
from backend.services.datasource.exceptions import ConnectionNotFoundError

from .builders import ConnectionStringBuilderFactory


logger = logging.getLogger(__name__)


class ConnectionTester:
    """Tests database connections and updates connection status."""

    def __init__(self):
        """Initialize connection tester."""
        self.builder_factory = ConnectionStringBuilderFactory()

    def test_connection(
        self, db: Session, connection_id: str
    ) -> Tuple[bool, str | None]:
        """Test a database connection.

        Attempts to connect to the database and execute a simple query
        to verify connectivity.

        Args:
            db: Database session
            connection_id: Connection ID to test

        Returns:
            Tuple of (success, error_message)

        Raises:
            ConnectionNotFoundError: If connection not found
        """
        connection = db.query(DataSourceConnection).filter_by(id=connection_id).first()
        if not connection:
            raise ConnectionNotFoundError(connection_id)

        try:
            # MongoDB requires pymongo — SQLAlchemy has no MongoDB dialect
            if connection.database_type == DatabaseType.MONGODB:
                success, error_msg = self._test_mongodb_connection(connection)
            else:
                success, error_msg = self._test_sqlalchemy_connection(connection)

            self._update_connection_status(
                db, connection, success=success, error_message=error_msg
            )

            if success:
                logger.info(
                    f"{LOG_PREFIX} Connection test successful for {connection.name}"
                )
            else:
                logger.error(
                    f"{LOG_PREFIX} Connection test failed for {connection.name}: {error_msg}"
                )

            return success, error_msg

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"{LOG_PREFIX} Connection test failed for {connection.name}: {error_msg}"
            )

            # Update connection status
            self._update_connection_status(
                db, connection, success=False, error_message=error_msg
            )

            return False, error_msg

    def _test_sqlalchemy_connection(
        self, connection: DataSourceConnection
    ) -> Tuple[bool, str | None]:
        """Test connection via SQLAlchemy (all non-MongoDB databases).

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Tuple of (success, error_message)
        """
        conn_str = self.builder_factory.build_connection_string(connection)
        connect_args = self._get_connect_args(
            connection.database_type, DEFAULT_CONNECTION_TIMEOUT_SECONDS
        )
        engine = create_engine(conn_str, connect_args=connect_args)
        test_query = self._get_test_query(connection.database_type)

        with engine.connect() as conn:
            result = conn.execute(text(test_query))
            result.fetchone()

        return True, None

    def _test_mongodb_connection(
        self, connection: DataSourceConnection
    ) -> Tuple[bool, str | None]:
        """Test MongoDB connectivity using pymongo ping command.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Tuple of (success, error_message)
        """
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        except ImportError:
            return False, "pymongo is not installed. Run: pip install pymongo"

        from backend.services.datasource.connection.builders.mongodb import (
            MongoDBConnectionStringBuilder,
        )

        builder = MongoDBConnectionStringBuilder()
        conn_str = builder.build(connection)

        client = MongoClient(
            conn_str,
            serverSelectionTimeoutMS=DEFAULT_CONNECTION_TIMEOUT_SECONDS * 1000,
        )
        try:
            client.admin.command("ping")
            return True, None
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            return False, str(e)
        finally:
            client.close()

    def _get_test_query(self, database_type: DatabaseType) -> str:
        """Get the appropriate test query for a database type.

        Args:
            database_type: Type of database

        Returns:
            SQL query string to test the connection
        """
        test_queries = {
            DatabaseType.POSTGRES: "SELECT version()",
            DatabaseType.MYSQL: "SELECT VERSION()",
            DatabaseType.MSSQL: "SELECT @@VERSION",
            DatabaseType.SQLITE: "SELECT sqlite_version()",
            DatabaseType.ORACLE: "SELECT 1 FROM dual",
        }

        # Default query for other types
        return test_queries.get(database_type, "SELECT 1")

    def _get_connect_args(
        self, database_type: DatabaseType, timeout_seconds: int
    ) -> dict:
        """Get driver-specific connect_args for the given database type.

        Args:
            database_type: Type of database
            timeout_seconds: Connection timeout in seconds

        Returns:
            Dictionary of connect_args for SQLAlchemy create_engine
        """
        if database_type == DatabaseType.ORACLE:
            return {"tcp_connect_timeout": timeout_seconds}
        if database_type == DatabaseType.MSSQL:
            # pyodbc uses "timeout" (ODBC LoginTimeout), not "connect_timeout"
            return {"timeout": timeout_seconds}
        return {"connect_timeout": timeout_seconds}

    def _update_connection_status(
        self,
        db: Session,
        connection: DataSourceConnection,
        success: bool,
        error_message: str | None,
    ) -> None:
        """Update connection test status in database.

        Args:
            db: Database session
            connection: Connection to update
            success: Whether the test was successful
            error_message: Error message if failed, None if successful
        """
        connection.last_connection_test = datetime.now(timezone.utc)
        connection.last_connection_status = "success" if success else "failed"
        connection.last_error_message = error_message

        db.commit()
