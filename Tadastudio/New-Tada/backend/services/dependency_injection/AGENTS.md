# Dependency Injection Service

## Overview

The Dependency Injection service provides centralised management of shared application dependencies in AgenticStudio,
specifically managing the lifecycle of `GraphManager` and `ExecutionEngine` instances. This module implements a
thread-safe singleton container pattern with FastAPI-native dependency injection support, enabling both direct access
for non-FastAPI code and automatic dependency injection in route handlers.

**Location:** [backend/services/dependency_injection/](../../backend/services/dependency_injection/)

**Primary Responsibilities:**

- Thread-safe initialisation of shared application dependencies
- Singleton lifecycle management for GraphManager and ExecutionEngine
- FastAPI dependency provider integration
- Type-safe access via Protocol definitions
- Clear error handling for uninitialised dependencies

**Key Use Cases:**

- Application startup dependency initialisation
- FastAPI route handler dependency injection
- Direct dependency access in non-FastAPI code (e.g., background tasks, utility scripts)
- Testing with mockable Protocol types

## Architecture

### Module Structure

```
backend/services/dependency_injection/
├── __init__.py           # Public API and exports (109 lines)
├── container.py          # Thread-safe singleton container (190 lines)
├── providers.py          # FastAPI dependency providers (115 lines)
├── types.py              # Protocol definitions for type safety (127 lines)
└── exceptions.py         # Custom exception classes (45 lines)
```

**File Purposes:**

- **`__init__.py`** - Public API surface with initialisation functions and convenience exports
- **`container.py`** - `DependencyContainer` singleton managing dependency lifecycle with thread-safe initialization
- **`providers.py`** - FastAPI dependency provider functions and type aliases for route injection
- **`types.py`** - `GraphManagerProtocol` and `ExecutionEngineProtocol` for type safety and testing
- **`exceptions.py`** - `DependencyError`, `DependencyNotInitializedError`, `InitializationError` exception hierarchy

### Design Patterns

#### Singleton Pattern

The `DependencyContainer` uses thread-safe singleton pattern with double-checked locking:

```python
class DependencyContainer:
    _instance: Optional["DependencyContainer"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check
                    cls._instance = super().__new__(cls)
        return cls._instance
```

#### Protocol Pattern (Structural Typing)

Uses Protocol for dependency interfaces, enabling type safety without coupling:

```python
class GraphManagerProtocol(Protocol):
    """Interface definition for GraphManager."""
    active_graphs: Dict[str, Any]

    def load_graph(self, graph_name: str, username: str = "default") -> Any:
        ...
```

#### FastAPI Dependency Injection

Provides annotated type aliases for seamless FastAPI integration:

```python
# Type alias with automatic dependency injection
GraphManager = Annotated[GraphManagerProtocol, Depends(get_graph_manager)]

# Usage in route handlers
@router.get("/graphs")
async def list_graphs(graph_mgr: GraphManager):
    return graph_mgr.list_graphs()
```

#### Dependency Flow

```
Application Startup (app.py lifespan)
    ↓
initialize_dependencies()
    ↓
DependencyContainer.initialize()
    ↓
├── GraphManager instance created
└── ExecutionEngine initialised via get_executor()
    ↓
Singleton instances stored in container
    ↓
┌─────────────────────┬────────────────────────┐
│ FastAPI Routes      │ Direct Access          │
│ (via Depends)       │ (get_graph_manager())  │
└─────────────────────┴────────────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.graph.GraphManager` - Workflow graph management
- `backend.services.execution.get_executor` - LangGraph execution engine
- `backend.services.execution.initialize_executor` - Execution engine setup
- `backend.services.config.get_logger` - Logging configuration

**External Dependencies:**

- `threading` - Thread synchronisation primitives
- `typing` - Type hints and Protocol support
- `fastapi` - Depends, HTTPException

**Database Dependencies:**
None directly (dependencies manage their own database connections)

**Environment Variables:**
None (configuration managed by injected dependencies)

## Public API

### Exported Functions

- `initialize_dependencies()` - Initialise all application dependencies (call once at startup)
- `is_initialized()` - Check if dependencies are initialised
- `get_graph_manager()` - Get GraphManager instance (direct access or FastAPI dependency)
- `get_execution_engine()` - Get ExecutionEngine instance (direct access or FastAPI dependency)

### Exported Classes/Type Aliases

- `GraphManager` - FastAPI type alias for GraphManager dependency injection
- `ExecutionEngine` - FastAPI type alias for ExecutionEngine dependency injection
- `GraphManagerProtocol` - Protocol defining GraphManager interface
- `ExecutionEngineProtocol` - Protocol defining ExecutionEngine interface

### Exceptions

```
Exception
└── DependencyError (base exception)
    ├── DependencyNotInitializedError
    └── InitializationError
```

## Core Classes

### `DependencyContainer`

Thread-safe singleton container managing the lifecycle of shared application dependencies.

**Purpose:** Provides centralised, thread-safe initialisation and access to shared dependencies with lazy initialization
support.

**Responsibilities:**

- Ensure single instance across application (singleton pattern)
- Thread-safe initialisation using locks
- Lazy initialisation of GraphManager and ExecutionEngine
- Property-based access with validation
- Clear error messages for uninitialised access

**Initialisation:**

```python
def __init__(self) -> None:
    """
    Initialise the container.

    Note: Only runs once due to _initialized flag and singleton pattern.
    """
```

The container is auto-instantiated as a module-level singleton:

```python
# Internal usage (not typically called directly)
from backend.services.dependency_injection.container import _container
```

**Key Methods:**

#### `initialize()`

```python
def initialize(self) -> None:
    """
    Initialise all application dependencies.

    Thread-safe with double-checked locking. Multiple calls are safe;
    subsequent calls are no-ops.

    Raises:
        InitializationError: If initialisation fails for any reason
    """
```

**Behaviour:**

- Creates GraphManager instance
- Calls `initialize_executor(graph_manager)` to set up execution engine
- Retrieves ExecutionEngine via `get_executor()`
- Stores both in thread-safe container
- Logs all steps for debugging
- Cleans up partial initialisation on failure

**Thread Safety:**
Uses `_init_lock` to prevent race conditions. Safe to call from multiple threads.

