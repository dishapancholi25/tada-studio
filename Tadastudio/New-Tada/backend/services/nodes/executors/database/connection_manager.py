"""
Database Connection Manager.

This module handles database connection retrieval, credential decryption,
and connection creation for database node execution.
"""

from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.services.database import SessionLocal
from backend.services.config import get_logger

from .config import DatabaseConnectionDetails
from .exceptions import DatabaseConnectionError


connection_logger = get_logger("nodes.executors.database.connection")


class DatabaseConnectionManager:
    """
    Manages database connections for node execution.

    Handles:
    - Retrieving connection details from datasource service
    - Decrypting credentials
    - Creating psycopg2 connections
    - SSL/TLS configuration

    Example:
        >>> manager = DatabaseConnectionManager(datasource_service, encryptor)
        >>> details = manager.get_connection_details("conn-123")
        >>> conn = manager.create_psycopg2_connection(details)
    """

    def __init__(
        self,
        datasource_service: Optional[Any] = None,
        encryptor: Optional[Any] = None,
    ):
        """
        Initialize connection manager.

        Args:
            datasource_service: Service for retrieving datasource records
            encryptor: Service for decrypting passwords
        """
        from backend.services.datasource import get_datasource_service
        from backend.encryption_utils import default_encryptor

        self.datasource_service = datasource_service or get_datasource_service()
        self.encryptor = encryptor or default_encryptor

    def get_connection_details(self, connection_id: str) -> DatabaseConnectionDetails:
        """
        Retrieve and decrypt database connection details.

        Args:
            connection_id: ID of the database connection

        Returns:
            DatabaseConnectionDetails with decrypted credentials

        Raises:
            DatabaseConnectionError: If connection not found or retrieval fails
        """
        connection_logger.info(
            f"[DATABASE-CONNECTION] Retrieving connection details for ID: {connection_id}"
        )

        db = SessionLocal()
        try:
            # Get connection from datasource service
            connection = self.datasource_service.get_connection(db, connection_id)

            if not connection:
                raise DatabaseConnectionError(
                    connection_id, f"Connection not found: {connection_id}"
                )

            connection_logger.debug(
                f"[DATABASE-CONNECTION] Found connection: {connection.host}:{connection.port}"
            )

            # Decrypt password
            password = ""
            if connection.encrypted_password:
                try:
                    password = self.encryptor.decrypt_password(
                        connection.encrypted_password
                    )
                    connection_logger.debug(
                        "[DATABASE-CONNECTION] Password decrypted successfully"
                    )
                except Exception as e:
                    raise DatabaseConnectionError(
                        connection_id, f"Failed to decrypt password: {e}"
                    ) from e

            # Build connection details
            details = DatabaseConnectionDetails(
                host=connection.host,
                port=connection.port or 5432,
                database=connection.database_name,
                username=connection.username,
                password=password,
                use_ssl=connection.use_ssl,
            )

            connection_logger.info(
                f"[DATABASE-CONNECTION] Connection details retrieved successfully: "
                f"{details.host}:{details.port}/{details.database}"
            )

            return details

        except DatabaseConnectionError:
            raise
        except Exception as e:
            connection_logger.error(
                f"[DATABASE-CONNECTION] Failed to retrieve connection details: {e}",
                exc_info=True,
            )
            raise DatabaseConnectionError(
                connection_id, f"Failed to retrieve connection: {e}"
            ) from e
        finally:
            db.close()

    def create_psycopg2_connection(
        self, details: DatabaseConnectionDetails
    ) -> psycopg2.extensions.connection:
        """
        Create a psycopg2 connection from connection details.

        Args:
            details: Database connection details

        Returns:
            psycopg2 connection object

        Raises:
            DatabaseConnectionError: If connection fails
        """
        connection_logger.info(
            f"[DATABASE-CONNECTION] Creating psycopg2 connection to "
            f"{details.host}:{details.port}/{details.database}"
        )

        try:
            conn = psycopg2.connect(**details.to_psycopg2_kwargs())

            connection_logger.info(
                f"[DATABASE-CONNECTION] Connection established successfully to "
                f"{details.host}:{details.port}/{details.database}"
            )

            return conn

        except psycopg2.Error as e:
            connection_logger.error(
                f"[DATABASE-CONNECTION] psycopg2 connection failed: {e}",
                exc_info=True,
            )
            raise DatabaseConnectionError(
                "unknown",
                f"Failed to connect to {details.host}:{details.port}: {e}",
            ) from e
        except Exception as e:
            connection_logger.error(
                f"[DATABASE-CONNECTION] Unexpected connection error: {e}",
                exc_info=True,
            )
            raise DatabaseConnectionError(
                "unknown", f"Unexpected connection error: {e}"
            ) from e

    def execute_with_cursor(
        self,
        connection: psycopg2.extensions.connection,
        query: str,
        values: list,
        return_results: bool = True,
    ) -> Any:
        """
        Execute a query with a RealDictCursor.

        Args:
            connection: psycopg2 connection
            query: SQL query to execute
            values: Query parameter values
            return_results: Whether to fetch and return results

        Returns:
            List of result dictionaries if return_results is True, otherwise None

        Raises:
            Exception: If query execution fails
        """
        connection_logger.debug(
            f"[DATABASE-CONNECTION] Executing query with {len(values)} parameters"
        )

        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, values)

                if return_results:
                    results = cursor.fetchall()
                    connection_logger.debug(
                        f"[DATABASE-CONNECTION] Query returned {len(results)} rows"
                    )
                    return [dict(row) for row in results]
                else:
                    rowcount = cursor.rowcount
                    connection_logger.debug(
                        f"[DATABASE-CONNECTION] Query affected {rowcount} rows"
                    )
                    return rowcount

    def execute_select_with_limit(
        self,
        connection: psycopg2.extensions.connection,
        query: str,
        params: dict,
        max_rows: int = 100,
    ) -> list:
        """
        Execute a SELECT query and return at most *max_rows* rows as dicts.

        Args:
            connection: psycopg2 connection
            query: SQL query string (may use %(name)s placeholders)
            params: Named parameter dict for psycopg2
            max_rows: Maximum number of rows to fetch

        Returns:
            List of result row dicts
        """
        connection_logger.debug(
            f"[DATABASE-CONNECTION] Running SELECT (max_rows={max_rows})"
        )
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or {})
                rows = cursor.fetchmany(max_rows)
                connection_logger.debug(
                    f"[DATABASE-CONNECTION] SELECT returned {len(rows)} rows"
                )
                return [dict(row) for row in rows]
