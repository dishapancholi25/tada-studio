# Datasource Service

## Overview

The datasource service module provides comprehensive functionality for managing external database connections, executing
queries, and inspecting database schemas. It serves as the bridge between AgenticStudio and external data sources (
PostgreSQL, MySQL, MSSQL, MongoDB, Oracle, SQLite), enabling workflows to interact with databases through a secure,
validated interface.

**Location:** [backend/services/datasource/](../../backend/services/datasource/)

**Primary Responsibilities:**

- Create, update, and manage database connection configurations
- Test database connectivity and maintain connection status
- Execute SQL queries with safety validation and permissions checking
- Inspect database schemas (tables, columns, indexes, foreign keys)
- Cache schema metadata to reduce introspection overhead
- Format query results in multiple output formats (JSON, CSV, Markdown)
- Track query execution history and performance metrics

**Key Use Cases:**

- Connecting workflows to external databases for data retrieval
- Enabling AI agents to query databases as part of workflow execution
- Managing multiple database connections per user or project
- Providing read-only or restricted access to specific database tables
- Inspecting database schemas for dynamic query generation

## Architecture

### Module Structure

```
backend/services/datasource/
├── __init__.py                  # Public API exports and singleton service
├── service.py                   # Main DataSourceService orchestrator
├── config.py                    # Configuration constants and defaults
├── exceptions.py                # Custom exception hierarchy
│
├── connection/                  # Connection management components
│   ├── __init__.py             # Connection module exports
│   ├── manager.py              # CRUD operations for connections
│   ├── tester.py               # Connection testing functionality
│   └── builders/               # Connection string builders (Factory pattern)
│       ├── __init__.py
│       ├── factory.py          # Builder factory
│       ├── base.py             # Abstract base builder
│       ├── postgres.py         # PostgreSQL builder
│       ├── mysql.py            # MySQL builder
│       ├── mssql.py            # MSSQL builder
│       ├── mongodb.py          # MongoDB builder
│       ├── oracle.py           # Oracle builder
│       └── sqlite.py           # SQLite builder
│
├── query/                       # Query execution and validation
│   ├── __init__.py             # Query module exports
│   ├── executor.py             # Query execution with safety measures
│   ├── validator.py            # SQL query validation
│   └── formatters.py           # Result formatting (JSON/CSV/Markdown)
│
└── schema/                      # Schema inspection and caching
    ├── __init__.py             # Schema module exports
    ├── inspector.py            # Database schema introspection
    ├── cache.py                # Schema caching with TTL
    └── filters.py              # Table whitelist/blacklist filtering
```

**File Descriptions:**