**Example:**

```python
from backend.services.dependency_injection.container import _container

try:
    _container.initialize()
    print("Dependencies initialized successfully")
except InitializationError as e:
    print(f"Initialization failed: {e}")
```

**Use Cases:**

- Called once during application startup in FastAPI lifespan
- Can be called again safely (idempotent)
- Testing scenarios where reset/reinit is needed

#### `graph_manager` (Property)

```python
@property
def graph_manager(self) -> GraphManagerProtocol:
    """
    Get the GraphManager instance.

    Returns:
        GraphManagerProtocol: The initialised GraphManager

    Raises:
        DependencyNotInitializedError: If initialize() hasn't been called
    """
```

**Parameters:** None (property)

**Returns:**

- `GraphManagerProtocol` - Initialised GraphManager instance

**Raises:**

- `DependencyNotInitializedError` - When accessed before `initialize()` called

**Example:**

```python
from backend.services.dependency_injection.container import _container

_container.initialize()
graph_mgr = _container.graph_manager
graphs = graph_mgr.list_graphs(username="alice")
```

**Behaviour:**

- Returns cached instance if initialised
- Raises clear error with dependency name if not initialised
- Logs error attempts for debugging

**Use Cases:**

- Direct access in non-FastAPI code
- Service layer integration
- Background tasks and workers

#### `execution_engine` (Property)

```python
@property
def execution_engine(self) -> ExecutionEngineProtocol:
    """
    Get the ExecutionEngine instance.

    Returns:
        ExecutionEngineProtocol: The initialised ExecutionEngine

    Raises:
        DependencyNotInitializedError: If initialize() hasn't been called
    """
```

**Parameters:** None (property)

**Returns:**

- `ExecutionEngineProtocol` - Initialised ExecutionEngine instance

**Raises:**

- `DependencyNotInitializedError` - When accessed before `initialize()` called

**Example:**

```python
from backend.services.dependency_injection.container import _container

_container.initialize()
engine = _container.execution_engine
await engine.execute_graph(graph_name="workflow-1", inputs={"message": "hello"})
```

**Behaviour:**

- Returns cached instance if initialised
- Raises clear error with dependency name if not initialised
- Logs error attempts for debugging

**Use Cases:**

- Direct access in non-FastAPI code
- Background job execution
- CLI tools and scripts

#### `is_initialized()`

```python
def is_initialized(self) -> bool:
    """
    Check if dependencies are initialised.

    Returns:
        bool: True if both GraphManager and ExecutionEngine are initialised
    """
```

**Parameters:** None

**Returns:**

- `bool` - True if both dependencies are ready, False otherwise

**Example:**

```python
from backend.services.dependency_injection.container import _container

if not _container.is_initialized():
    raise RuntimeError("Application not ready - dependencies not initialized")
```

**Use Cases:**

- Health checks
- Startup validation
- Testing setup verification

#### `reset()`

```python
def reset(self) -> None:
    """
    Reset the container (primarily for testing).

    Warning: This should only be used in test environments.
    """
```

**Parameters:** None

**Returns:** None

**Example:**

```python
import pytest
from backend.services.dependency_injection.container import _container

@pytest.fixture(autouse=True)
def reset_dependencies():
    """Reset dependencies after each test."""
    yield
    _container.reset()
```

**Behaviour:**

- Clears all cached dependencies
- Logs warning (should only happen in tests)
- Thread-safe via `_init_lock`

**Use Cases:**

- Test isolation
- Integration test setup/teardown
- Development environment resets

**Class Attributes:**

- `_instance: Optional[DependencyContainer]` - Singleton instance
- `_lock: threading.Lock` - Class-level lock for singleton creation
- `_init_lock: threading.Lock` - Instance-level lock for initialisation
- `_graph_manager: Optional[GraphManagerProtocol]` - Cached GraphManager
- `_execution_engine: Optional[ExecutionEngineProtocol]` - Cached ExecutionEngine

## Functions

### `initialize_dependencies()`

Initialise all application dependencies (public API wrapper).

**Signature:**

```python
def initialize_dependencies() -> None:
    """
    Initialise all application dependencies.

    This function must be called once during application startup,
    preferably in the FastAPI lifespan context.

    Raises:
        InitializationError: If initialisation fails
    """
```

**Parameters:** None

**Returns:** None

**Raises:**

- `InitializationError` - If dependency initialisation fails for any reason

**Example:**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.services.dependency_injection import initialize_dependencies

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initialize_dependencies()
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)
```

**Use Cases:**

- Application startup in FastAPI lifespan
- Standalone script initialisation
- Testing setup

### `is_initialized()`

Check if dependencies are initialised (public API wrapper).

**Signature:**

```python
def is_initialized() -> bool:
    """
    Check if dependencies are initialised.

    Returns:
        bool: True if both GraphManager and ExecutionEngine are initialised
    """
```

**Parameters:** None

**Returns:**

- `bool` - True if dependencies are ready, False otherwise

**Example:**

```python
from backend.services.dependency_injection import is_initialized

if not is_initialized():
    print("Warning: Dependencies not initialized yet")
else:
    print("System ready")
```

**Use Cases:**

- Health check endpoints
- Graceful degradation logic
- Startup sequence validation

### `get_graph_manager()`

Get GraphManager instance for direct access or FastAPI dependency injection.

**Signature:**

```python
def get_graph_manager() -> GraphManagerProtocol:
    """
    Provide FastAPI dependency for GraphManager.

    Returns:
        GraphManagerProtocol: The initialised GraphManager instance

    Raises:
        HTTPException: 503 Service Unavailable if not initialised (in FastAPI context)
        DependencyNotInitializedError: If not initialised (in direct call context)
    """
```

**Parameters:** None

**Returns:**

- `GraphManagerProtocol` - The GraphManager instance

**Raises:**

- `HTTPException` (503) - When used as FastAPI dependency and not initialised
- `DependencyNotInitializedError` - When called directly and not initialised

**Example (Direct Access):**

```python
from backend.services.dependency_injection import get_graph_manager

# In non-FastAPI code (background task, utility script, etc.)
graph_mgr = get_graph_manager()
graphs = graph_mgr.list_graphs(username="bob")
```

**Example (FastAPI Dependency):**

```python
from fastapi import APIRouter, Depends
from backend.services.dependency_injection import get_graph_manager, GraphManagerProtocol

