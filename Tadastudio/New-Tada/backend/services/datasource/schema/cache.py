"""Schema caching functionality."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import DataSourceConnection
from backend.services.datasource.config import (
    LOG_PREFIX,
    SCHEMA_CACHE_TTL_SECONDS,
    TABLE_DETAILS_CACHE_TTL_SECONDS,
    TABLE_LIST_CACHE_TTL_SECONDS,
)


logger = logging.getLogger(__name__)


class SchemaCache:
    """Manages schema caching for datasource connections.

    Implements cache storage and retrieval with TTL-based expiration
    to reduce database introspection overhead.
    """

    def get_cached_table_list(
        self, connection: DataSourceConnection, force_refresh: bool = False
    ) -> Optional[List[str]]:
        """Get cached table list if available and not expired.

        Args:
            connection: DataSourceConnection instance
            force_refresh: If True, ignore cache and return None

        Returns:
            Cached table list if valid, None otherwise
        """
        if force_refresh:
            return None

        cache_key = "table_list"
        return self._get_cache_entry(
            connection, cache_key, TABLE_LIST_CACHE_TTL_SECONDS
        )

    def set_cached_table_list(
        self, db: Session, connection: DataSourceConnection, table_list: List[str]
    ) -> None:
        """Cache table list for connection.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            table_list: List of table names to cache
        """
        cache_key = "table_list"
        self._set_cache_entry(db, connection, cache_key, table_list)
        logger.debug(
            f"{LOG_PREFIX} Cached {len(table_list)} tables for connection {connection.id}"
        )

    def get_cached_table_details(
        self,
        connection: DataSourceConnection,
        table_name: str,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get cached table details if available and not expired.

        Args:
            connection: DataSourceConnection instance
            table_name: Name of the table
            force_refresh: If True, ignore cache and return None

        Returns:
            Cached table details if valid, None otherwise
        """
        if force_refresh:
            return None

        cache_key = f"table_detail_{table_name}"
        return self._get_cache_entry(
            connection, cache_key, TABLE_DETAILS_CACHE_TTL_SECONDS
        )

    def set_cached_table_details(
        self,
        db: Session,
        connection: DataSourceConnection,
        table_name: str,
        details: Dict[str, Any],
    ) -> None:
        """Cache table details for a specific table.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            table_name: Name of the table
            details: Table details dictionary
        """
        cache_key = f"table_detail_{table_name}"
        self._set_cache_entry(db, connection, cache_key, details)
        logger.debug(
            f"{LOG_PREFIX} Cached details for table {table_name} "
            f"in connection {connection.id}"
        )

    def get_cached_schema(
        self, connection: DataSourceConnection, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get cached full schema if available and not expired.

        Args:
            connection: DataSourceConnection instance
            force_refresh: If True, ignore cache and return None

        Returns:
            Cached schema if valid, None otherwise
        """
        if force_refresh:
            return None

        if not connection.schema_cache or not connection.schema_last_updated:
            return None

        # Check if cache has expired
        cache_age = (
            datetime.now(timezone.utc) - connection.schema_last_updated
        ).total_seconds()

        if cache_age >= SCHEMA_CACHE_TTL_SECONDS:
            logger.debug(
                f"{LOG_PREFIX} Schema cache expired for connection {connection.id}"
            )
            return None

        logger.debug(f"{LOG_PREFIX} Using cached schema for connection {connection.id}")
        return connection.schema_cache

    def set_cached_schema(
        self, db: Session, connection: DataSourceConnection, schema: Dict[str, Any]
    ) -> None:
        """Cache full schema for connection.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            schema: Full schema dictionary
        """
        connection.schema_cache = schema
        connection.schema_last_updated = datetime.now(timezone.utc)
        db.commit()
        logger.debug(f"{LOG_PREFIX} Cached full schema for connection {connection.id}")

    def _get_cache_entry(
        self, connection: DataSourceConnection, cache_key: str, ttl_seconds: int
    ) -> Optional[Any]:
        """Get a cache entry if it exists and is not expired.

        Args:
            connection: DataSourceConnection instance
            cache_key: Cache key
            ttl_seconds: Time to live in seconds

        Returns:
            Cached data if valid, None otherwise
        """
        if not connection.schema_cache:
            return None

        cache_entry = connection.schema_cache.get(cache_key)
        if not cache_entry or not cache_entry.get("timestamp"):
            return None

        # Check if cache has expired
        cache_timestamp = datetime.fromisoformat(cache_entry["timestamp"])
        cache_age = (datetime.now(timezone.utc) - cache_timestamp).total_seconds()

        if cache_age >= ttl_seconds:
            return None

        return cache_entry.get("data")

    def _set_cache_entry(
        self,
        db: Session,
        connection: DataSourceConnection,
        cache_key: str,
        data: Any,
    ) -> None:
        """Set a cache entry with current timestamp.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            cache_key: Cache key
            data: Data to cache
        """
        # Ensure schema_cache dict exists
        if not connection.schema_cache:
            connection.schema_cache = {}

        # Store data with timestamp
        connection.schema_cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Update last updated timestamp
        connection.schema_last_updated = datetime.now(timezone.utc)

        db.commit()
