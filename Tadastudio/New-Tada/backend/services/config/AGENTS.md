# Config Service Module

## Overview

The config service module provides essential configuration utilities for the AgenticStudio backend application. It
consolidates all configuration-related functionality including URL construction, logging system setup, and execution
engine configuration.

**Location:** [backend/services/config/](../../backend/services/config/)

**Primary Responsibilities:**

- Dynamic API base URL resolution from environment variables
- Complete endpoint URL construction for API routes
- Comprehensive logging system initialisation and configuration
- Logger factory for creating named loggers throughout the application
- Execution engine configuration and feature flag management
- PostgreSQL connection string resolution for checkpointing

**Key Use Cases:**

- Configuring application logging with file rotation and console output
- Getting logger instances for different modules (API, execution, database, etc.)
- Resolving API URLs in different deployment environments (local, staging, production)
- Building complete endpoint URLs for HTTP execution and webhooks
- Configuring the execution engine with checkpointing and memory settings
- Creating execution engine instances with proper configuration

## Architecture

### Module Structure

```
backend/services/config/
├── __init__.py          # Public API exports
├── url.py               # URL configuration utilities
├── logging.py           # Logging system setup and logger factory
└── execution.py         # Execution engine configuration
```

**File Descriptions:**

- `__init__.py` - Consolidates and exports all configuration utilities with clear categorisation (URL, execution,
  logging)
- `url.py` - Handles dynamic API base URL resolution with fallback logic for different deployment scenarios
- `logging.py` - Sets up comprehensive logging with file rotation, console output, and specialised loggers
- `execution.py` - Provides execution engine configuration including checkpointing, memory, and PostgreSQL settings

### Design Patterns

**Factory Pattern:**

- `get_logger(name)` - Factory function for creating named loggers
- `create_execution_engine(graph_manager)` - Factory function for creating execution engine instances

**Singleton Pattern:**

- Logging initialisation uses a global flag (`_logging_initialized`) to prevent duplicate setup
- `setup_logging()` can be called multiple times but only initialises once

**Configuration Provider Pattern:**

- `ExecutionConfig` provides static methods to access execution-related configuration
- Environment variables are centralised with fallback defaults
- Configuration is accessed through static methods rather than instance methods

**Environment-Based Configuration:**

- All configuration reads from environment variables with sensible defaults
- Supports multiple deployment scenarios (local development, Azure, custom deployments)
- Graceful degradation when environment variables are not set

### Dependencies

**Internal Dependencies:**

- `backend.services.execution.ExecutionEngine` - Used by `create_execution_engine()`

**External Dependencies:**

- `logging` - Python standard library for logging functionality
- `logging.handlers.TimedRotatingFileHandler` - File rotation support
- `os` - Environment variable access
- `sys` - Standard output access for console logging
- `pathlib.Path` - File system operations for log directory creation

**Database Dependencies:**

- PostgreSQL - For execution checkpointing (connection string configuration)
- Environment variables for database connection parameters

**Environment Variables:**

URL Configuration:

- `API_BASE_URL` - Explicit API base URL override (highest priority)
- `BACKEND_URL` - Common deployment variable for backend URL
- `HOST` - Server host (default: "localhost")
- `PORT` - Server port (default: "8000")
- `USE_HTTPS` - Enable HTTPS protocol (default: "false")

Logging Configuration:

- `LOG_LEVEL` - Logging level (default: "INFO", options: DEBUG, INFO, WARNING, ERROR, CRITICAL)

Execution Configuration:

- `ENABLE_CHECKPOINTING` - Enable/disable checkpointing (default: "true")
- `ENABLE_MEMORY_SYSTEM` - Enable/disable memory system (default: "true")
- `DATABASE_URL` - PostgreSQL connection string (standard)
- `EXECUTION_POSTGRES_CONNECTION` - Alternative PostgreSQL connection string
- `KEY_POSTGRES_HOST` - PostgreSQL host (default: "localhost")
- `KEY_POSTGRES_DBNAME` - PostgreSQL database name (default: "langgraph")
- `KEY_POSTGRES_USER` - PostgreSQL user (default: "postgres")
- `KEY_POSTGRES_PASSWORD` - PostgreSQL password (default: "postgres")
- `KEY_POSTGRES_PORT` - PostgreSQL port (default: "5432")
- `KEY_POSTGRES_SSLMODE` - PostgreSQL SSL mode (default: "prefer")

## Public API

### Exported Functions

- `get_api_base_url()` - Get the dynamic API base URL from environment variables
- `get_endpoint_url(path: str)` - Construct complete endpoint URL by combining base URL with path
- `setup_logging(log_level=None)` - Initialise the comprehensive logging system
- `get_logger(name: str)` - Get a logger instance with the specified name
- `create_execution_engine(graph_manager)` - Create and initialise the execution engine

### Exported Classes

- `ExecutionConfig` - Static configuration class for execution engine settings

### Constants and Configuration

No constants are exported directly. All configuration is accessed through functions or static methods that read from
environment variables.

### Exceptions

This module does not define custom exceptions. It relies on standard Python exceptions:

- `OSError` - May be raised during log directory creation
- `ValueError` - May be raised for invalid log level values
- Environment-related exceptions from `os.getenv()` operations

## Core Classes

### `ExecutionConfig`

Static configuration class for the execution engine. Provides methods to access execution-related settings from
environment variables.

**Purpose:** Centralise execution engine configuration and provide a clean API for accessing execution settings
throughout the application.

**Responsibilities:**

- Determine execution engine type
- Check if checkpointing is enabled
- Check if memory system is enabled
- Resolve PostgreSQL connection string with multiple fallback options

**Initialisation:**

This is a static class with no instance methods. All methods are static and can be called directly on the class:

```python
# No initialisation needed - all methods are static
enabled = ExecutionConfig.use_checkpointing()
```

**Key Methods:**

#### `get_execution_engine_type()`

```python
@staticmethod
def get_execution_engine_type() -> str:
    """Get the execution engine type."""
```

**Returns:**

- `str` - Always returns `"execution_engine"` (simplified in Phase 4)

**Example:**

```python
from backend.services.config import ExecutionConfig

engine_type = ExecutionConfig.get_execution_engine_type()
print(f"Using engine: {engine_type}")  # Output: Using engine: execution_engine
```

**Behaviour:**

- Returns a constant string identifying the execution engine type
- Previously supported multiple engine types, now simplified to single production default
- Used internally by execution engine factory

**Use Cases:**

- Internal use by execution engine creation logic
- Logging and debugging execution engine configuration

#### `use_checkpointing()`

```python
@staticmethod
def use_checkpointing() -> bool:
    """Check if checkpointing is enabled (default: true)."""
```

**Returns:**

- `bool` - `True` if checkpointing is enabled, `False` otherwise

**Example:**

```python
from backend.services.config import ExecutionConfig

if ExecutionConfig.use_checkpointing():
    print("Checkpointing is enabled")
    # Initialise checkpointer
else:
    print("Checkpointing is disabled")
    # Skip checkpointer initialisation
```

**Behaviour:**

- Reads `ENABLE_CHECKPOINTING` environment variable
- Defaults to `True` if not set
- Case-insensitive comparison ("true", "True", "TRUE" all work)

**Use Cases:**

