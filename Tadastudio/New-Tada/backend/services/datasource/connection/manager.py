"""Connection manager for CRUD operations on datasource connections."""

import logging
from typing import List, Optional

from sqlalchemy import cast, literal, or_, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Session
from sqlalchemy.types import Text

from backend.encryption_utils import default_encryptor
from backend.models import DatabaseType, DataSourceConnection
from backend.services.datasource.config import LOG_PREFIX
from backend.services.datasource.exceptions import (
    ConnectionAlreadyExistsError,
)


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages CRUD operations for datasource connections.

    Handles creation, retrieval, updates, and deletion of database
    connection configurations with proper encryption of credentials.
    """

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
        """Create a new database connection configuration.

        Args:
            db: Database session
            name: Unique name for the connection
            description: Description of the connection
            database_type: Type of database
            connection_string: Full connection string (alternative to individual fields)
            host: Database host
            port: Database port
            database_name: Database name
            username: Database username
            password: Database password (will be encrypted)
            use_ssl: Whether to use SSL/TLS
            ssl_config: SSL configuration parameters
            connection_options: Additional connection options
            user_id: User ID who owns this connection

        Returns:
            Created DataSourceConnection

        Raises:
            ConnectionAlreadyExistsError: If connection name already exists
        """
        # Check if connection with name already exists
        existing = db.query(DataSourceConnection).filter_by(name=name).first()
        if existing:
            raise ConnectionAlreadyExistsError(name)

        # Create new connection
        connection = DataSourceConnection(
            name=name,
            description=description,
            database_type=database_type,
            use_ssl=use_ssl,
            ssl_config=ssl_config,
            connection_options=connection_options,
            user_id=user_id,
            visible_to_groups=visible_to_groups or [],
            read_only=read_only,
        )

        # Encrypt and store credentials
        if connection_string:
            connection.encrypted_connection_string = (
                default_encryptor.encrypt_connection_string(connection_string)
            )
        else:
            # Store individual fields
            connection.host = host
            connection.port = port
            connection.database_name = database_name
            connection.username = username
            if password:
                connection.encrypted_password = default_encryptor.encrypt_password(
                    password
                )

        db.add(connection)
        db.commit()
        db.refresh(connection)

        logger.info(f"{LOG_PREFIX} Created connection '{name}' (ID: {connection.id})")

        return connection

    def get_connection(
        self, db: Session, connection_id: str
    ) -> Optional[DataSourceConnection]:
        """Get a connection by ID.

        Args:
            db: Database session
            connection_id: Connection ID

        Returns:
            DataSourceConnection if found, None otherwise
        """
        return db.query(DataSourceConnection).filter_by(id=connection_id).first()

    def get_connection_by_name(
        self, db: Session, name: str
    ) -> Optional[DataSourceConnection]:
        """Get a connection by name.

        Args:
            db: Database session
            name: Connection name

        Returns:
            DataSourceConnection if found, None otherwise
        """
        return db.query(DataSourceConnection).filter_by(name=name).first()

    def list_connections(
        self,
        db: Session,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        user_groups: Optional[List[str]] = None,
        filter_type: str = "all",
    ) -> List[DataSourceConnection]:
        """List all connections, optionally filtered.

        Args:
            db: Database session
            active_only: Only return active connections
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            user_id: Current user ID (required for shared visibility)
            user_groups: List of groups the user belongs to
            filter_type: 'owned' (user's own), 'shared' (shared with user), or 'all'

        Returns:
            List of DataSourceConnection objects
        """
        query = db.query(DataSourceConnection)

        if active_only:
            query = query.filter_by(is_active=True)

        if user_id:
            if user_groups is None:
                user_groups = []

            # JSONB GIN visibility conditions matching collection pattern
            all_visible = DataSourceConnection.visible_to_groups.op("@>")(
                text("'[\"__all__\"]'::jsonb")
            )

            if user_groups:
                groups_overlap = DataSourceConnection.visible_to_groups.op("?|")(
                    cast(literal(user_groups), PG_ARRAY(Text))
                )
                shared_condition = or_(all_visible, groups_overlap)
            else:
                shared_condition = all_visible

            owned_condition = DataSourceConnection.user_id == user_id

            if filter_type == "owned":
                query = query.filter(owned_condition)
            elif filter_type == "shared":
                query = query.filter(
                    shared_condition, DataSourceConnection.user_id != user_id
                )
            else:  # 'all' - owned + shared
                query = query.filter(or_(owned_condition, shared_condition))

        return query.offset(skip).limit(limit).all()

    def update_visibility(
        self,
        db: Session,
        connection: DataSourceConnection,
        visible_to_groups: List[str],
    ) -> DataSourceConnection:
        """Update connection visibility groups.

        Args:
            db: Database session
            connection: The DataSourceConnection object to update (already fetched and ownership-checked by the caller)
            visible_to_groups: New list of group names

        Returns:
            Updated DataSourceConnection
        """
        connection.visible_to_groups = visible_to_groups
        db.commit()
        db.refresh(connection)

        logger.info(
            f"{LOG_PREFIX} Updated visibility for connection {connection.id} to {visible_to_groups}"
        )

        return connection

    def update_connection(
        self, db: Session, connection_id: str, **kwargs
    ) -> Optional[DataSourceConnection]:
        """Update a connection configuration.

        Args:
            db: Database session
            connection_id: Connection ID to update
            **kwargs: Fields to update

        Returns:
            Updated DataSourceConnection if found, None otherwise

        Note:
            Passwords and connection strings are automatically encrypted
        """
        connection = db.query(DataSourceConnection).filter_by(id=connection_id).first()
        if not connection:
            return None

        # Update fields with special handling for sensitive data
        for key, value in kwargs.items():
            if key == "connection_string" and value:
                connection.encrypted_connection_string = (
                    default_encryptor.encrypt_connection_string(value)
                )
            elif key == "password" and value:
                connection.encrypted_password = default_encryptor.encrypt_password(
                    value
                )
            elif hasattr(connection, key):
                setattr(connection, key, value)

        db.commit()
        db.refresh(connection)

        logger.info(f"{LOG_PREFIX} Updated connection {connection_id}")

        return connection

    def delete_connection(self, db: Session, connection_id: str) -> bool:
        """Delete a connection.

        Args:
            db: Database session
            connection_id: Connection ID to delete

        Returns:
            True if deleted, False if not found
        """
        connection = db.query(DataSourceConnection).filter_by(id=connection_id).first()
        if not connection:
            return False

        db.delete(connection)
        db.commit()

        logger.info(f"{LOG_PREFIX} Deleted connection {connection_id}")

        return True
