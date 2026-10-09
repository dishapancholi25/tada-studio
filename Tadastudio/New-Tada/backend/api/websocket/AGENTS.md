# WebSocket API Module

## Overview

The WebSocket API module provides real-time bidirectional communication for workflow execution updates in AgenticStudio. It
enables clients to receive live updates about workflow executions, node status changes, and HTTP-triggered execution
notifications through persistent WebSocket connections.

**Location:** [backend/api/websocket/](../../backend/api/websocket/)

**Base Path:** `/api/ws`

**Primary Responsibilities:**

- Real-time execution progress updates
- Node-level execution status streaming
- Execution reconnection support
- HTTP-triggered execution notifications
- Connection lifecycle management (ping/pong heartbeat)

## Architecture

### Module Structure

```
backend/api/websocket/
├── __init__.py                    # Module exports (routers)
├── execution.py                   # Execution WebSocket endpoint
└── http_listener.py               # HTTP listener WebSocket endpoint

backend/services/websocket/
├── __init__.py                    # Service exports and combined manager
├── connection_manager.py          # WebSocket connection management
├── http_listener_manager.py       # HTTP listener connection management
├── notifier.py                    # Execution event notification callbacks
└── reconnection/                  # Reconnection support
    ├── __init__.py
    ├── handler.py                 # Main reconnection handler
    ├── execution_loader.py        # Load execution state from database
    ├── node_state_sender.py       # Send node states to reconnected clients
    └── status_handler.py          # Handle different execution statuses
```

### Design Pattern

The WebSocket API follows an **event-driven notification architecture**:

```
Workflow Execution Engine
    ↓
WebSocketExecutionNotifier (callbacks)
    ↓
ConnectionManager (manages connections)
    ↓
Active WebSocket Connections
    ↓
Client (receives real-time updates)
```

**Message Flow:**

```
Client                    WebSocket Endpoint              Service Layer
  │                              │                              │
  │──── Connect ────────────────>│                              │
  │                              │─── Accept & Register ───────>│
  │<──── initial_status ─────────│                              │
  │                              │                              │
  │                              │<─── Execution Event ─────────│
  │<──── node_update ────────────│                              │
  │                              │                              │
  │──── ping ───────────────────>│                              │
  │<──── pong ───────────────────│                              │
  │                              │                              │
  │──── close ──────────────────>│                              │
  │                              │─── Disconnect ──────────────>│
```

**Benefits:**

- Real-time updates without polling
- Efficient bidirectional communication
- Automatic reconnection support
- Scalable connection management
- Event-driven architecture

## Authentication & Authorisation

### Authentication

WebSocket endpoints in this module **do not require explicit authentication** during the WebSocket handshake. However,
they are typically accessed after the user has been authenticated through the main application flow.

**Connection Pattern:**

