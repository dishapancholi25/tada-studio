# Datasources API Module

## Overview

The Datasources API module provides comprehensive database connection management for AgenticStudio workflows. It enables
users to create, configure, and manage connections to external databases, test connectivity, inspect database schemas,
and execute queries. This module is essential for workflows that need to interact with external data sources.

**Location:** [backend/api/datasources/](../../backend/api/datasources/)

**Base Path:** `/api/datasources`

**Primary Responsibilities:**

- Database connection CRUD operations (Create, Read, Update, Delete)
- Connection testing and validation
- Database schema inspection and caching
- Query execution with safety controls
- SSL/TLS configuration management
- Multi-database type support (PostgreSQL, MySQL, MSSQL, SQLite, MongoDB, Oracle)
- User-scoped connection management

## Architecture

### Module Structure

```
backend/api/datasources/
├── __init__.py           # Module exports (router)
├── routes.py             # All API endpoints (620 lines)
├── models.py             # Pydantic request/response models (99 lines)
└── dependencies.py       # FastAPI dependencies (54 lines)
```

**File Descriptions:**

- **routes.py**: Contains all 15 API endpoints for connection management, schema inspection, query execution, and SSL
  configuration. Routes directly delegate to the datasource service layer.

- **models.py**: Defines Pydantic models for API requests and responses including:
  - `DatabaseConnectionCreate` - Creating new connections
  - `DatabaseConnectionUpdate` - Updating existing connections
  - `DatabaseConnectionResponse` - Connection metadata responses
  - `QueryExecuteRequest` - Query execution requests
  - `TablePreviewRequest` - Table preview requests

- **dependencies.py**: Provides FastAPI dependency injection functions:
  - `get_database()` - Database session management
  - `get_user_id_from_claims()` - User ID extraction from JWT

### Design Pattern

The Datasources API follows a **direct service delegation pattern**:

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
DataSource Service (backend.services.datasource)
    ↓
┌────────────────┬─────────────────┬────────────────┐
│                │                 │                │
ConnectionManager SchemaInspector  QueryExecutor
│                │                 │                │
└────────────────┴─────────────────┴────────────────┘
    ↓                   ↓                ↓
Database ORM      SQLAlchemy      Direct DB Query
```

**Service Layer Components:**

- **ConnectionManager**: Handles CRUD operations for database connections
- **ConnectionTester**: Tests database connectivity and validates configuration
- **SchemaInspector**: Retrieves and caches database schema information
- **QueryExecutor**: Executes SQL queries with safety validation
- **ConnectionStringBuilderFactory**: Builds database-specific connection strings

**Benefits:**

- Thin route handlers focus on HTTP concerns and validation
- Service layer provides reusable database connection logic
- Schema caching improves performance
- Separation of connection string building per database type
- Centralized security and encryption handling

## Authentication & Authorisation

### Authentication

All endpoints require authentication via **OAuth2-Proxy** JWT tokens.

**Required Headers:**

- `Authorization: Bearer <jwt_token>` - JWT token from OAuth2-Proxy

**User Extraction Pattern:**

```python
from backend.api.auth.dependencies import get_current_user

