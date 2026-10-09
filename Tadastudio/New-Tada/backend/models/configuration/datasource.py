"""Data source connection models."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin
from ..enums import DatabaseType


class DataSourceConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing database connection configurations.

    Manages database connection settings including encrypted credentials,
    SSL configuration, access control, and usage tracking.

    Attributes:
        id: Unique connection identifier (UUID).
        name: Unique connection name.
        description: Connection description.
        database_type: Type of database (postgres, mysql, etc.).
        encrypted_connection_string: Full encrypted connection string.
        host: Database host.
        port: Database port.
        database_name: Database name.
        username: Database username.
        encrypted_password: Encrypted database password.
        use_ssl: Whether to use SSL/TLS.
        ssl_config: SSL configuration (JSON).
        connection_options: Database-specific options (JSON).
        is_active: Whether connection is active.
        last_connection_test: Last connection test timestamp.
        last_connection_status: Last connection test status.
        last_error_message: Last connection error message.
        schema_cache: Cached database schema (JSON).
        schema_last_updated: Schema cache last updated timestamp.
        allowed_tables: List of allowed tables (JSON).
        restricted_tables: List of restricted tables (JSON).
        read_only: Whether connection is read-only.
        query_count: Total number of queries executed.
        last_used: Last usage timestamp.
        user_id: Owner user ID.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "datasource_connections"

    # Connection details
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    database_type = Column(Enum(DatabaseType), nullable=False)

    # Connection configuration (encrypted)
    encrypted_connection_string = Column(Text, nullable=True)

    # Alternative: Individual fields (also encrypted where sensitive)
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    database_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    encrypted_password = Column(Text, nullable=True)

    # SSL/TLS configuration
    use_ssl = Column(Boolean, default=False)
    ssl_config = Column(JSON, nullable=True)

    # Connection options
    connection_options = Column(JSON, nullable=True)

    # Status and metadata
    is_active = Column(Boolean, default=True)
    last_connection_test = Column(DateTime(timezone=True), nullable=True)
    last_connection_status = Column(String(50), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Schema cache (for performance)
    schema_cache = Column(JSON, nullable=True)
    schema_last_updated = Column(DateTime(timezone=True), nullable=True)

    # Access control
    allowed_tables = Column(JSON, nullable=True)
    restricted_tables = Column(JSON, nullable=True)
    read_only = Column(Boolean, default=True)

    # Usage tracking
    query_count = Column(BigInteger, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)

    # Owner
    user_id = Column(String(255), nullable=True, index=True)

    # Sharing / visibility
    visible_to_groups = Column(JSONB, nullable=False, server_default="[]")

    # Relationships
    query_history = relationship(
        "DataSourceQueryHistory",
        back_populates="connection",
        cascade="all, delete-orphan",
    )


class DataSourceQueryHistory(Base, UUIDPrimaryKeyMixin):
    """Model for tracking queries executed against data sources.

    Tracks query execution history including query text, execution details,
    and results for auditing and performance monitoring.

    Attributes:
        id: Unique query history identifier (UUID).
        connection_id: Associated connection ID.
        query_text: SQL query text.
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE, etc.).
        executed_by: User or agent ID that executed the query.
        execution_context: Additional context (JSON).
        status: Query execution status (success, failed, timeout).
        rows_affected: Number of rows affected.
        execution_time_ms: Execution time in milliseconds.
        error_message: Error message if query failed.
        executed_at: Query execution timestamp.
    """

    __tablename__ = "datasource_query_history"

    connection_id = Column(
        String,
        ForeignKey("datasource_connections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Query details
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=True)

    # Execution details
    executed_by = Column(String(255), nullable=True)
    execution_context = Column(JSON, nullable=True)

    # Results
    status = Column(String(50), nullable=False)
    rows_affected = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    connection = relationship("DataSourceConnection", back_populates="query_history")