router = APIRouter()

@router.get("/graphs")
async def list_graphs(
    graph_mgr: GraphManagerProtocol = Depends(get_graph_manager)
):
    graphs = graph_mgr.list_graphs()
    return {"success": True, "graphs": graphs}
```

**Example (Convenience Type Alias):**

```python
from fastapi import APIRouter
from backend.services.dependency_injection import GraphManager

router = APIRouter()

# GraphManager is Annotated[GraphManagerProtocol, Depends(get_graph_manager)]
@router.get("/graphs")
async def list_graphs(graph_mgr: GraphManager):
    graphs = graph_mgr.list_graphs()
    return {"success": True, "graphs": graphs}
```

**Behaviour:**

- Returns cached instance from container
- In FastAPI context: converts `DependencyNotInitializedError` to HTTP 503
- Logs successful provision or errors
- Thread-safe access

**Use Cases:**

- FastAPI route handler dependency injection
- Service layer integration
- Background tasks and workers
- CLI tools

### `get_execution_engine()`

Get ExecutionEngine instance for direct access or FastAPI dependency injection.

**Signature:**

```python
def get_execution_engine() -> ExecutionEngineProtocol:
    """
    Provide FastAPI dependency for ExecutionEngine.

    Returns:
        ExecutionEngineProtocol: The initialised ExecutionEngine instance

    Raises:
        HTTPException: 503 Service Unavailable if not initialised (in FastAPI context)
        DependencyNotInitializedError: If not initialised (in direct call context)
    """
```

**Parameters:** None

**Returns:**

- `ExecutionEngineProtocol` - The ExecutionEngine instance

**Raises:**

- `HTTPException` (503) - When used as FastAPI dependency and not initialised
- `DependencyNotInitializedError` - When called directly and not initialised

**Example (Direct Access):**

```python
from backend.services.dependency_injection import get_execution_engine

# In background task
engine = get_execution_engine()
await engine.execute_graph(
    graph_name="data-pipeline",
    inputs={"source": "database"},
    thread_id="bg-task-123"
)
```

**Example (FastAPI Dependency):**

```python
from fastapi import APIRouter
from backend.services.dependency_injection import ExecutionEngine

router = APIRouter()

@router.post("/execute/{graph_name}")
async def execute_workflow(
    graph_name: str,
    engine: ExecutionEngine
):
    result = await engine.execute_graph(
        graph_name=graph_name,
        inputs={"message": "start"}
    )
    return {"success": True, "result": result}
```

**Behaviour:**

- Returns cached instance from container
- In FastAPI context: converts `DependencyNotInitializedError` to HTTP 503
- Logs successful provision or errors
- Thread-safe access

**Use Cases:**

- Workflow execution in API routes
- Background job processing
- Scheduled task execution
- CLI workflow runner

## Configuration

### Initialisation Patterns

#### Basic Initialisation (Application Startup)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.services.dependency_injection import initialize_dependencies

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    try:
        initialize_dependencies()
        print("Dependencies initialized successfully")
    except Exception as e:
        print(f"Failed to initialize dependencies: {e}")
        raise

    yield

    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)
```

#### Direct Access (Non-FastAPI Code)

```python
from backend.services.dependency_injection import (
    get_graph_manager,
    get_execution_engine,
    is_initialized
)

def process_workflow(graph_name: str):
    """Process workflow in background task."""

    # Check readiness
    if not is_initialized():
        raise RuntimeError("Dependencies not initialized")

    # Access dependencies
    graph_mgr = get_graph_manager()
    engine = get_execution_engine()

    # Use dependencies
    graph = graph_mgr.load_graph(graph_name, username="system")
    result = await engine.execute_graph(
        graph_name=graph_name,
        inputs={"source": "scheduler"}
    )

    return result
```

#### FastAPI Dependency Injection

```python
from fastapi import APIRouter, HTTPException
from backend.services.dependency_injection import GraphManager, ExecutionEngine

router = APIRouter()

@router.post("/workflows/{graph_name}/execute")
async def execute_workflow(
    graph_name: str,
    graph_mgr: GraphManager,
    engine: ExecutionEngine
):
    """Execute workflow with dependency injection."""

    # graph_mgr and engine are automatically injected
    try:
        # Load graph
        graph = graph_mgr.load_graph(graph_name)

        # Execute
        result = await engine.execute_graph(
            graph_name=graph_name,
            inputs={"trigger": "api"}
        )

        return {"success": True, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Testing Initialisation

```python
import pytest
from unittest.mock import Mock
from backend.services.dependency_injection.container import _container

@pytest.fixture
def mock_dependencies():
    """Provide mock dependencies for testing."""

    # Reset container
    _container.reset()

    # Create mocks
    mock_graph_mgr = Mock()
    mock_engine = Mock()

    # Inject mocks directly (bypassing normal init)
    _container._graph_manager = mock_graph_mgr
    _container._execution_engine = mock_engine

    yield {
        "graph_manager": mock_graph_mgr,
        "engine": mock_engine
    }

    # Cleanup
    _container.reset()

def test_with_mocks(mock_dependencies):
    """Test using mocked dependencies."""
    from backend.services.dependency_injection import get_graph_manager

    graph_mgr = get_graph_manager()
    graph_mgr.list_graphs.return_value = ["graph-1", "graph-2"]

    result = graph_mgr.list_graphs()
    assert result == ["graph-1", "graph-2"]
```

### Environment Variables

None. The dependency injection module itself does not use environment variables. However, the injected dependencies (
GraphManager, ExecutionEngine) may have their own environment configuration.

## Error Handling

### Exception Hierarchy

```
Exception
└── DependencyError (base exception for all dependency-related errors)
    ├── DependencyNotInitializedError (accessing uninitialised dependency)
    └── InitializationError (dependency initialisation failure)
```

### Exception Details

#### `DependencyError`

Base exception for all dependency-related errors.

**Inherits from:** `Exception`

**When raised:**

- Base class, typically not raised directly
- Catch this to handle all dependency-related errors

**Example:**

```python
from backend.services.dependency_injection import (
    get_graph_manager,
    DependencyError
)

