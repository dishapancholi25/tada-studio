# Trace API Module

## Overview

The Trace API module provides execution trace visualization and analysis for AgenticStudio workflows. It transforms flat
execution data into hierarchical trace trees compatible with LangSmith-style visualization, enabling detailed
performance analysis, cost tracking, and debugging capabilities.

**Location:** [backend/api/trace/](../../backend/api/trace/)

**Base Path:** `/api/trace`

**Primary Responsibilities:**

- Build hierarchical trace trees from execution data
- Provide detailed node execution information
- Calculate aggregated execution statistics
- Export traces in multiple formats (JSON, YAML, OpenTelemetry)
- Stream real-time execution updates via WebSocket
- Track LLM token usage and costs
- Support debugging and performance analysis

## Architecture

### Module Structure

```
backend/api/trace/
├── __init__.py           # Module exports (router, websocket_router)
├── routes.py             # REST API endpoints (124 lines)
└── websocket.py          # WebSocket streaming endpoint (52 lines)
```

**Note:** This module has a simplified architecture with no separate models.py or handlers/ directory. Route handlers
directly call services, making it lightweight and focused.

**Service Dependencies:**

```
backend/services/trace/
├── __init__.py              # Service exports
├── tree_builder.py          # Hierarchical trace tree construction (293 lines)
├── statistics.py            # Aggregated metrics calculation (279 lines)
├── export_service.py        # Multi-format export (171 lines)
├── cost_calculator.py       # LLM cost calculation (138 lines)
├── node_mapper.py           # Node type transformation (213 lines)
└── metadata_service.py      # Metadata enrichment
```

### Design Pattern

The Trace API follows a **direct service integration pattern**:

```
HTTP Request / WebSocket
    ↓
Route Handler (routes.py / websocket.py)
    ↓
Trace Services (services/trace/*)
    ↓
Execution History Service
    ↓
Database (PostgreSQL)
```

**Benefits:**

- Minimal overhead for read-heavy operations
- Direct service access for performance
- Simple debugging and testing
- Clear data transformation pipeline

**Data Flow:**

1. Fetch flat execution data from ExecutionHistoryService
2. Transform to hierarchical tree using TraceTreeBuilder
3. Enrich with metadata (costs, tokens, performance)
4. Return to client or stream via WebSocket

## Authentication & Authorisation

### Authentication

Trace endpoints don't explicitly require authentication in the current implementation but rely on execution data access
controls enforced by ExecutionHistoryService.

**Typical Integration:**

```python
from backend.auth.dependencies import get_current_user

# Future authentication pattern
@router.get("/{execution_id}/tree")
async def get_trace_tree(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Verify user has access to this execution
    pass
```

### Authorisation

**Execution-Scoped Access:**

- Users can only access traces for their own workflow executions
- ExecutionHistoryService enforces user-scoping at database level
- Shared workflows grant trace access to authorized users

## API Endpoints

### Trace Visualization (3 endpoints)

#### `GET /api/trace/{execution_id}/tree`

Get hierarchical trace tree for visualizing workflow execution.

**Authentication:** Required (via execution access control)

**Path Parameters:**

- `execution_id` - Execution UUID from workflow execution

**Response:**

```json
{
  "executionId": "exec-abc-123",
  "graphName": "customer-support-workflow",
  "status": "completed",
  "startTime": "2025-10-20T10:30:00.000Z",
  "endTime": "2025-10-20T10:30:15.432Z",
  "duration": 15.432,
  "nodes": [
    {
      "id": "node-exec-1",
      "nodeId": "start",
      "name": "START",
      "type": "start",
      "status": "completed",
      "startTime": "2025-10-20T10:30:00.000Z",
      "endTime": "2025-10-20T10:30:00.005Z",
      "duration": 0.005,
      "executionOrder": 0,
      "children": [
        {
          "id": "node-exec-2",
          "nodeId": "node-agent-1",
          "name": "Triage Agent",
          "type": "agent",
          "status": "completed",
          "startTime": "2025-10-20T10:30:00.010Z",
          "endTime": "2025-10-20T10:30:03.456Z",
          "duration": 3.446,
          "executionOrder": 1,
          "children": [
            {
              "id": "node-exec-2_llm_0",
              "name": "LLM Call (gpt-4o)",
              "type": "llm",
              "status": "completed",
              "startTime": "2025-10-20T10:30:00.010Z",
              "endTime": "2025-10-20T10:30:03.456Z",
              "duration": 3.446,
              "children": [],
              "metadata": {
                "model": "gpt-4o",
                "provider": "azure_openai",
                "temperature": 0.7,
                "tokens": {
                  "input": 345,
                  "output": 178,
                  "total": 523
                },
                "cost": 0.004123,
                "performance": {
                  "time_to_first_token": 0.234,
                  "tokens_per_second": 151.7,
                  "total_latency_ms": 3446
                }
              },
              "input": {
                "messages": [
                  {
                    "role": "system",
                    "content": "You are a helpful customer support agent..."
                  },
                  {
                    "role": "user",
                    "content": "My account is locked"
                  }
                ]
              },
              "output": "I'll help you unlock your account. Let me check your account status...",
              "error": null,
              "parent_id": "node-exec-2"
            }
          ],
          "metadata": {
            "nodeType": "AGENT",
            "isSubAgent": false,
            "tokens": {
              "input": 345,
              "output": 178,
              "total": 523
            },
            "cost": 0.004123,
            "llm": {
              "model": "gpt-4o",
              "provider": "azure_openai",
              "temperature": 0.7,
              "time_to_first_token": 0.234,
              "tokens_per_second": 151.7
            },
            "tool": {
              "tools_used": ["database_query"],
              "tool_call_count": 2
            }
          },
          "input": {
            "user_query": "My account is locked",
            "user_id": "12345"
          },
          "output": {
            "classification": "technical",
            "priority": "high",
            "agent_response": "Account locked - initiating unlock procedure"
          },
          "error": null,
          "messages": [
            {
              "role": "system",
              "content": "You are a helpful customer support agent..."
            },
            {
              "role": "user",
              "content": "My account is locked"
            },
            {
              "role": "assistant",
              "content": "I'll help you unlock your account..."
            }
          ]
        }
      ],
      "metadata": {
        "nodeType": "START",
        "isSubAgent": false
      },
      "input": {
        "user_query": "My account is locked",
        "user_id": "12345"
      },
      "output": {
        "user_query": "My account is locked",
        "user_id": "12345"
      },
      "error": null,
      "messages": null
    }
  ],
  "metadata": {
    "totalNodes": 8,
    "totalTokens": 1247,
    "totalCost": 0.0234,
    "nodeTypeCounts": {
      "START": 1,
      "AGENT": 3,
      "CONDITION": 1,
      "TOOL": 2,
      "END": 1
    },
    "inputData": {
      "user_query": "My account is locked",
      "user_id": "12345"
    },
    "outputData": {
      "resolution": "Account unlocked successfully",
      "actions_taken": ["password_reset", "notification_sent"]
    },
    "error": null
  }
}
```