- Determining whether to initialise PostgreSQL checkpointer
- Conditional checkpoint creation during execution
- Feature flag for checkpointing functionality

#### `use_memory()`

```python
@staticmethod
def use_memory() -> bool:
    """Check if memory system is enabled globally."""
```

**Returns:**

- `bool` - `True` if memory system is enabled, `False` otherwise

**Example:**

```python
from backend.services.config import ExecutionConfig

if ExecutionConfig.use_memory():
    print("Memory system is enabled")
    # Initialise conversation memory
else:
    print("Memory system is disabled")
    # Skip memory initialisation
```

**Behaviour:**

- Reads `ENABLE_MEMORY_SYSTEM` environment variable
- Defaults to `True` if not set
- Case-insensitive comparison

**Use Cases:**

- Enabling or disabling conversation memory globally
- Conditional memory manager initialisation
- Feature flag for memory functionality

#### `get_postgres_connection_string()`

```python
@staticmethod
def get_postgres_connection_string() -> str:
    """Get PostgreSQL connection string for checkpointing."""
```

**Returns:**

- `str` - Complete PostgreSQL connection string with SSL mode

**Example:**

```python
from backend.services.config import ExecutionConfig

conn_string = ExecutionConfig.get_postgres_connection_string()
print(f"Connecting to: {conn_string}")
# Output: postgresql://user:password@host:5432/dbname?sslmode=prefer
```

**Behaviour:**

- Tries three methods in order of priority:
    1. `DATABASE_URL` environment variable (standard for most deployments)
    2. `EXECUTION_POSTGRES_CONNECTION` environment variable (execution-specific)
    3. Constructs from individual components (`KEY_POSTGRES_*` variables)
- Always includes SSL mode in the connection string
- Uses sensible defaults for local development

**Use Cases:**

- Initialising PostgreSQL checkpointer for LangGraph
- Connecting to execution history database
- Database connection pooling configuration

**Connection String Priority:**

```python
# Priority 1: Explicit DATABASE_URL
DATABASE_URL=postgresql://user:pass@prod.db.com:5432/prod

# Priority 2: Execution-specific connection
EXECUTION_POSTGRES_CONNECTION=postgresql://user:pass@exec.db.com:5432/exec

# Priority 3: Individual components (lowest priority)
KEY_POSTGRES_HOST=localhost
KEY_POSTGRES_DBNAME=langgraph
KEY_POSTGRES_USER=postgres
KEY_POSTGRES_PASSWORD=postgres
KEY_POSTGRES_PORT=5432
KEY_POSTGRES_SSLMODE=prefer
```

## Functions

### `get_api_base_url()`

Get the dynamic API base URL for the backend service with intelligent fallback logic.

**Signature:**

```python
def get_api_base_url() -> str:
    """
    Get the dynamic API base URL for the backend service.

    Checks environment variables in order of preference:
    1. API_BASE_URL (explicit override)
    2. BACKEND_URL (common deployment variable)
    3. Constructed from HOST and PORT
    4. Default to localhost:8000

    Returns:
        str: The base URL for the API (e.g., 'https://your-backend-url.example.com' or 'http://localhost:8000')
    """
```

**Returns:**

- `str` - Complete base URL with protocol, host, and port (trailing slash removed)

**Example:**

```python
from backend.services.config import get_api_base_url

# In production with API_BASE_URL set
base_url = get_api_base_url()
print(base_url)  # https://your-backend-url.example.com

# In local development
base_url = get_api_base_url()
print(base_url)  # http://localhost:8000

# With custom host and port
# HOST=0.0.0.0 PORT=3000
base_url = get_api_base_url()
print(base_url)  # http://0.0.0.0:3000
```

**Behaviour:**

- Tries environment variables in order: `API_BASE_URL` → `BACKEND_URL` → constructed from `HOST` and `PORT`
- Automatically removes trailing slashes for consistency
- Intelligently selects protocol (HTTP for localhost, HTTPS for remote hosts)
- Respects `USE_HTTPS` environment variable for custom deployments
- Always returns a valid URL string

**Use Cases:**

- Constructing webhook URLs for HTTP execution
- Building callback URLs for external services
- Generating public-facing API endpoint URLs
- Environment-agnostic URL generation

**Environment Resolution Logic:**

```python
# Priority 1: Explicit override
API_BASE_URL=https://api.mycompany.com

# Priority 2: Common deployment variable
BACKEND_URL=https://your-backend-url.example.com

# Priority 3: Constructed (automatic protocol selection)
HOST=localhost PORT=8000  → http://localhost:8000
HOST=api.example.com PORT=443 USE_HTTPS=true → https://api.example.com:443
HOST=127.0.0.1 PORT=5000 → http://127.0.0.1:5000
```

### `get_endpoint_url()`

Construct a complete endpoint URL by combining the base URL with a path.

**Signature:**

```python
def get_endpoint_url(path: str) -> str:
    """
    Get a complete endpoint URL by combining the base URL with a path.

    Args:
        path: The API path (e.g., '/api/http-execution/trigger/my-workflow')

    Returns:
        str: Complete URL
    """
```

**Parameters:**

- `path` (str) - API path to append to base URL (leading slash optional)

**Returns:**

- `str` - Complete URL with protocol, host, port, and path

**Example:**

```python
from backend.services.config import get_endpoint_url

# With leading slash
url = get_endpoint_url("/api/http-execution/trigger/my-workflow")
print(url)
# https://your-backend-url.example.com/api/http-execution/trigger/my-workflow

# Without leading slash (automatically added)
url = get_endpoint_url("api/graphs/123/execute")
print(url)
# https://your-backend-url.example.com/api/graphs/123/execute

# With query parameters
url = get_endpoint_url("/api/memory?user_id=123")
print(url)
# http://localhost:8000/api/memory?user_id=123
```

**Behaviour:**

- Automatically prepends leading slash if missing
- Uses `get_api_base_url()` internally for environment-aware base URL
- Preserves query parameters and fragments in the path
- Returns properly formatted URL string

**Use Cases:**

- Generating webhook trigger URLs for published workflows
- Building callback URLs for email checkpoints
- Creating SSE endpoint URLs for real-time updates
- Constructing API endpoint URLs in responses

### `setup_logging()`

Set up comprehensive logging configuration for the application with file rotation and specialised loggers.

**Signature:**

```python
def setup_logging(log_level=None) -> logging.Logger:
    """Set up comprehensive logging configuration for the application.

    Args:
        log_level: Logging level to use. If None, reads from LOG_LEVEL env var (defaults to INFO)

    Returns:
        logging.Logger: The configured root logger
    """
```

**Parameters:**

- `log_level` (int, optional) - Logging level constant from `logging` module (e.g., `logging.DEBUG`). If `None`, reads
  from `LOG_LEVEL` environment variable (default: `INFO`)

**Returns:**

- `logging.Logger` - The configured root logger instance

**Example:**

```python
from backend.services.config import setup_logging
import logging

# Basic setup (uses LOG_LEVEL environment variable or defaults to INFO)
logger = setup_logging()
logger.info("Application started")

# Explicit log level
logger = setup_logging(log_level=logging.DEBUG)
logger.debug("Debug logging enabled")

# Can be called multiple times safely (only initialises once)
setup_logging()  # No-op, already initialized
setup_logging(logging.WARNING)  # No-op, already initialized
```