@router.post("/connections")
async def create_connection(
    connection_data: DatabaseConnectionCreate,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    # Extract user_id from JWT claims
    user_id = get_user_id_from_claims(current_user)
    # Use user_id for user-scoped operations
```

**JWT Claims Structure:**

```json
{
  "sub": "user-uuid-here",
  "email": "user@example.com",
  "name": "User Name",
  "exp": 1234567890
}
```

### Authorisation

**User-Scoped Data Access:**

All database connections are scoped to individual users:

- Users can only view and manage their own database connections
- Connection creation automatically associates with the authenticated user
- List operations filter by user_id to prevent cross-user access
- Get/update/delete operations validate ownership at the service layer

**Implementation Example:**

```python
# Creating a user-scoped connection
def create_connection(
    db: Session,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    user_id = get_user_id_from_claims(current_user)
    service = get_datasource_service()

    # Connection automatically linked to user_id
    connection = service.create_connection(
        db=db,
        name="My Database",
        database_type=DatabaseType.POSTGRES,
        # ... other fields
        user_id=user_id  # Enforces user ownership
    )
```

**Security Considerations:**

- Passwords and connection strings are encrypted before storage
- SSL/TLS configuration supported for secure connections
- Read-only mode available to prevent destructive operations
- Query validation prevents certain dangerous operations
- Connection credentials never returned in API responses

## API Endpoints

### Connection Management

#### `POST /api/datasources/connections`

Creates a new database connection configuration.

**Authentication:** Required

**Request Body:**

```json
{
  "name": "Production PostgreSQL",
  "description": "Main production database for customer data",
  "database_type": "postgres",
  "host": "db.example.com",
  "port": 5432,
  "database_name": "customers_db",
  "username": "app_user",
  "password": "secure_password_123",
  "use_ssl": true,
  "ssl_config": {
    "sslmode": "verify-full",
    "sslrootcert": "/path/to/ca-cert.pem"
  },
  "connection_options": {
    "pool_size": 10,
    "max_overflow": 20
  }
}
```

**Alternative: Using Connection String:**

```json
{
  "name": "Production PostgreSQL",
  "description": "Main production database",
  "database_type": "postgres",
  "connection_string": "postgresql://user:password@host:5432/dbname?sslmode=require"
}
```

**Response:**

```json
{
  "id": "conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "name": "Production PostgreSQL",
  "description": "Main production database for customer data",
  "database_type": "postgres",
  "host": "db.example.com",
  "port": 5432,
  "database_name": "customers_db",
  "username": "app_user",
  "use_ssl": true,
  "is_active": true,
  "read_only": false,
  "last_connection_test": null,
  "last_connection_status": null,
  "last_error_message": null,
  "query_count": 0,
  "last_used": null,
  "created_at": "2025-10-20T10:30:00Z",
  "updated_at": null
}
```

**Use Cases:**

- Setting up connections to external databases for workflow data access
- Configuring connections for data extraction workflows
- Establishing secure connections to production databases
- Creating read-only connections for reporting workflows

**Behaviour:**

- Validates that either connection_string OR individual fields (host, port, etc.) are provided
- Encrypts password and connection_string before storing in database
- Associates connection with authenticated user automatically
- Does NOT test the connection during creation (use `/test` endpoint)
- Returns connection metadata without sensitive credentials

**Validation:**

- `name` must be unique per user
- `database_type` must be one of: postgres, mysql, mssql, sqlite, mongodb, oracle
- Either `connection_string` OR `host`/`database_name` must be provided
- `port` must be valid for the database type
- `ssl_config` structure validated against database type requirements

**Errors:**

- `400 Bad Request` - Invalid database type or missing required fields
- `400 Bad Request` - Duplicate connection name for user
- `500 Internal Server Error` - Database storage failure

---

#### `GET /api/datasources/connections`

Lists all database connections for the authenticated user.

**Authentication:** Required

**Query Parameters:**

- `active_only` - Only return active connections (default: true)
- `skip` - Number of records to skip for pagination (default: 0)
- `limit` - Maximum number of records to return (default: 100)

**Request Example:**

```
GET /api/datasources/connections?active_only=true&skip=0&limit=50
```

**Response:**

```json
[
  {
    "id": "conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "name": "Production PostgreSQL",
    "description": "Main production database",
    "database_type": "postgres",
    "host": "db.example.com",
    "port": 5432,
    "database_name": "customers_db",
    "username": "app_user",
    "use_ssl": true,
    "is_active": true,
    "read_only": false,
    "last_connection_test": "2025-10-20T09:15:00Z",
    "last_connection_status": "success",
    "last_error_message": null,
    "query_count": 47,
    "last_used": "2025-10-20T10:25:00Z",
    "created_at": "2025-10-19T14:30:00Z",
    "updated_at": "2025-10-20T09:15:00Z"
  },
  {
    "id": "conn_b2c3d4e5-f6a7-5b6c-9d0e-1f2a3b4c5d6e",
    "name": "Analytics MySQL",
    "description": "Analytics database for reporting",
    "database_type": "mysql",
    "host": "analytics.example.com",
    "port": 3306,
    "database_name": "analytics",
    "username": "readonly_user",
    "use_ssl": false,
    "is_active": true,
    "read_only": true,
    "last_connection_test": "2025-10-20T08:00:00Z",
    "last_connection_status": "success",
    "last_error_message": null,
    "query_count": 152,
    "last_used": "2025-10-20T10:20:00Z",
    "created_at": "2025-10-18T11:00:00Z",
    "updated_at": "2025-10-20T08:00:00Z"
  }
]
```

**Use Cases:**

- Displaying available database connections in UI
- Selecting a connection for workflow configuration
- Monitoring connection health and usage statistics
- Auditing database connection inventory

**Behaviour:**

- Automatically filters connections by authenticated user
- Excludes inactive connections when `active_only=true`
- Orders results by creation date (newest first)
- Returns empty array if no connections found
- Includes connection statistics (query_count, last_used)

**Performance:**

- Fast operation (simple database query)
- Pagination recommended for users with many connections
- Results do not include full schema information

---

#### `GET /api/datasources/connections/{connection_id}`

Retrieves details for a specific database connection.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection

**Request Example:**

```
GET /api/datasources/connections/conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
```

**Response:**

```json
{
  "id": "conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "name": "Production PostgreSQL",
  "description": "Main production database",
  "database_type": "postgres",
  "host": "db.example.com",
  "port": 5432,
  "database_name": "customers_db",
  "username": "app_user",
  "use_ssl": true,
  "is_active": true,
  "read_only": false,
  "last_connection_test": "2025-10-20T09:15:00Z",
  "last_connection_status": "success",
  "last_error_message": null,
  "query_count": 47,
  "last_used": "2025-10-20T10:25:00Z",
  "created_at": "2025-10-19T14:30:00Z",
  "updated_at": "2025-10-20T09:15:00Z"
}
```

**Use Cases:**

- Viewing connection details in UI
- Retrieving connection configuration for editing
- Checking connection health status
- Debugging connection issues

**Behaviour:**

- Returns connection metadata without sensitive credentials
- Includes last test status and error messages
- Shows usage statistics (query_count, last_used)

**Errors:**

- `404 Not Found` - Connection does not exist or user lacks access

---

#### `PUT /api/datasources/connections/{connection_id}`

Updates an existing database connection configuration.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection to update

**Request Body (all fields optional):**

```json
{
  "name": "Production PostgreSQL - Updated",
  "description": "Updated description",
  "host": "new-db.example.com",
  "port": 5433,
  "password": "new_password_456",
  "is_active": true,
  "read_only": true,
  "ssl_config": {
    "sslmode": "require"
  }
}
```

**Response:**

```json
{
  "id": "conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "name": "Production PostgreSQL - Updated",
  "description": "Updated description",
  "database_type": "postgres",
  "host": "new-db.example.com",
  "port": 5433,
  "database_name": "customers_db",
  "username": "app_user",
  "use_ssl": true,
  "is_active": true,
  "read_only": true,
  "last_connection_test": "2025-10-20T09:15:00Z",
  "last_connection_status": "success",
  "last_error_message": null,
  "query_count": 47,
  "last_used": "2025-10-20T10:25:00Z",
  "created_at": "2025-10-19T14:30:00Z",
  "updated_at": "2025-10-20T10:30:00Z"
}
```

**Use Cases:**

- Updating database credentials after password rotation
- Changing connection host after database migration
- Enabling/disabling read-only mode for safety
- Activating or deactivating connections

**Behaviour:**

- Only updates fields provided in request body (partial update)
- Null values are ignored (use empty string to clear fields)
- Encrypts new password if provided
- Updates `updated_at` timestamp
- Does not re-test connection automatically

**Validation:**

- Cannot change `database_type` after creation
- `name` must remain unique per user if changed
- Invalid field values rejected with 400 error

**Errors:**

- `404 Not Found` - Connection does not exist
- `400 Bad Request` - Invalid field values

---

#### `DELETE /api/datasources/connections/{connection_id}`

Deletes a database connection.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection to delete

**Request Example:**

```
DELETE /api/datasources/connections/conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
```

**Response:**

```json
{
  "message": "Connection deleted successfully"
}
```

**Use Cases:**

- Removing obsolete database connections
- Cleaning up after database decommissioning
- Removing connections with invalid credentials

**Behaviour:**

- Permanently deletes the connection record
- Clears cached schema information for the connection
- Does not affect historical query logs or execution history
- Cannot be undone

**Errors:**

- `404 Not Found` - Connection does not exist

**Important Notes:**

- Workflows referencing this connection will fail until reconfigured
- Consider deactivating (`is_active=false`) instead of deleting if connection might be needed later

---

### Connection Testing

#### `POST /api/datasources/connections/{connection_id}/test`

Tests connectivity to a configured database connection.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection to test

**Request Example:**

```
POST /api/datasources/connections/conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d/test
```

**Response (Success):**

```json
{
  "success": true,
  "error_message": null,
  "tested_at": "2025-10-20T10:35:42Z"
}
```

**Response (Failure):**

```json
{
  "success": false,
  "error_message": "FATAL: password authentication failed for user \"app_user\"",
  "tested_at": "2025-10-20T10:36:15Z"
}
```

**Use Cases:**

- Verifying database connection after creation
- Diagnosing connection issues
- Checking if credentials are still valid
- Validating network connectivity to database

**Behaviour:**

- Establishes actual connection to database
- Executes simple query to verify connectivity
- Updates connection's `last_connection_test`, `last_connection_status`, and `last_error_message` fields
- Times out after 10 seconds
- Does not cache results

**Performance:**

- Medium speed operation (network dependent)
- Typical response time: 100ms - 5 seconds
- Can be slow for remote databases or network issues

**Errors:**

- Returns success=false with error_message for connection failures
- Does not throw HTTP errors unless connection record not found

---

#### `POST /api/datasources/connections/test`

Tests a database connection configuration without saving it to the database.

**Authentication:** Required

**Request Body:**

```json
{
  "name": "temp_test",
  "database_type": "postgres",
  "host": "test-db.example.com",
  "port": 5432,
  "database_name": "test_db",
  "username": "test_user",
  "password": "test_password",
  "use_ssl": true,
  "ssl_config": {
    "sslmode": "require"
  }
}
```

**Response (Success):**

```json
{
  "success": true,
  "error_message": null,
  "tested_at": "2025-10-20T10:40:00Z"
}
```

**Response (Failure):**

```json
{
  "success": false,
  "error_message": "could not translate host name \"test-db.example.com\" to address: Name or service not known",
  "tested_at": "2025-10-20T10:40:05Z"
}
```

**Use Cases:**

- Validating connection details before creating connection
- Testing new database credentials
- Troubleshooting connection configuration
- Pre-flight validation in connection creation UI

**Behaviour:**

- Creates temporary connection object (not persisted)
- Tests actual database connectivity
- Executes database-specific version query
- Timeout after 10 seconds
- No side effects on database

**Database-Specific Test Queries:**

- PostgreSQL: `SELECT version()`
- MySQL: `SELECT VERSION()`
- MSSQL: `SELECT @@VERSION`
- SQLite: `SELECT sqlite_version()`
- Other: `SELECT 1`

**Performance:**

- Medium speed operation (100ms - 5 seconds)
- Network dependent

---

### Schema Inspection

#### `GET /api/datasources/connections/{connection_id}/tables`

Retrieves list of table names for a database connection (optimised fast operation).

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection

**Query Parameters:**

- `force_refresh` - Force refresh the cache (default: false)

**Request Example:**

```
GET /api/datasources/connections/conn_a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d/tables?force_refresh=false
```

**Response:**

```json
{
  "tables": [
    "customers",
    "orders",
    "products",
    "order_items",
    "categories",
    "users",
    "sessions",
    "audit_log"
  ]
}
```

**Use Cases:**

- Populating table selection dropdowns in UI
- Quick discovery of available tables
- Workflow configuration for table-specific operations
- Validating table existence before queries

**Behaviour:**

- Returns simple array of table names (no column details)
- Results cached for performance (24-hour default TTL)
- `force_refresh=true` invalidates cache and fetches fresh data
- Excludes system tables and views (database-dependent filtering)
- Orders tables alphabetically

**Performance:**

- Very fast operation when cached (< 50ms)
- Medium speed when not cached (500ms - 3 seconds)
- Use this endpoint instead of `/schema` for better performance

**Errors:**

- `404 Not Found` - Connection not found or retrieval failed

---

#### `GET /api/datasources/connections/{connection_id}/tables/{table_name}/details`

Retrieves detailed information for a single table including columns, types, and constraints.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection
- `table_name` - Name of the table

**Query Parameters:**

- `force_refresh` - Force refresh the cache (default: false)

**Request Example:**

```
GET /api/datasources/connections/conn_abc123/tables/customers/details
```

**Response:**

```json
{
  "table_name": "customers",
  "columns": [
    {
      "name": "id",
      "type": "INTEGER",
      "nullable": false,
      "default": "nextval('customers_id_seq')",
      "autoincrement": true
    },
    {
      "name": "email",
      "type": "VARCHAR(255)",
      "nullable": false,
      "default": null,
      "autoincrement": false
    },
    {
      "name": "first_name",
      "type": "VARCHAR(100)",
      "nullable": true,
      "default": null,
      "autoincrement": false
    },
    {
      "name": "last_name",
      "type": "VARCHAR(100)",
      "nullable": true,
      "default": null,
      "autoincrement": false
    },
    {
      "name": "created_at",
      "type": "TIMESTAMP",
      "nullable": false,
      "default": "CURRENT_TIMESTAMP",
      "autoincrement": false
    }
  ],
  "primary_keys": ["id"],
  "foreign_keys": [],
  "indexes": [
    {
      "name": "idx_customers_email",
      "columns": ["email"],
      "unique": true
    }
  ],
  "row_count_estimate": 45231
}
```

**Use Cases:**

- Building dynamic forms for data insertion
- Validating query column references
- Understanding table structure for workflow design
- Generating documentation for database schema

**Behaviour:**

- Returns comprehensive table metadata
- Cached for performance (use `force_refresh` for latest)
- Includes column types, nullability, defaults, and constraints
- Provides primary key and foreign key information
- Row count is estimated (not exact)

**Performance:**

- Fast when cached (< 100ms)
- Medium speed when not cached (1-3 seconds for large tables)

**Errors:**

- `404 Not Found` - Table not found or connection invalid

---

#### `GET /api/datasources/connections/{connection_id}/schema`

Retrieves complete database schema including all tables and their details (legacy endpoint).

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection

**Query Parameters:**

- `force_refresh` - Force refresh the schema cache (default: false)

**Request Example:**

```
GET /api/datasources/connections/conn_abc123/schema?force_refresh=false
```

**Response:**

```json
{
  "database_name": "customers_db",
  "database_type": "postgres",
  "tables": {
    "customers": {
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "nullable": false,
          "default": "nextval('customers_id_seq')",
          "autoincrement": true
        },
        {
          "name": "email",
          "type": "VARCHAR(255)",
          "nullable": false,
          "default": null,
          "autoincrement": false
        }
      ],
      "primary_keys": ["id"],
      "foreign_keys": [],
      "indexes": [
        {
          "name": "idx_customers_email",
          "columns": ["email"],
          "unique": true
        }
      ]
    },
    "orders": {
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "nullable": false,
          "default": "nextval('orders_id_seq')",
          "autoincrement": true
        },
        {
          "name": "customer_id",
          "type": "INTEGER",
          "nullable": false,
          "default": null,
          "autoincrement": false
        },
        {
          "name": "total_amount",
          "type": "NUMERIC(10,2)",
          "nullable": false,
          "default": null,
          "autoincrement": false
        }
      ],
      "primary_keys": ["id"],
      "foreign_keys": [
        {
          "column": "customer_id",
          "referenced_table": "customers",
          "referenced_column": "id"
        }
      ],
      "indexes": []
    }
  },
  "cached_at": "2025-10-20T10:00:00Z"
}
```

**Use Cases:**

- Comprehensive schema analysis
- Database documentation generation
- Initial schema discovery for new connections
- Database migration planning

**Behaviour:**

- Returns complete schema for all tables
- Heavily cached (24-hour default TTL)
- `force_refresh=true` forces fresh retrieval
- Can be slow for large databases
- Includes relationships between tables

**Performance:**

- Fast when cached (< 200ms)
- **Slow when not cached** (5-30 seconds for large databases)
- Not recommended for frequent calls
- **Use `/tables` and `/tables/{table_name}/details` for better performance**

**Deprecation Notice:**
This endpoint is considered legacy. For better performance, use:

- `/api/datasources/connections/{connection_id}/tables` - for table list
- `/api/datasources/connections/{connection_id}/tables/{table_name}/details` - for individual table details

**Errors:**

- `404 Not Found` - Connection not found or schema retrieval failed

---

#### `GET /api/datasources/connections/{connection_id}/tables/{table_name}/columns`

Retrieves detailed column information for a specific table, formatted for insert operations.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection
- `table_name` - Name of the table

**Request Example:**

```
GET /api/datasources/connections/conn_abc123/tables/customers/columns
```

**Response:**

```json
{
  "table_name": "customers",
  "columns": [
    {
      "column_name": "id",
      "column_type": "INTEGER",
      "is_nullable": false,
      "is_required": false,
      "default_value": "nextval('customers_id_seq')",
      "is_primary_key": true,
      "is_autoincrement": true
    },
    {
      "column_name": "email",
      "column_type": "VARCHAR(255)",
      "is_nullable": false,
      "is_required": true,
      "default_value": null,
      "is_primary_key": false,
      "is_autoincrement": false
    },
    {
      "column_name": "first_name",
      "column_type": "VARCHAR(100)",
      "is_nullable": true,
      "is_required": false,
      "default_value": null,
      "is_primary_key": false,
      "is_autoincrement": false
    },
    {
      "column_name": "created_at",
      "column_type": "TIMESTAMP",
      "is_nullable": false,
      "is_required": false,
      "default_value": "CURRENT_TIMESTAMP",
      "is_primary_key": false,
      "is_autoincrement": false
    }
  ],
  "primary_keys": ["id"],
  "foreign_keys": []
}
```

**Use Cases:**

- Building insert/update forms with proper validation
- Determining which fields are required for data insertion
- Understanding field constraints for workflow nodes
- Validating data before database operations

**Behaviour:**

- Forces schema refresh to ensure latest column information
- Computes `is_required` based on nullable and default values
- Identifies primary keys and autoincrement columns
- Formatted specifically for insert node UI requirements

**Column Metadata:**

- `is_required`: true if NOT nullable AND no default value
- `is_primary_key`: true if column is part of primary key
- `is_autoincrement`: true for auto-generated values (skip in inserts)

**Performance:**

- Medium speed (always refreshes schema, 1-3 seconds)

**Errors:**

- `404 Not Found` - Connection or table not found

---

### Query Execution

#### `POST /api/datasources/connections/{connection_id}/query`

Executes a SQL query on a database connection.

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection

**Request Body:**

```json
{
  "query": "SELECT id, email, first_name, last_name FROM customers WHERE created_at > '2025-10-01' ORDER BY created_at DESC",
  "limit": 100
}
```

**Response:**

```json
{
  "columns": ["id", "email", "first_name", "last_name"],
  "rows": [
    [1523, "alice@example.com", "Alice", "Johnson"],
    [1524, "bob@example.com", "Bob", "Smith"],
    [1525, "charlie@example.com", "Charlie", "Davis"]
  ],
  "row_count": 3,
  "executed_at": "2025-10-20T10:45:00Z",
  "execution_time_ms": 45
}
```

**Use Cases:**

- Executing custom SQL queries from workflows
- Data extraction for processing
- Validation queries before data operations
- Ad-hoc data analysis

**Behaviour:**

- Executes the provided SQL query against the database
- Enforces row limit (default: 1000, max configurable)
- Validates query for safety (read-only restrictions if enabled)
- Updates connection's `query_count` and `last_used` fields
- Returns results in columnar format

**Validation:**

- Checks if connection is read-only
- Validates query syntax (database-dependent)
- Blocks certain dangerous operations in read-only mode
- Enforces maximum row limit

**Safety Features:**

- Read-only connections reject INSERT/UPDATE/DELETE/DROP/TRUNCATE
- Query timeout prevents long-running queries
- Row limit prevents memory exhaustion
- Parameterised queries recommended (not shown in example)

**Performance:**

- Depends on query complexity and database
- Typical range: 50ms - 30 seconds
- Large result sets may be slow
- Consider pagination for large datasets

**Errors:**

- `400 Bad Request` - Invalid query syntax or disallowed operation
- `500 Internal Server Error` - Query execution failure, connection timeout

**Important Notes:**

- For read-only connections, only SELECT queries allowed
- Query results limited to prevent memory issues
- No transaction support (each query auto-committed)
- Consider using table preview for simple data viewing

---

#### `POST /api/datasources/connections/{connection_id}/preview`

Retrieves a preview of table data (convenience endpoint for SELECT queries).

**Authentication:** Required

**Path Parameters:**

- `connection_id` - UUID of the connection

**Request Body:**

```json
{
  "table_name": "customers",
  "limit": 50
}
```

**Response:**

```json
{
  "table_name": "customers",
  "columns": ["id", "email", "first_name", "last_name", "created_at"],
  "rows": [
    [1, "alice@example.com", "Alice", "Johnson", "2025-09-15T08:30:00Z"],
    [2, "bob@example.com", "Bob", "Smith", "2025-09-16T14:20:00Z"],
    [3, "charlie@example.com", "Charlie", "Davis", "2025-09-17T10:45:00Z"]
  ],
  "row_count": 3,
  "total_rows_estimate": 45231,
  "previewed_at": "2025-10-20T10:50:00Z"
}
```

**Use Cases:**

- Quick preview of table data in UI
- Validating table contents before operations
- Inspecting sample data for workflow design
- Debugging data issues

**Behaviour:**

- Executes simple `SELECT * FROM table_name LIMIT {limit}`
- Returns all columns from the table
- Does not support WHERE clauses or complex queries
- Provides estimated total row count (database-dependent)
- Default limit: 100 rows

**Performance:**

- Fast operation (< 1 second typically)
- Limit reduces data transfer and processing time

**Errors:**

- `400 Bad Request` - Invalid table name
- `500 Internal Server Error` - Table preview failed

---

### SSL Configuration

#### `GET /api/datasources/ssl-config-schema/{database_type}`

Retrieves the SSL configuration schema for a specific database type.

**Authentication:** None Required

**Path Parameters:**

- `database_type` - One of: postgres, mysql, mssql, sqlite, mongodb, oracle

**Request Example:**

```
GET /api/datasources/ssl-config-schema/postgres
```

**Response (PostgreSQL):**

```json
{
  "description": "PostgreSQL SSL configuration",
  "options": {
    "sslmode": {
      "type": "string",
      "description": "SSL mode for PostgreSQL connection",
      "enum": ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
      "default": "require",
      "required": false
    },
    "sslcert": {
      "type": "string",
      "description": "Path to client certificate file",
      "required": false
    },
    "sslkey": {
      "type": "string",
      "description": "Path to client private key file",
      "required": false
    },
    "sslrootcert": {
      "type": "string",
      "description": "Path to CA certificate file",
      "required": false
    }
  },
  "example": {
    "sslmode": "verify-full",
    "sslrootcert": "/path/to/ca-cert.pem"
  }
}
```

**Response (MySQL):**

```json
{
  "description": "MySQL SSL configuration",
  "options": {
    "ssl_ca": {
      "type": "string",
      "description": "Path to CA certificate file",
      "required": false
    },
    "ssl_cert": {
      "type": "string",
      "description": "Path to client certificate file",
      "required": false
    },
    "ssl_key": {
      "type": "string",
      "description": "Path to client private key file",
      "required": false
    },
    "ssl_verify_cert": {
      "type": "boolean",
      "description": "Verify server certificate",
      "default": true,
      "required": false
    },
    "ssl_verify_identity": {
      "type": "boolean",
      "description": "Verify server identity",
      "default": false,
      "required": false
    }
  },
  "example": {
    "ssl_verify_cert": true
  },
  "note": "For remote MySQL connections (like db4free.net), SSL is typically negotiated automatically without certificate paths."
}
```

**Response (SQLite):**

```json
{
  "description": "SQLite does not support SSL (file-based database)",
  "options": {},
  "example": {},
  "note": "SQLite is a local file-based database and does not use network connections or SSL."
}
```

**Use Cases:**

- Building SSL configuration forms in UI
- Understanding SSL options for specific database type
- Validating SSL configuration before connection creation
- Documentation for database connection setup

**Behaviour:**

- Returns database-specific SSL schema
- Includes field types, descriptions, and examples
- Shows available options and defaults
- Provides guidance notes for each database type

**Supported Database Types:**

- **PostgreSQL**: Full SSL support with certificate verification
- **MySQL**: SSL with optional certificate paths
- **MSSQL**: Encryption and certificate trust options
- **MongoDB**: Experimental SSL support
- **Oracle**: Wallet-based SSL configuration
- **SQLite**: No SSL (local file-based)

**Errors:**

- `404 Not Found` - Invalid database type

---

## Error Handling

### Error Response Format

All error responses follow a consistent structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors (422):

```json
{
  "detail": [
    {
      "loc": ["body", "database_type"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

### Common Error Codes

#### 400 Bad Request

- Invalid database type specified
- Missing required fields (connection_string OR host/database_name)
- Duplicate connection name for user
- Invalid query syntax
- Disallowed operation on read-only connection
- Invalid table name

**When it occurs:**

```python
# Example: Creating connection with duplicate name
POST /api/datasources/connections
{
  "name": "Existing Connection Name",  # Already exists
  "database_type": "postgres",
  ...
}

# Response
{
  "detail": "Connection with name 'Existing Connection Name' already exists"
}
```

#### 401 Unauthorized

- Missing or invalid JWT token
- Expired authentication token
- User not found in database

**When it occurs:**

```bash
# Missing Authorization header
curl -X GET http://api.example.com/api/datasources/connections

# Response
{
  "detail": "Not authenticated"
}
```

#### 404 Not Found

- Connection ID does not exist
- User lacks access to connection
- Table not found in database schema
- SSL schema not found for database type

**When it occurs:**

```python
# Example: Getting non-existent connection
GET /api/datasources/connections/conn_nonexistent123

# Response
{
  "detail": "Connection not found"
}
```

#### 422 Unprocessable Entity

- Request body validation failure
- Invalid field types
- Missing required request fields

**When it occurs:**

```python
# Example: Invalid database_type enum value
POST /api/datasources/connections
{
  "name": "Test",
  "database_type": "invalid_db_type"  # Not in enum
}

# Response
{
  "detail": [
    {
      "loc": ["body", "database_type"],
      "msg": "value is not a valid enumeration member; permitted: 'postgres', 'mysql', 'mssql', 'sqlite', 'mongodb', 'oracle'",
      "type": "type_error.enum"
    }
  ]
}
```

#### 500 Internal Server Error

- Database storage failure
- Connection string building failure
- Query execution error
- Unexpected exceptions in service layer

**When it occurs:**

```python
# Example: Database connection failure
POST /api/datasources/connections/conn_abc123/query
{
  "query": "SELECT * FROM nonexistent_table"
}

# Response
{
  "detail": "Query execution failed: relation \"nonexistent_table\" does not exist"
}
```

### Error Handling Example

**Python Client Example:**

```python
import requests

def create_datasource_connection(token, connection_config):
    """Create a datasource connection with proper error handling."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.example.com/api/datasources/connections"

    try:
        response = requests.post(url, json=connection_config, headers=headers)
        response.raise_for_status()

        connection = response.json()
        print(f"✓ Connection created: {connection['id']}")

        # Test the connection
        test_response = requests.post(
            f"{url}/{connection['id']}/test",
            headers=headers
        )
        test_response.raise_for_status()

        test_result = test_response.json()
        if test_result["success"]:
            print(f"✓ Connection test successful")
            return connection
        else:
            print(f"⚠ Connection created but test failed: {test_result['error_message']}")
            return connection

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print(f"✗ Invalid request: {e.response.json()['detail']}")
        elif e.response.status_code == 401:
            print(f"✗ Authentication failed - check your token")
        elif e.response.status_code == 404:
            print(f"✗ Resource not found: {e.response.json()['detail']}")
        elif e.response.status_code == 422:
            errors = e.response.json()['detail']
            print(f"✗ Validation errors:")
            for error in errors:
                print(f"  - {error['loc']}: {error['msg']}")
        else:
            print(f"✗ Server error: {e.response.json()['detail']}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error: {e}")
        raise

# Usage
connection_config = {
    "name": "Production Database",
    "database_type": "postgres",
    "host": "db.example.com",
    "port": 5432,
    "database_name": "mydb",
    "username": "app_user",
    "password": "secure_password",
    "use_ssl": True,
    "ssl_config": {"sslmode": "require"}
}

try:
    connection = create_datasource_connection("your-jwt-token", connection_config)
except Exception:
    print("Failed to create connection")
```

**JavaScript Client Example:**

```javascript
async function createDatasourceConnection(token, connectionConfig) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  try {
    // Create connection
    const response = await fetch('https://api.example.com/api/datasources/connections', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(connectionConfig)
    });

    if (!response.ok) {
      const error = await response.json();

      switch (response.status) {
        case 400:
          throw new Error(`Invalid request: ${error.detail}`);
        case 401:
          throw new Error('Authentication failed - check your token');
        case 422:
          const validationErrors = error.detail
            .map(e => `${e.loc.join('.')}: ${e.msg}`)
            .join(', ');
          throw new Error(`Validation errors: ${validationErrors}`);
        case 500:
          throw new Error(`Server error: ${error.detail}`);
        default:
          throw new Error(`HTTP ${response.status}: ${error.detail}`);
      }
    }

    const connection = await response.json();
    console.log('✓ Connection created:', connection.id);

    // Test connection
    const testResponse = await fetch(
      `https://api.example.com/api/datasources/connections/${connection.id}/test`,
      { method: 'POST', headers: headers }
    );

    const testResult = await testResponse.json();
    if (testResult.success) {
      console.log('✓ Connection test successful');
    } else {
      console.warn('⚠ Connection created but test failed:', testResult.error_message);
    }

    return connection;

  } catch (error) {
    console.error('✗ Failed to create connection:', error.message);
    throw error;
  }
}

// Usage
const connectionConfig = {
  name: "Production Database",
  database_type: "postgres",
  host: "db.example.com",
  port: 5432,
  database_name: "mydb",
  username: "app_user",
  password: "secure_password",
  use_ssl: true,
  ssl_config: { sslmode: "require" }
};

try {
  const connection = await createDatasourceConnection('your-jwt-token', connectionConfig);
} catch (error) {
  // Handle error appropriately
}
```

---

## Integration with Services Layer

### Dependency Flow

```
API Route (routes.py)
    ↓
DataSource Service (services/datasource/service.py)
    ↓
    ├─→ ConnectionManager (services/datasource/connection/manager.py)
    │       ↓
    │   ConnectionStringBuilderFactory (connection/builders/factory.py)
    │       ↓
    │   Database-specific builders (postgres.py, mysql.py, etc.)
    │
    ├─→ ConnectionTester (services/datasource/connection/tester.py)
    │       ↓
    │   SQLAlchemy Engine (test connection)
    │
    ├─→ SchemaInspector (services/datasource/schema/inspector.py)
    │       ↓
    │   Schema Cache (schema/cache.py)
    │       ↓
    │   SQLAlchemy Inspector (metadata reflection)
    │
    └─→ QueryExecutor (services/datasource/query/executor.py)
            ↓
        QueryValidator (query/validator.py)
            ↓
        QueryFormatter (query/formatters.py)
            ↓
        SQLAlchemy Engine (execute query)
```

### Example Integration

**Complete Flow Example:**

```python
# 1. Route Handler (routes.py)
from backend.services.datasource import get_datasource_service

@router.post("/connections/{connection_id}/query")
async def execute_query(
    connection_id: str,
    request: QueryExecuteRequest,
    db: Session = Depends(get_database),
):
    """Execute a query on a database connection."""
    try:
        # Delegate to service layer
        service = get_datasource_service()
        result = await service.execute_query(
            db=db,
            connection_id=connection_id,
            query=request.query,
            limit=request.limit
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )


# 2. Service Layer (services/datasource/service.py)
class DataSourceService:
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.query_executor = QueryExecutor()

    async def execute_query(
        self,
        db: Session,
        connection_id: str,
        query: str,
        limit: int = 1000
    ):
        """Execute query using QueryExecutor."""
        # Get connection from manager
        connection = self.connection_manager.get_connection(db, connection_id)
        if not connection:
            raise ValueError("Connection not found")

        # Delegate to query executor
        return await self.query_executor.execute_query(
            db=db,
            connection=connection,
            query=query,
            limit=limit
        )


# 3. Query Executor (services/datasource/query/executor.py)
class QueryExecutor:
    def __init__(self):
        self.validator = QueryValidator()
        self.formatter = QueryFormatter()

    async def execute_query(self, db, connection, query, limit):
        """Execute and format query results."""
        # Validate query
        self.validator.validate_query(query, connection.read_only)

        # Build connection string
        conn_str = ConnectionStringBuilderFactory.build_connection_string(
            connection
        )

        # Execute query
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchmany(limit)

        # Format results
        formatted = self.formatter.format_results(result, rows)

        # Update usage statistics
        connection.query_count += 1
        connection.last_used = datetime.now(timezone.utc)
        db.commit()

        return formatted
```

### Services Used

**1. DataSourceService** ([backend/services/datasource/service.py](../../backend/services/datasource/service.py:1))

- Main orchestrator for all datasource operations
- Coordinates between connection, schema, and query services
- Provides high-level API for datasource management

**2. ConnectionManager
** ([backend/services/datasource/connection/manager.py](../../backend/services/datasource/connection/manager.py:1))

- Handles CRUD operations for database connections
- Encrypts/decrypts credentials
- Manages connection lifecycle
- Enforces user-scoped access

**3. ConnectionTester
** ([backend/services/datasource/connection/tester.py](../../backend/services/datasource/connection/tester.py:1))

- Tests database connectivity
- Validates connection configuration
- Updates connection test status
- Handles connection errors gracefully

**4. SchemaInspector
** ([backend/services/datasource/schema/inspector.py](../../backend/services/datasource/schema/inspector.py:1))

- Retrieves database schema metadata
- Inspects tables, columns, constraints
- Uses SQLAlchemy reflection
- Caches schema for performance

**5. SchemaCache** ([backend/services/datasource/schema/cache.py](../../backend/services/datasource/schema/cache.py:1))

- Caches database schema information
- Reduces database round-trips
- Configurable TTL (time-to-live)
- Invalidation on demand

**6. QueryExecutor
** ([backend/services/datasource/query/executor.py](../../backend/services/datasource/query/executor.py:1))

- Executes SQL queries safely
- Enforces row limits
- Tracks query statistics
- Handles query timeouts

**7. QueryValidator
** ([backend/services/datasource/query/validator.py](../../backend/services/datasource/query/validator.py:1))

- Validates SQL query syntax
- Enforces read-only restrictions
- Blocks dangerous operations (DROP, TRUNCATE)
- Prevents SQL injection (when using parameterised queries)

**8. QueryFormatter
** ([backend/services/datasource/query/formatters.py](../../backend/services/datasource/query/formatters.py:1))

- Formats query results to JSON
- Converts database types to Python types
- Handles special data types (dates, decimals, etc.)
- Optimises result serialisation

**9. ConnectionStringBuilderFactory
** ([backend/services/datasource/connection/builders/factory.py](../../backend/services/datasource/connection/builders/factory.py:1))

- Factory for database-specific connection string builders
- Delegates to appropriate builder based on database type
- Handles SSL configuration
- Decrypts credentials securely

**10. Database-Specific Builders
** ([backend/services/datasource/connection/builders/](../../backend/services/datasource/connection/builders/))

- PostgreSQL, MySQL, MSSQL, SQLite, MongoDB, Oracle builders
- Each handles database-specific connection string format
- Manages SSL/TLS configuration per database type
- Applies database-specific connection options

---

## Usage Examples

### Complete Database Connection Workflow

This example demonstrates a complete workflow: creating a connection, testing it, inspecting schema, and executing
queries.

**Python Example:**

```python
import requests
from typing import Dict, Any

class DatasourceClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def create_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new database connection."""
        response = requests.post(
            f"{self.base_url}/api/datasources/connections",
            json=config,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test a database connection."""
        response = requests.post(
            f"{self.base_url}/api/datasources/connections/{connection_id}/test",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_tables(self, connection_id: str) -> list:
        """Get list of tables."""
        response = requests.get(
            f"{self.base_url}/api/datasources/connections/{connection_id}/tables",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["tables"]

    def get_table_details(self, connection_id: str, table_name: str) -> Dict[str, Any]:
        """Get details for a specific table."""
        response = requests.get(
            f"{self.base_url}/api/datasources/connections/{connection_id}/tables/{table_name}/details",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def execute_query(self, connection_id: str, query: str, limit: int = 100) -> Dict[str, Any]:
        """Execute a SQL query."""
        response = requests.post(
            f"{self.base_url}/api/datasources/connections/{connection_id}/query",
            json={"query": query, "limit": limit},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def preview_table(self, connection_id: str, table_name: str, limit: int = 50) -> Dict[str, Any]:
        """Preview table data."""
        response = requests.post(
            f"{self.base_url}/api/datasources/connections/{connection_id}/preview",
            json={"table_name": table_name, "limit": limit},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()


# Usage Example
def main():
    client = DatasourceClient(
        base_url="https://api.agenticstudio.com",
        token="your-jwt-token-here"
    )

    # Step 1: Create a database connection
    print("Creating database connection...")
    connection_config = {
        "name": "Customer Analytics DB",
        "description": "PostgreSQL database for customer analytics",
        "database_type": "postgres",
        "host": "analytics-db.example.com",
        "port": 5432,
        "database_name": "analytics",
        "username": "analytics_user",
        "password": "secure_password_123",
        "use_ssl": True,
        "ssl_config": {
            "sslmode": "require"
        }
    }

    connection = client.create_connection(connection_config)
    connection_id = connection["id"]
    print(f"✓ Connection created: {connection_id}")

    # Step 2: Test the connection
    print("\nTesting connection...")
    test_result = client.test_connection(connection_id)

    if test_result["success"]:
        print("✓ Connection test successful")
    else:
        print(f"✗ Connection test failed: {test_result['error_message']}")
        return

    # Step 3: Get list of tables
    print("\nFetching table list...")
    tables = client.get_tables(connection_id)
    print(f"✓ Found {len(tables)} tables:")
    for table in tables[:5]:  # Show first 5
        print(f"  - {table}")

    # Step 4: Get details for a specific table
    if tables:
        table_name = tables[0]
        print(f"\nGetting details for table '{table_name}'...")
        table_details = client.get_table_details(connection_id, table_name)

        print(f"✓ Table: {table_details['table_name']}")
        print(f"  Columns: {len(table_details['columns'])}")
        print(f"  Primary Keys: {table_details['primary_keys']}")

        # Show column details
        print("\n  Column Details:")
        for col in table_details['columns'][:5]:  # Show first 5 columns
            print(f"    - {col['name']} ({col['type']}) - Nullable: {col['nullable']}")

    # Step 5: Preview table data
    if tables:
        print(f"\nPreviewing data from table '{table_name}'...")
        preview = client.preview_table(connection_id, table_name, limit=10)

        print(f"✓ Retrieved {preview['row_count']} rows")
        print(f"  Columns: {', '.join(preview['columns'])}")
        print(f"  Sample rows:")
        for i, row in enumerate(preview['rows'][:3], 1):
            print(f"    {i}. {row}")

    # Step 6: Execute custom query
    print("\nExecuting custom query...")
    query = f"SELECT * FROM {table_name} LIMIT 5"
    result = client.execute_query(connection_id, query, limit=5)

    print(f"✓ Query executed in {result['execution_time_ms']}ms")
    print(f"  Returned {result['row_count']} rows")
    print(f"  Columns: {', '.join(result['columns'])}")

    # Step 7: Execute analytical query
    print("\nExecuting analytical query...")
    analytical_query = f"""
        SELECT
            COUNT(*) as total_records,
            MIN(created_at) as earliest_date,
            MAX(created_at) as latest_date
        FROM {table_name}
    """
    analytics = client.execute_query(connection_id, analytical_query)

    print(f"✓ Analytics results:")
    if analytics['rows']:
        row = analytics['rows'][0]
        print(f"  Total Records: {row[0]}")
        print(f"  Date Range: {row[1]} to {row[2]}")

    print("\n✓ Workflow completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e.response.status_code}")
        print(f"  {e.response.json()}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
```

**JavaScript Example:**

```javascript
class DatasourceClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async createConnection(config) {
    const response = await fetch(`${this.baseUrl}/api/datasources/connections`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async testConnection(connectionId) {
    const response = await fetch(
      `${this.baseUrl}/api/datasources/connections/${connectionId}/test`,
      { method: 'POST', headers: this.headers }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async getTables(connectionId) {
    const response = await fetch(
      `${this.baseUrl}/api/datasources/connections/${connectionId}/tables`,
      { headers: this.headers }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const data = await response.json();
    return data.tables;
  }

  async executeQuery(connectionId, query, limit = 100) {
    const response = await fetch(
      `${this.baseUrl}/api/datasources/connections/${connectionId}/query`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ query, limit })
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }
}

// Usage
async function runWorkflow() {
  const client = new DatasourceClient(
    'https://api.agenticstudio.com',
    'your-jwt-token-here'
  );

  try {
    // Create connection
    console.log('Creating database connection...');
    const connection = await client.createConnection({
      name: 'Customer Analytics DB',
      database_type: 'postgres',
      host: 'analytics-db.example.com',
      port: 5432,
      database_name: 'analytics',
      username: 'analytics_user',
      password: 'secure_password_123',
      use_ssl: true,
      ssl_config: { sslmode: 'require' }
    });

    console.log('✓ Connection created:', connection.id);

    // Test connection
    console.log('\nTesting connection...');
    const testResult = await client.testConnection(connection.id);

    if (!testResult.success) {
      throw new Error(`Connection test failed: ${testResult.error_message}`);
    }
    console.log('✓ Connection test successful');

    // Get tables
    console.log('\nFetching tables...');
    const tables = await client.getTables(connection.id);
    console.log(`✓ Found ${tables.length} tables`);

    // Execute query
    if (tables.length > 0) {
      console.log('\nExecuting query...');
      const result = await client.executeQuery(
        connection.id,
        `SELECT * FROM ${tables[0]} LIMIT 5`,
        5
      );

      console.log(`✓ Query executed in ${result.execution_time_ms}ms`);
      console.log(`  Returned ${result.row_count} rows`);
    }

    console.log('\n✓ Workflow completed!');

  } catch (error) {
    console.error('✗ Error:', error.message);
  }
}

runWorkflow();
```

---

## Performance Considerations

### Endpoint Performance

**Fast Operations (< 200ms):**

- `GET /connections` - List connections (cached, simple query)
- `GET /connections/{id}` - Get single connection (simple query)
- `PUT /connections/{id}` - Update connection (simple update)
- `DELETE /connections/{id}` - Delete connection (simple delete)
- `GET /connections/{id}/tables` - Get table list (when cached)

**Medium Speed Operations (200ms - 5 seconds):**

- `POST /connections` - Create connection (encryption, validation)
- `POST /connections/{id}/test` - Test connection (network dependent)
- `POST /connections/test` - Test connection config (network dependent)
- `GET /connections/{id}/tables/{table}/details` - Get table details (when cached)
- `GET /connections/{id}/tables/{table}/columns` - Get columns (forced refresh)
- `POST /connections/{id}/preview` - Preview table data (query execution)
- `POST /connections/{id}/query` - Execute simple queries

**Slow Operations (5+ seconds):**

- `GET /connections/{id}/schema` - Get full schema (not cached, many tables)
- `POST /connections/{id}/query` - Complex queries, large result sets
- `GET /connections/{id}/tables` - Get table list (not cached, many tables)
- Any operation with `force_refresh=true` on large databases

### Optimisation Tips

**1. Use Table List Instead of Full Schema**

❌ **Bad: Fetching full schema for table list**

```python
# Slow - retrieves all table details
response = requests.get(f"{base_url}/connections/{conn_id}/schema")
tables = list(response.json()["tables"].keys())
```

✅ **Good: Use dedicated table list endpoint**

```python
# Fast - retrieves only table names
response = requests.get(f"{base_url}/connections/{conn_id}/tables")
tables = response.json()["tables"]
```

**2. Leverage Schema Caching**

❌ **Bad: Always forcing refresh**

```python
# Slow - forces database query every time
for table in tables:
    response = requests.get(
        f"{base_url}/connections/{conn_id}/tables/{table}/details?force_refresh=true"
    )
```

✅ **Good: Use cached data**

```python
# Fast - uses cached schema (refreshed every 24 hours)
for table in tables:
    response = requests.get(
        f"{base_url}/connections/{conn_id}/tables/{table}/details"
    )
```

**3. Limit Query Results**

❌ **Bad: Fetching unlimited results**

```python
# Potentially slow and memory-intensive
result = client.execute_query(
    connection_id,
    "SELECT * FROM large_table",
    limit=10000  # Too large
)
```

✅ **Good: Use appropriate limits**

```python
# Fast - limits result set size
result = client.execute_query(
    connection_id,
    "SELECT * FROM large_table",
    limit=100  # Reasonable limit
)
```

**4. Use Table Preview for Simple Data Viewing**

❌ **Bad: Writing SELECT query**

```python
# More verbose and slower
result = client.execute_query(
    connection_id,
    f"SELECT * FROM {table_name} LIMIT 50"
)
```

✅ **Good: Use preview endpoint**

```python
# Simpler and optimised
result = client.preview_table(connection_id, table_name, limit=50)
```

**5. Batch Connection Tests**

❌ **Bad: Testing connections sequentially**

```python
# Slow - waits for each test to complete
for conn_id in connection_ids:
    test_result = client.test_connection(conn_id)
```

✅ **Good: Test connections in parallel**

```python
import asyncio
import aiohttp

async def test_connections_parallel(connection_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [
            test_connection_async(session, conn_id)
            for conn_id in connection_ids
        ]
        results = await asyncio.gather(*tasks)
    return results
```

**6. Cache SSL Config Schemas**

✅ **Good: Fetch SSL schemas once and cache**

```python
# Fetch once at application startup
ssl_schemas = {}
for db_type in ["postgres", "mysql", "mssql"]:
    response = requests.get(f"{base_url}/ssl-config-schema/{db_type}")
    ssl_schemas[db_type] = response.json()

# Reuse cached schemas
postgres_ssl_options = ssl_schemas["postgres"]["options"]
```

**7. Use Read-Only Connections for Reporting**

✅ **Good: Configure read-only mode for safety**

```python
# Create read-only connection for reporting workflows
connection_config = {
    "name": "Reporting DB (Read-Only)",
    "database_type": "postgres",
    # ... connection details
    "read_only": True  # Prevents accidental modifications
}
```

**Benefits:**

- Prevents accidental data modifications
- Enforces SELECT-only queries
- Safer for production database access
- Better performance (no transaction overhead)

---

## Related Documentation

### Architecture Documentation

- [AgenticStudio Architecture Overview](../architecture/README.md) - System architecture and design patterns
- [Service Layer Design](../architecture/services.md) - Service layer organisation and patterns
- [Database Schema](../architecture/database.md) - Database models and relationships

### Related API Modules

- [Graph API](../graph/graph.md) - Workflow management and execution (uses datasources for data operations)
- [Execution API](../execution/execution.md) - Workflow execution (integrates with datasource queries)
- [Authentication API](../../../backend/api/auth/auth.md) - User authentication and authorisation

### Service Documentation

- [Datasource Service](../../backend/services/datasource/README.md) - Service layer implementation
- [Connection Management](../../backend/services/datasource/connection/README.md) - Connection handling
- [Schema Inspection](../../backend/services/datasource/schema/README.md) - Schema caching and inspection
- [Query Execution](../../backend/services/datasource/query/README.md) - Safe query execution

### External References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - Database toolkit used for connections
- [PostgreSQL SSL](https://www.postgresql.org/docs/current/libpq-ssl.html) - PostgreSQL SSL configuration
- [MySQL SSL](https://dev.mysql.com/doc/refman/8.0/en/using-encrypted-connections.html) - MySQL SSL configuration

---

## Summary

The Datasources API module is a critical component of AgenticStudio that enables workflows to interact with external
databases. It provides a secure, user-scoped interface for managing database connections across multiple database types
including PostgreSQL, MySQL, Microsoft SQL Server, SQLite, MongoDB, and Oracle.

The module excels at providing both quick operations (listing connections, getting connection details) and more complex
functionality (schema inspection, query execution) whilst maintaining strong security practices through credential
encryption, SSL/TLS support, and user-scoped access control. The service layer architecture ensures separation of
concerns, with dedicated components for connection management, schema inspection, and query execution.

Performance is optimised through intelligent schema caching, with separate endpoints for fast table listing versus
detailed schema retrieval. The module enforces safety through read-only mode support, query validation, and row limits
to prevent accidental data loss or resource exhaustion.

**Key Features:**

- **Multi-Database Support**: Seamless integration with 6 major database types
- **Security-First Design**: Encrypted credentials, SSL/TLS configuration, user-scoped access
- **Performance Optimised**: Schema caching, separate fast/slow endpoints, query limits
- **Developer-Friendly**: Comprehensive error handling, test endpoints, SSL schema documentation
- **Production-Ready**: Connection testing, health monitoring, usage statistics tracking

**Primary Use Cases:**

- Configuring database connections for data-driven workflows
- Extracting data from external systems for processing
- Executing queries as part of automated workflows
- Inspecting database schemas for dynamic workflow configuration
- Testing database connectivity and validating credentials
- Managing multiple database connections across different environments