**Use Cases:**

- Visualize workflow execution in trace viewer UI
- Debug workflow execution paths
- Understand agent reasoning and tool usage
- Analyze LLM calls and message flow
- Identify performance bottlenecks

**Behaviour:**

- Fetches all node executions for the given execution ID
- Builds hierarchical parent-child relationships
- Extracts LLM calls as child nodes within agents
- Sorts nodes by execution order and start time
- Calculates aggregate metadata (tokens, costs, node counts)
- Handles multiple executions of same node (loops)

**Tree Structure:**

- Root nodes have no `parent_agent_id`
- Child nodes reference parent via `parent_agent_id`
- LLM calls nested under agent nodes
- Tool executions appear as metadata within nodes
- Execution order preserved in sorting

**Node Types:**

- `start` - Workflow entry point
- `end` - Workflow exit point
- `agent` - AI agent with LLM
- `orchestrator` - Orchestrator agent with sub-agents
- `tool` - Tool execution (search, database, etc.)
- `condition` - Conditional branching
- `human` - Human-in-the-loop
- `llm` - Direct LLM call (synthetic node)
- `subgraph` - Subworkflow execution

**Errors:**

- `404` - Execution not found
- `500` - Error building trace tree (logged to server)

#### `GET /api/trace/{execution_id}/nodes/{node_id}`

Get detailed information for a specific node in the execution trace.

**Authentication:** Required (via execution access control)

**Path Parameters:**

- `execution_id` - Execution UUID
- `node_id` - Node database ID (from tree response)

**Response:**

```json
{
  "node": {
    "id": "node-exec-2",
    "node_id": "node-agent-1",
    "node_name": "Triage Agent",
    "node_type": "AGENT",
    "graph_execution_id": "exec-abc-123",
    "status": "completed",
    "start_time": "2025-10-20T10:30:00.010Z",
    "end_time": "2025-10-20T10:30:03.456Z",
    "duration_seconds": 3.446,
    "execution_order": 1,
    "parent_agent_id": null,
    "is_sub_agent": false,
    "input_data": {
      "user_query": "My account is locked",
      "user_id": "12345"
    },
    "output_data": {
      "classification": "technical",
      "priority": "high",
      "agent_response": "Account locked - initiating unlock procedure"
    },
    "error_message": null,
    "input_tokens": 345,
    "output_tokens": 178,
    "total_tokens": 523,
    "total_cost": 0.004123,
    "tokens_per_second": 151.7,
    "time_to_first_token": 0.234,
    "llm_metadata": {
      "model": "gpt-4o",
      "provider": "azure_openai",
      "temperature": 0.7,
      "max_tokens": 2000,
      "streaming": true,
      "time_to_first_token": 0.234,
      "tokens_per_second": 151.7,
      "total_latency_ms": 3446
    },
    "tool_metadata": {
      "tools_used": ["database_query"],
      "tool_call_count": 2,
      "tool_executions": [
        {
          "tool_name": "database_query",
          "timestamp": "2025-10-20T10:30:01.123Z",
          "duration_ms": 234,
          "input": {
            "query": "SELECT * FROM accounts WHERE user_id = ?",
            "params": ["12345"]
          },
          "output": {
            "account_status": "locked",
            "lock_reason": "too_many_failed_attempts"
          },
          "status": "success"
        },
        {
          "tool_name": "database_query",
          "timestamp": "2025-10-20T10:30:02.567Z",
          "duration_ms": 187,
          "input": {
            "query": "UPDATE accounts SET status = 'active' WHERE user_id = ?",
            "params": ["12345"]
          },
          "output": {
            "rows_affected": 1
          },
          "status": "success"
        }
      ]
    },
    "message_structure": {
      "messages": [
        {
          "role": "system",
          "content": "You are a helpful customer support agent..."
        },
        {
          "role": "user",
          "content": "My account is locked"
        },
        {
          "role": "assistant",
          "content": "I'll help you unlock your account. Let me check your account status...",
          "tool_calls": [
            {
              "id": "call_abc123",
              "type": "function",
              "function": {
                "name": "database_query",
                "arguments": "{\"query\": \"SELECT * FROM accounts WHERE user_id = '12345'\"}"
              }
            }
          ]
        },
        {
          "role": "tool",
          "content": "{\"account_status\": \"locked\", \"lock_reason\": \"too_many_failed_attempts\"}",
          "tool_call_id": "call_abc123"
        },
        {
          "role": "assistant",
          "content": "I can see your account is locked due to too many failed login attempts. I'll unlock it now."
        }
      ]
    },
    "orchestration_metadata": null,
    "memory_metadata": null,
    "environment_metadata": {
      "python_version": "3.11.5",
      "platform": "linux"
    }
  },
  "metadata": {
    "hasLLMData": true,
    "hasToolData": true,
    "hasMessages": true,
    "hasOrchestration": false
  }
}
```