```javascript
// Client connects with execution ID
const ws = new WebSocket(`ws://localhost:8000/api/ws/execution/${executionId}`);
```

**Security Considerations:**

- Execution IDs act as capability tokens (knowledge of ID grants access)
- Connections are isolated by execution ID
- No cross-execution data leakage
- Execution IDs are UUIDs (difficult to guess)

### Authorisation

**Connection-Scoped Access:**

- Clients can only receive updates for executions they connect to
- No ability to query or access other executions through WebSocket
- HTTP listener connections scoped by graph name
- Connections automatically isolated by ConnectionManager

**Implementation:**

```python
# In execution.py
@execution_router.websocket("/execution/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    # Connect to specific execution only
    await ws_manager.connect(websocket, execution_id)
    # Client can only receive updates for this execution_id
```

## API Endpoints

### Execution Updates

#### `WS /api/ws/execution/{execution_id}`

Establishes a WebSocket connection to receive real-time updates for a specific workflow execution.

**Protocol:** WebSocket

**Path Parameters:**

- `execution_id` - Unique execution identifier (WebSocket execution ID or database execution ID)

**Connection Flow:**

1. **Client Initiates Connection**
2. **Server Accepts & Sends Initial Status**
3. **Real-time Updates Stream**
4. **Periodic Ping/Pong Heartbeat**
5. **Graceful Disconnection**

**Client Messages (Send):**

```json
// Ping to keep connection alive
"ping"

// Request to close connection
"close"

// Reconnect to existing execution
{
  "type": "reconnect",
  "thread_id": "thread-abc-123",
  "db_execution_id": "db-exec-456"
}
```

**Server Messages (Receive):**

**Initial Status:**

```json
{
  "type": "initial_status",
  "execution_id": "exec-abc-123",
  "data": {
    "status": "running",
    "graph_name": "customer-support-workflow",
    "started_at": "2025-10-20T10:30:00.000Z",
    "completed_at": null,
    "db_execution_id": 42,
    "nodes": [
      {
        "node_id": "start",
        "node_name": "Start",
        "status": "completed",
        "node_type": "START"
      },
      {
        "node_id": "node-agent-1",
        "node_name": "Triage Agent",
        "status": "running",
        "node_type": "AGENT"
      }
    ],
    "node_executions": {
      "start": {
        "id": 101,
        "node_id": "start",
        "node_name": "Start",
        "node_type": "START",
        "status": "completed",
        "execution_order": 0,
        "start_time": "2025-10-20T10:30:00.000Z",
        "end_time": "2025-10-20T10:30:00.010Z",
        "duration_seconds": 0.01,
        "input_data": {"user_query": "Help with account"},
        "output_data": {"user_query": "Help with account"},
        "error_message": null,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "total_cost": 0.0
      }
    }
  }
}
```

**Node Update:**

```json
{
  "type": "node_update",
  "execution_id": "exec-abc-123",
  "timestamp": "2025-10-20T10:30:05.234Z",
  "data": {
    "node_id": "node-agent-1",
    "node_name": "Triage Agent",
    "node_type": "AGENT",
    "status": "completed",
    "output": {
      "classification": "technical_support",
      "priority": "high",
      "response": "I've analyzed your query..."
    },
    "error": null,
    "duration_seconds": 3.421,
    "input_data": {
      "user_query": "Help with account"
    },
    "start_time": "2025-10-20T10:30:01.813Z",
    "end_time": "2025-10-20T10:30:05.234Z",
    "input_tokens": 124,
    "output_tokens": 87,
    "total_tokens": 211,
    "is_sub_agent": false,
    "parent_agent_id": null,
    "database_node_id": "102",
    "execution_order": 1
  }
}
```

**Execution Status:**

```json
{
  "type": "execution_status",
  "execution_id": "exec-abc-123",
  "timestamp": "2025-10-20T10:30:15.456Z",
  "data": {
    "status": "completed",
    "result": {
      "final_output": "Issue resolved successfully",
      "actions_taken": ["password_reset", "notification_sent"]
    },
    "error": null
  }
}
```

**Execution Paused:**

```json
{
  "type": "execution_status",
  "execution_id": "exec-abc-123",
  "timestamp": "2025-10-20T10:30:10.000Z",
  "data": {
    "status": "paused",
    "result": {
      "reason": "human_input_required",
      "checkpoint_id": "checkpoint-123",
      "thread_id": "thread-456"
    },
    "error": null
  }
}
```

**Reconnection Confirmation:**

```json
{
  "type": "reconnected",
  "execution_id": "exec-abc-123",
  "timestamp": "2025-10-20T10:35:00.000Z",
  "data": {
    "status": "running",
    "thread_id": "thread-abc-123",
    "db_execution_id": "42",
    "graph_name": "customer-support-workflow"
  }
}
```

**Heartbeat:**

```json
// Server sends
"ping"

// Client should respond
"pong"
```

**Use Cases:**

- Real-time workflow execution monitoring
- Live dashboard updates
- Progress tracking for long-running workflows
- Debugging execution flow
- User notifications for workflow completion

**Behaviour:**

**Initial Connection:**

1. Client connects to WebSocket endpoint
2. Server accepts connection
3. Server queries database for execution status
4. Server sends `initial_status` with current execution state
5. Server sends all existing node execution states

**Real-time Updates:**

1. Execution engine triggers events (node start, node complete, etc.)
2. WebSocketExecutionNotifier receives callback
3. ConnectionManager sends update to all connected clients for that execution
4. Clients receive JSON messages in real-time

**Heartbeat:**

1. Every 30 seconds, server sends `"ping"` if no client message received
2. Client should respond with `"pong"`
3. Connection closed if ping fails (client disconnected)

**Reconnection:**

1. Client sends reconnect message with `thread_id` and `db_execution_id`
2. Server loads execution state from database
3. Server sends all node states to bring client up to date
4. Server sends current execution status (running, paused, completed)

**Graceful Shutdown:**

1. Client sends `"close"` message
2. Server disconnects WebSocket
3. ConnectionManager removes connection from active connections

**Performance Considerations:**

- Message batching: Updates sent immediately (no batching delay)
- Connection pooling: Each execution can have multiple connected clients
- Automatic cleanup: Failed sends result in automatic disconnection
- Memory efficient: Uses asyncio for concurrent connections

**Errors:**

**Connection Errors:**

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
  // Connection failed - retry with exponential backoff
};
```

**Disconnection:**

```javascript
ws.onclose = (event) => {
  console.log('WebSocket closed:', event.code, event.reason);
  // Reconnect or notify user
};
```

**Message Errors:**

- Invalid JSON: Server logs error, no response sent
- Unknown message type: Server logs warning, ignores message
- Malformed reconnect request: Server logs error, sends reconnect_failed

### HTTP Execution Notifications

#### `WS /api/ws/http-listener/{graph_name}`

Establishes a WebSocket connection to receive notifications when a workflow is triggered via HTTP endpoint. This allows
UI clients to be notified when workflows are executed externally.

**Protocol:** WebSocket

**Path Parameters:**

- `graph_name` - Workflow name to listen for executions

**Client Messages (Send):**

```json
// Ping to keep connection alive
"ping"
```

**Server Messages (Receive):**

**HTTP Execution Started:**

```json
{
  "type": "http_execution_started",
  "execution_id": "exec-http-789",
  "graph_name": "customer-support-workflow",
  "timestamp": "2025-10-20T10:45:00.123Z",
  "data": {
    "input": {
      "user_query": "External API request",
      "source": "api_integration"
    },
    "source": "http"
  }
}
```

**Heartbeat:**

```json
// Client sends
"ping"

// Server responds
"pong"
```

**Use Cases:**

- UI dashboard showing HTTP-triggered executions
- Notification systems for external workflow triggers
- Monitoring external API integrations
- Real-time workflow trigger logs
- Multi-client workflow monitoring

**Behaviour:**

**Connection:**

1. Client connects to HTTP listener endpoint with graph name
2. Server accepts connection
3. HTTPListenerManager registers connection for that graph
4. Client waits for execution notifications

**Notification Broadcast:**

1. External HTTP request triggers workflow execution
2. HTTP execution endpoint notifies HTTPListenerManager
3. Manager broadcasts execution start to all listeners for that graph
4. Clients receive notification with execution ID and input data

**Heartbeat:**

1. Client periodically sends `"ping"` to keep connection alive
2. Server responds with `"pong"`
3. Connection maintained as long as heartbeat continues

**Disconnection:**

1. Client closes connection or heartbeat fails
2. HTTPListenerManager removes connection
3. No further notifications sent to that client

**Integration Pattern:**

```javascript
// UI client listens for HTTP executions
const ws = new WebSocket('ws://localhost:8000/api/ws/http-listener/customer-support-workflow');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'http_execution_started') {
    // Show notification in UI
    showNotification(`Workflow triggered: ${message.execution_id}`);

    // Optionally connect to execution WebSocket for live updates
    connectToExecution(message.execution_id);
  }
};

// Keep connection alive
setInterval(() => {
  ws.send('ping');
}, 25000);
```

**Performance Considerations:**

- Lightweight notifications: Only execution start events sent
- Graph-scoped: Only receive notifications for specific workflows
- Broadcast efficiency: Single event sent to multiple listeners
- No polling overhead: Push-based notifications

**Errors:**

**Disconnection:**

```javascript
ws.onclose = () => {
  // Reconnect after delay
  setTimeout(() => {
    connectHTTPListener(graphName);
  }, 5000);
};
```

## Error Handling

### Error Response Format

WebSocket errors are not sent as JSON error responses. Instead, they manifest as:

**Connection Failures:**

- WebSocket connection refused (server down)
- Invalid execution ID (connection accepted but no updates)
- Network errors (connection drops)

**Message Errors:**

- Invalid JSON: Logged by server, no error sent to client
- Unknown message type: Logged by server, message ignored
- Malformed data: Logged by server, may cause disconnection

### Common Error Scenarios

**Execution Not Found:**

- **Symptom:** Connection established, but no `initial_status` sent
- **Cause:** Invalid execution ID or execution not in database
- **Solution:** Verify execution ID, check execution exists

**Connection Timeout:**

- **Symptom:** Connection closes unexpectedly
- **Cause:** Network issues, server restart, or client heartbeat failure
- **Solution:** Implement reconnection logic with exponential backoff

**Reconnection Failed:**

```json
{
  "type": "reconnect_failed",
  "execution_id": "exec-abc-123",
  "timestamp": "2025-10-20T10:35:00.000Z",
  "data": {
    "error": "Execution not found in database"
  }
}
```

**Database Errors:**

- **Symptom:** No `initial_status` or reconnection data sent
- **Cause:** Database connection failure or query error
- **Solution:** Check database connectivity, verify execution exists

### Error Handling Example

```javascript
class ExecutionWebSocket {
  constructor(executionId) {
    this.executionId = executionId;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/api/ws/execution/${this.executionId}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.stopHeartbeat();
      this.attemptReconnect();
    };
  }

  handleMessage(message) {
    switch (message.type) {
      case 'initial_status':
        this.handleInitialStatus(message.data);
        break;
      case 'node_update':
        this.handleNodeUpdate(message.data);
        break;
      case 'execution_status':
        this.handleExecutionStatus(message.data);
        break;
      case 'reconnected':
        console.log('Reconnected to execution');
        break;
      case 'reconnect_failed':
        console.error('Reconnection failed:', message.data.error);
        break;
      default:
        if (message === 'ping') {
          this.ws.send('pong');
        }
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 25000);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  disconnect() {
    this.ws.send('close');
    this.ws.close();
  }
}
```

## Integration with Services Layer

### Dependency Flow

```
Execution Engine
    ↓
WebSocketExecutionNotifier (callback layer)
    ↓
ConnectionManager (connection management)
    ↓
Active WebSocket Connections (clients)
```

**Separation of Concerns:**

- **API Layer** (`backend/api/websocket/`): WebSocket endpoint handlers
- **Service Layer** (`backend/services/websocket/`): Connection management and notification logic
- **Execution Engine**: Triggers events via notifier callbacks

### Example Integration

**Execution Engine Integration:**

```python
# In workflow execution engine
from backend.services.websocket import notifier

async def execute_node(execution_id: str, node_id: str, node_name: str, node_type: str):
    """Execute a single node and send WebSocket updates."""

    # Notify node start
    await notifier.on_node_start(
        execution_id=execution_id,
        node_id=node_id,
        node_name=node_name,
        node_type=node_type
    )

    try:
        # Execute node logic
        start_time = datetime.now()
        result = await run_node_logic(node_id)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Notify node completion
        await notifier.on_node_complete(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            output=result,
            node_type=node_type,
            duration_seconds=duration,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )

    except Exception as error:
        # Notify node error
        await notifier.on_node_error(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            error=str(error),
            node_type=node_type
        )
        raise
```

**HTTP Execution Notification:**

```python
# In HTTP execution endpoint
from backend.services.websocket import manager

@router.post("/http/execute/{graph_name}")
async def execute_via_http(graph_name: str, input_data: dict):
    """Execute workflow via HTTP and notify listeners."""

    # Start execution
    execution_id = await start_execution(graph_name, input_data)

    # Notify HTTP listeners
    await manager.broadcast_http_execution_start(
        execution_id=execution_id,
        graph_name=graph_name,
        input_data=input_data
    )

    return {"execution_id": execution_id}
```

### Services Used

**ConnectionManager** ([connection_manager.py](../../services/websocket/connection_manager.py))

- Manages active WebSocket connections by execution ID
- Sends updates to connected clients
- Handles connection/disconnection lifecycle
- Provides broadcast capabilities

**HTTPListenerManager** ([http_listener_manager.py](../../services/websocket/http_listener_manager.py))

- Manages HTTP listener WebSocket connections
- Broadcasts HTTP execution start notifications
- Handles listener connection lifecycle
- Scopes listeners by graph name

**WebSocketExecutionNotifier** ([notifier.py](../../services/websocket/notifier.py))

- Provides callback methods for execution engine
- Translates execution events to WebSocket messages
- Delegates to ConnectionManager for message sending
- Handles reconnection logic

**Reconnection Handler** ([reconnection/handler.py](../../services/websocket/reconnection/handler.py))

- Loads execution state from database on reconnection
- Sends historical node states to reconnected clients
- Handles different execution statuses (running, paused, completed)
- Provides seamless reconnection experience

## Usage Examples

### Complete Execution Monitoring Example

```javascript
// Monitor workflow execution with full error handling
class WorkflowMonitor {
  constructor(executionId) {
    this.executionId = executionId;
    this.nodes = new Map();
    this.status = 'unknown';
    this.connect();
  }

  connect() {
    const wsUrl = `ws://localhost:8000/api/ws/execution/${this.executionId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log(`Connected to execution: ${this.executionId}`);
    };

    this.ws.onmessage = (event) => {
      const data = event.data;

      // Handle ping/pong
      if (data === 'ping') {
        this.ws.send('pong');
        return;
      }

      // Parse JSON message
      try {
        const message = JSON.parse(data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket connection closed');
    };
  }

  handleMessage(message) {
    console.log('Received message:', message.type);

    switch (message.type) {
      case 'initial_status':
        this.handleInitialStatus(message.data);
        break;

      case 'node_update':
        this.handleNodeUpdate(message.data);
        break;

      case 'execution_status':
        this.handleExecutionStatus(message.data);
        break;

      case 'reconnected':
        console.log('Reconnected successfully');
        break;
    }
  }

  handleInitialStatus(data) {
    console.log('Initial status:', data.status);
    console.log('Graph name:', data.graph_name);

    this.status = data.status;

    // Process existing node executions
    if (data.node_executions) {
      for (const [nodeId, nodeData] of Object.entries(data.node_executions)) {
        this.nodes.set(nodeId, nodeData);
        this.updateUI(nodeId, nodeData);
      }
    }
  }

  handleNodeUpdate(data) {
    console.log(`Node ${data.node_name} (${data.node_id}): ${data.status}`);

    // Update node state
    this.nodes.set(data.node_id, data);

    // Update UI
    this.updateUI(data.node_id, data);

    // Log performance metrics
    if (data.status === 'completed') {
      console.log(`  Duration: ${data.duration_seconds}s`);
      if (data.total_tokens) {
        console.log(`  Tokens: ${data.total_tokens}`);
      }
    }

    // Log errors
    if (data.error) {
      console.error(`  Error: ${data.error}`);
    }
  }

  handleExecutionStatus(data) {
    console.log('Execution status:', data.status);

    this.status = data.status;

    if (data.status === 'completed') {
      console.log('Execution completed successfully');
      console.log('Result:', data.result);
      this.onComplete(data.result);
    } else if (data.status === 'failed') {
      console.error('Execution failed:', data.error);
      this.onError(data.error);
    } else if (data.status === 'paused') {
      console.log('Execution paused:', data.result);
      this.onPaused(data.result);
    }
  }

  updateUI(nodeId, nodeData) {
    // Update UI elements to reflect node status
    const nodeElement = document.getElementById(`node-${nodeId}`);
    if (nodeElement) {
      nodeElement.className = `node-status-${nodeData.status}`;
      nodeElement.textContent = `${nodeData.node_name}: ${nodeData.status}`;
    }
  }

  onComplete(result) {
    // Handle workflow completion
    console.log('Workflow completed:', result);
  }

  onError(error) {
    // Handle workflow error
    console.error('Workflow failed:', error);
  }

  onPaused(pauseData) {
    // Handle workflow pause (e.g., human-in-the-loop)
    console.log('Workflow paused, awaiting input:', pauseData);
  }

  disconnect() {
    if (this.ws) {
      this.ws.send('close');
      this.ws.close();
    }
  }
}

