# Checkpoint Service

## Overview

The checkpoint service provides comprehensive metadata management for LangGraph checkpoints, solving the critical issue
where LangGraph's native checkpoint storage doesn't preserve custom interrupt metadata across checkpoint boundaries. The
service implements a layered architecture combining in-memory caching with persistent database storage for optimal
performance.

**Location:** `backend/services/checkpoint/`

**Primary Responsibilities:**

- Store and retrieve checkpoint metadata for paused workflows
- Manage subworkflow checkpoint context and parent-child relationships
- Track checkpoint lifecycle status (active, resumed, completed)
- Provide fast access through in-memory caching
- Ensure data consistency between cache and database

**Key Use Cases:**

- Persisting workflow pause/interrupt metadata for resumption
- Tracking subworkflow execution context across checkpoints
- Managing email inbox checkpoints for asynchronous responses
- Maintaining parent-child workflow relationships during delegation
- Supporting checkpoint-based workflow recovery and debugging

## Architecture

### Module Structure

```
backend/services/checkpoint/
├── __init__.py              # Public API exports and module documentation
├── types.py                 # TypedDict definitions and constants
├── cache.py                 # In-memory cache implementation
├── repository.py            # Database operations layer (Repository pattern)
└── metadata_manager.py      # Main service orchestration layer
```

**File Descriptions:**

- **`__init__.py`**: Defines the public API surface by exporting key classes, functions, and types. Provides
  module-level documentation and usage examples.

- **`types.py`**: Contains type definitions including `CheckpointMetadataDict` (TypedDict for metadata structure) and
  `CheckpointStatusType` (constants for checkpoint states).

- **`cache.py`**: Implements `CheckpointMetadataCache`, a simple dictionary-based in-memory cache for fast metadata
  access without database queries.

- **`repository.py`**: Implements `CheckpointMetadataRepository` following the Repository pattern, encapsulating all
  SQLAlchemy database operations for checkpoint metadata.

- **`metadata_manager.py`**: Implements `CheckpointMetadataManager`, the main service class that orchestrates cache and
  repository operations, providing the primary interface for checkpoint metadata management.

### Design Patterns

**Repository Pattern:**
The service uses the Repository pattern to abstract database operations, providing a clean separation between data
access logic (`CheckpointMetadataRepository`) and business logic (`CheckpointMetadataManager`).

**Cache-Aside Pattern:**
The manager implements cache-aside (lazy loading) caching:

1. Check cache first on read
2. On cache miss, query database
3. Populate cache with database result
4. Write-through on updates (update both cache and database)

**Singleton-like Access:**
The module provides a singleton-like access pattern through `get_checkpoint_metadata_manager()`, allowing consistent
access while maintaining testability through dependency injection.

**Component Relationships:**

```
┌─────────────────────────────────────┐
│   API Layer / Execution Engine      │
│  (resume_handler, execution_engine) │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   CheckpointMetadataManager         │
│   (Service Orchestration Layer)     │
│   - Coordinates cache & repository  │
│   - Business logic                  │
└──────┬──────────────────────┬───────┘
       │                      │
       ▼                      ▼
┌──────────────┐    ┌─────────────────┐
│    Cache     │    │   Repository    │
│  (In-Memory) │    │   (Database)    │
└──────────────┘    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ CheckpointMetadata│
                    │  (SQLAlchemy)   │
                    └─────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.models.execution.checkpoint.CheckpointMetadata` - SQLAlchemy model for database storage
- `backend.services.database.SessionLocal` - Database session management
- `backend.services.config.get_logger` - Logging infrastructure

**External Dependencies:**

- `sqlalchemy` - Database ORM and query building
- `typing` - Type hints and TypedDict definitions

**Database Dependencies:**

- **Table:** `checkpoint_metadata`
- **Relationships:** Foreign key to `node_executions.id` for checkpoint node tracking
- **Indexes:** Indexes on `checkpoint_id` (unique) and `thread_id` for fast lookups

**Environment Variables:**
None directly consumed by this service. Database configuration is inherited from `backend.services.database`.

## Public API

### Exported Classes

- `CheckpointMetadataManager` - Main service for managing checkpoint metadata with caching
- `CheckpointMetadataRepository` - Database operations layer for checkpoint metadata
- `CheckpointMetadataCache` - In-memory cache for fast metadata access
- `CheckpointMetadataDict` - TypedDict defining metadata structure

### Exported Functions

- `get_checkpoint_metadata_manager()` - Factory function returning the manager singleton instance
- `checkpoint_metadata_manager` - Pre-initialised global manager instance (legacy)

### Constants and Configuration

**`CheckpointStatusType`** - Constants for checkpoint lifecycle states:

- `CheckpointStatusType.ACTIVE` - Checkpoint is active and can be resumed (`"active"`)
- `CheckpointStatusType.RESUMED` - Checkpoint has been resumed (`"resumed"`)
- `CheckpointStatusType.COMPLETED` - Checkpoint execution has completed (`"completed"`)

**Type Definitions:**

- `CheckpointMetadataDict` - TypedDict for checkpoint metadata structure
- `MetadataDict` - Alias for `Dict[str, Any]` used for general metadata

### Exceptions

This module does not define custom exceptions. It relies on:

- **SQLAlchemy Exceptions** - Caught and logged internally:
  - `SQLAlchemyError` - General database errors
  - `IntegrityError` - Constraint violations (e.g., duplicate checkpoint_id)

Error handling is done through return values:

- Database operations return `None` on failure
- Boolean operations return `False` on failure
- All errors are logged with appropriate context

## Core Classes

### `CheckpointMetadataManager`

Main service class for managing checkpoint metadata, providing a high-level interface that combines caching and database
operations for optimal performance.

**Purpose:** Orchestrate checkpoint metadata storage, retrieval, and lifecycle management while maintaining consistency
between cache and database layers.

**Responsibilities:**

- Store checkpoint metadata with automatic cache/database synchronisation
- Retrieve metadata with cache-first strategy
- Update checkpoint status throughout lifecycle
- Manage active checkpoint queries
- Clear completed checkpoint metadata

**Initialisation:**

```python
def __init__(
    self,
    repository: Optional[CheckpointMetadataRepository] = None,
    cache: Optional[CheckpointMetadataCache] = None,
) -> None:
    """
    Args:
        repository: Optional repository instance (creates default if None)
        cache: Optional cache instance (creates default if None)
    """
```

**Attributes:**

- `repository: CheckpointMetadataRepository` - Database operations layer
- `cache: CheckpointMetadataCache` - In-memory cache layer

**Key Methods:**

#### `store_checkpoint_metadata()`

Store or update checkpoint metadata in both database and cache.

```python
def store_checkpoint_metadata(
    self,
    checkpoint_id: str,
    thread_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """Store checkpoint metadata in database and cache."""
```

**Parameters:**

- `checkpoint_id` (str) - Unique checkpoint identifier from LangGraph
- `thread_id` (str) - Thread/execution identifier
- `metadata` (Dict[str, Any]) - Checkpoint metadata dictionary containing interrupt data and context

**Returns:**

- `bool` - True if stored successfully, False on database error

**Raises:**
No exceptions raised directly. Database errors are caught and logged.

**Example:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Store subworkflow checkpoint metadata
success = manager.store_checkpoint_metadata(
    checkpoint_id="cp_1a2b3c4d",
    thread_id="thread_xyz789",
    metadata={
        "subworkflow_checkpoint": True,
        "subworkflow_name": "email-processor",
        "subworkflow_thread_id": "sub_thread_abc123",
        "parent_execution_id": "exec_parent_456",
        "checkpoint_node_exec_id": "node_exec_789",
        "parent_tool_call": {
            "id": "call_123",
            "function": {"name": "send_email"},
        },
    },
)

if success:
    print("Checkpoint metadata stored successfully")