try:
    graph_mgr = get_graph_manager()
except DependencyError as e:
    logger.error(f"Dependency error: {e}")
    # Handle all dependency-related errors
```

#### `DependencyNotInitializedError`

Raised when accessing a dependency that hasn't been initialised.

**Inherits from:** `DependencyError`

**Attributes:**

- `dependency_name: str` - Name of the dependency (e.g., "GraphManager", "ExecutionEngine")

**When raised:**

- Accessing `container.graph_manager` before calling `initialize()`
- Accessing `container.execution_engine` before calling `initialize()`
- Calling `get_graph_manager()` before `initialize_dependencies()`
- Calling `get_execution_engine()` before `initialize_dependencies()`

**Example:**

```python
from backend.services.dependency_injection import (
    get_graph_manager,
    DependencyNotInitializedError
)

try:
    # Forget to call initialize_dependencies()
    graph_mgr = get_graph_manager()
except DependencyNotInitializedError as e:
    print(f"Dependency not initialized: {e.dependency_name}")
    print(f"Error message: {e}")
    # Output: GraphManager not initialized. Call initialize_dependencies() first.
```

#### `InitializationError`

Raised when dependency initialisation fails.

**Inherits from:** `DependencyError`

**When raised:**

- GraphManager instantiation fails
- ExecutionEngine initialisation fails
- Any exception during `initialize()` or `initialize_dependencies()`

**Example:**

```python
from backend.services.dependency_injection import (
    initialize_dependencies,
    InitializationError
)

try:
    initialize_dependencies()
except InitializationError as e:
    logger.critical(f"Application startup failed: {e}")
    # Check underlying cause
    if e.__cause__:
        logger.critical(f"Root cause: {e.__cause__}")
    sys.exit(1)
```

### Error Handling Patterns

#### Pattern 1: Application Startup

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.services.dependency_injection import (
    initialize_dependencies,
    InitializationError
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper error handling."""

    # Startup
    try:
        initialize_dependencies()
        logger.info("Application dependencies initialized")
    except InitializationError as e:
        logger.critical(f"Failed to initialize dependencies: {e}")
        logger.critical("Application cannot start")
        raise

    yield

    # Shutdown
    logger.info("Application shutting down")

app = FastAPI(lifespan=lifespan)
```

#### Pattern 2: Direct Access with Fallback

```python
from backend.services.dependency_injection import (
    get_graph_manager,
    DependencyNotInitializedError,
    is_initialized
)

def get_graph_list_safe():
    """Get graph list with graceful degradation."""

    # Check first
    if not is_initialized():
        logger.warning("Dependencies not initialized, returning empty list")
        return []

    try:
        graph_mgr = get_graph_manager()
        return graph_mgr.list_graphs()
    except DependencyNotInitializedError:
        logger.error("Race condition: dependencies became uninitialized")
        return []
    except Exception as e:
        logger.error(f"Error listing graphs: {e}")
        return []
```

#### Pattern 3: FastAPI Route Error Handling

```python
from fastapi import APIRouter, HTTPException
from backend.services.dependency_injection import GraphManager, ExecutionEngine

router = APIRouter()

@router.post("/execute/{graph_name}")
async def execute_workflow(
    graph_name: str,
    graph_mgr: GraphManager,
    engine: ExecutionEngine
):
    """
    Execute workflow.

    Dependencies are automatically injected by FastAPI.
    If not initialized, FastAPI returns 503 automatically.
    """
    try:
        graph = graph_mgr.load_graph(graph_name)
        result = await engine.execute_graph(graph_name=graph_name)
        return {"success": True, "result": result}
    except Exception as e:
        # Handle business logic errors
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Pattern 4: Testing Error Cases

```python
import pytest
from backend.services.dependency_injection import (
    get_graph_manager,
    DependencyNotInitializedError
)
from backend.services.dependency_injection.container import _container

def test_access_before_init():
    """Test error when accessing uninitialized dependency."""

    # Ensure clean state
    _container.reset()

    # Should raise error
    with pytest.raises(DependencyNotInitializedError) as exc_info:
        get_graph_manager()

    # Check error details
    assert exc_info.value.dependency_name == "GraphManager"
    assert "initialize_dependencies()" in str(exc_info.value)
```

## Integration Patterns

### Integration with API Layer

The dependency injection module is primarily used in FastAPI route handlers for automatic dependency injection.

#### Example: Graph API Integration

```python
# backend/api/graph/routes.py
from fastapi import APIRouter
from backend.services.dependency_injection import GraphManager

router = APIRouter(prefix="/api/graph")

@router.get("/list")
async def list_graphs(graph_mgr: GraphManager):
    """
    List all graphs.

    GraphManager is automatically injected via dependency injection.
    """
    graphs = graph_mgr.list_graphs()
    return {"success": True, "graphs": graphs}

@router.get("/health")
async def health_check(graph_mgr: GraphManager, engine: ExecutionEngine):
    """Health check with metrics from dependencies."""
    return {
        "status": "healthy",
        "active_graphs": len(graph_mgr.active_graphs),
        "active_executions": len(engine.active_executions)
    }
```

#### Example: Handler Function Integration

```python
# backend/api/graph/handlers/graph_crud.py
from typing import Dict, Any
from backend.services.dependency_injection import get_graph_manager

