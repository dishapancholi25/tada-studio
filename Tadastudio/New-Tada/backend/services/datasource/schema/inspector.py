"""Schema inspection functionality."""

import logging
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.models import DataSourceConnection
from backend.services.datasource.config import LOG_PREFIX
from backend.services.datasource.connection.builders import (
    ConnectionStringBuilderFactory,
)
from backend.services.datasource.exceptions import SchemaInspectionError

from .cache import SchemaCache
from .filters import TableFilter


logger = logging.getLogger(__name__)


class SchemaInspector:
    """Inspects database schemas and retrieves metadata.

    Provides methods to get table lists, table details, and full schemas
    with caching and filtering support.
    """

    def __init__(self):
        """Initialize schema inspector."""
        self.builder_factory = ConnectionStringBuilderFactory()
        self.cache = SchemaCache()
        self.filter = TableFilter()

    def get_table_list(
        self, db: Session, connection: DataSourceConnection, force_refresh: bool = False
    ) -> List[str]:
        """Get list of table names for a connection.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            force_refresh: Force refresh the cache

        Returns:
            List of table names

        Raises:
            SchemaInspectionError: If inspection fails
        """
        # Check cache first
        if not force_refresh:
            cached = self.cache.get_cached_table_list(connection)
            if cached is not None:
                return cached

        try:
            # Get connection string and create engine
            conn_str = self.builder_factory.build_connection_string(connection)
            engine = create_engine(conn_str)
            inspector = inspect(engine)

            # Get all table names
            all_tables = inspector.get_table_names()

            # Apply filters
            filtered_tables = self.filter.filter_tables(connection, all_tables)

            # Update cache
            self.cache.set_cached_table_list(db, connection, filtered_tables)

            logger.info(
                f"{LOG_PREFIX} Retrieved {len(filtered_tables)} tables "
                f"for connection {connection.name}"
            )

            return filtered_tables

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX} Failed to get table list for {connection.name}: {str(e)}"
            )
            raise SchemaInspectionError(connection.id, str(e))

    def get_table_details(
        self,
        db: Session,
        connection: DataSourceConnection,
        table_name: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Get detailed information for a single table.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            table_name: Name of the table
            force_refresh: Force refresh the cache

        Returns:
            Dictionary containing table details

        Raises:
            SchemaInspectionError: If inspection fails
        """
        # Check cache first
        if not force_refresh:
            cached = self.cache.get_cached_table_details(connection, table_name)
            if cached is not None:
                return cached

        try:
            # Get connection string and create engine
            conn_str = self.builder_factory.build_connection_string(connection)
            engine = create_engine(conn_str)
            inspector = inspect(engine)

            # Get table details
            table_info = self._inspect_table(inspector, table_name)

            # Update cache
            self.cache.set_cached_table_details(db, connection, table_name, table_info)

            logger.info(
                f"{LOG_PREFIX} Retrieved details for table {table_name} "
                f"in connection {connection.name}"
            )

            return table_info

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX} Failed to get table details for {table_name}: {str(e)}"
            )
            raise SchemaInspectionError(connection.id, str(e))

    def get_full_schema(
        self, db: Session, connection: DataSourceConnection, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Get the complete database schema.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            force_refresh: Force refresh the cache

        Returns:
            Dictionary containing complete schema

        Raises:
            SchemaInspectionError: If inspection fails
        """
        # Check cache first
        if not force_refresh:
            cached = self.cache.get_cached_schema(connection)
            if cached is not None:
                return cached

        try:
            # Get connection string and create engine
            conn_str = self.builder_factory.build_connection_string(connection)
            engine = create_engine(conn_str)
            inspector = inspect(engine)

            schema = {"tables": {}, "views": []}

            # Get all tables
            all_tables = inspector.get_table_names()

            # Inspect each allowed table
            for table_name in all_tables:
                if self.filter.is_table_allowed(connection, table_name):
                    schema["tables"][table_name] = self._inspect_table(
                        inspector, table_name
                    )

            # Get views if supported
            try:
                schema["views"] = inspector.get_view_names()
            except Exception:
                pass  # Some databases don't support views

            # Update cache
            self.cache.set_cached_schema(db, connection, schema)

            logger.info(
                f"{LOG_PREFIX} Retrieved full schema for connection {connection.name}: "
                f"{len(schema['tables'])} tables, {len(schema['views'])} views"
            )

            return schema

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX} Failed to get schema for {connection.name}: {str(e)}"
            )
            raise SchemaInspectionError(connection.id, str(e))

    def _inspect_table(self, inspector, table_name: str) -> Dict[str, Any]:
        """Inspect a single table and get its metadata.

        Args:
            inspector: SQLAlchemy inspector
            table_name: Name of the table

        Returns:
            Dictionary with table metadata
        """
        table_info = {
            "columns": [],
            "primary_keys": [],
            "foreign_keys": [],
            "indexes": [],
        }

        # Get columns
        for column in inspector.get_columns(table_name):
            table_info["columns"].append(
                {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column["nullable"],
                    "default": str(column.get("default", "")),
                    "autoincrement": column.get("autoincrement", False),
                }
            )

        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name)
        if pk_constraint:
            table_info["primary_keys"] = pk_constraint.get("constrained_columns", [])

        # Get foreign keys
        for fk in inspector.get_foreign_keys(table_name):
            table_info["foreign_keys"].append(
                {
                    "name": fk.get("name"),
                    "columns": fk.get("constrained_columns", []),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": fk.get("referred_columns", []),
                }
            )

        # Get indexes
        for index in inspector.get_indexes(table_name):
            table_info["indexes"].append(
                {
                    "name": index.get("name"),
                    "columns": index.get("column_names", []),
                    "unique": index.get("unique", False),
                }
            )

        return table_info