// Usage
const monitor = new WorkflowMonitor('exec-abc-123');

// Clean up on page unload
window.addEventListener('beforeunload', () => {
  monitor.disconnect();
});
```

### Python Client Example

```python
import asyncio
import json
import websockets

async def monitor_execution(execution_id: str):
    """Monitor workflow execution via WebSocket."""
    uri = f"ws://localhost:8000/api/ws/execution/{execution_id}"

    async with websockets.connect(uri) as websocket:
        print(f"Connected to execution: {execution_id}")

        try:
            while True:
                message = await websocket.recv()

                # Handle ping/pong
                if message == "ping":
                    await websocket.send("pong")
                    continue

                # Parse JSON message
                try:
                    data = json.loads(message)
                    handle_message(data)
                except json.JSONDecodeError:
                    print(f"Invalid JSON: {message}")

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

def handle_message(message: dict):
    """Handle WebSocket message."""
    msg_type = message.get("type")
    data = message.get("data", {})

    if msg_type == "initial_status":
        print(f"Initial status: {data.get('status')}")
        print(f"Graph: {data.get('graph_name')}")

    elif msg_type == "node_update":
        print(f"Node {data.get('node_name')}: {data.get('status')}")
        if data.get("status") == "completed":
            print(f"  Duration: {data.get('duration_seconds')}s")
            print(f"  Tokens: {data.get('total_tokens')}")

    elif msg_type == "execution_status":
        print(f"Execution: {data.get('status')}")
        if data.get("status") == "completed":
            print(f"Result: {data.get('result')}")