**Use Cases:**

- Display detailed node inspector in UI
- Analyze individual node execution
- Debug LLM prompts and responses
- Review tool call inputs and outputs
- Examine message history
- Investigate node failures

**Behaviour:**

- Fetches complete node execution record from database
- Includes all metadata (LLM, tools, orchestration, memory)
- Provides boolean flags for UI to show/hide sections
- Returns full message history for agents
- Includes error details if node failed

**Metadata Fields:**

- `llm_metadata` - LLM configuration, performance metrics
- `tool_metadata` - Tool executions with inputs/outputs
- `message_structure` - Complete message history (agents only)
- `orchestration_metadata` - Sub-agent delegation info (orchestrators)
- `memory_metadata` - Memory operations (if memory enabled)
- `environment_metadata` - Execution environment details

**Errors:**

- `404` - Node not found or execution not found
- `500` - Error fetching node details

#### `GET /api/trace/{execution_id}/stats`

Get aggregated statistics for an execution.

**Authentication:** Required (via execution access control)

**Path Parameters:**

- `execution_id` - Execution UUID

**Response:**

```json
{
  "totalNodes": 8,
  "completedNodes": 8,
  "failedNodes": 0,
  "runningNodes": 0,
  "totalTokens": 1247,
  "totalCost": 0.0234,
  "averageDuration": 1.929,
  "tokensByType": {
    "AGENT": 1247,
    "TOOL": 0,
    "CONDITION": 0
  },
  "costByType": {
    "AGENT": 0.0234
  },
  "costByModel": {
    "gpt-4o": 0.0234
  },
  "performanceMetrics": {
    "averageTokensPerSecond": 151.7,
    "averageTimeToFirstToken": 0.234
  }
}
```

**Use Cases:**

- Display execution summary dashboard
- Track token usage and costs
- Monitor performance metrics
- Compare execution efficiency
- Generate cost reports
- Identify expensive operations

**Behaviour:**

- Queries all nodes for the execution
- Calculates aggregate statistics across all nodes
- Groups metrics by node type and LLM model
- Averages performance metrics
- Handles both completed and failed nodes

**Statistics Calculated:**

- **Node counts:** Total, completed, failed, running
- **Token metrics:** Total tokens, grouped by type
- **Cost metrics:** Total cost, by type, by model
- **Performance:** Average tokens/sec, time to first token
- **Duration:** Average node execution time

**Cost Calculation:**

- Uses model-specific pricing (see CostCalculator)
- Supports GPT-4, GPT-3.5, Claude models
- Pricing in AUD per 1M tokens
- Input and output tokens priced separately

**Model Pricing (per 1M tokens in AUD):**

- `gpt-4o`: Input $3.85, Output $15.42
- `gpt-4o-mini`: Input $0.15, Output $0.60
- `gpt-4-turbo`: Input $10.00, Output $30.00
- `gpt-4`: Input $30.00, Output $60.00
- `claude-3-opus`: Input $15.00, Output $75.00
- `claude-3-sonnet`: Input $3.00, Output $15.00

**Errors:**

- `404` - Execution not found
- `500` - Error calculating statistics

### Export (1 endpoint)

#### `GET /api/trace/{execution_id}/export`

Export trace in various formats for external analysis or integration.

**Authentication:** Required (via execution access control)

**Path Parameters:**

- `execution_id` - Execution UUID

**Query Parameters:**

- `export_format` - Export format: `json`, `yaml`, or `opentelemetry` (default: `json`)

**Response (format=json):**

```json
{
  "executionId": "exec-abc-123",
  "graphName": "customer-support-workflow",
  "status": "completed",
  "startTime": "2025-10-20T10:30:00.000Z",
  "endTime": "2025-10-20T10:30:15.432Z",
  "duration": 15.432,
  "nodes": [
    {
      "id": "node-exec-1",
      "name": "START",
      "type": "start",
      "status": "completed",
      "startTime": "2025-10-20T10:30:00.000Z",
      "endTime": "2025-10-20T10:30:00.005Z",
      "duration": 0.005,
      "children": []
    }
  ],
  "metadata": {
    "totalNodes": 8,
    "totalTokens": 1247,
    "totalCost": 0.0234
  }
}
```

**Response (format=yaml):**

```yaml
executionId: exec-abc-123
graphName: customer-support-workflow
status: completed
startTime: '2025-10-20T10:30:00.000Z'
endTime: '2025-10-20T10:30:15.432Z'
duration: 15.432
nodes:
- id: node-exec-1
  name: START
  type: start
  status: completed
  startTime: '2025-10-20T10:30:00.000Z'
  endTime: '2025-10-20T10:30:00.005Z'
  duration: 0.005
  children: []
metadata:
  totalNodes: 8
  totalTokens: 1247
  totalCost: 0.0234
```

**Response (format=opentelemetry):**

```json
{
  "data": [
    {
      "traceID": "exec-abc-123",
      "spans": [
        {
          "traceId": "exec-abc-123",
          "spanId": "node-exec-1",
          "parentSpanId": null,
          "operationName": "START",
          "startTime": "2025-10-20T10:30:00.000Z",
          "endTime": "2025-10-20T10:30:00.005Z",
          "duration": 0.005,
          "tags": {
            "node.type": "start",
            "node.status": "completed"
          },
          "logs": [],
          "process": {
            "serviceName": "agentic-studio",
            "tags": {}
          }
        },
        {
          "traceId": "exec-abc-123",
          "spanId": "node-exec-2",
          "parentSpanId": "node-exec-1",
          "operationName": "Triage Agent",
          "startTime": "2025-10-20T10:30:00.010Z",
          "endTime": "2025-10-20T10:30:03.456Z",
          "duration": 3.446,
          "tags": {
            "node.type": "agent",
            "node.status": "completed",
            "tokens.total": 523,
            "tokens.input": 345,
            "tokens.output": 178,
            "cost.total": 0.004123,
            "llm.model": "gpt-4o",
            "llm.provider": "azure_openai"
          },
          "logs": [],
          "process": {
            "serviceName": "agentic-studio",
            "tags": {}
          }
        }
      ],
      "processes": {
        "agentic-studio": {
          "serviceName": "agentic-studio",
          "tags": []
        }
      }
    }
  ]
}
```