async def handle_list_graphs(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    List graphs for a user.

    Uses direct access pattern for handler functions.
    """
    user_id = current_user["id"]

    # Direct access (not FastAPI route, so can't use Depends)
    graph_mgr = get_graph_manager()
    graphs = graph_mgr.list_graphs(username=user_id)

    return {"success": True, "graphs": graphs}
```

### Integration with Other Services

The dependency injection module doesn't depend on other services but provides access to services that do.

#### Example: Execution Service Integration

```python
# Backend workflow execution using injected dependencies
from backend.services.dependency_injection import (
    get_graph_manager,
    get_execution_engine
)

async def execute_scheduled_workflow(graph_name: str, schedule_id: str):
    """Execute workflow from scheduler."""

    # Get dependencies
    graph_mgr = get_graph_manager()
    engine = get_execution_engine()

    # Load graph
    graph = graph_mgr.load_graph(graph_name, username="system")

    # Execute workflow
    result = await engine.execute_graph(
        graph_name=graph_name,
        inputs={
            "trigger": "schedule",
            "schedule_id": schedule_id
        },
        thread_id=f"scheduled-{schedule_id}"
    )

    return result
```

#### Example: Checkpoint Service Integration

```python
# backend/api/checkpoints/dependencies.py
from backend.services.dependency_injection import get_execution_engine

def get_checkpoint_manager():
    """
    Get checkpoint manager from execution engine.

    Shows how other services build on dependency injection.
    """
    engine = get_execution_engine()
    # ExecutionEngine has checkpoint functionality
    return engine
```

### Dependency Flow

```
┌─────────────────────────────────────────┐
│      Application Startup (app.py)      │
│     initialize_dependencies()          │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│       DependencyContainer               │
│  ┌──────────────────────────────┐      │
│  │ 1. GraphManager created      │      │
│  │ 2. ExecutionEngine init      │      │
│  │ 3. Instances cached          │      │
│  └──────────────────────────────┘      │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴─────────────┐
        │                        │
        ▼                        ▼
┌──────────────┐        ┌─────────────────┐
│  FastAPI     │        │  Direct Access  │
│  Routes      │        │  (handlers,     │
│  (via        │        │   background    │
│   Depends)   │        │   tasks, CLI)   │
└──────────────┘        └─────────────────┘
```

**Services that depend on this module:**

- All API route modules (graph, execution, checkpoints, etc.)
- Background task processors
- CLI tools and scripts
- Health check endpoints

**Services this module depends on:**

- `backend.services.graph` (GraphManager)
- `backend.services.execution` (ExecutionEngine)
- `backend.services.config` (logging)

### Common Integration Patterns

#### Pattern 1: FastAPI Route with Both Dependencies

```python
from fastapi import APIRouter
from backend.services.dependency_injection import GraphManager, ExecutionEngine

router = APIRouter()

@router.post("/workflows/{graph_name}/execute")
async def execute_workflow(
    graph_name: str,
    graph_mgr: GraphManager,
    engine: ExecutionEngine
):
    """Execute workflow using both dependencies."""

    # Validate graph exists
    graph = graph_mgr.load_graph(graph_name)

    # Execute
    result = await engine.execute_graph(
        graph_name=graph_name,
        inputs={"source": "api"}
    )

    return {"success": True, "result": result}
```

#### Pattern 2: Handler Function with Direct Access

```python
from backend.services.dependency_injection import get_graph_manager

async def background_task_handler(graph_name: str):
    """Background task using direct access."""

    # Can't use FastAPI Depends in background task
    graph_mgr = get_graph_manager()

    # Process
    graphs = graph_mgr.list_graphs()
    for graph in graphs:
        process_graph(graph)
```

#### Pattern 3: Health Check with Metrics

```python
from fastapi import APIRouter
from backend.services.dependency_injection import GraphManager, ExecutionEngine

router = APIRouter()

@router.get("/health")
async def health_check(
    graph_mgr: GraphManager,
    engine: ExecutionEngine
):
    """Health check leveraging dependency metrics."""

    return {
        "status": "healthy",
        "metrics": {
            "active_graphs": len(graph_mgr.active_graphs),
            "active_executions": len(engine.active_executions),
            "total_executions": len(engine.execution_history)
        }
    }
```

## Usage Examples

### Example 1: Basic FastAPI Application Setup

Complete application startup with dependency initialisation:

```python
# backend/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.services.dependency_injection import initialize_dependencies

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""

    # Startup: Initialize dependencies
    try:
        initialize_dependencies()
        print("✓ Dependencies initialized")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        raise

    yield

    # Shutdown
    print("Application shutting down")

# Create app
app = FastAPI(
    title="AgenticStudio API",
    lifespan=lifespan
)

# Include routers
from backend.api.graph import router as graph_router
app.include_router(graph_router)
```

### Example 2: FastAPI Route with Dependency Injection

Using the type alias convenience pattern for clean route definitions:

```python
# backend/api/graph/routes.py
from fastapi import APIRouter, HTTPException
from backend.services.dependency_injection import GraphManager, ExecutionEngine
from typing import Dict, Any

router = APIRouter(prefix="/api/graph", tags=["graph"])

@router.post("/workflows/{graph_name}/execute")
async def execute_workflow(
    graph_name: str,
    inputs: Dict[str, Any],
    graph_mgr: GraphManager,
    engine: ExecutionEngine
):
    """
    Execute a workflow.

    GraphManager and ExecutionEngine are automatically injected.
    If not initialized, FastAPI returns 503 automatically.
    """

    try:
        # Load graph to validate it exists
        graph = graph_mgr.load_graph(graph_name)

        # Execute workflow
        result = await engine.execute_graph(
            graph_name=graph_name,
            inputs=inputs,
            thread_id=None  # New thread
        )

        return {
            "success": True,
            "graph_name": graph_name,
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution failed: {str(e)}"
        )


@router.get("/graphs")
async def list_graphs(graph_mgr: GraphManager):
    """List all available graphs."""

    graphs = graph_mgr.list_graphs()
    return {
        "success": True,
        "count": len(graphs),
        "graphs": graphs
    }


@router.get("/health")
async def health_check(
    graph_mgr: GraphManager,
    engine: ExecutionEngine
):
    """
    System health check with dependency metrics.
    """

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "active_graphs": len(graph_mgr.active_graphs),
            "active_executions": len(engine.active_executions),
            "execution_history": len(engine.execution_history)
        }
    }
```

### Example 3: Direct Access in Background Tasks

Using dependency injection outside FastAPI context:

```python
# backend/tasks/workflow_scheduler.py
import asyncio
from datetime import datetime
from backend.services.dependency_injection import (
    get_graph_manager,
    get_execution_engine,
    is_initialized,
    DependencyNotInitializedError
)

async def scheduled_workflow_executor(graph_name: str, schedule_id: str):
    """
    Execute scheduled workflow.

    Background task that runs outside FastAPI request context.
    """

    # Verify dependencies are ready
    if not is_initialized():
        raise RuntimeError("Cannot execute: dependencies not initialized")

    try:
        # Direct access (can't use FastAPI Depends here)
        graph_mgr = get_graph_manager()
        engine = get_execution_engine()

        # Load graph
        print(f"[{schedule_id}] Loading graph '{graph_name}'...")
        graph = graph_mgr.load_graph(graph_name, username="scheduler")

        # Execute workflow
        print(f"[{schedule_id}] Executing workflow...")
        result = await engine.execute_graph(
            graph_name=graph_name,
            inputs={
                "trigger": "schedule",
                "schedule_id": schedule_id,
                "timestamp": datetime.now().isoformat()
            },
            thread_id=f"schedule-{schedule_id}"
        )

        print(f"[{schedule_id}] ✓ Execution completed")
        return result

    except DependencyNotInitializedError as e:
        print(f"[{schedule_id}] ✗ Dependency error: {e}")
        raise
    except Exception as e:
        print(f"[{schedule_id}] ✗ Execution failed: {e}")
        raise


async def workflow_scheduler_loop():
    """
    Main scheduler loop.

    Runs continuously, executing scheduled workflows.
    """

    # Wait for dependencies to be ready
    while not is_initialized():
        print("Waiting for dependencies to initialize...")
        await asyncio.sleep(1)

    print("✓ Scheduler ready")

    # Scheduler loop
    while True:
        try:
            # Get scheduled workflows
            graph_mgr = get_graph_manager()
            graphs = graph_mgr.list_graphs(username="scheduler")

            # Execute each scheduled graph
            for graph in graphs:
                await scheduled_workflow_executor(
                    graph_name=graph["name"],
                    schedule_id=f"sched-{datetime.now().timestamp()}"
                )

            # Wait before next check
            await asyncio.sleep(60)

        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    # Run scheduler
    asyncio.run(workflow_scheduler_loop())
```

### Example 4: Testing with Mock Dependencies

Complete testing setup with dependency mocking:

```python
# tests/test_workflow_execution.py
import pytest
from unittest.mock import Mock, AsyncMock
from backend.services.dependency_injection.container import _container
from backend.services.dependency_injection import (
    get_graph_manager,
    get_execution_engine,
    DependencyNotInitializedError
)

@pytest.fixture(autouse=True)
def reset_container():
    """Reset dependency container after each test."""
    yield
    _container.reset()


@pytest.fixture
def mock_graph_manager():
    """Provide mocked GraphManager."""
    mock = Mock()
    mock.active_graphs = {}
    mock.list_graphs.return_value = [
        {"name": "graph-1", "nodes": []},
        {"name": "graph-2", "nodes": []}
    ]
    mock.load_graph.return_value = {"name": "graph-1", "nodes": []}
    return mock


@pytest.fixture
def mock_execution_engine():
    """Provide mocked ExecutionEngine."""
    mock = Mock()
    mock.active_executions = {}
    mock.execution_history = []
    mock.execute_graph = AsyncMock(return_value={"status": "completed"})
    return mock


@pytest.fixture
def initialized_dependencies(mock_graph_manager, mock_execution_engine):
    """Initialize dependencies with mocks."""
    # Inject mocks into container
    _container._graph_manager = mock_graph_manager
    _container._execution_engine = mock_execution_engine

    yield {
        "graph_manager": mock_graph_manager,
        "engine": mock_execution_engine
    }


def test_uninitialized_access():
    """Test error when accessing uninitialized dependencies."""

    # Container is reset (autouse fixture)
    with pytest.raises(DependencyNotInitializedError) as exc_info:
        get_graph_manager()

    assert exc_info.value.dependency_name == "GraphManager"
    assert "initialize_dependencies()" in str(exc_info.value)


def test_list_graphs(initialized_dependencies):
    """Test graph listing with mocked dependencies."""

    graph_mgr = get_graph_manager()
    graphs = graph_mgr.list_graphs()

    assert len(graphs) == 2
    assert graphs[0]["name"] == "graph-1"
    graph_mgr.list_graphs.assert_called_once()


@pytest.mark.asyncio
async def test_execute_workflow(initialized_dependencies):
    """Test workflow execution with mocked dependencies."""

    mocks = initialized_dependencies
    engine = get_execution_engine()

    # Execute
    result = await engine.execute_graph(
        graph_name="graph-1",
        inputs={"message": "test"}
    )

    # Verify
    assert result["status"] == "completed"
    mocks["engine"].execute_graph.assert_called_once_with(
        graph_name="graph-1",
        inputs={"message": "test"}
    )


@pytest.mark.asyncio
async def test_fastapi_route_with_mocks(initialized_dependencies):
    """Test FastAPI route handler with mocked dependencies."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, APIRouter
    from backend.services.dependency_injection import GraphManager

    # Create test app
    router = APIRouter()

    @router.get("/graphs")
    async def list_graphs(graph_mgr: GraphManager):
        graphs = graph_mgr.list_graphs()
        return {"success": True, "graphs": graphs}

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Test endpoint
    response = client.get("/graphs")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["graphs"]) == 2