# Run monitor
asyncio.run(monitor_execution("exec-abc-123"))
```

### React Hook Example

```javascript
import { useState, useEffect, useRef } from 'react';

/**
 * React hook for monitoring workflow execution via WebSocket
 */
export function useExecutionWebSocket(executionId) {
  const [status, setStatus] = useState('connecting');
  const [nodes, setNodes] = useState({});
  const [executionStatus, setExecutionStatus] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!executionId) return;

    const wsUrl = `ws://localhost:8000/api/ws/execution/${executionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      const data = event.data;

      if (data === 'ping') {
        ws.send('pong');
        return;
      }

      try {
        const message = JSON.parse(data);
        handleMessage(message);
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('error');
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setStatus('disconnected');
    };

    function handleMessage(message) {
      switch (message.type) {
        case 'initial_status':
          setExecutionStatus(message.data.status);
          if (message.data.node_executions) {
            setNodes(message.data.node_executions);
          }
          break;

        case 'node_update':
          setNodes((prev) => ({
            ...prev,
            [message.data.node_id]: message.data,
          }));
          break;

        case 'execution_status':
          setExecutionStatus(message.data.status);
          break;
      }
    }

    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [executionId]);

  return { status, nodes, executionStatus };
}

// Usage in component
function ExecutionMonitor({ executionId }) {
  const { status, nodes, executionStatus } = useExecutionWebSocket(executionId);

  return (
    <div>
      <h2>Execution Status: {executionStatus}</h2>
      <p>WebSocket: {status}</p>

      <div className="nodes">
        {Object.values(nodes).map((node) => (
          <div key={node.node_id} className={`node-${node.status}`}>
            <h3>{node.node_name}</h3>
            <p>Status: {node.status}</p>
            {node.duration_seconds && <p>Duration: {node.duration_seconds}s</p>}
            {node.total_tokens && <p>Tokens: {node.total_tokens}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Performance Considerations

### Endpoint Performance

**Connection Establishment:**

- **Fast (< 100ms):** WebSocket handshake and initial connection
- **Medium (100ms - 1s):** Loading initial status from database
- **Variable:** Depends on execution state complexity

**Message Delivery:**

- **Immediate (< 10ms):** Message sent to connected clients
- **Batching:** No batching - updates sent immediately
- **Throughput:** Can handle hundreds of concurrent connections per execution

### Optimisation Tips

**1. Efficient Connection Management:**

```javascript
// Good: Single WebSocket per execution
const ws = new WebSocket(`ws://localhost:8000/api/ws/execution/${executionId}`);