- **service.py** - Main orchestrator that coordinates connection, query, and schema components
- **config.py** - Configuration constants for timeouts, cache TTL, default ports, and query limits
- **exceptions.py** - Custom exception classes for error handling
- **connection/manager.py** - Handles CRUD operations for connection configurations with credential encryption
- **connection/tester.py** - Tests database connectivity and updates connection status
- **connection/builders/** - Factory pattern implementation for building database-specific connection strings
- **query/executor.py** - Executes queries with validation, safety measures, and result formatting
- **query/validator.py** - Validates SQL queries for safety and permission compliance
- **query/formatters.py** - Formats query results into different output formats
- **schema/inspector.py** - Inspects database schemas to retrieve table and column metadata
- **schema/cache.py** - Caches schema information with TTL-based expiration
- **schema/filters.py** - Filters tables based on whitelist/blacklist configuration

### Design Patterns

#### Singleton Pattern

The service module uses a singleton pattern to ensure a single `DataSourceService` instance:

```
User Code
    ↓
get_datasource_service() ──→ Singleton Instance
    ↓                             ↓
DataSourceService ←──────────────┘
```

#### Factory Pattern

Connection string builders use the Factory pattern to eliminate conditional logic:

```
ConnectionStringBuilderFactory
    ↓
    ├── PostgreSQLConnectionStringBuilder
    ├── MySQLConnectionStringBuilder
    ├── MSSQLConnectionStringBuilder
    ├── MongoDBConnectionStringBuilder
    ├── OracleConnectionStringBuilder
    └── SQLiteConnectionStringBuilder
```

#### Strategy Pattern

Each database type has its own builder strategy, implementing the `ConnectionStringBuilder` interface:

```python
# Abstract base class
class ConnectionStringBuilder(ABC):
    def build(self, connection: DataSourceConnection) -> str:
        pass

# Concrete implementations
class PostgreSQLConnectionStringBuilder(ConnectionStringBuilder):
    def build(self, connection: DataSourceConnection) -> str:
        # PostgreSQL-specific connection string building
        pass
```

#### Component Organisation

The service is organised into three major subsystems:

```
DataSourceService
    │
    ├── ConnectionManager ──→ Manages connection CRUD
    │       └── Uses: ConnectionStringBuilderFactory
    │
    ├── ConnectionTester ───→ Tests database connectivity
    │       └── Uses: ConnectionStringBuilderFactory
    │
    ├── SchemaInspector ────→ Inspects database schemas
    │       ├── Uses: SchemaCache
    │       ├── Uses: TableFilter
    │       └── Uses: ConnectionStringBuilderFactory
    │
    └── QueryExecutor ──────→ Executes queries safely
            ├── Uses: QueryValidator
            ├── Uses: ResultFormatter
            └── Uses: ConnectionStringBuilderFactory
```

### Dependencies

#### Internal Dependencies

- **backend.models** - `DataSourceConnection`, `DatabaseType`, `DataSourceQueryHistory`
- **backend.encryption_utils** - `default_encryptor` for credential encryption
- **backend.services.database** - Database session management

#### External Dependencies

- **sqlalchemy** - Database abstraction layer and query execution
- **sqlalchemy.orm** - ORM for database operations
- Standard library: `logging`, `csv`, `io`, `datetime`, `typing`, `abc`, `re`

#### Database Dependencies

The service stores connection configurations in the application database:

- **DataSourceConnection** table - Connection configurations with encrypted credentials
- **DataSourceQueryHistory** table - Query execution logs and performance metrics

#### Environment Variables

No environment variables are directly required by the service. Configuration is managed through the database and the
`config.py` constants.

## Public API

### Exported Classes

- `DataSourceService` - Main service orchestrator for all datasource operations

### Exported Functions

- `get_datasource_service()` - Returns the singleton DataSourceService instance

### Constants and Configuration

All constants are defined in [backend/services/datasource/config.py](../../backend/services/datasource/config.py):

**Logging:**

- `LOG_PREFIX` - "[DATASOURCE]" prefix for structured logging

**Cache TTL (Time To Live):**

- `SCHEMA_CACHE_TTL_SECONDS` - 3600 (1 hour)
- `TABLE_LIST_CACHE_TTL_SECONDS` - 3600 (1 hour)
- `TABLE_DETAILS_CACHE_TTL_SECONDS` - 3600 (1 hour)

**Connection Configuration:**

- `DEFAULT_CONNECTION_TIMEOUT_SECONDS` - 10
- `DEFAULT_QUERY_TIMEOUT_SECONDS` - 30
- `DEFAULT_QUERY_ROW_LIMIT` - 1000
- `DEFAULT_TABLE_PREVIEW_LIMIT` - 100

**Database Default Ports:**

- `DEFAULT_POSTGRES_PORT` - 5432
- `DEFAULT_MYSQL_PORT` - 3306
- `DEFAULT_MSSQL_PORT` - 1433
- `DEFAULT_MONGODB_PORT` - 27017
- `DEFAULT_ORACLE_PORT` - 1521

**MSSQL ODBC Drivers:**

- `DEFAULT_MSSQL_DRIVER` - "{ODBC Driver 17 for SQL Server}"
- `MSSQL_DRIVER_OPTIONS` - List of available ODBC drivers

**PostgreSQL SSL Modes:**

- `POSTGRES_SSL_MODES` - ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
- `DEFAULT_POSTGRES_SSL_MODE` - "require"

**Query Operation Types:**

- `READ_OPERATIONS` - ["SELECT"]
- `WRITE_OPERATIONS` - ["INSERT", "UPDATE", "DELETE"]
- `DDL_OPERATIONS` - ["CREATE", "ALTER", "DROP", "TRUNCATE"]
- `ALL_OPERATIONS` - Combined list of all operations
- `DANGEROUS_KEYWORDS` - List of restricted SQL keywords

### Exceptions

```
Exception
└── DatasourceError (base exception)
    ├── ConnectionNotFoundError
    ├── ConnectionAlreadyExistsError
    ├── ConnectionTestFailedError
    ├── UnsupportedDatabaseTypeError
    ├── SchemaInspectionError
    ├── InvalidQueryError
    ├── QueryExecutionError
    └── ReadOnlyViolationError
```

## Core Classes

### `DataSourceService`

Main service orchestrator that provides a unified interface for all datasource operations.

**Purpose:** Coordinates connection management, schema inspection, and query execution through a single service
interface.

**Responsibilities:**

- Initialise and manage connection, schema, and query subsystems
- Provide high-level methods for connection CRUD operations
- Execute queries with proper validation and safety measures
- Inspect database schemas and cache metadata
- Maintain query execution history

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise datasource service with all subsystems."""
```

The service automatically initialises all subsystem components:

- ConnectionManager for connection CRUD
- ConnectionTester for connectivity testing
- SchemaInspector for schema introspection
- QueryExecutor for safe query execution

**Key Methods:**

#### `create_connection()`

```python
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
) -> DataSourceConnection:
    """Create a new database connection configuration."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `name` (str) - Unique name for the connection
- `description` (str) - Human-readable description
- `database_type` (DatabaseType) - Type of database (POSTGRES, MYSQL, etc.)
- `connection_string` (Optional[str]) - Full connection string (alternative to individual fields)
- `host` (Optional[str]) - Database host address
- `port` (Optional[int]) - Database port number
- `database_name` (Optional[str]) - Name of the database
- `username` (Optional[str]) - Database username
- `password` (Optional[str]) - Database password (will be encrypted)
- `use_ssl` (bool) - Whether to use SSL/TLS (default: False)
- `ssl_config` (Optional[dict]) - SSL configuration parameters
- `connection_options` (Optional[dict]) - Additional connection options
- `user_id` (Optional[str]) - User ID who owns this connection

**Returns:**

- `DataSourceConnection` - Created connection configuration object

**Raises:**

- `ConnectionAlreadyExistsError` - If connection name already exists

**Example:**

```python
from backend.services.datasource import get_datasource_service
from backend.models import DatabaseType
from backend.services.database import get_db_session

service = get_datasource_service()
db = get_db_session()

# Create PostgreSQL connection
connection = service.create_connection(
    db=db,
    name="production_db",
    description="Production PostgreSQL database",
    database_type=DatabaseType.POSTGRES,
    host="db.example.com",
    port=5432,
    database_name="agenticstudio_prod",
    username="app_user",
    password="secure_password123",
    use_ssl=True,
    ssl_config={"ssl_mode": "require"},
    user_id="user_123",
)

print(f"Created connection: {connection.id}")
```

**Behaviour:**

- Validates that connection name is unique
- Encrypts password and connection string before storage
- Creates database record with all configuration
- Returns fully initialised DataSourceConnection object

**Use Cases:**

- Setting up database connections for workflows
- Configuring data sources for AI agents to query
- Adding external databases for data retrieval in automation

#### `get_connection()`

```python
def get_connection(
    self,
    db: Session,
    connection_id: str,
) -> Optional[DataSourceConnection]:
    """Get a connection by ID."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `connection_id` (str) - Connection ID to retrieve

**Returns:**

- `DataSourceConnection` - Connection object if found, None otherwise

**Example:**

```python
connection = service.get_connection(db, connection_id="conn_abc123")
if connection:
    print(f"Found connection: {connection.name}")
else:
    print("Connection not found")
```

#### `list_connections()`

```python
def list_connections(
    self,
    db: Session,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
) -> List[DataSourceConnection]:
    """List all connections with optional filtering."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `active_only` (bool) - Only return active connections (default: True)
- `skip` (int) - Number of records to skip for pagination (default: 0)
- `limit` (int) - Maximum records to return (default: 100)
- `user_id` (Optional[str]) - Filter by user ID

**Returns:**

- `List[DataSourceConnection]` - List of connection objects

**Example:**

```python
# Get all active connections for a user
connections = service.list_connections(
    db=db,
    active_only=True,
    skip=0,
    limit=50,
    user_id="user_123",
)

for conn in connections:
    print(f"{conn.name} ({conn.database_type})")
```

#### `test_connection()`

```python
def test_connection(
    self,
    db: Session,
    connection_id: str,
) -> Tuple[bool, Optional[str]]:
    """Test a database connection."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `connection_id` (str) - Connection ID to test

**Returns:**

- `Tuple[bool, Optional[str]]` - (success, error_message) tuple

**Raises:**

- `ConnectionNotFoundError` - If connection not found

**Example:**

```python
success, error = service.test_connection(db, connection_id="conn_abc123")

if success:
    print("Connection test successful")
else:
    print(f"Connection test failed: {error}")
```

**Behaviour:**

- Builds connection string using appropriate builder
- Attempts to connect to the database
- Executes a database-specific test query (SELECT version(), etc.)
- Updates connection status in database (last_connection_test, last_connection_status)
- Returns success/failure with error details

#### `execute_query()`

```python
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
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `connection_id` (str) - Connection ID to execute query on
- `query` (str) - SQL query to execute
- `limit` (int) - Maximum rows to return (default: 1000)
- `user_id` (Optional[str]) - User ID executing the query
- `context` (Optional[Dict[str, Any]]) - Additional context for logging

**Returns:**

- `Dict[str, Any]` - Query results or error information

**Example:**

```python
import asyncio

async def run_query():
    result = await service.execute_query(
        db=db,
        connection_id="conn_abc123",
        query="SELECT * FROM users WHERE active = true",
        limit=100,
        user_id="user_123",
        context={"workflow_id": "wf_456", "action": "user_fetch"},
    )

    if result["success"]:
        print(f"Retrieved {result['row_count']} rows")
        print(f"Columns: {result['columns']}")
        print(f"Data: {result['data']}")
    else:
        print(f"Query failed: {result['error']}")

asyncio.run(run_query())
```

**Behaviour:**

- Validates connection exists and is active
- Delegates to QueryExecutor with READ + INSERT/UPDATE operations allowed
- Validates query for safety (dangerous keywords, permissions)
- Executes query with timeout and row limit
- Logs query execution to history table
- Updates connection usage statistics
- Returns formatted results with metadata

**Use Cases:**

- Executing SELECT queries from workflows
- Allowing AI agents to query databases
- Inserting or updating data from automation

#### `get_schema()`

```python
def get_schema(
    self,
    db: Session,
    connection_id: str,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    """Get the database schema for a connection."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `connection_id` (str) - Connection ID
- `force_refresh` (bool) - Force cache refresh (default: False)

**Returns:**

- `Optional[Dict[str, Any]]` - Schema dictionary with tables and views, None if error

**Example:**

```python
schema = service.get_schema(db, connection_id="conn_abc123", force_refresh=True)

if schema:
    print(f"Tables: {len(schema['tables'])}")
    for table_name, table_info in schema['tables'].items():
        print(f"  {table_name}: {len(table_info['columns'])} columns")
```

**Behaviour:**

- Checks cache first unless force_refresh is True
- Inspects database schema using SQLAlchemy inspector
- Retrieves table lists, columns, primary keys, foreign keys, indexes
- Applies whitelist/blacklist filters if configured
- Caches results with TTL
- Returns complete schema dictionary

#### `get_table_list()`

```python
def get_table_list(
    self,
    db: Session,
    connection_id: str,
    force_refresh: bool = False,
) -> Optional[List[str]]:
    """Get list of table names for a connection."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `connection_id` (str) - Connection ID
- `force_refresh` (bool) - Force cache refresh (default: False)

**Returns:**

- `Optional[List[str]]` - List of table names, None if error

**Example:**

```python
tables = service.get_table_list(db, connection_id="conn_abc123")
if tables:
    print(f"Available tables: {', '.join(tables)}")
```

#### `get_table_details()`

```python
def get_table_details(
    self,
    db: Session,
    connection_id: str,
    table_name: str,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    """Get detailed information for a single table."""
```

**Parameters:**

- `db` (Session) - SQLAlchemy database session
- `connection_id` (str) - Connection ID
- `table_name` (str) - Name of table to inspect
- `force_refresh` (bool) - Force cache refresh (default: False)

**Returns:**

- `Optional[Dict[str, Any]]` - Table details dictionary, None if error

**Example:**

```python
table_info = service.get_table_details(
    db=db,
    connection_id="conn_abc123",
    table_name="users",
)

if table_info:
    print(f"Columns: {[col['name'] for col in table_info['columns']]}")
    print(f"Primary keys: {table_info['primary_keys']}")
    print(f"Foreign keys: {len(table_info['foreign_keys'])}")
```

### `ConnectionManager`

Manages CRUD operations for datasource connections.

**Purpose:** Handles creation, retrieval, updates, and deletion of database connection configurations with proper
encryption of credentials.

**Location:
** [backend/services/datasource/connection/manager.py](../../backend/services/datasource/connection/manager.py)

**Responsibilities:**

- Create new connection configurations
- Retrieve connections by ID or name
- List connections with filtering and pagination
- Update connection configurations
- Delete connections
- Encrypt/decrypt sensitive credentials

**Key Methods:**

All methods are documented in the DataSourceService section above, as ConnectionManager methods are exposed through the
service interface.

### `ConnectionTester`

Tests database connections and updates connection status.

**Purpose:** Verifies database connectivity by attempting to connect and execute a test query.

**Location:** [backend/services/datasource/connection/tester.py](../../backend/services/datasource/connection/tester.py)

**Responsibilities:**

- Build connection strings for testing
- Attempt database connections with timeout
- Execute database-specific test queries
- Update connection status in database
- Track last connection test timestamp and results

**Key Methods:**

See `test_connection()` documented in the DataSourceService section.

### `ConnectionStringBuilderFactory`

Factory for creating database-specific connection string builders.

**Purpose:** Provides a factory interface to create the appropriate connection string builder based on database type,
eliminating conditional logic.

**Location:
** [backend/services/datasource/connection/builders/factory.py](../../backend/services/datasource/connection/builders/factory.py)

**Responsibilities:**

- Map database types to builder classes
- Create builder instances for specific database types
- Build connection strings from DataSourceConnection objects
- Handle encrypted connection strings

**Design Pattern:** Factory Method Pattern with Strategy Pattern

**Key Methods:**

#### `create_builder()`

```python
@classmethod
def create_builder(
    cls,
    database_type: DatabaseType,
) -> ConnectionStringBuilder:
    """Create a connection string builder for the specified database type."""
```

**Parameters:**

- `database_type` (DatabaseType) - Type of database

**Returns:**

- `ConnectionStringBuilder` - Database-specific builder instance

**Raises:**

- `UnsupportedDatabaseTypeError` - If database type is not supported

**Example:**

```python
from backend.services.datasource.connection.builders import ConnectionStringBuilderFactory
from backend.models import DatabaseType

# Create a PostgreSQL builder
builder = ConnectionStringBuilderFactory.create_builder(DatabaseType.POSTGRES)
```

#### `build_connection_string()`

```python
@classmethod
def build_connection_string(
    cls,
    connection: DataSourceConnection,
) -> str:
    """Build a connection string from the connection configuration."""
```

**Parameters:**

- `connection` (DataSourceConnection) - Connection configuration object

**Returns:**

- `str` - Complete connection string

**Example:**

```python
from backend.services.datasource.connection.builders import ConnectionStringBuilderFactory

# Build connection string from connection object
conn_str = ConnectionStringBuilderFactory.build_connection_string(connection)
# Returns: "postgresql://user:pass@host:5432/dbname?sslmode=require"
```

**Behaviour:**

- If connection has encrypted_connection_string, decrypts and returns it
- Otherwise, creates appropriate builder and builds connection string
- Handles credential decryption automatically
- Returns database-specific connection string format

### `QueryExecutor`

Executes queries on datasource connections with safety measures.

**Purpose:** Safely execute SQL queries with validation, permissions checking, result formatting, and history logging.

**Location:** [backend/services/datasource/query/executor.py](../../backend/services/datasource/query/executor.py)

**Responsibilities:**

- Validate queries before execution
- Enforce read-only and operation restrictions
- Execute queries with timeout and row limits
- Format results in multiple output formats
- Log query execution history
- Track query performance metrics
- Handle errors with detailed logging

**Dependencies:**

- QueryValidator for query validation
- ResultFormatter for output formatting
- ConnectionStringBuilderFactory for connection strings

**Key Methods:**

See `execute_query()` documented in the DataSourceService section for the primary interface.

**Internal Methods:**

The QueryExecutor uses several internal methods to handle different query types:

- `_execute_with_engine()` - Executes query with SQLAlchemy engine
- `_handle_select_result()` - Processes SELECT query results
- `_handle_insert_result()` - Processes INSERT query results
- `_handle_other_result()` - Processes UPDATE/DELETE query results
- `_handle_error()` - Logs errors and returns error response
- `_log_query_history()` - Records query execution to history table

### `QueryValidator`

Validates SQL queries for safety and permissions.

**Purpose:** Check queries for dangerous operations, proper table references, and adherence to allowed operations before
execution.

**Location:** [backend/services/datasource/query/validator.py](../../backend/services/datasource/query/validator.py)

**Responsibilities:**

- Extract operation type from queries (SELECT, INSERT, etc.)
- Validate operations against allowed list
- Check for dangerous keywords (DROP, DELETE, TRUNCATE, etc.)
- Validate table references against whitelist
- Prevent multiple statement execution
- Handle CTE (WITH clause) queries
- Validate operation-specific requirements

**Key Methods:**

#### `validate()`

```python
def validate(
    self,
    query: str,
    allowed_operations: List[str],
    table_names: Optional[List[str]] = None,
    enable_read_only: bool = False,
) -> None:
    """Validate a SQL query."""
```

**Parameters:**

- `query` (str) - SQL query to validate
- `allowed_operations` (List[str]) - List of allowed SQL operations
- `table_names` (Optional[List[str]]) - Optional list of allowed table names
- `enable_read_only` (bool) - Whether read-only mode is enabled

**Raises:**

- `InvalidQueryError` - If query fails validation

**Example:**

```python
from backend.services.datasource.query import QueryValidator

validator = QueryValidator()

try:
    validator.validate(
        query="SELECT * FROM users WHERE active = true",
        allowed_operations=["SELECT"],
        table_names=["users", "orders"],
        enable_read_only=True,
    )
    print("Query is valid")
except InvalidQueryError as e:
    print(f"Invalid query: {e}")
```

#### `extract_operation()`

```python
def extract_operation(self, query: str) -> str:
    """Extract the main SQL operation from a query."""
```

**Parameters:**

- `query` (str) - SQL query

**Returns:**

- `str` - Main operation keyword (SELECT, INSERT, UPDATE, etc.)

**Example:**

```python
operation = validator.extract_operation("SELECT * FROM users")
print(operation)  # Output: "SELECT"
```

### `SchemaInspector`

Inspects database schemas and retrieves metadata.

**Purpose:** Provide methods to get table lists, table details, and full schemas with caching and filtering support.

**Location:** [backend/services/datasource/schema/inspector.py](../../backend/services/datasource/schema/inspector.py)

**Responsibilities:**

- Inspect database schemas using SQLAlchemy
- Retrieve table lists with whitelist/blacklist filtering
- Get detailed table metadata (columns, keys, indexes)
- Cache schema information to reduce overhead
- Handle database-specific schema variations

**Dependencies:**

- SchemaCache for caching metadata
- TableFilter for whitelist/blacklist filtering
- ConnectionStringBuilderFactory for connections

**Key Methods:**

See `get_schema()`, `get_table_list()`, and `get_table_details()` documented in the DataSourceService section.

### `SchemaCache`

Manages schema caching for datasource connections.

**Purpose:** Implements cache storage and retrieval with TTL-based expiration to reduce database introspection overhead.

**Location:** [backend/services/datasource/schema/cache.py](../../backend/services/datasource/schema/cache.py)

**Responsibilities:**

- Cache table lists with TTL
- Cache table details per table
- Cache full schemas
- Check cache expiration
- Invalidate cache on force_refresh

**Key Methods:**

#### `get_cached_table_list()`

```python
def get_cached_table_list(
    self,
    connection: DataSourceConnection,
    force_refresh: bool = False,
) -> Optional[List[str]]:
    """Get cached table list if available and not expired."""
```

**Returns:**

- `Optional[List[str]]` - Cached table list if valid, None otherwise

#### `set_cached_table_list()`

```python
def set_cached_table_list(
    self,
    db: Session,
    connection: DataSourceConnection,
    table_list: List[str],
) -> None:
    """Cache table list for connection."""
```

Similar methods exist for table details and full schemas.

### `TableFilter`

Filters table lists based on allowed and restricted table configuration.

**Purpose:** Handle whitelist (allowed_tables) and blacklist (restricted_tables) filtering for database schema
introspection.

**Location:** [backend/services/datasource/schema/filters.py](../../backend/services/datasource/schema/filters.py)

**Responsibilities:**

- Apply whitelist filtering to table lists
- Apply blacklist filtering to table lists
- Check if individual tables are allowed

**Key Methods:**

#### `filter_tables()`

```python
def filter_tables(
    self,
    connection: DataSourceConnection,
    tables: List[str],
) -> List[str]:
    """Filter table list based on connection configuration."""
```

**Parameters:**

- `connection` (DataSourceConnection) - Connection with filter configuration
- `tables` (List[str]) - List of all table names

**Returns:**

- `List[str]` - Filtered list of table names

**Example:**

```python
from backend.services.datasource.schema import TableFilter

filter = TableFilter()

# Connection configured with allowed_tables = ["users", "orders"]
filtered = filter.filter_tables(connection, ["users", "orders", "admin_logs"])
print(filtered)  # Output: ["users", "orders"]
```

#### `is_table_allowed()`

```python
def is_table_allowed(
    self,
    connection: DataSourceConnection,
    table_name: str,
) -> bool:
    """Check if a table is allowed based on connection configuration."""
```

**Returns:**

- `bool` - True if table is allowed, False otherwise

### `ResultFormatter`

Formats query results in different output formats.

**Purpose:** Convert query results into JSON, CSV, or Markdown format for different consumption scenarios.

**Location:** [backend/services/datasource/query/formatters.py](../../backend/services/datasource/query/formatters.py)

**Responsibilities:**

- Format results as JSON (default)
- Format results as CSV
- Format results as Markdown tables
- Normalise values for JSON serialisation (dates, None, etc.)

**Key Methods:**

#### `format_results()`

```python
def format_results(
    self,
    results: List[Dict[str, Any]],
    columns: List[str],
    format_type: str = "json",
    include_schema: bool = True,
    schema_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format query results in the specified format."""
```

**Parameters:**

- `results` (List[Dict[str, Any]]) - List of result rows as dictionaries
- `columns` (List[str]) - List of column names
- `format_type` (str) - Output format: "json", "csv", or "markdown" (default: "json")
- `include_schema` (bool) - Whether to include schema information (default: True)
- `schema_info` (Optional[Dict[str, Any]]) - Column schema information

**Returns:**

- `Dict[str, Any]` - Formatted results dictionary

**Example:**

```python
from backend.services.datasource.query import ResultFormatter

formatter = ResultFormatter()

results = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
]

# Format as JSON
json_output = formatter.format_results(
    results=results,
    columns=["id", "name", "email"],
    format_type="json",
)

# Format as CSV
csv_output = formatter.format_results(
    results=results,
    columns=["id", "name", "email"],
    format_type="csv",
)

# Format as Markdown
md_output = formatter.format_results(
    results=results,
    columns=["id", "name", "email"],
    format_type="markdown",
)
```

## Functions

### `get_datasource_service()`

Gets or creates the singleton datasource service instance.

**Signature:**

```python
def get_datasource_service() -> DataSourceService:
    """Get or create the singleton datasource service instance.

    Returns:
        DataSourceService instance
    """
```

**Parameters:** None

**Returns:**

- `DataSourceService` - Singleton service instance

**Example:**

```python
from backend.services.datasource import get_datasource_service

# Get service instance
service = get_datasource_service()

# Use service methods
connections = service.list_connections(db)
```

**Use Cases:**

- Accessing datasource functionality from API routes
- Using datasource service in workflow nodes
- Integrating with AI agent tool execution

## Configuration

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.datasource import get_datasource_service

service = get_datasource_service()
```

**With Database Session:**

```python
from backend.services.datasource import get_datasource_service
from backend.services.database import get_db_session

service = get_datasource_service()
db = get_db_session()

# Now use service with db session
connections = service.list_connections(db)
```

**In FastAPI Routes:**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.services.datasource import get_datasource_service
from backend.api.dependencies import get_database

router = APIRouter()

@router.get("/connections")
async def list_connections(db: Session = Depends(get_database)):
    service = get_datasource_service()
    connections = service.list_connections(db)
    return connections
```

## Error Handling

### Exception Hierarchy

```
Exception
└── DatasourceError (base exception for all datasource errors)
    ├── ConnectionNotFoundError (connection ID not found)
    ├── ConnectionAlreadyExistsError (duplicate connection name)
    ├── ConnectionTestFailedError (connection test failed)
    ├── UnsupportedDatabaseTypeError (unsupported database type)
    ├── SchemaInspectionError (schema inspection failed)
    ├── InvalidQueryError (query validation failed)
    ├── QueryExecutionError (query execution failed)
    └── ReadOnlyViolationError (write operation on read-only connection)
```

### Exception Details

#### `DatasourceError`

Base exception for all datasource-related errors.

**Inherits from:** `Exception`

**When raised:**

- Never raised directly, used as base class for specific errors

#### `ConnectionNotFoundError`

Raised when a datasource connection is not found.

**Inherits from:** `DatasourceError`

**Attributes:**

- `connection_id: str` - The connection ID that was not found

**When raised:**

- Attempting to retrieve a non-existent connection
- Attempting to test a non-existent connection
- Attempting to query a non-existent connection

**Example:**

```python
from backend.services.datasource import get_datasource_service
from backend.services.datasource.exceptions import ConnectionNotFoundError

service = get_datasource_service()

try:
    connection = service.get_connection(db, connection_id="invalid_id")
    if not connection:
        raise ConnectionNotFoundError("invalid_id")
except ConnectionNotFoundError as e:
    print(f"Error: {e}")
    # Error: Connection not found: invalid_id
```

#### `ConnectionAlreadyExistsError`

Raised when attempting to create a connection with a name that already exists.

**Inherits from:** `DatasourceError`

**Attributes:**

- `name: str` - The connection name that already exists

**When raised:**

- Creating a connection with a duplicate name

**Example:**

```python
from backend.services.datasource.exceptions import ConnectionAlreadyExistsError

try:
    service.create_connection(
        db=db,
        name="production_db",  # Name already exists
        description="Duplicate connection",
        database_type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
    )
except ConnectionAlreadyExistsError as e:
    print(f"Error: {e}")
    # Error: Connection with name 'production_db' already exists
```

#### `InvalidQueryError`

Raised when a query fails validation.

**Inherits from:** `DatasourceError`

**Attributes:**

- `query: str` - The invalid query
- `reason: str` - The reason why the query is invalid

**When raised:**

- Query contains dangerous keywords not in allowed operations
- Query references tables not in whitelist
- Query contains multiple statements
- Query operation not in allowed operations
- Empty or malformed query

**Example:**

```python
from backend.services.datasource.exceptions import InvalidQueryError

try:
    result = await service.execute_query(
        db=db,
        connection_id="conn_123",
        query="DROP TABLE users",  # Dangerous operation
    )
except InvalidQueryError as e:
    print(f"Query validation failed: {e.reason}")
    # Output: Query contains restricted keyword: DROP
```

#### `ReadOnlyViolationError`

Raised when attempting to modify data on a read-only connection.

**Inherits from:** `DatasourceError`

**Attributes:**

- `connection_id: str` - The read-only connection ID
- `operation: str` - The write operation that was attempted

**When raised:**

- Attempting INSERT, UPDATE, DELETE, or DDL operations on read-only connection

**Example:**

```python
from backend.services.datasource.exceptions import ReadOnlyViolationError

try:
    # Connection is configured as read_only=True
    result = await service.execute_query(
        db=db,
        connection_id="readonly_conn",
        query="UPDATE users SET active = false",
    )
except ReadOnlyViolationError as e:
    print(f"Error: {e}")
    # Error: Connection readonly_conn is read-only, cannot perform UPDATE
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.datasource import get_datasource_service
from backend.services.datasource.exceptions import (
    DatasourceError,
    ConnectionNotFoundError,
    InvalidQueryError,
    QueryExecutionError,
)

service = get_datasource_service()

try:
    # Execute query
    result = await service.execute_query(
        db=db,
        connection_id=connection_id,
        query=user_query,
        limit=100,
    )

    if result["success"]:
        return {"data": result["data"], "row_count": result["row_count"]}
    else:
        # Query executed but returned error
        return {"error": result["error"], "error_type": result.get("error_type")}

except ConnectionNotFoundError as e:
    # Handle connection not found
    logger.error(f"Connection not found: {e.connection_id}")
    return {"error": f"Connection {e.connection_id} does not exist"}

except InvalidQueryError as e:
    # Handle query validation errors
    logger.warning(f"Invalid query: {e.reason}")
    return {"error": f"Query validation failed: {e.reason}"}

except QueryExecutionError as e:
    # Handle query execution errors
    logger.error(f"Query execution failed: {e.error_message}")
    return {"error": f"Query failed: {e.error_message}"}

except DatasourceError as e:
    # Handle any other datasource errors
    logger.error(f"Datasource error: {e}")
    return {"error": "An error occurred with the datasource"}

except Exception as e:
    # Handle unexpected errors
    logger.exception("Unexpected error in query execution")
    return {"error": "An unexpected error occurred"}
```

## Integration Patterns

### Integration with API Layer

The datasource service is primarily used through FastAPI routes
in [backend/api/datasources/routes.py](../../backend/api/datasources/routes.py).

**Example: Create Connection Endpoint**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.services.datasource import get_datasource_service
from backend.api.dependencies import get_database
from backend.api.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/datasources", tags=["datasources"])

@router.post("/connections")
async def create_connection(
    connection_data: DatabaseConnectionCreate,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Create a new database connection."""
    try:
        service = get_datasource_service()
        connection = service.create_connection(
            db=db,
            name=connection_data.name,
            description=connection_data.description,
            database_type=connection_data.database_type,
            host=connection_data.host,
            port=connection_data.port,
            database_name=connection_data.database_name,
            username=connection_data.username,
            password=connection_data.password,
            user_id=current_user["sub"],
        )
        return connection
    except ConnectionAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Example: Execute Query Endpoint**

```python
@router.post("/connections/{connection_id}/query")
async def execute_query(
    connection_id: str,
    query_request: QueryExecuteRequest,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Execute a query on a database connection."""
    service = get_datasource_service()

    result = await service.execute_query(
        db=db,
        connection_id=connection_id,
        query=query_request.query,
        limit=query_request.limit or 1000,
        user_id=current_user["sub"],
    )

    return result
```

### Integration with Other Services

The datasource service is used by workflow nodes and AI agents to access external databases.

**Example: Database Query Node**

```python
from backend.services.datasource import get_datasource_service
from backend.services.database import get_db_session

class DatabaseQueryNode:
    """Workflow node that queries a database."""

    async def execute(self, inputs: dict) -> dict:
        """Execute database query node."""
        db = get_db_session()
        service = get_datasource_service()

        # Execute query from node configuration
        result = await service.execute_query(
            db=db,
            connection_id=inputs["connection_id"],
            query=inputs["query"],
            limit=inputs.get("limit", 100),
            context={"node_id": self.node_id, "workflow_id": self.workflow_id},
        )

        if result["success"]:
            return {"data": result["data"], "row_count": result["row_count"]}
        else:
            raise NodeExecutionError(result["error"])
```

**Example: AI Agent Database Tool**

```python
from backend.services.datasource import get_datasource_service

async def database_query_tool(
    connection_id: str,
    query: str,
    db_session,
) -> str:
    """AI agent tool for querying databases."""
    service = get_datasource_service()

    result = await service.execute_query(
        db=db_session,
        connection_id=connection_id,
        query=query,
        limit=100,
        context={"tool": "database_query", "agent": "llm_agent"},
    )

    if result["success"]:
        # Format results for AI consumption
        rows = result["data"]
        return f"Query returned {len(rows)} rows:\n{json.dumps(rows, indent=2)}"
    else:
        return f"Query failed: {result['error']}"
```

### Dependency Flow

```
API Routes (backend/api/datasources/)
    ↓
DataSourceService (singleton)
    ↓
    ├── ConnectionManager ──→ Database (DataSourceConnection table)
    ├── ConnectionTester  ──→ External Database
    ├── SchemaInspector   ──→ External Database + Cache
    └── QueryExecutor     ──→ External Database + Query History
```

**Data Flow:**

1. **Connection Creation:** API → Service → ConnectionManager → Database (encrypted credentials)
2. **Connection Testing:** API → Service → ConnectionTester → External DB → Status Update
3. **Query Execution:** API → Service → QueryExecutor → Validator → External DB → Formatter → History Log
4. **Schema Inspection:** API → Service → SchemaInspector → Cache Check → External DB → Cache Update

### Common Integration Patterns

#### Pattern 1: Secure Connection Management

```python
from backend.services.datasource import get_datasource_service
from backend.services.database import get_db_session

async def create_and_test_connection(
    name: str,
    database_type: DatabaseType,
    host: str,
    port: int,
    database_name: str,
    username: str,
    password: str,
    user_id: str,
) -> dict:
    """Create connection and immediately test it."""
    db = get_db_session()
    service = get_datasource_service()

    # Create connection (credentials encrypted automatically)
    connection = service.create_connection(
        db=db,
        name=name,
        description=f"Connection to {database_name}",
        database_type=database_type,
        host=host,
        port=port,
        database_name=database_name,
        username=username,
        password=password,
        user_id=user_id,
    )

    # Test connection
    success, error = service.test_connection(db, connection.id)

    return {
        "connection_id": connection.id,
        "test_success": success,
        "test_error": error,
    }
```

#### Pattern 2: Schema-Aware Query Execution

```python
async def query_with_schema_validation(
    connection_id: str,
    query: str,
    db_session,
) -> dict:
    """Execute query with schema validation."""
    service = get_datasource_service()

    # Get schema first
    schema = service.get_schema(db_session, connection_id)
    if not schema:
        return {"error": "Could not retrieve database schema"}

    # Extract table names from schema
    table_names = list(schema["tables"].keys())

    # Execute query (validator will check table references)
    result = await service.execute_query(
        db=db_session,
        connection_id=connection_id,
        query=query,
        limit=100,
    )

    return result
```

#### Pattern 3: Cached Schema Inspection

```python
def get_connection_metadata(connection_id: str, db_session) -> dict:
    """Get comprehensive connection metadata with caching."""
    service = get_datasource_service()

    # Get basic connection info
    connection = service.get_connection(db_session, connection_id)
    if not connection:
        return {"error": "Connection not found"}

    # Get cached schema (fast)
    schema = service.get_schema(db_session, connection_id, force_refresh=False)

    # Get cached table list (fast)
    tables = service.get_table_list(db_session, connection_id, force_refresh=False)

    return {
        "connection": {
            "id": connection.id,
            "name": connection.name,
            "database_type": connection.database_type,
            "status": connection.last_connection_status,
        },
        "tables": tables,
        "schema": schema,
    }
```

## Usage Examples

### Example 1: Basic Connection and Query

Complete end-to-end example of creating a connection and executing a query:

```python
from backend.services.datasource import get_datasource_service
from backend.models import DatabaseType
from backend.services.database import get_db_session
import asyncio

async def basic_usage_example():
    """Basic datasource usage example."""

    # Step 1: Get service and database session
    service = get_datasource_service()
    db = get_db_session()

    # Step 2: Create a PostgreSQL connection
    connection = service.create_connection(
        db=db,
        name="my_postgres_db",
        description="Example PostgreSQL connection",
        database_type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
        database_name="myapp",
        username="app_user",
        password="secure_password",
        user_id="user_123",
    )

    print(f"Created connection: {connection.id}")

    # Step 3: Test the connection
    success, error = service.test_connection(db, connection.id)
    if success:
        print("Connection test successful!")
    else:
        print(f"Connection test failed: {error}")
        return

    # Step 4: Execute a query
    result = await service.execute_query(
        db=db,
        connection_id=connection.id,
        query="SELECT * FROM users WHERE active = true LIMIT 10",
        limit=10,
        user_id="user_123",
    )

    # Step 5: Process results
    if result["success"]:
        print(f"Query successful! Retrieved {result['row_count']} rows")
        print(f"Columns: {result['columns']}")
        for row in result["data"]:
            print(row)
    else:
        print(f"Query failed: {result['error']}")

# Run the example
asyncio.run(basic_usage_example())
```

### Example 2: Schema Inspection and Analysis

Complete example showing schema inspection capabilities:

```python
from backend.services.datasource import get_datasource_service
from backend.services.database import get_db_session

def schema_inspection_example():
    """Schema inspection example."""

    service = get_datasource_service()
    db = get_db_session()

    connection_id = "conn_abc123"

    # Get full schema
    schema = service.get_schema(db, connection_id, force_refresh=True)

    if not schema:
        print("Failed to retrieve schema")
        return

    print(f"Database schema has {len(schema['tables'])} tables")
    print(f"Database has {len(schema['views'])} views\n")

    # Analyse each table
    for table_name, table_info in schema["tables"].items():
        print(f"Table: {table_name}")
        print(f"  Columns: {len(table_info['columns'])}")

        # Show columns
        for col in table_info["columns"]:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"    - {col['name']}: {col['type']} {nullable}")

        # Show primary keys
        if table_info["primary_keys"]:
            print(f"  Primary Keys: {', '.join(table_info['primary_keys'])}")

        # Show foreign keys
        if table_info["foreign_keys"]:
            print(f"  Foreign Keys: {len(table_info['foreign_keys'])}")
            for fk in table_info["foreign_keys"]:
                print(f"    - {fk['columns']} → {fk['referred_table']}.{fk['referred_columns']}")

        # Show indexes
        if table_info["indexes"]:
            print(f"  Indexes: {len(table_info['indexes'])}")
            for idx in table_info["indexes"]:
                unique = "UNIQUE" if idx["unique"] else ""
                print(f"    - {idx['name']} ({', '.join(idx['columns'])}) {unique}")

        print()

schema_inspection_example()
```

### Example 3: Multi-Format Query Results

Show how to get query results in different formats:

```python
from backend.services.datasource import get_datasource_service
from backend.services.datasource.query import QueryExecutor, ResultFormatter
from backend.services.database import get_db_session
import asyncio

async def multi_format_query_example():
    """Example showing different output formats."""

    service = get_datasource_service()
    db = get_db_session()

    connection_id = "conn_abc123"
    query = "SELECT id, name, email, created_at FROM users LIMIT 5"

    # Execute query with JSON format (default)
    json_result = await service.execute_query(
        db=db,
        connection_id=connection_id,
        query=query,
        limit=5,
    )

    print("JSON Format:")
    print(json_result["data"])
    print()

    # For CSV and Markdown, we need to use the formatter directly
    if json_result["success"]:
        formatter = ResultFormatter()

        # Format as CSV
        csv_result = formatter.format_results(
            results=json_result["data"],
            columns=json_result["columns"],
            format_type="csv",
        )

        print("CSV Format:")
        print(csv_result["data"])
        print()

        # Format as Markdown
        md_result = formatter.format_results(
            results=json_result["data"],
            columns=json_result["columns"],
            format_type="markdown",
        )

        print("Markdown Format:")
        print(md_result["data"])
        print()

asyncio.run(multi_format_query_example())
```

### Example 4: Connection with Whitelisting

Example showing table whitelisting for restricted access:

```python
from backend.services.datasource import get_datasource_service
from backend.models import DatabaseType, DataSourceConnection
from backend.services.database import get_db_session
import asyncio

async def whitelisted_connection_example():
    """Example with table whitelist for restricted access."""

    service = get_datasource_service()
    db = get_db_session()

    # Create connection with table whitelist
    connection = service.create_connection(
        db=db,
        name="restricted_db",
        description="Connection with limited table access",
        database_type=DatabaseType.POSTGRES,
        host="db.example.com",
        port=5432,
        database_name="production",
        username="readonly_user",
        password="readonly_pass",
        user_id="user_123",
    )

    # Configure whitelist by updating the connection
    updated_connection = service.update_connection(
        db=db,
        connection_id=connection.id,
        allowed_tables=["users", "orders"],  # Only these tables accessible
        read_only=True,  # Enforce read-only mode
    )

    print(f"Connection configured with whitelist: {updated_connection.allowed_tables}")

    # Get table list (will only show whitelisted tables)
    tables = service.get_table_list(db, connection.id)
    print(f"Available tables: {tables}")  # Output: ['users', 'orders']

    # This query will work (allowed table)
    result1 = await service.execute_query(
        db=db,
        connection_id=connection.id,
        query="SELECT * FROM users LIMIT 10",
    )
    print(f"Query on allowed table: {result1['success']}")  # True

    # This query will fail (table not in whitelist)
    result2 = await service.execute_query(
        db=db,
        connection_id=connection.id,
        query="SELECT * FROM admin_logs LIMIT 10",
    )
    print(f"Query on restricted table: {result2['success']}")  # False
    print(f"Error: {result2.get('error')}")

asyncio.run(whitelisted_connection_example())
```

### Example 5: Testing Pattern

Show how to use the datasource service in tests:

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.datasource import get_datasource_service
from backend.models import DatabaseType

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()

@pytest.fixture
def datasource_service():
    """Datasource service fixture."""
    return get_datasource_service()

def test_create_connection(datasource_service, mock_db_session):
    """Test creating a database connection."""
    connection = datasource_service.create_connection(
        db=mock_db_session,
        name="test_connection",
        description="Test connection",
        database_type=DatabaseType.SQLITE,
        connection_string="sqlite:///test.db",
        user_id="test_user",
    )

    assert connection is not None
    assert connection.name == "test_connection"
    assert connection.database_type == DatabaseType.SQLITE

@pytest.mark.asyncio
async def test_execute_query_validation(datasource_service, mock_db_session):
    """Test query validation."""
    from backend.services.datasource.exceptions import InvalidQueryError

    # Mock connection
    mock_connection = Mock()
    mock_connection.id = "test_conn"
    mock_connection.is_active = True
    mock_connection.read_only = False

    with patch.object(datasource_service, 'get_connection', return_value=mock_connection):
        # Test dangerous query
        result = await datasource_service.execute_query(
            db=mock_db_session,
            connection_id="test_conn",
            query="DROP TABLE users",  # Dangerous operation
        )

        # Should return error, not exception
        assert result["success"] is False
        assert "error" in result
```

## Performance Considerations

### Performance Characteristics

**Connection Management:**

- Create connection: O(1) - Single database insert with encryption
- List connections: O(n) - Query with pagination support
- Get connection: O(1) - Index lookup by ID or name

**Schema Inspection:**

- Get table list: O(n) - Cached, O(1) cache hit, O(n) cache miss where n = number of tables
- Get table details: O(1) - Cached per table
- Get full schema: O(n*m) - Where n = tables, m = average columns per table. Cached with 1-hour TTL

**Query Execution:**

- Query validation: O(q) - Where q = query length for regex matching
- Query execution: O(r) - Where r = result set size (limited by max_rows)
- Result formatting: O(r*c) - Where r = rows, c = columns

**Memory Usage:**

- Connection objects: ~1-2KB per connection (credentials encrypted)
- Schema cache: ~10-100KB per database depending on size
- Query results: Configurable via max_rows limit (default 1000 rows)

**I/O Characteristics:**

- Network-bound: Query execution depends on database network latency
- I/O-bound: Schema inspection involves database metadata queries
- Cache-optimised: Schema caching reduces repeated database introspection

### Optimisation Tips

#### Tip 1: Use Schema Caching

**Problem:**

```python
# Inefficient: Repeatedly inspecting schema without cache
for _ in range(10):
    schema = service.get_schema(db, connection_id, force_refresh=True)
    # Re-inspects database each time (slow)
```

**Solution:**

```python
# Efficient: Use cached schema
schema = service.get_schema(db, connection_id, force_refresh=False)
# Subsequent calls use cached data (fast)

# Only force refresh when schema changes
if schema_changed:
    schema = service.get_schema(db, connection_id, force_refresh=True)
```

#### Tip 2: Limit Query Results

**Problem:**

```python
# Inefficient: Fetching all rows
result = await service.execute_query(
    db=db,
    connection_id=connection_id,
    query="SELECT * FROM large_table",
    limit=1000000,  # Too many rows
)
```

**Solution:**

```python
# Efficient: Use reasonable limits
result = await service.execute_query(
    db=db,
    connection_id=connection_id,
    query="SELECT * FROM large_table WHERE created_at > '2024-01-01'",
    limit=100,  # Reasonable limit
)

# For large datasets, use pagination
offset = 0
page_size = 100
while True:
    result = await service.execute_query(
        db=db,
        connection_id=connection_id,
        query=f"SELECT * FROM large_table LIMIT {page_size} OFFSET {offset}",
        limit=page_size,
    )
    if not result["data"]:
        break
    process_batch(result["data"])
    offset += page_size
```

#### Tip 3: Reuse Connections

**Problem:**

```python
# Inefficient: Creating new connection for each query
for query in queries:
    connection = service.create_connection(...)  # Slow
    result = await service.execute_query(db, connection.id, query)
```

**Solution:**

```python
# Efficient: Reuse existing connection
connection = service.get_connection_by_name(db, "production_db")
if not connection:
    connection = service.create_connection(...)

# Execute multiple queries on same connection
for query in queries:
    result = await service.execute_query(db, connection.id, query)
```

#### Tip 4: Use Table Whitelisting

**Problem:**

```python
# Inefficient: Inspecting entire schema when only specific tables needed
schema = service.get_schema(db, connection_id)  # Gets all tables
```

**Solution:**

```python
# Efficient: Configure whitelist to reduce inspection scope
service.update_connection(
    db=db,
    connection_id=connection_id,
    allowed_tables=["users", "orders"],  # Only inspect these tables
)

# Schema inspection now only covers whitelisted tables
schema = service.get_schema(db, connection_id)  # Faster
```

### Async/Await Support

The datasource service supports async operations for query execution:

```python
from backend.services.datasource import get_datasource_service
import asyncio

async def async_query_example():
    """Example using async query execution."""
    service = get_datasource_service()

    # Execute query asynchronously
    result = await service.execute_query(
        db=db,
        connection_id="conn_123",
        query="SELECT * FROM users",
        limit=100,
    )

    return result

# Run async function
result = asyncio.run(async_query_example())
```

**Concurrent Queries:**

```python
async def concurrent_queries_example():
    """Execute multiple queries concurrently."""
    service = get_datasource_service()

    # Execute multiple queries in parallel
    results = await asyncio.gather(
        service.execute_query(db, "conn_1", "SELECT COUNT(*) FROM users"),
        service.execute_query(db, "conn_1", "SELECT COUNT(*) FROM orders"),
        service.execute_query(db, "conn_2", "SELECT * FROM products LIMIT 10"),
    )

    return results

results = asyncio.run(concurrent_queries_example())
```

### Connection Pooling

Connection pooling is handled by SQLAlchemy automatically. Each query creates a temporary engine that is disposed after
use. For production use with high query volume, consider implementing connection pooling at the application level.

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from backend.services.datasource import DataSourceService, get_datasource_service
from backend.models import DatabaseType

@pytest.fixture
def service():
    """Datasource service fixture."""
    return DataSourceService()

@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()

def test_service_initialisation(service):
    """Test service initialises all subsystems."""
    assert service.connection_manager is not None
    assert service.connection_tester is not None
    assert service.schema_inspector is not None
    assert service.query_executor is not None

def test_get_datasource_service_singleton():
    """Test singleton pattern."""
    service1 = get_datasource_service()
    service2 = get_datasource_service()
    assert service1 is service2  # Same instance
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch

@patch('backend.services.datasource.service.ConnectionManager')
def test_create_connection_with_mock(mock_manager_class, service, mock_db):
    """Test connection creation with mocked manager."""
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager

    mock_connection = Mock()
    mock_connection.id = "test_123"
    mock_connection.name = "test_conn"
    mock_manager.create_connection.return_value = mock_connection

    # Re-initialise service with mocked manager
    service = DataSourceService()

    result = service.create_connection(
        db=mock_db,
        name="test_conn",
        description="Test",
        database_type=DatabaseType.SQLITE,
        connection_string="sqlite:///test.db",
    )

    assert result.id == "test_123"
    mock_manager.create_connection.assert_called_once()
```

### Integration Testing

```python
import pytest
from backend.services.datasource import get_datasource_service
from backend.models import DatabaseType
from backend.services.database import get_db_session

@pytest.mark.integration
async def test_full_connection_workflow():
    """Integration test for complete connection workflow."""
    service = get_datasource_service()
    db = get_db_session()

    # Create SQLite connection for testing
    connection = service.create_connection(
        db=db,
        name=f"test_integration_{uuid.uuid4()}",
        description="Integration test connection",
        database_type=DatabaseType.SQLITE,
        connection_string="sqlite:///:memory:",
    )

    try:
        # Test connection
        success, error = service.test_connection(db, connection.id)
        assert success is True
        assert error is None

        # Execute query
        result = await service.execute_query(
            db=db,
            connection_id=connection.id,
            query="SELECT 1 as test_value",
        )

        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["data"][0]["test_value"] == 1

    finally:
        # Cleanup
        service.delete_connection(db, connection.id)
```

## Best Practices

### Do's

✅ **Always use the singleton service instance**

```python
# Good: Use singleton
from backend.services.datasource import get_datasource_service

service = get_datasource_service()
```

```python
# Bad: Don't instantiate directly
from backend.services.datasource.service import DataSourceService

service = DataSourceService()  # Creates duplicate instance
```

✅ **Always encrypt sensitive credentials**

```python
# Good: Service handles encryption automatically
connection = service.create_connection(
    db=db,
    name="production",
    database_type=DatabaseType.POSTGRES,
    password="sensitive_password",  # Automatically encrypted
)
```

```python
# Bad: Don't store plaintext passwords
connection.password = "plaintext_password"  # Not encrypted!
db.commit()
```

✅ **Use read-only mode for untrusted queries**

```python
# Good: Configure read-only for user-submitted queries
service.update_connection(
    db=db,
    connection_id=connection_id,
    read_only=True,  # Prevents data modification
)

# Now users can only SELECT
result = await service.execute_query(
    db=db,
    connection_id=connection_id,
    query=user_submitted_query,
)
```

✅ **Always set query limits**

```python
# Good: Set reasonable limits
result = await service.execute_query(
    db=db,
    connection_id=connection_id,
    query="SELECT * FROM large_table",
    limit=100,  # Prevents memory overflow
)
```

✅ **Use table whitelisting for restricted access**

```python
# Good: Limit table access for security
service.update_connection(
    db=db,
    connection_id=connection_id,
    allowed_tables=["users", "orders"],  # Only these tables accessible
)
```

✅ **Leverage schema caching**

```python
# Good: Use cached schema
schema = service.get_schema(db, connection_id, force_refresh=False)

# Only refresh when needed
if schema_has_changed:
    schema = service.get_schema(db, connection_id, force_refresh=True)
```

### Don'ts

❌ **Don't bypass query validation**

```python
# Bad: Don't execute queries without service validation
from sqlalchemy import create_engine, text

engine = create_engine(connection_string)
with engine.connect() as conn:
    conn.execute(text(user_query))  # No validation, dangerous!
```

Explanation: Always use the service's `execute_query()` method which validates queries for dangerous operations,
enforces permissions, and logs execution history.

❌ **Don't store unencrypted connection strings**

```python
# Bad: Don't log or expose connection strings
logger.info(f"Connection string: {connection_string}")  # Exposes credentials!

# Bad: Don't return connection strings in API responses
return {"connection_string": connection.connection_string}  # Security risk!
```

Explanation: Connection strings contain credentials and should never be logged or exposed. The service handles
encryption/decryption internally.

❌ **Don't ignore connection test results**

```python
# Bad: Don't skip connection testing
connection = service.create_connection(...)
# Immediately use connection without testing
result = await service.execute_query(db, connection.id, query)  # May fail
```

```python
# Good: Test before using
connection = service.create_connection(...)
success, error = service.test_connection(db, connection.id)
if not success:
    logger.error(f"Connection failed: {error}")
    return
# Now safe to use
```

❌ **Don't fetch unlimited rows**

```python
# Bad: Fetching all rows from large tables
result = await service.execute_query(
    db=db,
    connection_id=connection_id,
    query="SELECT * FROM million_row_table",
    limit=999999,  # Memory overflow risk!
)
```

Explanation: Always use reasonable row limits (100-1000) and implement pagination for large datasets.

❌ **Don't hardcode database credentials**

```python
# Bad: Hardcoded credentials
connection = service.create_connection(
    db=db,
    name="prod_db",
    database_type=DatabaseType.POSTGRES,
    password="hardcoded_password123",  # Security risk!
)
```

```python
# Good: Use environment variables or secrets management
import os

connection = service.create_connection(
    db=db,
    name="prod_db",
    database_type=DatabaseType.POSTGRES,
    password=os.getenv("DB_PASSWORD"),  # From environment
)
```

## Related Documentation

### Related Services

- [Database Service](./database.md) - Application database operations and migrations
- [Execution Service](./execution.md) - Workflow execution that may use datasource queries
- [Agent Service](./agent.md) - AI agents that can use datasource tools

### Related API Modules

- [Datasources API](../agents-guide/api/datasources.md) - HTTP endpoints for datasource management
- [Workflow API](../agents-guide/api/workflow.md) - Workflow execution that may include database nodes

### Related Models

- **DataSourceConnection** - Connection configuration model ([backend/models/](../../backend/models/))
- **DataSourceQueryHistory** - Query execution history model
- **DatabaseType** - Enum for supported database types

### External Documentation

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - Database abstraction layer used by the service
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
- [MySQL Connection Parameters](https://dev.mysql.com/doc/refman/8.0/en/connecting.html)
- [MSSQL ODBC Drivers](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

## Summary

The datasource service module provides a comprehensive, secure solution for managing external database connections and
executing queries within AgenticStudio workflows. It abstracts the complexity of connecting to multiple database types (
PostgreSQL, MySQL, MSSQL, MongoDB, Oracle, SQLite) behind a unified interface while enforcing security measures like
query validation, credential encryption, and read-only modes.

The service is organised into three major subsystems: connection management (creating, testing, and managing
connections), query execution (validating and executing queries safely), and schema inspection (introspecting and
caching database metadata). This modular design makes the service maintainable and extensible while providing optimal
performance through intelligent caching strategies.

**Key Features:**

- Multi-database support with database-specific connection string builders (Factory pattern)
- Secure credential management with automatic encryption/decryption
- SQL query validation to prevent dangerous operations
- Schema caching with configurable TTL to reduce database introspection overhead
- Query result formatting in multiple formats (JSON, CSV, Markdown)
- Comprehensive query execution history and performance tracking
- Table whitelisting/blacklisting for granular access control
- Read-only mode enforcement for untrusted query sources

**Primary Use Cases:**

- Enabling workflows to query external databases for data retrieval
- Providing AI agents with database query capabilities
- Managing multiple database connections per user or project
- Inspecting database schemas for dynamic query generation
- Executing validated queries with safety measures and permissions

**When to Use This Service:**

- When workflows need to access external databases
- When AI agents require database querying tools
- When building database-backed automation workflows
- When providing users with secure database query interfaces
- When integrating external data sources into AgenticStudio