**Use Cases:**

- Export for external analysis tools
- Import into Jaeger or LangSmith
- Generate reports in YAML format
- Integrate with OpenTelemetry infrastructure
- Backup execution traces
- Share traces with external teams

**Behaviour:**

- Builds trace tree using TraceTreeBuilder
- Converts to requested format using ExportService
- JSON format returns trace tree as-is
- YAML format converts to YAML string
- OpenTelemetry format creates span-based structure

**Export Formats:**

**JSON:**

- Native trace tree format
- Hierarchical structure preserved
- All metadata included
- Directly usable by frontend

**YAML:**

- Human-readable text format
- Same structure as JSON
- Suitable for documentation
- Easy to diff and version control

**OpenTelemetry:**

- Compatible with Jaeger, Zipkin
- Span-based distributed tracing format
- Parent-child relationships via span IDs
- Tags include tokens, costs, LLM metadata
- Service name: "agentic-studio"

**OpenTelemetry Tags:**

- `node.type` - Node type
- `node.status` - Execution status
- `tokens.total` - Total tokens used
- `tokens.input` - Input tokens
- `tokens.output` - Output tokens
- `cost.total` - Total cost
- `llm.model` - LLM model name
- `llm.provider` - LLM provider

**Errors:**

- `404` - Execution not found
- `500` - Error building or exporting trace

### Real-time Streaming (1 endpoint)

#### `WS /api/trace/{execution_id}/stream`

Stream real-time trace updates via WebSocket for live execution monitoring.

**Authentication:** WebSocket connection (handle authentication in connection handshake)

**Path Parameters:**

- `execution_id` - Execution UUID to monitor

**Connection:**

```javascript
const ws = new WebSocket('ws://localhost:8000/api/trace/exec-abc-123/stream');

ws.onopen = () => {
  console.log('Connected to trace stream');
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Trace update:', update);
  // Update UI with new trace tree
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from trace stream');
};
```

**Message Format:**

```json
{
  "type": "trace_update",
  "data": {
    "executionId": "exec-abc-123",
    "graphName": "customer-support-workflow",
    "status": "running",
    "startTime": "2025-10-20T10:30:00.000Z",
    "endTime": null,
    "duration": 0,
    "nodes": [
      {
        "id": "node-exec-1",
        "name": "START",
        "type": "start",
        "status": "completed",
        "children": [
          {
            "id": "node-exec-2",
            "name": "Triage Agent",
            "type": "agent",
            "status": "running",
            "startTime": "2025-10-20T10:30:00.010Z",
            "endTime": null,
            "children": []
          }
        ]
      }
    ],
    "metadata": {
      "totalNodes": 2,
      "totalTokens": 0,
      "totalCost": 0
    }
  }
}
```

**Use Cases:**

- Live execution monitoring in UI
- Real-time trace visualization
- Monitor long-running workflows
- Debug workflows in real-time
- Display execution progress

**Behaviour:**

- Client connects to WebSocket endpoint
- Server accepts connection
- Server polls execution state every 1 second
- Builds fresh trace tree on each poll
- Sends complete tree as JSON message
- Continues until client disconnects or error occurs
- Automatically closes on execution completion (optional)

**Update Frequency:**

- Fixed 1-second polling interval
- Sends updates even if no changes (allows for staleness detection)
- Consider implementing change detection for efficiency

**Connection Lifecycle:**

1. Client initiates WebSocket connection
2. Server accepts and starts polling loop
3. Every second: fetch execution, build tree, send update
4. If error occurs: log error, break loop
5. If client disconnects: WebSocketDisconnect caught, exit cleanly
6. Server closes WebSocket connection

**Performance Considerations:**

- Each update rebuilds entire trace tree
- Database query every second per connection
- Consider caching for high-frequency updates
- Multiple clients each get their own polling loop

**Best Practices:**

