# WebSocket Service

## Overview

The WebSocket service provides real-time communication infrastructure for streaming workflow execution updates to
connected clients. It manages bidirectional WebSocket connections, broadcasts execution status changes, node updates,
and handles client reconnection to ongoing or completed executions.

**Location:** [backend/services/websocket/](../../backend/services/websocket/)

**Primary Responsibilities:**

- Manage active WebSocket connections for execution monitoring
- Broadcast real-time execution and node status updates
- Handle HTTP execution listener notifications
- Support client reconnection to in-progress or paused executions
- Maintain connection lifecycle and cleanup

**Key Use Cases:**

- Real-time workflow execution monitoring in the frontend UI
- Live node execution status updates during agent workflows
- Notification of HTTP-triggered workflow executions
- Checkpoint/pause state synchronisation on reconnection
- Multi-client execution monitoring

## Architecture

### Module Structure

```
backend/services/websocket/
├── __init__.py                    # Module exports and global instances
├── connection_manager.py          # WebSocket connection management
├── http_listener_manager.py       # HTTP execution listener management
├── notifier.py                    # Execution event notifier callbacks
└── reconnection/                  # Reconnection handling
    ├── __init__.py               # Reconnection exports
    ├── handler.py                # Main reconnection handler
    ├── status_handler.py         # Execution status-specific handling
    ├── node_state_sender.py      # Node state broadcasting
    └── execution_loader.py       # Database execution loading
```

**File Descriptions:**

- **`__init__.py`** - Defines the public API, creates global singleton instances (`connection_manager`,
  `http_listener_manager`, `notifier`, `manager`), and provides a `CombinedManager` for backward compatibility
- **`connection_manager.py`** - Core WebSocket connection tracking and message broadcasting for execution updates
- **`http_listener_manager.py`** - Manages WebSocket connections that listen for HTTP-triggered workflow executions
- **`notifier.py`** - Event-driven callback interface for the execution engine to send real-time updates
- **`reconnection/`** - Handles client reconnection logic, restoring execution state from the database

### Design Patterns

**Singleton Pattern:**
The module creates global singleton instances (`connection_manager`, `http_listener_manager`, `notifier`) that are
shared across the application. This ensures consistent connection state across all services.

```python
# From __init__.py
connection_manager = ConnectionManager()
http_listener_manager = HTTPListenerManager()
notifier = WebSocketExecutionNotifier(connection_manager)
```

**Observer/Callback Pattern:**
The `WebSocketExecutionNotifier` provides callback methods that the execution engine invokes when events occur (
`on_execution_start`, `on_node_complete`, `on_execution_paused`, etc.).

**Facade Pattern:**
The `CombinedManager` provides a unified interface that delegates to specialised managers (`ConnectionManager` and
`HTTPListenerManager`), maintaining backward compatibility while allowing internal refactoring.

**Repository Pattern:**
The reconnection module uses `execution_loader.py` to abstract database access for execution state retrieval.

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI WebSocket Routes                  │
│   /api/ws/execution/{execution_id}                          │
│   /api/ws/http-listener/{graph_name}                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      Combined Manager                        │
│  (Backward Compatibility Facade)                            │
└────────┬───────────────────────────────────┬────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────────┐          ┌──────────────────────────┐
│  ConnectionManager  │          │  HTTPListenerManager     │
│  - Execution        │          │  - HTTP listener         │
│    connections      │          │    connections           │
│  - Broadcast        │          │  - HTTP execution        │
│    updates          │          │    notifications         │
└──────────┬──────────┘          └──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│          WebSocketExecutionNotifier                          │
│  - Callback interface for execution engine                  │
│  - Event handlers (start, complete, error, pause)           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  Reconnection Module                         │
│  - Execution state restoration                              │
│  - Database loading                                         │
│  - Status-specific handling                                 │
└─────────────────────────────────────────────────────────────┘
```

**Integration Flow:**

1. Frontend connects via WebSocket to `/api/ws/execution/{execution_id}`
2. API route calls `manager.connect(websocket, execution_id)`
3. Execution engine calls `notifier.on_node_start()` when node executes
4. Notifier calls `connection_manager.send_node_update()`
5. ConnectionManager broadcasts JSON message to all connected clients for that execution
6. On reconnection, `handle_reconnect_execution()` loads state from database and replays it

### Dependencies

**Internal Dependencies:**

- `backend.services.config` - Logger configuration
- `backend.services.database` - Database session management (`get_db`)
- `backend.models` - Database models (`GraphExecution`, `NodeExecution`)

**External Dependencies:**

- `fastapi` - WebSocket support (`fastapi.WebSocket`)
- `asyncio` - Asynchronous I/O and task management
- `json` - JSON serialisation for message formatting
- `datetime` - Timestamp generation
- `sqlalchemy` - Database ORM for execution loading

**Database Dependencies:**

- `graph_executions` table - Execution status, metadata, results
- `node_executions` table - Node execution history, status, outputs

**Environment Variables:**
None. The module uses global configuration from `backend.services.config`.

## Public API

### Exported Classes

- `ConnectionManager` - Manages WebSocket connections for execution updates
- `HTTPListenerManager` - Manages WebSocket connections for HTTP execution notifications
- `WebSocketExecutionNotifier` - Provides callback methods for execution engine events
- `CombinedManager` - Legacy combined interface delegating to specialised managers (not exported in `__all__`)

### Exported Instances

- `manager` - Global `CombinedManager` instance providing unified access
- `notifier` - Global `WebSocketExecutionNotifier` instance for execution callbacks

### Exported Functions

The `reconnection` submodule exports:

- `handle_reconnect_execution()` - Handles client reconnection to existing executions

### Constants and Configuration

None. The module uses runtime configuration only.

### Exceptions

No custom exceptions. Uses standard Python exceptions:

- `Exception` - Generic WebSocket send failures (caught and logged)
- `asyncio.TimeoutError` - Connection timeout during receive operations
- `fastapi.WebSocketDisconnect` - Client disconnection

## Core Classes

### `ConnectionManager`

Manages WebSocket connections and broadcasts execution updates to connected clients.

**Purpose:**
Provides centralised WebSocket connection tracking and message broadcasting for execution monitoring. Maintains separate
connection pools per execution ID to ensure clients only receive updates for executions they're watching.

**Responsibilities:**

- Accept and track WebSocket connections per execution ID
- Maintain a global set of all active connections
- Broadcast execution status updates to relevant connections
- Send node execution updates with comprehensive metadata
- Handle graceful disconnection and cleanup
- Remove stale/failed connections automatically

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise WebSocket connection manager."""
```

Creates empty connection tracking dictionaries:

- `self.active_connections: Dict[str, Set[WebSocket]]` - Connections grouped by execution ID
- `self.all_connections: Set[WebSocket]` - All connections regardless of execution

**Key Methods:**

#### `connect()`

```python
async def connect(
    self,
    websocket: WebSocket,
    execution_id: Optional[str] = None,
) -> None:
    """Accept a new WebSocket connection."""
```

**Parameters:**

- `websocket` (WebSocket) - FastAPI WebSocket connection to accept
- `execution_id` (Optional[str]) - Execution ID to associate with this connection, or None for general connections

**Returns:**

- None

**Raises:**

- No explicit exceptions (FastAPI handles connection errors)

**Example:**

```python
from backend.services.websocket import connection_manager
from fastapi import WebSocket

@app.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await connection_manager.connect(websocket, execution_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle messages
    finally:
        connection_manager.disconnect(websocket, execution_id)
```

**Behaviour:**

- Calls `websocket.accept()` to establish the WebSocket connection
- Adds websocket to `all_connections` set
- If `execution_id` provided, adds websocket to `active_connections[execution_id]` set
- Logs connection count for debugging

**Use Cases:**

- Accept new client connections for execution monitoring
- Re-establish connections after disconnection
- Connect general monitoring clients (without execution_id)

#### `disconnect()`

```python
def disconnect(
    self,
    websocket: WebSocket,
    execution_id: Optional[str] = None,
) -> None:
    """Remove a WebSocket connection."""
```

**Parameters:**

- `websocket` (WebSocket) - WebSocket connection to remove
- `execution_id` (Optional[str]) - Execution ID associated with connection, or None to remove from all

**Returns:**

- None

**Example:**

```python
# Disconnect specific execution
connection_manager.disconnect(websocket, execution_id="exec-123")

# Disconnect from all executions
connection_manager.disconnect(websocket)
```

**Behaviour:**

- Removes websocket from `all_connections`
- If `execution_id` provided, removes from that execution's connection set
- If no `execution_id`, removes websocket from all execution connection sets
- Cleans up empty execution connection sets
- Logs remaining connection counts

**Use Cases:**

- Clean up on normal client disconnection
- Remove failed/stale connections
- Handle client-initiated close requests

#### `send_execution_update()`

```python
async def send_execution_update(
    self,
    execution_id: str,
    event_type: str,
    data: Dict[str, Any],
) -> None:
    """Send an update to all connections watching an execution."""
```

**Parameters:**

- `execution_id` (str) - Execution ID to send update for
- `event_type` (str) - Event type identifier (e.g., "node_update", "execution_status", "reconnected")
- `data` (Dict[str, Any]) - Event payload data

**Returns:**

- None

**Example:**

```python
await connection_manager.send_execution_update(
    execution_id="exec-123",
    event_type="node_update",
    data={
        "node_id": "node-456",
        "node_name": "LLM Agent",
        "status": "running",
    }
)
```

**Behaviour:**

- Checks if any connections exist for execution_id (warns if none)
- Constructs JSON message with type, execution_id, timestamp, and data
- Broadcasts message to all connections watching this execution
- Catches send failures and tracks disconnected sockets
- Calls `disconnect()` for failed connections
- Uses `asyncio.sleep(0)` to force immediate message flushing

