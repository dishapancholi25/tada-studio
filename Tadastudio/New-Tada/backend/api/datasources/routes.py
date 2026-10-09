"""API endpoints for database connections."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_scope
from backend.encryption_utils import default_encryptor
from backend.models import DatabaseType, DataSourceConnection
from backend.services.auth.rbac import _redact_email
from backend.services.datasource import get_datasource_service
from backend.services.datasource.connection.builders.factory import (
    ConnectionStringBuilderFactory,
)

from .dependencies import get_database, get_user_id_from_claims
from .models import (
    DatabaseConnectionCreate,
    DatabaseConnectionResponse,
    DatabaseConnectionUpdate,
    QueryExecuteRequest,
    TablePreviewRequest,
    UpdateVisibilityRequest,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/datasources",
    tags=["datasources"],
    dependencies=[Depends(require_active_user)],
)


@router.post("/connections", response_model=DatabaseConnectionResponse, dependencies=[Depends(require_scope("datasource:*:write"))])
async def create_connection(
    connection_data: DatabaseConnectionCreate,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new database connection."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_datasource_service()
        connection = service.create_connection(
            db=db,
            name=connection_data.name,
            description=connection_data.description,
            database_type=connection_data.database_type,
            connection_string=connection_data.connection_string,
            host=connection_data.host,
            port=connection_data.port,
            database_name=connection_data.database_name,
            username=connection_data.username,
            password=connection_data.password,
            use_ssl=connection_data.use_ssl,
            ssl_config=connection_data.ssl_config,
            connection_options=connection_data.connection_options,
            user_id=user_id,
            visible_to_groups=connection_data.visible_to_groups,
            read_only=connection_data.read_only,
        )

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] Datasource connection created by {_redact_email(user_email)}: "
            f"id={connection.id}, name={connection.name}, type={connection.database_type}"
        )

        return DatabaseConnectionResponse(
            id=connection.id,
            name=connection.name,
            description=connection.description,
            database_type=connection.database_type,
            host=connection.host,
            port=connection.port,
            database_name=connection.database_name,
            username=connection.username,
            use_ssl=connection.use_ssl,
            is_active=connection.is_active,
            read_only=connection.read_only,
            last_connection_test=connection.last_connection_test,
            last_connection_status=connection.last_connection_status,
            last_error_message=connection.last_error_message,
            query_count=connection.query_count,
            last_used=connection.last_used,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
            visible_to_groups=connection.visible_to_groups or [],
            user_id=connection.user_id,
            is_read_only=False,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATASOURCES] Failed to create connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create connection")


@router.get("/connections", response_model=List[DatabaseConnectionResponse], dependencies=[Depends(require_scope("datasource:*:read"))])
async def list_connections(
    active_only: bool = Query(True, description="Only return active connections"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    filter_type: str = Query("all", description="Filter: 'all', 'owned', or 'shared'"),
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List database connections for the authenticated user (owned + shared)."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_datasource_service()
        connections = service.list_connections(
            db=db,
            active_only=active_only,
            skip=skip,
            limit=limit,
            user_id=user_id,
            filter_type=filter_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATASOURCES] Error listing connections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list connections")

    return [
        DatabaseConnectionResponse(
            id=conn.id,
            name=conn.name,
            description=conn.description,
            database_type=conn.database_type,
            host=conn.host,
            port=conn.port,
            database_name=conn.database_name,
            username=conn.username,
            use_ssl=conn.use_ssl,
            is_active=conn.is_active,
            read_only=conn.read_only,
            last_connection_test=conn.last_connection_test,
            last_connection_status=conn.last_connection_status,
            last_error_message=conn.last_error_message,
            query_count=conn.query_count,
            last_used=conn.last_used,
            created_at=conn.created_at,
            updated_at=conn.updated_at,
            visible_to_groups=conn.visible_to_groups or [],
            user_id=conn.user_id,
            is_read_only=conn.user_id != user_id,
        )
        for conn in connections
    ]


@router.get("/connections/{connection_id}", response_model=DatabaseConnectionResponse, dependencies=[Depends(require_scope("datasource:*:read"))])
async def get_connection(
    connection_id: str,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific database connection."""
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    return DatabaseConnectionResponse(
        id=connection.id,
        name=connection.name,
        description=connection.description,
        database_type=connection.database_type,
        host=connection.host,
        port=connection.port,
        database_name=connection.database_name,
        username=connection.username,
        use_ssl=connection.use_ssl,
        is_active=connection.is_active,
        read_only=connection.read_only,
        last_connection_test=connection.last_connection_test,
        last_connection_status=connection.last_connection_status,
        last_error_message=connection.last_error_message,
        query_count=connection.query_count,
        last_used=connection.last_used,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        visible_to_groups=connection.visible_to_groups or [],
        user_id=connection.user_id,
        is_read_only=connection.user_id != user_id,
    )