```

**Behaviour:**

- Checks if checkpoint already exists in database
- If exists, updates the record with new metadata
- If new, creates a new database record
- On success, updates cache with metadata
- All operations are logged with DEBUG and INFO levels
- Database errors are caught, logged, and return False

**Side Effects:**

- Writes to database (`checkpoint_metadata` table)
- Updates in-memory cache
- Logs INFO level messages for tracking

**Use Cases:**

- Store interrupt metadata when workflow pauses for user input
- Save subworkflow context during workflow delegation
- Persist email inbox checkpoint information
- Update checkpoint metadata when resuming with new context

#### `get_checkpoint_metadata()`

Retrieve checkpoint metadata using cache-first strategy.

```python
def get_checkpoint_metadata(
    self,
    checkpoint_id: str,
) -> Optional[MetadataDict]:
    """Retrieve checkpoint metadata from cache or database."""
```

**Parameters:**

- `checkpoint_id` (str) - The checkpoint ID to look up

**Returns:**

- `Optional[MetadataDict]` - Metadata dictionary if found, None if not found or on error

**Raises:**
No exceptions raised. Database errors are caught and logged.

**Example:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Retrieve checkpoint metadata
metadata = manager.get_checkpoint_metadata("cp_1a2b3c4d")

if metadata:
    print(f"Thread ID: {metadata['thread_id']}")
    if metadata.get("subworkflow_checkpoint"):
        print(f"Subworkflow: {metadata['subworkflow_name']}")
        print(f"Parent execution: {metadata['parent_execution_id']}")
else:
    print("Checkpoint not found")
```

**Behaviour:**

- First checks in-memory cache for metadata
- On cache hit, returns cached data immediately
- On cache miss, queries database for active checkpoint
- Database result is converted to dictionary format
- Cache is populated with database result for future requests
- Returns None if checkpoint not found or not active

**Side Effects:**

- May populate cache on database hit
- Logs DEBUG/INFO messages for cache hits/misses

**Use Cases:**

- Retrieve subworkflow context when resuming execution
- Check if checkpoint is for subworkflow delegation
- Get parent execution details for context propagation
- Retrieve email inbox address for response routing

#### `update_checkpoint_status()`

Update the lifecycle status of a checkpoint.

```python
def update_checkpoint_status(
    self,
    checkpoint_id: str,
    status: str,
) -> bool:
    """Update the status of a checkpoint."""
```

**Parameters:**

- `checkpoint_id` (str) - The checkpoint ID to update
- `status` (str) - New status value (use `CheckpointStatusType` constants)

**Returns:**

- `bool` - True if updated successfully, False if checkpoint not found or on error

**Raises:**
No exceptions raised. Database errors are caught and logged.

**Example:**

```python
from backend.services.checkpoint import (
    get_checkpoint_metadata_manager,
    CheckpointStatusType,
)

manager = get_checkpoint_metadata_manager()

# Mark checkpoint as completed after successful resume
success = manager.update_checkpoint_status(
    "cp_1a2b3c4d",
    CheckpointStatusType.COMPLETED,
)

if success:
    print("Checkpoint marked as completed")
```

**Behaviour:**

- Updates status field in database record
- Sets `updated_at` timestamp to current UTC time
- Returns False if checkpoint not found
- Cache is NOT automatically invalidated (cache may be stale)

**Use Cases:**

- Mark checkpoint as RESUMED when resumption begins
- Mark checkpoint as COMPLETED when execution finishes
- Track checkpoint lifecycle for auditing and debugging

#### `clear_checkpoint_metadata()`

Clear checkpoint from cache and mark as completed in database.

```python
def clear_checkpoint_metadata(
    self,
    checkpoint_id: str,
) -> bool:
    """Clear checkpoint metadata from cache and mark as completed in database."""
```

**Parameters:**

- `checkpoint_id` (str) - The checkpoint ID to clear

**Returns:**

- `bool` - True if cleared successfully, False on database error

**Raises:**
No exceptions raised. Database errors are caught and logged.

**Example:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Clear checkpoint after successful completion
manager.clear_checkpoint_metadata("cp_1a2b3c4d")
```

**Behaviour:**

- Removes checkpoint from cache immediately
- Updates database status to COMPLETED
- Both operations are logged
- Returns result from status update operation

**Side Effects:**

- Removes entry from cache
- Updates database status and timestamp

**Use Cases:**

- Clean up checkpoint after successful execution
- Remove stale checkpoints from cache
- Mark checkpoints as completed for historical tracking

#### `get_active_checkpoints()`

Get all active checkpoints, optionally filtered by thread ID.

```python
def get_active_checkpoints(
    self,
    thread_id: Optional[str] = None,
) -> List[MetadataDict]:
    """Get all active checkpoints, optionally filtered by thread ID."""
```

**Parameters:**

- `thread_id` (Optional[str]) - Optional thread ID to filter by (default: None returns all)

**Returns:**

- `List[MetadataDict]` - List of checkpoint metadata dictionaries (empty list on error)

**Raises:**
No exceptions raised. Database errors are caught and logged.

**Example:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Get all active checkpoints for a specific thread
active_checkpoints = manager.get_active_checkpoints("thread_xyz789")

for checkpoint in active_checkpoints:
    print(f"Checkpoint: {checkpoint['checkpoint_id']}")
    print(f"  Created: {checkpoint.get('created_at')}")
    print(f"  Subworkflow: {checkpoint.get('subworkflow_checkpoint')}")
    print(f"  Node: {checkpoint.get('checkpoint_node_exec_id')}")

# Get all active checkpoints across all threads
all_active = manager.get_active_checkpoints()
print(f"Total active checkpoints: {len(all_active)}")
```

**Behaviour:**

- Queries database for checkpoints with status = "active"
- Optionally filters by thread_id if provided
- Converts each model instance to metadata dictionary
- Adds `created_at` timestamp as ISO format string
- Returns empty list on database errors

**Use Cases:**

- List all paused workflows for a user session
- Check for pending checkpoints before cleanup
- Display active checkpoints in admin dashboard
- Audit checkpoint usage across system

### `CheckpointMetadataRepository`

Database operations layer following the Repository pattern, encapsulating all SQLAlchemy operations for checkpoint
metadata.

**Purpose:** Provide a clean abstraction over database operations with proper error handling and transaction management.

**Responsibilities:**

- Execute database queries for checkpoint metadata
- Handle database errors gracefully
- Convert between ORM models and dictionaries
- Manage database sessions and transactions

**Key Methods:**

#### `get_by_checkpoint_id()`

Retrieve checkpoint metadata by checkpoint ID with optional status filter.

```python
@staticmethod
def get_by_checkpoint_id(
    checkpoint_id: str,
    status: Optional[str] = None,
) -> Optional[CheckpointMetadata]:
    """Retrieve checkpoint metadata by checkpoint ID."""
```

**Parameters:**

- `checkpoint_id` (str) - The checkpoint ID to look up
- `status` (Optional[str]) - Optional status filter (e.g., "active", "completed")

**Returns:**

- `Optional[CheckpointMetadata]` - SQLAlchemy model instance if found, None otherwise

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository, CheckpointStatusType

repo = CheckpointMetadataRepository()

# Get active checkpoint only
checkpoint = repo.get_by_checkpoint_id("cp_1a2b3c4d", status=CheckpointStatusType.ACTIVE)
if checkpoint:
    print(f"Thread: {checkpoint.thread_id}")
    print(f"Is subworkflow: {checkpoint.is_subworkflow}")
```

#### `create()`

Create a new checkpoint metadata record in the database.

```python
@staticmethod
def create(
    checkpoint_id: str,
    thread_id: str,
    metadata: Dict[str, Any],
) -> Optional[CheckpointMetadata]:
    """Create a new checkpoint metadata record."""