```

## Performance Considerations

### Performance Characteristics

**Singleton Access:** O(1)

- Container access is constant time
- No lookup or search required

**Initialisation:** O(1) with blocking

- One-time initialisation during startup
- Thread-safe locking adds minimal overhead
- Subsequent calls are no-ops (early return)

**Memory Usage:**

- Minimal overhead (single container instance)
- Dependencies themselves manage their own memory
- No caching beyond the two main dependencies

**I/O Characteristics:**

- CPU-bound: Thread synchronisation only
- No I/O operations in dependency injection itself
- Dependencies (GraphManager, ExecutionEngine) handle their own I/O

### Optimisation Tips

#### Tip 1: Cache Dependency References

**Problem:**

```python
# Inefficient: Multiple property access with validation
@router.get("/endpoint1")
async def endpoint1(graph_mgr: GraphManager):
    graphs = get_graph_manager().list_graphs()  # Access 1

@router.get("/endpoint2")
async def endpoint2():
    graphs = get_graph_manager().list_graphs()  # Access 2
    status = get_graph_manager().get_status()   # Access 3
```

**Solution:**

```python
# Efficient: Use FastAPI dependency injection
@router.get("/endpoint1")
async def endpoint1(graph_mgr: GraphManager):
    # Injected once per request
    graphs = graph_mgr.list_graphs()