@router.put("/connections/{connection_id}", response_model=DatabaseConnectionResponse, dependencies=[Depends(require_scope("datasource:*:write"))])
async def update_connection(
    connection_id: str,
    update_data: DatabaseConnectionUpdate,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update a database connection."""
    # Verify user owns this connection before allowing update (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    existing = service.get_connection_for_user(db, connection_id, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Convert update data to dict and remove None values
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

    connection = service.update_connection(
        db=db, connection_id=connection_id, **update_dict
    )

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Audit logging for security events
    user_email = current_user.get("email", "unknown")
    updated_fields = ", ".join(update_dict.keys())
    logger.info(
        f"[AUDIT] Datasource connection updated by {_redact_email(user_email)}: "
        f"id={connection_id}, fields={updated_fields}"
    )

    return DatabaseConnectionResponse(
        id=connection.id,
        name=connection.name,
        description=connection.description,
        database_type=connection.database_type,
        host=connection.host,
        port=connection.port,
        database_name=connection.database_name,
        username=connection.username,
        use_ssl=connection.use_ssl,
        is_active=connection.is_active,
        read_only=connection.read_only,
        last_connection_test=connection.last_connection_test,
        last_connection_status=connection.last_connection_status,
        last_error_message=connection.last_error_message,
        query_count=connection.query_count,
        last_used=connection.last_used,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        visible_to_groups=connection.visible_to_groups or [],
        user_id=connection.user_id,
        is_read_only=False,
    )


@router.patch(
    "/connections/{connection_id}/visibility",
    response_model=DatabaseConnectionResponse,
    dependencies=[Depends(require_scope("datasource:*:write"))],
)
async def update_connection_visibility(
    connection_id: str,
    request: UpdateVisibilityRequest,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update connection visibility groups. Only the connection owner can change visibility."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_datasource_service()
        connection = service.update_visibility(
            db=db,
            connection_id=connection_id,
            visible_to_groups=request.visible_to_groups,
            user_id=user_id,
        )

        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] Datasource connection visibility updated by {_redact_email(user_email)}: "
            f"id={connection_id}, groups={request.visible_to_groups}"
        )

        return DatabaseConnectionResponse(
            id=connection.id,
            name=connection.name,
            description=connection.description,
            database_type=connection.database_type,
            host=connection.host,
            port=connection.port,
            database_name=connection.database_name,
            username=connection.username,
            use_ssl=connection.use_ssl,
            is_active=connection.is_active,
            read_only=connection.read_only,
            last_connection_test=connection.last_connection_test,
            last_connection_status=connection.last_connection_status,
            last_error_message=connection.last_error_message,
            query_count=connection.query_count,
            last_used=connection.last_used,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
            visible_to_groups=connection.visible_to_groups or [],
            user_id=connection.user_id,
            is_read_only=False,
        )

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Only the owner can change visibility"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATASOURCES] Failed to update visibility: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update visibility")


@router.delete("/connections/{connection_id}", dependencies=[Depends(require_scope("datasource:*:write"))])
async def delete_connection(
    connection_id: str,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a database connection."""
    # Verify user owns this connection before allowing delete (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    existing = service.get_connection_for_user(db, connection_id, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    success = service.delete_connection(db, connection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Audit logging for security events
    user_email = current_user.get("email", "unknown")
    logger.info(
        f"[AUDIT] Datasource connection deleted by {_redact_email(user_email)}: "
        f"id={connection_id}"
    )

    return {"message": "Connection deleted successfully"}


@router.post("/connections/{connection_id}/test", dependencies=[Depends(require_scope("datasource:*:read"))])
async def test_connection(connection_id: str, db: Session = Depends(get_database)):
    """Test a database connection."""
    service = get_datasource_service()
    success, error_message = service.test_connection(db, connection_id)

    return {
        "success": success,
        "error_message": error_message,
        "tested_at": datetime.now(timezone.utc),
    }


@router.post("/connections/test", dependencies=[Depends(require_scope("datasource:*:read"))])
async def test_connection_config(
    connection_data: DatabaseConnectionCreate, db: Session = Depends(get_database)
):
    """Test a database connection configuration without saving it."""
    # Create a temporary connection object (not saved to DB)
    # Only include mapped fields; set encrypted credentials after
    temp_connection = DataSourceConnection(
        name="temp_test",
        description="Temporary connection for testing",
        database_type=connection_data.database_type,
        host=connection_data.host,
        port=connection_data.port,
        database_name=connection_data.database_name,
        username=connection_data.username,
        use_ssl=connection_data.use_ssl,
        ssl_config=connection_data.ssl_config,
        connection_options=connection_data.connection_options,
    )

    # Encrypt credentials if provided
    if connection_data.connection_string:
        temp_connection.encrypted_connection_string = (
            default_encryptor.encrypt_connection_string(
                connection_data.connection_string
            )
        )
    elif connection_data.password:
        temp_connection.encrypted_password = default_encryptor.encrypt_password(
            connection_data.password
        )

    # Test the connection
    try:
        conn_str = ConnectionStringBuilderFactory.build_connection_string(
            temp_connection
        )
        engine = create_engine(conn_str, connect_args={"connect_timeout": 10})

        with engine.connect() as conn:
            if connection_data.database_type == DatabaseType.POSTGRES:
                result = conn.execute(text("SELECT version()"))
            elif connection_data.database_type == DatabaseType.MYSQL:
                result = conn.execute(text("SELECT VERSION()"))
            elif connection_data.database_type == DatabaseType.MSSQL:
                result = conn.execute(text("SELECT @@VERSION"))
            elif connection_data.database_type == DatabaseType.SQLITE:
                result = conn.execute(text("SELECT sqlite_version()"))
            else:
                result = conn.execute(text("SELECT 1"))

            result.fetchone()

        return {
            "success": True,
            "error_message": None,
            "tested_at": datetime.now(timezone.utc),
        }

    except Exception as e:
        return {
            "success": False,
            "error_message": str(e),
            "tested_at": datetime.now(timezone.utc),
        }


@router.get("/connections/{connection_id}/tables", dependencies=[Depends(require_scope("datasource:*:read"))])
async def get_connection_tables(
    connection_id: str,
    force_refresh: bool = Query(False, description="Force refresh the cache"),
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get list of table names for a connection (fast operation)."""
    # Verify user has access to this connection (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    tables = service.get_table_list(db, connection_id, force_refresh)
    if tables is None:
        raise HTTPException(
            status_code=404,
            detail="Connection not found or table list retrieval failed",
        )

    return {"tables": tables}


@router.get("/connections/{connection_id}/tables/{table_name}/details", dependencies=[Depends(require_scope("datasource:*:read"))])
async def get_single_table_details(
    connection_id: str,
    table_name: str,
    force_refresh: bool = Query(False, description="Force refresh the cache"),
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get detailed information for a single table."""
    # Verify user has access to this connection (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    details = service.get_table_details(db, connection_id, table_name, force_refresh)
    if details is None:
        raise HTTPException(
            status_code=404, detail="Table not found or details retrieval failed"
        )

    return details


@router.get("/connections/{connection_id}/schema", dependencies=[Depends(require_scope("datasource:*:read"))])
async def get_connection_schema(
    connection_id: str,
    force_refresh: bool = Query(False, description="Force refresh the schema cache"),
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the database schema for a connection (legacy endpoint - use /tables for better performance)."""
    # Verify user has access to this connection (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    schema = service.get_schema(db, connection_id, force_refresh)
    if schema is None:
        raise HTTPException(
            status_code=404, detail="Connection not found or schema retrieval failed"
        )

    return schema


@router.get("/connections/{connection_id}/tables/{table_name}/columns", dependencies=[Depends(require_scope("datasource:*:read"))])
async def get_table_columns(
    connection_id: str,
    table_name: str,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get detailed column information for a specific table."""
    # Verify user has access to this connection (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    logger.info(
        f"Getting columns for table '{table_name}' in connection '{connection_id}'"
    )

    # Force refresh to ensure we have the latest schema
    schema = service.get_schema(db, connection_id, True)
    if schema is None:
        logger.error(f"Schema not found for connection '{connection_id}'")
        raise HTTPException(
            status_code=404, detail="Connection not found or schema retrieval failed"
        )

    logger.info(f"Available tables in schema: {list(schema.get('tables', {}).keys())}")

    table_info = schema.get("tables", {}).get(table_name)
    if not table_info:
        logger.error(f"Table '{table_name}' not found in schema")
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    # Format columns with additional metadata for the insert node
    columns = []
    for col in table_info.get("columns", []):
        columns.append(
            {
                "column_name": col["name"],
                "column_type": col["type"],
                "is_nullable": col["nullable"],
                "is_required": not col["nullable"] and not col.get("default"),
                "default_value": col.get("default"),
                "is_primary_key": col["name"] in table_info.get("primary_keys", []),
                "is_autoincrement": col.get("autoincrement", False),
            }
        )

    logger.info(
        f"Successfully retrieved {len(columns)} columns for table '{table_name}'"
    )

    return {
        "table_name": table_name,
        "columns": columns,
        "primary_keys": table_info.get("primary_keys", []),
        "foreign_keys": table_info.get("foreign_keys", []),
    }


@router.post("/connections/{connection_id}/query", dependencies=[Depends(require_scope("datasource:*:write"))])
async def execute_query(
    connection_id: str,
    request: QueryExecuteRequest,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute a query on a database connection."""
    # Verify user has access to this connection (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        result = await service.execute_query(
            db=db, connection_id=connection_id, query=request.query, limit=request.limit
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATASOURCES] Query execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Query execution failed")


@router.post("/connections/{connection_id}/preview", dependencies=[Depends(require_scope("datasource:*:read"))])
async def preview_table(
    connection_id: str,
    request: TablePreviewRequest,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a preview of table data."""
    # Verify user has access to this connection (ISG Finding 6430)
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()
    connection = service.get_connection_for_user(db, connection_id, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        result = await service.get_table_preview(
            db=db,
            connection_id=connection_id,
            table_name=request.table_name,
            limit=request.limit,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATASOURCES] Table preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Table preview failed")


@router.get("/ssl-config-schema/{database_type}")
async def get_ssl_config_schema(database_type: DatabaseType):
    """
    Get the SSL configuration schema for a specific database type.

    Returns the expected structure and available options for SSL configuration.
    """
    schemas = {
        DatabaseType.POSTGRES: {
            "description": "PostgreSQL SSL configuration",
            "options": {
                "sslmode": {
                    "type": "string",
                    "description": "SSL mode for PostgreSQL connection",
                    "enum": [
                        "disable",
                        "allow",
                        "prefer",
                        "require",
                        "verify-ca",
                        "verify-full",
                    ],
                    "default": "require",
                    "required": False,
                },
                "sslcert": {
                    "type": "string",
                    "description": "Path to client certificate file",
                    "required": False,
                },
                "sslkey": {
                    "type": "string",
                    "description": "Path to client private key file",
                    "required": False,
                },
                "sslrootcert": {
                    "type": "string",
                    "description": "Path to CA certificate file",
                    "required": False,
                },
            },
            "example": {
                "sslmode": "verify-full",
                "sslrootcert": "/path/to/ca-cert.pem",
            },
        },
        DatabaseType.MYSQL: {
            "description": "MySQL SSL configuration",
            "options": {
                "ssl_ca": {
                    "type": "string",
                    "description": "Path to CA certificate file",
                    "required": False,
                },
                "ssl_cert": {
                    "type": "string",
                    "description": "Path to client certificate file",
                    "required": False,
                },
                "ssl_key": {
                    "type": "string",
                    "description": "Path to client private key file",
                    "required": False,
                },
                "ssl_verify_cert": {
                    "type": "boolean",
                    "description": "Verify server certificate",
                    "default": True,
                    "required": False,
                },
                "ssl_verify_identity": {
                    "type": "boolean",
                    "description": "Verify server identity",
                    "default": False,
                    "required": False,
                },
            },
            "example": {"ssl_verify_cert": True},
            "note": "For remote MySQL connections (like db4free.net), SSL is typically negotiated automatically without certificate paths.",
        },
        DatabaseType.MSSQL: {
            "description": "Microsoft SQL Server SSL configuration",
            "options": {
                "driver": {
                    "type": "string",
                    "description": "ODBC driver to use",
                    "enum": [
                        "{ODBC Driver 17 for SQL Server}",
                        "{ODBC Driver 18 for SQL Server}",
                        "{SQL Server}",
                    ],
                    "default": "{ODBC Driver 17 for SQL Server}",
                    "required": False,
                },
                "encrypt": {
                    "type": "string",
                    "description": "Enable connection encryption",
                    "enum": ["yes", "no", "optional"],
                    "default": "yes",
                    "required": False,
                },
                "trustServerCertificate": {
                    "type": "string",
                    "description": "Trust the server certificate without validation",
                    "enum": ["yes", "no"],
                    "default": "no",
                    "required": False,
                },
                "certificate": {
                    "type": "string",
                    "description": "Path to certificate file",
                    "required": False,
                },
            },
            "example": {"encrypt": "yes", "trustServerCertificate": "no"},
        },
        DatabaseType.MONGODB: {
            "description": "MongoDB SSL configuration (experimental)",
            "options": {
                "ssl_ca": {
                    "type": "string",
                    "description": "Path to CA certificate file",
                    "required": False,
                },
                "ssl_certfile": {
                    "type": "string",
                    "description": "Path to client certificate file",
                    "required": False,
                },
                "ssl_keyfile": {
                    "type": "string",
                    "description": "Path to client private key file",
                    "required": False,
                },
                "ssl_cert_reqs": {
                    "type": "string",
                    "description": "Certificate verification requirement",
                    "enum": ["CERT_NONE", "CERT_OPTIONAL", "CERT_REQUIRED"],
                    "default": "CERT_REQUIRED",
                    "required": False,
                },
            },
            "example": {"ssl_cert_reqs": "CERT_REQUIRED"},
        },
        DatabaseType.ORACLE: {
            "description": "Oracle SSL configuration (experimental)",
            "options": {
                "service_name": {
                    "type": "string",
                    "description": "Oracle service name",
                    "required": False,
                },
                "wallet_location": {
                    "type": "string",
                    "description": "Path to Oracle Wallet directory",
                    "required": False,
                },
                "wallet_password": {
                    "type": "string",
                    "description": "Oracle Wallet password",
                    "required": False,
                },
            },
            "example": {"service_name": "ORCL"},
        },
        DatabaseType.SQLITE: {
            "description": "SQLite does not support SSL (file-based database)",
            "options": {},
            "example": {},
            "note": "SQLite is a local file-based database and does not use network connections or SSL.",
        },
    }

    schema = schemas.get(database_type)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"SSL schema not found for database type: {database_type}",
        )

    return schema
