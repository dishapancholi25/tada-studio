"""Pydantic models for datasource API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models import DatabaseType


class DatabaseConnectionCreate(BaseModel):
    """Model for creating a database connection."""

    name: str = Field(..., description="Unique name for the connection")
    description: Optional[str] = Field(
        None, description="Description of the connection"
    )
    database_type: DatabaseType = Field(..., description="Type of database")

    # Connection details (either connection_string OR individual fields)
    connection_string: Optional[str] = Field(None, description="Full connection string")
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port")
    database_name: Optional[str] = Field(None, description="Database name")
    username: Optional[str] = Field(None, description="Database username")
    password: Optional[str] = Field(None, description="Database password")

    # SSL/TLS
    use_ssl: bool = Field(False, description="Use SSL/TLS for connection")
    ssl_config: Optional[Dict[str, Any]] = Field(None, description="SSL configuration")

    # Additional options
    connection_options: Optional[Dict[str, Any]] = Field(
        None, description="Database-specific connection options"
    )

    # Access control
    read_only: bool = Field(True, description="Whether the connection is read-only")

    # Sharing / visibility
    visible_to_groups: List[str] = Field(
        default_factory=list,
        description="Groups that can access this connection. Use ['__all__'] for everyone.",
    )


class DatabaseConnectionUpdate(BaseModel):
    """Model for updating a database connection."""

    name: Optional[str] = None
    description: Optional[str] = None

    # Connection details
    connection_string: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # SSL/TLS
    use_ssl: Optional[bool] = None
    ssl_config: Optional[Dict[str, Any]] = None

    # Additional options
    connection_options: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    read_only: Optional[bool] = None
    allowed_tables: Optional[List[str]] = None
    restricted_tables: Optional[List[str]] = None


class UpdateVisibilityRequest(BaseModel):
    """Model for updating connection visibility."""

    visible_to_groups: List[str] = Field(
        ...,
        description="Groups that can access this connection. Use ['__all__'] for everyone.",
    )


class DatabaseConnectionResponse(BaseModel):
    """Model for database connection response."""

    id: str
    name: str
    description: Optional[str]
    database_type: DatabaseType
    host: Optional[str]
    port: Optional[int]
    database_name: Optional[str]
    username: Optional[str]
    use_ssl: bool
    is_active: bool
    read_only: bool
    last_connection_test: Optional[datetime]
    last_connection_status: Optional[str]
    last_error_message: Optional[str]
    query_count: int
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    visible_to_groups: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None
    is_read_only: bool = False


class QueryExecuteRequest(BaseModel):
    """Model for executing a query."""

    query: str = Field(..., description="SQL query to execute")
    limit: int = Field(1000, description="Maximum number of rows to return")


class TablePreviewRequest(BaseModel):
    """Model for table preview request."""

    table_name: str = Field(..., description="Name of the table to preview")
    limit: int = Field(100, description="Number of rows to preview")