**Behaviour:**

- **Idempotent:** Can be called multiple times but only initialises once
- **Creates log directory:** Creates `logs/` directory if it doesn't exist
- **File rotation:** Rotates log files daily, keeps 7 days of backups
- **Multiple log files:**
  - `logs/app.log` - All application logs
  - `logs/execution.log` - Execution-specific logs (DEBUG level)
  - `logs/api.log` - API-specific logs (DEBUG level)
- **Console output:** UTF-8 encoded console handler for stdout
- **Formatters:**
  - Detailed formatter for files: `%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s`
  - Simple formatter for console: `%(asctime)s - %(levelname)s - %(message)s`
- **Specialised loggers:**
  - `execution` logger → `logs/execution.log`
  - `api` logger → `logs/api.log`
  - `database` logger → INFO level minimum
- **Non-propagating:** Specialised loggers don't propagate to root logger (prevents duplicates)

**Use Cases:**

- Application startup initialisation
- Setting up logging before any other operations
- Configuring different log levels for development vs production
- Ensuring consistent logging across the entire application

**Log Level Configuration:**

```python
# Via environment variable
# LOG_LEVEL=DEBUG
setup_logging()  # Uses DEBUG level

# Via parameter (highest priority)
setup_logging(log_level=logging.WARNING)

# Default (no env var, no parameter)
setup_logging()  # Uses INFO level
```

### `get_logger()`

Get a logger instance with the specified name. This is the standard way to create loggers throughout the application.

**Signature:**

```python
def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
```

**Parameters:**

- `name` (str) - Name for the logger (typically module name or component name)

**Returns:**

- `logging.Logger` - Logger instance configured by `setup_logging()`

**Example:**

```python
from backend.services.config import get_logger

# Get logger for current module
logger = get_logger(__name__)
logger.info("Processing request")

# Get logger with custom name
api_logger = get_logger("api")
api_logger.debug("API request received")

# Get logger for specific component
execution_logger = get_logger("execution")
execution_logger.info("Starting workflow execution")

# Use in exception handling
try:
    result = process_data()
except Exception as e:
    logger.error(f"Error processing data: {e}", exc_info=True)
```

**Behaviour:**

- Returns a named logger from Python's logging system
- Logger configuration is determined by `setup_logging()`
- Specialised logger names (`execution`, `api`) get their own log files
- All other loggers log to `logs/app.log` and console
- Inherits log level from root logger unless explicitly set

**Use Cases:**

- Creating module-level loggers (standard pattern: `logger = get_logger(__name__)`)
- Getting specialised loggers for specific components
- Consistent logging across the application
- Structured logging with named loggers

**Logger Naming Conventions:**

```python
# Module-level logger (recommended)
logger = get_logger(__name__)  # e.g., "backend.services.graph.builder"

# Component-specific loggers
api_logger = get_logger("api")  # → logs/api.log
execution_logger = get_logger("execution")  # → logs/execution.log
db_logger = get_logger("database")  # → logs/app.log (INFO level minimum)

# Feature-specific loggers
checkpoint_logger = get_logger("execution.checkpoint")
memory_logger = get_logger("execution.memory")
```

### `create_execution_engine()`

Create and initialise the execution engine with the provided graph manager.

**Signature:**

```python
def create_execution_engine(graph_manager: GraphManager) -> ExecutionEngine:
    """Create the execution engine."""
```

**Parameters:**

- `graph_manager` (GraphManager) - Graph manager instance for building and compiling workflows

**Returns:**

- `ExecutionEngine` - Configured execution engine instance

**Example:**

```python
from backend.services.config import create_execution_engine
from backend.services.graph import GraphManager

# Get graph manager (usually via dependency injection)
graph_manager = GraphManager()

# Create execution engine
engine = create_execution_engine(graph_manager)

# Use execution engine
result = await engine.execute_graph(
    graph_id="workflow-123",
    input_data={"message": "Hello"},
)
```

**Behaviour:**

- Creates an `ExecutionEngine` instance with the provided graph manager
- Logs engine creation at INFO level
- Engine is configured based on `ExecutionConfig` settings
- Returns ready-to-use execution engine instance

**Use Cases:**

- Application startup to initialise execution engine
- Dependency injection setup
- Testing execution engine with mock graph manager

## Configuration

### Environment Variables

**URL Configuration:**

- `API_BASE_URL` - Explicit API base URL override (default: None, required: no)
  - Highest priority override for the API base URL
  - Example: `https://api.mycompany.com`
  - Use when you need complete control over the base URL

- `BACKEND_URL` - Common deployment variable for backend URL (default: None, required: no)
  - Second priority, commonly used in cloud deployments
  - Example: `https://your-backend-url.example.com`
  - Azure App Service sets this automatically

- `HOST` - Server host (default: "localhost", required: no)
  - Used when `API_BASE_URL` and `BACKEND_URL` are not set
  - Example: `0.0.0.0` for Docker, `api.example.com` for custom domain

- `PORT` - Server port (default: "8000", required: no)
  - Used with `HOST` to construct base URL
  - Example: `3000`, `80`, `443`

- `USE_HTTPS` - Enable HTTPS protocol (default: "false", required: no)
  - Only used when constructing URL from `HOST` and `PORT`
  - Automatically `true` for non-localhost hosts
  - Example: `true` for custom domains with SSL

**Logging Configuration:**

- `LOG_LEVEL` - Logging level (default: "INFO", required: no)
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Case-insensitive
  - Example: `LOG_LEVEL=DEBUG` for development

**Execution Configuration:**

- `ENABLE_CHECKPOINTING` - Enable/disable checkpointing (default: "true", required: no)
  - Controls whether workflow state is persisted to PostgreSQL
  - Example: `ENABLE_CHECKPOINTING=false` to disable

- `ENABLE_MEMORY_SYSTEM` - Enable/disable memory system (default: "true", required: no)
  - Controls whether conversation memory is enabled globally
  - Example: `ENABLE_MEMORY_SYSTEM=false` to disable

**PostgreSQL Configuration (for checkpointing):**

- `DATABASE_URL` - PostgreSQL connection string (default: None, required: no)
  - Standard connection string format, highest priority
  - Example: `postgresql://user:password@host:5432/dbname?sslmode=require`

- `EXECUTION_POSTGRES_CONNECTION` - Alternative PostgreSQL connection string (default: None, required: no)
  - Execution-specific connection string, second priority
  - Example: `postgresql://execuser:execpass@exechost:5432/execdb`

- `KEY_POSTGRES_HOST` - PostgreSQL host (default: "localhost", required: no)
  - Used when building connection string from components
  - Example: `postgres.mycompany.com`

- `KEY_POSTGRES_DBNAME` - PostgreSQL database name (default: "langgraph", required: no)
  - Database name for checkpointing
  - Example: `agenticstudio_prod`

- `KEY_POSTGRES_USER` - PostgreSQL user (default: "postgres", required: no)
  - Database user for checkpointing
  - Example: `agenticstudio_user`

- `KEY_POSTGRES_PASSWORD` - PostgreSQL password (default: "postgres", required: no)
  - Database password for checkpointing
  - Example: `secure_password_123`