**Use Cases:**

- Send custom execution events
- Broadcast reconnection confirmations
- Send checkpoint/pause notifications

#### `send_node_update()`

```python
async def send_node_update(
    self,
    execution_id: str,
    node_id: str,
    node_name: str,
    status: str,
    output: Optional[Any] = None,
    error: Optional[str] = None,
    node_type: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    input_data: Optional[Any] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    is_sub_agent: Optional[bool] = None,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[str] = None,
    execution_order: Optional[int] = None,
) -> None:
    """Send a node execution update with complete data."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `node_id` (str) - Graph node ID
- `node_name` (str) - Human-readable node name
- `status` (str) - Node status ("running", "completed", "failed", "paused")
- `output` (Optional[Any]) - Node output data
- `error` (Optional[str]) - Error message if failed
- `node_type` (Optional[str]) - Node type (e.g., "AGENT", "HTTP", "DATABASE")
- `duration_seconds` (Optional[float]) - Execution duration
- `input_data` (Optional[Any]) - Node input data
- `start_time` (Optional[str]) - ISO 8601 start timestamp
- `end_time` (Optional[str]) - ISO 8601 end timestamp
- `input_tokens` (Optional[int]) - LLM input tokens
- `output_tokens` (Optional[int]) - LLM output tokens
- `total_tokens` (Optional[int]) - Total LLM tokens
- `is_sub_agent` (Optional[bool]) - Whether this is a sub-agent node
- `parent_agent_id` (Optional[str]) - Parent agent ID if sub-agent
- `database_node_id` (Optional[str]) - Database primary key
- `execution_order` (Optional[int]) - Execution sequence number

**Returns:**

- None

**Example:**

```python
await connection_manager.send_node_update(
    execution_id="exec-123",
    node_id="agent-456",
    node_name="Research Agent",
    status="completed",
    output={"result": "Analysis complete"},
    node_type="AGENT",
    duration_seconds=3.45,
    input_data={"query": "Analyse market trends"},
    start_time="2025-10-27T10:30:00",
    end_time="2025-10-27T10:30:03.45",
    input_tokens=150,
    output_tokens=300,
    total_tokens=450,
)
```

**Behaviour:**

- Constructs comprehensive data payload with all provided fields
- Logs detailed node update information for debugging
- Calls `send_execution_update()` with event_type="node_update"

**Use Cases:**

- Send node start notifications
- Broadcast node completion with results
- Send node failure with error details
- Update node pause state at checkpoints

#### `send_execution_status()`

```python
async def send_execution_status(
    self,
    execution_id: str,
    status: str,
    result: Optional[Any] = None,
    error: Optional[str] = None,
) -> None:
    """Send execution status update."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `status` (str) - Execution status ("started", "running", "completed", "failed", "paused")
- `result` (Optional[Any]) - Execution result data
- `error` (Optional[str]) - Error message if failed

**Returns:**

- None

**Example:**

```python
# Execution started
await connection_manager.send_execution_status(
    execution_id="exec-123",
    status="started",
    result={"graph_name": "data_pipeline"}
)

# Execution completed
await connection_manager.send_execution_status(
    execution_id="exec-123",
    status="completed",
    result={"output": "Pipeline succeeded", "records_processed": 1000}
)

# Execution failed
await connection_manager.send_execution_status(
    execution_id="exec-123",
    status="failed",
    error="Database connection timeout"
)
```

**Behaviour:**

- Calls `send_execution_update()` with event_type="execution_status"
- Includes status, result, and error in data payload

**Use Cases:**

- Signal execution start to connected clients
- Broadcast execution completion with final results
- Send execution failure notifications
- Indicate execution pause state

#### `broadcast()`

```python
async def broadcast(self, message: str) -> None:
    """Broadcast a message to all connected clients."""
```

**Parameters:**

- `message` (str) - Message string to broadcast (typically JSON)

**Returns:**

- None

**Example:**

```python
import json

message = json.dumps({
    "type": "system_notification",
    "message": "System maintenance in 5 minutes"
})
await connection_manager.broadcast(message)
```

**Behaviour:**

- Sends message to all connections in `all_connections`
- Catches send failures and tracks disconnected sockets
- Removes failed connections

**Use Cases:**

- Send system-wide notifications
- Broadcast maintenance announcements
- Send general updates to all clients

**Class Attributes:**

- `active_connections: Dict[str, Set[WebSocket]]` - Connections grouped by execution ID
- `all_connections: Set[WebSocket]` - All active connections

**Properties:**
None.

---

### `HTTPListenerManager`

Manages WebSocket connections for HTTP execution notifications.

**Purpose:**
Allows UI clients to listen for HTTP-triggered workflow executions, enabling real-time notification when external
systems trigger workflows via the HTTP execution API.

**Responsibilities:**

- Accept WebSocket connections for HTTP execution listening
- Track listeners by graph name
- Broadcast HTTP execution start events to relevant listeners
- Handle listener disconnection and cleanup

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise HTTP listener manager."""
```

Creates empty listener tracking dictionaries:

- `self.http_listeners: Dict[str, Set[WebSocket]]` - Listeners grouped by graph name
- `self.all_http_listeners: Set[WebSocket]` - All listeners regardless of graph

**Key Methods:**

#### `connect_http_listener()`

```python
async def connect_http_listener(
    self,
    websocket: WebSocket,
    graph_name: Optional[str] = None,
) -> None:
    """Connect a WebSocket as an HTTP execution listener."""
```

**Parameters:**

- `websocket` (WebSocket) - WebSocket connection to accept
- `graph_name` (Optional[str]) - Graph name to listen for, or None for all graphs

**Returns:**

- None

**Example:**

```python
from backend.services.websocket import http_listener_manager

# Listen for specific graph
await http_listener_manager.connect_http_listener(
    websocket,
    graph_name="customer_onboarding"
)

# Listen for all graphs
await http_listener_manager.connect_http_listener(websocket)
```

**Behaviour:**

- Calls `websocket.accept()` to establish connection
- Adds websocket to `all_http_listeners`
- If `graph_name` provided, adds to `http_listeners[graph_name]` set
- Logs connection for debugging

**Use Cases:**

- Connect UI clients to monitor HTTP-triggered executions
- Set up listeners for specific workflow graphs
- Monitor all HTTP executions across graphs

#### `disconnect_http_listener()`

```python
def disconnect_http_listener(
    self,
    websocket: WebSocket,
    graph_name: Optional[str] = None,
) -> None:
    """Disconnect an HTTP listener."""
```

**Parameters:**

- `websocket` (WebSocket) - WebSocket to disconnect
- `graph_name` (Optional[str]) - Graph name to disconnect from, or None for all

**Returns:**

- None

**Example:**

```python
http_listener_manager.disconnect_http_listener(
    websocket,
    graph_name="customer_onboarding"
)
```

**Behaviour:**

- Removes websocket from `all_http_listeners`
- If `graph_name` provided, removes from that graph's listener set
- If no `graph_name`, removes from all graph listener sets
- Cleans up empty listener sets

**Use Cases:**

- Clean up on client disconnection
- Remove specific graph listeners
- Handle connection failures

#### `broadcast_http_execution_start()`

```python
async def broadcast_http_execution_start(
    self,
    execution_id: str,
    graph_name: str,
    input_data: Dict[str, Any],
) -> None:
    """Broadcast HTTP execution start to all relevant listeners."""
```

**Parameters:**

- `execution_id` (str) - New execution ID
- `graph_name` (str) - Graph being executed
- `input_data` (Dict[str, Any]) - Execution input data

**Returns:**

- None

**Example:**

```python
await http_listener_manager.broadcast_http_execution_start(
    execution_id="exec-789",
    graph_name="customer_onboarding",
    input_data={
        "customer_id": "CUST-123",
        "email": "customer@example.com"
    }
)
```

**Behaviour:**

- Constructs message with type="http_execution_started", execution_id, graph_name, timestamp, and data
- Sends to graph-specific listeners in `http_listeners[graph_name]`
- Sends to general listeners in `all_http_listeners` (avoiding duplicates)
- Removes failed connections
- Logs successful sends

**Use Cases:**

- Notify UI of HTTP-triggered executions
- Alert monitoring dashboards of new workflow runs
- Trigger UI updates when external systems invoke workflows

**Class Attributes:**

- `http_listeners: Dict[str, Set[WebSocket]]` - Listeners grouped by graph name
- `all_http_listeners: Set[WebSocket]` - All HTTP listeners

**Properties:**
None.

---

### `WebSocketExecutionNotifier`

Provides callback methods for the execution engine to send real-time updates.

**Purpose:**
Acts as the bridge between the execution engine and WebSocket infrastructure. Provides a clean callback interface that
execution components can invoke without direct WebSocket knowledge.

**Responsibilities:**

- Receive execution lifecycle events from the engine
- Transform events into WebSocket messages
- Delegate to ConnectionManager for broadcasting
- Handle reconnection requests
- Provide semantic event methods (start, complete, error, pause)

**Initialisation:**

```python
def __init__(self, connection_manager: ConnectionManager) -> None:
    """Initialise WebSocket execution notifier."""
```

**Parameters:**

- `connection_manager` (ConnectionManager) - Connection manager instance to use for broadcasting

**Example:**

```python
from backend.services.websocket import ConnectionManager, WebSocketExecutionNotifier