@router.get("/endpoint2")
async def endpoint2(graph_mgr: GraphManager):
    # Single instance per request
    graphs = graph_mgr.list_graphs()
    status = graph_mgr.get_status()
```

#### Tip 2: Avoid Redundant Initialisation Checks

**Problem:**

```python
# Inefficient: Checking initialization repeatedly
def process_item(item):
    if not is_initialized():
        raise RuntimeError("Not initialized")
    graph_mgr = get_graph_manager()
    # ... process item

# Called 1000 times
for item in items:
    process_item(item)  # 1000 initialization checks!
```

**Solution:**

```python
# Efficient: Check once, process many
if not is_initialized():
    raise RuntimeError("Not initialized")

graph_mgr = get_graph_manager()  # Get once

for item in items:
    # Use cached reference
    graph_mgr.process(item)
```

### Thread Safety

The dependency injection module is fully thread-safe:

```python
import threading
from backend.services.dependency_injection import get_graph_manager

def worker_thread():
    """Safe to access from multiple threads."""
    graph_mgr = get_graph_manager()
    graphs = graph_mgr.list_graphs()
    print(f"Thread {threading.current_thread().name}: {len(graphs)} graphs")

# Safe concurrent access
threads = [
    threading.Thread(target=worker_thread, name=f"Worker-{i}")
    for i in range(10)
]

for t in threads:
    t.start()

for t in threads:
    t.join()
```

**Thread Safety Guarantees:**

- Singleton creation uses double-checked locking
- Initialisation uses separate lock for thread safety
- Property access is thread-safe (reads only after init)
- No shared mutable state after initialisation

### Async/Await Support

Dependencies are synchronously initialised but can be used in async contexts:

```python
from backend.services.dependency_injection import ExecutionEngine

@router.post("/execute")
async def execute_workflow(engine: ExecutionEngine):
    """
    ExecutionEngine dependency is synchronously retrieved,
    but its methods can be async.
    """

    # Sync: Get dependency (fast, from cache)
    # Async: Use dependency methods
    result = await engine.execute_graph(
        graph_name="workflow-1",
        inputs={"message": "hello"}
    )

    return {"result": result}
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock
from backend.services.dependency_injection import (
    get_graph_manager,
    DependencyNotInitializedError
)
from backend.services.dependency_injection.container import _container

@pytest.fixture(autouse=True)
def reset_dependencies():
    """Reset container after each test for isolation."""
    yield
    _container.reset()


def test_container_singleton():
    """Test that container is a singleton."""
    from backend.services.dependency_injection.container import DependencyContainer

    instance1 = DependencyContainer()
    instance2 = DependencyContainer()

    assert instance1 is instance2


def test_uninitialized_access_raises_error():
    """Test error when accessing uninitialized dependency."""

    with pytest.raises(DependencyNotInitializedError) as exc_info:
        get_graph_manager()

    assert exc_info.value.dependency_name == "GraphManager"


def test_is_initialized_returns_false_before_init():
    """Test is_initialized before calling initialize."""
    from backend.services.dependency_injection import is_initialized

    assert is_initialized() is False


def test_graph_manager_access_after_mock_init():
    """Test accessing GraphManager after manual mock initialization."""

    # Manually inject mock
    mock_graph_mgr = Mock()
    _container._graph_manager = mock_graph_mgr
    _container._execution_engine = Mock()  # Both needed for is_initialized

    # Should work now
    graph_mgr = get_graph_manager()
    assert graph_mgr is mock_graph_mgr
```

### Mocking Dependencies

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.dependency_injection.container import _container

@pytest.fixture
def mock_dependencies():
    """Fixture providing fully mocked dependencies."""

    # Reset
    _container.reset()

    # Create comprehensive mocks
    mock_graph_mgr = Mock()
    mock_graph_mgr.active_graphs = {"graph-1": {}}
    mock_graph_mgr.list_graphs.return_value = ["graph-1", "graph-2"]
    mock_graph_mgr.load_graph.return_value = {"name": "graph-1"}
    mock_graph_mgr.get_graph.return_value = {"name": "graph-1"}

    mock_engine = Mock()
    mock_engine.active_executions = {}
    mock_engine.execution_history = []
    mock_engine.execute_graph = AsyncMock(return_value={"status": "completed"})

    # Inject mocks
    _container._graph_manager = mock_graph_mgr
    _container._execution_engine = mock_engine

    yield {
        "graph_manager": mock_graph_mgr,
        "engine": mock_engine
    }

    # Cleanup
    _container.reset()


def test_with_mocked_graph_manager(mock_dependencies):
    """Test using mocked GraphManager."""
    from backend.services.dependency_injection import get_graph_manager

    graph_mgr = get_graph_manager()
    graphs = graph_mgr.list_graphs()

    assert graphs == ["graph-1", "graph-2"]
    graph_mgr.list_graphs.assert_called_once()


@pytest.mark.asyncio
async def test_with_mocked_engine(mock_dependencies):
    """Test using mocked ExecutionEngine."""
    from backend.services.dependency_injection import get_execution_engine

    engine = get_execution_engine()
    result = await engine.execute_graph(graph_name="test")

    assert result["status"] == "completed"
    engine.execute_graph.assert_called_once_with(graph_name="test")
```

### Integration Testing

```python
import pytest
from backend.services.dependency_injection import (
    initialize_dependencies,
    get_graph_manager,
    get_execution_engine,
    is_initialized
)
from backend.services.dependency_injection.container import _container

@pytest.fixture(scope="module")
def initialized_app():
    """Initialize real dependencies for integration tests."""

    # Initialize with real dependencies
    initialize_dependencies()

    yield

    # Cleanup
    _container.reset()


@pytest.mark.integration
def test_real_initialization(initialized_app):
    """Test real dependency initialization."""

    assert is_initialized() is True

    # Get real instances
    graph_mgr = get_graph_manager()
    engine = get_execution_engine()

    # Verify they're real objects with expected attributes
    assert hasattr(graph_mgr, "active_graphs")
    assert hasattr(engine, "active_executions")


@pytest.mark.integration
async def test_real_graph_operations(initialized_app):
    """Test real graph operations."""

    graph_mgr = get_graph_manager()

    # Real operation
    graphs = graph_mgr.list_graphs(username="test-user")

    # Should return list (may be empty)
    assert isinstance(graphs, list)


@pytest.mark.integration
def test_fastapi_app_startup():
    """Test full FastAPI app startup."""
    from fastapi.testclient import TestClient
    from backend.app import app

    # App startup should initialize dependencies
    client = TestClient(app)

    # Verify initialization
    assert is_initialized() is True

    # Test health endpoint
    response = client.get("/api/graph/health")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "active_graphs" in data
```