- `KEY_POSTGRES_PORT` - PostgreSQL port (default: "5432", required: no)
  - Database port for checkpointing
  - Example: `5433` for non-standard port

- `KEY_POSTGRES_SSLMODE` - PostgreSQL SSL mode (default: "prefer", required: no)
  - SSL connection mode for PostgreSQL
  - Options: `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full`
  - Example: `require` for production

### Initialisation Patterns

**Basic Logging Initialisation:**

```python
from backend.services.config import setup_logging, get_logger

# Set up logging once at application startup
setup_logging()

# Get loggers throughout the application
logger = get_logger(__name__)
logger.info("Application started")
```

**Advanced Logging Initialisation:**

```python
import logging
from backend.services.config import setup_logging, get_logger

# Set up logging with explicit log level
setup_logging(log_level=logging.DEBUG)

# Get specialised loggers
api_logger = get_logger("api")
execution_logger = get_logger("execution")

# Use loggers
api_logger.info("API server started")
execution_logger.debug("Execution engine initialised")
```

**URL Configuration:**

```python
from backend.services.config import get_api_base_url, get_endpoint_url

# Get base URL (environment-aware)
base_url = get_api_base_url()
print(f"API Base URL: {base_url}")

# Build complete endpoint URLs
trigger_url = get_endpoint_url("/api/http-execution/trigger/my-workflow")
webhook_url = get_endpoint_url("/api/webhooks/callback")

print(f"Trigger URL: {trigger_url}")
print(f"Webhook URL: {webhook_url}")
```

**Execution Engine Configuration:**

```python
from backend.services.config import ExecutionConfig, create_execution_engine
from backend.services.graph import GraphManager

# Check configuration
if ExecutionConfig.use_checkpointing():
    conn_string = ExecutionConfig.get_postgres_connection_string()
    print(f"Checkpointing enabled: {conn_string}")

if ExecutionConfig.use_memory():
    print("Memory system enabled")

# Create execution engine
graph_manager = GraphManager()
engine = create_execution_engine(graph_manager)
```

**Complete Application Setup:**

```python
import logging
from backend.services.config import (
    setup_logging,
    get_logger,
    ExecutionConfig,
    create_execution_engine,
    get_api_base_url,
)
from backend.services.graph import GraphManager

# 1. Set up logging first
setup_logging(log_level=logging.INFO)
logger = get_logger(__name__)

# 2. Log configuration
logger.info(f"API Base URL: {get_api_base_url()}")
logger.info(f"Checkpointing: {ExecutionConfig.use_checkpointing()}")
logger.info(f"Memory System: {ExecutionConfig.use_memory()}")

# 3. Create execution engine
graph_manager = GraphManager()
engine = create_execution_engine(graph_manager)

logger.info("Application initialised successfully")
```

### Dependency Injection

The config service is typically imported directly rather than injected, as it provides foundational configuration
utilities:

```python
# In FastAPI application
from fastapi import FastAPI
from backend.services.config import setup_logging, get_logger

app = FastAPI()

# Set up logging at application startup
@app.on_event("startup")
async def startup_event():
    setup_logging()
    logger = get_logger(__name__)
    logger.info("FastAPI application started")

# Use logger in routes
@app.get("/health")
async def health_check():
    logger = get_logger(__name__)
    logger.debug("Health check requested")
    return {"status": "healthy"}
```

## Error Handling

### Exception Hierarchy

The config module does not define custom exceptions. It relies on standard Python exceptions:

```
Exception
├── OSError
│   └── Raised during log directory creation if permissions are insufficient
├── ValueError
│   └── Raised for invalid log level strings
└── AttributeError
    └── Raised when accessing invalid environment variables
```

### Error Handling Patterns

**Logging Setup Error Handling:**

```python
from backend.services.config import setup_logging, get_logger
import logging

try:
    # Set up logging
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Logging initialised successfully")
except OSError as e:
    # Handle log directory creation errors
    print(f"Failed to create log directory: {e}")
    # Fallback to console-only logging
    logging.basicConfig(level=logging.INFO)
except ValueError as e:
    # Handle invalid log level
    print(f"Invalid log level configuration: {e}")
    setup_logging()  # Use default INFO level
```

**Environment Variable Error Handling:**

```python
from backend.services.config import ExecutionConfig, get_logger

logger = get_logger(__name__)

try:
    # Get PostgreSQL connection string
    conn_string = ExecutionConfig.get_postgres_connection_string()
    logger.info(f"Using connection: {conn_string}")
except Exception as e:
    # Handle connection string errors
    logger.error(f"Failed to get PostgreSQL connection string: {e}")
    # Use fallback or raise
    raise RuntimeError("Database configuration is required") from e
```

**URL Configuration Error Handling:**

```python
from backend.services.config import get_api_base_url, get_endpoint_url, get_logger

logger = get_logger(__name__)

try:
    # Get base URL and build endpoint
    base_url = get_api_base_url()
    endpoint = get_endpoint_url("/api/trigger/workflow")

    logger.info(f"Generated endpoint: {endpoint}")
except Exception as e:
    # Handle URL configuration errors
    logger.error(f"Failed to generate endpoint URL: {e}")
    # Use fallback URL
    endpoint = "http://localhost:8000/api/trigger/workflow"
```

**Recommended Pattern:**

```python
from backend.services.config import setup_logging, get_logger, ExecutionConfig
import logging
import sys

def initialise_application():
    """Initialise application with comprehensive error handling."""

    try:
        # 1. Set up logging
        setup_logging()
        logger = get_logger(__name__)

        # 2. Verify execution configuration
        if ExecutionConfig.use_checkpointing():
            try:
                conn_string = ExecutionConfig.get_postgres_connection_string()
                logger.info("Checkpointing enabled")
            except Exception as e:
                logger.error(f"Checkpointing configuration error: {e}")
                raise

        # 3. Log successful initialisation
        logger.info("Application initialised successfully")
        return True

    except OSError as e:
        print(f"CRITICAL: Failed to set up logging: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"CRITICAL: Application initialisation failed: {e}", file=sys.stderr)
        sys.exit(1)

# Run initialisation
if __name__ == "__main__":
    initialise_application()
```

## Integration Patterns

### Integration with API Layer

The config service is used extensively in the API layer for logging and URL generation:

```python
# backend/api/http_execution/routes.py
from fastapi import APIRouter, HTTPException
from backend.services.config import get_logger, get_endpoint_url

router = APIRouter()
logger = get_logger(__name__)

@router.post("/trigger/{workflow_id}")
async def trigger_workflow(workflow_id: str):
    """Trigger a published workflow via HTTP."""

    # Log API request
    logger.info(f"Triggering workflow: {workflow_id}")

    try:
        # Generate callback URL
        callback_url = get_endpoint_url(f"/api/http-execution/callback/{workflow_id}")

        logger.debug(f"Callback URL: {callback_url}")

        # Execute workflow
        result = await execute_workflow(workflow_id, callback_url)

        logger.info(f"Workflow {workflow_id} executed successfully")
        return result

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### Integration with Execution Service

The config service provides execution engine configuration:

```python
# backend/services/execution/engine.py
from backend.services.config import get_logger, ExecutionConfig
from backend.services.execution.checkpointer import initialize_checkpointer

logger = get_logger(__name__)