```javascript
// Client-side: Reconnect on disconnect
function connectTraceStream(executionId) {
  const ws = new WebSocket(`ws://localhost:8000/api/trace/${executionId}/stream`);

  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    if (update.type === 'trace_update') {
      updateTraceVisualization(update.data);

      // Auto-disconnect when execution completes
      if (update.data.status === 'completed' || update.data.status === 'failed') {
        ws.close();
      }
    }
  };

  ws.onclose = () => {
    // Reconnect if execution still running (check via REST API)
    // setTimeout(() => connectTraceStream(executionId), 2000);
  };

  return ws;
}
```

**Errors:**

- WebSocket disconnect if execution not found
- Connection closes on server error
- Errors logged to server logs

**Alternative: REST Polling:**
For simpler clients, poll `GET /api/trace/{execution_id}/tree` instead:

```javascript
async function pollTraceTree(executionId) {
  while (true) {
    const response = await fetch(`/api/trace/${executionId}/tree`);
    const tree = await response.json();
    updateTraceVisualization(tree);

    if (tree.status !== 'running') break;

    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}
```

## Error Handling

### Error Response Format

All REST endpoints return errors in this format:

```json
{
  "detail": "Execution not found"
}
```

For 500 errors:

```json
{
  "detail": "Error building trace tree: [error details]"
}
```

### Common Error Codes

**Not Found Errors (404):**

- `Execution not found` - Execution ID doesn't exist or user lacks access
- `Node not found` - Node ID doesn't exist in execution

**Server Errors (500):**

- `Error building trace tree: [details]` - Tree construction failed
- `Error fetching node details: [details]` - Node fetch failed
- `Error calculating execution stats: [details]` - Statistics calculation failed
- `Error exporting trace: [details]` - Export conversion failed

**WebSocket Errors:**

- `WebSocketDisconnect` - Client disconnected (logged, not returned)
- `Error sending trace update: [details]` - Update transmission failed (logged)

### Error Handling Example

**Python Client:**

```python
import requests

def get_trace_tree_safe(execution_id: str):
    """Get trace tree with error handling."""
    try:
        response = requests.get(f"http://localhost:8000/api/trace/{execution_id}/tree")
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Execution {execution_id} not found")
            return None
        elif e.response.status_code == 500:
            print(f"Server error building trace: {e.response.json().get('detail')}")
            return None
        else:
            raise
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
```

**JavaScript Client:**

```javascript
async function getTraceTreeSafe(executionId) {
  try {
    const response = await fetch(`/api/trace/${executionId}/tree`);

    if (!response.ok) {
      if (response.status === 404) {
        console.error('Execution not found');
        return null;
      } else if (response.status === 500) {
        const error = await response.json();
        console.error('Server error:', error.detail);
        return null;
      }
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fetch trace tree:', error);
    return null;
  }
}
```

## Integration with Services Layer

### Dependency Flow

```
Trace API Routes
    ↓
┌─────────────────────────────────────┐
│    Trace Services Layer             │
├─────────────────────────────────────┤
│ - TraceTreeBuilder                  │
│ - StatisticsService                 │
│ - ExportService                     │
│ - CostCalculator                    │
│ - NodeMapper                        │
│ - TraceMetadataService              │
└─────────────────────────────────────┘
    ↓
ExecutionHistoryService
    ↓
Database (PostgreSQL)
```

### Example Integration

**Route Handler:**

```python
# backend/api/trace/routes.py
from backend.services.execution.history import ExecutionHistoryService
from backend.services.trace import TraceTreeBuilder

@router.get("/{execution_id}/tree")
async def get_trace_tree(execution_id: str) -> Dict[str, Any]:
    """Get hierarchical trace tree for an execution."""
    try:
        # Step 1: Fetch flat execution data
        execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

        if not execution_data:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Step 2: Build hierarchical tree
        trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

        return trace_tree

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building trace tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Tree Building Process:**

```python
# backend/services/trace/tree_builder.py
class TraceTreeBuilder:
    """Build hierarchical trace tree from flat execution data."""

    @classmethod
    def build_trace_tree(cls, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform flat execution data into hierarchical trace tree."""
        builder = cls()
        nodes = execution_data.get("node_executions", [])

        # Step 1: Create trace nodes and build lookup maps
        builder._build_node_map(nodes)

        # Step 2: Build parent-child relationships
        builder._build_hierarchy(nodes)

        # Step 3: Sort by execution order
        builder._sort_tree()

        # Step 4: Calculate aggregate metadata
        metadata = builder._calculate_metadata(execution_data, nodes)

        return {
            "executionId": execution_data["id"],
            "graphName": execution_data["graph_name"],
            "status": execution_data["status"],
            "nodes": builder.root_nodes,
            "metadata": metadata
        }
```

**Statistics Calculation:**

```python
# backend/services/trace/statistics.py
class StatisticsService:
    """Calculate aggregated statistics for trace executions."""

    @classmethod
    def calculate_execution_stats(cls, nodes: List[Any]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for an execution."""
        return {
            "totalNodes": len(nodes),
            "completedNodes": cls._count_by_status(nodes, "completed"),
            "totalTokens": cls._sum_tokens(nodes),
            "totalCost": CostCalculator.calculate_total_cost(nodes),
            "costByModel": cls._group_cost_by_model(nodes),
            "performanceMetrics": cls._calculate_performance_metrics(nodes)
        }
```

### Services Used

**ExecutionHistoryService** ([backend/services/execution/history/](../../backend/services/execution/history/))

- Fetches execution and node execution data from database
- Provides `get_graph_execution_dict()` for complete execution data
- Provides `get_node_execution()` for individual node details
- Enforces user-scoped access control
- Handles ORM to dictionary conversion

**TraceTreeBuilder** ([backend/services/trace/tree_builder.py](../../services/trace/tree_builder.py))

- Transforms flat node list into hierarchical tree
- Builds parent-child relationships
- Extracts LLM calls as child nodes
- Sorts nodes by execution order
- Handles duplicate node executions (loops)
- Calculates aggregate metadata

**StatisticsService** ([backend/services/trace/statistics.py](../../services/trace/statistics.py))

- Calculates aggregated metrics across nodes
- Groups tokens and costs by type and model
- Computes performance averages
- Counts node statuses
- Handles both ORM objects and dictionaries

**ExportService** ([backend/services/trace/export_service.py](../../services/trace/export_service.py))

- Exports traces in multiple formats
- JSON export (pass-through)
- YAML export with formatting
- OpenTelemetry span conversion
- Tag extraction and mapping

**CostCalculator** ([backend/services/trace/cost_calculator.py](../../services/trace/cost_calculator.py))

- Calculates LLM costs from token usage
- Model-specific pricing (GPT-4, Claude, etc.)
- Supports AUD and USD pricing
- Per-node and aggregate cost calculation
- Enriches nodes with cost metadata

**NodeMapper** ([backend/services/trace/node_mapper.py](../../services/trace/node_mapper.py))

- Maps internal node types to trace viewer types
- Transforms database nodes to trace nodes
- Extracts LLM calls from agent executions
- Builds comprehensive metadata
- Preserves message history

**TraceMetadataService
** ([backend/services/trace/metadata_service.py](../../services/trace/metadata_service.py))

- Enriches traces with additional metadata
- Provides metadata extraction utilities
- (Implementation details not examined)

## Usage Examples

### Complete Trace Visualization Workflow

**Python Example:**

```python
import requests
import time

BASE_URL = "http://localhost:8000"

def visualize_execution_trace(execution_id: str):
    """Complete workflow for visualizing an execution trace."""

    # Step 1: Get trace tree
    print(f"Fetching trace tree for execution {execution_id}...")
    response = requests.get(f"{BASE_URL}/api/trace/{execution_id}/tree")

    if response.status_code == 404:
        print("Execution not found")
        return

    response.raise_for_status()
    trace_tree = response.json()

    # Step 2: Display execution summary
    print(f"\n{'='*60}")
    print(f"Execution: {trace_tree['graphName']}")
    print(f"Status: {trace_tree['status']}")
    print(f"Duration: {trace_tree['duration']:.2f}s")
    print(f"{'='*60}\n")

    # Step 3: Get statistics
    print("Fetching execution statistics...")
    response = requests.get(f"{BASE_URL}/api/trace/{execution_id}/stats")
    response.raise_for_status()
    stats = response.json()

    # Step 4: Display statistics
    print(f"Total Nodes: {stats['totalNodes']}")
    print(f"Completed: {stats['completedNodes']}")
    print(f"Failed: {stats['failedNodes']}")
    print(f"Total Tokens: {stats['totalTokens']}")
    print(f"Total Cost: ${stats['totalCost']:.4f}")
    print(f"\nCost by Model:")
    for model, cost in stats['costByModel'].items():
        print(f"  {model}: ${cost:.4f}")

    # Step 5: Examine individual nodes
    print(f"\nNode Execution Tree:")
    print_trace_tree(trace_tree['nodes'], indent=0)

    # Step 6: Export for external analysis
    print(f"\nExporting to OpenTelemetry format...")
    response = requests.get(
        f"{BASE_URL}/api/trace/{execution_id}/export",
        params={"export_format": "opentelemetry"}
    )
    response.raise_for_status()
    otel_trace = response.json()

    print(f"Exported {len(otel_trace['data'][0]['spans'])} spans")
    print(f"Trace ID: {otel_trace['data'][0]['traceID']}")

    # Step 7: Get detailed node information
    if trace_tree['nodes']:
        first_node = trace_tree['nodes'][0]
        if first_node.get('children'):
            agent_node = first_node['children'][0]

            print(f"\nExamining node: {agent_node['name']}")
            response = requests.get(
                f"{BASE_URL}/api/trace/{execution_id}/nodes/{agent_node['id']}"
            )
            response.raise_for_status()
            node_details = response.json()

            print(f"  Type: {node_details['node']['node_type']}")
            print(f"  Status: {node_details['node']['status']}")
            print(f"  Duration: {node_details['node']['duration_seconds']:.3f}s")

            if node_details['metadata']['hasLLMData']:
                llm = node_details['node']['llm_metadata']
                print(f"  Model: {llm['model']}")
                print(f"  Tokens: {node_details['node']['total_tokens']}")
                print(f"  Cost: ${node_details['node']['total_cost']:.4f}")
                print(f"  Tokens/sec: {llm.get('tokens_per_second', 0):.1f}")

            if node_details['metadata']['hasToolData']:
                tools = node_details['node']['tool_metadata']
                print(f"  Tools used: {', '.join(tools['tools_used'])}")
                print(f"  Tool calls: {tools['tool_call_count']}")

def print_trace_tree(nodes, indent=0):
    """Recursively print trace tree."""
    for node in nodes:
        prefix = "  " * indent
        status_symbol = "✓" if node['status'] == 'completed' else "✗"
        print(f"{prefix}{status_symbol} {node['name']} ({node['type']}) - {node.get('duration', 0):.3f}s")

        if node.get('children'):
            print_trace_tree(node['children'], indent + 1)

# Execute the workflow
visualize_execution_trace("exec-abc-123")
```

**Output:**

```
Fetching trace tree for execution exec-abc-123...

============================================================
Execution: customer-support-workflow
Status: completed
Duration: 15.43s
============================================================

Fetching execution statistics...
Total Nodes: 8
Completed: 8
Failed: 0
Total Tokens: 1247
Total Cost: $0.0234

Cost by Model:
  gpt-4o: $0.0234

Node Execution Tree:
✓ START (start) - 0.005s
  ✓ Triage Agent (agent) - 3.446s
    ✓ LLM Call (gpt-4o) (llm) - 3.446s
  ✓ Priority Router (condition) - 0.012s
  ✓ Response Agent (agent) - 2.134s
    ✓ LLM Call (gpt-4o) (llm) - 2.134s
✓ END (end) - 0.003s

Exporting to OpenTelemetry format...
Exported 8 spans
Trace ID: exec-abc-123

Examining node: Triage Agent
  Type: AGENT
  Status: completed
  Duration: 3.446s
  Model: gpt-4o
  Tokens: 523
  Cost: $0.0041
  Tokens/sec: 151.7
  Tools used: database_query
  Tool calls: 2
```

### Real-time Trace Monitoring

**JavaScript Example:**

```javascript
class TraceMonitor {
  constructor(executionId) {
    this.executionId = executionId;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    console.log(`Connecting to trace stream for ${this.executionId}...`);

    this.ws = new WebSocket(
      `ws://localhost:8000/api/trace/${this.executionId}/stream`
    );

    this.ws.onopen = () => {
      console.log('✓ Connected to trace stream');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      this.handleTraceUpdate(update);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('Disconnected from trace stream');
      this.handleDisconnect();
    };
  }

  handleTraceUpdate(update) {
    if (update.type !== 'trace_update') return;

    const trace = update.data;

    console.log(`\n${'='.repeat(60)}`);
    console.log(`Status: ${trace.status}`);
    console.log(`Nodes: ${trace.metadata.totalNodes}`);
    console.log(`Tokens: ${trace.metadata.totalTokens}`);
    console.log(`Cost: $${trace.metadata.totalCost.toFixed(4)}`);

    // Display currently executing nodes
    const runningNodes = this.findRunningNodes(trace.nodes);
    if (runningNodes.length > 0) {
      console.log(`\nCurrently running:`);
      runningNodes.forEach(node => {
        const elapsed = this.calculateElapsed(node.startTime);
        console.log(`  - ${node.name} (${elapsed.toFixed(1)}s)`);
      });
    }

    // Auto-disconnect when complete
    if (trace.status === 'completed' || trace.status === 'failed') {
      console.log(`\nExecution ${trace.status}! Disconnecting...`);
      this.ws.close();
    }
  }

  findRunningNodes(nodes) {
    const running = [];

    const traverse = (nodeList) => {
      for (const node of nodeList) {
        if (node.status === 'running') {
          running.push(node);
        }
        if (node.children) {
          traverse(node.children);
        }
      }
    };

    traverse(nodes);
    return running;
  }

  calculateElapsed(startTime) {
    if (!startTime) return 0;
    const start = new Date(startTime);
    const now = new Date();
    return (now - start) / 1000;
  }

  handleDisconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      console.log(`Reconnecting in ${delay/1000}s... (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const monitor = new TraceMonitor('exec-abc-123');
monitor.connect();

// Disconnect after 60 seconds
setTimeout(() => {
  console.log('\nStopping monitor...');
  monitor.disconnect();
}, 60000);
```

### Export and Integration

**Export to YAML for Documentation:**

```python
import requests
import yaml

def export_trace_to_yaml(execution_id: str, output_file: str):
    """Export trace to YAML file for documentation."""
    response = requests.get(
        f"http://localhost:8000/api/trace/{execution_id}/export",
        params={"export_format": "yaml"}
    )
    response.raise_for_status()

    # Response is YAML string
    yaml_content = response.text

    # Save to file
    with open(output_file, 'w') as f:
        f.write(yaml_content)

    print(f"Trace exported to {output_file}")

export_trace_to_yaml("exec-abc-123", "execution_trace.yaml")
```

**Import into Jaeger (OpenTelemetry):**

```python
import requests
import json

def send_to_jaeger(execution_id: str, jaeger_url: str):
    """Send trace to Jaeger using OpenTelemetry format."""
    # Get trace in OpenTelemetry format
    response = requests.get(
        f"http://localhost:8000/api/trace/{execution_id}/export",
        params={"export_format": "opentelemetry"}
    )
    response.raise_for_status()
    otel_trace = response.json()

    # Send to Jaeger collector
    jaeger_response = requests.post(
        f"{jaeger_url}/api/traces",
        json=otel_trace,
        headers={"Content-Type": "application/json"}
    )
    jaeger_response.raise_for_status()

    trace_id = otel_trace['data'][0]['traceID']
    print(f"Trace sent to Jaeger: {trace_id}")
    print(f"View at: {jaeger_url}/trace/{trace_id}")

send_to_jaeger("exec-abc-123", "http://localhost:16686")
```

**Cost Report Generation:**

```python
import requests
from datetime import datetime, timedelta

def generate_cost_report(execution_ids: list):
    """Generate cost report for multiple executions."""
    total_cost = 0
    total_tokens = 0
    model_breakdown = {}

    print("Execution Cost Report")
    print("=" * 80)
    print(f"{'Execution ID':<40} {'Tokens':<12} {'Cost':<10}")
    print("-" * 80)

    for exec_id in execution_ids:
        response = requests.get(f"http://localhost:8000/api/trace/{exec_id}/stats")
        if response.status_code != 200:
            continue

        stats = response.json()
        total_cost += stats['totalCost']
        total_tokens += stats['totalTokens']

        print(f"{exec_id:<40} {stats['totalTokens']:<12} ${stats['totalCost']:<10.4f}")

        # Accumulate model breakdown
        for model, cost in stats['costByModel'].items():
            model_breakdown[model] = model_breakdown.get(model, 0) + cost

    print("-" * 80)
    print(f"{'TOTAL':<40} {total_tokens:<12} ${total_cost:<10.4f}")
    print("\nCost by Model:")
    for model, cost in sorted(model_breakdown.items(), key=lambda x: x[1], reverse=True):
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0
        print(f"  {model:<30} ${cost:>10.4f} ({percentage:>5.1f}%)")

# Generate report for recent executions
recent_executions = [
    "exec-abc-123",
    "exec-abc-124",
    "exec-abc-125"
]
generate_cost_report(recent_executions)
```

## Performance Considerations

### Endpoint Performance

**Fast Endpoints (< 500ms):**

- `GET /{execution_id}/tree` - Cached execution data, tree building optimised
- `GET /{execution_id}/stats` - Aggregate calculations efficient
- `GET /{execution_id}/nodes/{node_id}` - Single database query

**Medium Endpoints (500ms - 2s):**

- `GET /{execution_id}/export?format=json` - Tree building + passthrough
- `GET /{execution_id}/export?format=yaml` - Tree building + YAML serialisation

**Potentially Slow Endpoints (> 2s):**

- `GET /{execution_id}/export?format=opentelemetry` - Complex span conversion
- Large executions (>1000 nodes) - Tree building and traversal

**WebSocket Performance:**

- 1-second polling creates constant database load
- Each connected client adds one query per second
- Consider implementing change detection to reduce updates
- Connection overhead: ~5-10ms per message

### Optimisation Tips

**1. Cache Trace Trees for Completed Executions:**

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_trace_tree(execution_id: str, status: str):
    """Cache trace trees for completed executions."""
    if status not in ['completed', 'failed']:
        # Don't cache running executions
        return None

    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
    return TraceTreeBuilder.build_trace_tree(execution_data)

# Use in route
trace_tree = get_cached_trace_tree(execution_id, execution_status)
if trace_tree is None:
    # Build fresh for running executions
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
```

**2. Implement Change Detection for WebSocket:**

```python
import hashlib
import json

last_tree_hash = {}

async def stream_trace_updates(websocket: WebSocket, execution_id: str):
    """Stream updates only when tree changes."""
    await websocket.accept()

    try:
        while True:
            execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
            if not execution_data:
                break

            trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

            # Calculate hash of tree
            tree_json = json.dumps(trace_tree, sort_keys=True)
            tree_hash = hashlib.md5(tree_json.encode()).hexdigest()

            # Only send if changed
            if last_tree_hash.get(execution_id) != tree_hash:
                await websocket.send_json({"type": "trace_update", "data": trace_tree})
                last_tree_hash[execution_id] = tree_hash

            # Check if execution complete
            if trace_tree['status'] in ['completed', 'failed']:
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    finally:
        last_tree_hash.pop(execution_id, None)
```

**3. Use Pagination for Large Traces:**

```python
# For very large executions, consider lazy loading children
@router.get("/{execution_id}/tree")
async def get_trace_tree(
    execution_id: str,
    max_depth: int = Query(default=10, le=50)
):
    """Get trace tree with depth limit."""
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

    # Limit tree depth
    limit_tree_depth(trace_tree['nodes'], max_depth)

    return trace_tree

def limit_tree_depth(nodes, max_depth, current_depth=0):
    """Truncate tree at maximum depth."""
    if current_depth >= max_depth:
        for node in nodes:
            node['children'] = []
        return

    for node in nodes:
        if node.get('children'):
            limit_tree_depth(node['children'], max_depth, current_depth + 1)
```

**4. Database Query Optimization:**

```python
# ExecutionHistoryService should use eager loading
def get_graph_execution_dict(execution_id: str):
    """Fetch execution with all nodes in single query."""
    with get_db() as db:
        execution = db.query(GraphExecution).options(
            joinedload(GraphExecution.node_executions)  # Eager load
        ).filter(GraphExecution.id == execution_id).first()

        if not execution:
            return None

        return execution_to_dict(execution)
```

**5. Compress WebSocket Messages:**

```python
import gzip
import base64

async def stream_trace_updates_compressed(websocket: WebSocket, execution_id: str):
    """Stream compressed trace updates."""
    await websocket.accept()

    try:
        while True:
            execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
            if execution_data:
                trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

                # Compress JSON
                json_str = json.dumps(trace_tree)
                compressed = gzip.compress(json_str.encode())
                encoded = base64.b64encode(compressed).decode()

                await websocket.send_json({
                    "type": "trace_update_compressed",
                    "data": encoded,
                    "encoding": "gzip+base64"
                })

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
```

### Performance Benchmarks

**Typical Performance (100-node execution):**

- Tree building: 50-100ms
- Statistics calculation: 20-30ms
- JSON export: <10ms (passthrough)
- YAML export: 30-50ms
- OpenTelemetry export: 100-200ms
- WebSocket message: 5-10ms

**Large Execution (1000+ nodes):**

- Tree building: 500ms - 2s
- Statistics calculation: 100-200ms
- OpenTelemetry export: 1-3s
- Consider pagination or depth limiting

**WebSocket Load:**

- 1 client: ~1 query/sec
- 10 clients: ~10 queries/sec
- 100 clients: ~100 queries/sec (consider rate limiting)

## Related Documentation

- [Graph API](../../../backend/api/graph/graph.md) - Workflow management and execution
- [Execution History API](../../../backend/api/execution_history/execution_history.md) - Execution records and logs (when documented)
- [WebSocket API](../../../backend/api/websocket/websocket.md) - Real-time workflow updates (when documented)
- [Architecture Overview](../../../docs/architecture/00-overview.md) - System architecture
- [Data Flow Patterns](../../../docs/architecture/02-data-flow.md) - How data flows through the system
- [Services Layer](../services/README.md) - Backend services documentation (when documented)
- [LangSmith Integration](../integrations/langsmith.md) - LangSmith tracing integration (when documented)

## Summary

The Trace API provides comprehensive execution visualization and analysis capabilities for AgenticStudio workflows. As a
focused module with only 5 endpoints, it delivers powerful debugging and monitoring features through a simple, efficient
design.

**Key Features:**

- **Hierarchical Visualization** - Transforms flat execution data into intuitive tree structures
- **Cost Tracking** - Calculates LLM costs with model-specific pricing
- **Real-time Updates** - WebSocket streaming for live execution monitoring
- **Multiple Export Formats** - JSON, YAML, and OpenTelemetry compatibility
- **Performance Metrics** - Token usage, latency, and throughput tracking
- **Detailed Node Inspection** - Full access to inputs, outputs, messages, and metadata
- **LLM Call Extraction** - Separate visualization of individual LLM interactions

**Primary Use Cases:**

1. **Debugging Workflows** - Understand execution paths and identify failures
2. **Performance Analysis** - Identify slow nodes and optimise workflows
3. **Cost Management** - Track token usage and LLM costs across executions
4. **Integration** - Export to Jaeger, LangSmith, or other observability platforms
5. **Real-time Monitoring** - Watch workflows execute in live trace viewer
6. **Report Generation** - Create execution summaries and cost reports

**Architecture Highlights:**

- Simple direct service integration pattern
- No separate handlers or models - lightweight and focused
- Efficient tree building with parent-child relationship mapping
- Comprehensive service layer with modular components
- Support for looping (duplicate node executions)
- LLM call extraction for detailed AI interaction visibility

This module is essential for understanding, debugging, and optimising AgenticStudio workflows, providing
LangSmith-compatible tracing with powerful cost tracking and export capabilities.
