# Database Service Documentation

## Overview

The database service provides core database connectivity, session management, and schema migration capabilities for the
AgenticStudio backend. It manages PostgreSQL connections through SQLAlchemy ORM with optimised connection pooling for cloud
deployments and provides thread-safe database initialisation with automated migrations.

**Location:** `backend/services/database/`

**Primary Responsibilities:**

- PostgreSQL database engine creation and configuration
- Database session management with context managers
- Connection pool management optimised for Azure/cloud deployments
- SQLAlchemy Base class provisioning for ORM models
- Automated database initialisation and schema migrations
- Worker-safe concurrent initialisation using PostgreSQL advisory locks

**Key Use Cases:**

- FastAPI dependency injection for database sessions
- Application startup database initialisation
- ORM model definition and table creation
- Schema evolution through migrations
- Connection pool configuration for production deployments

## Table of Contents

- [Architecture](#architecture)
- [Public API](#public-api)
- [Core Classes](#core-classes)
- [Functions](#functions)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Integration Patterns](#integration-patterns)
- [Usage Examples](#usage-examples)
- [Performance Considerations](#performance-considerations)
- [Testing Patterns](#testing-patterns)
- [Best Practices](#best-practices)
- [Related Documentation](#related-documentation)
- [Summary](#summary)

## Architecture

### Module Structure

```
backend/services/database/
├── __init__.py              # Public API exports
├── base.py                  # SQLAlchemy declarative base
├── config.py                # Database configuration management
├── engine.py                # Engine creation and connection pool
├── session.py               # Session factory and context managers
└── migrations/              # Schema migration system
    ├── __init__.py          # Migration runner and init_db()
    ├── registry.py          # Migration registry and tracking
    └── schema_updates.py    # Individual migration functions
```

**File Descriptions:**

- **`__init__.py`** - Public API that exports commonly used functions and classes
- **`base.py`** - Provides SQLAlchemy `Base` class for ORM model inheritance
- **`config.py`** - `DatabaseConfig` dataclass with environment variable loading
- **`engine.py`** - SQLAlchemy engine creation with connection pool configuration
- **`session.py`** - Session factory creation and `get_db()` context manager
- **`migrations/__init__.py`** - Database initialisation with advisory locks
- **`migrations/registry.py`** - Migration registry with enable/disable flags
- **`migrations/schema_updates.py`** - Individual idempotent migration functions

### Design Patterns

**Singleton Pattern:**

- Global engine instance (`_engine`) created on first access
- Global session factory (`_SessionLocal`) created on first access
- Provides consistent database connections across the application
- Reset functions available for testing and reconfiguration

**Context Manager Pattern:**

- `get_db()` provides automatic transaction management
- Commits on success, rolls back on exceptions
- Guarantees session cleanup in finally block

**Migration Pattern:**

- Idempotent migrations that can be safely run multiple times
- PostgreSQL advisory locks prevent concurrent execution
- Registry-based migration system with enable/disable flags
- Each migration checks for existence before making changes

**Dependency Injection:**

- Designed for FastAPI's dependency injection system
- `get_db()` context manager used with `Depends()`
- Session lifecycle managed automatically per request

**Configuration Pattern:**

- `DatabaseConfig.from_env()` loads environment variables
- Supports both `DATABASE_URL` and component-based configuration
- Fallback defaults for development environments

### Dependencies

**Internal Dependencies:**

- `backend.models` - Uses `Base` from this service for all ORM models
- All API modules - Use `get_db()` for database access
- All service modules - Use database sessions for persistence

**External Dependencies:**

- `sqlalchemy` (2.0+) - ORM and database toolkit
- `psycopg2` - PostgreSQL adapter
- `pgvector` extension - Vector similarity search support

**Database Dependencies:**

- PostgreSQL 12+ (required)
- pgvector extension (optional, for embedding storage)

**Environment Variables:**
See [Configuration](#configuration) section for detailed list.

### Component Relationships

```
┌─────────────────────────────────────────────────┐
│           FastAPI Application                   │
│              (backend/app.py)                   │
└────────────┬────────────────────────────────────┘
             │
             │ init_db() on startup
             │
             ▼
┌─────────────────────────────────────────────────┐
│        Database Service Module                  │
│     (backend/services/database/)                │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐        ┌──────────────┐       │
│  │   Base      │◄───────┤  ORM Models  │       │
│  │(base.py)    │        │ (backend/    │       │
│  └─────────────┘        │  models/)    │       │
│                         └──────────────┘       │
│                                                 │
│  ┌─────────────┐                               │
│  │Config       │                               │
│  │(config.py)  │                               │
│  └──────┬──────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌─────────────┐        ┌──────────────┐       │
│  │Engine       │───────►│Session       │       │
│  │(engine.py)  │        │(session.py)  │       │
│  └─────────────┘        └──────┬───────┘       │
│                                │               │
│                                ▼               │
│                         ┌──────────────┐       │
│                         │  get_db()    │       │
│                         │  Context Mgr │       │
│                         └──────┬───────┘       │
│                                │               │
└────────────────────────────────┼───────────────┘
                                 │
                                 ▼
                    ┌────────────────────┐
                    │  API Routes        │
                    │  (FastAPI)         │
                    │  Depends(get_db)   │
                    └────────────────────┘
```

## Public API

### Exported Classes

- `DatabaseConfig` - Database configuration with environment variable loading
- `Base` - SQLAlchemy declarative base for ORM models

### Exported Functions

- `get_db()` - Context manager for database sessions (primary usage)
- `init_db()` - Initialise database tables and run migrations
- `get_engine()` - Get or create the global database engine
- `create_database_engine()` - Create a new database engine with configuration
- `reset_engine()` - Reset the global engine instance (testing)
- `get_session_factory()` - Get or create the global session factory
- `reset_session_factory()` - Reset the global session factory (testing)

### Constants and Configuration

- `SessionLocal` - Pre-initialised session factory (backward compatibility)

### Exceptions

This module does not define custom exceptions. It raises SQLAlchemy exceptions:

```
sqlalchemy.exc.SQLAlchemyError
├── OperationalError        # Connection and operational errors
├── IntegrityError          # Constraint violations
├── DataError               # Data type errors
└── ProgrammingError        # SQL syntax and semantic errors
```

## Core Classes

### `DatabaseConfig`

Database configuration dataclass that encapsulates all connection and pool settings.

**Purpose:** Provides type-safe configuration management with environment variable loading and sensible defaults for
production deployments.

**Responsibilities:**

- Load configuration from environment variables
- Validate configuration parameters
- Provide connection arguments for SQLAlchemy engine
- Support both `DATABASE_URL` and component-based configuration
- Log configuration for debugging

**Initialisation:**

```python
from backend.services.database import DatabaseConfig

# Manual initialisation
config = DatabaseConfig(
    connection_string="postgresql+psycopg2://user:pass@host:5432/db",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=180,
    pool_use_lifo=True,
    pool_pre_ping=True,
    connect_timeout=10,
    statement_timeout_ms=600000,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5,
    application_name="my-app",
)
```

**Class Attributes:**

- `connection_string: str` - PostgreSQL connection string (required)
- `pool_size: int` - Size of the connection pool (default: 5)
- `max_overflow: int` - Maximum overflow connections beyond pool_size (default: 5)
- `pool_timeout: int` - Timeout for getting connection from pool in seconds (default: 30)
- `pool_recycle: int` - Connection recycle time in seconds (default: 180)
- `pool_use_lifo: bool` - Use LIFO (Last-In-First-Out) for connection pool (default: True)
- `pool_pre_ping: bool` - Test connections before using them (default: True)
- `connect_timeout: int` - Connection timeout in seconds (default: 10)
- `statement_timeout_ms: int` - SQL statement timeout in milliseconds (default: 600000)
- `keepalives_idle: int` - TCP keepalive idle time in seconds (default: 30)
- `keepalives_interval: int` - TCP keepalive interval in seconds (default: 10)
- `keepalives_count: int` - TCP keepalive probe count (default: 5)
- `application_name: Optional[str]` - Application name for PostgreSQL (default: "langgraph-backend")

### Key Methods

#### `from_env()`

```python
@classmethod
def from_env(cls) -> DatabaseConfig:
    """Create DatabaseConfig from environment variables."""
```

**Parameters:** None

**Returns:**

- `DatabaseConfig` - Configuration instance loaded from environment

**Raises:**

- `ValueError` - If no database configuration is found

**Example:**

```python
from backend.services.database import DatabaseConfig

# Load from environment variables
config = DatabaseConfig.from_env()
```

**Behaviour:**

- Checks for `DATABASE_URL` environment variable first
- Falls back to component-based configuration (`KEY_POSTGRES_*` variables)
- Loads pool and connection settings from `DB_*` environment variables
- Uses sensible defaults for all optional parameters
- Logs configuration source for debugging

**Use Cases:**

- Application startup configuration
- Production environment configuration
- Testing with custom database parameters

#### `get_connect_args()`

```python
def get_connect_args(self) -> dict:
    """Get connection arguments for SQLAlchemy engine."""
```

**Parameters:** None

**Returns:**

- `dict` - Connection arguments for psycopg2 adapter

**Example:**

```python
config = DatabaseConfig.from_env()
connect_args = config.get_connect_args()

# Returns:
# {
#     "keepalives": 1,
#     "keepalives_idle": 30,
#     "keepalives_interval": 10,
#     "keepalives_count": 5,
#     "connect_timeout": 10,
#     "options": "-c statement_timeout=600000",
#     "application_name": "langgraph-backend"
# }
```

**Behaviour:**

- Configures TCP keepalives for reliable connections
- Sets statement timeout at PostgreSQL level
- Includes application name for monitoring

**Use Cases:**

- Engine creation with optimised connection settings
- Cloud deployment reliability (Azure, AWS RDS, etc.)
- Connection health monitoring

#### `log_configuration()`

```python
def log_configuration(self) -> None:
    """Log database configuration for debugging."""
```

**Parameters:** None

**Returns:** None

**Example:**

```python
config = DatabaseConfig.from_env()
config.log_configuration()

# Logs:
# [DATABASE] Configuration: pool_size=5, max_overflow=5, pool_timeout=30,
# recycle=180, lifo=True, pre_ping=True, app_name=langgraph-backend
```

**Behaviour:**

- Logs pool configuration parameters
- Uses INFO level logging
- Omits sensitive connection string details

**Use Cases:**

- Application startup debugging
- Production environment verification
- Troubleshooting connection issues

### `Base`

SQLAlchemy declarative base class for all ORM models.

**Purpose:** Provides the base class that all SQLAlchemy models inherit from, enabling ORM functionality and table
creation.

**Responsibilities:**

- Define common base for all ORM models
- Enable SQLAlchemy metadata tracking
- Support `Base.metadata.create_all()` for table creation

**Example:**

```python
from backend.services.database import Base
from sqlalchemy import Column, String, Integer

class User(Base):
    """User ORM model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
```

**Use Cases:**

- Defining new ORM models
- Creating database tables
- Establishing table relationships

## Functions

### `get_db()`

Context manager for database sessions with automatic transaction management.

**Signature:**

```python
@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
```

**Parameters:** None

**Returns:**

- `Generator[Session, None, None]` - SQLAlchemy Session instance

**Raises:**

- Re-raises any exception after rollback

**Example:**

```python
from backend.services.database import get_db
from backend.models import User

# Basic usage
with get_db() as db:
    user = db.query(User).filter(User.email == "user@example.com").first()
    if user:
        user.name = "Updated Name"
    # Automatically commits on success

# FastAPI dependency injection
from fastapi import Depends
from sqlalchemy.orm import Session

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List all users."""
    return db.query(User).all()
```

**Behaviour:**

- Creates a new session from the session factory
- Yields the session for use in with-block
- Commits transaction on successful completion
- Rolls back transaction on exception
- Always closes the session in finally block
- Logs session lifecycle events at DEBUG level

**Use Cases:**

- FastAPI route handlers with dependency injection
- Standalone database operations
- Service layer database access
- Testing with database fixtures

### `init_db()`

Initialise database tables and run schema migrations with worker-safe concurrent execution.

**Signature:**

```python
def init_db() -> None:
    """Initialize database tables and run migrations."""
```

**Parameters:** None

**Returns:** None

**Raises:**

- `Exception` - If critical initialisation steps fail

**Example:**

```python
from backend.services.database import init_db

# Call on application startup
try:
    init_db()
    print("Database initialised successfully")
except Exception as e:
    print(f"Database initialisation failed: {e}")
    raise
```

**Behaviour:**

- Attempts to acquire PostgreSQL advisory lock (lock ID: 123456789)
- If lock acquired:
  - Creates all tables defined in `Base.metadata` (idempotent)
  - Runs all enabled migrations from registry
  - Releases advisory lock
- If lock not acquired:
  - Waits 1-3 seconds (randomised to avoid thundering herd)
  - Returns without error (another worker is handling initialisation)
- All operations are idempotent and safe to run multiple times

**Use Cases:**

- Application startup (FastAPI lifespan event)
- Worker process initialisation
- Test database setup
- Development environment setup

**Worker Safety:**
Uses PostgreSQL advisory locks to ensure only one worker performs initialisation, preventing race conditions in
multi-worker deployments (e.g., Gunicorn, Uvicorn with multiple workers).

### `get_engine()`

Get or create the global database engine singleton.

**Signature:**

```python
def get_engine(config: Optional[DatabaseConfig] = None) -> Engine:
    """Get or create the global database engine."""
```

**Parameters:**

- `config` (Optional[DatabaseConfig]) - Database configuration. Only used on first call. (default: None, loads from
  environment)

**Returns:**

- `Engine` - SQLAlchemy Engine instance

**Example:**

```python
from backend.services.database import get_engine

# Get engine with default configuration
engine = get_engine()

# Execute raw SQL
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.scalar())
```

**Behaviour:**

- Returns existing engine if already created
- Creates new engine on first call using provided or environment config
- Stores engine in module-level singleton
- Thread-safe for concurrent access

**Use Cases:**

- Direct SQL execution
- Custom database operations
- Performance monitoring

### `create_database_engine()`

Create a new SQLAlchemy engine with connection pool settings.

**Signature:**

```python
def create_database_engine(config: Optional[DatabaseConfig] = None) -> Engine:
    """Create SQLAlchemy engine with connection pool settings."""
```

**Parameters:**

- `config` (Optional[DatabaseConfig]) - Database configuration. If None, loads from environment.

**Returns:**

- `Engine` - SQLAlchemy Engine instance

**Raises:**

- `ValueError` - If database configuration is invalid

**Example:**

```python
from backend.services.database import create_database_engine, DatabaseConfig

# Create engine with custom configuration
config = DatabaseConfig.from_env()
config.pool_size = 20
config.max_overflow = 40

engine = create_database_engine(config)
```

**Behaviour:**

- Loads configuration from environment if not provided
- Creates SQLAlchemy engine with connection pool settings
- Configures pool pre-ping for connection health checks
- Sets up keepalives and timeouts for cloud reliability
- Logs engine creation and configuration

**Use Cases:**

- Custom engine configuration for specific use cases
- Multiple database connections
- Testing with different configurations
- Migration tools

### `reset_engine()`

Reset the global engine instance for testing or reconfiguration.

**Signature:**

```python
def reset_engine() -> None:
    """Reset the global engine instance."""
```

**Parameters:** None

**Returns:** None

**Example:**

```python
from backend.services.database import reset_engine, get_engine

# Reset engine (useful in tests)
reset_engine()

# Next get_engine() call will create new engine
new_engine = get_engine()
```

**Behaviour:**

- Disposes of current engine (closes all connections)
- Clears global engine reference
- Clears global config reference
- Logs engine disposal

**Use Cases:**

- Test isolation and cleanup
- Configuration changes requiring new engine
- Connection pool reset
- Development environment restart

### `get_session_factory()`

Get or create the global session factory singleton.

**Signature:**

```python
def get_session_factory() -> sessionmaker:
    """Get or create the global session factory."""
```

**Parameters:** None

**Returns:**

- `sessionmaker` - SQLAlchemy sessionmaker instance

**Example:**

```python
from backend.services.database import get_session_factory

# Get session factory
SessionFactory = get_session_factory()

# Create session manually
db = SessionFactory()
try:
    users = db.query(User).all()
finally:
    db.close()
```

**Behaviour:**

- Returns existing session factory if already created
- Creates new session factory on first call
- Binds to global engine
- Configures autocommit=False, autoflush=False, expire_on_commit=False

**Use Cases:**

- Manual session management
- Custom session lifecycle control
- Integration with other frameworks
- Testing utilities

### `reset_session_factory()`

Reset the global session factory for testing or reconfiguration.

**Signature:**

```python
def reset_session_factory() -> None:
    """Reset the global session factory."""
```

**Parameters:** None

**Returns:** None

**Example:**

```python
from backend.services.database import reset_session_factory, get_session_factory

# Reset session factory
reset_session_factory()

# Next get_session_factory() call will create new factory
new_factory = get_session_factory()
```

**Behaviour:**

- Clears global session factory reference
- Logs session factory reset
- Next call to get_session_factory() creates new factory

**Use Cases:**

- Test cleanup
- Session factory reconfiguration
- Development environment reset

## Configuration

### Environment Variables

The database service uses the following environment variables:

**Connection Configuration:**

- `DATABASE_URL` - Complete PostgreSQL connection string (optional, takes precedence)
  - Format: `postgresql+psycopg2://user:password@host:port/dbname?sslmode=prefer`
  - Default: Built from component variables below
  - Required: No (can use component-based config)

**Component-based Configuration (used if DATABASE_URL not set):**

- `KEY_POSTGRES_HOST` - PostgreSQL server hostname
  - Default: `localhost`
  - Required: No

- `KEY_POSTGRES_DBNAME` - Database name
  - Default: `langgraph`
  - Required: No

- `KEY_POSTGRES_USER` - Database username
  - Default: `postgres`
  - Required: No

- `KEY_POSTGRES_PASSWORD` - Database password
  - Default: `postgres`
  - Required: No

- `KEY_POSTGRES_PORT` - PostgreSQL server port
  - Default: `5432`
  - Required: No

- `KEY_POSTGRES_SSLMODE` - SSL mode for connection
  - Default: `prefer`
  - Options: `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full`
  - Required: No

**Connection Pool Configuration:**

- `DB_POOL_SIZE` - Size of the connection pool
  - Default: `5`
  - Required: No
  - Recommended: 5-10 for typical applications, 10-20 for high-traffic

- `DB_MAX_OVERFLOW` - Maximum overflow connections beyond pool_size
  - Default: `5`
  - Required: No
  - Recommended: Same as pool_size

- `DB_POOL_TIMEOUT` - Timeout for getting connection from pool (seconds)
  - Default: `30`
  - Required: No

- `DB_POOL_RECYCLE_SECONDS` - Connection recycle time (seconds)
  - Default: `180`
  - Required: No
  - Note: Important for cloud databases with idle connection timeouts

- `DB_POOL_USE_LIFO` - Use LIFO (Last-In-First-Out) for connection pool
  - Default: `True`
  - Required: No
  - Note: LIFO can improve connection reuse

- `DB_POOL_PRE_PING` - Test connections before using them
  - Default: `True`
  - Required: No
  - Note: Essential for cloud deployments

**Connection Settings:**

- `DB_CONNECT_TIMEOUT` - Connection timeout (seconds)
  - Default: `10`
  - Required: No

- `DB_STATEMENT_TIMEOUT_MS` - SQL statement timeout (milliseconds)
  - Default: `600000` (10 minutes)
  - Required: No

- `DB_KEEPALIVES_IDLE` - TCP keepalive idle time (seconds)
  - Default: `30`
  - Required: No

- `DB_KEEPALIVES_INTERVAL` - TCP keepalive interval (seconds)
  - Default: `10`
  - Required: No

- `DB_KEEPALIVES_COUNT` - TCP keepalive probe count
  - Default: `5`
  - Required: No

- `DB_APPLICATION_NAME` - Application name for PostgreSQL monitoring
  - Default: `langgraph-backend`
  - Required: No

### Initialisation Patterns

#### Basic Initialisation

```python
from backend.services.database import init_db, get_db
from backend.models import User

# 1. Initialise database (typically in app startup)
init_db()

# 2. Use database sessions
with get_db() as db:
    users = db.query(User).all()
    print(f"Found {len(users)} users")
```

#### FastAPI Application Initialisation

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from backend.services.database import init_db, get_db
from backend.models import User

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        init_db()
        print("Database initialised successfully")
    except Exception as e:
        print(f"Database initialisation failed: {e}")
        raise

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List all users."""
    return db.query(User).all()
```

#### Custom Configuration

```python
from backend.services.database import (
    DatabaseConfig,
    create_database_engine,
    reset_engine,
    reset_session_factory,
)

# Create custom configuration
config = DatabaseConfig(
    connection_string="postgresql+psycopg2://user:pass@host:5432/db",
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
    pool_recycle=300,
    pool_pre_ping=True,
    application_name="my-custom-app",
)

# Reset existing engine/session factory
reset_engine()
reset_session_factory()

# Create new engine with custom config
engine = create_database_engine(config)
```

#### Testing Initialisation

```python
import pytest
from backend.services.database import (
    init_db,
    reset_engine,
    reset_session_factory,
)

@pytest.fixture(scope="session")
def setup_database():
    """Setup database for tests."""
    # Initialize database once per test session
    init_db()
    yield
    # Cleanup
    reset_engine()
    reset_session_factory()

@pytest.fixture
def db():
    """Provide database session for each test."""
    from backend.services.database import get_db

    with get_db() as session:
        yield session
        # Rollback any changes made during test
        session.rollback()
```

## Error Handling

### Exception Hierarchy

The database service raises SQLAlchemy exceptions:

```
Exception
└── sqlalchemy.exc.SQLAlchemyError
    ├── OperationalError
    │   ├── Connection timeout
    │   ├── Connection refused
    │   └── Lost connection
    ├── IntegrityError
    │   ├── Unique constraint violation
    │   ├── Foreign key violation
    │   └── Check constraint violation
    ├── DataError
    │   ├── Invalid data type
    │   └── Value out of range
    ├── ProgrammingError
    │   ├── Table does not exist
    │   ├── Column does not exist
    │   └── SQL syntax error
    └── InvalidRequestError
        ├── Session already closed
        └── Invalid query state
```

### Exception Details

#### `OperationalError`

Raised when database operations fail due to connection or operational issues.

**Inherits from:** `SQLAlchemyError`

**When raised:**

- Cannot connect to database
- Connection lost during operation
- Database is unreachable
- Authentication failure

**Example:**

```python
from sqlalchemy.exc import OperationalError
from backend.services.database import get_db

try:
    with get_db() as db:
        result = db.execute(text("SELECT 1"))
except OperationalError as e:
    logger.error(f"Database operation failed: {e}")
    # Handle connection error (retry, circuit breaker, etc.)
```

#### `IntegrityError`

Raised when database constraints are violated.

**Inherits from:** `SQLAlchemyError`

**When raised:**

- Unique constraint violation
- Foreign key constraint violation
- Check constraint violation
- Not null constraint violation

**Example:**

```python
from sqlalchemy.exc import IntegrityError
from backend.services.database import get_db
from backend.models import User

try:
    with get_db() as db:
        user = User(email="duplicate@example.com")
        db.add(user)
        db.commit()
except IntegrityError as e:
    logger.error(f"Constraint violation: {e}")
    # Handle duplicate email or other constraint violation
    return {"error": "Email already exists"}
```

#### `ProgrammingError`

Raised when SQL syntax or semantic errors occur.

**Inherits from:** `SQLAlchemyError`

**When raised:**

- Table or column does not exist
- SQL syntax error
- Invalid query structure

**Example:**

```python
from sqlalchemy.exc import ProgrammingError
from backend.services.database import get_db

try:
    with get_db() as db:
        result = db.execute(text("SELECT * FROM nonexistent_table"))
except ProgrammingError as e:
    logger.error(f"SQL programming error: {e}")
    # Handle missing table or invalid SQL
```

### Error Handling Patterns

#### Standard Error Handling

```python
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from backend.services.database import get_db
from backend.models import User
import logging

logger = logging.getLogger(__name__)

def create_user(email: str, name: str) -> dict:
    """Create user with comprehensive error handling."""

    try:
        with get_db() as db:
            # Check if user exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return {"error": "User already exists", "code": "DUPLICATE"}

            # Create new user
            user = User(email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)

            return {"success": True, "user_id": user.id}

    except IntegrityError as e:
        logger.error(f"Integrity constraint violated: {e}")
        return {"error": "Database constraint violation", "code": "CONSTRAINT"}

    except OperationalError as e:
        logger.error(f"Database operation failed: {e}")
        return {"error": "Database connection error", "code": "CONNECTION"}

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return {"error": "Database error", "code": "DATABASE"}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "Internal server error", "code": "INTERNAL"}
```

#### Retry Pattern for Connection Errors

```python
from sqlalchemy.exc import OperationalError
from backend.services.database import get_db
import time
import logging

logger = logging.getLogger(__name__)

def execute_with_retry(operation, max_retries: int = 3, delay: float = 1.0):
    """Execute database operation with retry on connection errors."""

    for attempt in range(max_retries):
        try:
            with get_db() as db:
                return operation(db)

        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
                continue
            else:
                logger.error(f"Database operation failed after {max_retries} attempts")
                raise

# Usage
def get_user_by_email(email: str):
    """Get user with automatic retry."""
    def operation(db):
        return db.query(User).filter(User.email == email).first()

    return execute_with_retry(operation)
```

#### Transaction Rollback Pattern

```python
from sqlalchemy.exc import SQLAlchemyError
from backend.services.database import get_db
from backend.models import User, Workflow
import logging

logger = logging.getLogger(__name__)

def create_user_and_workflow(email: str, name: str, workflow_data: dict) -> dict:
    """Create user and workflow in single transaction."""

    try:
        with get_db() as db:
            # Create user
            user = User(email=email, name=name)
            db.add(user)
            db.flush()  # Get user.id without committing

            # Create workflow
            workflow = Workflow(
                name=workflow_data["name"],
                owner_id=user.id,
            )
            db.add(workflow)

            # Commit automatically handled by context manager
            return {"success": True, "user_id": user.id, "workflow_id": workflow.id}

    except SQLAlchemyError as e:
        # Transaction automatically rolled back by context manager
        logger.error(f"Transaction failed: {e}")
        return {"error": "Failed to create user and workflow", "code": "TRANSACTION"}
```

## Integration Patterns

### Integration with API Layer

The database service is primarily used in FastAPI route handlers through dependency injection:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.services.database import get_db
from backend.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])

class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str

@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all users with pagination."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Create a new user."""
    # Check for existing user
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user = User(email=user_data.email, name=user_data.name)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

### Integration with Other Services

Service layer modules use the database service for persistence:

```python
# Example: Memory service using database
from backend.services.database import get_db
from backend.models import ConversationMemory
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class MemoryRepository:
    """Repository for conversation memory persistence."""

    def get_conversation_history(
        self,
        thread_id: str,
        limit: int = 50,
    ) -> List[ConversationMemory]:
        """Get conversation history for a thread."""

        with get_db() as db:
            memories = (
                db.query(ConversationMemory)
                .filter(ConversationMemory.thread_id == thread_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(limit)
                .all()
            )
            return list(reversed(memories))

    def save_conversation_turn(
        self,
        thread_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Optional[dict] = None,
    ) -> ConversationMemory:
        """Save a conversation turn."""

        with get_db() as db:
            memory = ConversationMemory(
                thread_id=thread_id,
                user_message=user_message,
                assistant_message=assistant_message,
                metadata=metadata or {},
            )
            db.add(memory)
            db.commit()
            db.refresh(memory)

            return memory
```

### Dependency Flow

```
┌─────────────────────────────────────────┐
│     FastAPI Application Layer           │
│  (backend/api/*/routes.py)              │
│                                         │
│  - Uses Depends(get_db)                 │
│  - Receives Session in route handlers   │
└─────────────┬───────────────────────────┘
              │
              │ Depends on
              │
              ▼
┌─────────────────────────────────────────┐
│     Database Service                    │
│  (backend/services/database/)           │
│                                         │
│  - Provides get_db() context manager    │
│  - Manages engine and session factory   │
│  - Runs migrations on startup           │
└─────────────┬───────────────────────────┘
              │
              │ Used by
              │
              ▼
┌─────────────────────────────────────────┐
│     ORM Models                          │
│  (backend/models/)                      │
│                                         │
│  - Inherit from Base                    │
│  - Define table schema                  │
│  - Used in queries                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│     Service Layer                       │
│  (backend/services/*/)                  │
│                                         │
│  - Uses get_db() for persistence        │
│  - Repository pattern                   │
│  - Business logic + database access     │
└─────────────┬───────────────────────────┘
              │
              │ Depends on
              │
              ▼
┌─────────────────────────────────────────┐
│     Database Service                    │
└─────────────────────────────────────────┘
```

**Services depending on database:**

- All services in `backend/services/` that require persistence
- `backend/api/*` route modules
- `backend/models/*` ORM models

**Services that database depends on:**

- None (database service is a foundational layer)

### Common Integration Patterns

#### Pattern 1: FastAPI Dependency Injection

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.services.database import get_db

@app.get("/resource")
def get_resource(
    resource_id: str,
    db: Session = Depends(get_db),
):
    """Get resource using injected database session."""
    return db.query(Resource).filter(Resource.id == resource_id).first()
```

#### Pattern 2: Service Layer Repository

```python
from backend.services.database import get_db
from backend.models import Workflow
from typing import List

class WorkflowRepository:
    """Repository for workflow persistence."""

    def get_by_user(self, user_id: str) -> List[Workflow]:
        """Get workflows for a user."""
        with get_db() as db:
            return db.query(Workflow).filter(Workflow.owner_id == user_id).all()

    def create(self, workflow_data: dict) -> Workflow:
        """Create a new workflow."""
        with get_db() as db:
            workflow = Workflow(**workflow_data)
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
            return workflow
```

#### Pattern 3: Manual Session Management

```python
from backend.services.database import get_session_factory
from backend.models import GraphExecution

SessionFactory = get_session_factory()

def batch_process_executions(execution_ids: List[str]):
    """Process executions in batches with manual session control."""

    db = SessionFactory()
    try:
        for execution_id in execution_ids:
            execution = db.query(GraphExecution).filter(
                GraphExecution.id == execution_id
            ).first()

            if execution:
                # Process execution
                execution.status = "processed"
                db.add(execution)

            # Commit in batches
            if len(db.new) + len(db.dirty) >= 100:
                db.commit()

        # Final commit
        db.commit()

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
```

## Usage Examples

### Example 1: Basic Usage

Complete end-to-end example of basic database usage:

```python
from backend.services.database import init_db, get_db, Base
from backend.models import User
from sqlalchemy import Column, String

# Step 1: Initialize database (typically on app startup)
init_db()
print("Database initialized")

# Step 2: Query data using context manager
with get_db() as db:
    # Query all users
    users = db.query(User).all()
    print(f"Found {len(users)} users")

    # Query specific user
    user = db.query(User).filter(User.email == "john@example.com").first()
    if user:
        print(f"User: {user.name} ({user.email})")

# Step 3: Create new record
with get_db() as db:
    new_user = User(
        email="jane@example.com",
        name="Jane Doe",
    )
    db.add(new_user)
    # Automatically commits on context exit

print("User created successfully")
```

### Example 2: FastAPI Integration

Complete example showing FastAPI application with database integration:

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.services.database import init_db, get_db
from backend.models import User, Workflow
from pydantic import BaseModel
from typing import List

app = FastAPI(title="AgenticStudio API")

# Pydantic models
class WorkflowCreate(BaseModel):
    name: str
    description: str

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str

    class Config:
        from_attributes = True

# Startup event
@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

# Routes
@app.get("/workflows", response_model=List[WorkflowResponse])
def list_workflows(
    user_id: str,
    db: Session = Depends(get_db),
):
    """List all workflows for a user."""
    workflows = (
        db.query(Workflow)
        .filter(Workflow.owner_id == user_id)
        .all()
    )
    return workflows

@app.post("/workflows", response_model=WorkflowResponse)
def create_workflow(
    workflow_data: WorkflowCreate,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Create a new workflow."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create workflow
    workflow = Workflow(
        name=workflow_data.name,
        description=workflow_data.description,
        owner_id=user_id,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    return workflow

@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """Get workflow by ID."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow

@app.delete("/workflows/{workflow_id}")
def delete_workflow(
    workflow_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.owner_id == user_id,
    ).first()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db.delete(workflow)
    db.commit()

    return {"success": True, "message": "Workflow deleted"}
```

### Example 3: Service Layer Pattern

Show a realistic service layer implementation:

```python
from backend.services.database import get_db
from backend.models import GraphExecution, NodeExecution, User
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExecutionHistoryService:
    """Service for managing execution history."""

    def create_execution(
        self,
        user_id: str,
        workflow_id: str,
        input_data: dict,
    ) -> Optional[GraphExecution]:
        """Create a new graph execution."""

        try:
            with get_db() as db:
                # Verify user exists
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User not found: {user_id}")
                    return None

                # Create execution
                execution = GraphExecution(
                    user_id=user_id,
                    workflow_id=workflow_id,
                    input_data=input_data,
                    status="pending",
                    created_at=datetime.utcnow(),
                )
                db.add(execution)
                db.commit()
                db.refresh(execution)

                logger.info(f"Created execution: {execution.id}")
                return execution

        except SQLAlchemyError as e:
            logger.error(f"Failed to create execution: {e}")
            return None

    def get_execution_history(
        self,
        user_id: str,
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[GraphExecution]:
        """Get execution history for a user."""

        try:
            with get_db() as db:
                query = db.query(GraphExecution).filter(
                    GraphExecution.user_id == user_id
                )

                if workflow_id:
                    query = query.filter(GraphExecution.workflow_id == workflow_id)

                executions = (
                    query
                    .order_by(GraphExecution.created_at.desc())
                    .limit(limit)
                    .all()
                )

                return executions

        except SQLAlchemyError as e:
            logger.error(f"Failed to get execution history: {e}")
            return []

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        output_data: Optional[dict] = None,
    ) -> bool:
        """Update execution status and output."""

        try:
            with get_db() as db:
                execution = db.query(GraphExecution).filter(
                    GraphExecution.id == execution_id
                ).first()

                if not execution:
                    logger.error(f"Execution not found: {execution_id}")
                    return False

                execution.status = status
                if output_data:
                    execution.output_data = output_data
                execution.updated_at = datetime.utcnow()

                db.commit()
                logger.info(f"Updated execution {execution_id} status to {status}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to update execution: {e}")
            return False

    def get_execution_with_nodes(
        self,
        execution_id: str,
    ) -> Optional[dict]:
        """Get execution with all node executions."""

        try:
            with get_db() as db:
                execution = db.query(GraphExecution).filter(
                    GraphExecution.id == execution_id
                ).first()

                if not execution:
                    return None

                # Get node executions
                nodes = db.query(NodeExecution).filter(
                    NodeExecution.graph_execution_id == execution_id
                ).order_by(NodeExecution.created_at).all()

                return {
                    "execution": execution,
                    "nodes": nodes,
                    "node_count": len(nodes),
                }

        except SQLAlchemyError as e:
            logger.error(f"Failed to get execution with nodes: {e}")
            return None


# Usage in API layer
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/executions")
execution_service = ExecutionHistoryService()

@router.get("/{execution_id}")
def get_execution(execution_id: str):
    """Get execution with node details."""
    result = execution_service.get_execution_with_nodes(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result

@router.get("/user/{user_id}")
def get_user_executions(user_id: str, limit: int = 50):
    """Get user's execution history."""
    executions = execution_service.get_execution_history(
        user_id=user_id,
        limit=limit,
    )
    return {"executions": executions, "count": len(executions)}
```

### Example 4: Testing Usage

Show how to use the database service in tests:

```python
import pytest
from sqlalchemy.orm import Session
from backend.services.database import (
    init_db,
    get_db,
    reset_engine,
    reset_session_factory,
    Base,
)
from backend.models import User, Workflow

# Session-level fixture
@pytest.fixture(scope="session")
def setup_test_database():
    """Setup database once for all tests."""
    # Initialize database
    init_db()
    yield
    # Cleanup
    reset_engine()
    reset_session_factory()

# Function-level fixture
@pytest.fixture
def db(setup_test_database) -> Session:
    """Provide database session for each test."""
    with get_db() as session:
        yield session
        # Rollback any changes made during test
        session.rollback()

# Test using database
def test_create_user(db: Session):
    """Test user creation."""
    # Create user
    user = User(
        email="test@example.com",
        name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Verify user was created
    assert user.id is not None
    assert user.email == "test@example.com"

    # Query user
    found_user = db.query(User).filter(User.email == "test@example.com").first()
    assert found_user is not None
    assert found_user.id == user.id

def test_user_workflow_relationship(db: Session):
    """Test user-workflow relationship."""
    # Create user
    user = User(email="owner@example.com", name="Owner")
    db.add(user)
    db.flush()

    # Create workflow
    workflow = Workflow(
        name="Test Workflow",
        owner_id=user.id,
    )
    db.add(workflow)
    db.commit()

    # Query workflows for user
    workflows = db.query(Workflow).filter(Workflow.owner_id == user.id).all()
    assert len(workflows) == 1
    assert workflows[0].name == "Test Workflow"

def test_transaction_rollback(db: Session):
    """Test transaction rollback on error."""
    # Create user
    user = User(email="rollback@example.com", name="Rollback Test")
    db.add(user)
    db.commit()

    # Try to create duplicate (should fail)
    with pytest.raises(Exception):
        duplicate = User(email="rollback@example.com", name="Duplicate")
        db.add(duplicate)
        db.commit()

    # Rollback should have occurred
    db.rollback()

    # Original user should still exist
    found = db.query(User).filter(User.email == "rollback@example.com").first()
    assert found is not None
    assert found.name == "Rollback Test"

# Integration test
@pytest.mark.integration
def test_database_connection():
    """Test database connection."""
    from backend.services.database import get_engine
    from sqlalchemy import text

    engine = get_engine()

    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

# Mock database for unit tests
@pytest.fixture
def mock_db(mocker):
    """Mock database session for unit tests."""
    mock_session = mocker.MagicMock(spec=Session)
    mocker.patch(
        "backend.services.database.get_db",
        return_value=mock_session,
    )
    return mock_session

def test_service_with_mock_db(mock_db):
    """Test service using mocked database."""
    from backend.services.some_service import SomeService

    # Setup mock
    mock_db.query().filter().first.return_value = User(
        id="user123",
        email="test@example.com",
    )

    # Test service
    service = SomeService()
    user = service.get_user("user123")

    assert user.id == "user123"
    assert user.email == "test@example.com"
```

## Performance Considerations

### Performance Characteristics

**Engine and Connection Pool:**

- Engine creation: O(1) - Singleton pattern
- Connection acquisition: O(1) - Connection pool
- Connection pool size: Configurable (default: 5 + 5 overflow)
- Pool timeout: Configurable (default: 30 seconds)

**Session Operations:**

- Session creation: O(1) - Factory pattern
- Query execution: Depends on query complexity and indexes
- Transaction commit: O(n) where n = number of changes
- Session cleanup: O(1) - Connection returned to pool

**Database Initialization:**

- `init_db()`: O(m + n) where m = tables, n = migrations
- Advisory lock: O(1) - PostgreSQL internal
- Table creation: O(m) where m = number of tables
- Migration execution: O(n) where n = number of migrations

**I/O Characteristics:**

- I/O-bound operations (network/disk)
- Connection pool reduces connection overhead
- Pre-ping adds latency but improves reliability
- Statement timeout prevents runaway queries

### Optimisation Tips

#### Tip 1: Use Connection Pooling Effectively

**Problem:**

```python
# Creating new engine for each request (inefficient)
def get_user(user_id: str):
    engine = create_database_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
        return result.fetchone()
```

**Solution:**

```python
# Use global engine and session factory (efficient)
from backend.services.database import get_db

def get_user(user_id: str):
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()
```

**Benefit:** Reuses connections from pool, reduces connection overhead by 90%+

#### Tip 2: Batch Operations

**Problem:**

```python
# Multiple round trips to database (inefficient)
from backend.services.database import get_db

def update_users(user_updates: list[dict]):
    for update in user_updates:
        with get_db() as db:
            user = db.query(User).filter(User.id == update["id"]).first()
            user.name = update["name"]
            db.commit()  # Commit for each user
```

**Solution:**

```python
# Single transaction for all updates (efficient)
from backend.services.database import get_db

def update_users(user_updates: list[dict]):
    with get_db() as db:
        for update in user_updates:
            user = db.query(User).filter(User.id == update["id"]).first()
            if user:
                user.name = update["name"]
        # Single commit for all updates
```

**Benefit:** Reduces database round trips from n to 1, improves throughput by 10-100x

#### Tip 3: Use Query Optimization

**Problem:**

```python
# N+1 query problem (inefficient)
from backend.services.database import get_db

def get_workflows_with_owners():
    with get_db() as db:
        workflows = db.query(Workflow).all()
        result = []
        for workflow in workflows:
            # Additional query for each workflow
            owner = db.query(User).filter(User.id == workflow.owner_id).first()
            result.append({"workflow": workflow, "owner": owner})
        return result
```

**Solution:**

```python
# Eager loading with join (efficient)
from backend.services.database import get_db
from sqlalchemy.orm import joinedload

def get_workflows_with_owners():
    with get_db() as db:
        workflows = (
            db.query(Workflow)
            .options(joinedload(Workflow.owner))
            .all()
        )
        return [{"workflow": w, "owner": w.owner} for w in workflows]
```

**Benefit:** Reduces queries from n+1 to 1, improves latency by 10-100x

#### Tip 4: Connection Pool Sizing

```python
from backend.services.database import DatabaseConfig, create_database_engine

# Development: Small pool
dev_config = DatabaseConfig.from_env()
dev_config.pool_size = 5
dev_config.max_overflow = 5

# Production: Larger pool based on workers
# Formula: pool_size = (num_workers * 2) + overflow
prod_config = DatabaseConfig.from_env()
prod_config.pool_size = 20  # For 8 workers
prod_config.max_overflow = 20
prod_config.pool_timeout = 60

# Create engine with optimised config
engine = create_database_engine(prod_config)
```

**Guidelines:**

- Development: pool_size = 5-10
- Production: pool_size = (concurrent_requests / 2) to concurrent_requests
- max_overflow = pool_size (doubles capacity for spikes)
- Monitor pool exhaustion and adjust accordingly

#### Tip 5: Statement Timeout

```python
# Set appropriate statement timeout
config = DatabaseConfig.from_env()
config.statement_timeout_ms = 30000  # 30 seconds for normal queries

# For long-running queries (reports, analytics)
config.statement_timeout_ms = 300000  # 5 minutes
```

**Guidelines:**

- API queries: 5-30 seconds
- Background jobs: 1-10 minutes
- Analytics queries: 10-30 minutes
- Monitor slow query log and adjust timeouts

### Async/Await Support

The current implementation is synchronous. For async support, use SQLAlchemy 2.0's async features:

```python
# Future async implementation example (not currently implemented)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:5432/db",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_async_db():
    """Async context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Usage
async def get_user_async(user_id: str):
    async with get_async_db() as db:
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

### Connection Pooling

The database service uses SQLAlchemy's QueuePool with optimised settings:

**Pool Configuration:**

- `pool_size=5` - Core pool size (always maintained)
- `max_overflow=5` - Additional connections on demand (total: 10)
- `pool_timeout=30` - Wait 30s for connection before failing
- `pool_recycle=180` - Recycle connections every 3 minutes
- `pool_use_lifo=True` - Reuse recent connections (better for cloud)
- `pool_pre_ping=True` - Test connections before use

**Best Practices:**

- Set pool_size based on concurrent requests
- Use pool_pre_ping in cloud environments
- Monitor pool exhaustion with logging
- Adjust pool_recycle for cloud database idle timeouts

### Batch Operations

```python
from backend.services.database import get_db
from backend.models import User

# Efficient batch insert
def create_users_batch(user_data_list: list[dict]):
    with get_db() as db:
        users = [User(**data) for data in user_data_list]
        db.bulk_save_objects(users)
        # Single commit for all inserts

# Efficient batch update
def update_users_batch(updates: list[dict]):
    with get_db() as db:
        db.bulk_update_mappings(User, updates)
        # Single commit for all updates
```

**Guidelines:**

- Use `bulk_save_objects()` for inserts (10-100x faster)
- Use `bulk_update_mappings()` for updates
- Batch size: 100-1000 records per transaction
- Commit once per batch, not per record

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from backend.services.database import get_db, DatabaseConfig

@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = None
    return session

@pytest.fixture
def mock_get_db(mock_session):
    """Mock get_db context manager."""
    @contextmanager
    def _mock_get_db():
        yield mock_session
    return _mock_get_db

def test_database_config_from_env():
    """Test configuration loading from environment."""
    with patch.dict('os.environ', {
        'DATABASE_URL': 'postgresql://user:pass@host:5432/db',
        'DB_POOL_SIZE': '10',
        'DB_MAX_OVERFLOW': '20',
    }):
        config = DatabaseConfig.from_env()

        assert 'postgresql://user:pass@host:5432/db' in config.connection_string
        assert config.pool_size == 10
        assert config.max_overflow == 20

def test_get_connect_args():
    """Test connection args generation."""
    config = DatabaseConfig(
        connection_string="postgresql://localhost/test",
        keepalives_idle=60,
        connect_timeout=20,
    )

    connect_args = config.get_connect_args()

    assert connect_args["keepalives"] == 1
    assert connect_args["keepalives_idle"] == 60
    assert connect_args["connect_timeout"] == 20
    assert "statement_timeout" in connect_args["options"]

def test_service_with_mocked_db(mock_get_db, mock_session):
    """Test service layer with mocked database."""
    from backend.models import User

    # Setup mock
    mock_user = User(id="user123", email="test@example.com")
    mock_session.first.return_value = mock_user

    # Use mocked get_db
    with patch('backend.services.database.get_db', mock_get_db):
        with get_db() as db:
            user = db.query(User).filter(User.id == "user123").first()

        assert user.id == "user123"
        assert user.email == "test@example.com"
```

### Mocking Dependencies

```python
@patch('backend.services.database.get_engine')
def test_session_factory_creation(mock_get_engine):
    """Test session factory creation with mocked engine."""
    from backend.services.database import create_session_factory

    mock_engine = Mock()
    mock_get_engine.return_value = mock_engine

    session_factory = create_session_factory()

    assert session_factory is not None
    mock_get_engine.assert_called_once()

@patch('backend.services.database.create_database_engine')
def test_init_db_with_mock(mock_create_engine):
    """Test init_db with mocked engine."""
    from backend.services.database import init_db

    mock_engine = Mock()
    mock_connection = Mock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection

    # Mock advisory lock
    mock_result = Mock()
    mock_result.scalar.return_value = True
    mock_connection.execute.return_value = mock_result

    mock_create_engine.return_value = mock_engine

    # Run init_db
    with patch('backend.services.database.get_engine', return_value=mock_engine):
        init_db()

    # Verify advisory lock was attempted
    assert mock_connection.execute.called
```

### Integration Testing

```python
@pytest.mark.integration
def test_database_connection():
    """Test real database connection."""
    from backend.services.database import get_engine
    from sqlalchemy import text

    engine = get_engine()

    with engine.connect() as conn:
        # Test basic query
        result = conn.execute(text("SELECT 1 as value"))
        assert result.scalar() == 1

        # Test PostgreSQL version
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version

@pytest.mark.integration
def test_full_crud_workflow():
    """Test complete CRUD workflow."""
    from backend.services.database import get_db
    from backend.models import User
    import uuid

    user_id = str(uuid.uuid4())

    # Create
    with get_db() as db:
        user = User(id=user_id, email=f"{user_id}@test.com", name="Test User")
        db.add(user)
        db.commit()

    # Read
    with get_db() as db:
        found = db.query(User).filter(User.id == user_id).first()
        assert found is not None
        assert found.email == f"{user_id}@test.com"

    # Update
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        user.name = "Updated Name"
        db.commit()

    # Verify update
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        assert user.name == "Updated Name"

    # Delete
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        db.delete(user)
        db.commit()

    # Verify deletion
    with get_db() as db:
        found = db.query(User).filter(User.id == user_id).first()
        assert found is None

@pytest.mark.integration
def test_transaction_rollback():
    """Test transaction rollback on error."""
    from backend.services.database import get_db
    from backend.models import User
    from sqlalchemy.exc import IntegrityError

    # Create user
    with get_db() as db:
        user = User(email="unique@test.com", name="Unique User")
        db.add(user)
        db.commit()

    # Try to create duplicate (should rollback)
    try:
        with get_db() as db:
            duplicate = User(email="unique@test.com", name="Duplicate")
            db.add(duplicate)
            db.commit()
    except IntegrityError:
        pass  # Expected

    # Verify only one user exists
    with get_db() as db:
        count = db.query(User).filter(User.email == "unique@test.com").count()
        assert count == 1
```

## Best Practices

### Do's

✅ **Use `get_db()` context manager for automatic transaction management**

```python
from backend.services.database import get_db

# Correct: Automatic commit/rollback/cleanup
with get_db() as db:
    user = db.query(User).first()
    user.name = "Updated"
    # Automatically commits on success
```

**Why:** Guarantees proper session cleanup and transaction management, prevents connection leaks.

✅ **Initialise database once on application startup**

```python
from fastapi import FastAPI
from backend.services.database import init_db

app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()  # Safe for multi-worker deployments
```

**Why:** PostgreSQL advisory locks ensure safe concurrent initialisation across workers.

✅ **Use FastAPI dependency injection for route handlers**

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.services.database import get_db

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

**Why:** FastAPI handles session lifecycle, provides better testing support, cleaner code.

✅ **Configure connection pool based on deployment environment**

```python
# Production configuration
import os
os.environ['DB_POOL_SIZE'] = '20'
os.environ['DB_MAX_OVERFLOW'] = '20'
os.environ['DB_POOL_RECYCLE_SECONDS'] = '180'
os.environ['DB_POOL_PRE_PING'] = 'true'
```

**Why:** Optimises resource usage and reliability for production workloads.

✅ **Use ORM models with `Base` for type safety**

```python
from backend.services.database import Base
from sqlalchemy import Column, String, Integer

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
```

**Why:** Provides type hints, query builder, relationship management, and migration support.

✅ **Handle database exceptions appropriately**

```python
from sqlalchemy.exc import IntegrityError, OperationalError

try:
    with get_db() as db:
        db.add(user)
except IntegrityError:
    return {"error": "User already exists"}
except OperationalError:
    logger.error("Database connection failed")
    raise
```

**Why:** Different exceptions require different handling strategies (retry, user error, system error).

### Don'ts

❌ **Don't create engine or session factory in request handlers**

```python
# WRONG: Creates new engine on every request
from backend.services.database import create_database_engine

@app.get("/users")
def list_users():
    engine = create_database_engine()  # ❌ Very inefficient
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users"))
        return result.fetchall()
```

**Why:** Bypasses connection pooling, creates new connections on every request, 100x slower.

**Correct approach:**

```python
# CORRECT: Use get_db() context manager
from backend.services.database import get_db

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

❌ **Don't forget to handle transactions manually when using session factory**

```python
# WRONG: No commit or rollback
from backend.services.database import get_session_factory

SessionFactory = get_session_factory()
db = SessionFactory()
user = User(email="test@example.com")
db.add(user)
# ❌ Missing commit, user never saved
```

**Why:** Changes are not persisted without commit, session leaks without close.

**Correct approach:**

```python
# CORRECT: Use get_db() or manual transaction management
with get_db() as db:
    user = User(email="test@example.com")
    db.add(user)
    # Automatically commits
```

❌ **Don't use raw SQL strings without parameterisation**

```python
# WRONG: SQL injection vulnerability
from backend.services.database import get_db
from sqlalchemy import text

email = request.args.get("email")
with get_db() as db:
    # ❌ SQL injection risk
    result = db.execute(text(f"SELECT * FROM users WHERE email = '{email}'"))
```

**Why:** Vulnerable to SQL injection attacks, bypasses query parameterisation safety.

**Correct approach:**

```python
# CORRECT: Use ORM or parameterised queries
with get_db() as db:
    # ORM (preferred)
    user = db.query(User).filter(User.email == email).first()

    # Or parameterised raw SQL
    result = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": email}
    )
```

❌ **Don't run migrations manually in production**

```python
# WRONG: Manual migration execution
from backend.services.database.migrations.schema_updates import add_thread_id_column
from backend.services.database import get_engine

engine = get_engine()
with engine.connect() as conn:
    add_thread_id_column(conn)  # ❌ No lock, not tracked
```

**Why:** No advisory lock protection, race conditions in multi-worker deployments, not tracked in registry.

**Correct approach:**

```python
# CORRECT: Use init_db() which handles locks and tracking
from backend.services.database import init_db

init_db()  # Runs all migrations safely
```

❌ **Don't query inside loops (N+1 problem)**

```python
# WRONG: N+1 query problem
from backend.services.database import get_db

with get_db() as db:
    workflows = db.query(Workflow).all()
    for workflow in workflows:
        # ❌ Additional query for each workflow
        owner = db.query(User).filter(User.id == workflow.owner_id).first()
        print(f"{workflow.name} - {owner.name}")
```

**Why:** Executes n+1 database queries instead of 1, extremely slow for large datasets.

**Correct approach:**

```python
# CORRECT: Use eager loading with joinedload
from sqlalchemy.orm import joinedload

with get_db() as db:
    workflows = db.query(Workflow).options(joinedload(Workflow.owner)).all()
    for workflow in workflows:
        print(f"{workflow.name} - {workflow.owner.name}")  # No additional query
```

❌ **Don't ignore connection pool exhaustion**

```python
# WRONG: Not monitoring pool usage
# Default pool_size=5 may be too small for production
```

**Why:** Pool exhaustion causes request timeouts, poor user experience, cascading failures.

**Correct approach:**

```python
# CORRECT: Monitor and adjust pool configuration
import os

# Set based on expected concurrent requests
os.environ['DB_POOL_SIZE'] = '20'
os.environ['DB_MAX_OVERFLOW'] = '20'

# Monitor pool usage in logs
# Increase if seeing "QueuePool limit exceeded" errors
```

## Related Documentation

### Related Services

- [Auth Service](./auth.md) - User authentication, uses database for user storage
- [Checkpoint Service](./checkpoint.md) - Checkpoint persistence, uses database for state storage
- [Memory Service](./memory.md) - Conversation memory, uses database for message history

### Related API Modules

- [Auth API](../agents-guide/api/auth.md) - Authentication endpoints using database sessions
- [Graph API](../agents-guide/api/graph.md) - Workflow execution tracking in database

### Architecture Documentation

- Database schema is defined in `backend/models/` - All ORM model definitions
- Migration system is in `backend/services/database/migrations/` - Schema evolution

### External Documentation

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - ORM and database toolkit
- [PostgreSQL Documentation](https://www.postgresql.org/docs/) - Database server
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/) - FastAPI integration patterns
- [psycopg2 Documentation](https://www.psycopg.org/docs/) - PostgreSQL adapter

## Summary

The database service is a foundational layer that provides PostgreSQL database connectivity, session management, and
schema migration capabilities for the AgenticStudio backend. It abstracts SQLAlchemy configuration and provides a clean,
consistent API for database access throughout the application.

The service is built around three core concepts: the `Base` declarative class for ORM models, the `get_db()` context
manager for session management, and the `init_db()` function for worker-safe database initialisation. It uses singleton
patterns for the database engine and session factory to ensure efficient connection pooling and resource management.

The migration system uses PostgreSQL advisory locks to enable safe concurrent initialisation in multi-worker
deployments (e.g., Gunicorn, Uvicorn with multiple workers). All migrations are idempotent and can be safely run
multiple times. The `DatabaseConfig` class provides comprehensive configuration management with support for both
`DATABASE_URL` and component-based environment variables, with optimised defaults for cloud deployments.

**Key Features:**

- PostgreSQL connection management with optimised connection pooling
- Thread-safe database engine and session factory singletons
- Context manager for automatic transaction management and cleanup
- Worker-safe database initialisation using PostgreSQL advisory locks
- Idempotent schema migration system with registry-based tracking
- FastAPI dependency injection support
- Comprehensive configuration via environment variables
- Production-ready defaults for Azure/cloud deployments

**Primary Use Cases:**

- FastAPI route handlers requiring database access
- Service layer persistence operations
- Application startup database initialisation
- ORM model definition and table creation
- Schema evolution through migrations
- Testing with database fixtures

**When to Use This Service:**

- Any operation requiring PostgreSQL database access
- Creating new ORM models
- Implementing CRUD operations
- Running database queries
- Managing database sessions and transactions
- Initialising database schema on application startup
- Evolving database schema through migrations