class ExecutionEngine:
    """Workflow execution engine."""

    def __init__(self, graph_manager):
        self.graph_manager = graph_manager
        self.checkpointer = None

        # Use ExecutionConfig to determine if checkpointing is enabled
        if ExecutionConfig.use_checkpointing():
            logger.info("Initialising checkpointer")
            conn_string = ExecutionConfig.get_postgres_connection_string()
            self.checkpointer = initialize_checkpointer(conn_string)
        else:
            logger.warning("Checkpointing is disabled")

        # Check memory configuration
        if ExecutionConfig.use_memory():
            logger.info("Memory system enabled")
        else:
            logger.warning("Memory system disabled")
```

### Integration with Other Services

The config service is used across all backend services for consistent logging:

```python
# backend/services/graph/builder.py
from backend.services.config import get_logger

logger = get_logger(__name__)

class GraphBuilder:
    """Build LangGraph workflows from graph definitions."""

    def build_graph(self, graph_id: str):
        """Build a graph from definition."""

        logger.info(f"Building graph: {graph_id}")

        try:
            # Build graph logic
            graph = self._construct_graph(graph_id)

            logger.debug(f"Graph {graph_id} has {len(graph.nodes)} nodes")
            logger.info(f"Graph {graph_id} built successfully")

            return graph

        except Exception as e:
            logger.error(f"Failed to build graph {graph_id}: {e}", exc_info=True)
            raise
```

### Dependency Flow

```
Config Service
├── Provides logging to:
│   ├── API Layer (all routes and handlers)
│   ├── Execution Service (engine, executors, handlers)
│   ├── Graph Service (builder, manager, compilation)
│   ├── Memory Service (manager, repository)
│   ├── Database Service (connections, queries)
│   └── All other backend services
│
├── Provides URL configuration to:
│   ├── HTTP Execution (trigger URLs, callbacks)
│   ├── Email Checkpoints (resume URLs)
│   ├── Workflow Publishing (public endpoints)
│   └── Webhook Handlers (callback URLs)
│
└── Provides execution configuration to:
    ├── Execution Engine (checkpointing, memory)
    ├── Graph Manager (execution engine creation)
    └── Checkpoint Service (PostgreSQL connection)
```

### Common Integration Patterns

#### Pattern 1: Module-Level Logger

```python
# Standard pattern used throughout the codebase
from backend.services.config import get_logger

# Create module-level logger
logger = get_logger(__name__)

class MyService:
    """Example service with logging."""

    def process(self, data):
        """Process data with logging."""
        logger.info("Processing data")

        try:
            result = self._do_process(data)
            logger.debug(f"Processing result: {result}")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise
```

#### Pattern 2: Application Startup

```python
# Application initialisation pattern
from fastapi import FastAPI
from backend.services.config import setup_logging, get_logger, create_execution_engine
from backend.services.graph import GraphManager

app = FastAPI()

@app.on_event("startup")
async def startup():
    """Initialise application on startup."""

    # 1. Set up logging first
    setup_logging()
    logger = get_logger(__name__)

    # 2. Initialise services
    graph_manager = GraphManager()
    execution_engine = create_execution_engine(graph_manager)

    # 3. Store in app state
    app.state.graph_manager = graph_manager
    app.state.execution_engine = execution_engine

    logger.info("Application startup complete")
```

#### Pattern 3: Environment-Aware URL Generation

```python
# Generate environment-aware URLs
from backend.services.config import get_endpoint_url, get_logger

logger = get_logger(__name__)

def create_workflow_trigger_url(workflow_slug: str) -> str:
    """Create trigger URL for published workflow."""

    # Automatically uses correct base URL for environment
    trigger_url = get_endpoint_url(f"/api/http-execution/trigger/{workflow_slug}")

    logger.debug(f"Generated trigger URL: {trigger_url}")

    return trigger_url

# Works in all environments:
# - Local: http://localhost:8000/api/http-execution/trigger/my-workflow
# - Staging: https://staging-api.example.com/api/http-execution/trigger/my-workflow
# - Production: https://api.example.com/api/http-execution/trigger/my-workflow
```

#### Pattern 4: Feature Flag Usage

```python
# Use execution configuration as feature flags
from backend.services.config import ExecutionConfig, get_logger

logger = get_logger(__name__)

def execute_workflow(graph_id: str, input_data: dict):
    """Execute workflow with configuration-based features."""

    # Check if checkpointing is enabled
    if ExecutionConfig.use_checkpointing():
        logger.info("Executing with checkpointing")
        return execute_with_checkpoints(graph_id, input_data)
    else:
        logger.info("Executing without checkpointing")
        return execute_stateless(graph_id, input_data)

def build_agent(agent_config: dict):
    """Build agent with optional memory."""

    # Check if memory is enabled
    if ExecutionConfig.use_memory():
        logger.info("Building agent with memory")
        agent_config["memory"] = True
    else:
        logger.info("Building agent without memory")
        agent_config["memory"] = False

    return create_agent(agent_config)
```

## Usage Examples

### Example 1: Basic Logging Setup

Complete example showing how to set up logging and use loggers:

```python
from backend.services.config import setup_logging, get_logger

# Step 1: Set up logging once at application startup
setup_logging()

# Step 2: Get logger for your module
logger = get_logger(__name__)

# Step 3: Use logger throughout your code
logger.info("Application started")
logger.debug("Debug information")
logger.warning("Warning message")
logger.error("Error occurred")

# Step 4: Log exceptions with stack traces
try:
    result = 1 / 0
except Exception as e:
    logger.error(f"Division error: {e}", exc_info=True)
```

### Example 2: Environment-Aware URL Configuration

Complete example showing URL generation in different environments:

```python
from backend.services.config import get_api_base_url, get_endpoint_url, get_logger

# Set up logging
logger = get_logger(__name__)

# Get base URL (automatically selects correct environment)
base_url = get_api_base_url()
logger.info(f"API Base URL: {base_url}")

# Build complete endpoint URLs
trigger_url = get_endpoint_url("/api/http-execution/trigger/my-workflow")
callback_url = get_endpoint_url("/api/webhooks/callback/12345")
health_url = get_endpoint_url("/health")

# Log URLs
logger.info(f"Trigger URL: {trigger_url}")
logger.info(f"Callback URL: {callback_url}")
logger.info(f"Health URL: {health_url}")

# Use URLs in application
def send_webhook(workflow_id: str, data: dict):
    """Send webhook with environment-aware URL."""
    webhook_url = get_endpoint_url(f"/api/webhooks/{workflow_id}")

    # Send HTTP request to webhook_url
    # ...

    logger.info(f"Webhook sent to: {webhook_url}")

# Example output in different environments:
# Local:      http://localhost:8000/api/http-execution/trigger/my-workflow
# Production: https://your-backend-url.example.com/api/http-execution/trigger/my-workflow
```

### Example 3: Complete Application Initialisation

Realistic example showing complete application setup with configuration:

```python
import logging
import sys
from fastapi import FastAPI
from backend.services.config import (
    setup_logging,
    get_logger,
    ExecutionConfig,
    create_execution_engine,
    get_api_base_url,
)
from backend.services.graph import GraphManager

# Create FastAPI app
app = FastAPI(title="AgenticStudio Backend")

