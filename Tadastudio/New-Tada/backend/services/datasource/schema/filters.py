"""Table filtering functionality for allowed/restricted table lists."""

import logging
from typing import List

from backend.models import DataSourceConnection
from backend.services.datasource.config import LOG_PREFIX


logger = logging.getLogger(__name__)


class TableFilter:
    """Filters table lists based on allowed and restricted table configuration.

    Handles whitelist (allowed_tables) and blacklist (restricted_tables)
    filtering for database schema introspection.
    """

    def filter_tables(
        self, connection: DataSourceConnection, tables: List[str]
    ) -> List[str]:
        """Filter table list based on connection configuration.

        Args:
            connection: DataSourceConnection with filter configuration
            tables: List of all table names

        Returns:
            Filtered list of table names
        """
        filtered = tables

        # Apply whitelist filter
        if connection.allowed_tables:
            filtered = [t for t in filtered if t in connection.allowed_tables]
            logger.debug(
                f"{LOG_PREFIX} Applied whitelist filter: "
                f"{len(tables)} -> {len(filtered)} tables"
            )

        # Apply blacklist filter
        if connection.restricted_tables:
            filtered = [t for t in filtered if t not in connection.restricted_tables]
            logger.debug(
                f"{LOG_PREFIX} Applied blacklist filter: "
                f"{len(tables)} -> {len(filtered)} tables"
            )

        return filtered

    def is_table_allowed(
        self, connection: DataSourceConnection, table_name: str
    ) -> bool:
        """Check if a table is allowed based on connection configuration.

        Args:
            connection: DataSourceConnection with filter configuration
            table_name: Name of the table to check

        Returns:
            True if table is allowed, False otherwise
        """
        # Check whitelist
        if connection.allowed_tables and table_name not in connection.allowed_tables:
            return False

        # Check blacklist
        if connection.restricted_tables and table_name in connection.restricted_tables:
            return False

        return True