```

**Parameters:**

- `checkpoint_id` (str) - Unique checkpoint identifier
- `thread_id` (str) - Thread identifier
- `metadata` (Dict[str, Any]) - Dictionary containing checkpoint metadata

**Returns:**

- `Optional[CheckpointMetadata]` - Created model instance if successful, None on error

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository

repo = CheckpointMetadataRepository()

checkpoint = repo.create(
    checkpoint_id="cp_1a2b3c4d",
    thread_id="thread_xyz789",
    metadata={
        "subworkflow_checkpoint": True,
        "subworkflow_name": "email-handler",
        "subworkflow_thread_id": "sub_thread_abc123",
        "checkpoint_node_exec_id": "node_exec_789",
        "parent_execution_id": "exec_parent_456",
        "parent_tool_call": {"id": "call_123"},
    },
)

if checkpoint:
    print(f"Created checkpoint: {checkpoint.id}")
```

**Behaviour:**

- Extracts metadata fields and creates CheckpointMetadata model
- Sets status to ACTIVE by default
- Stores full metadata in `interrupt_data` JSON field
- Commits transaction and refreshes model
- Returns None on IntegrityError (duplicate checkpoint_id) or database error

#### `update()`

Update an existing checkpoint metadata record.

```python
@staticmethod
def update(
    checkpoint_id: str,
    thread_id: str,
    metadata: Dict[str, Any],
) -> Optional[CheckpointMetadata]:
    """Update an existing checkpoint metadata record."""
```

**Parameters:**

- `checkpoint_id` (str) - Checkpoint identifier to update
- `thread_id` (str) - Thread identifier
- `metadata` (Dict[str, Any]) - Updated metadata dictionary

**Returns:**

- `Optional[CheckpointMetadata]` - Updated model instance if successful, None if not found or on error

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository

repo = CheckpointMetadataRepository()

updated = repo.update(
    checkpoint_id="cp_1a2b3c4d",
    thread_id="thread_xyz789",
    metadata={
        "subworkflow_checkpoint": True,
        "subworkflow_name": "email-handler-v2",
        "additional_context": "Updated after retry",
    },
)
```

**Behaviour:**

- Finds existing checkpoint record
- Updates all metadata fields
- Resets status to ACTIVE
- Updates `updated_at` timestamp
- Returns None if checkpoint not found

#### `update_status()`

Update only the status field of a checkpoint.

```python
@staticmethod
def update_status(
    checkpoint_id: str,
    status: str,
) -> bool:
    """Update the status of a checkpoint."""
```

**Parameters:**

- `checkpoint_id` (str) - The checkpoint ID
- `status` (str) - New status value

**Returns:**

- `bool` - True if updated successfully, False if not found or on error

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository, CheckpointStatusType

repo = CheckpointMetadataRepository()

success = repo.update_status("cp_1a2b3c4d", CheckpointStatusType.COMPLETED)
```

#### `get_active_checkpoints()`

Get all active checkpoints with optional thread ID filter.

```python
@staticmethod
def get_active_checkpoints(
    thread_id: Optional[str] = None,
) -> List[CheckpointMetadata]:
    """Get all active checkpoints, optionally filtered by thread ID."""
```

**Parameters:**

- `thread_id` (Optional[str]) - Optional thread ID to filter by

**Returns:**

- `List[CheckpointMetadata]` - List of active checkpoint model instances

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository

repo = CheckpointMetadataRepository()

active = repo.get_active_checkpoints(thread_id="thread_xyz789")
for checkpoint in active:
    print(f"Active checkpoint: {checkpoint.checkpoint_id}")
```

#### `to_metadata_dict()`

Convert CheckpointMetadata model instance to metadata dictionary.

```python
@staticmethod
def to_metadata_dict(
    checkpoint_meta: CheckpointMetadata,
) -> MetadataDict:
    """Convert CheckpointMetadata model to metadata dictionary."""
```

**Parameters:**

- `checkpoint_meta` (CheckpointMetadata) - SQLAlchemy model instance

**Returns:**

- `MetadataDict` - Dictionary containing all checkpoint metadata

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository

repo = CheckpointMetadataRepository()

model = repo.get_by_checkpoint_id("cp_1a2b3c4d")
if model:
    metadata_dict = repo.to_metadata_dict(model)
    print(metadata_dict["thread_id"])
```

**Behaviour:**

- Starts with stored `interrupt_data` JSON
- Overlays key fields from model columns
- Ensures all expected fields are present in result

### `CheckpointMetadataCache`

Simple in-memory dictionary-based cache for checkpoint metadata.

**Purpose:** Provide fast access to checkpoint metadata without database queries.

**Responsibilities:**