async def initialise_application():
    """Initialise application with comprehensive configuration."""

    try:
        # Step 1: Set up logging first
        setup_logging(log_level=logging.INFO)
        logger = get_logger(__name__)
        logger.info("=== Application Initialisation ===")

        # Step 2: Log environment configuration
        base_url = get_api_base_url()
        logger.info(f"API Base URL: {base_url}")

        # Step 3: Log execution configuration
        checkpointing_enabled = ExecutionConfig.use_checkpointing()
        memory_enabled = ExecutionConfig.use_memory()

        logger.info(f"Checkpointing: {'enabled' if checkpointing_enabled else 'disabled'}")
        logger.info(f"Memory System: {'enabled' if memory_enabled else 'disabled'}")

        # Step 4: Get PostgreSQL connection if checkpointing is enabled
        if checkpointing_enabled:
            conn_string = ExecutionConfig.get_postgres_connection_string()
            # Mask password in logs
            safe_conn = conn_string.split('@')[1] if '@' in conn_string else conn_string
            logger.info(f"PostgreSQL: {safe_conn}")

        # Step 5: Create execution engine
        graph_manager = GraphManager()
        execution_engine = create_execution_engine(graph_manager)

        # Step 6: Store in app state
        app.state.graph_manager = graph_manager
        app.state.execution_engine = execution_engine

        logger.info("=== Application Initialised Successfully ===")
        return True

    except Exception as e:
        print(f"CRITICAL: Application initialisation failed: {e}", file=sys.stderr)
        sys.exit(1)

# FastAPI startup event
@app.on_event("startup")
async def startup_event():
    """Run initialisation on startup."""
    await initialise_application()