## Best Practices

### Do's

**✅ Initialize once at application startup**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ Initialize in lifespan
    initialize_dependencies()
    yield

app = FastAPI(lifespan=lifespan)
```

**✅ Use FastAPI type aliases in route handlers**

```python
# ✅ Clean, automatic injection
@router.get("/graphs")
async def list_graphs(graph_mgr: GraphManager):
    return graph_mgr.list_graphs()
```

**✅ Use direct access in non-FastAPI code**

```python
# ✅ Correct for background tasks
def background_task():
    graph_mgr = get_graph_manager()
    graph_mgr.process()
```

**✅ Check initialization in background workers**

```python
# ✅ Safe background worker startup
async def worker():
    while not is_initialized():
        await asyncio.sleep(0.1)

    # Now safe to use
    engine = get_execution_engine()
```

**✅ Use Protocol types for testing**

```python
# ✅ Easy to mock with Protocol
def process(graph_mgr: GraphManagerProtocol):
    graphs = graph_mgr.list_graphs()
```

**✅ Handle initialization errors gracefully**

```python
# ✅ Proper error handling
try:
    initialize_dependencies()
except InitializationError as e:
    logger.critical(f"Startup failed: {e}")
    sys.exit(1)
```

### Don'ts

**❌ Don't call initialize_dependencies() in route handlers**

```python
# ❌ Wrong: Re-initializing on every request
@router.get("/graphs")
async def list_graphs():
    initialize_dependencies()  # ❌ Don't do this!
    graph_mgr = get_graph_manager()
    return graph_mgr.list_graphs()

# ✅ Correct: Initialize once at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_dependencies()  # ✅ Once at startup
    yield
```

**❌ Don't use Depends() in non-FastAPI code**

```python
# ❌ Wrong: Depends doesn't work outside routes
def background_task(graph_mgr: GraphManager):  # ❌ Won't work!
    graph_mgr.process()

# ✅ Correct: Direct access
def background_task():
    graph_mgr = get_graph_manager()  # ✅ Works everywhere
    graph_mgr.process()
```

**❌ Don't create multiple containers**

```python
# ❌ Wrong: Attempting to create multiple containers
container1 = DependencyContainer()
container2 = DependencyContainer()
# They're the same instance anyway (singleton)

# ✅ Correct: Use the public API
from backend.services.dependency_injection import get_graph_manager
graph_mgr = get_graph_manager()
```

**❌ Don't access _container directly in application code**

```python
# ❌ Wrong: Accessing private container
from backend.services.dependency_injection.container import _container
graph_mgr = _container.graph_manager  # ❌ Private API!

# ✅ Correct: Use public API
from backend.services.dependency_injection import get_graph_manager
graph_mgr = get_graph_manager()  # ✅ Public API
```

**❌ Don't forget to reset container in tests**

```python
# ❌ Wrong: Tests may interfere with each other
def test_something():
    # ... test code ...
    # ❌ Forgot to reset!

# ✅ Correct: Always reset after tests
@pytest.fixture(autouse=True)
def reset_container():
    yield
    _container.reset()  # ✅ Clean slate for each test
```

**❌ Don't catch DependencyError without re-raising**

```python
# ❌ Wrong: Silently catching critical errors
try:
    initialize_dependencies()
except DependencyError:
    pass  # ❌ Application can't work without dependencies!

# ✅ Correct: Let it fail or handle properly
try:
    initialize_dependencies()
except InitializationError as e:
    logger.critical(f"Cannot start: {e}")
    sys.exit(1)  # ✅ Fail fast
```

## Related Documentation

### Related Services

- [Graph Service](./graph.md) - GraphManager implementation and workflow management
- [Execution Service](./execution.md) - ExecutionEngine implementation and workflow execution
- [Checkpoint Service](./checkpoint.md) - Checkpoint management via ExecutionEngine

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Primary consumer of dependency injection
- [Checkpoints API](../agents-guide/api/checkpoints.md) - Uses ExecutionEngine for checkpoint operations
- [HTTP Execution API](../agents-guide/api/http_execution.md) - Uses both GraphManager and ExecutionEngine

### Architecture Documentation

- [Design Principles](../architecture/03-design-principles.md) - Dependency injection patterns in AgenticStudio
- [System Overview](../architecture/00-overview.md) - How DI fits into overall architecture

## Summary

The Dependency Injection service provides a robust, thread-safe foundation for managing shared application dependencies
in AgenticStudio. By implementing a singleton container pattern with FastAPI-native integration, it enables clean separation
of concerns, easy testing, and type-safe dependency access throughout the application.

The module's design prioritises developer experience through Protocol-based typing, clear error messages, comprehensive
logging, and dual access patterns (FastAPI injection and direct access). This flexibility ensures that dependencies can
be reliably accessed whether in FastAPI route handlers, background tasks, CLI tools, or test environments.

**Key Features:**

- Thread-safe singleton container with double-checked locking
- FastAPI-native dependency injection via Annotated type aliases
- Protocol-based typing for flexibility and testability
- Dual access patterns (FastAPI Depends and direct access)
- Clear exception hierarchy with actionable error messages
- Comprehensive logging for debugging and monitoring

**Primary Use Cases:**

- Application startup dependency initialisation
- FastAPI route handler dependency injection
- Background task and worker dependency access
- CLI tool and script integration
- Test environment with mockable dependencies

**When to Use This Service:**

- **Always** for accessing GraphManager or ExecutionEngine
- **Startup** to initialise shared application dependencies
- **Routes** via FastAPI dependency injection type aliases
- **Background Tasks** via direct access functions
- **Testing** with Protocol types for easy mocking