- Store metadata in memory by checkpoint_id
- Retrieve cached metadata
- Remove stale entries
- Track cache size

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialize the checkpoint metadata cache."""
```

**Attributes:**

- `_cache: Dict[str, MetadataDict]` - Internal dictionary storing metadata

**Key Methods:**

#### `get()`

```python
def get(self, checkpoint_id: str) -> Optional[MetadataDict]:
    """Retrieve checkpoint metadata from cache."""
```

**Example:**

```python
from backend.services.checkpoint import CheckpointMetadataCache

cache = CheckpointMetadataCache()
metadata = cache.get("cp_1a2b3c4d")
if metadata:
    print(f"Cache hit: {metadata['thread_id']}")
```

#### `set()`

```python
def set(self, checkpoint_id: str, metadata: MetadataDict) -> None:
    """Store checkpoint metadata in cache."""
```

**Example:**

```python
cache.set("cp_1a2b3c4d", {"thread_id": "thread_xyz789", ...})
```

#### `delete()`

```python
def delete(self, checkpoint_id: str) -> bool:
    """Remove checkpoint metadata from cache."""
```

**Returns:**

- `bool` - True if item was cached and removed, False if not in cache

**Example:**

```python
was_cached = cache.delete("cp_1a2b3c4d")
```

#### `clear()`

```python
def clear(self) -> None:
    """Clear all cached checkpoint metadata."""
```

**Example:**

```python
cache.clear()  # Remove all cached items
```

#### `size()`

```python
def size(self) -> int:
    """Get the number of cached items."""
```

**Example:**

```python
num_cached = cache.size()
print(f"Cache contains {num_cached} checkpoints")
```

## Functions

### `get_checkpoint_metadata_manager()`

Factory function that returns the checkpoint metadata manager singleton instance.

**Signature:**

```python
def get_checkpoint_metadata_manager() -> CheckpointMetadataManager:
    """Get the checkpoint metadata manager instance.

    This function provides a singleton-like access pattern while allowing
    for dependency injection and testing flexibility.
    """
```

**Parameters:**
None

**Returns:**

- `CheckpointMetadataManager` - The manager instance (creates on first call)

**Raises:**
No exceptions raised.

**Example:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

# Get manager instance
manager = get_checkpoint_metadata_manager()

# Use manager
manager.store_checkpoint_metadata(
    checkpoint_id="cp_123",
    thread_id="thread_456",
    metadata={"subworkflow_checkpoint": False},
)

# Subsequent calls return same instance
manager2 = get_checkpoint_metadata_manager()
assert manager is manager2  # True
```

**Use Cases:**

- Primary method for accessing checkpoint service in application code
- Enables singleton pattern while maintaining testability
- Recommended over using the global `checkpoint_metadata_manager` instance

## Configuration

### Configuration Classes

This service does not define configuration classes. It uses configuration inherited from:

- `backend.services.database` - Database connection and session management
- `backend.services.config` - Logging configuration

### Environment Variables

This service does not directly consume environment variables. Database configuration is managed by
`backend.services.database`.

### Initialisation Patterns

**Basic Initialisation (Recommended):**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

# Get the singleton manager instance
manager = get_checkpoint_metadata_manager()

# Use manager for all checkpoint operations
metadata = manager.get_checkpoint_metadata("cp_123")
```

**Direct Instantiation (Testing):**

```python
from backend.services.checkpoint import (
    CheckpointMetadataManager,
    CheckpointMetadataRepository,
    CheckpointMetadataCache,
)

# Create with default dependencies
manager = CheckpointMetadataManager()

# Create with custom dependencies (useful for testing)
custom_repo = CheckpointMetadataRepository()
custom_cache = CheckpointMetadataCache()
manager = CheckpointMetadataManager(repository=custom_repo, cache=custom_cache)
```

**Legacy Global Instance:**

```python
from backend.services.checkpoint import checkpoint_metadata_manager

# Pre-initialised global instance (legacy)
# Note: Use get_checkpoint_metadata_manager() in new code
metadata = checkpoint_metadata_manager.get_checkpoint_metadata("cp_123")
```

**Dependency Injection in Execution Engine:**

```python
from backend.services.checkpoint import checkpoint_metadata_manager
from backend.services.execution.resume_handler import ResumeHandler

# Checkpoint service is imported and used directly in resume handler
checkpoint_metadata = checkpoint_metadata_manager.get_checkpoint_metadata(
    checkpoint_id
)

if checkpoint_metadata and checkpoint_metadata.get("subworkflow_checkpoint"):
    # Handle subworkflow checkpoint
    pass
```

## Error Handling

### Exception Hierarchy

This module does not define custom exceptions. It relies on standard Python and SQLAlchemy exceptions:

```
Exception
├── SQLAlchemyError (from sqlalchemy.exc)
│   ├── IntegrityError (duplicate checkpoint_id, constraint violations)
│   └── (other database errors)
└── (standard Python exceptions)
```

### Exception Details

#### SQLAlchemy Exceptions

**When raised:**

- Database connection failures
- Constraint violations (duplicate checkpoint_id)
- Invalid queries or data types
- Transaction failures

**Handling:**
All SQLAlchemy exceptions are caught internally by repository methods and logged. Methods return `None` or `False` to
indicate failure rather than propagating exceptions.

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.checkpoint import (
    get_checkpoint_metadata_manager,
    CheckpointStatusType,
)

manager = get_checkpoint_metadata_manager()

# Store checkpoint metadata
success = manager.store_checkpoint_metadata(
    checkpoint_id="cp_123",
    thread_id="thread_456",
    metadata={"subworkflow_checkpoint": True, "subworkflow_name": "processor"},
)

if not success:
    # Handle storage failure
    logger.error("Failed to store checkpoint metadata")
    # Fallback: continue without persistent checkpoint metadata
    # or raise application-specific exception

# Retrieve checkpoint metadata
metadata = manager.get_checkpoint_metadata("cp_123")

if metadata is None:
    # Handle not found case
    logger.warning("Checkpoint metadata not found")
    # Fallback: treat as regular (non-subworkflow) checkpoint
    metadata = {"subworkflow_checkpoint": False}

# Use metadata safely
if metadata.get("subworkflow_checkpoint"):
    subworkflow_name = metadata.get("subworkflow_name")
    # Process subworkflow checkpoint
```

**Repository-Level Error Handling:**

```python
from backend.services.checkpoint import CheckpointMetadataRepository

repo = CheckpointMetadataRepository()

# Database operations return None on error
checkpoint = repo.create(
    checkpoint_id="cp_123",
    thread_id="thread_456",
    metadata={...},
)

if checkpoint is None:
    # Database operation failed
    # Check logs for specific error (IntegrityError, SQLAlchemyError, etc.)
    logger.error("Failed to create checkpoint metadata")
```

**Cache-First Pattern with Error Recovery:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Try to get metadata (cache-first, falls back to database)
metadata = manager.get_checkpoint_metadata("cp_123")

if metadata is None:
    # Not found in cache or database
    # Could be:
    # 1. Checkpoint doesn't exist
    # 2. Database error occurred (check logs)
    # 3. Checkpoint was already completed/cleared

    # Safe fallback
    metadata = {
        "checkpoint_id": "cp_123",
        "thread_id": "unknown",
        "subworkflow_checkpoint": False,
    }
```

## Integration Patterns

### Integration with API Layer

The checkpoint service is not directly exposed via REST API. The API layer interacts with checkpoints through the
execution engine, which internally uses the checkpoint service.

**Indirect API Usage via Execution Engine:**

```python
# From backend/api/checkpoints/routes.py
from fastapi import APIRouter, HTTPException
from backend.services.dependency_injection import get_execution_engine

router = APIRouter(prefix="/api/checkpoints", tags=["checkpoints"])

@router.post("/resume")
async def resume_from_checkpoint(request: ResumeExecutionRequest):
    """Resume execution from a checkpoint."""

    # API layer calls execution engine
    engine = get_execution_engine()

    # Engine internally uses checkpoint service to:
    # 1. Retrieve checkpoint metadata
    # 2. Determine if it's a subworkflow checkpoint
    # 3. Route to appropriate resume handler
    result = await engine.resume_from_checkpoint(
        graph_name=request.graph_name,
        thread_id=request.thread_id,
        checkpoint_id=request.checkpoint_id,
        new_input=request.new_input,
    )

    return {
        "status": "resumed",
        "thread_id": request.thread_id,
        "checkpoint_id": request.checkpoint_id,
        "result": result,
    }
```

### Integration with Other Services

#### Integration with Execution Service

The checkpoint service is primarily used by the execution service for workflow resumption.

```python
# From backend/services/execution/resume_handler.py
from backend.services.checkpoint import checkpoint_metadata_manager

class ResumeHandler:
    """Handles resuming workflow execution from checkpoints."""

    async def resume(
        self,
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        new_input: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resume execution from a checkpoint."""

        # Check if this is a subworkflow checkpoint
        checkpoint_metadata = checkpoint_metadata_manager.get_checkpoint_metadata(
            checkpoint_id
        )

        if checkpoint_metadata and checkpoint_metadata.get("subworkflow_checkpoint"):
            # Delegate to subworkflow resume handler
            return await self._handle_subworkflow_resume(
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                checkpoint_metadata=checkpoint_metadata,
                new_input=new_input,
            )

        # Regular workflow resume
        # ... resume execution
```

#### Integration with Database Service

```python
from backend.services.checkpoint import CheckpointMetadataRepository
from backend.services.database import SessionLocal
from backend.models import CheckpointMetadata

# Repository uses SessionLocal for database operations
class CheckpointMetadataRepository:

    @staticmethod
    def get_by_checkpoint_id(checkpoint_id: str):
        """Retrieve checkpoint using database service."""

        # Use database service's session management
        with SessionLocal() as db:
            checkpoint_meta = db.query(CheckpointMetadata).filter_by(
                checkpoint_id=checkpoint_id
            ).first()

            return checkpoint_meta