# Example route using logger
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger = get_logger(__name__)
    logger.debug("Health check requested")

    return {
        "status": "healthy",
        "checkpointing": ExecutionConfig.use_checkpointing(),
        "memory": ExecutionConfig.use_memory(),
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Example 4: Testing Usage

Show how to use the config service in tests:

```python
import pytest
import logging
from unittest.mock import patch
from backend.services.config import (
    setup_logging,
    get_logger,
    get_api_base_url,
    get_endpoint_url,
    ExecutionConfig,
)

def test_logging_setup():
    """Test logging setup."""
    # Set up logging
    logger = setup_logging(log_level=logging.DEBUG)

    # Verify logger is configured
    assert logger is not None
    assert logger.level == logging.DEBUG

def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test")

    # Verify logger has correct name
    assert logger.name == "test"

@patch.dict('os.environ', {'API_BASE_URL': 'https://test-api.example.com'})
def test_get_api_base_url_with_override():
    """Test API base URL with explicit override."""
    base_url = get_api_base_url()

    assert base_url == "https://test-api.example.com"

@patch.dict('os.environ', {'HOST': 'localhost', 'PORT': '3000'})
def test_get_api_base_url_constructed():
    """Test API base URL constructed from components."""
    base_url = get_api_base_url()

    assert base_url == "http://localhost:3000"

def test_get_endpoint_url():
    """Test endpoint URL construction."""
    with patch('backend.services.config.url.get_api_base_url', return_value='http://localhost:8000'):
        endpoint = get_endpoint_url("/api/test")

        assert endpoint == "http://localhost:8000/api/test"

def test_get_endpoint_url_without_leading_slash():
    """Test endpoint URL construction without leading slash."""
    with patch('backend.services.config.url.get_api_base_url', return_value='http://localhost:8000'):
        endpoint = get_endpoint_url("api/test")

        assert endpoint == "http://localhost:8000/api/test"

@patch.dict('os.environ', {'ENABLE_CHECKPOINTING': 'true'})
def test_use_checkpointing_enabled():
    """Test checkpointing configuration."""
    assert ExecutionConfig.use_checkpointing() is True

@patch.dict('os.environ', {'ENABLE_CHECKPOINTING': 'false'})
def test_use_checkpointing_disabled():
    """Test checkpointing disabled."""
    assert ExecutionConfig.use_checkpointing() is False

@patch.dict('os.environ', {
    'KEY_POSTGRES_HOST': 'testhost',
    'KEY_POSTGRES_DBNAME': 'testdb',
    'KEY_POSTGRES_USER': 'testuser',
    'KEY_POSTGRES_PASSWORD': 'testpass',
    'KEY_POSTGRES_PORT': '5433',
    'KEY_POSTGRES_SSLMODE': 'require',
})
def test_get_postgres_connection_string():
    """Test PostgreSQL connection string construction."""
    conn_string = ExecutionConfig.get_postgres_connection_string()

    assert 'testhost' in conn_string
    assert 'testdb' in conn_string
    assert 'testuser' in conn_string
    assert 'testpass' in conn_string
    assert '5433' in conn_string
    assert 'sslmode=require' in conn_string

@pytest.fixture
def mock_graph_manager():
    """Mock graph manager for testing."""
    from unittest.mock import Mock
    return Mock()

def test_create_execution_engine(mock_graph_manager):
    """Test execution engine creation."""
    from backend.services.config import create_execution_engine

    engine = create_execution_engine(mock_graph_manager)

    assert engine is not None
    assert engine.graph_manager == mock_graph_manager
```

## Performance Considerations

### Performance Characteristics

**Logging Operations:**

- `setup_logging()` - O(1) complexity, runs once at startup
- `get_logger(name)` - O(1) lookup in logger registry
- File rotation - Handled by Python's logging module, minimal overhead
- Log writes - Buffered I/O, asynchronous file writes

**URL Configuration:**

- `get_api_base_url()` - O(1) environment variable lookups with string operations
- `get_endpoint_url(path)` - O(1) string concatenation

**Execution Configuration:**

- All `ExecutionConfig` methods - O(1) environment variable reads with minimal string processing
- Connection string construction - O(1) string formatting

**Memory Usage:**

- Logging system creates one root logger and 3 specialised loggers
- Log file handlers with 7-day rotation (automatic cleanup)
- Minimal memory footprint for configuration utilities

### Optimisation Tips

#### Tip 1: Logger Caching

**Problem:**

```python
# Inefficient: Creating logger on every request
def process_request(data):
    logger = get_logger(__name__)  # Lookup on every call
    logger.info("Processing request")
```

**Solution:**

```python
# Efficient: Create logger once at module level
logger = get_logger(__name__)  # Created once

def process_request(data):
    logger.info("Processing request")  # Reuse logger
```

#### Tip 2: URL Caching for Static Endpoints

**Problem:**

```python
# Inefficient: Regenerating URL on every call
def get_callback_url():
    return get_endpoint_url("/api/callback")  # Regenerates every time
```

**Solution:**

```python
# Efficient: Cache URL at module level if it doesn't change
CALLBACK_URL = get_endpoint_url("/api/callback")  # Generated once

def get_callback_url():
    return CALLBACK_URL  # Return cached value
```

#### Tip 3: Configuration Caching

**Problem:**

```python
# Inefficient: Reading environment variable on every check
def execute_workflow(graph_id: str):
    if ExecutionConfig.use_checkpointing():  # ENV var read
        # ...
    if ExecutionConfig.use_memory():  # ENV var read
        # ...
```

**Solution:**

```python
# Efficient: Cache configuration at application startup
CHECKPOINTING_ENABLED = ExecutionConfig.use_checkpointing()
MEMORY_ENABLED = ExecutionConfig.use_memory()

def execute_workflow(graph_id: str):
    if CHECKPOINTING_ENABLED:  # Cached value
        # ...
    if MEMORY_ENABLED:  # Cached value
        # ...
```

#### Tip 4: Conditional Logging

**Problem:**

```python
# Inefficient: String formatting even when not logging
logger.debug(f"Complex data: {json.dumps(large_object)}")  # Always formats
```

**Solution:**

```python
# Efficient: Only format if debug logging is enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Complex data: {json.dumps(large_object)}")
```

### Log File Management

**Automatic Rotation:**

```python
# Log files rotate automatically at midnight
# Keeps 7 days of backups
# Old files are automatically deleted

# logs/app.log          - Current log
# logs/app.log.2025-01-20  - Yesterday's log
# logs/app.log.2025-01-19  - 2 days ago
# ...
# logs/app.log.2025-01-14  - 7 days ago (oldest kept)
```

**Manual Cleanup (if needed):**

```python
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_logs(days_to_keep: int = 7):
    """Manually clean up log files older than specified days."""
    log_dir = Path("logs")
    cutoff = datetime.now() - timedelta(days=days_to_keep)

    for log_file in log_dir.glob("*.log.*"):
        if log_file.stat().st_mtime < cutoff.timestamp():
            log_file.unlink()
            print(f"Deleted old log file: {log_file}")
```

## Testing Patterns

### Unit Testing

```python
import pytest
import logging
from unittest.mock import patch, Mock
from backend.services.config import (
    setup_logging,
    get_logger,
    get_api_base_url,
    get_endpoint_url,
    ExecutionConfig,
)

@pytest.fixture
def reset_logging():
    """Reset logging state between tests."""
    # Reset the global flag
    import backend.services.config.logging as logging_module
    logging_module._logging_initialized = False
    yield
    # Clean up loggers after test
    logging.getLogger().handlers.clear()

def test_setup_logging(reset_logging):
    """Test logging setup with explicit level."""
    logger = setup_logging(log_level=logging.WARNING)

    assert logger.level == logging.WARNING
    assert len(logger.handlers) > 0

def test_setup_logging_idempotent(reset_logging):
    """Test that setup_logging can be called multiple times."""
    logger1 = setup_logging()
    logger2 = setup_logging()

    # Should return same logger
    assert logger1 is logger2

def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test.module")

    assert logger.name == "test.module"
    assert isinstance(logger, logging.Logger)

@patch.dict('os.environ', {'API_BASE_URL': 'https://api.example.com'})
def test_get_api_base_url_explicit():
    """Test API base URL with explicit override."""
    base_url = get_api_base_url()
    assert base_url == "https://api.example.com"

@patch.dict('os.environ', {'BACKEND_URL': 'https://backend.example.com'})
def test_get_api_base_url_backend():
    """Test API base URL from BACKEND_URL."""
    base_url = get_api_base_url()
    assert base_url == "https://backend.example.com"

@patch.dict('os.environ', {'HOST': 'api.test.com', 'PORT': '443', 'USE_HTTPS': 'true'})
def test_get_api_base_url_constructed():
    """Test API base URL constructed from components."""
    base_url = get_api_base_url()
    assert base_url == "https://api.test.com:443"

def test_get_endpoint_url():
    """Test endpoint URL construction."""
    with patch('backend.services.config.url.get_api_base_url', return_value='http://localhost:8000'):
        url = get_endpoint_url("/api/test")
        assert url == "http://localhost:8000/api/test"

def test_get_endpoint_url_adds_leading_slash():
    """Test endpoint URL adds leading slash if missing."""
    with patch('backend.services.config.url.get_api_base_url', return_value='http://localhost:8000'):
        url = get_endpoint_url("api/test")
        assert url == "http://localhost:8000/api/test"

@patch.dict('os.environ', {'ENABLE_CHECKPOINTING': 'true'})
def test_execution_config_checkpointing_enabled():
    """Test checkpointing enabled."""
    assert ExecutionConfig.use_checkpointing() is True

@patch.dict('os.environ', {'ENABLE_CHECKPOINTING': 'false'})
def test_execution_config_checkpointing_disabled():
    """Test checkpointing disabled."""
    assert ExecutionConfig.use_checkpointing() is False

@patch.dict('os.environ', {'ENABLE_MEMORY_SYSTEM': 'true'})
def test_execution_config_memory_enabled():
    """Test memory system enabled."""
    assert ExecutionConfig.use_memory() is True

@patch.dict('os.environ', {
    'DATABASE_URL': 'postgresql://user:pass@host:5432/db?sslmode=require'
})
def test_get_postgres_connection_string_database_url():
    """Test PostgreSQL connection from DATABASE_URL."""
    conn = ExecutionConfig.get_postgres_connection_string()
    assert conn == 'postgresql://user:pass@host:5432/db?sslmode=require'

def test_execution_config_get_execution_engine_type():
    """Test execution engine type."""
    engine_type = ExecutionConfig.get_execution_engine_type()
    assert engine_type == "execution_engine"
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch, MagicMock
import pytest

@patch('backend.services.config.execution.get_logger')
def test_create_execution_engine_with_mock_logger(mock_get_logger):
    """Test execution engine creation with mocked logger."""
    from backend.services.config import create_execution_engine

    # Set up mock logger
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger

    # Create mock graph manager
    mock_graph_manager = Mock()

    # Create execution engine
    with patch('backend.services.config.execution.ExecutionEngine'):
        engine = create_execution_engine(mock_graph_manager)

        # Verify logger was called
        mock_logger.info.assert_called_once()

@patch('backend.services.config.url.os.getenv')
def test_get_api_base_url_with_mock_env(mock_getenv):
    """Test API base URL with mocked environment."""
    # Mock environment variables
    def getenv_side_effect(key, default=None):
        env_vars = {
            'API_BASE_URL': None,
            'BACKEND_URL': None,
            'HOST': 'testhost',
            'PORT': '9000',
            'USE_HTTPS': 'false',
        }
        return env_vars.get(key, default)

    mock_getenv.side_effect = getenv_side_effect

    from backend.services.config import get_api_base_url
    base_url = get_api_base_url()

    assert base_url == "http://testhost:9000"
```

### Integration Testing

```python
import pytest
from pathlib import Path

@pytest.mark.integration
def test_logging_creates_log_files():
    """Integration test: verify log files are created."""
    from backend.services.config import setup_logging, get_logger

    # Set up logging
    setup_logging()
    logger = get_logger("integration_test")

    # Write log message
    logger.info("Integration test message")

    # Verify log files exist
    log_dir = Path("logs")
    assert log_dir.exists()
    assert (log_dir / "app.log").exists()

@pytest.mark.integration
def test_complete_configuration_integration():
    """Integration test: test complete configuration flow."""
    from backend.services.config import (
        setup_logging,
        get_logger,
        ExecutionConfig,
        get_api_base_url,
        get_endpoint_url,
    )

    # Set up logging
    setup_logging()
    logger = get_logger(__name__)

    # Test URL configuration
    base_url = get_api_base_url()
    endpoint = get_endpoint_url("/api/test")

    assert endpoint.startswith(base_url)

    # Test execution configuration
    checkpointing = ExecutionConfig.use_checkpointing()
    memory = ExecutionConfig.use_memory()

    assert isinstance(checkpointing, bool)
    assert isinstance(memory, bool)

    # Log results
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Endpoint: {endpoint}")
    logger.info(f"Checkpointing: {checkpointing}")
    logger.info(f"Memory: {memory}")
```

## Best Practices

### Do's

✅ **Create loggers at module level**

```python
from backend.services.config import get_logger

# Create logger once at module level
logger = get_logger(__name__)

class MyService:
    def process(self):
        # Reuse module-level logger
        logger.info("Processing...")
```

✅ **Call setup_logging() once at application startup**

```python
from fastapi import FastAPI
from backend.services.config import setup_logging

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Set up logging once
    setup_logging()
```

✅ **Use structured logging with context**

```python
from backend.services.config import get_logger

logger = get_logger(__name__)

def process_workflow(workflow_id: str):
    logger.info(f"Processing workflow: {workflow_id}")
    try:
        result = execute(workflow_id)
        logger.info(f"Workflow {workflow_id} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
        raise
```

✅ **Cache configuration values at application startup**

```python
from backend.services.config import ExecutionConfig, get_endpoint_url

# Cache at module level
CHECKPOINTING_ENABLED = ExecutionConfig.use_checkpointing()
CALLBACK_URL = get_endpoint_url("/api/callback")

def execute_workflow(graph_id: str):
    if CHECKPOINTING_ENABLED:
        # Use cached value
        create_checkpoint()
```

✅ **Use environment variables for configuration**

```python
# .env file
LOG_LEVEL=DEBUG
ENABLE_CHECKPOINTING=true
API_BASE_URL=https://api.example.com

# Application automatically reads from environment
from backend.services.config import setup_logging, get_api_base_url

setup_logging()  # Uses LOG_LEVEL from env
base_url = get_api_base_url()  # Uses API_BASE_URL from env
```

✅ **Include exc_info=True for exception logging**

```python
from backend.services.config import get_logger

logger = get_logger(__name__)

try:
    risky_operation()
except Exception as e:
    # Include stack trace
    logger.error(f"Operation failed: {e}", exc_info=True)
```

### Don'ts

❌ **Don't create loggers inside functions (inefficient)**

```python
# BAD: Creates logger on every call
def process_data():
    logger = get_logger(__name__)  # Wasteful
    logger.info("Processing...")

# GOOD: Create logger at module level
logger = get_logger(__name__)

def process_data():
    logger.info("Processing...")
```

❌ **Don't call setup_logging() multiple times with different levels**

```python
# BAD: setup_logging is idempotent - second call does nothing
setup_logging(logging.DEBUG)
setup_logging(logging.WARNING)  # Ignored! Still DEBUG

# GOOD: Call once with desired level
setup_logging(logging.INFO)
```

❌ **Don't hardcode URLs**

```python
# BAD: Hardcoded URL breaks in different environments
callback_url = "http://localhost:8000/api/callback"

# GOOD: Use get_endpoint_url for environment-aware URLs
from backend.services.config import get_endpoint_url
callback_url = get_endpoint_url("/api/callback")
```

❌ **Don't read environment variables directly**

```python
# BAD: Bypasses configuration layer
import os
checkpointing = os.getenv("ENABLE_CHECKPOINTING") == "true"

# GOOD: Use ExecutionConfig
from backend.services.config import ExecutionConfig
checkpointing = ExecutionConfig.use_checkpointing()
```

❌ **Don't ignore logging setup errors**

```python
# BAD: Silent failure
try:
    setup_logging()
except:
    pass  # Logging might not work!

# GOOD: Handle and fallback
from backend.services.config import setup_logging
import logging
import sys

try:
    setup_logging()
except Exception as e:
    print(f"Logging setup failed: {e}", file=sys.stderr)
    logging.basicConfig(level=logging.INFO)  # Fallback
```

❌ **Don't concatenate URLs manually**

```python
# BAD: Manual URL construction
base = get_api_base_url()
url = base + "/" + path  # Might create //

# GOOD: Use get_endpoint_url
url = get_endpoint_url(path)
```

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Uses `ExecutionConfig` for checkpointing and memory configuration
- [Graph Service](./graph.md) - Uses logging extensively for graph building and compilation
- [Memory Service](./memory.md) - Uses logging and checks `ExecutionConfig.use_memory()`
- [Database Service](./database.md) - Uses PostgreSQL connection string from `ExecutionConfig`
- [Checkpoint Service](./checkpoint.md) - Uses logging and checkpointing configuration

### Related API Modules

- [HTTP Execution API](../agents-guide/api/http_execution.md) - Uses URL configuration for trigger and callback URLs
- [Graph API](../agents-guide/api/graph.md) - Uses logging throughout API handlers
- [Workflow Publishing API](../agents-guide/api/workflow.md) - Uses URL configuration for published workflow endpoints
- [Authentication API](../agents-guide/api/auth.md) - Uses logging for authentication events

### Architecture Documentation

- Service Layer Architecture - Overview of service layer patterns
- Configuration Management - Detailed configuration strategy
- Logging Strategy - Comprehensive logging architecture

### External Documentation

- [Python logging](https://docs.python.org/3/library/logging.html) - Official Python logging documentation
- [Python os module](https://docs.python.org/3/library/os.html) - Environment variable access
- [TimedRotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler) - Log
  rotation documentation

## Summary

The config service module is a foundational utility module that provides essential configuration functionality for the
AgenticStudio backend application. It consolidates URL configuration, logging system setup, and execution engine
configuration into a clean, easy-to-use API.

The module is designed with deployment flexibility in mind, automatically adapting to different environments (local
development, staging, production) through environment variables. It provides sensible defaults for local development
while supporting production deployments on platforms like Azure App Service.

The logging system is comprehensive, featuring automatic file rotation, specialised loggers for different components (
API, execution, database), and consistent formatting. The logger factory pattern (`get_logger()`) ensures consistent
logging throughout the application with minimal boilerplate.

**Key Features:**

- Environment-aware API base URL resolution with intelligent fallbacks
- Complete endpoint URL construction for webhooks and callbacks
- Comprehensive logging system with file rotation and specialised loggers
- Logger factory for consistent logging across the application
- Execution engine configuration with feature flags (checkpointing, memory)
- PostgreSQL connection string resolution with multiple fallback options
- Idempotent initialisation (setup_logging can be called multiple times safely)
- Zero custom dependencies (uses only Python standard library)

**Primary Use Cases:**

- Application startup initialisation (logging setup, configuration loading)
- Creating module-level loggers for consistent logging
- Generating environment-aware URLs for webhooks, callbacks, and API endpoints
- Configuring execution engine with checkpointing and memory settings
- Resolving database connection strings for checkpointing
- Feature flag checks for conditional functionality

**When to Use This Service:**

- At application startup to initialise logging system
- When creating a new module that needs logging (use `get_logger(__name__)`)
- When generating URLs for HTTP execution, webhooks, or callbacks
- When configuring the execution engine or checkpointing system
- When you need environment-aware configuration with sensible defaults
- When you need to check if features like checkpointing or memory are enabled

This service is used extensively across the entire AgenticStudio backend and is one of the first services initialised during
application startup. Its simplicity and reliability make it a cornerstone of the backend architecture.
