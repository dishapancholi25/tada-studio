"""Configuration and constants for datasource service."""

# Logging prefix for structured logging
LOG_PREFIX = "[DATASOURCE]"

# Cache configuration
SCHEMA_CACHE_TTL_SECONDS = 3600  # 1 hour
TABLE_LIST_CACHE_TTL_SECONDS = 3600  # 1 hour
TABLE_DETAILS_CACHE_TTL_SECONDS = 3600  # 1 hour

# Connection configuration
DEFAULT_CONNECTION_TIMEOUT_SECONDS = 10
DEFAULT_QUERY_TIMEOUT_SECONDS = 30
DEFAULT_QUERY_ROW_LIMIT = 1000
DEFAULT_TABLE_PREVIEW_LIMIT = 100

# Database-specific defaults
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_MYSQL_PORT = 3306
DEFAULT_MSSQL_PORT = 1433
DEFAULT_MONGODB_PORT = 27017
DEFAULT_ORACLE_PORT = 1521

# ODBC driver options
DEFAULT_MSSQL_DRIVER = "{ODBC Driver 17 for SQL Server}"
MSSQL_DRIVER_OPTIONS = [
    "{ODBC Driver 17 for SQL Server}",
    "{ODBC Driver 18 for SQL Server}",
    "{SQL Server}",
]

# PostgreSQL SSL modes
POSTGRES_SSL_MODES = [
    "disable",
    "allow",
    "prefer",
    "require",
    "verify-ca",
    "verify-full",
]
DEFAULT_POSTGRES_SSL_MODE = "require"

# Query validation
DANGEROUS_KEYWORDS = [
    "DROP",
    "DELETE",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXECUTE",
    "EXEC",
    "CALL",
    "MERGE",
    "REPLACE",
]

READ_OPERATIONS = ["SELECT"]
WRITE_OPERATIONS = ["INSERT", "UPDATE", "DELETE"]
DDL_OPERATIONS = ["CREATE", "ALTER", "DROP", "TRUNCATE"]
ALL_OPERATIONS = READ_OPERATIONS + WRITE_OPERATIONS + DDL_OPERATIONS
