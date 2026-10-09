# Nodes Service Documentation

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Public API](#public-api)
- [Core Classes](#core-classes)
- [Node Executors](#node-executors)
- [Handler Services](#handler-services)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Integration Patterns](#integration-patterns)
- [Usage Examples](#usage-examples)
- [Performance Considerations](#performance-considerations)
- [Testing Patterns](#testing-patterns)
- [Best Practices](#best-practices)
- [Related Documentation](#related-documentation)
- [Summary](#summary)

## Overview

The nodes service module provides a modular, extensible framework for executing different types of workflow nodes (
agents, HTTP requests, conditions, file operations, database operations, etc.) in the AgenticStudio backend.

**Location:** `backend/services/nodes/`

**Primary Responsibilities:**

- Provides abstract base class and protocol for node executors
- Implements Strategy pattern via NodeExecutorRegistry for dynamic executor selection
- Provides concrete executors for all supported node types (AGENT, HTTP_REQUEST, CONDITION, FILE_READ, EMAIL_SEND,
  DATABASE_INSERT)
- Manages database tracking for node executions
- Handles WebSocket notifications for real-time UI updates
- Ensures consistent execution flow across all node types

**Key Use Cases:**

- Execute different types of workflow nodes with a consistent interface
- Register custom node executors for new node types
- Track node execution history in the database
- Send real-time execution updates via WebSocket
- Handle errors consistently across all node types

---

## Architecture

### Module Structure

```
backend/services/nodes/
├── __init__.py                      # Public API exports
├── base.py                          # BaseNodeExecutor, NodeExecutorProtocol
├── registry.py                      # NodeExecutorRegistry (Strategy pattern)
├── executors/                       # Concrete executor implementations
│   ├── __init__.py                  # Executor exports
│   ├── agent.py                     # AgentNodeExecutor
│   ├── http.py                      # HttpNodeExecutor
│   ├── condition.py                 # ConditionNodeExecutor
│   ├── file.py                      # FileNodeExecutor
│   ├── email.py                     # EmailNodeExecutor
│   └── database/                    # Database executor package
│       ├── __init__.py              # Database package exports
│       ├── executor.py              # DatabaseNodeExecutor
│       ├── connection_manager.py    # DatabaseConnectionManager
│       ├── query_builder.py         # DatabaseQueryBuilder
│       ├── config.py                # Configuration classes
│       └── exceptions.py            # Custom exceptions
└── handlers/                        # Shared handler services
    ├── __init__.py                  # Handler exports
    ├── database_tracker.py          # NodeDatabaseTracker
    └── notification_handler.py      # NodeNotificationHandler
```

**File Purposes:**

- **base.py**: Abstract base class and protocol defining the executor interface
- **registry.py**: Centralized registry implementing Strategy pattern for executor selection
- **executors/*.py**: Concrete implementations for each node type
- **executors/database/**: Full sub-package for database operations with modular services
- **handlers/database_tracker.py**: Shared service for tracking executions in database
- **handlers/notification_handler.py**: Shared service for WebSocket notifications

### Design Patterns

#### 1. **Strategy Pattern**

The `NodeExecutorRegistry` allows dynamic selection of executors based on node type:

```python
# Register executors for different node types
NodeExecutorRegistry.register(NodeType.AGENT, AgentNodeExecutor)
NodeExecutorRegistry.register(NodeType.HTTP_REQUEST, HttpNodeExecutor)

# Get the appropriate executor at runtime
executor = NodeExecutorRegistry.get_executor(node.type, dependencies)
await executor.execute(node, state, graph, execution_id)
```

#### 2. **Template Method Pattern**

`BaseNodeExecutor` provides template methods with hooks:

```python
class BaseNodeExecutor(ABC):
    async def pre_execute(self, node, state, execution_id):
        """Hook called before execution"""
        pass

    @abstractmethod
    async def execute(self, node, state, graph, execution_id, user_id):
        """Main execution method - must be implemented"""
        pass

    async def post_execute(self, node, state, execution_id, result, duration):
        """Hook called after successful execution"""
        pass

    async def on_error(self, node, state, execution_id, error):
        """Hook called on error"""
        pass
```

#### 3. **Dependency Injection Pattern**

Executors receive dependencies through constructor injection:

```python
class AgentNodeExecutor(BaseNodeExecutor):
    def __init__(
        self,
        execution_history_service: Any,
        ws_notifier: Any,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        super().__init__(execution_history_service, ws_notifier, subgraph_executor, graph_manager)
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)
```

#### 4. **Separation of Concerns**

Handler services extract common functionality:

```
┌─────────────────────┐
│  AgentNodeExecutor  │
│  HttpNodeExecutor   │  ───────────┐
│  FileNodeExecutor   │             │
└─────────────────────┘             │
                                    ▼
                        ┌──────────────────────────┐
                        │ NodeDatabaseTracker      │
                        │ - create_node_execution  │
                        │ - complete_node_execution│
                        └──────────────────────────┘
                                    │
                                    ▼
                        ┌──────────────────────────┐
                        │ NodeNotificationHandler  │
                        │ - notify_start           │
                        │ - notify_complete        │
                        │ - notify_error           │
                        └──────────────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.models.workflow` - EnhancedNodeData, NodeType models
- `backend.services.workflow.state` - WorkflowState management
- `backend.services.execution` - ExecutionEngine, ExecutionHistoryService
- `backend.services.websocket` - WebSocket notifier service
- `backend.services.io` - InputBuilder, MappingValueExtractor
- `backend.services.memory` - Memory manager for agent context
- `backend.services.agent` - Agent compilation and execution
- `backend.services.conditions` - Condition evaluation
- `backend.services.email` - Email sending
- `backend.services.datasource` - Database connections

**External Dependencies:**

- `requests` - HTTP requests (HttpNodeExecutor)
- `langchain_core` - LLM integrations (AgentNodeExecutor, FileNodeExecutor)
- `psycopg2` - PostgreSQL connections (DatabaseNodeExecutor)

**Database Dependencies:**

- Uses `execution_history_service` to create and track node_execution records
- Stores input/output data, token counts, execution order, timing

**Configuration:**

- No environment variables required
- Configuration embedded in node definitions via node configs (agent_config, http_request_action_config, etc.)

---

## Public API

### Exported Classes

From `backend.services.nodes`:

- **`BaseNodeExecutor`** - Abstract base class for all node executors
- **`NodeExecutorProtocol`** - Protocol defining executor interface (for duck typing)
- **`NodeExecutorRegistry`** - Registry for managing and retrieving executors

From `backend.services.nodes.executors`:

- **`AgentNodeExecutor`** - Executor for AGENT nodes
- **`HttpNodeExecutor`** - Executor for HTTP_REQUEST_ACTION nodes
- **`ConditionNodeExecutor`** - Executor for CONDITION nodes
- **`FileNodeExecutor`** - Executor for FILE_READ nodes
- **`EmailNodeExecutor`** - Executor for EMAIL_SEND nodes
- **`DatabaseNodeExecutor`** - Executor for DATABASE_INSERT nodes

From `backend.services.nodes.handlers`:

- **`NodeDatabaseTracker`** - Shared service for database tracking
- **`NodeNotificationHandler`** - Shared service for WebSocket notifications

From `backend.services.nodes.executors.database`:

- **`DatabaseConnectionManager`** - Manages database connections
- **`DatabaseQueryBuilder`** - Builds SQL queries
- **`DatabaseInsertConfig`** - Type-safe configuration for database inserts

### Exported Functions

No standalone functions are exported. The module uses class-based architecture.

### Constants and Configuration

No module-level constants exported. Configuration is per-node-type.

### Exceptions

**Database Executor Exceptions:**

```
Exception
└── DatabaseNodeError
    ├── DatabaseConnectionError    # Connection failures
    ├── QueryBuildError            # Query construction errors
    ├── QueryExecutionError        # Query execution errors
    └── ConfigurationError         # Invalid configuration
```

See [Error Handling](#error-handling) section for details.

---

## Core Classes

### `BaseNodeExecutor`

Abstract base class providing a consistent interface for all node executors.

**Purpose:** Establish a standard execution contract and provide common lifecycle hooks for all node types.

**Responsibilities:**

- Define the `execute()` method signature that all executors must implement
- Provide lifecycle hooks (`pre_execute`, `post_execute`, `on_error`)
- Store shared dependencies (execution_history_service, ws_notifier, graph_manager)
- Validate node configuration via `validate_config()`

**Initialisation:**

```python
def __init__(
    self,
    execution_history_service: Any,
    ws_notifier: Any,
    subgraph_executor: Optional[Any] = None,
    graph_manager: Optional[Any] = None,
) -> None:
    """
    Args:
        execution_history_service: Service for tracking execution history
        ws_notifier: WebSocket notifier for real-time updates
        subgraph_executor: Optional executor for handling subgraphs
        graph_manager: Optional manager for graph operations
    """
```

**Key Methods:**

#### `execute()`

```python
@abstractmethod
async def execute(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    graph: Any,
    execution_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the node and return state updates.

    Must be implemented by all concrete executors.
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to execute with configuration
- `state` (WorkflowState) - Current workflow state dictionary
- `graph` - The StateGraph or graph definition
- `execution_id` (str) - Unique execution identifier
- `user_id` (Optional[str]) - Optional user identifier

**Returns:**

- `Dict[str, Any]` - State updates to apply, typically containing:
  - `node_output`: Structured output data
  - Execution order updates
  - Any other state modifications

**Raises:**

- Subclass-specific exceptions (e.g., `DatabaseNodeError`)

**Example:**

```python
from backend.services.nodes import BaseNodeExecutor

class CustomNodeExecutor(BaseNodeExecutor):
    async def execute(self, node, state, graph, execution_id, user_id=None):
        # Pre-execution setup
        await self.pre_execute(node, state, execution_id)

        try:
            # Execute node logic
            result = await self._do_work(node, state)

            # Post-execution cleanup
            await self.post_execute(node, state, execution_id, result, duration=1.5)

            return {"node_output": result}
        except Exception as e:
            await self.on_error(node, state, execution_id, e)
            raise
```

**Behaviour:**

- Called by workflow execution engine for each node
- Should create database tracking record via `NodeDatabaseTracker`
- Should send WebSocket notifications via `NodeNotificationHandler`
- Should handle errors gracefully and return error state
- Should update execution order in state

**Use Cases:**

- Implementing new custom node types
- Standardizing execution flow across different node types
- Ensuring consistent database tracking and notifications

#### `validate_config()`

```python
async def validate_config(self, node: EnhancedNodeData) -> bool:
    """
    Validate node configuration before execution.

    Override to provide node-type-specific validation.
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to validate

**Returns:**

- `bool` - True if valid, False otherwise

**Example:**

```python
async def validate_config(self, node: EnhancedNodeData) -> bool:
    if not node.http_request_action_config:
        return False
    if not node.http_request_action_config.url_template:
        return False
    return True
```

#### `pre_execute()`

```python
async def pre_execute(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    execution_id: str,
) -> None:
    """
    Execute setup tasks before node execution.

    Override to perform setup like logging, notifications, resource allocation.
    """
```

**Use Cases:**

- Send early WebSocket notification
- Initialize resources
- Log execution start

#### `post_execute()`

```python
async def post_execute(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    execution_id: str,
    result: Dict[str, Any],
    duration_seconds: float,
) -> None:
    """
    Execute cleanup tasks after successful execution.

    Override for cleanup like notifications, metrics, resource cleanup.
    """
```

**Use Cases:**

- Send completion WebSocket notification
- Collect metrics
- Clean up resources

#### `on_error()`

```python
async def on_error(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    execution_id: str,
    error: Exception,
) -> None:
    """
    Handle node execution failure.

    Override for error handling like logging, notifications, recovery.
    """
```

**Use Cases:**

- Log detailed error information
- Send error WebSocket notification
- Attempt error recovery
- Clean up partial state

**Class Attributes:**

- `execution_history_service: Any` - Service for execution tracking
- `ws_notifier: Any` - WebSocket notifier
- `subgraph_executor: Optional[Any]` - Subgraph executor
- `graph_manager: Optional[Any]` - Graph manager

---

### `NodeExecutorProtocol`

Protocol defining the interface for node executors using structural subtyping.

**Purpose:** Allow any class implementing `execute()` and `validate_config()` to be used as a node executor without
inheriting from `BaseNodeExecutor`.

**Responsibilities:**

- Define minimum interface for duck typing
- Enable type checking without inheritance

**Key Methods:**

```python
async def execute(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    graph: Any,
    execution_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a node and return state updates."""
    ...

async def validate_config(self, node: EnhancedNodeData) -> bool:
    """Validate node configuration."""
    ...
```

**Example:**

```python
from typing import Dict, Any, Optional
from backend.services.nodes import NodeExecutorProtocol
from backend.models.workflow import EnhancedNodeData
from backend.services.workflow.state import WorkflowState

class MyCustomExecutor:  # No inheritance needed!
    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {"node_output": {"result": "custom"}}

    async def validate_config(self, node: EnhancedNodeData) -> bool:
        return True

# Type checker accepts this
executor: NodeExecutorProtocol = MyCustomExecutor()
```

**Use Cases:**

- Creating lightweight custom executors without inheritance
- Type checking with duck typing
- Testing with mock executors

---

### `NodeExecutorRegistry`

Centralized registry for node executors implementing the Strategy pattern.

**Purpose:** Provide dynamic executor selection based on node type, supporting both class-based and factory-based
registration.

**Responsibilities:**

- Maintain mapping of NodeType to executor classes or factories
- Instantiate executors with dependencies
- Cache factory-created instances
- Provide query and management methods

**Class Attributes:**

- `_executors: Dict[str, Type[BaseNodeExecutor]]` - Registered executor classes
- `_factories: Dict[str, Callable[[], BaseNodeExecutor]]` - Registered factory functions
- `_instances: Dict[str, BaseNodeExecutor]` - Cached instances from factories

**Key Methods:**

#### `register()`

```python
@classmethod
def register(
    cls,
    node_type: NodeType,
    executor_class: Optional[Type[BaseNodeExecutor]] = None,
    factory: Optional[Callable[[], BaseNodeExecutor]] = None,
) -> None:
    """
    Register an executor for a specific node type.

    Can register either a class or a factory function (mutually exclusive).
    """
```

**Parameters:**

- `node_type` (NodeType) - The NodeType this executor handles
- `executor_class` (Optional[Type[BaseNodeExecutor]]) - Executor class to register
- `factory` (Optional[Callable]) - Factory function returning executor instance

**Raises:**

- `ValueError` - If both or neither of executor_class and factory provided

**Example:**

```python
from backend.services.nodes import NodeExecutorRegistry
from backend.models.workflow import NodeType

# Register with class
NodeExecutorRegistry.register(NodeType.AGENT, AgentNodeExecutor)

# Register with factory (for dependency injection)
def create_http_executor():
    return HttpNodeExecutor(
        execution_history_service=get_execution_service(),
        ws_notifier=get_ws_notifier(),
    )

NodeExecutorRegistry.register(
    NodeType.HTTP_REQUEST,
    factory=create_http_executor
)
```

**Behaviour:**

- Class registrations require dependencies to be passed during `get_executor()`
- Factory registrations create and cache a single instance
- Logs registration events for debugging

#### `get_executor()`

```python
@classmethod
def get_executor(
    cls,
    node_type: NodeType,
    dependencies: Optional[Dict[str, Any]] = None,
) -> BaseNodeExecutor:
    """
    Get an executor for a specific node type.

    For class registration: instantiates with dependencies
    For factory registration: returns cached instance or creates one
    """
```

**Parameters:**

- `node_type` (NodeType) - The NodeType to get executor for
- `dependencies` (Optional[Dict[str, Any]]) - Dependencies for class-based executors

**Returns:**

- `BaseNodeExecutor` - Executor instance for the node type

**Raises:**

- `KeyError` - If no executor registered for the node type

**Example:**

```python
from backend.models.workflow import NodeType

# Get executor registered as class
executor = NodeExecutorRegistry.get_executor(
    NodeType.AGENT,
    dependencies={
        "execution_history_service": service,
        "ws_notifier": notifier,
        "graph_manager": manager,
    }
)

# Get executor registered as factory
executor = NodeExecutorRegistry.get_executor(NodeType.HTTP_REQUEST)

# Use the executor
result = await executor.execute(node, state, graph, exec_id)
```

**Behaviour:**

- Checks factories first, then classes
- Caches factory instances (singleton per node type)
- Validates dependencies for class-based executors
- Logs executor creation for debugging

**Use Cases:**

- Dynamic executor selection at runtime
- Dependency injection for executors
- Singleton pattern for factory-based executors

#### `is_registered()`

```python
@classmethod
def is_registered(cls, node_type: NodeType) -> bool:
    """Check if an executor is registered for a node type."""
```

**Example:**

```python
if NodeExecutorRegistry.is_registered(NodeType.AGENT):
    executor = NodeExecutorRegistry.get_executor(NodeType.AGENT)
else:
    raise ValueError(f"No executor for {NodeType.AGENT}")
```

#### `list_registered_types()`

```python
@classmethod
def list_registered_types(cls) -> List[str]:
    """List all registered node types."""
```

**Example:**

```python
registered = NodeExecutorRegistry.list_registered_types()
print(f"Registered executors: {', '.join(registered)}")
# Output: Registered executors: AGENT, CONDITION, DATABASE_INSERT, EMAIL_SEND, FILE_READ, HTTP_REQUEST
```

#### `unregister()`

```python
@classmethod
def unregister(cls, node_type: NodeType) -> None:
    """
    Unregister an executor for a node type.

    Useful for testing or hot-swapping executors.
    """
```

**Example:**

```python
# Hot-swap executor implementation
NodeExecutorRegistry.unregister(NodeType.AGENT)
NodeExecutorRegistry.register(NodeType.AGENT, NewAgentExecutor)
```

#### `clear()`

```python
@classmethod
def clear(cls) -> None:
    """
    Clear all registered executors.

    Useful for testing or reinitialization.
    """
```

**Example:**

```python
# Clean slate for testing
NodeExecutorRegistry.clear()
# Re-register with test implementations
```

---

## Node Executors

### `AgentNodeExecutor`

Executor for AGENT nodes, handling LLM agent execution with tools and memory.

**Purpose:** Coordinate agent execution including input building, tool execution, memory management, and result
tracking.

**Responsibilities:**

- Build input with memory context if enabled
- Execute agent via graph_manager
- Track tool executions as separate node_execution records
- Store conversation in memory if enabled
- Track token usage
- Send WebSocket notifications
- Handle errors gracefully

**Key Methods:**

#### `execute()`

Orchestrates complete agent execution flow:

1. Send early start notification
2. Build input with memory context
3. Create database tracking record
4. Execute agent with graph_manager
5. Process response and token counts
6. Update database and send completion notification
7. Track tool executions
8. Store memory if enabled
9. Return state updates

**Example:**

```python
from backend.services.nodes.executors import AgentNodeExecutor

executor = AgentNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
    graph_manager=graph_manager,
)

result = await executor.execute(
    node=agent_node,
    state=current_state,
    graph=workflow_graph,
    execution_id="exec-abc123",
    user_id="user-456",
)

print(result["node_output"]["raw"])  # Agent response
print(result["node_output"]["token_counts"])  # Token usage
print(result["node_output"]["tool_executions"])  # Tools used
```

**Behaviour:**

- Loads conversation memory from `memory_manager` if `memory_enabled=True`
- Executes agent asynchronously via `graph_manager.execute_agent_async()`
- Creates separate `node_execution` records for each tool used
- Stores conversation in memory automatically (handled by async executor)
- Increments execution order in state
- Sends real-time WebSocket updates during execution

**Internal Methods:**

- `_send_early_notification()` - Send WebSocket notification before database tracking
- `_build_input_with_memory()` - Build input with conversation history
- `_create_tracking_record()` - Create node_execution record
- `_execute_agent_logic()` - Execute agent via graph_manager
- `_process_agent_response()` - Extract response and token counts
- `_complete_tracking()` - Update database and send completion notification
- `_track_tool_executions()` - Create node_execution records for tools
- `_store_memory_if_enabled()` - Store conversation (no-op for async executor)
- `_build_state_update()` - Build state update dictionary
- `_handle_error()` - Handle execution errors

---

### `HttpNodeExecutor`

Executor for HTTP_REQUEST_ACTION nodes, handling HTTP requests with comprehensive configuration.

**Purpose:** Execute HTTP requests with dynamic parameter mapping, authentication, retry logic, and response parsing.

**Responsibilities:**

- Process URL/query/header/body parameter mappings from workflow state
- Set up authentication (Bearer, API Key, Basic Auth)
- Execute requests with retry and exponential backoff
- Parse and extract response data
- Validate status codes
- Track execution in database

**Key Methods:**

#### `execute()`

Executes HTTP request with full parameter mapping and error handling.

**Example:**

```python
from backend.services.nodes.executors import HttpNodeExecutor

executor = HttpNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
)

# HTTP node configured with:
# - URL template: "https://api.example.com/users/{user_id}"
# - Query params: limit=10
# - Headers: Authorization from previous node
# - Body: JSON from previous node outputs

result = await executor.execute(
    node=http_node,
    state=current_state,
    graph=workflow_graph,
    execution_id="exec-def456",
)

print(result["node_output"]["structured"]["status_code"])  # 200
print(result["node_output"]["structured"]["data"])  # Parsed JSON response
```

**Configuration Features:**

- **URL Parameters**: `{param}` placeholders replaced with values from state
- **Query Parameters**: Appended as `?key=value` from mappings
- **Headers**: Static headers + dynamic headers from state
- **Body**: JSON body built from field mappings or template string
- **Authentication**: Bearer token, API key, or Basic Auth
- **Retry Logic**: Configurable max retries with exponential backoff
- **Response Path**: Extract nested fields from JSON response (e.g., `"data.users"`)
- **Success Codes**: Validate response against expected status codes

**Internal Methods:**

- `_validate_config()` - Validate HTTP configuration exists
- `_parse_config()` - Parse config into `HttpRequestConfig`
- `_build_request()` - Build complete HTTP request specification
- `_process_url_parameters()` - Substitute URL path parameters
- `_process_query_parameters()` - Extract query parameters from state
- `_process_headers()` - Build headers from base config and mappings
- `_process_body()` - Build request body from mappings or template
- `_setup_auth()` - Configure authentication
- `_execute_request()` - Execute with retry logic
- `_handle_response()` - Parse and validate response

---

### `ConditionNodeExecutor`

Executor for CONDITION nodes, evaluating conditions and determining workflow branching.

**Purpose:** Evaluate conditions (binary, multi-branch, expression, LLM-based) and determine which branch to take.

**Responsibilities:**

- Evaluate different condition types (simple, expression, LLM)
- Support binary (true/false) and multi-branch conditions
- Store condition result in state for routing
- Track execution in database

**Condition Types:**

1. **Binary Simple**: Compare values with operators (==, !=, >, <, >=, <=, contains, etc.)
2. **Expression**: Evaluate Python-like expressions on workflow state
3. **Multi-Branch**: Evaluate multiple conditions, return branch index
4. **LLM-Based**: Use LLM to evaluate natural language condition

**Example:**

```python
from backend.services.nodes.executors import ConditionNodeExecutor

executor = ConditionNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
    graph_manager=graph_manager,
)

# Binary condition: if agent_response contains "approved"
result = await executor.execute(
    node=condition_node,
    state=current_state,
    graph=workflow_graph,
    execution_id="exec-ghi789",
)

print(result["branch_taken"])  # 0 for true, 1 for false
print(result["source_handle"])  # "true" or "false"
print(result["condition_result"])  # "true" or "false"
```

**Behaviour:**

- Stores condition result in state as `__condition_result_{node_id}` for routing
- Delegates evaluation to `ConditionEvaluator` service
- Returns branch information (branch_taken, source_handle, branch_label, condition_result)
- Tracks execution in database with branch result

**Internal Methods:**

- `_evaluate_condition()` - Main evaluation dispatcher
- `_evaluate_binary()` - Binary true/false conditions
- `_evaluate_expression()` - Expression-based conditions
- `_evaluate_multi_branch()` - Multi-branch conditions
- `_evaluate_llm()` - LLM-based natural language conditions
- `_default_branch()` - Return default when no config
- `_track_condition()` - Track in database and notify

---

### `FileNodeExecutor`

Executor for FILE_READ nodes, handling file reading with OCR support.

**Purpose:** Read files from various sources (path, base64, content) and extract text using OCR for PDFs/images or
direct reading for text files.

**Responsibilities:**

- Accept file input in multiple formats (path, base64, content)
- Validate file size, type, and permissions
- Extract text from PDFs, images, and documents using GPT-4o OCR
- Read plain text files directly
- Support chunking for large documents

**Supported File Types:**

- **OCR Processing**: PDF, PNG, JPG, JPEG, DOCX, XLSX, PPTX
- **Direct Text**: TXT, MD, CSV, JSON, XML, HTML

**Example:**

```python
from backend.services.nodes.executors import FileNodeExecutor

executor = FileNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
    graph_manager=graph_manager,
)

# File provided in workflow state
state["file_info"] = {
    "path": "/uploads/document.pdf",
    # or "base64": "data:application/pdf;base64,..."
    # or "content": "plain text content"
}

result = await executor.execute(
    node=file_node,
    state=state,
    graph=workflow_graph,
    execution_id="exec-jkl012",
)

print(result["node_output"]["structured"]["text"])  # Extracted text
print(result["node_output"]["structured"]["chunks"])  # Text chunks if enabled
```

**Configuration:**

```python
file_read_config = {
    "max_file_size_mb": 10,  # Maximum file size in MB
    "allowed_extensions": [".pdf", ".png", ".jpg", ".txt"],
    "enable_ocr": True,  # Use OCR for PDFs/images
    "chunk_size": 1000,  # Characters per chunk (0 = no chunking)
    "chunk_overlap": 100,  # Overlap between chunks
}
```

**Behaviour:**

- Validates file exists and is within size limit
- Creates temporary file if base64 provided
- Uses GPT-4o vision API for OCR processing
- Falls back to text reading for plain text files
- Cleans up temporary files automatically
- Handles errors gracefully with detailed messages

---

### `EmailNodeExecutor`

Executor for EMAIL_SEND nodes, sending emails via configured provider.

**Purpose:** Send emails with dynamic field extraction from workflow state, template substitution, and HTML support.

**Responsibilities:**

- Extract email fields (to, from, subject, body) from workflow state
- Apply template variable substitution
- Send email via provider (Mailgun)
- Support HTML and plain text emails
- Track send status in database

**Example:**

```python
from backend.services.nodes.executors import EmailNodeExecutor

executor = EmailNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
)

# Email configured with field mappings
result = await executor.execute(
    node=email_node,
    state=current_state,
    graph=workflow_graph,
    execution_id="exec-mno345",
)

print(result["node_output"]["structured"]["success"])  # True
print(result["node_output"]["structured"]["message_id"])  # Provider message ID
```

**Configuration:**

```python
email_send_config = {
    # Field sources (static or from previous nodes)
    "to_address": "user@example.com",
    "to_source_mode": "static",  # or "specific" for mapping
    "from_address": "noreply@example.com",
    "subject": "Workflow Complete",
    "subject_source_mode": "static",
    "body": "Hello {{user_name}}, your workflow is complete!",
    "body_source_mode": "static",

    # Template variables
    "use_template": True,
    "template_variables": [
        {
            "variable_name": "user_name",
            "source_mode": "specific",
            "source_node_id": "node-123",
            "source_field_path": "output.name",
        }
    ],

    # Email settings
    "is_html": False,
    "provider": "mailgun",
}
```

**Behaviour:**

- Extracts field values from workflow state using `MappingValueExtractor`
- Substitutes template variables like `{{user_name}}` with values from state
- Sends email via configured provider
- Returns success status and provider message ID
- Handles email send failures gracefully

---

### `DatabaseNodeExecutor`

Executor for DATABASE_INSERT nodes, inserting data into databases with column mapping.

**Purpose:** Insert rows into databases with dynamic column value extraction from workflow state.

**Responsibilities:**

- Get database connection details from datasource service
- Build INSERT queries with column mappings
- Extract column values from workflow state
- Execute queries with proper error handling
- Support PostgreSQL databases
- Track execution in database

**Example:**

```python
from backend.services.nodes.executors.database import DatabaseNodeExecutor

executor = DatabaseNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
)

# Database insert configured with column mappings
result = await executor.execute(
    node=db_node,
    state=current_state,
    graph=workflow_graph,
    execution_id="exec-pqr678",
)

print(result["node_output"]["structured"]["rows_inserted"])  # 1
print(result["node_output"]["structured"]["success"])  # True
```

**Configuration:**

```python
database_insert_config = {
    "connection_id": "conn-123",  # Datasource connection ID
    "table_name": "users",
    "column_mappings": [
        {
            "column_name": "email",
            "source_mode": "specific",  # Extract from previous node
            "source_node_id": "node-456",
            "source_field_path": "output.email",
        },
        {
            "column_name": "name",
            "source_mode": "static",  # Static value
            "static_value": "John Doe",
        },
        {
            "column_name": "created_at",
            "source_mode": "expression",  # SQL expression
            "expression": "NOW()",
        },
    ],
}
```

**Architecture:**

The database executor uses a modular architecture with separate services:

- **`DatabaseConnectionManager`**: Get connection details from datasource service
- **`DatabaseQueryBuilder`**: Build INSERT queries with proper SQL escaping
- **`MappingValueExtractor`**: Extract values from workflow state
- **Custom Exceptions**: Specific error types for different failure modes

**Behaviour:**

- Validates connection exists and is accessible
- Builds parameterized SQL query for safety
- Extracts column values from state using mappings
- Executes INSERT query with transaction
- Returns row count and success status
- Throws specific exceptions for different error types

**Internal Services:**

- `_validate_and_parse_config()` - Parse config into `DatabaseInsertConfig`
- `_execute_insert()` - Execute INSERT with connection
- `_create_tracking_record()` - Track in database
- `_complete_tracking()` - Update tracking on completion
- `_build_state_update()` - Build state updates
- `_handle_error()` - Handle errors with notifications

---

## Handler Services

### `NodeDatabaseTracker`

Shared service for tracking node executions in the database.

**Purpose:** Provide reusable methods for creating, updating, and completing node execution records.

**Location:** `backend/services/nodes/handlers/database_tracker.py`

**Initialisation:**

```python
from backend.services.nodes.handlers import NodeDatabaseTracker

tracker = NodeDatabaseTracker(execution_history_service)
# or use default service
tracker = NodeDatabaseTracker()
```

**Key Methods:**

#### `create_node_execution()`

```python
async def create_node_execution(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    node_type: str,
    input_data: Dict[str, Any],
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
) -> Optional[int]:
    """
    Create a node execution record in the database.

    Returns node_exec_id or None if tracking disabled.
    """
```

**Example:**

```python
node_exec_id = await tracker.create_node_execution(
    node=agent_node,
    state=current_state,
    node_type="AGENT",
    input_data={"message": "Hello, agent!"},
    is_sub_agent=False,
    parent_agent_id=None,
)
```

#### `complete_node_execution()`

```python
async def complete_node_execution(
    self,
    node_exec_id: Optional[int],
    output_data: Dict[str, Any],
    token_counts: Optional[Dict[str, int]] = None,
) -> bool:
    """
    Complete a node execution record with output and token counts.

    Returns True if successful, False otherwise.
    """
```

**Example:**

```python
await tracker.complete_node_execution(
    node_exec_id=node_exec_id,
    output_data={"response": "Agent completed successfully"},
    token_counts={
        "input_tokens": 150,
        "output_tokens": 75,
        "total_tokens": 225,
    },
)
```

#### `get_execution_order()`

```python
def get_execution_order(self, state: WorkflowState) -> int:
    """Get current execution order from state."""
```

#### `increment_execution_order()`

```python
def increment_execution_order(self, state: WorkflowState) -> Dict[str, int]:
    """Increment execution order and return update dict."""
```

**Example:**

```python
current_order = tracker.get_execution_order(state)  # 5
order_update = tracker.increment_execution_order(state)
# order_update = {"execution_order": 6}
```

**Use Cases:**

- Track all node executions in execution_history database
- Maintain execution order for UI display
- Store input/output data for debugging
- Track token usage for billing

---

### `NodeNotificationHandler`

Shared service for sending WebSocket notifications during node execution.

**Purpose:** Provide reusable methods for sending start, progress, complete, and error notifications.

**Location:** `backend/services/nodes/handlers/notification_handler.py`

**Initialisation:**

```python
from backend.services.nodes.handlers import NodeNotificationHandler

handler = NodeNotificationHandler(ws_notifier)
# or use default notifier
handler = NodeNotificationHandler()
```

**Key Methods:**

#### `notify_start()`

```python
async def notify_start(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    node_type: str,
    node_exec_id: Optional[int] = None,
    execution_order: Optional[int] = None,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
) -> bool:
    """
    Send WebSocket notification when node starts execution.

    Returns True if successful, False otherwise.
    """
```

**Example:**

```python
await handler.notify_start(
    node=agent_node,
    state=current_state,
    node_type="AGENT",
    node_exec_id=123,
    execution_order=5,
    is_sub_agent=False,
    parent_agent_id=None,
)
```

#### `notify_complete()`

```python
async def notify_complete(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    output: Dict[str, Any],
    node_type: str,
    node_exec_id: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    input_data: Optional[Dict[str, Any]] = None,
    token_counts: Optional[Dict[str, int]] = None,
    execution_order: Optional[int] = None,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
) -> bool:
    """
    Send WebSocket notification when node completes.

    Returns True if successful, False otherwise.
    """
```

**Example:**

```python
await handler.notify_complete(
    node=agent_node,
    state=current_state,
    output={"response": "Complete!"},
    node_type="AGENT",
    node_exec_id=123,
    duration_seconds=2.5,
    token_counts={"total_tokens": 225},
    execution_order=5,
)
```

#### `notify_error()`

```python
async def notify_error(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    error_message: str,
    node_type: str,
) -> bool:
    """
    Send WebSocket notification when node fails.

    Returns True if successful, False otherwise.
    """
```

**Example:**

```python
await handler.notify_error(
    node=agent_node,
    state=current_state,
    error_message="Agent execution failed: timeout",
    node_type="AGENT",
)
```

**Use Cases:**

- Real-time UI updates during workflow execution
- Show node progress in execution timeline
- Display errors immediately to users
- Track execution state across WebSocket connection

---

## Configuration

### Initialisation Patterns

#### Basic Executor Initialisation

```python
from backend.services.nodes.executors import AgentNodeExecutor

# Create executor with dependencies
executor = AgentNodeExecutor(
    execution_history_service=execution_service,
    ws_notifier=ws_notifier,
    graph_manager=graph_manager,
)

# Execute node
result = await executor.execute(node, state, graph, execution_id)
```

#### Registry-Based Initialisation

```python
from backend.services.nodes import NodeExecutorRegistry
from backend.models.workflow import NodeType

# Register executors
NodeExecutorRegistry.register(NodeType.AGENT, AgentNodeExecutor)
NodeExecutorRegistry.register(NodeType.HTTP_REQUEST, HttpNodeExecutor)

# Get executor dynamically
executor = NodeExecutorRegistry.get_executor(
    node.type,
    dependencies={
        "execution_history_service": service,
        "ws_notifier": notifier,
        "graph_manager": manager,
    }
)

# Execute
result = await executor.execute(node, state, graph, execution_id)
```

#### Factory-Based Initialisation

```python
from backend.services.nodes import NodeExecutorRegistry
from backend.models.workflow import NodeType

# Create factory function with dependency injection
def create_agent_executor():
    return AgentNodeExecutor(
        execution_history_service=get_execution_service(),
        ws_notifier=get_ws_notifier(),
        graph_manager=get_graph_manager(),
    )

# Register factory
NodeExecutorRegistry.register(
    NodeType.AGENT,
    factory=create_agent_executor
)

# Get cached instance
executor = NodeExecutorRegistry.get_executor(NodeType.AGENT)
```

### Environment Variables

No environment variables required. All configuration is embedded in node definitions.

### Node-Specific Configuration

Each node type has its own configuration structure:

**Agent Node:**

```python
node.agent_config = {
    "agent_name": "MyAgent",
    "model": "gpt-4",
    "temperature": 0.7,
    "memory_enabled": True,
    "system_prompt": "You are a helpful assistant",
}
```

**HTTP Request Node:**

```python
node.http_request_action_config = {
    "url_template": "https://api.example.com/users/{user_id}",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "auth_type": "bearer",
    "auth_config": {"token": "secret-token"},
    "url_param_mappings": [...],
    "query_param_mappings": [...],
    "body_mappings": [...],
}
```

**Database Insert Node:**

```python
node.database_insert_config = {
    "connection_id": "conn-123",
    "table_name": "users",
    "column_mappings": [
        {
            "column_name": "email",
            "source_mode": "specific",
            "source_node_id": "node-456",
            "source_field_path": "output.email",
        }
    ],
}
```

---

## Error Handling

### Exception Hierarchy

**Database Executor Exceptions:**

```
Exception
└── DatabaseNodeError (base exception for database errors)
    ├── DatabaseConnectionError    # Connection failures
    ├── QueryBuildError            # Query construction errors
    ├── QueryExecutionError        # Query execution errors
    └── ConfigurationError         # Invalid configuration
```

### Exception Details

#### `DatabaseNodeError`

Base exception for all database node errors.

**Inherits from:** `Exception`

**When raised:**

- Any database node operation failure

**Example:**

```python
from backend.services.nodes.executors.database import DatabaseNodeError

try:
    result = await db_executor.execute(node, state, graph, exec_id)
except DatabaseNodeError as e:
    logger.error(f"Database operation failed: {e}")
    # Handle database-specific errors
```

#### `DatabaseConnectionError`

Failed to connect to database.

**Inherits from:** `DatabaseNodeError`

**When raised:**

- Connection details are invalid
- Database server is unreachable
- Authentication fails
- SSL/TLS connection fails

**Attributes:**

- `connection_id: str` - ID of the failed connection

**Example:**

```python
from backend.services.nodes.executors.database import DatabaseConnectionError

try:
    connection = manager.get_connection(connection_id)
except DatabaseConnectionError as e:
    logger.error(f"Connection {e.connection_id} failed: {e}")
    # Notify user to check connection settings
```

#### `QueryBuildError`

Failed to build database query.

**Inherits from:** `DatabaseNodeError`

**When raised:**

- Query configuration is invalid
- Column mappings are malformed
- Value extraction fails
- SQL syntax errors in expressions

**Attributes:**

- `table_name: str` - Table for the failed query

**Example:**

```python
from backend.services.nodes.executors.database import QueryBuildError

try:
    query, values = builder.build_insert_query(config, state)
except QueryBuildError as e:
    logger.error(f"Query build failed for {e.table_name}: {e}")
    # Show configuration error to user
```

#### `QueryExecutionError`

Failed to execute database query.

**Inherits from:** `DatabaseNodeError`

**When raised:**

- Query syntax is invalid
- Constraint violations occur (unique, foreign key, etc.)
- Data type mismatches
- Permission issues

**Attributes:**

- `query: str` - The SQL query that failed

**Example:**

```python
from backend.services.nodes.executors.database import QueryExecutionError

try:
    cursor.execute(query, values)
except QueryExecutionError as e:
    logger.error(f"Query execution failed: {e}")
    # Show query error to user (with truncated query)
```

#### `ConfigurationError`

Invalid database node configuration.

**Inherits from:** `DatabaseNodeError`

**When raised:**

- Required configuration fields are missing
- Configuration values are invalid
- Configuration format is incorrect

**Attributes:**

- `field_name: str` - Name of the invalid field

**Example:**

```python
from backend.services.nodes.executors.database import ConfigurationError

try:
    config = DatabaseInsertConfig.from_node_config(node_config)
except ConfigurationError as e:
    logger.error(f"Invalid config field '{e.field_name}': {e}")
    # Guide user to fix configuration
```

### Error Handling Patterns

#### Executor-Level Error Handling

```python
from backend.services.nodes.executors import AgentNodeExecutor

executor = AgentNodeExecutor(
    execution_history_service=service,
    ws_notifier=notifier,
    graph_manager=manager,
)

try:
    result = await executor.execute(node, state, graph, execution_id)
except Exception as e:
    # Executor handles errors internally and returns error state
    # Error notification sent via WebSocket
    # Error logged with context
    logger.error(f"Node execution failed: {e}", exc_info=True)
```

**Behaviour:**

- Executors catch all exceptions internally
- Return error state instead of raising
- Send error WebSocket notification
- Log error with full context
- Update database tracking with error status

#### Database-Specific Error Handling

```python
from backend.services.nodes.executors.database import (
    DatabaseNodeExecutor,
    DatabaseConnectionError,
    QueryExecutionError,
    ConfigurationError,
)

executor = DatabaseNodeExecutor(
    execution_history_service=service,
    ws_notifier=notifier,
)

try:
    result = await executor.execute(node, state, graph, execution_id)
except ConfigurationError as e:
    # Configuration issue - guide user to fix config
    return {
        "error": f"Configuration error: {e}",
        "error_type": "configuration",
        "field": e.field_name,
    }
except DatabaseConnectionError as e:
    # Connection issue - guide user to check connection
    return {
        "error": f"Connection failed: {e}",
        "error_type": "connection",
        "connection_id": e.connection_id,
    }
except QueryExecutionError as e:
    # Query issue - show query error
    return {
        "error": f"Query failed: {e}",
        "error_type": "execution",
        "query": e.query[:100],
    }
```

#### Workflow-Level Error Handling

```python
from backend.services.nodes import NodeExecutorRegistry
from backend.models.workflow import NodeType

# Get executor for node
executor = NodeExecutorRegistry.get_executor(
    node.type,
    dependencies=deps,
)

# Execute with error handling
result = await executor.execute(node, state, graph, execution_id)

# Check for errors in result
if "error" in result.get("node_output", {}).get("structured", {}):
    error_msg = result["node_output"]["structured"]["error"]
    logger.error(f"Node {node.name} failed: {error_msg}")

    # Workflow can decide to:
    # - Continue with error state
    # - Stop execution
    # - Route to error handling node
```

---

## Integration Patterns

### Integration with Execution Layer

The nodes service integrates with the execution engine:

```python
# From backend/services/execution/workflow_executor.py

from backend.services.nodes import NodeExecutorRegistry

class WorkflowExecutor:
    async def execute_node(self, node, state):
        """Execute a single node using registered executor."""

        # Get appropriate executor for node type
        executor = NodeExecutorRegistry.get_executor(
            node.type,
            dependencies={
                "execution_history_service": self.execution_history_service,
                "ws_notifier": self.ws_notifier,
                "graph_manager": self.graph_manager,
            }
        )

        # Execute node
        result = await executor.execute(
            node=node,
            state=state,
            graph=self.graph,
            execution_id=self.execution_id,
            user_id=self.user_id,
        )

        # Apply state updates
        state.update(result)

        return result
```

### Integration with API Layer

API endpoints use executors for ad-hoc execution:

```python
# From backend/api/nodes/routes.py

from fastapi import APIRouter, Depends
from backend.services.nodes.executors import AgentNodeExecutor

router = APIRouter()

@router.post("/nodes/agent/execute")
async def execute_agent_node(
    request: AgentExecuteRequest,
    executor: AgentNodeExecutor = Depends(get_agent_executor),
):
    """Execute an agent node directly via API."""

    # Build state from request
    state = {
        "execution_id": generate_execution_id(),
        "db_execution_id": request.execution_id,
        "node_outputs": request.previous_outputs,
    }

    # Execute
    result = await executor.execute(
        node=request.node,
        state=state,
        graph=request.graph,
        execution_id=state["execution_id"],
    )

    return {
        "success": True,
        "output": result["node_output"],
    }
```

### Integration with Graph Manager

Agent executors delegate to graph manager:

```python
# From backend/services/nodes/executors/agent.py

class AgentNodeExecutor(BaseNodeExecutor):
    async def _execute_agent_logic(self, node, input_message, state, graph):
        """Execute agent using graph manager."""

        tool_execution_tracker = []

        # Use graph manager's async execution
        result = await self.graph_manager.execute_agent_async(
            node,
            input_message,
            tool_execution_tracker=tool_execution_tracker,
            db_execution_id=state.get("db_execution_id"),
            return_token_counts=True,
            graph_name=graph.name if hasattr(graph, 'name') else None,
        )

        return result, tool_execution_tracker
```

### Dependency Flow

```
┌─────────────────────┐
│   API Layer         │
│   /execute endpoint │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ WorkflowExecutor    │
│ (execution service) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│ NodeExecutorRegistry        │
│ .get_executor(node.type)    │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Concrete Executor           │
│ AgentNodeExecutor           │
│ HttpNodeExecutor            │
│ DatabaseNodeExecutor        │
└──────────┬──────────────────┘
           │
           ├────────────┬────────────┬─────────────┐
           ▼            ▼            ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Database │ │   WS     │ │  Graph   │ │  Memory  │
    │ Tracker  │ │ Notifier │ │ Manager  │ │ Manager  │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Common Integration Patterns

#### Pattern 1: Executor Registration at Startup

```python
# From backend/main.py or app initialization

from backend.services.nodes import NodeExecutorRegistry
from backend.services.nodes.executors import (
    AgentNodeExecutor,
    HttpNodeExecutor,
    ConditionNodeExecutor,
    FileNodeExecutor,
    EmailNodeExecutor,
    DatabaseNodeExecutor,
)
from backend.models.workflow import NodeType

def register_executors():
    """Register all node executors at application startup."""

    # Use factory pattern for shared dependencies
    def create_agent_executor():
        return AgentNodeExecutor(
            execution_history_service=get_execution_service(),
            ws_notifier=get_ws_notifier(),
            graph_manager=get_graph_manager(),
        )

    def create_http_executor():
        return HttpNodeExecutor(
            execution_history_service=get_execution_service(),
            ws_notifier=get_ws_notifier(),
        )

    # Register factories (singleton per type)
    NodeExecutorRegistry.register(NodeType.AGENT, factory=create_agent_executor)
    NodeExecutorRegistry.register(NodeType.HTTP_REQUEST, factory=create_http_executor)
    NodeExecutorRegistry.register(NodeType.CONDITION, factory=create_condition_executor)
    NodeExecutorRegistry.register(NodeType.FILE_READ, factory=create_file_executor)
    NodeExecutorRegistry.register(NodeType.EMAIL_SEND, factory=create_email_executor)
    NodeExecutorRegistry.register(NodeType.DATABASE_INSERT, factory=create_database_executor)

# Call at startup
@app.on_event("startup")
async def startup():
    register_executors()
```

#### Pattern 2: Dynamic Executor Creation

```python
# For one-off execution or testing

from backend.services.nodes.executors import AgentNodeExecutor

async def execute_single_agent(node, state):
    """Execute a single agent node with custom dependencies."""

    executor = AgentNodeExecutor(
        execution_history_service=custom_service,
        ws_notifier=custom_notifier,
        graph_manager=custom_manager,
    )

    result = await executor.execute(
        node=node,
        state=state,
        graph=None,
        execution_id=generate_id(),
    )

    return result
```

#### Pattern 3: Executor Testing

```python
# Unit test with mock dependencies

import pytest
from unittest.mock import Mock, AsyncMock
from backend.services.nodes.executors import AgentNodeExecutor

@pytest.fixture
def mock_dependencies():
    return {
        "execution_history_service": Mock(),
        "ws_notifier": AsyncMock(),
        "graph_manager": AsyncMock(),
    }

async def test_agent_executor(mock_dependencies):
    """Test agent executor with mocked dependencies."""

    executor = AgentNodeExecutor(**mock_dependencies)

    # Mock graph_manager response
    mock_dependencies["graph_manager"].execute_agent_async.return_value = (
        "Agent response",
        {"total_tokens": 100},
        []  # tool_executions
    )

    result = await executor.execute(
        node=test_node,
        state=test_state,
        graph=test_graph,
        execution_id="test-123",
    )

    assert result["node_output"]["raw"] == "Agent response"
    assert mock_dependencies["ws_notifier"].on_node_start.called
```

---

## Usage Examples

### Example 1: Basic Agent Execution

Complete end-to-end example of executing an agent node:

```python
from backend.services.nodes.executors import AgentNodeExecutor
from backend.services.execution.history import ExecutionHistoryService
from backend.services.websocket import notifier as ws_notifier
from backend.services.graph import get_graph_manager
from backend.models.workflow import EnhancedNodeData, AgentConfig

# Step 1: Create agent node
agent_node = EnhancedNodeData(
    uniq_id="agent-abc123",
    name="Customer Service Agent",
    type="AGENT",
    agent_config=AgentConfig(
        agent_name="CustomerServiceBot",
        model="gpt-4",
        temperature=0.7,
        memory_enabled=True,
        system_prompt="You are a helpful customer service assistant.",
    ),
)

# Step 2: Initialize executor
executor = AgentNodeExecutor(
    execution_history_service=ExecutionHistoryService,
    ws_notifier=ws_notifier,
    graph_manager=get_graph_manager(),
)

# Step 3: Prepare state
state = {
    "execution_id": "exec-def456",
    "db_execution_id": 789,
    "execution_order": 0,
    "node_outputs": {},
    "message": "How do I reset my password?",
}

# Step 4: Execute
result = await executor.execute(
    node=agent_node,
    state=state,
    graph=workflow_graph,
    execution_id=state["execution_id"],
    user_id="user-123",
)

# Step 5: Process result
print(f"Agent response: {result['node_output']['raw']}")
print(f"Token usage: {result['node_output']['token_counts']}")
print(f"Tools used: {result['node_output'].get('tool_executions', [])}")

# Output:
# Agent response: To reset your password, go to Settings > Security > Reset Password...
# Token usage: {'input_tokens': 150, 'output_tokens': 75, 'total_tokens': 225}
# Tools used: []
```

### Example 2: HTTP Request with Dynamic Parameters

Complete example showing HTTP request with parameter mapping:

```python
from backend.services.nodes.executors import HttpNodeExecutor
from backend.models.workflow import EnhancedNodeData, HttpRequestActionConfig

# Step 1: Create HTTP request node with configuration
http_node = EnhancedNodeData(
    uniq_id="http-xyz789",
    name="Fetch User Data",
    type="HTTP_REQUEST",
    http_request_action_config=HttpRequestActionConfig(
        url_template="https://api.example.com/users/{user_id}",
        method="GET",
        headers={"Accept": "application/json"},
        auth_type="bearer",
        auth_config={"token": "secret-token-123"},
        url_param_mappings=[
            {
                "parameter_name": "user_id",
                "source_mode": "specific",
                "source_node_id": "agent-abc123",
                "source_field_path": "output.user_id",
            }
        ],
        query_param_mappings=[
            {
                "parameter_name": "include_profile",
                "source_mode": "static",
                "static_value": "true",
            }
        ],
        response_path="data.user",
        success_status_codes=[200],
        max_retries=3,
        timeout_seconds=30,
    ),
)

# Step 2: Initialize executor
executor = HttpNodeExecutor(
    execution_history_service=ExecutionHistoryService,
    ws_notifier=ws_notifier,
)

# Step 3: Prepare state with previous node output
state = {
    "execution_id": "exec-ghi789",
    "db_execution_id": 790,
    "execution_order": 1,
    "node_outputs": {
        "agent-abc123": {
            "output": {"user_id": "12345"}
        }
    },
}

# Step 4: Execute
result = await executor.execute(
    node=http_node,
    state=state,
    graph=workflow_graph,
    execution_id=state["execution_id"],
)

# Step 5: Access result
print(f"Status: {result['node_output']['structured']['status_code']}")
print(f"User data: {result['node_output']['structured']['data']}")

# Output:
# Status: 200
# User data: {'id': '12345', 'name': 'John Doe', 'email': 'john@example.com'}
```

### Example 3: Database Insert with Column Mapping

Complete example showing database insertion:

```python
from backend.services.nodes.executors.database import DatabaseNodeExecutor
from backend.models.workflow import EnhancedNodeData, DatabaseInsertConfig

# Step 1: Create database insert node
db_node = EnhancedNodeData(
    uniq_id="db-insert-123",
    name="Save User to Database",
    type="DATABASE_INSERT",
    database_insert_config=DatabaseInsertConfig(
        connection_id="postgres-conn-456",
        table_name="users",
        column_mappings=[
            {
                "column_name": "email",
                "source_mode": "specific",
                "source_node_id": "http-xyz789",
                "source_field_path": "data.email",
            },
            {
                "column_name": "name",
                "source_mode": "specific",
                "source_node_id": "http-xyz789",
                "source_field_path": "data.name",
            },
            {
                "column_name": "created_at",
                "source_mode": "expression",
                "expression": "NOW()",
            },
            {
                "column_name": "status",
                "source_mode": "static",
                "static_value": "active",
            },
        ],
    ),
)

# Step 2: Initialize executor
executor = DatabaseNodeExecutor(
    execution_history_service=ExecutionHistoryService,
    ws_notifier=ws_notifier,
)

# Step 3: Prepare state with previous outputs
state = {
    "execution_id": "exec-jkl012",
    "db_execution_id": 791,
    "execution_order": 2,
    "node_outputs": {
        "http-xyz789": {
            "data": {
                "email": "john@example.com",
                "name": "John Doe",
            }
        }
    },
}

# Step 4: Execute
result = await executor.execute(
    node=db_node,
    state=state,
    graph=workflow_graph,
    execution_id=state["execution_id"],
)

# Step 5: Check result
print(f"Success: {result['node_output']['structured']['success']}")
print(f"Rows inserted: {result['node_output']['structured']['rows_inserted']}")

# Output:
# Success: True
# Rows inserted: 1
```

### Example 4: Registry-Based Workflow Execution

Complete workflow using executor registry:

```python
from backend.services.nodes import NodeExecutorRegistry
from backend.models.workflow import NodeType

async def execute_workflow_nodes(graph, state):
    """
    Execute all nodes in a workflow using the registry.

    This example shows how the execution engine uses the registry
    to dynamically select and execute different node types.
    """

    # Common dependencies for all executors
    dependencies = {
        "execution_history_service": ExecutionHistoryService,
        "ws_notifier": ws_notifier,
        "graph_manager": get_graph_manager(),
    }

    # Execute each node in sequence
    for node in graph.nodes:
        print(f"Executing {node.type} node: {node.name}")

        # Get appropriate executor for this node type
        executor = NodeExecutorRegistry.get_executor(
            node.type,
            dependencies=dependencies,
        )

        # Execute node
        result = await executor.execute(
            node=node,
            state=state,
            graph=graph,
            execution_id=state["execution_id"],
        )

        # Update state with result
        state.update(result)
        state["node_outputs"][node.uniq_id] = result["node_output"]

        print(f"✓ Completed {node.name}")
        print(f"  Output: {result['node_output']['raw'][:100]}...")

    return state

# Example workflow with multiple node types
workflow_graph = Graph(
    name="User Onboarding",
    nodes=[
        agent_node,      # AGENT: Welcome user
        http_node,       # HTTP_REQUEST: Fetch user profile
        condition_node,  # CONDITION: Check if premium
        email_node,      # EMAIL_SEND: Send welcome email
        db_node,         # DATABASE_INSERT: Save to database
    ],
)

# Execute workflow
initial_state = {
    "execution_id": "exec-workflow-001",
    "db_execution_id": 100,
    "execution_order": 0,
    "node_outputs": {},
    "message": "Welcome new user!",
}

final_state = await execute_workflow_nodes(workflow_graph, initial_state)

print(f"\nWorkflow complete! Executed {final_state['execution_order']} nodes")
```

### Example 5: Testing Node Executors

Show how to test executors with mocked dependencies:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.nodes.executors import AgentNodeExecutor
from backend.models.workflow import EnhancedNodeData, AgentConfig

@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for testing."""
    return {
        "execution_history_service": Mock(),
        "ws_notifier": AsyncMock(),
        "graph_manager": AsyncMock(),
    }

@pytest.fixture
def test_node():
    """Create test agent node."""
    return EnhancedNodeData(
        uniq_id="test-agent",
        name="Test Agent",
        type="AGENT",
        agent_config=AgentConfig(
            agent_name="TestBot",
            model="gpt-4",
            temperature=0.7,
            memory_enabled=False,
        ),
    )

@pytest.fixture
def test_state():
    """Create test state."""
    return {
        "execution_id": "test-exec",
        "db_execution_id": 999,
        "execution_order": 0,
        "node_outputs": {},
        "message": "Test message",
    }

async def test_agent_executor_success(mock_dependencies, test_node, test_state):
    """Test successful agent execution."""

    # Setup mock graph manager response
    mock_dependencies["graph_manager"].execute_agent_async = AsyncMock(
        return_value=(
            "Agent response here",
            {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            []  # tool_executions
        )
    )

    # Create executor
    executor = AgentNodeExecutor(**mock_dependencies)

    # Execute
    result = await executor.execute(
        node=test_node,
        state=test_state,
        graph=None,
        execution_id="test-exec",
    )

    # Verify result
    assert result["node_output"]["raw"] == "Agent response here"
    assert result["node_output"]["token_counts"]["total_tokens"] == 75

    # Verify WebSocket notifications sent
    assert mock_dependencies["ws_notifier"].on_node_start.called
    assert mock_dependencies["ws_notifier"].on_node_complete.called

async def test_agent_executor_with_tools(mock_dependencies, test_node, test_state):
    """Test agent execution with tool calls."""

    # Mock response with tool executions
    tool_executions = [
        {
            "tool_name": "web_search",
            "tool_input": {"query": "Python tutorial"},
            "tool_output": "Found 10 results",
        }
    ]

    mock_dependencies["graph_manager"].execute_agent_async = AsyncMock(
        return_value=(
            "Based on my search, here are the results...",
            {"total_tokens": 150},
            tool_executions
        )
    )

    executor = AgentNodeExecutor(**mock_dependencies)
    result = await executor.execute(
        node=test_node,
        state=test_state,
        graph=Mock(),
        execution_id="test-exec",
    )

    # Verify tool executions tracked
    assert "tool_executions" in result["node_output"]
    assert len(result["node_output"]["tool_executions"]) == 1
    assert result["node_output"]["tool_executions"][0]["tool_name"] == "web_search"

async def test_agent_executor_error_handling(mock_dependencies, test_node, test_state):
    """Test agent executor error handling."""

    # Mock graph manager to raise error
    mock_dependencies["graph_manager"].execute_agent_async = AsyncMock(
        side_effect=Exception("Agent execution failed")
    )

    executor = AgentNodeExecutor(**mock_dependencies)
    result = await executor.execute(
        node=test_node,
        state=test_state,
        graph=None,
        execution_id="test-exec",
    )

    # Verify error state returned
    assert "error" in result["node_output"]["structured"]
    assert "Agent execution failed" in result["node_output"]["raw"]

    # Verify error notification sent
    assert mock_dependencies["ws_notifier"].on_node_error.called
```

---

## Performance Considerations

### Performance Characteristics

**Executor Overhead:**

- Executor instantiation: O(1) - lightweight, minimal overhead
- Registry lookup: O(1) - dictionary lookup
- State updates: O(1) - simple dict operations

**Node Type Performance:**

| Node Type       | Complexity     | I/O Bound | Notes                                |
|-----------------|----------------|-----------|--------------------------------------|
| AGENT           | O(n) tokens    | Yes       | Network calls to LLM, tool execution |
| HTTP_REQUEST    | O(1)           | Yes       | Network latency, retry backoff       |
| CONDITION       | O(1)           | No        | CPU-bound expression evaluation      |
| FILE_READ       | O(n) file size | Yes       | Disk I/O, OCR processing             |
| EMAIL_SEND      | O(1)           | Yes       | Network call to email provider       |
| DATABASE_INSERT | O(n) rows      | Yes       | Database connection, query execution |

**Memory Usage:**

- Executor instances: ~1-2 KB per instance
- State dictionary: Proportional to node outputs
- Large responses (file content, HTTP bodies) can be 1-10 MB

### Optimisation Tips

#### Tip 1: Use Factory Registration for Shared Dependencies

**Problem:**

```python
# Creating new instances for each execution
for node in nodes:
    executor = AgentNodeExecutor(
        execution_history_service=service,  # Created each time
        ws_notifier=notifier,
        graph_manager=manager,
    )
    await executor.execute(node, state, graph, exec_id)
```

**Solution:**

```python
# Register factory once at startup
def create_agent_executor():
    return AgentNodeExecutor(
        execution_history_service=get_execution_service(),
        ws_notifier=get_ws_notifier(),
        graph_manager=get_graph_manager(),
    )

NodeExecutorRegistry.register(NodeType.AGENT, factory=create_agent_executor)

# Reuse cached instance
for node in nodes:
    executor = NodeExecutorRegistry.get_executor(node.type)  # Singleton
    await executor.execute(node, state, graph, exec_id)
```

**Benefit:** Reduces object creation overhead, shares dependencies

#### Tip 2: Parallel Node Execution

For independent nodes (no data dependencies), execute in parallel:

```python
import asyncio
from backend.services.nodes import NodeExecutorRegistry

async def execute_nodes_parallel(nodes, state, graph, execution_id):
    """Execute independent nodes in parallel."""

    dependencies = {...}

    async def execute_one(node):
        executor = NodeExecutorRegistry.get_executor(node.type, dependencies)
        return await executor.execute(node, state, graph, execution_id)

    # Execute all nodes concurrently
    results = await asyncio.gather(*[execute_one(node) for node in nodes])

    return results

# Use for independent nodes
parallel_nodes = [email_node, slack_notification_node, log_node]
results = await execute_nodes_parallel(parallel_nodes, state, graph, exec_id)
```

**Benefit:** Reduces total execution time for I/O-bound operations

#### Tip 3: Optimize State Size

**Problem:**

```python
# Storing large responses in state
state["node_outputs"][node.uniq_id] = {
    "raw": large_file_content,  # 10 MB file
    "structured": {...},
    "fields": {...},
}
```

**Solution:**

```python
# Store reference or summary instead
state["node_outputs"][node.uniq_id] = {
    "raw": file_summary,  # Just metadata
    "structured": {"file_path": "/tmp/upload.pdf", "size_bytes": 10485760},
    "fields": {"file_id": "file-123"},
}

# Access full content only when needed
if need_full_content:
    content = read_file(state["node_outputs"][node.uniq_id]["structured"]["file_path"])
```

**Benefit:** Reduces memory usage, faster state serialization

### Async/Await Support

All executors are fully async:

```python
from backend.services.nodes.executors import AgentNodeExecutor

async def my_async_workflow():
    executor = AgentNodeExecutor(...)

    # All execute methods are async
    result = await executor.execute(node, state, graph, exec_id)

    return result

# Run with asyncio
import asyncio
asyncio.run(my_async_workflow())
```

**Concurrency Benefits:**

- Non-blocking I/O for HTTP requests, database operations
- Can handle multiple workflow executions concurrently
- WebSocket notifications don't block execution

### Batch Operations

Database executor can be extended for batch inserts:

```python
# Future enhancement: batch insert support
result = await db_executor.execute_batch(
    nodes=[db_node1, db_node2, db_node3],
    states=[state1, state2, state3],
    graph=graph,
    execution_id=exec_id,
)
```

---

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock
from backend.services.nodes.executors import HttpNodeExecutor

@pytest.fixture
def http_executor():
    """Create HTTP executor with mocked dependencies."""
    return HttpNodeExecutor(
        execution_history_service=Mock(),
        ws_notifier=AsyncMock(),
    )

@pytest.fixture
def http_node():
    """Create test HTTP node."""
    return EnhancedNodeData(
        uniq_id="test-http",
        name="Test HTTP Request",
        type="HTTP_REQUEST",
        http_request_action_config=HttpRequestActionConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={},
            auth_type="none",
            max_retries=1,
            timeout_seconds=5,
            success_status_codes=[200],
        ),
    )

async def test_http_executor_success(http_executor, http_node):
    """Test successful HTTP request."""

    state = {"execution_id": "test", "db_execution_id": 1, "execution_order": 0}

    with patch('requests.request') as mock_request:
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response

        result = await http_executor.execute(
            node=http_node,
            state=state,
            graph=None,
            execution_id="test",
        )

        assert result["node_output"]["structured"]["success"] is True
        assert result["node_output"]["structured"]["status_code"] == 200
        assert result["node_output"]["structured"]["data"] == {"data": "test"}

async def test_http_executor_retry(http_executor, http_node):
    """Test HTTP request retry logic."""

    state = {"execution_id": "test", "db_execution_id": 1, "execution_order": 0}

    with patch('requests.request') as mock_request:
        # Mock timeout on first attempt, success on second
        mock_request.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            Mock(status_code=200, json=lambda: {"data": "test"}),
        ]

        result = await http_executor.execute(
            node=http_node,
            state=state,
            graph=None,
            execution_id="test",
        )

        # Should succeed after retry
        assert result["node_output"]["structured"]["success"] is True
        assert mock_request.call_count == 2  # First attempt + 1 retry
```

### Mocking Dependencies

```python
from unittest.mock import Mock, AsyncMock, patch
import pytest

@pytest.fixture
def mock_execution_service():
    """Mock execution history service."""
    service = Mock()
    service.create_node_execution.return_value = {"id": 123}
    service.start_node_execution.return_value = None
    service.complete_node_execution.return_value = None
    return service

@pytest.fixture
def mock_ws_notifier():
    """Mock WebSocket notifier."""
    notifier = AsyncMock()
    notifier.on_node_start.return_value = None
    notifier.on_node_complete.return_value = None
    notifier.on_node_error.return_value = None
    return notifier

@pytest.fixture
def mock_graph_manager():
    """Mock graph manager."""
    manager = AsyncMock()
    manager.execute_agent_async.return_value = (
        "Test response",
        {"total_tokens": 100},
        []  # tool_executions
    )
    return manager

async def test_with_mocked_dependencies(
    mock_execution_service,
    mock_ws_notifier,
    mock_graph_manager,
):
    """Test executor with all mocked dependencies."""

    executor = AgentNodeExecutor(
        execution_history_service=mock_execution_service,
        ws_notifier=mock_ws_notifier,
        graph_manager=mock_graph_manager,
    )

    result = await executor.execute(test_node, test_state, test_graph, "test-exec")

    # Verify all dependencies called
    assert mock_execution_service.create_node_execution.called
    assert mock_ws_notifier.on_node_start.called
    assert mock_graph_manager.execute_agent_async.called
```

### Integration Testing

```python
@pytest.mark.integration
async def test_agent_executor_integration():
    """Integration test with real dependencies."""

    # Use real services (not mocks)
    from backend.services.execution.history import ExecutionHistoryService
    from backend.services.websocket import notifier
    from backend.services.graph import get_graph_manager

    executor = AgentNodeExecutor(
        execution_history_service=ExecutionHistoryService,
        ws_notifier=notifier,
        graph_manager=get_graph_manager(),
    )

    # Create real test data in database
    db_execution = create_test_execution()

    state = {
        "execution_id": "integration-test",
        "db_execution_id": db_execution.id,
        "execution_order": 0,
        "node_outputs": {},
        "message": "Test integration",
    }

    # Execute with real agent
    result = await executor.execute(
        node=real_agent_node,
        state=state,
        graph=real_graph,
        execution_id=state["execution_id"],
    )

    # Verify database was updated
    node_exec = ExecutionHistoryService.get_node_execution(...)
    assert node_exec.status == "completed"
    assert node_exec.output_data is not None

    # Clean up test data
    cleanup_test_execution(db_execution.id)
```

---

## Best Practices

### Do's

✅ **Always use the registry for executor selection in production**

```python
# Good: Dynamic selection, easy to extend
executor = NodeExecutorRegistry.get_executor(node.type, dependencies)
result = await executor.execute(node, state, graph, exec_id)
```

✅ **Register executors with factories for dependency injection**

```python
# Good: Singleton pattern, shared dependencies
def create_agent_executor():
    return AgentNodeExecutor(
        execution_history_service=get_execution_service(),
        ws_notifier=get_ws_notifier(),
        graph_manager=get_graph_manager(),
    )

NodeExecutorRegistry.register(NodeType.AGENT, factory=create_agent_executor)
```

✅ **Always send WebSocket notifications for UI responsiveness**

```python
# Good: User sees real-time progress
async def execute(self, node, state, graph, execution_id, user_id=None):
    await self.notification_handler.notify_start(node, state, "AGENT")

    try:
        result = await self._do_work(node, state)
        await self.notification_handler.notify_complete(node, state, result, "AGENT")
        return result
    except Exception as e:
        await self.notification_handler.notify_error(node, state, str(e), "AGENT")
        raise
```

✅ **Track all executions in database for debugging and auditing**

```python
# Good: Full audit trail
node_exec_id = await self.database_tracker.create_node_execution(
    node, state, "AGENT", input_data
)
# ... execute ...
await self.database_tracker.complete_node_execution(
    node_exec_id, output_data, token_counts
)
```

✅ **Handle errors gracefully and return error state instead of crashing**

```python
# Good: Workflow continues with error state
try:
    result = await self._execute_node_logic(node, state)
    return self._build_state_update(result)
except Exception as e:
    logger.error(f"Node execution failed: {e}", exc_info=True)
    return self._build_error_state(e)
```

✅ **Use handlers (NodeDatabaseTracker, NodeNotificationHandler) for shared functionality**

```python
# Good: Reusable, consistent behavior
self.database_tracker = NodeDatabaseTracker(execution_history_service)
self.notification_handler = NodeNotificationHandler(ws_notifier)

# Use in execute method
await self.database_tracker.create_node_execution(...)
await self.notification_handler.notify_start(...)
```

### Don'ts

❌ **Don't hardcode executor selection with if/elif chains**

```python
# Bad: Hard to maintain, not extensible
if node.type == "AGENT":
    executor = AgentNodeExecutor(...)
elif node.type == "HTTP_REQUEST":
    executor = HttpNodeExecutor(...)
elif node.type == "DATABASE_INSERT":
    executor = DatabaseNodeExecutor(...)
# ... 20 more elif statements

# Good: Use registry
executor = NodeExecutorRegistry.get_executor(node.type, dependencies)
```

**Why:** Registry pattern is extensible, maintainable, testable.

❌ **Don't create new executor instances for each execution**

```python
# Bad: Creates new instances repeatedly
for node in nodes:
    executor = AgentNodeExecutor(service, notifier, manager)  # New instance each time
    await executor.execute(node, state, graph, exec_id)

# Good: Reuse cached instances
for node in nodes:
    executor = NodeExecutorRegistry.get_executor(node.type)  # Singleton
    await executor.execute(node, state, graph, exec_id)
```

**Why:** Reduces object creation overhead, shares dependencies.

❌ **Don't skip database tracking or notifications**

```python
# Bad: No tracking, no UI updates
async def execute(self, node, state, graph, execution_id, user_id=None):
    result = await self._do_work(node, state)
    return {"node_output": result}

# Good: Full tracking and notifications
async def execute(self, node, state, graph, execution_id, user_id=None):
    node_exec_id = await self.database_tracker.create_node_execution(...)
    await self.notification_handler.notify_start(...)
    result = await self._do_work(node, state)
    await self.database_tracker.complete_node_execution(...)
    await self.notification_handler.notify_complete(...)
    return {"node_output": result}
```

**Why:** Tracking enables debugging, auditing; notifications enable real-time UI.

❌ **Don't raise exceptions from execute() method**

```python
# Bad: Crashes workflow
async def execute(self, node, state, graph, execution_id, user_id=None):
    if not self._validate(node):
        raise ValueError("Invalid configuration")  # Crashes workflow
    # ...

# Good: Return error state
async def execute(self, node, state, graph, execution_id, user_id=None):
    if not self._validate(node):
        return self._build_error_state("Invalid configuration")  # Workflow continues
    # ...
```

**Why:** Workflows should handle errors gracefully and continue when possible.

❌ **Don't mix business logic with infrastructure concerns**

```python
# Bad: Database calls mixed with business logic
async def execute(self, node, state, graph, execution_id, user_id=None):
    # Direct database calls
    ExecutionHistoryService.create_node_execution(...)
    # Business logic
    result = self._do_work(node, state)
    # More database calls
    ExecutionHistoryService.complete_node_execution(...)

# Good: Use handlers for infrastructure
async def execute(self, node, state, graph, execution_id, user_id=None):
    await self.database_tracker.create_node_execution(...)  # Handler
    result = self._do_work(node, state)  # Business logic
    await self.database_tracker.complete_node_execution(...)  # Handler
```

**Why:** Separation of concerns improves testability and maintainability.

❌ **Don't forget to increment execution order**

```python
# Bad: Execution order not updated
return {"node_output": result}

# Good: Always increment
order_update = self.database_tracker.increment_execution_order(state)
return {"node_output": result, **order_update}
```

**Why:** Execution order is used for UI display and debugging.

---

## Related Documentation

### Related Services

- [Execution Service](execution.md) - Workflow execution engine that uses node executors
- [Graph Service](graph.md) - Graph building and management, used by agent executors
- [IO Service](io.md) - Input building and mapping extraction, used by all executors
- [Memory Service](memory.md) - Conversation memory management, used by agent executors
- [Email Service](email.md) - Email sending integration, used by email executor

### Related API Modules

- [Workflow API](../../../backend/api/workflow/workflow.md) - Workflow execution endpoints
- [Nodes API](../agents-guide/api/nodes.md) - Node configuration and management

### External Documentation

- [LangChain Documentation](https://python.langchain.com/) - Agent and tool execution
- [Requests Documentation](https://requests.readthedocs.io/) - HTTP client library
- [Psycopg2 Documentation](https://www.psycopg.org/) - PostgreSQL adapter

---

## Summary

The nodes service module provides a comprehensive, modular framework for executing different types of workflow nodes in
the AgenticStudio backend. Built on the Strategy and Template Method patterns, it enables dynamic executor selection,
consistent execution flow, and easy extensibility for new node types.

The module uses a clean service-oriented architecture with separation of concerns:

- `BaseNodeExecutor` and `NodeExecutorProtocol` define the executor interface
- `NodeExecutorRegistry` implements the Strategy pattern for dynamic executor selection
- Concrete executors (`AgentNodeExecutor`, `HttpNodeExecutor`, etc.) implement node-type-specific logic
- Handler services (`NodeDatabaseTracker`, `NodeNotificationHandler`) extract common infrastructure concerns
- The database executor uses a full sub-package with modular services for connection management and query building

All executors follow a consistent execution flow:

1. Create database tracking record
2. Send WebSocket start notification
3. Execute node-specific logic
4. Complete database tracking with output and metrics
5. Send WebSocket completion notification
6. Return state updates

**Key Features:**

- Dynamic executor selection via registry (Strategy pattern)
- Consistent execution interface via base class (Template Method pattern)
- Separation of concerns with handler services
- Full database tracking for all node executions
- Real-time WebSocket notifications for UI updates
- Comprehensive error handling with specific exception types
- Support for dependency injection via factory functions
- Fully async/await for concurrent execution
- Modular architecture for easy testing and extension

**Primary Use Cases:**

- Execute workflow nodes of different types (AGENT, HTTP_REQUEST, CONDITION, FILE_READ, EMAIL_SEND, DATABASE_INSERT)
- Track node execution history in database for debugging and auditing
- Send real-time execution updates via WebSocket for responsive UI
- Register custom executors for new node types
- Test executors with mocked dependencies

**When to Use This Service:**

- Implementing workflow execution logic
- Adding new node types to the platform
- Building execution history and debugging tools
- Creating real-time execution monitoring interfaces
- Testing workflow execution with different configurations