// Bad: Multiple WebSockets for same execution
const ws1 = new WebSocket(`ws://localhost:8000/api/ws/execution/${executionId}`);
const ws2 = new WebSocket(`ws://localhost:8000/api/ws/execution/${executionId}`);
```

**2. Heartbeat Configuration:**

```javascript
// Good: Reasonable heartbeat interval (25-30 seconds)
setInterval(() => ws.send('ping'), 25000);

// Bad: Too frequent heartbeat (wastes bandwidth)
setInterval(() => ws.send('ping'), 1000);
```

**3. Message Processing:**

```javascript
// Good: Efficient message handling
ws.onmessage = (event) => {
  if (event.data === 'ping') {
    ws.send('pong');
    return;
  }

  const message = JSON.parse(event.data);
  processMessage(message);
};

// Bad: Parsing all messages regardless of type
ws.onmessage = (event) => {
  const message = JSON.parse(event.data); // Fails on "ping"
  processMessage(message);
};
```

**4. Reconnection Strategy:**

```javascript
// Good: Exponential backoff
attemptReconnect() {
  const delay = Math.min(1000 * Math.pow(2, this.attempts), 30000);
  setTimeout(() => this.connect(), delay);
}

// Bad: Immediate reconnect loop (can overwhelm server)
attemptReconnect() {
  this.connect();
}
```

**5. Memory Management:**

```javascript
// Good: Clean up on disconnect
window.addEventListener('beforeunload', () => {
  ws.close();
});