manager = ConnectionManager()
notifier = WebSocketExecutionNotifier(manager)
```

**Key Methods:**

#### `on_execution_start()`

```python
async def on_execution_start(
    self,
    execution_id: str,
    graph_name: str,
) -> None:
    """Handle execution start event."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `graph_name` (str) - Graph name being executed

**Returns:**

- None

**Example:**

```python
await notifier.on_execution_start(
    execution_id="exec-123",
    graph_name="data_pipeline"
)
```

**Behaviour:**

- Calls `manager.send_execution_status()` with status="started" and graph_name in result

**Use Cases:**

- Signal workflow execution start to monitoring clients
- Initialize execution tracking in frontend

#### `on_node_start()`

```python
async def on_node_start(
    self,
    execution_id: str,
    node_id: str,
    node_name: str,
    node_type: str,
    is_sub_agent: Optional[bool] = None,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[str] = None,
    execution_order: Optional[int] = None,
) -> None:
    """Handle node start event."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `node_id` (str) - Node ID
- `node_name` (str) - Node name
- `node_type` (str) - Node type
- `is_sub_agent` (Optional[bool]) - Whether node is a sub-agent
- `parent_agent_id` (Optional[str]) - Parent agent ID if sub-agent
- `database_node_id` (Optional[str]) - Database node execution ID
- `execution_order` (Optional[int]) - Execution sequence number

**Returns:**

- None

**Example:**

```python
await notifier.on_node_start(
    execution_id="exec-123",
    node_id="agent-456",
    node_name="Research Agent",
    node_type="AGENT",
    database_node_id="db-789",
    execution_order=3
)
```

**Behaviour:**

- Calls `manager.send_node_update()` with status="running" and minimal metadata

**Use Cases:**

- Indicate node execution has begun
- Show real-time progress in UI
- Track execution flow

#### `on_node_complete()`

```python
async def on_node_complete(
    self,
    execution_id: str,
    node_id: str,
    node_name: str,
    output: Any,
    node_type: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    input_data: Optional[Any] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    is_sub_agent: Optional[bool] = None,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[str] = None,
    execution_order: Optional[int] = None,
) -> None:
    """Handle node completion event."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `node_id` (str) - Node ID
- `node_name` (str) - Node name
- `output` (Any) - Node output data
- `node_type` (Optional[str]) - Node type
- `duration_seconds` (Optional[float]) - Execution duration
- `input_data` (Optional[Any]) - Input data
- `start_time` (Optional[str]) - ISO 8601 start time
- `end_time` (Optional[str]) - ISO 8601 end time
- `input_tokens` (Optional[int]) - LLM input tokens
- `output_tokens` (Optional[int]) - LLM output tokens
- `total_tokens` (Optional[int]) - Total tokens
- `is_sub_agent` (Optional[bool]) - Whether sub-agent
- `parent_agent_id` (Optional[str]) - Parent agent ID
- `database_node_id` (Optional[str]) - Database node ID
- `execution_order` (Optional[int]) - Execution order

**Returns:**

- None

**Example:**

```python
await notifier.on_node_complete(
    execution_id="exec-123",
    node_id="agent-456",
    node_name="Research Agent",
    output={"analysis": "Market trends are positive"},
    node_type="AGENT",
    duration_seconds=3.45,
    input_data={"query": "Analyse markets"},
    start_time="2025-10-27T10:30:00",
    end_time="2025-10-27T10:30:03.45",
    input_tokens=150,
    output_tokens=300,
    total_tokens=450,
)
```

**Behaviour:**

- Calls `manager.send_node_update()` with status="completed" and full metadata

**Use Cases:**

- Send node results to frontend
- Display completion status in UI
- Track token usage and costs

#### `on_node_error()`

```python
async def on_node_error(
    self,
    execution_id: str,
    node_id: str,
    node_name: str,
    error: str,
    node_type: Optional[str] = None,
    database_node_id: Optional[str] = None,
) -> None:
    """Handle node error event."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `node_id` (str) - Node ID
- `node_name` (str) - Node name
- `error` (str) - Error message
- `node_type` (Optional[str]) - Node type
- `database_node_id` (Optional[str]) - Database node ID

**Returns:**

- None

**Example:**

```python
await notifier.on_node_error(
    execution_id="exec-123",
    node_id="db-query-789",
    node_name="User Database Query",
    error="Connection timeout after 30 seconds",
    node_type="DATABASE"
)
```

**Behaviour:**

- Calls `manager.send_node_update()` with status="failed" and error message

**Use Cases:**

- Display node failures in UI
- Alert users to execution problems
- Log error details for debugging

#### `on_execution_complete()`

```python
async def on_execution_complete(
    self,
    execution_id: str,
    result: Any,
) -> None:
    """Handle execution completion event."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `result` (Any) - Final execution result

**Returns:**

- None

**Example:**

```python
await notifier.on_execution_complete(
    execution_id="exec-123",
    result={
        "status": "success",
        "records_processed": 1000,
        "output_file": "results.csv"
    }
)
```

**Behaviour:**

- Calls `manager.send_execution_status()` with status="completed" and result

**Use Cases:**

- Signal workflow completion to UI
- Display final results to users
- Trigger post-execution actions

#### `on_node_paused()`

```python
async def on_node_paused(
    self,
    execution_id: str,
    node_id: str,
    node_name: str,
    node_type: Optional[str] = None,
    database_node_id: Optional[str] = None,
    is_sub_agent: Optional[bool] = None,
    parent_agent_id: Optional[str] = None,
) -> None:
    """Handle node pause event (e.g., checkpoint)."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `node_id` (str) - Node ID
- `node_name` (str) - Node name
- `node_type` (Optional[str]) - Node type
- `database_node_id` (Optional[str]) - Database node ID
- `is_sub_agent` (Optional[bool]) - Whether sub-agent
- `parent_agent_id` (Optional[str]) - Parent agent ID

**Returns:**

- None

**Example:**

```python
await notifier.on_node_paused(
    execution_id="exec-123",
    node_id="checkpoint-456",
    node_name="Manual Approval Checkpoint",
    node_type="CHECKPOINT",
)
```

**Behaviour:**

- Logs checkpoint debug information
- Calls `manager.send_node_update()` with status="paused"

**Use Cases:**

- Indicate checkpoint pause to UI
- Show waiting-for-input state
- Enable checkpoint resumption interface

#### `on_execution_paused()`

```python
async def on_execution_paused(
    self,
    execution_id: str,
    payload: Any,
) -> None:
    """Handle execution pause event for human-in-the-loop."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `payload` (Any) - Pause payload (checkpoint details)

**Returns:**

- None

**Example:**

```python
await notifier.on_execution_paused(
    execution_id="exec-123",
    payload={
        "checkpoint_id": "ckpt-789",
        "thread_id": "thread-456",
        "node_id": "checkpoint-456",
        "prompt": "Approve this analysis before proceeding?",
        "db_execution_id": "db-exec-123"
    }
)
```

**Behaviour:**

- Logs pause debug information
- Calls `manager.send_execution_status()` with status="paused" and payload

**Use Cases:**

- Pause execution for human approval
- Display checkpoint prompt to user
- Enable resumption with user input

#### `on_execution_resumed()`

```python
async def on_execution_resumed(
    self,
    execution_id: str,
    payload: Any | None = None,
) -> None:
    """Handle execution resumption after pause."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `payload` (Any | None) - Resumption payload (user input, etc.)

**Returns:**

- None

**Example:**

```python
await notifier.on_execution_resumed(
    execution_id="exec-123",
    payload={"user_approval": True, "notes": "Approved by manager"}
)
```

**Behaviour:**

- Logs resumption debug information
- Calls `manager.send_execution_status()` with status="running" and payload

**Use Cases:**

- Signal execution continuation to UI
- Update execution state after checkpoint
- Resume real-time monitoring

#### `on_execution_error()`

```python
async def on_execution_error(
    self,
    execution_id: str,
    error: str,
) -> None:
    """Handle execution error event."""
```

**Parameters:**

- `execution_id` (str) - Execution ID
- `error` (str) - Error message

**Returns:**

- None

**Example:**

```python
await notifier.on_execution_error(
    execution_id="exec-123",
    error="Workflow failed: Invalid API credentials"
)
```

**Behaviour:**

- Calls `manager.send_execution_status()` with status="failed" and error

**Use Cases:**

- Broadcast execution failures
- Alert users to critical errors
- Trigger error recovery workflows

#### `handle_reconnect_execution()`

```python
async def handle_reconnect_execution(
    self,
    websocket: WebSocket,
    execution_id: str,
    thread_id: Optional[str] = None,
    db_execution_id: Optional[str] = None,
) -> None:
    """Handle reconnection to an existing execution."""
```

**Parameters:**

- `websocket` (WebSocket) - WebSocket to reconnect
- `execution_id` (str) - Execution ID to reconnect to
- `thread_id` (Optional[str]) - Thread ID for stateful executions
- `db_execution_id` (Optional[str]) - Database execution ID

**Returns:**

- None

**Example:**

```python
await notifier.handle_reconnect_execution(
    websocket=websocket,
    execution_id="exec-123",
    thread_id="thread-456",
    db_execution_id="db-exec-789"
)
```

**Behaviour:**

- Delegates to `reconnection.handle_reconnect_execution()`
- Loads execution state from database
- Replays all node states to client
- Sends current execution status

**Use Cases:**

- Restore UI state after page refresh
- Reconnect after network disconnection
- Resume monitoring paused executions

**Class Attributes:**

- `manager: ConnectionManager` - Connection manager for broadcasting

**Properties:**
None.

---

### `CombinedManager`

Combined manager that delegates to specialised managers for backward compatibility.

**Purpose:**
Provides a unified interface over `ConnectionManager` and `HTTPListenerManager`, allowing legacy code to use a single
manager instance while internally delegating to specialised managers.

**Responsibilities:**

- Delegate connection methods to `ConnectionManager`
- Delegate HTTP listener methods to `HTTPListenerManager`
- Maintain backward compatibility with older code

**Initialisation:**

```python
def __init__(
    self,
    connection_mgr: ConnectionManager,
    http_mgr: HTTPListenerManager,
) -> None:
    """Initialise combined manager."""
```

**Parameters:**

