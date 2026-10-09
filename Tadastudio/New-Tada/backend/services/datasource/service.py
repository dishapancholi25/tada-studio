"""Main datasource service orchestrator."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models import DatabaseType, DataSourceConnection
from backend.services.datasource.config import (
    DEFAULT_QUERY_ROW_LIMIT,
    DEFAULT_TABLE_PREVIEW_LIMIT,
    LOG_PREFIX,
    READ_OPERATIONS,
)

from .connection import ConnectionManager, ConnectionTester
from .query import QueryExecutor
from .schema import SchemaInspector


logger = logging.getLogger(__name__)


def _get_user_groups(user_id: str) -> List[str]:
    """Get groups for a user, returning empty list on failure."""
    try:
        from backend.services.groups.service import GroupService

        return GroupService().get_user_groups(user_id)
    except Exception:
        return []


class DataSourceService:
    """Main service for managing datasource connections and operations.

    Orchestrates all datasource functionality including connection management,
    schema inspection, and query execution.
    """

    def __init__(self):
        """Initialize datasource service."""
        self.connection_manager = ConnectionManager()
        self.connection_tester = ConnectionTester()
        self.schema_inspector = SchemaInspector()
        self.query_executor = QueryExecutor()
        logger.info(f"{LOG_PREFIX} DataSource service initialized")

    # Connection Management Methods

    def create_connection(
        self,
        db: Session,
        name: str,
        description: str,
        database_type: DatabaseType,
        connection_string: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
        ssl_config: Optional[dict] = None,
        connection_options: Optional[dict] = None,
        user_id: Optional[str] = None,
        visible_to_groups: Optional[List[str]] = None,
        read_only: bool = True,
    ) -> DataSourceConnection:
        """Create a new database connection configuration."""
        if visible_to_groups is None:
            visible_to_groups = []

        # Validate groups exist (skip __all__ special token)
        groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
        if groups_to_validate:
            try:
                from backend.services.groups.service import GroupService

                GroupService().validate_groups_exist(groups_to_validate)
            except Exception as e:
                logger.warning(f"{LOG_PREFIX} Could not validate groups: {e}")

        return self.connection_manager.create_connection(
            db=db,
            name=name,
            description=description,
            database_type=database_type,
            connection_string=connection_string,
            host=host,
            port=port,
            database_name=database_name,
            username=username,
            password=password,
            use_ssl=use_ssl,
            ssl_config=ssl_config,
            connection_options=connection_options,
            user_id=user_id,
            visible_to_groups=visible_to_groups,
            read_only=read_only,
        )

    def get_connection(
        self, db: Session, connection_id: str
    ) -> Optional[DataSourceConnection]:
        """Get a connection by ID."""
        return self.connection_manager.get_connection(db, connection_id)

    def get_connection_for_user(
        self, db: Session, connection_id: str, user_id: str
    ) -> Optional[DataSourceConnection]:
        """Get a connection by ID, enforcing visibility rules.

        Returns the connection only if the user is the owner or the connection
        is shared with them (via __all__ or their groups). Returns None if the
        connection does not exist or is not visible to the user.
        """
        connection = self.connection_manager.get_connection(db, connection_id)
        if not connection:
            return None
        if connection.user_id == user_id:
            return connection
        groups = connection.visible_to_groups or []
        if "__all__" in groups:
            return connection
        if groups:
            user_groups = _get_user_groups(user_id)
            if any(g in groups for g in user_groups):
                return connection
        return None

    def get_connection_by_name(
        self, db: Session, name: str
    ) -> Optional[DataSourceConnection]:
        """Get a connection by name."""
        return self.connection_manager.get_connection_by_name(db, name)

    def list_connections(
        self,
        db: Session,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        filter_type: str = "all",
    ) -> List[DataSourceConnection]:
        """List all connections, including shared ones visible to the user."""
        user_groups = _get_user_groups(user_id) if user_id else []
        return self.connection_manager.list_connections(
            db, active_only, skip, limit, user_id, user_groups, filter_type
        )

    def update_visibility(
        self,
        db: Session,
        connection_id: str,
        visible_to_groups: List[str],
        user_id: str,
    ) -> Optional[DataSourceConnection]:
        """Update connection visibility groups. Only the owner can update."""
        connection = self.connection_manager.get_connection(db, connection_id)
        if not connection:
            raise ValueError(f"Connection not found: {connection_id}")

        if connection.user_id != user_id:
            raise PermissionError("Only the owner can change visibility")

        # Validate groups exist (skip __all__ special token)
        groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
        if groups_to_validate:
            try:
                from backend.services.groups.service import GroupService

                GroupService().validate_groups_exist(groups_to_validate)
            except ValueError:
                raise
            except Exception as e:
                logger.warning(f"{LOG_PREFIX} Could not validate groups: {e}")

        # Pass the already-fetched connection to avoid a redundant DB round-trip
        return self.connection_manager.update_visibility(
            db, connection, visible_to_groups
        )

    def update_connection(
        self, db: Session, connection_id: str, **kwargs
    ) -> Optional[DataSourceConnection]:
        """Update a connection configuration."""
        return self.connection_manager.update_connection(db, connection_id, **kwargs)

    def delete_connection(self, db: Session, connection_id: str) -> bool:
        """Delete a connection."""
        return self.connection_manager.delete_connection(db, connection_id)

    # Connection Testing

    def test_connection(
        self, db: Session, connection_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Test a database connection."""
        return self.connection_tester.test_connection(db, connection_id)

    # Schema Inspection Methods

    def get_table_list(
        self, db: Session, connection_id: str, force_refresh: bool = False
    ) -> Optional[List[str]]:
        """Get list of table names for a connection."""
        connection = self.get_connection(db, connection_id)
        if not connection:
            return None

        try:
            return self.schema_inspector.get_table_list(db, connection, force_refresh)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to get table list: {e}")
            return None

    def get_table_details(
        self,
        db: Session,
        connection_id: str,
        table_name: str,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information for a single table."""
        connection = self.get_connection(db, connection_id)
        if not connection:
            return None

        try:
            return self.schema_inspector.get_table_details(
                db, connection, table_name, force_refresh
            )
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to get table details: {e}")
            return None

    def get_schema(
        self, db: Session, connection_id: str, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get the database schema for a connection."""
        connection = self.get_connection(db, connection_id)
        if not connection:
            return None

        try:
            return self.schema_inspector.get_full_schema(db, connection, force_refresh)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to get schema: {e}")
            return None

    # Query Execution Methods

    async def execute_query(
        self,
        db: Session,
        connection_id: str,
        query: str,
        limit: int = DEFAULT_QUERY_ROW_LIMIT,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a query on a database connection."""
        connection = self.get_connection(db, connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}

        if not connection.is_active:
            return {"success": False, "error": "Connection is not active"}

        return await self.query_executor.execute_query(
            db=db,
            connection=connection,
            query=query,
            allowed_operations=READ_OPERATIONS + ["INSERT", "UPDATE"],
            max_rows=limit,
            user_id=user_id,
            context=context,
        )

    async def get_table_preview(
        self,
        db: Session,
        connection_id: str,
        table_name: str,
        limit: int = DEFAULT_TABLE_PREVIEW_LIMIT,
    ) -> Dict[str, Any]:
        """Get a preview of table data."""
        # Basic sanitization
        if not table_name.replace("_", "").replace("-", "").isalnum():
            return {"success": False, "error": "Invalid table name"}

        # Build simple SELECT query
        query = f"SELECT * FROM {table_name}"

        return await self.execute_query(
            db=db,
            connection_id=connection_id,
            query=query,
            limit=limit,
            context={"action": "table_preview", "table": table_name},
        )