// Good: Limit stored node history
const MAX_NODES = 1000;
if (nodes.size > MAX_NODES) {
  // Remove oldest nodes
  const oldestKey = nodes.keys().next().value;
  nodes.delete(oldestKey);
}
```

**6. Connection Pooling Considerations:**

```python
# Server-side: ConnectionManager efficiently handles multiple connections
# Each execution can have multiple connected clients
# No need for client-side connection pooling
```

## Related Documentation

- [Graph API](../../../backend/api/graph/graph.md) - Workflow management and execution
- [Execution API](../../../backend/api/execution/execution.md) - Synchronous execution endpoints (when documented)
- [HTTP Execution API](../../../backend/api/http_execution/http_execution.md) - HTTP streaming execution (when documented)
- [Architecture: Real-time Updates](../architecture/05-real-time-updates.md) - Real-time architecture (when documented)
- [Services: WebSocket Manager](../../services/websocket.md) - WebSocket service layer (when documented)

## Summary

The WebSocket API provides real-time bidirectional communication for workflow execution monitoring in AgenticStudio. It
enables clients to receive live updates about execution progress, node status changes, and external workflow triggers
through persistent WebSocket connections.

**Key Features:**

- **Real-time Updates:** Instant node and execution status updates
- **Efficient Communication:** Push-based updates, no polling overhead
- **Reconnection Support:** Seamless reconnection with state recovery
- **HTTP Notifications:** Alerts for externally-triggered executions
- **Scalable Architecture:** Handles multiple concurrent connections per execution
- **Developer Friendly:** Simple message format, easy client integration

**Primary Use Cases:**

- Live workflow execution dashboards
- Real-time progress monitoring for long-running workflows
- Debugging and development tooling
- User notifications for workflow completion
- Multi-client workflow monitoring and collaboration

The WebSocket API is essential for building responsive, real-time user interfaces for workflow management and execution
monitoring in AgenticStudio. It complements the REST API by providing instant updates without the overhead of HTTP polling,
making it ideal for production workflow monitoring systems.