- `connection_mgr` (ConnectionManager) - Connection manager instance
- `http_mgr` (HTTPListenerManager) - HTTP listener manager instance

**Example:**

```python
from backend.services.websocket import (
    ConnectionManager,
    HTTPListenerManager,
    CombinedManager
)

conn_mgr = ConnectionManager()
http_mgr = HTTPListenerManager()
manager = CombinedManager(conn_mgr, http_mgr)
```

**Key Methods:**

All methods delegate to underlying managers:

- `connect()` → `connection_mgr.connect()`
- `disconnect()` → `connection_mgr.disconnect()`
- `send_execution_update()` → `connection_mgr.send_execution_update()`
- `send_node_update()` → `connection_mgr.send_node_update()`
- `send_execution_status()` → `connection_mgr.send_execution_status()`
- `broadcast()` → `connection_mgr.broadcast()`
- `connect_http_listener()` → `http_mgr.connect_http_listener()`
- `disconnect_http_listener()` → `http_mgr.disconnect_http_listener()`
- `broadcast_http_execution_start()` → `http_mgr.broadcast_http_execution_start()`

**Use Cases:**

- Maintain compatibility with existing code
- Simplify imports for common use cases
- Provide single manager instance via global `manager`

**Class Attributes:**

- `_connection_mgr: ConnectionManager` - Underlying connection manager
- `_http_mgr: HTTPListenerManager` - Underlying HTTP listener manager

**Properties:**
None.

## Functions

### `handle_reconnect_execution()`

Handles reconnection to an existing execution.

**Signature:**

```python
async def handle_reconnect_execution(
    manager: ConnectionManager,
    notifier: WebSocketExecutionNotifier,
    websocket: WebSocket,
    execution_id: str,
    thread_id: Optional[str] = None,
    db_execution_id: Optional[str] = None,
) -> None:
    """
    Handle reconnection to an existing execution.

    Args:
        manager: ConnectionManager instance
        notifier: WebSocketExecutionNotifier instance
        websocket: WebSocket connection
        execution_id: Execution ID
        thread_id: Optional thread ID
        db_execution_id: Optional database execution ID
    """
```

**Parameters:**

- `manager` (ConnectionManager) - Connection manager to use
- `notifier` (WebSocketExecutionNotifier) - Notifier for callbacks
- `websocket` (WebSocket) - WebSocket to connect
- `execution_id` (str) - Execution ID to reconnect to
- `thread_id` (Optional[str]) - Thread ID for stateful executions
- `db_execution_id` (Optional[str]) - Database execution ID to load state from

**Returns:**

- None

**Raises:**

- `Exception` - On database or connection errors (caught and sent as reconnect_failed event)

**Example:**

```python
from backend.services.websocket.reconnection import handle_reconnect_execution
from backend.services.websocket import connection_manager, notifier

await handle_reconnect_execution(
    manager=connection_manager,
    notifier=notifier,
    websocket=websocket,
    execution_id="exec-123",
    thread_id="thread-456",
    db_execution_id="db-exec-789"
)
```

**Behaviour:**

1. Connects websocket to execution via `manager.connect()`
2. Loads execution from database using `db_execution_id`
3. Sends reconnection confirmation with execution status
4. Replays all node execution states to client
5. Handles current execution status:
    - **Paused**: Sends checkpoint details via `notifier.on_execution_paused()`
    - **Running**: Sends running status
    - **Completed**: Sends completion status with result
6. On error, sends reconnect_failed event with error details

**Use Cases:**

- Restore UI state after page refresh
- Recover from temporary network disconnection
- Resume monitoring paused/checkpoint executions
- View completed execution history

## Configuration

### Configuration Classes

None. The module uses global singleton instances.

### Environment Variables

None. The module relies on:

- Database configuration from `backend.services.database`
- Logger configuration from `backend.services.config`

### Initialisation Patterns

**Basic Initialisation (Recommended):**

Use the global singleton instances exported by the module:

```python
from backend.services.websocket import manager, notifier, connection_manager, http_listener_manager

# Use in API routes
@app.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)
    # ... handle messages

# Use in execution engine
await notifier.on_node_start(
    execution_id="exec-123",
    node_id="agent-456",
    node_name="Research Agent",
    node_type="AGENT"
)
```

**Custom Initialisation (Advanced):**

For testing or custom configurations:

```python
from backend.services.websocket import (
    ConnectionManager,
    HTTPListenerManager,
    WebSocketExecutionNotifier,
    CombinedManager
)

# Create custom instances
custom_conn_mgr = ConnectionManager()
custom_http_mgr = HTTPListenerManager()
custom_notifier = WebSocketExecutionNotifier(custom_conn_mgr)
custom_manager = CombinedManager(custom_conn_mgr, custom_http_mgr)
```

**Dependency Injection:**

The execution engine receives the notifier instance:

```python
# From backend/services/execution/engine.py
from backend.services.websocket import notifier as ws_notifier

class ExecutionEngine:
    def __init__(self, graph_manager):
        self.notifier = ws_notifier
        # ... other initialisation

    async def execute_node(self, node):
        await self.notifier.on_node_start(...)
        # ... execute node
        await self.notifier.on_node_complete(...)
```

## Error Handling

### Exception Hierarchy

The module does not define custom exceptions. It uses standard Python exceptions:

```
Exception
├── RuntimeError (connection failures)
├── asyncio.TimeoutError (receive timeouts)
└── fastapi.WebSocketDisconnect (client disconnections)
```

### Exception Details

#### WebSocket Send Failures

Raised when sending to a disconnected or failed WebSocket.

**When raised:**

- Client has disconnected
- Network connection lost
- Client closed connection abnormally

**Example:**

```python
try:
    await websocket.send_text(message)
except Exception as e:
    logger.error(f"Failed to send WebSocket message: {e}")
    # Connection is tracked and removed during next broadcast
```

#### `asyncio.TimeoutError`

Raised during WebSocket receive operations when client doesn't send within timeout.

**When raised:**

- Client idle for longer than timeout period
- Client not responding to pings

**Example:**

```python
try:
    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
except asyncio.TimeoutError:
    # Send ping to keep connection alive
    await websocket.send_text("ping")
```

#### `WebSocketDisconnect`

Raised by FastAPI when client disconnects WebSocket.

**When raised:**

- Client closes connection normally
- Network disconnection
- Browser tab closed

**Example:**

```python
from fastapi import WebSocketDisconnect

try:
    while True:
        data = await websocket.receive_text()
except WebSocketDisconnect:
    logger.info("Client disconnected normally")
finally:
    manager.disconnect(websocket, execution_id)
```

### Error Handling Patterns

**Recommended Pattern for WebSocket Routes:**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.websocket import manager as ws_manager
from backend.services.config import get_logger

logger = get_logger("websocket_route")