```

### Dependency Flow

```
┌────────────────────────┐
│    API Routes          │
│  /api/checkpoints/*    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Execution Engine      │
│  resume_from_checkpoint│
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  ResumeHandler         │
│  - Checks checkpoint   │
│  - Routes to handler   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ CheckpointMetadata     │
│ Manager (this service) │
│ - get_checkpoint_*     │
│ - store_checkpoint_*   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Database Service       │
│ checkpoint_metadata    │
└────────────────────────┘
```

**Services that depend on checkpoint:**

- `backend.services.execution` - Resume handler and execution engine
- `backend.api.checkpoints` - Checkpoint API endpoints (indirect)

**Services that checkpoint depends on:**

- `backend.services.database` - Database session management
- `backend.services.config` - Logging infrastructure
- `backend.models` - CheckpointMetadata ORM model

### Common Integration Patterns

#### Pattern 1: Storing Checkpoint on Workflow Pause

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

# When workflow pauses and creates checkpoint
async def handle_workflow_interrupt(
    checkpoint_id: str,
    thread_id: str,
    interrupt_value: Dict[str, Any],
):
    """Store checkpoint metadata when workflow is interrupted."""

    manager = get_checkpoint_metadata_manager()

    # Extract metadata from interrupt value
    metadata = {
        "subworkflow_checkpoint": interrupt_value.get("is_subworkflow", False),
        "subworkflow_name": interrupt_value.get("subworkflow_name"),
        "subworkflow_thread_id": interrupt_value.get("subworkflow_thread_id"),
        "checkpoint_node_exec_id": interrupt_value.get("node_exec_id"),
        "parent_execution_id": interrupt_value.get("parent_execution_id"),
        "parent_tool_call": interrupt_value.get("parent_tool_call"),
    }

    # Store metadata for later retrieval
    success = manager.store_checkpoint_metadata(
        checkpoint_id=checkpoint_id,
        thread_id=thread_id,
        metadata=metadata,
    )

    if not success:
        logger.warning(f"Failed to store checkpoint metadata: {checkpoint_id}")
```

#### Pattern 2: Retrieving Checkpoint on Resume

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

# When resuming from checkpoint
async def resume_workflow(checkpoint_id: str, thread_id: str):
    """Resume workflow using stored checkpoint metadata."""

    manager = get_checkpoint_metadata_manager()

    # Retrieve stored metadata
    metadata = manager.get_checkpoint_metadata(checkpoint_id)

    if metadata is None:
        # Checkpoint metadata not found, treat as regular checkpoint
        logger.warning(f"No metadata found for checkpoint: {checkpoint_id}")
        return await regular_resume(checkpoint_id, thread_id)

    # Check if subworkflow checkpoint
    if metadata.get("subworkflow_checkpoint"):
        # Resume subworkflow with parent context
        return await resume_subworkflow(
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
            subworkflow_name=metadata["subworkflow_name"],
            parent_execution_id=metadata["parent_execution_id"],
            parent_tool_call=metadata["parent_tool_call"],
        )
    else:
        # Regular workflow resume
        return await regular_resume(checkpoint_id, thread_id)
```

#### Pattern 3: Cleanup After Completion

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager, CheckpointStatusType

# After workflow completes
async def finalize_workflow_execution(checkpoint_id: str, thread_id: str):
    """Clean up checkpoint metadata after completion."""

    manager = get_checkpoint_metadata_manager()

    # Mark checkpoint as completed and clear from cache
    manager.clear_checkpoint_metadata(checkpoint_id)

    logger.info(f"Checkpoint {checkpoint_id} marked as completed")
```

## Usage Examples

### Example 1: Basic Usage - Store and Retrieve

Complete end-to-end example of storing and retrieving checkpoint metadata:

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

# Step 1: Get the manager instance
manager = get_checkpoint_metadata_manager()

# Step 2: Store checkpoint metadata when workflow pauses
checkpoint_id = "cp_1a2b3c4d5e6f"
thread_id = "thread_xyz789"

success = manager.store_checkpoint_metadata(
    checkpoint_id=checkpoint_id,
    thread_id=thread_id,
    metadata={
        "subworkflow_checkpoint": False,
        "checkpoint_node_exec_id": "node_exec_abc123",
        "parent_execution_id": None,
    },
)

if success:
    print(f"Checkpoint metadata stored: {checkpoint_id}")
else:
    print("Failed to store checkpoint metadata")

# Step 3: Retrieve metadata later (e.g., on resume)
metadata = manager.get_checkpoint_metadata(checkpoint_id)

if metadata:
    print(f"Retrieved checkpoint for thread: {metadata['thread_id']}")
    print(f"Is subworkflow: {metadata['subworkflow_checkpoint']}")
else:
    print("Checkpoint metadata not found")
```

### Example 2: Advanced Usage - Subworkflow Checkpoint

Complete example showing subworkflow checkpoint management:

```python
from backend.services.checkpoint import (
    get_checkpoint_metadata_manager,
    CheckpointStatusType,
)

# Get manager
manager = get_checkpoint_metadata_manager()

# Store subworkflow checkpoint with full context
checkpoint_id = "cp_subworkflow_123"
thread_id = "parent_thread_456"

success = manager.store_checkpoint_metadata(
    checkpoint_id=checkpoint_id,
    thread_id=thread_id,
    metadata={
        # Subworkflow identification
        "subworkflow_checkpoint": True,
        "subworkflow_name": "email-processor",
        "subworkflow_thread_id": "sub_thread_789",

        # Parent context
        "parent_execution_id": "exec_parent_101",
        "checkpoint_node_exec_id": "node_exec_delegate_202",

        # Tool call that triggered subworkflow
        "parent_tool_call": {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "send_email",
                "arguments": {
                    "to": "user@example.com",
                    "subject": "Workflow Update",
                },
            },
        },
    },
)

# Later, when resuming, check if it's a subworkflow
metadata = manager.get_checkpoint_metadata(checkpoint_id)

if metadata and metadata.get("subworkflow_checkpoint"):
    print(f"Subworkflow checkpoint detected")
    print(f"  Subworkflow: {metadata['subworkflow_name']}")
    print(f"  Subworkflow thread: {metadata['subworkflow_thread_id']}")
    print(f"  Parent execution: {metadata['parent_execution_id']}")
    print(f"  Parent tool call: {metadata['parent_tool_call']}")

    # Route to subworkflow resume handler
    # ... delegate to specialized handler

# After completion, clean up
manager.clear_checkpoint_metadata(checkpoint_id)
```

### Example 3: Complete Workflow - Resume Handler Integration

Show a realistic, complete workflow integrated with execution service:

```python
from typing import Any, Dict, Optional
from backend.services.checkpoint import (
    get_checkpoint_metadata_manager,
    CheckpointStatusType,
)
from backend.services.execution.history import ExecutionHistoryService

async def resume_from_checkpoint_workflow(
    graph_name: str,
    thread_id: str,
    checkpoint_id: str,
    new_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Complete workflow for resuming from checkpoint with metadata handling."""

    # Step 1: Get checkpoint metadata manager
    manager = get_checkpoint_metadata_manager()

    # Step 2: Retrieve checkpoint metadata
    checkpoint_metadata = manager.get_checkpoint_metadata(checkpoint_id)

    if checkpoint_metadata is None:
        # No metadata found - treat as regular checkpoint
        logger.warning(f"No metadata for checkpoint: {checkpoint_id}")
        checkpoint_metadata = {
            "subworkflow_checkpoint": False,
            "checkpoint_id": checkpoint_id,
            "thread_id": thread_id,
        }

    try:
        # Step 3: Check if this is a subworkflow checkpoint
        if checkpoint_metadata.get("subworkflow_checkpoint"):
            logger.info(f"Resuming subworkflow checkpoint: {checkpoint_id}")

            # Extract subworkflow details
            subworkflow_name = checkpoint_metadata["subworkflow_name"]
            subworkflow_thread_id = checkpoint_metadata["subworkflow_thread_id"]
            parent_execution_id = checkpoint_metadata["parent_execution_id"]
            parent_tool_call = checkpoint_metadata["parent_tool_call"]

            # Resume subworkflow with context
            result = await resume_subworkflow(
                subworkflow_name=subworkflow_name,
                subworkflow_thread_id=subworkflow_thread_id,
                parent_execution_id=parent_execution_id,
                parent_tool_call=parent_tool_call,
                checkpoint_id=checkpoint_id,
                new_input=new_input,
            )

        else:
            logger.info(f"Resuming regular checkpoint: {checkpoint_id}")

            # Regular workflow resume
            result = await resume_regular_workflow(
                graph_name=graph_name,
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                new_input=new_input,
            )

        # Step 4: Update checkpoint status on success
        if result.get("status") == "completed":
            manager.clear_checkpoint_metadata(checkpoint_id)
            logger.info(f"Checkpoint completed and cleared: {checkpoint_id}")
        elif result.get("status") == "paused":
            # Workflow paused again at new checkpoint
            new_checkpoint_id = result.get("checkpoint_id")
            if new_checkpoint_id and new_checkpoint_id != checkpoint_id:
                # Store new checkpoint metadata
                manager.store_checkpoint_metadata(
                    checkpoint_id=new_checkpoint_id,
                    thread_id=thread_id,
                    metadata=result.get("metadata", {}),
                )

        return result

    except Exception as e:
        logger.error(f"Error resuming checkpoint {checkpoint_id}: {e}")
        raise


async def resume_subworkflow(
    subworkflow_name: str,
    subworkflow_thread_id: str,
    parent_execution_id: str,
    parent_tool_call: Dict[str, Any],
    checkpoint_id: str,
    new_input: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Resume subworkflow with parent context."""
    # Implementation would use subworkflow resume handler
    # This is a placeholder for illustration
    logger.info(f"Resuming subworkflow: {subworkflow_name}")
    return {
        "status": "completed",
        "subworkflow": subworkflow_name,
        "result": {"message": "Subworkflow completed"},
    }


async def resume_regular_workflow(
    graph_name: str,
    thread_id: str,
    checkpoint_id: str,
    new_input: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Resume regular workflow."""
    # Implementation would use regular resume handler
    # This is a placeholder for illustration
    logger.info(f"Resuming regular workflow: {graph_name}")
    return {
        "status": "completed",
        "graph_name": graph_name,
        "result": {"message": "Workflow completed"},
    }
```

### Example 4: Testing Usage

Show how to use this service in tests with dependency injection:

```python
import pytest
from unittest.mock import Mock
from backend.services.checkpoint import (
    CheckpointMetadataManager,
    CheckpointMetadataRepository,
    CheckpointMetadataCache,
)

def test_checkpoint_metadata_manager_basic():
    """Test basic checkpoint metadata storage and retrieval."""

    # Create manager with default dependencies
    manager = CheckpointMetadataManager()

    # Store checkpoint metadata
    success = manager.store_checkpoint_metadata(
        checkpoint_id="test_cp_123",
        thread_id="test_thread_456",
        metadata={
            "subworkflow_checkpoint": False,
            "test_field": "test_value",
        },
    )

    assert success is True

    # Retrieve checkpoint metadata
    metadata = manager.get_checkpoint_metadata("test_cp_123")

    assert metadata is not None
    assert metadata["checkpoint_id"] == "test_cp_123"
    assert metadata["thread_id"] == "test_thread_456"
    assert metadata["subworkflow_checkpoint"] is False


def test_checkpoint_metadata_manager_with_mocks():
    """Test checkpoint manager with mocked dependencies."""

    # Create mock repository
    mock_repo = Mock(spec=CheckpointMetadataRepository)
    mock_cache = Mock(spec=CheckpointMetadataCache)

    # Setup mock behaviour
    mock_cache.get.return_value = None  # Cache miss
    mock_repo.get_by_checkpoint_id.return_value = None  # Not in database

    # Create manager with mocked dependencies
    manager = CheckpointMetadataManager(
        repository=mock_repo,
        cache=mock_cache,
    )

    # Test get operation
    result = manager.get_checkpoint_metadata("test_cp_123")

    # Verify interactions
    mock_cache.get.assert_called_once_with("test_cp_123")
    mock_repo.get_by_checkpoint_id.assert_called_once()
    assert result is None


@pytest.mark.integration
def test_checkpoint_metadata_full_workflow():
    """Integration test for complete checkpoint workflow."""

    manager = CheckpointMetadataManager()
    checkpoint_id = "integration_test_cp"
    thread_id = "integration_test_thread"

    # Store checkpoint
    success = manager.store_checkpoint_metadata(
        checkpoint_id=checkpoint_id,
        thread_id=thread_id,
        metadata={
            "subworkflow_checkpoint": True,
            "subworkflow_name": "test-subworkflow",
        },
    )
    assert success is True

    # Retrieve checkpoint
    metadata = manager.get_checkpoint_metadata(checkpoint_id)
    assert metadata is not None
    assert metadata["subworkflow_checkpoint"] is True

    # Get active checkpoints
    active = manager.get_active_checkpoints(thread_id=thread_id)
    assert len(active) >= 1
    assert any(cp["checkpoint_id"] == checkpoint_id for cp in active)

    # Clear checkpoint
    cleared = manager.clear_checkpoint_metadata(checkpoint_id)
    assert cleared is True

    # Verify cleared
    metadata_after = manager.get_checkpoint_metadata(checkpoint_id)
    assert metadata_after is None  # Cleared from cache and marked completed
```

## Performance Considerations

### Performance Characteristics

**CheckpointMetadataManager:**

- `store_checkpoint_metadata()` - O(1) cache write + O(1) database write = **O(1)**
- `get_checkpoint_metadata()` - O(1) cache lookup, O(1) database query on miss = **O(1) amortised**
- `update_checkpoint_status()` - O(1) database update = **O(1)**
- `clear_checkpoint_metadata()` - O(1) cache delete + O(1) database update = **O(1)**
- `get_active_checkpoints()` - O(n) where n = number of active checkpoints = **O(n)**

**CheckpointMetadataCache:**

- All operations (get, set, delete, size) - **O(1)** dictionary operations
- `clear()` - **O(1)** dictionary clear

**CheckpointMetadataRepository:**

- Database queries are indexed on `checkpoint_id` (unique index) and `thread_id` (index)
- Single record operations - **O(1)** with index
- `get_active_checkpoints()` - **O(n)** table scan with status filter

**Memory Usage:**

- Cache stores full metadata dictionaries in memory
- Memory usage = O(n * m) where n = cached checkpoints, m = average metadata size
- Typical metadata size: ~500 bytes to 2KB per checkpoint
- No automatic cache eviction - manual clearing required

**I/O Characteristics:**

- **I/O-bound** - Database operations dominate performance
- Cache reduces database reads significantly
- Write operations always hit database
- Network latency to database affects performance

### Optimisation Tips

#### Tip 1: Batch Checkpoint Queries

**Problem:**

```python
# Inefficient: Multiple individual queries
for checkpoint_id in checkpoint_ids:
    metadata = manager.get_checkpoint_metadata(checkpoint_id)
    process(metadata)
```

**Solution:**

```python
# Efficient: Single batch query
from backend.services.checkpoint import CheckpointMetadataRepository

repo = CheckpointMetadataRepository()

# Get all active checkpoints for thread at once
active_checkpoints = manager.get_active_checkpoints(thread_id=thread_id)

# Process all checkpoints
for checkpoint_metadata in active_checkpoints:
    process(checkpoint_metadata)
```

#### Tip 2: Cache Warming for High-Traffic Threads

**Problem:**

```python
# Cold cache on first access causes database hit
metadata = manager.get_checkpoint_metadata(checkpoint_id)  # Database query
```

**Solution:**

```python
# Warm cache on thread initialisation
async def initialise_thread(thread_id: str):
    """Warm cache with active checkpoints for thread."""

    manager = get_checkpoint_metadata_manager()

    # Load all active checkpoints for thread (warms cache)
    active_checkpoints = manager.get_active_checkpoints(thread_id=thread_id)

    logger.info(f"Warmed cache with {len(active_checkpoints)} checkpoints")
```

#### Tip 3: Periodic Cache Cleanup

**Problem:**

```python
# Cache grows indefinitely with completed checkpoints
# Memory usage increases over time
```

**Solution:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

async def periodic_cache_cleanup():
    """Periodically clear cache to prevent memory growth."""

    manager = get_checkpoint_metadata_manager()

    # Option 1: Clear entire cache (simplest)
    manager.cache.clear()
    logger.info("Checkpoint cache cleared")

    # Option 2: Selective cleanup (more sophisticated)
    # Get all active checkpoints from database
    active_checkpoints = manager.get_active_checkpoints()
    active_ids = {cp["checkpoint_id"] for cp in active_checkpoints}

    # Clear cache entries not in active set
    # (requires exposing cache._cache or adding method)
    # This is an advanced pattern - use with caution
```

#### Tip 4: Minimise Metadata Size

**Problem:**

```python
# Large metadata objects consume memory and increase database I/O
metadata = manager.store_checkpoint_metadata(
    checkpoint_id=cp_id,
    thread_id=thread_id,
    metadata={
        "subworkflow_checkpoint": True,
        "full_state_copy": entire_workflow_state,  # Large object
        "complete_history": all_execution_history,  # Large array
    },
)
```

**Solution:**

```python
# Store only essential metadata, reference other data by ID
metadata = manager.store_checkpoint_metadata(
    checkpoint_id=cp_id,
    thread_id=thread_id,
    metadata={
        "subworkflow_checkpoint": True,
        "subworkflow_name": "email-processor",
        "subworkflow_thread_id": sub_thread_id,
        "parent_execution_id": parent_exec_id,  # Reference, not full object
        "checkpoint_node_exec_id": node_exec_id,  # Reference
        "parent_tool_call": {  # Only essential tool call data
            "id": "call_123",
            "function": {"name": "send_email"},
        },
        # Do NOT store: full state, complete history, large objects
    },
)

# Retrieve large objects separately if needed
if execution_id:
    full_state = ExecutionHistoryService.get_graph_execution_dict(execution_id)
```

### Async/Await Support

The checkpoint service is **synchronous** and does not directly support async/await. However, it can be safely used in
async contexts as database operations are performed in blocking calls.

**Using in Async Code:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

async def async_resume_handler(checkpoint_id: str):
    """Async function using synchronous checkpoint service."""

    manager = get_checkpoint_metadata_manager()

    # Synchronous call in async function (blocks event loop)
    metadata = manager.get_checkpoint_metadata(checkpoint_id)

    if metadata:
        # Process metadata
        await process_checkpoint(metadata)
```

**Note:** Database operations block the event loop. For high-concurrency applications, consider:

1. Moving checkpoint queries to background tasks
2. Using async SQLAlchemy if needed in future
3. Minimising checkpoint queries in hot paths

### Connection Pooling

Database connection pooling is managed by `backend.services.database.SessionLocal`, not by the checkpoint service
directly.

**Database Session Management:**

```python
# From repository.py
from backend.services.database import SessionLocal

# Each operation uses a context-managed session
with SessionLocal() as db:
    checkpoint = db.query(CheckpointMetadata).filter_by(
        checkpoint_id=checkpoint_id
    ).first()
    # Session automatically closed after block
```

**Connection pool configuration** is handled at the database service level. See `backend.services.database`
documentation for connection pool tuning.

### Batch Operations

**Get Active Checkpoints in Batch:**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Efficient: Single query for all active checkpoints in thread
active_checkpoints = manager.get_active_checkpoints(thread_id="thread_123")

# Process in batch
for checkpoint in active_checkpoints:
    print(f"Active: {checkpoint['checkpoint_id']}")
```

**Note:** There is no built-in batch store/update operation. Each `store_checkpoint_metadata()` call is a separate
database transaction. For high-throughput scenarios, consider batching at the application level or extending the
repository with batch operations.

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.checkpoint import (
    CheckpointMetadataManager,
    CheckpointMetadataRepository,
    CheckpointMetadataCache,
    CheckpointStatusType,
)

@pytest.fixture
def cache():
    """Cache fixture."""
    return CheckpointMetadataCache()


@pytest.fixture
def repository():
    """Repository fixture."""
    return Mock(spec=CheckpointMetadataRepository)


@pytest.fixture
def manager(repository, cache):
    """Manager fixture with mocked repository."""
    return CheckpointMetadataManager(repository=repository, cache=cache)


def test_store_checkpoint_creates_new(manager, repository, cache):
    """Test storing new checkpoint."""

    # Mock repository responses
    repository.get_by_checkpoint_id.return_value = None  # Doesn't exist
    repository.create.return_value = Mock(checkpoint_id="cp_123")

    # Store checkpoint
    result = manager.store_checkpoint_metadata(
        checkpoint_id="cp_123",
        thread_id="thread_456",
        metadata={"subworkflow_checkpoint": False},
    )

    # Assertions
    assert result is True
    repository.create.assert_called_once()
    cache.set.assert_called_once_with("cp_123", {"subworkflow_checkpoint": False})


def test_get_checkpoint_cache_hit(manager, cache):
    """Test getting checkpoint from cache."""

    # Setup cache to return metadata
    cache.get.return_value = {
        "checkpoint_id": "cp_123",
        "thread_id": "thread_456",
        "subworkflow_checkpoint": True,
    }

    # Get checkpoint
    metadata = manager.get_checkpoint_metadata("cp_123")

    # Should return cached data without hitting repository
    assert metadata is not None
    assert metadata["checkpoint_id"] == "cp_123"
    cache.get.assert_called_once_with("cp_123")


def test_get_checkpoint_cache_miss_db_hit(manager, repository, cache):
    """Test getting checkpoint from database on cache miss."""

    # Setup mocks
    cache.get.return_value = None  # Cache miss

    mock_checkpoint = Mock()
    mock_checkpoint.checkpoint_id = "cp_123"
    mock_checkpoint.thread_id = "thread_456"
    mock_checkpoint.is_subworkflow = False
    mock_checkpoint.interrupt_data = {"test": "data"}

    repository.get_by_checkpoint_id.return_value = mock_checkpoint
    repository.to_metadata_dict.return_value = {
        "checkpoint_id": "cp_123",
        "thread_id": "thread_456",
        "subworkflow_checkpoint": False,
    }

    # Get checkpoint
    metadata = manager.get_checkpoint_metadata("cp_123")

    # Should query database and update cache
    assert metadata is not None
    repository.get_by_checkpoint_id.assert_called_once()
    cache.set.assert_called_once()
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch
import pytest

@patch('backend.services.checkpoint.repository.SessionLocal')
def test_repository_with_mocked_session(mock_session_local):
    """Test repository with mocked database session."""

    # Create mock session
    mock_session = Mock()
    mock_session_local.return_value.__enter__.return_value = mock_session

    # Setup mock query
    mock_query = Mock()
    mock_session.query.return_value = mock_query
    mock_query.filter_by.return_value = mock_query
    mock_query.first.return_value = None

    # Test repository operation
    from backend.services.checkpoint import CheckpointMetadataRepository

    result = CheckpointMetadataRepository.get_by_checkpoint_id("cp_123")

    # Verify session was used
    assert result is None
    mock_session.query.assert_called_once()


def test_manager_error_handling():
    """Test manager handles repository errors gracefully."""

    # Create mock repository that raises exception
    mock_repo = Mock(spec=CheckpointMetadataRepository)
    mock_repo.create.return_value = None  # Simulate database error

    manager = CheckpointMetadataManager(repository=mock_repo)

    # Store should return False on error
    result = manager.store_checkpoint_metadata(
        checkpoint_id="cp_123",
        thread_id="thread_456",
        metadata={},
    )

    assert result is False
```

### Integration Testing

```python
import pytest
from backend.services.checkpoint import (
    get_checkpoint_metadata_manager,
    CheckpointStatusType,
)
from backend.services.database import SessionLocal
from backend.models import CheckpointMetadata


@pytest.mark.integration
def test_checkpoint_full_lifecycle():
    """Integration test for complete checkpoint lifecycle."""

    manager = get_checkpoint_metadata_manager()

    checkpoint_id = "integration_cp_test_123"
    thread_id = "integration_thread_456"

    try:
        # 1. Store checkpoint
        success = manager.store_checkpoint_metadata(
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
            metadata={
                "subworkflow_checkpoint": True,
                "subworkflow_name": "test-workflow",
                "subworkflow_thread_id": "sub_thread_789",
            },
        )
        assert success is True

        # 2. Retrieve from database (clear cache first)
        manager.cache.delete(checkpoint_id)
        metadata = manager.get_checkpoint_metadata(checkpoint_id)
        assert metadata is not None
        assert metadata["checkpoint_id"] == checkpoint_id
        assert metadata["subworkflow_checkpoint"] is True

        # 3. Update status
        success = manager.update_checkpoint_status(
            checkpoint_id,
            CheckpointStatusType.RESUMED,
        )
        assert success is True

        # 4. Verify in database
        with SessionLocal() as db:
            cp = db.query(CheckpointMetadata).filter_by(
                checkpoint_id=checkpoint_id
            ).first()
            assert cp.status == CheckpointStatusType.RESUMED

        # 5. Clear checkpoint
        cleared = manager.clear_checkpoint_metadata(checkpoint_id)
        assert cleared is True

        # 6. Verify completed status
        with SessionLocal() as db:
            cp = db.query(CheckpointMetadata).filter_by(
                checkpoint_id=checkpoint_id
            ).first()
            assert cp.status == CheckpointStatusType.COMPLETED

    finally:
        # Cleanup
        with SessionLocal() as db:
            db.query(CheckpointMetadata).filter_by(
                checkpoint_id=checkpoint_id
            ).delete()
            db.commit()


@pytest.mark.integration
def test_get_active_checkpoints_filter():
    """Integration test for filtering active checkpoints."""

    manager = get_checkpoint_metadata_manager()

    test_thread = "test_thread_active_filter"
    checkpoint_ids = [
        "cp_active_1",
        "cp_active_2",
        "cp_active_3",
    ]

    try:
        # Create multiple active checkpoints
        for cp_id in checkpoint_ids:
            manager.store_checkpoint_metadata(
                checkpoint_id=cp_id,
                thread_id=test_thread,
                metadata={"test": True},
            )

        # Get active checkpoints for thread
        active = manager.get_active_checkpoints(thread_id=test_thread)

        # Verify all created checkpoints are returned
        assert len(active) >= 3
        active_ids = {cp["checkpoint_id"] for cp in active}
        for cp_id in checkpoint_ids:
            assert cp_id in active_ids

    finally:
        # Cleanup
        with SessionLocal() as db:
            for cp_id in checkpoint_ids:
                db.query(CheckpointMetadata).filter_by(
                    checkpoint_id=cp_id
                ).delete()
            db.commit()
```

## Best Practices

### Do's

✅ **Use the factory function for accessing the service**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

# Good: Use factory function
manager = get_checkpoint_metadata_manager()
metadata = manager.get_checkpoint_metadata(checkpoint_id)
```

✅ **Check return values for None/False**

```python
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# Good: Check for None
metadata = manager.get_checkpoint_metadata(checkpoint_id)
if metadata is None:
    # Handle not found case
    logger.warning(f"Checkpoint not found: {checkpoint_id}")
    # Use fallback
    metadata = {"subworkflow_checkpoint": False}
```

✅ **Store minimal metadata**

```python
# Good: Store only essential fields
manager.store_checkpoint_metadata(
    checkpoint_id=cp_id,
    thread_id=thread_id,
    metadata={
        "subworkflow_checkpoint": True,
        "subworkflow_name": "processor",
        "subworkflow_thread_id": sub_thread_id,
        "parent_execution_id": parent_id,  # Reference by ID
        "checkpoint_node_exec_id": node_id,  # Reference by ID
    },
)
```

✅ **Clear completed checkpoints**

```python
# Good: Clean up after completion
from backend.services.checkpoint import get_checkpoint_metadata_manager

manager = get_checkpoint_metadata_manager()

# After workflow completes
manager.clear_checkpoint_metadata(checkpoint_id)
```

✅ **Use CheckpointStatusType constants**

```python
from backend.services.checkpoint import CheckpointStatusType

# Good: Use constants
manager.update_checkpoint_status(checkpoint_id, CheckpointStatusType.COMPLETED)

# Bad: Magic strings
# manager.update_checkpoint_status(checkpoint_id, "completed")
```

### Don'ts

❌ **Don't store large objects in metadata**

```python
# Bad: Storing entire workflow state
manager.store_checkpoint_metadata(
    checkpoint_id=cp_id,
    thread_id=thread_id,
    metadata={
        "full_workflow_state": entire_state_dict,  # Too large!
        "complete_execution_history": all_history,  # Too large!
    },
)

# Good: Store references
manager.store_checkpoint_metadata(
    checkpoint_id=cp_id,
    thread_id=thread_id,
    metadata={
        "execution_id": exec_id,  # Reference to retrieve state separately
        "checkpoint_node_exec_id": node_id,
    },
)
```

❌ **Don't ignore error return values**

```python
# Bad: Ignoring return value
manager.store_checkpoint_metadata(cp_id, thread_id, metadata)
# What if it failed?

# Good: Check return value
success = manager.store_checkpoint_metadata(cp_id, thread_id, metadata)
if not success:
    logger.error(f"Failed to store checkpoint: {cp_id}")
    # Handle error appropriately
```

❌ **Don't bypass the cache layer**

```python
from backend.services.checkpoint import CheckpointMetadataRepository

# Bad: Using repository directly
repo = CheckpointMetadataRepository()
checkpoint = repo.get_by_checkpoint_id(cp_id)  # Bypasses cache!

# Good: Use manager which handles caching
from backend.services.checkpoint import get_checkpoint_metadata_manager
manager = get_checkpoint_metadata_manager()
metadata = manager.get_checkpoint_metadata(cp_id)  # Uses cache
```

❌ **Don't forget to handle subworkflow checkpoints**

```python
# Bad: Assuming all checkpoints are regular
metadata = manager.get_checkpoint_metadata(checkpoint_id)
result = resume_regular_workflow(checkpoint_id)  # Breaks on subworkflow!

# Good: Check checkpoint type
metadata = manager.get_checkpoint_metadata(checkpoint_id)
if metadata and metadata.get("subworkflow_checkpoint"):
    result = resume_subworkflow(checkpoint_id, metadata)
else:
    result = resume_regular_workflow(checkpoint_id)
```

❌ **Don't cache checkpoint data in application code**

```python
# Bad: Maintaining separate cache
checkpoint_cache = {}
checkpoint_cache[cp_id] = metadata  # Duplicate caching!

# Good: Trust the service's cache
manager = get_checkpoint_metadata_manager()
metadata = manager.get_checkpoint_metadata(cp_id)  # Already cached
```

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Workflow execution engine that uses checkpoint service for resume operations
- [Database Service](./database.md) - Database session management and ORM configuration used by checkpoint repository

### Related API Modules

- [Checkpoint API](../agents-guide/api/checkpoints.md) - REST API endpoints for checkpoint operations (indirect usage via execution
  engine)

### Architecture Documentation

- [Workflow Execution Architecture](../architecture/execution.md) - Overall workflow execution architecture including
  checkpoints
- [Database Schema](../architecture/database.md) - Database schema including checkpoint_metadata table

## Summary

The checkpoint service provides robust, performant metadata management for LangGraph checkpoints, solving the critical
limitation where LangGraph's native storage doesn't preserve custom interrupt metadata. By combining in-memory caching
with persistent database storage, the service ensures fast access while maintaining data consistency and durability.

The service implements a clean layered architecture following the Repository pattern, separating concerns between
business logic (`CheckpointMetadataManager`), data access (`CheckpointMetadataRepository`), and caching (
`CheckpointMetadataCache`). This design promotes testability, maintainability, and flexibility while providing a simple,
intuitive API for checkpoint metadata operations.

**Key Features:**

- Cache-first retrieval strategy for optimal performance
- Persistent database storage for durability and recovery
- Support for subworkflow checkpoint context preservation
- Lifecycle status tracking (active, resumed, completed)
- Clean separation of concerns with Repository pattern
- Comprehensive error handling with logging
- Thread-safe singleton access pattern

**Primary Use Cases:**

- Storing workflow pause/interrupt metadata for later resumption
- Managing subworkflow execution context and parent-child relationships
- Tracking email inbox checkpoints for asynchronous user responses
- Supporting checkpoint-based workflow debugging and auditing
- Enabling complex workflow delegation patterns with context preservation

**When to Use This Service:**

- When implementing workflow checkpoints that need to preserve custom metadata
- When building subworkflow delegation with parent context tracking
- When implementing email-based workflow interactions with inbox checkpoints
- When tracking checkpoint lifecycle for monitoring and debugging
- When optimising checkpoint metadata access with caching