@router.websocket("/ws/execution/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint with proper error handling."""

    try:
        # Connect
        await ws_manager.connect(websocket, execution_id)

        # Send initial state
        await websocket.send_json({"type": "connected", "execution_id": execution_id})

        # Message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle messages
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "close":
                    break

            except asyncio.TimeoutError:
                # Keep alive with ping
                try:
                    await websocket.send_text("ping")
                except Exception:
                    logger.warning("Failed to send ping, connection lost")
                    break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {execution_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        # Always clean up
        ws_manager.disconnect(websocket, execution_id)
        logger.info(f"Connection cleanup complete: {execution_id}")
```

**Recommended Pattern for Execution Engine Integration:**

```python
from backend.services.websocket import notifier
from backend.services.config import get_logger

logger = get_logger("execution_engine")

async def execute_workflow(execution_id: str, graph_name: str):
    """Execute workflow with WebSocket notifications."""

    try:
        # Signal start
        await notifier.on_execution_start(execution_id, graph_name)

        # Execute nodes
        for node in nodes:
            try:
                await notifier.on_node_start(
                    execution_id,
                    node.id,
                    node.name,
                    node.type
                )

                result = await execute_node(node)

                await notifier.on_node_complete(
                    execution_id,
                    node.id,
                    node.name,
                    output=result,
                    node_type=node.type
                )

            except Exception as e:
                logger.error(f"Node failed: {node.id}: {e}")
                await notifier.on_node_error(
                    execution_id,
                    node.id,
                    node.name,
                    error=str(e),
                    node_type=node.type
                )
                raise

        # Signal completion
        await notifier.on_execution_complete(execution_id, {"status": "success"})

    except Exception as e:
        logger.error(f"Execution failed: {execution_id}: {e}")
        await notifier.on_execution_error(execution_id, str(e))
        raise
```

## Integration Patterns

### Integration with API Layer

The WebSocket service integrates with FastAPI WebSocket routes for real-time communication.

**Execution Monitoring Route:**

```python
# From backend/api/websocket/execution.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.websocket import manager as ws_manager
from backend.services.websocket import notifier as ws_notifier
import json

router = APIRouter(prefix="/api/ws", tags=["websocket"])

@router.websocket("/execution/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    """Stream real-time execution updates via WebSocket."""

    # Connect client
    await ws_manager.connect(websocket, execution_id)

    try:
        # Send initial execution status from database
        status = get_execution_status_with_nodes(execution_id)
        if status:
            await websocket.send_json({
                "type": "initial_status",
                "execution_id": execution_id,
                "data": status
            })

        # Handle incoming messages
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

            if data == "ping":
                await websocket.send_text("pong")
            elif data == "close":
                break
            else:
                # Handle JSON commands
                try:
                    message = json.loads(data)
                    if message.get("type") == "reconnect":
                        await ws_notifier.handle_reconnect_execution(
                            websocket,
                            execution_id,
                            message.get("thread_id"),
                            message.get("db_execution_id")
                        )
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        pass

    finally:
        ws_manager.disconnect(websocket, execution_id)
```

**HTTP Listener Route:**

```python
# From backend/api/websocket/http_listener.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.websocket import manager as ws_manager

router = APIRouter(prefix="/api/ws", tags=["websocket"])

@router.websocket("/http-listener/{graph_name}")
async def websocket_http_listener(websocket: WebSocket, graph_name: str):
    """Listen for HTTP-triggered execution notifications."""

    await ws_manager.connect_http_listener(websocket, graph_name)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        pass

    finally:
        ws_manager.disconnect_http_listener(websocket, graph_name)
```

**HTTP Execution Handler:**

```python
# From backend/api/http_execution/handlers/execution.py
from backend.services.websocket import manager as ws_manager

async def execute_http_workflow(graph_name: str, input_data: dict, execution_id: str):
    """Execute workflow triggered by HTTP request."""

    # Notify HTTP listeners of execution start
    await ws_manager.broadcast_http_execution_start(
        execution_id=execution_id,
        graph_name=graph_name,
        input_data=input_data
    )

    # Execute workflow
    result = await execute_workflow(graph_name, input_data, execution_id)

    return result
```

### Integration with Other Services

**Execution Engine Integration:**

```python
# From backend/services/execution/engine.py
from backend.services.websocket import notifier as ws_notifier

class ExecutionEngine:
    """Slim execution engine coordinator."""

    def __init__(self, graph_manager):
        self.graph_manager = graph_manager
        self.notifier = ws_notifier
        # ... other initialisation

    async def execute_workflow(self, execution_id: str, graph_name: str, inputs: dict):
        """Execute a workflow with real-time updates."""

        # Notify execution start
        await self.notifier.on_execution_start(execution_id, graph_name)

        try:
            # Execute nodes
            for node in workflow.nodes:
                await self._execute_node(execution_id, node)

            # Notify completion
            result = {"status": "success", "output": final_output}
            await self.notifier.on_execution_complete(execution_id, result)

            return result

        except Exception as e:
            # Notify error
            await self.notifier.on_execution_error(execution_id, str(e))
            raise

    async def _execute_node(self, execution_id: str, node):
        """Execute a single node with updates."""

        # Notify node start
        await self.notifier.on_node_start(
            execution_id,
            node.id,
            node.name,
            node.type
        )

        try:
            # Execute
            result = await node.execute()

            # Notify completion
            await self.notifier.on_node_complete(
                execution_id,
                node.id,
                node.name,
                output=result,
                node_type=node.type,
                duration_seconds=node.duration
            )

            return result

        except Exception as e:
            # Notify error
            await self.notifier.on_node_error(
                execution_id,
                node.id,
                node.name,
                error=str(e),
                node_type=node.type
            )
            raise
```

**Checkpoint Service Integration:**

```python
# From backend/services/execution/checkpoint/
from backend.services.websocket import notifier

async def handle_checkpoint_pause(execution_id: str, checkpoint_id: str, prompt: str):
    """Handle checkpoint pause with WebSocket notification."""

    # Notify node pause
    await notifier.on_node_paused(
        execution_id,
        checkpoint_id,
        "Manual Approval Checkpoint",
        node_type="CHECKPOINT"
    )

    # Notify execution pause with checkpoint details
    await notifier.on_execution_paused(
        execution_id,
        payload={
            "checkpoint_id": checkpoint_id,
            "prompt": prompt,
            "thread_id": thread_id,
            "db_execution_id": db_execution_id
        }
    )

    # Wait for resumption...
```

**Email Resumption Integration:**

```python
# From backend/api/email/handlers/resumption.py
from backend.services.websocket import notifier

async def handle_email_resumption(execution_id: str, user_response: str):
    """Handle email-based checkpoint resumption."""

    # Notify execution resumed
    await notifier.on_execution_resumed(
        execution_id,
        payload={"user_response": user_response, "source": "email"}
    )

    # Resume execution
    await resume_execution(execution_id, user_response)
```

### Dependency Flow

```
Frontend WebSocket Client
         ↓ connects to
FastAPI WebSocket Routes (/api/ws/execution/{id}, /api/ws/http-listener/{graph})
         ↓ uses
WebSocket Service (manager, notifier)
         ↑ called by
Execution Engine (backend/services/execution/)
         ↓ uses
Database Service (backend/services/database/)
         ↓ queries
Database Models (backend/models/)
```

**What services this module depends on:**

- `backend.services.config` - Logger configuration
- `backend.services.database` - Database access for reconnection
- `backend.models` - Database models for execution loading

**What services depend on this module:**

- `backend.api.websocket` - WebSocket API routes
- `backend.api.http_execution` - HTTP execution handlers
- `backend.services.execution.engine` - Execution engine
- `backend.services.email.polling` - Email checkpoint resumption
- `backend.services.nodes.handlers` - Node execution handlers

### Common Integration Patterns

#### Pattern 1: Execution Lifecycle Notifications

Standard pattern for notifying clients of execution lifecycle events:

```python
from backend.services.websocket import notifier

async def execute_workflow(execution_id: str, graph_name: str, inputs: dict):
    """Execute workflow with full lifecycle notifications."""

    # Start
    await notifier.on_execution_start(execution_id, graph_name)

    try:
        for node in nodes:
            # Node start
            await notifier.on_node_start(
                execution_id, node.id, node.name, node.type
            )

            # Execute
            result = await execute_node(node)

            # Node complete
            await notifier.on_node_complete(
                execution_id, node.id, node.name, output=result
            )

        # Complete
        await notifier.on_execution_complete(execution_id, final_result)

    except Exception as e:
        # Error
        await notifier.on_execution_error(execution_id, str(e))
        raise
```

#### Pattern 2: HTTP Execution Notification

Pattern for notifying listeners when HTTP triggers workflow execution:

```python
from backend.services.websocket import manager

async def handle_http_trigger(graph_name: str, input_data: dict):
    """Handle HTTP-triggered workflow execution."""

    # Generate execution ID
    execution_id = generate_execution_id()

    # Notify HTTP listeners
    await manager.broadcast_http_execution_start(
        execution_id=execution_id,
        graph_name=graph_name,
        input_data=input_data
    )

    # Execute workflow
    result = await execute_workflow(execution_id, graph_name, input_data)

    return {"execution_id": execution_id, "result": result}
```

#### Pattern 3: Checkpoint Pause/Resume

Pattern for handling checkpoint-based pauses and resumptions:

```python
from backend.services.websocket import notifier

async def handle_checkpoint(execution_id: str, checkpoint_config: dict):
    """Handle checkpoint pause."""

    # Pause node
    await notifier.on_node_paused(
        execution_id,
        checkpoint_config["node_id"],
        checkpoint_config["node_name"],
        node_type="CHECKPOINT"
    )

    # Pause execution with checkpoint details
    await notifier.on_execution_paused(
        execution_id,
        payload={
            "checkpoint_id": checkpoint_config["checkpoint_id"],
            "prompt": checkpoint_config["prompt"],
            "thread_id": checkpoint_config["thread_id"]
        }
    )

    # Wait for resumption (blocking or async)
    user_input = await wait_for_checkpoint_resumption(execution_id)

    # Resume
    await notifier.on_execution_resumed(
        execution_id,
        payload={"user_input": user_input}
    )

    # Continue execution
    return user_input
```

#### Pattern 4: Client Reconnection

Pattern for handling client reconnection after disconnection:

```python
from backend.services.websocket import notifier
import json

@router.websocket("/ws/execution/{execution_id}")
async def websocket_route(websocket: WebSocket, execution_id: str):
    """WebSocket route with reconnection support."""

    await manager.connect(websocket, execution_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                if message.get("type") == "reconnect":
                    # Handle reconnection
                    await notifier.handle_reconnect_execution(
                        websocket,
                        execution_id,
                        thread_id=message.get("thread_id"),
                        db_execution_id=message.get("db_execution_id")
                    )

            except json.JSONDecodeError:
                # Handle non-JSON messages
                if data == "ping":
                    await websocket.send_text("pong")

    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(websocket, execution_id)
```

## Usage Examples

### Example 1: Basic WebSocket Connection in API Route

Complete example of a basic WebSocket route for execution monitoring:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.websocket import manager
from backend.services.config import get_logger

router = APIRouter()
logger = get_logger("websocket_basic")

@router.websocket("/ws/execution/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    """Basic WebSocket endpoint for execution monitoring."""

    logger.info(f"Client connecting to execution: {execution_id}")

    # Step 1: Connect the WebSocket
    await manager.connect(websocket, execution_id)

    try:
        # Step 2: Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "execution_id": execution_id,
            "message": "Successfully connected to execution"
        })

        # Step 3: Keep connection alive
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            # Handle ping-pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "close":
                logger.info(f"Client requested close: {execution_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {execution_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        # Step 4: Clean up connection
        manager.disconnect(websocket, execution_id)
        logger.info(f"Connection cleanup complete: {execution_id}")
```

### Example 2: Execution Engine Integration

Complete example showing execution engine integration with WebSocket notifications:

```python
from backend.services.websocket import notifier
from backend.services.graph import GraphManager
from backend.services.config import get_logger
from typing import Any, Dict

logger = get_logger("execution_example")

class SimpleExecutionEngine:
    """Simple execution engine with WebSocket notifications."""

    def __init__(self, graph_manager: GraphManager):
        self.graph_manager = graph_manager
        self.notifier = notifier

    async def execute_workflow(
        self,
        execution_id: str,
        graph_name: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a workflow with full WebSocket notifications."""

        logger.info(f"Starting execution: {execution_id}")

        # Step 1: Load workflow graph
        graph = self.graph_manager.get_graph(graph_name)

        # Step 2: Notify execution start
        await self.notifier.on_execution_start(execution_id, graph_name)

        try:
            # Step 3: Execute each node in sequence
            state = inputs.copy()

            for node in graph.nodes:
                logger.info(f"Executing node: {node.id}")

                # Notify node start
                await self.notifier.on_node_start(
                    execution_id=execution_id,
                    node_id=node.id,
                    node_name=node.name,
                    node_type=node.type,
                    execution_order=node.order
                )

                try:
                    # Execute node
                    import time
                    start_time = time.time()

                    result = await self._execute_node(node, state)

                    duration = time.time() - start_time

                    # Update state
                    state[node.id] = result

                    # Notify node completion
                    await self.notifier.on_node_complete(
                        execution_id=execution_id,
                        node_id=node.id,
                        node_name=node.name,
                        output=result,
                        node_type=node.type,
                        duration_seconds=duration,
                        input_data=state.get("input"),
                        start_time=time.strftime("%Y-%m-%dT%H:%M:%S"),
                        end_time=time.strftime("%Y-%m-%dT%H:%M:%S")
                    )

                except Exception as e:
                    logger.error(f"Node failed: {node.id}: {e}")

                    # Notify node error
                    await self.notifier.on_node_error(
                        execution_id=execution_id,
                        node_id=node.id,
                        node_name=node.name,
                        error=str(e),
                        node_type=node.type
                    )

                    raise

            # Step 4: Prepare final result
            final_result = {
                "status": "success",
                "output": state.get("final_output", state),
                "nodes_executed": len(graph.nodes)
            }

            # Step 5: Notify execution completion
            await self.notifier.on_execution_complete(
                execution_id=execution_id,
                result=final_result
            )

            logger.info(f"Execution completed: {execution_id}")
            return final_result

        except Exception as e:
            logger.error(f"Execution failed: {execution_id}: {e}")

            # Notify execution error
            await self.notifier.on_execution_error(
                execution_id=execution_id,
                error=str(e)
            )

            raise

    async def _execute_node(self, node, state):
        """Execute a single node (simplified)."""
        # Node execution logic here
        return {"result": f"Executed {node.name}"}
```

### Example 3: HTTP Listener Workflow

Complete example showing HTTP listener setup and notification:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.websocket import manager
from backend.services.config import get_logger
import uuid

router = APIRouter()
logger = get_logger("http_listener_example")

# Frontend WebSocket route for listening to HTTP executions
@router.websocket("/ws/http-listener/{graph_name}")
async def http_listener(websocket: WebSocket, graph_name: str):
    """Listen for HTTP-triggered executions of a specific graph."""

    logger.info(f"HTTP listener connecting for graph: {graph_name}")

    # Connect as HTTP listener
    await manager.connect_http_listener(websocket, graph_name)

    try:
        # Keep connection alive
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
            elif data == "close":
                break

    except WebSocketDisconnect:
        logger.info(f"HTTP listener disconnected: {graph_name}")

    finally:
        manager.disconnect_http_listener(websocket, graph_name)

# HTTP API endpoint that triggers execution
@router.post("/api/execute/{graph_name}")
async def execute_http_workflow(graph_name: str, input_data: dict):
    """Execute workflow via HTTP request and notify listeners."""

    # Generate execution ID
    execution_id = str(uuid.uuid4())

    logger.info(f"HTTP execution triggered: {graph_name}, {execution_id}")

    # Step 1: Notify HTTP listeners that execution is starting
    await manager.broadcast_http_execution_start(
        execution_id=execution_id,
        graph_name=graph_name,
        input_data=input_data
    )

    # Step 2: Execute workflow (using execution engine)
    from backend.services.execution import get_executor

    executor = get_executor()
    result = await executor.execute_workflow(
        execution_id=execution_id,
        graph_name=graph_name,
        inputs=input_data
    )

    # Step 3: Return execution ID for monitoring
    return {
        "execution_id": execution_id,
        "graph_name": graph_name,
        "status": "started",
        "message": f"Execution started. Connect to /ws/execution/{execution_id} for updates."
    }
```

### Example 4: Checkpoint Pause and Reconnection

Complete example showing checkpoint handling and client reconnection:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.websocket import manager, notifier
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.models import GraphExecution
import json
import asyncio

router = APIRouter()
logger = get_logger("checkpoint_example")

async def execute_workflow_with_checkpoint(
    execution_id: str,
    graph_name: str,
    inputs: dict
):
    """Execute workflow with checkpoint pause."""

    # Start execution
    await notifier.on_execution_start(execution_id, graph_name)

    # Execute some nodes
    await notifier.on_node_start(
        execution_id, "node-1", "Data Fetch", "HTTP"
    )

    data = await fetch_data()

    await notifier.on_node_complete(
        execution_id, "node-1", "Data Fetch", output=data, node_type="HTTP"
    )

    # Reach checkpoint - pause for human approval
    checkpoint_id = "checkpoint-123"

    logger.info(f"Reaching checkpoint: {checkpoint_id}")

    # Notify node pause
    await notifier.on_node_paused(
        execution_id=execution_id,
        node_id=checkpoint_id,
        node_name="Manual Approval",
        node_type="CHECKPOINT"
    )

    # Notify execution pause with checkpoint details
    await notifier.on_execution_paused(
        execution_id=execution_id,
        payload={
            "checkpoint_id": checkpoint_id,
            "prompt": "Please review the data and approve to continue",
            "thread_id": "thread-456",
            "db_execution_id": "db-exec-789",
            "data": data
        }
    )

    # Wait for resumption (in real code, this would use LangGraph checkpointer)
    # For this example, we'll simulate waiting
    logger.info(f"Waiting for checkpoint resumption: {checkpoint_id}")

    # ... checkpoint wait logic ...

# WebSocket route with reconnection support
@router.websocket("/ws/execution/{execution_id}")
async def websocket_with_reconnection(websocket: WebSocket, execution_id: str):
    """WebSocket route supporting reconnection to paused executions."""

    await manager.connect(websocket, execution_id)

    try:
        # Send initial status from database
        with get_db() as db:
            execution = db.query(GraphExecution).filter(
                GraphExecution.websocket_execution_id == execution_id
            ).first()

            if execution:
                await websocket.send_json({
                    "type": "initial_status",
                    "execution_id": execution_id,
                    "data": {
                        "status": execution.status,
                        "graph_name": execution.graph_name,
                        "db_execution_id": execution.id
                    }
                })

        # Handle messages
        while True:
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=30.0
            )

            if data == "ping":
                await websocket.send_text("pong")

            elif data == "close":
                break

            else:
                # Parse JSON commands
                try:
                    message = json.loads(data)

                    # Handle reconnection request
                    if message.get("type") == "reconnect":
                        logger.info(f"Reconnection requested: {execution_id}")

                        # Restore execution state from database
                        await notifier.handle_reconnect_execution(
                            websocket=websocket,
                            execution_id=execution_id,
                            thread_id=message.get("thread_id"),
                            db_execution_id=message.get("db_execution_id")
                        )

                    # Handle checkpoint resumption
                    elif message.get("type") == "resume_checkpoint":
                        logger.info(f"Checkpoint resumption: {execution_id}")

                        user_input = message.get("user_input")

                        # Notify resumption
                        await notifier.on_execution_resumed(
                            execution_id=execution_id,
                            payload={"user_input": user_input}
                        )

                        # Resume execution (would call actual resume logic)
                        # await resume_execution(execution_id, user_input)

                except json.JSONDecodeError:
                    logger.debug(f"Received non-JSON message: {data}")

    except asyncio.TimeoutError:
        # Keepalive ping
        try:
            await websocket.send_text("ping")
        except Exception:
            logger.warning("Connection lost during ping")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {execution_id}")

    finally:
        manager.disconnect(websocket, execution_id)

async def fetch_data():
    """Simulate data fetching."""
    return {"records": 100, "status": "success"}
```

## Performance Considerations

### Performance Characteristics

**Connection Management:**

- Connection tracking: O(1) for add/remove operations (set operations)
- Lookup by execution_id: O(1) average (dictionary lookup)
- Message broadcast: O(n) where n is number of connected clients for that execution
- Memory usage: O(m + n) where m is number of executions and n is total connections

**Message Broadcasting:**

- Time complexity: O(n) per broadcast, where n is number of connections
- Network I/O: Asynchronous, non-blocking
- Serialisation: O(k) where k is message size (JSON serialisation)

**Reconnection:**

- Database query: O(1) for execution lookup (indexed by ID)
- Node loading: O(n) where n is number of node executions
- State replay: O(n) broadcasts where n is number of nodes

**I/O Characteristics:**

- **I/O-bound:** WebSocket send/receive operations are network I/O
- **Network-bound:** Performance limited by network latency and bandwidth
- **Database I/O:** Reconnection requires database queries (I/O-bound)

### Optimisation Tips

#### Tip 1: Batch Node Updates for Large Workflows

**Problem:**

```python
# Inefficient: Broadcasting many small updates individually
for node in large_workflow.nodes:  # e.g., 1000 nodes
    await notifier.on_node_complete(execution_id, node.id, node.name, output)
    # Each call sends individual WebSocket message
```

**Solution:**

```python
# More efficient: Batch updates when appropriate
# Note: Current implementation doesn't support batching,
# but you can reduce update frequency

# Only send updates for important nodes
if node.type in ["AGENT", "CHECKPOINT"] or node.order % 10 == 0:
    await notifier.on_node_complete(execution_id, node.id, node.name, output)

# Or use a batching wrapper (custom implementation)
async with BatchedNotifier(notifier, execution_id, batch_size=10) as batch:
    for node in large_workflow.nodes:
        batch.add_node_update(node.id, node.name, output)
        # Automatically batches and sends every 10 updates
```

#### Tip 2: Limit Message Payload Size

**Problem:**

```python
# Inefficient: Sending large output data
huge_output = {
    "raw_data": [large_list_with_10000_items],
    "full_response": gigabyte_of_text
}

await notifier.on_node_complete(
    execution_id,
    node.id,
    node.name,
    output=huge_output  # This will be slow to serialise and send
)
```

**Solution:**

```python
# Efficient: Truncate or summarise large outputs
def truncate_output(output, max_size=1000):
    """Truncate large outputs for WebSocket transmission."""
    import json

    serialised = json.dumps(output)

    if len(serialised) > max_size:
        return {
            "summary": "Output truncated due to size",
            "size_bytes": len(serialised),
            "preview": serialised[:max_size] + "..."
        }

    return output

# Send truncated output
truncated = truncate_output(huge_output, max_size=5000)

await notifier.on_node_complete(
    execution_id,
    node.id,
    node.name,
    output=truncated
)
```

#### Tip 3: Clean Up Stale Connections

**Problem:**

```python
# Connections may become stale but remain tracked
# This wastes memory and processing on failed sends
```

**Solution:**

```python
# The ConnectionManager already handles this automatically
# Failed sends during broadcast automatically remove stale connections

# But you can also implement periodic cleanup
async def cleanup_stale_connections():
    """Periodically verify and clean up connections."""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes

        for execution_id in list(manager.active_connections.keys()):
            connections = manager.active_connections[execution_id]

            # Send ping to verify connections
            disconnected = []
            for ws in connections:
                try:
                    await ws.send_text("ping")
                except Exception:
                    disconnected.append(ws)

            # Remove failed connections
            for ws in disconnected:
                manager.disconnect(ws, execution_id)
```

### Async/Await Support

The entire WebSocket service is built on async/await patterns for non-blocking I/O.

**Async Methods:**

All public methods are async (except `disconnect()` which is synchronous):

```python
from backend.services.websocket import manager, notifier

# All connection and notification methods are async
async def example():
    # Async connection management
    await manager.connect(websocket, execution_id)

    # Async message sending
    await manager.send_execution_update(execution_id, "custom", data)
    await manager.send_node_update(execution_id, node_id, node_name, status)
    await manager.send_execution_status(execution_id, "running")
    await manager.broadcast(message)

    # Async HTTP listener methods
    await manager.connect_http_listener(websocket, graph_name)
    await manager.broadcast_http_execution_start(execution_id, graph_name, inputs)

    # Async notifier callbacks
    await notifier.on_execution_start(execution_id, graph_name)
    await notifier.on_node_start(execution_id, node_id, node_name, node_type)
    await notifier.on_node_complete(execution_id, node_id, node_name, output)
    await notifier.on_execution_complete(execution_id, result)

    # Sync disconnection (no await needed)
    manager.disconnect(websocket, execution_id)
```

**Concurrent Execution:**

```python
import asyncio

async def broadcast_to_multiple_executions(executions: list):
    """Send updates to multiple executions concurrently."""

    tasks = [
        notifier.on_node_complete(
            execution_id=exec_id,
            node_id=node_id,
            node_name=node_name,
            output=output
        )
        for exec_id, node_id, node_name, output in executions
    ]

    # Execute all broadcasts concurrently
    await asyncio.gather(*tasks)
```

**Error Handling in Async Code:**

```python
async def safe_notification(execution_id: str):
    """Safely send notifications with error handling."""

    try:
        await notifier.on_node_start(execution_id, "node-1", "Node 1", "AGENT")

        # Execute node
        result = await execute_node()

        await notifier.on_node_complete(execution_id, "node-1", "Node 1", result)

    except asyncio.CancelledError:
        # Handle task cancellation
        logger.warning("Notification cancelled")
        raise

    except Exception as e:
        # Handle other errors
        logger.error(f"Notification failed: {e}")
        await notifier.on_node_error(execution_id, "node-1", "Node 1", str(e))
```

### Connection Pooling

The module maintains connection pools internally using sets and dictionaries:

```python
# Internal connection pooling structure
active_connections: Dict[str, Set[WebSocket]] = {
    "exec-123": {websocket1, websocket2, websocket3},
    "exec-456": {websocket4, websocket5}
}

all_connections: Set[WebSocket] = {
    websocket1, websocket2, websocket3, websocket4, websocket5
}
```

**Best Practices:**

- Connections are automatically pooled by execution_id
- No manual pool management required
- Automatic cleanup on disconnection
- Thread-safe for async operations

### Batch Operations

While the module doesn't provide built-in batching, you can implement batching patterns:

```python
from collections import defaultdict
import asyncio

class BatchedWebSocketNotifier:
    """Batching wrapper for WebSocket notifications."""

    def __init__(self, notifier, batch_size=10, flush_interval=1.0):
        self.notifier = notifier
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batches = defaultdict(list)
        self._flush_task = None

    async def start(self):
        """Start periodic flush task."""
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def add_node_update(self, execution_id, node_id, node_name, status, output):
        """Add node update to batch."""
        self.batches[execution_id].append({
            "node_id": node_id,
            "node_name": node_name,
            "status": status,
            "output": output
        })

        # Flush if batch is full
        if len(self.batches[execution_id]) >= self.batch_size:
            await self._flush_batch(execution_id)

    async def _flush_batch(self, execution_id):
        """Flush batch for execution_id."""
        if execution_id not in self.batches or not self.batches[execution_id]:
            return

        batch = self.batches[execution_id]
        self.batches[execution_id] = []

        # Send batched update
        await self.notifier.manager.send_execution_update(
            execution_id,
            "batch_node_updates",
            {"nodes": batch}
        )

    async def _periodic_flush(self):
        """Periodically flush all batches."""
        while True:
            await asyncio.sleep(self.flush_interval)

            for execution_id in list(self.batches.keys()):
                await self._flush_batch(execution_id)

    async def stop(self):
        """Stop and flush remaining batches."""
        if self._flush_task:
            self._flush_task.cancel()

        for execution_id in list(self.batches.keys()):
            await self._flush_batch(execution_id)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.websocket import (
    ConnectionManager,
    HTTPListenerManager,
    WebSocketExecutionNotifier
)

@pytest.fixture
def connection_manager():
    """Connection manager fixture."""
    return ConnectionManager()

@pytest.fixture
def http_listener_manager():
    """HTTP listener manager fixture."""
    return HTTPListenerManager()

@pytest.fixture
def notifier(connection_manager):
    """Notifier fixture."""
    return WebSocketExecutionNotifier(connection_manager)

@pytest.mark.asyncio
async def test_connect(connection_manager):
    """Test WebSocket connection."""
    # Create mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()

    execution_id = "test-exec-123"

    # Connect
    await connection_manager.connect(mock_ws, execution_id)

    # Verify
    mock_ws.accept.assert_called_once()
    assert mock_ws in connection_manager.all_connections
    assert mock_ws in connection_manager.active_connections[execution_id]

@pytest.mark.asyncio
async def test_disconnect(connection_manager):
    """Test WebSocket disconnection."""
    # Setup
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    execution_id = "test-exec-123"

    await connection_manager.connect(mock_ws, execution_id)

    # Disconnect
    connection_manager.disconnect(mock_ws, execution_id)

    # Verify
    assert mock_ws not in connection_manager.all_connections
    assert execution_id not in connection_manager.active_connections

@pytest.mark.asyncio
async def test_send_execution_update(connection_manager):
    """Test sending execution update."""
    # Setup
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    execution_id = "test-exec-123"
    await connection_manager.connect(mock_ws, execution_id)

    # Send update
    await connection_manager.send_execution_update(
        execution_id,
        "test_event",
        {"key": "value"}
    )

    # Verify
    mock_ws.send_text.assert_called_once()
    call_args = mock_ws.send_text.call_args[0][0]
    assert "test_event" in call_args
    assert "test-exec-123" in call_args

@pytest.mark.asyncio
async def test_notifier_on_node_complete(notifier, connection_manager):
    """Test notifier on_node_complete callback."""
    # Setup
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    execution_id = "test-exec-123"
    await connection_manager.connect(mock_ws, execution_id)

    # Send node complete
    await notifier.on_node_complete(
        execution_id=execution_id,
        node_id="node-456",
        node_name="Test Node",
        output={"result": "success"},
        node_type="AGENT"
    )

    # Verify
    mock_ws.send_text.assert_called_once()
    call_args = mock_ws.send_text.call_args[0][0]
    assert "node_update" in call_args
    assert "completed" in call_args
    assert "Test Node" in call_args
```

### Mocking Dependencies

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.services.websocket.reconnection import handle_reconnect_execution

@pytest.mark.asyncio
@patch('backend.services.websocket.reconnection.handler.get_db')
@patch('backend.services.websocket.reconnection.handler.load_execution_from_db')
async def test_handle_reconnect_execution(mock_load_execution, mock_get_db):
    """Test reconnection handler with mocked database."""

    # Setup mocks
    mock_manager = Mock()
    mock_manager.connect = AsyncMock()
    mock_manager.send_execution_update = AsyncMock()

    mock_notifier = Mock()
    mock_notifier.on_execution_paused = AsyncMock()

    mock_websocket = AsyncMock()

    # Mock database execution
    mock_execution = Mock()
    mock_execution.status = "paused"
    mock_execution.graph_name = "test_graph"

    mock_node = Mock()
    mock_node.node_type = "CHECKPOINT"
    mock_node.status = "paused"
    mock_node.node_metadata = {
        "checkpoint_id": "ckpt-123",
        "prompt": "Test prompt"
    }
    mock_node.node_id = "node-456"

    mock_load_execution.return_value = (mock_execution, [mock_node])

    # Execute
    await handle_reconnect_execution(
        manager=mock_manager,
        notifier=mock_notifier,
        websocket=mock_websocket,
        execution_id="exec-123",
        thread_id="thread-456",
        db_execution_id="db-exec-789"
    )

    # Verify
    mock_manager.connect.assert_called_once_with(mock_websocket, "exec-123")
    mock_manager.send_execution_update.assert_called()
    mock_notifier.on_execution_paused.assert_called_once()
```

### Integration Testing

```python
import pytest
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from backend.services.websocket import connection_manager, notifier

app = FastAPI()

@app.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await connection_manager.connect(websocket, execution_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "close":
                break
    finally:
        connection_manager.disconnect(websocket, execution_id)

@pytest.mark.integration
def test_websocket_integration():
    """Integration test for WebSocket connection."""

    client = TestClient(app)

    with client.websocket_connect("/ws/execution/test-exec-123") as websocket:
        # Connection established

        # Simulate execution update from another task
        async def send_update():
            await asyncio.sleep(0.1)
            await notifier.on_node_start(
                "test-exec-123",
                "node-456",
                "Test Node",
                "AGENT"
            )

        # Run async update in background
        asyncio.run(send_update())

        # Receive update
        data = websocket.receive_json()
        assert data["type"] == "node_update"
        assert data["execution_id"] == "test-exec-123"

        # Close connection
        websocket.send_text("close")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_execution_lifecycle():
    """Integration test for full execution lifecycle."""

    execution_id = "test-exec-integration"

    # Track received messages
    received_messages = []

    # Mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()

    async def track_send(message):
        received_messages.append(message)

    mock_ws.send_text = AsyncMock(side_effect=track_send)

    # Connect
    await connection_manager.connect(mock_ws, execution_id)

    try:
        # Simulate execution
        await notifier.on_execution_start(execution_id, "test_graph")
        await notifier.on_node_start(execution_id, "node-1", "Node 1", "AGENT")
        await notifier.on_node_complete(execution_id, "node-1", "Node 1", {"result": "success"})
        await notifier.on_execution_complete(execution_id, {"final": "result"})

        # Verify messages
        assert len(received_messages) == 4
        assert any("started" in msg for msg in received_messages)
        assert any("completed" in msg for msg in received_messages)

    finally:
        connection_manager.disconnect(mock_ws, execution_id)
```

## Best Practices

### Do's

✅ **Always clean up connections in finally blocks**

```python
@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle messages
    finally:
        # Always disconnect, even on errors
        manager.disconnect(websocket, execution_id)
```

✅ **Use the global singleton instances**

```python
# Recommended
from backend.services.websocket import manager, notifier

await notifier.on_node_start(execution_id, node_id, node_name, node_type)

# Not recommended: creating new instances
from backend.services.websocket import WebSocketExecutionNotifier, ConnectionManager
new_manager = ConnectionManager()  # Don't do this
new_notifier = WebSocketExecutionNotifier(new_manager)  # Don't do this
```

✅ **Implement keepalive pings for long-running connections**

```python
@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout
                )
                # Handle message
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text("ping")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, execution_id)
```

✅ **Handle reconnection for long-running executions**

```python
@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)

    try:
        # Send initial state on connection
        initial_state = load_execution_state(execution_id)
        if initial_state:
            await websocket.send_json({
                "type": "initial_status",
                "data": initial_state
            })

        # Handle reconnection requests
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "reconnect":
                    await notifier.handle_reconnect_execution(
                        websocket,
                        execution_id,
                        message.get("thread_id"),
                        message.get("db_execution_id")
                    )
            except json.JSONDecodeError:
                pass
    finally:
        manager.disconnect(websocket, execution_id)
```

✅ **Log WebSocket events for debugging**

```python
from backend.services.config import get_logger

logger = get_logger("websocket_route")

@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    logger.info(f"Client connecting: {execution_id}")

    await manager.connect(websocket, execution_id)

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message: {execution_id}: {data}")
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {execution_id}")
    finally:
        manager.disconnect(websocket, execution_id)
```

✅ **Send comprehensive metadata in node updates**

```python
await notifier.on_node_complete(
    execution_id=execution_id,
    node_id=node.id,
    node_name=node.name,
    output=result,
    node_type=node.type,
    duration_seconds=duration,
    input_data=input_data,
    start_time=start_time.isoformat(),
    end_time=end_time.isoformat(),
    input_tokens=tokens.input,
    output_tokens=tokens.output,
    total_tokens=tokens.total,
    database_node_id=db_node.id,
    execution_order=order
)
```

### Don'ts

❌ **Don't create multiple ConnectionManager instances**

```python
# Wrong: Creates separate connection pools
from backend.services.websocket import ConnectionManager

manager1 = ConnectionManager()
manager2 = ConnectionManager()

# These won't share connections!
await manager1.connect(ws, execution_id)
await manager2.send_execution_update(execution_id, "event", {})  # Won't reach ws!

# Right: Use global singleton
from backend.services.websocket import manager

await manager.connect(ws, execution_id)
await manager.send_execution_update(execution_id, "event", {})  # Works!
```

❌ **Don't forget to handle WebSocketDisconnect exceptions**

```python
# Wrong: No exception handling
@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)
    while True:
        data = await websocket.receive_text()
        # If client disconnects, this will raise WebSocketDisconnect
        # and connection won't be cleaned up!

# Right: Handle disconnection
@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, execution_id)
```

❌ **Don't send huge payloads via WebSocket**

```python
# Wrong: Sending massive data structures
gigantic_output = {
    "raw_data": [{"item": i} for i in range(1000000)],  # 1 million items
    "full_text": "x" * 10_000_000  # 10 MB of text
}

await notifier.on_node_complete(
    execution_id, node_id, node_name,
    output=gigantic_output  # This will be extremely slow!
)

# Right: Truncate or summarise large outputs
def truncate_large_output(output, max_size=10000):
    import json
    serialised = json.dumps(output)
    if len(serialised) > max_size:
        return {
            "summary": "Output truncated",
            "size": len(serialised),
            "preview": serialised[:max_size]
        }
    return output

await notifier.on_node_complete(
    execution_id, node_id, node_name,
    output=truncate_large_output(gigantic_output)
)
```

❌ **Don't block the event loop with synchronous operations**

```python
# Wrong: Blocking database call
import time

@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)

    # This blocks the entire event loop!
    execution = db.query(GraphExecution).filter(...).first()
    time.sleep(5)  # Blocking sleep

    await websocket.send_json({"data": execution})

# Right: Use async operations
@router.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)

    # Non-blocking database access
    execution = await asyncio.to_thread(load_execution, execution_id)

    # Non-blocking sleep
    await asyncio.sleep(5)

    await websocket.send_json({"data": execution})
```

❌ **Don't ignore send failures silently**

```python
# Wrong: Ignoring failures
try:
    await websocket.send_text(message)
except Exception:
    pass  # Silently ignore - connection may be stale!

# Right: Log and clean up
try:
    await websocket.send_text(message)
except Exception as e:
    logger.error(f"Failed to send message: {e}")
    manager.disconnect(websocket, execution_id)
    raise
```

## Related Documentation

### Related Services

- [execution](./execution.md) - Execution engine service that uses WebSocket notifier for real-time updates
- [checkpoint](./checkpoint.md) - Checkpoint service for human-in-the-loop pauses (uses WebSocket for pause/resume
  notifications)
- [database](./database.md) - Database service used for execution state loading during reconnection
- [config](./config.md) - Configuration service providing logger instances

### Related API Modules

- [WebSocket API](../agents-guide/api/websocket.md) - FastAPI WebSocket routes (`/api/ws/execution/{id}`,
  `/api/ws/http-listener/{graph}`)
- [HTTP Execution API](../agents-guide/api/http_execution.md) - HTTP execution endpoints that notify WebSocket listeners
- [Email API](../agents-guide/api/email.md) - Email checkpoint resumption that uses WebSocket notifications

### Architecture Documentation

- [Real-Time Communication Architecture](../architecture/realtime.md) - Overview of WebSocket communication patterns
- [Execution Architecture](../architecture/execution.md) - How execution engine integrates with WebSocket service
- [Checkpoint Architecture](../architecture/checkpoints.md) - Checkpoint pause/resume flow with WebSocket

### External Documentation

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) - FastAPI WebSocket documentation
- [Python asyncio](https://docs.python.org/3/library/asyncio.html) - Asynchronous I/O documentation
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455) - WebSocket protocol specification

## Summary

The WebSocket service provides a robust, production-ready infrastructure for real-time communication between the
AgenticStudio backend and frontend clients. It enables live streaming of workflow execution updates, node status changes,
checkpoint pauses, and HTTP execution notifications.

The service is built around three core components: `ConnectionManager` for connection tracking and message broadcasting,
`HTTPListenerManager` for HTTP execution notifications, and `WebSocketExecutionNotifier` for execution engine event
callbacks. These components work together seamlessly through the singleton pattern, ensuring consistent connection state
across the application.

A key strength of the service is its reconnection support, which allows clients to restore execution state after
disconnection by loading historical data from the database and replaying node states. This makes the UI resilient to
network interruptions and page refreshes, providing a seamless user experience even during long-running workflows.

**Key Features:**

- Real-time execution and node status updates via WebSocket
- Connection management grouped by execution ID
- HTTP execution listener notifications for external triggers
- Client reconnection with state restoration from database
- Checkpoint pause/resume notifications for human-in-the-loop workflows
- Automatic stale connection cleanup
- Comprehensive event callbacks for execution lifecycle
- Asynchronous, non-blocking I/O for high performance

**Primary Use Cases:**

- Real-time workflow execution monitoring in frontend dashboards
- Live node status updates during multi-step agent workflows
- Checkpoint pause notifications with prompt display to users
- HTTP-triggered execution notifications to listening clients
- Reconnection after network disconnection or page refresh
- Multi-client monitoring of the same execution

**When to Use This Service:**

- When building real-time monitoring interfaces for workflow executions
- When implementing checkpoint/human-in-the-loop functionality
- When notifying UI clients of HTTP-triggered executions
- When creating dashboards that track execution progress live
- When supporting client reconnection to in-progress or paused workflows
- When broadcasting execution events to multiple connected clients simultaneously
