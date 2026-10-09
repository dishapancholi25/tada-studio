# Execution API Module

## Overview

The Execution API module provides endpoints for managing paused workflow executions in AgenticStudio. It enables inspection,
monitoring, and control of workflows that have paused at checkpoint nodes, supporting human-in-the-loop patterns and
workflow approval gates.

**Location:** [backend/api/execution/](../../backend/api/execution/)

**Base Path:** `/api/executions`

**Primary Responsibilities:**

- Query paused executions by graph or across all workflows
- Retrieve complete execution state with node-level history
- Access checkpoint data for resuming paused workflows
- Cancel paused executions
- Provide progress tracking and execution metrics

## Architecture

### Module Structure

```
backend/api/execution/
├── __init__.py           # Module exports (router)
├── models.py             # Pydantic request/response models (171 lines)
└── paused_routes.py      # API endpoint definitions (301 lines)
```

**Key Files:**

- ****init**.py** - Exports the FastAPI router from paused_routes
- **models.py** - 11 Pydantic models for structured request/response data
- **paused_routes.py** - 5 API endpoints with dependency injection

**No Handlers Directory:**
Unlike the graph module, this is a simpler module where routes directly call service layer methods without an
intermediate handler layer.

### Design Pattern

The Execution API follows a **direct service integration pattern**:

```
HTTP Request
    ↓
Route Handler (paused_routes.py)
    ↓
Dependency Injection (get_paused_execution_service)
    ↓
PausedExecutionService (business logic)
    ↓
CheckpointHandler + Database Queries
    ↓
Database / LangGraph Checkpoint Store
```

**Benefits:**

- Simpler architecture for focused functionality
- Direct service calls reduce boilerplate
- Easy to test and maintain
- Clear separation of concerns

**Service Dependencies:**

```python
# Dependency injection pattern
def get_paused_execution_service() -> PausedExecutionService:
    execution_engine = get_execution_engine()
    return PausedExecutionService(execution_engine)
```

## Authentication & Authorisation

### Authentication

**Current Status:** The execution endpoints currently do **not enforce authentication**. This means:

- No user-specific scoping of executions
- All paused executions are visible to all callers
- No authorisation checks on execution access

**Recommendation:** In production, these endpoints should integrate with the OAuth2-Proxy authentication used by other
modules:

```python
from backend.api.auth.dependencies import get_current_user

@router.get("/paused")
async def get_all_paused_executions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
):
    # Filter executions by current_user["id"]
    ...
```

### Authorisation

**User-Scoped Data:** Currently not implemented.

**Future Implementation:**

- Executions should be filtered by user ID
- Users should only see their own paused executions
- Cancellation should require execution ownership
- Checkpoint data should be access-controlled

**Database Session Pattern:**

```python
def get_db():
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## API Endpoints

### Paused Execution Queries (2 endpoints)

#### `GET /api/executions/paused/{graph_name}`

Get all paused executions for a specific graph/workflow with pagination.

**Authentication:** None (should be required)

**Path Parameters:**

- `graph_name` - Name of the graph/workflow to query

**Query Parameters:**

- `skip` - Number of records to skip for pagination (default: 0)
- `limit` - Maximum number of records to return (default: 20, max: 100)

**Response:**

```json
{
  "executions": [
    {
      "execution_id": "exec-abc-123-def-456",
      "thread_id": "thread-789-ghi-012",
      "websocket_execution_id": "ws-exec-345",
      "graph_name": "customer-approval-workflow",
      "paused_at": "2025-10-20T10:30:00Z",
      "checkpoint": {
        "node_id": "checkpoint-approval",
        "node_name": "Manager Approval",
        "checkpoint_id": "chk-1a2b3c4d",
        "prompt": "Please review and approve the customer refund request",
        "last_input": {
          "refund_amount": 150.00,
          "customer_id": "cust-12345",
          "reason": "Product defect"
        },
        "previous_output": {
          "classification": "refund_eligible",
          "risk_score": 0.15,
          "agent_recommendation": "approve"
        }
      },
      "progress": {
        "completed_nodes": 5,
        "total_nodes": 12,
        "percentage": 41.67
      }
    },
    {
      "execution_id": "exec-def-456-ghi-789",
      "thread_id": "thread-012-jkl-345",
      "websocket_execution_id": "ws-exec-678",
      "graph_name": "customer-approval-workflow",
      "paused_at": "2025-10-20T09:15:00Z",
      "checkpoint": {
        "node_id": "checkpoint-approval",
        "node_name": "Manager Approval",
        "checkpoint_id": "chk-5e6f7g8h",
        "prompt": "Please review and approve the customer refund request",
        "last_input": {
          "refund_amount": 350.00,
          "customer_id": "cust-67890",
          "reason": "Wrong item shipped"
        },
        "previous_output": {
          "classification": "refund_eligible",
          "risk_score": 0.08,
          "agent_recommendation": "approve"
        }
      },
      "progress": {
        "completed_nodes": 5,
        "total_nodes": 12,
        "percentage": 41.67
      }
    }
  ],
  "pagination": {
    "total": 47,
    "skip": 0,
    "limit": 20,
    "has_more": true,
    "next_skip": 20
  }
}
```

**Use Cases:**

- Build a task queue UI for a specific workflow
- Monitor pending approval items for a business process
- Track human-in-the-loop workflow states
- Generate workflow-specific dashboards

**Behaviour:**

- Queries database for executions with `status = 'paused'` and matching `graph_name`
- Automatically enforces maximum limit of 100 to prevent performance issues
- Returns checkpoint information including prompt and previous node output
- Calculates progress percentage based on completed vs total nodes
- Provides pagination metadata for building UI controls

**Validation:**

- `graph_name` must be a valid string
- `limit` is automatically capped at 100 even if larger value provided
- `skip` must be non-negative (enforced by FastAPI)

**Performance:**

- Typical response time: 50-200ms for 20 records
- Includes database join to fetch checkpoint node details
- Paginated to prevent large result sets

**Errors:**

- `500 Internal Server Error` - Database query failure or service unavailable
- `503 Service Unavailable` - Execution engine not initialised

#### `GET /api/executions/paused`

Get all paused executions across all graphs, grouped by workflow name.

**Authentication:** None (should be required)

**Response:**

```json
{
  "total_paused": 73,
  "by_graph": {
    "customer-approval-workflow": [
      {
        "execution_id": "exec-abc-123-def-456",
        "thread_id": "thread-789-ghi-012",
        "websocket_execution_id": "ws-exec-345",
        "graph_name": "customer-approval-workflow",
        "paused_at": "2025-10-20T10:30:00Z",
        "checkpoint": {
          "node_id": "checkpoint-approval",
          "node_name": "Manager Approval",
          "checkpoint_id": "chk-1a2b3c4d",
          "prompt": "Please review and approve the customer refund request",
          "last_input": {
            "refund_amount": 150.00,
            "customer_id": "cust-12345"
          },
          "previous_output": {
            "classification": "refund_eligible",
            "agent_recommendation": "approve"
          }
        },
        "progress": {
          "completed_nodes": 5,
          "total_nodes": 12,
          "percentage": 41.67
        }
      }
    ],
    "invoice-processing-workflow": [
      {
        "execution_id": "exec-ghi-789-jkl-012",
        "thread_id": "thread-345-mno-678",
        "websocket_execution_id": "ws-exec-901",
        "graph_name": "invoice-processing-workflow",
        "paused_at": "2025-10-20T08:45:00Z",
        "checkpoint": {
          "node_id": "checkpoint-verification",
          "node_name": "Invoice Verification",
          "checkpoint_id": "chk-9i0j1k2l",
          "prompt": "Verify invoice details before payment processing",
          "last_input": {
            "invoice_number": "INV-2025-0123",
            "amount": 5250.00,
            "vendor": "Acme Supplies Ltd"
          },
          "previous_output": {
            "ocr_confidence": 0.97,
            "validation_passed": true,
            "extracted_fields": 12
          }
        },
        "progress": {
          "completed_nodes": 8,
          "total_nodes": 15,
          "percentage": 53.33
        }
      },
      {
        "execution_id": "exec-mno-345-pqr-678",
        "thread_id": "thread-678-stu-901",
        "websocket_execution_id": "ws-exec-234",
        "graph_name": "invoice-processing-workflow",
        "paused_at": "2025-10-20T07:20:00Z",
        "checkpoint": {
          "node_id": "checkpoint-verification",
          "node_name": "Invoice Verification",
          "checkpoint_id": "chk-3m4n5o6p",
          "prompt": "Verify invoice details before payment processing",
          "last_input": {
            "invoice_number": "INV-2025-0124",
            "amount": 1875.50,
            "vendor": "Tech Solutions Inc"
          },
          "previous_output": {
            "ocr_confidence": 0.94,
            "validation_passed": true,
            "extracted_fields": 11
          }
        },
        "progress": {
          "completed_nodes": 8,
          "total_nodes": 15,
          "percentage": 53.33
        }
      }
    ],
    "contract-review-workflow": [
      {
        "execution_id": "exec-stu-901-vwx-234",
        "thread_id": "thread-901-yza-567",
        "websocket_execution_id": "ws-exec-567",
        "graph_name": "contract-review-workflow",
        "paused_at": "2025-10-20T11:00:00Z",
        "checkpoint": {
          "node_id": "checkpoint-legal-review",
          "node_name": "Legal Team Review",
          "checkpoint_id": "chk-7q8r9s0t",
          "prompt": "Legal review required before contract finalisation",
          "last_input": {
            "contract_id": "CNT-2025-0045",
            "contract_value": 125000.00,
            "counterparty": "Global Enterprises LLC"
          },
          "previous_output": {
            "risk_analysis": "medium",
            "clauses_flagged": 3,
            "ai_recommendation": "review_required"
          }
        },
        "progress": {
          "completed_nodes": 3,
          "total_nodes": 8,
          "percentage": 37.5
        }
      }
    ]
  }
}
```

**Use Cases:**

- Build a centralised task management dashboard
- Monitor all pending work items across the platform
- Generate workload reports by workflow type
- Prioritise human review tasks
- Track SLA metrics for approval workflows

**Behaviour:**

- Queries all paused executions from database (no filtering by graph)
- Groups results by `graph_name` for easy UI rendering
- Returns complete checkpoint information for each execution
- No pagination (returns all paused executions)

**Performance Considerations:**

- Can return large datasets if many workflows are paused
- Consider implementing pagination if `total_paused > 1000`
- Response time: 100-500ms depending on total count
- Multiple database queries for checkpoint details

**Errors:**

- `500 Internal Server Error` - Database query failure
- `503 Service Unavailable` - Execution engine not initialised

**Best Practices:**

```python
# Client-side filtering and sorting
response = get_all_paused_executions()
graphs = response["by_graph"]

# Sort by oldest first
for graph_name, executions in graphs.items():
    executions.sort(key=lambda x: x["paused_at"])

# Filter high-priority only
high_priority = {
    name: execs for name, execs in graphs.items()
    if any(e["checkpoint"].get("priority") == "high" for e in execs)
}
```

### Execution State Management (2 endpoints)

#### `GET /api/executions/{execution_id}/state`

Get the complete state of an execution, including all node executions, checkpoint information, and graph definition.

**Authentication:** None (should be required)

**Path Parameters:**

- `execution_id` - The database execution ID (UUID format)

**Response:**

```json
{
  "execution": {
    "id": "exec-abc-123-def-456",
    "thread_id": "thread-789-ghi-012",
    "websocket_execution_id": "ws-exec-345",
    "graph_name": "customer-approval-workflow",
    "status": "paused",
    "created_at": "2025-10-20T10:25:00Z",
    "input_data": {
      "customer_id": "cust-12345",
      "request_type": "refund",
      "amount": 150.00,
      "reason": "Product defect - screen not working",
      "order_id": "ORD-2025-1234"
    },
    "output_data": null,
    "error_message": null
  },
  "nodes": [
    {
      "id": "node-exec-001",
      "node_id": "start",
      "node_name": "Start",
      "node_type": "START",
      "status": "completed",
      "execution_order": 1,
      "start_time": "2025-10-20T10:25:00.123Z",
      "end_time": "2025-10-20T10:25:00.145Z",
      "duration_seconds": 0.022,
      "input_data": {
        "customer_id": "cust-12345",
        "request_type": "refund",
        "amount": 150.00
      },
      "output_data": {
        "customer_id": "cust-12345",
        "request_type": "refund",
        "amount": 150.00
      },
      "error_message": null,
      "is_sub_agent": false,
      "parent_agent_id": null,
      "total_tokens": null
    },
    {
      "id": "node-exec-002",
      "node_id": "agent-classifier",
      "node_name": "Request Classifier",
      "node_type": "AGENT",
      "status": "completed",
      "execution_order": 2,
      "start_time": "2025-10-20T10:25:00.156Z",
      "end_time": "2025-10-20T10:25:03.421Z",
      "duration_seconds": 3.265,
      "input_data": {
        "customer_id": "cust-12345",
        "request_type": "refund",
        "amount": 150.00,
        "reason": "Product defect - screen not working"
      },
      "output_data": {
        "classification": "refund_eligible",
        "risk_score": 0.15,
        "agent_response": "Based on the product defect description and purchase history, this refund request is eligible for approval.",
        "confidence": 0.92
      },
      "error_message": null,
      "is_sub_agent": false,
      "parent_agent_id": null,
      "total_tokens": 487
    },
    {
      "id": "node-exec-003",
      "node_id": "tool-database-lookup",
      "node_name": "Customer History Lookup",
      "node_type": "TOOL",
      "status": "completed",
      "execution_order": 3,
      "start_time": "2025-10-20T10:25:03.445Z",
      "end_time": "2025-10-20T10:25:03.687Z",
      "duration_seconds": 0.242,
      "input_data": {
        "customer_id": "cust-12345",
        "query_type": "refund_history"
      },
      "output_data": {
        "previous_refunds": 1,
        "customer_lifetime_value": 2450.00,
        "account_age_days": 547,
        "satisfaction_score": 4.2
      },
      "error_message": null,
      "is_sub_agent": false,
      "parent_agent_id": null,
      "total_tokens": null
    },
    {
      "id": "node-exec-004",
      "node_id": "condition-routing",
      "node_name": "Approval Routing",
      "node_type": "CONDITION",
      "status": "completed",
      "execution_order": 4,
      "start_time": "2025-10-20T10:25:03.701Z",
      "end_time": "2025-10-20T10:25:03.724Z",
      "duration_seconds": 0.023,
      "input_data": {
        "classification": "refund_eligible",
        "risk_score": 0.15,
        "amount": 150.00
      },
      "output_data": {
        "route": "manager_approval",
        "reason": "Amount exceeds automatic approval threshold"
      },
      "error_message": null,
      "is_sub_agent": false,
      "parent_agent_id": null,
      "total_tokens": null
    },
    {
      "id": "node-exec-005",
      "node_id": "checkpoint-approval",
      "node_name": "Manager Approval",
      "node_type": "CHECKPOINT",
      "status": "paused",
      "execution_order": 5,
      "start_time": "2025-10-20T10:25:03.735Z",
      "end_time": null,
      "duration_seconds": null,
      "input_data": {
        "refund_amount": 150.00,
        "customer_id": "cust-12345",
        "reason": "Product defect",
        "classification": "refund_eligible"
      },
      "output_data": null,
      "error_message": null,
      "is_sub_agent": false,
      "parent_agent_id": null,
      "total_tokens": null
    }
  ],
  "checkpoint_state": {
    "node_id": "checkpoint-approval",
    "node_name": "Manager Approval",
    "checkpoint_id": "chk-1a2b3c4d",
    "prompt": "Please review and approve the customer refund request",
    "last_input": {
      "refund_amount": 150.00,
      "customer_id": "cust-12345",
      "reason": "Product defect",
      "classification": "refund_eligible"
    },
    "previous_output": {
      "route": "manager_approval",
      "reason": "Amount exceeds automatic approval threshold"
    }
  },
  "can_resume": true,
  "graph_definition": {
    "name": "customer-approval-workflow",
    "nodes": [
      {
        "id": "start",
        "type": "START",
        "data": {"name": "Start"}
      },
      {
        "id": "agent-classifier",
        "type": "AGENT",
        "data": {
          "name": "Request Classifier",
          "llm_config": {"type": "azure_openai", "model_name": "gpt-4"}
        }
      },
      {
        "id": "checkpoint-approval",
        "type": "CHECKPOINT",
        "data": {
          "name": "Manager Approval",
          "prompt": "Please review and approve the customer refund request"
        }
      }
    ],
    "edges": []
  }
}
```

**Use Cases:**

- Debugging workflow execution issues
- Auditing execution history for compliance
- Building detailed execution inspection UIs
- Analysing performance bottlenecks
- Reviewing AI agent decision-making process
- Understanding why a workflow paused

**Behaviour:**

- Retrieves complete execution record from database
- Fetches all node executions ordered by `execution_order`
- Calculates duration for completed nodes
- Includes checkpoint state if execution is paused
- Queries LangGraph checkpoint store to verify resume capability
- Returns full graph definition for context

**Response Fields Explained:**

**execution:**

- Core execution metadata
- Status indicates current state (paused, running, completed, failed, cancelled)
- Input/output data shows workflow-level state

**nodes:**

- Ordered list of all node executions
- Includes timing information for performance analysis
- Shows input/output for each node (data flow tracing)
- Token usage for AGENT nodes (cost tracking)
- Execution order for understanding flow

**checkpoint_state:**

- Only present if execution is paused
- Contains prompt to display to user
- Includes context needed for human decision-making
- Previous output provides reasoning trail

**can_resume:**

- `true` if LangGraph checkpoint exists in checkpoint store
- `false` if checkpoint was purged or execution cannot resume
- Critical for determining if resume action is available

**graph_definition:**

- Complete workflow structure used for this execution
- Useful for understanding execution context
- May differ from current graph definition if workflow was updated

**Validation:**

- `execution_id` must be valid UUID format
- Execution must exist in database

**Errors:**

- `404 Not Found` - Execution doesn't exist
- `500 Internal Server Error` - Database query failure
- `503 Service Unavailable` - Execution engine not available

**Performance:**

- Typical response time: 100-300ms
- Includes multiple database queries (execution + nodes + checkpoint)
- Response size: 5-50KB depending on node count and data size
- Consider pagination for executions with > 100 nodes

#### `GET /api/executions/{execution_id}/checkpoint-data`

Get checkpoint-specific data needed for resuming a paused execution.

**Authentication:** None (should be required)

**Path Parameters:**

- `execution_id` - The database execution ID

**Response:**

```json
{
  "execution_id": "exec-abc-123-def-456",
  "thread_id": "thread-789-ghi-012",
  "websocket_execution_id": "ws-exec-345",
  "checkpoint": {
    "node_id": "checkpoint-approval",
    "node_name": "Manager Approval",
    "checkpoint_id": "chk-1a2b3c4d",
    "prompt": "Please review and approve the customer refund request",
    "last_input": {
      "refund_amount": 150.00,
      "customer_id": "cust-12345",
      "reason": "Product defect",
      "classification": "refund_eligible",
      "customer_history": {
        "previous_refunds": 1,
        "lifetime_value": 2450.00,
        "satisfaction_score": 4.2
      }
    },
    "previous_output": {
      "route": "manager_approval",
      "reason": "Amount exceeds automatic approval threshold",
      "agent_classification": "refund_eligible",
      "risk_score": 0.15
    }
  },
  "graph_name": "customer-approval-workflow"
}
```

**Use Cases:**

- Preparing UI for human approval workflow
- Displaying context to user for decision-making
- Implementing custom resume logic
- Building approval dashboards with rich context
- Creating notification emails with execution details

**Behaviour:**

- Validates execution exists and is paused
- Retrieves checkpoint node information from database
- Fetches previous node's output for context
- Queries LangGraph checkpoint store for resume data
- Returns all information needed to display prompt and resume execution

**Checkpoint Data Structure:**

**checkpoint.prompt:**

- Human-readable message for the user
- Defined in workflow's checkpoint node configuration
- Should clearly explain what decision/action is needed

**checkpoint.last_input:**

- Input data passed to the checkpoint node
- Contains all context from previous workflow steps
- Available for display in approval UI
- Can include nested objects (customer history, analysis results, etc.)

**checkpoint.previous_output:**

- Output from the node that executed before checkpoint
- Often contains AI agent's recommendation or analysis
- Provides reasoning trail for human reviewer
- Useful for audit purposes

**thread_id and checkpoint_id:**

- Required for resuming execution via WebSocket or HTTP execution endpoints
- Thread ID identifies the LangGraph execution thread
- Checkpoint ID identifies the specific pause point

**Validation:**

- Execution must exist
- Execution status must be "paused"
- Checkpoint node must exist for the execution

**Errors:**

- `404 Not Found` - Execution doesn't exist
- `400 Bad Request` - Execution is not paused (wrong status)
- `400 Bad Request` - No checkpoint found for execution
- `500 Internal Server Error` - Database or checkpoint store query failure
- `503 Service Unavailable` - Execution engine not available

**Integration Example:**

```python
# Fetch checkpoint data for approval UI
response = requests.get(f"/api/executions/{execution_id}/checkpoint-data")
checkpoint_data = response.json()

# Display to user
print(f"Workflow: {checkpoint_data['graph_name']}")
print(f"Prompt: {checkpoint_data['checkpoint']['prompt']}")
print(f"Context: {checkpoint_data['checkpoint']['last_input']}")

# User makes decision
user_decision = input("Approve? (yes/no): ")

# Resume execution via WebSocket API (separate endpoint)
if user_decision == "yes":
    resume_execution(
        thread_id=checkpoint_data['thread_id'],
        checkpoint_id=checkpoint_data['checkpoint']['checkpoint_id'],
        user_input={"approved": True, "reviewer": "manager@example.com"}
    )
```

**Performance:**

- Typical response time: 50-150ms
- Lightweight compared to full state endpoint
- Only fetches checkpoint-specific data
- Response size: 1-10KB

**Difference from `/state` Endpoint:**

- `/checkpoint-data`: Focused on resume data, minimal response
- `/state`: Complete execution history with all nodes
- Use `/checkpoint-data` for approval UIs (faster)
- Use `/state` for debugging and auditing (comprehensive)

### Execution Control (1 endpoint)

#### `POST /api/executions/{execution_id}/cancel`

Cancel a paused execution, setting its status to cancelled and preventing future resumption.

**Authentication:** None (should be required)

**Path Parameters:**

- `execution_id` - The database execution ID to cancel

**Request Body:** None

**Response:**

```json
{
  "status": "cancelled",
  "execution_id": "exec-abc-123-def-456",
  "message": "Execution cancelled successfully"
}
```

**Use Cases:**

- User manually cancels a pending approval
- Timeout-based cancellation of stale executions
- Workflow cleanup and housekeeping
- Rejecting requests that no longer need processing
- Bulk cancellation of outdated work items

**Behaviour:**

1. Validates execution exists in database
2. Checks execution status is "paused" (cannot cancel completed/failed executions)
3. Updates execution status to "cancelled"
4. Sets execution `end_time` to current timestamp
5. Finds all checkpoint nodes with status "paused" for this execution
6. Updates all paused checkpoint nodes to "cancelled" status
7. Sets checkpoint nodes' `end_time` to current timestamp
8. Commits transaction to database
9. Returns success confirmation

**Side Effects:**

- Execution status changes from "paused" to "cancelled"
- All paused checkpoint nodes marked as cancelled
- Execution becomes non-resumable
- End time is recorded for reporting
- Changes are permanent (cannot be undone)

**Important Notes:**

- Does **not** delete LangGraph checkpoint from checkpoint store
- Checkpoint data remains accessible for auditing
- Does not affect the graph definition
- Does not delete node execution history
- Execution remains in database for historical tracking

**Validation:**

- Execution must exist
- Execution status must be "paused"
- Cannot cancel executions with status: running, completed, failed, cancelled

**Errors:**

- `404 Not Found` - Execution doesn't exist

  ```json
  {
    "detail": "Execution not found: exec-invalid-id"
  }
  ```

- `400 Bad Request` - Execution is not paused

  ```json
  {
    "detail": "Execution is not paused (status: completed)"
  }
  ```

- `500 Internal Server Error` - Database update failed

  ```json
  {
    "detail": "Database error during cancellation"
  }
  ```

- `503 Service Unavailable` - Execution engine not available

  ```json
  {
    "detail": "Execution engine not available"
  }
  ```

**Rollback Behaviour:**
If the database commit fails, the transaction is rolled back and no changes are persisted.

**Example Usage:**

```python
import requests

# Cancel a paused execution
execution_id = "exec-abc-123-def-456"
response = requests.post(f"/api/executions/{execution_id}/cancel")

if response.status_code == 200:
    data = response.json()
    print(f"Cancelled: {data['message']}")
    print(f"Status: {data['status']}")
elif response.status_code == 404:
    print("Execution not found")
elif response.status_code == 400:
    print(f"Cannot cancel: {response.json()['detail']}")
else:
    print("Server error")
```

**Bulk Cancellation Pattern:**

```python
# Cancel all paused executions for a specific graph
paused = requests.get("/api/executions/paused/old-workflow")
executions = paused.json()["executions"]

cancelled_count = 0
for execution in executions:
    try:
        response = requests.post(f"/api/executions/{execution['execution_id']}/cancel")
        if response.status_code == 200:
            cancelled_count += 1
    except Exception as e:
        print(f"Failed to cancel {execution['execution_id']}: {e}")

print(f"Cancelled {cancelled_count} executions")
```

**Timeout-Based Cancellation:**

```python
from datetime import datetime, timedelta

# Cancel executions paused for more than 7 days
all_paused = requests.get("/api/executions/paused").json()
stale_threshold = datetime.utcnow() - timedelta(days=7)

for graph_name, executions in all_paused["by_graph"].items():
    for execution in executions:
        paused_at = datetime.fromisoformat(execution["paused_at"].replace('Z', '+00:00'))
        if paused_at < stale_threshold:
            print(f"Cancelling stale execution: {execution['execution_id']}")
            requests.post(f"/api/executions/{execution['execution_id']}/cancel")
```

**Performance:**

- Typical response time: 20-50ms
- Single database transaction
- Updates 1 execution record + N checkpoint nodes (usually 1)
- Fast operation suitable for bulk cancellation

## Error Handling

### Error Response Format

All errors follow FastAPI's standard HTTPException format:

```json
{
  "detail": "Human-readable error message explaining what went wrong"
}
```

### Common Error Codes

#### Service Unavailable (503)

**When:** Execution engine not initialised or unavailable

**Error:**

```json
{
  "detail": "Execution engine not available"
}
```

**Cause:**

- Dependency injection failed to get execution engine
- LangGraph execution engine not started
- Connection to checkpoint store failed

**Resolution:**

- Check execution engine initialisation in application startup
- Verify checkpoint store (PostgreSQL) is accessible
- Review dependency injection configuration

#### Not Found (404)

**When:** Execution ID doesn't exist in database

**Error:**

```json
{
  "detail": "Execution not found: exec-invalid-id-123"
}
```

**Cause:**

- Invalid execution ID provided
- Execution was deleted from database
- Execution ID from different environment

**Resolution:**

- Verify execution ID is correct
- Check execution wasn't manually deleted
- Ensure using correct database environment

#### Bad Request (400)

**When:** Validation error or invalid operation

**Examples:**

**Execution not paused:**

```json
{
  "detail": "Execution is not paused (status: completed)"
}
```

**No checkpoint found:**

```json
{
  "detail": "No paused checkpoint found for execution: exec-abc-123"
}
```

**Cause:**

- Attempting to cancel non-paused execution
- Requesting checkpoint data for execution without checkpoint
- Execution already completed/failed/cancelled

**Resolution:**

- Check execution status before operation
- Verify execution is in expected state
- Use `/state` endpoint to inspect execution first

#### Internal Server Error (500)

**When:** Database query fails or unexpected error

**Error:**

```json
{
  "detail": "Database error message or generic failure"
}
```

**Cause:**

- Database connection lost
- Query timeout
- Data corruption
- Unexpected exception in service layer

**Resolution:**

- Check database connectivity
- Review application logs for stack traces
- Verify database schema integrity
- Check for race conditions in concurrent requests

### Error Handling Example

```python
import requests
from requests.exceptions import HTTPError

def get_execution_state_safe(execution_id: str):
    """
    Safely fetch execution state with comprehensive error handling.
    """
    try:
        response = requests.get(f"/api/executions/{execution_id}/state")
        response.raise_for_status()
        return response.json()

    except HTTPError as e:
        status_code = e.response.status_code
        error_detail = e.response.json().get("detail", "Unknown error")

        if status_code == 404:
            print(f"Execution not found: {execution_id}")
            return None
        elif status_code == 503:
            print("Service unavailable - execution engine not ready")
            print("Retrying in 5 seconds...")
            time.sleep(5)
            return get_execution_state_safe(execution_id)  # Retry
        elif status_code == 500:
            print(f"Server error: {error_detail}")
            # Log to monitoring system
            log_error(f"Failed to fetch execution state: {error_detail}")
            return None
        else:
            print(f"Unexpected error ({status_code}): {error_detail}")
            raise

    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None


def cancel_execution_safe(execution_id: str) -> bool:
    """
    Safely cancel an execution with error handling.

    Returns:
        True if cancelled successfully, False otherwise
    """
    try:
        response = requests.post(f"/api/executions/{execution_id}/cancel")
        response.raise_for_status()
        print(f"Cancelled execution: {execution_id}")
        return True

    except HTTPError as e:
        status_code = e.response.status_code
        error_detail = e.response.json().get("detail", "Unknown error")

        if status_code == 404:
            print(f"Cannot cancel - execution not found: {execution_id}")
        elif status_code == 400:
            if "not paused" in error_detail.lower():
                print(f"Cannot cancel - execution not paused (already completed/failed)")
            else:
                print(f"Cannot cancel - validation error: {error_detail}")
        elif status_code == 500:
            print(f"Cancellation failed - server error: {error_detail}")
        else:
            print(f"Unexpected error ({status_code}): {error_detail}")

        return False

    except requests.RequestException as e:
        print(f"Network error during cancellation: {e}")
        return False
```

### Logging and Debugging

All endpoints log to the application logger with prefix `[PAUSED-EXEC-API]`:

**Example log messages:**

```
[PAUSED-EXEC-API] GET /paused/customer-approval-workflow (skip=0, limit=20)
[PAUSED-EXEC-API] Returning 15 paused executions for customer-approval-workflow
[PAUSED-EXEC-API] GET /exec-abc-123/state
[PAUSED-EXEC-API] POST /exec-abc-123/cancel
[PAUSED-EXEC-API] Failed to get paused executions for graph 'invalid-name': Database error
[PAUSED-EXEC-API] Execution engine not available: Connection refused
```

**Service layer logs** (prefix `[PAUSED-EXEC-SERVICE]`):

```
[PAUSED-EXEC-SERVICE] Initialized paused execution service
[PAUSED-EXEC-SERVICE] Fetching paused executions for graph: customer-approval-workflow (skip=0, limit=20)
[PAUSED-EXEC-SERVICE] Returning 15 paused executions for customer-approval-workflow
[PAUSED-EXEC-SERVICE] Fetching execution state for: exec-abc-123
[PAUSED-EXEC-SERVICE] Returning state for execution exec-abc-123 with 5 nodes (can_resume=True)
[PAUSED-EXEC-SERVICE] Cancelling paused execution: exec-abc-123
[PAUSED-EXEC-SERVICE] Successfully cancelled execution: exec-abc-123 (updated 1 paused nodes)
```

**Enable debug logging:**

```python
import logging
logging.getLogger("backend.api.execution").setLevel(logging.DEBUG)
logging.getLogger("backend.services.execution.paused").setLevel(logging.DEBUG)
```

## Integration with Services Layer

### Dependency Flow

```
API Route (paused_routes.py)
    ↓
FastAPI Dependency Injection
    ↓ get_paused_execution_service()
    ↓
PausedExecutionService
    ↓
CheckpointHandler + Database Queries
    ↓
LangGraph Checkpoint Store + PostgreSQL Database
```

### Dependency Injection Pattern

**Service Factory:**

```python
# In paused_routes.py

def get_paused_execution_service() -> PausedExecutionService:
    """
    Get the paused execution service instance.

    Returns:
        PausedExecutionService: Initialized service with execution engine

    Raises:
        HTTPException: If execution engine is not available
    """
    try:
        execution_engine = get_execution_engine()
        return PausedExecutionService(execution_engine)
    except Exception as e:
        logger.error(f"[PAUSED-EXEC-API] Execution engine not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="Execution engine not available"
        )
```

**Usage in Routes:**

```python
@router.get("/paused/{graph_name}", response_model=PausedExecutionsResponse)
async def get_paused_executions(
    graph_name: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
) -> Dict[str, Any]:
    # Service is automatically injected
    result = service.get_paused_executions_by_graph(db, graph_name, skip, limit)
    return result
```

### Example Integration

**Complete Request Flow:**

```python
# 1. HTTP Request arrives
# GET /api/executions/paused/customer-approval-workflow?skip=0&limit=20

# 2. FastAPI route handler invoked
@router.get("/paused/{graph_name}")
async def get_paused_executions(
    graph_name: str,  # = "customer-approval-workflow"
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),  # Database session injected
    service: PausedExecutionService = Depends(get_paused_execution_service),  # Service injected
):
    # 3. Enforce maximum limit
    if limit > 100:
        limit = 100

    # 4. Call service layer
    result = service.get_paused_executions_by_graph(db, graph_name, skip, limit)

    # 5. Return result (FastAPI handles JSON serialization)
    return result


# In PausedExecutionService:
def get_paused_executions_by_graph(
    self, db: Session, graph_name: str, skip: int = 0, limit: int = 20
) -> Dict[str, Any]:
    # 6. Query database for paused executions
    paused_executions, total_count = get_paused_executions_by_graph(
        db, graph_name, skip, limit
    )

    # 7. Build summaries with checkpoint info
    summaries = []
    for execution in paused_executions:
        checkpoint_node = get_checkpoint_node(db, execution.id)
        summary = PausedExecutionSummary(execution, checkpoint_node)
        summaries.append(summary.to_dict())

    # 8. Calculate pagination
    has_more = (skip + limit) < total_count
    next_skip = skip + limit if has_more else None

    # 9. Return structured response
    return {
        "executions": summaries,
        "pagination": {
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
            "next_skip": next_skip,
        },
    }
```

### Services Used

#### PausedExecutionService

**Location:** `backend/services/execution/paused/service.py`

**Responsibilities:**

- Business logic for paused execution management
- Orchestrating database queries
- Building response models
- Coordinating with CheckpointHandler

**Key Methods:**

- `get_paused_executions_by_graph()` - Query paused executions with pagination
- `get_all_paused_executions()` - Query all paused executions
- `get_execution_state()` - Build complete execution state
- `cancel_paused_execution()` - Cancel execution and update nodes
- `get_checkpoint_data()` - Extract checkpoint resumption data

**Initialization:**

```python
def __init__(self, execution_engine: Any):
    """
    Initialize with execution engine for checkpoint access.

    Args:
        execution_engine: LangGraph execution engine instance
    """
    self.checkpoint_handler = CheckpointHandler(execution_engine)
```

#### CheckpointHandler

**Location:** `backend/services/execution/paused/checkpoint_handler.py`

**Responsibilities:**

- Interact with LangGraph checkpoint store
- Extract checkpoint metadata
- Build checkpoint information for responses
- Verify resume capability

**Key Methods:**

- `get_checkpoint_info()` - Extract checkpoint data from node
- `get_checkpoint_info_for_resume()` - Build resume-specific data
- `can_resume_from_checkpoint()` - Check if checkpoint exists in store
- `build_node_execution_details()` - Format node execution history

#### Database Query Functions

**Location:** `backend/services/execution/paused/queries.py`

**Functions:**

- `get_paused_executions_by_graph()` - Query by graph name with pagination
- `get_all_paused_executions()` - Query all paused executions
- `get_execution_by_id()` - Fetch execution by ID
- `get_node_executions_by_execution_id()` - Fetch all node executions
- `get_checkpoint_node()` - Find paused checkpoint node
- `get_previous_node()` - Get node before checkpoint
- `get_paused_nodes_by_execution_id()` - Find all paused nodes

**Query Example:**

```python
def get_paused_executions_by_graph(
    db: Session, graph_name: str, skip: int = 0, limit: int = 20
) -> Tuple[List[GraphExecution], int]:
    """
    Query paused executions for a graph with pagination.

    Returns:
        Tuple of (executions list, total count)
    """
    # Query with filters
    query = db.query(GraphExecution).filter(
        GraphExecution.graph_name == graph_name,
        GraphExecution.status == "paused"
    )

    # Get total count
    total_count = query.count()

    # Apply pagination
    executions = query.order_by(
        GraphExecution.created_at.desc()
    ).offset(skip).limit(limit).all()

    return executions, total_count
```

### Service Layer Testing

**Example Unit Test:**

```python
import pytest
from unittest.mock import Mock, MagicMock
from backend.services.execution.paused.service import PausedExecutionService

def test_get_paused_executions_by_graph():
    # Mock execution engine
    mock_engine = Mock()
    service = PausedExecutionService(mock_engine)

    # Mock database session
    mock_db = MagicMock()

    # Mock query results
    mock_execution = Mock()
    mock_execution.id = "exec-123"
    mock_execution.graph_name = "test-workflow"
    mock_execution.status = "paused"

    # Call service
    result = service.get_paused_executions_by_graph(
        mock_db, "test-workflow", skip=0, limit=20
    )

    # Assertions
    assert "executions" in result
    assert "pagination" in result
    assert result["pagination"]["skip"] == 0
    assert result["pagination"]["limit"] == 20
```

## Usage Examples

### Complete Paused Execution Management Workflow

```python
import requests
import time
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"

class PausedExecutionManager:
    """
    Manager for interacting with paused execution API endpoints.
    """

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    def list_paused_by_graph(
        self, graph_name: str, skip: int = 0, limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get paused executions for a specific workflow.
        """
        response = requests.get(
            f"{self.base_url}/api/executions/paused/{graph_name}",
            params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    def list_all_paused(self) -> Dict[str, Any]:
        """
        Get all paused executions across all workflows.
        """
        response = requests.get(f"{self.base_url}/api/executions/paused")
        response.raise_for_status()
        return response.json()

    def get_execution_state(self, execution_id: str) -> Dict[str, Any]:
        """
        Get complete execution state with node history.
        """
        response = requests.get(
            f"{self.base_url}/api/executions/{execution_id}/state"
        )
        response.raise_for_status()
        return response.json()

    def get_checkpoint_data(self, execution_id: str) -> Dict[str, Any]:
        """
        Get checkpoint data for resuming execution.
        """
        response = requests.get(
            f"{self.base_url}/api/executions/{execution_id}/checkpoint-data"
        )
        response.raise_for_status()
        return response.json()

    def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Cancel a paused execution.
        """
        response = requests.post(
            f"{self.base_url}/api/executions/{execution_id}/cancel"
        )
        response.raise_for_status()
        return response.json()


# Example 1: Build approval dashboard
def build_approval_dashboard():
    """
    Build a dashboard showing all pending approvals.
    """
    manager = PausedExecutionManager()

    # Get all paused executions
    all_paused = manager.list_all_paused()

    print(f"Total Pending Approvals: {all_paused['total_paused']}")
    print("\nBy Workflow:")
    print("-" * 80)

    for graph_name, executions in all_paused["by_graph"].items():
        print(f"\n{graph_name}: {len(executions)} pending")

        for execution in executions[:3]:  # Show first 3
            checkpoint = execution["checkpoint"]
            paused_at = execution["paused_at"]

            print(f"  • {checkpoint['node_name']}")
            print(f"    ID: {execution['execution_id']}")
            print(f"    Paused: {paused_at}")
            print(f"    Prompt: {checkpoint['prompt']}")
            print(f"    Progress: {execution['progress']['percentage']:.1f}%")


# Example 2: Process approval queue
def process_approval_queue(graph_name: str, auto_approve_threshold: float = 100.0):
    """
    Process approval queue for a specific workflow.

    Args:
        graph_name: Workflow name to process
        auto_approve_threshold: Amount threshold for auto-approval
    """
    manager = PausedExecutionManager()

    # Get paused executions for this workflow
    result = manager.list_paused_by_graph(graph_name, skip=0, limit=50)
    executions = result["executions"]

    print(f"Processing {len(executions)} pending approvals for {graph_name}")

    for execution in executions:
        execution_id = execution["execution_id"]
        checkpoint = execution["checkpoint"]

        # Get checkpoint data for decision-making
        checkpoint_data = manager.get_checkpoint_data(execution_id)
        last_input = checkpoint_data["checkpoint"]["last_input"]

        # Example: Auto-approve small amounts
        amount = last_input.get("refund_amount", 0)
        if amount <= auto_approve_threshold:
            print(f"Auto-approving ${amount} refund (exec: {execution_id})")
            # Would call resume endpoint here (WebSocket/HTTP execution API)
            # resume_execution(checkpoint_data["thread_id"], approved=True)
        else:
            print(f"Manual review required for ${amount} (exec: {execution_id})")
            # Display to user for manual approval


# Example 3: Monitor execution progress
def monitor_execution_progress(execution_id: str, poll_interval: int = 5):
    """
    Monitor execution progress until completion.

    Args:
        execution_id: Execution to monitor
        poll_interval: Seconds between status checks
    """
    manager = PausedExecutionManager()

    print(f"Monitoring execution: {execution_id}")

    while True:
        try:
            state = manager.get_execution_state(execution_id)
            execution = state["execution"]
            status = execution["status"]

            # Calculate progress
            completed_nodes = len([n for n in state["nodes"] if n["status"] == "completed"])
            total_nodes = len(state["nodes"])
            progress_pct = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0

            print(f"Status: {status} | Progress: {progress_pct:.1f}% ({completed_nodes}/{total_nodes} nodes)")

            if status == "paused":
                checkpoint = state.get("checkpoint_state")
                if checkpoint:
                    print(f"Paused at: {checkpoint['node_name']}")
                    print(f"Prompt: {checkpoint['prompt']}")
                break
            elif status in ["completed", "failed", "cancelled"]:
                print(f"Execution finished with status: {status}")
                break

            time.sleep(poll_interval)

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print("Execution not found")
                break
            raise


# Example 4: Cancel stale executions
def cancel_stale_executions(days_threshold: int = 7):
    """
    Cancel executions paused for more than N days.

    Args:
        days_threshold: Number of days before considering execution stale
    """
    manager = PausedExecutionManager()

    all_paused = manager.list_all_paused()
    now = datetime.utcnow()
    cancelled_count = 0

    for graph_name, executions in all_paused["by_graph"].items():
        for execution in executions:
            paused_at = datetime.fromisoformat(
                execution["paused_at"].replace('Z', '+00:00')
            )
            age_days = (now - paused_at.replace(tzinfo=None)).days

            if age_days >= days_threshold:
                execution_id = execution["execution_id"]
                print(f"Cancelling stale execution: {execution_id} (age: {age_days} days)")

                try:
                    manager.cancel_execution(execution_id)
                    cancelled_count += 1
                except Exception as e:
                    print(f"Failed to cancel {execution_id}: {e}")

    print(f"\nCancelled {cancelled_count} stale executions")


# Example 5: Export execution audit trail
def export_execution_audit_trail(execution_id: str, output_file: str):
    """
    Export complete execution history for auditing.

    Args:
        execution_id: Execution to export
        output_file: Path to output JSON file
    """
    import json

    manager = PausedExecutionManager()
    state = manager.get_execution_state(execution_id)

    # Build audit trail
    audit_trail = {
        "execution_id": execution_id,
        "graph_name": state["execution"]["graph_name"],
        "status": state["execution"]["status"],
        "created_at": state["execution"]["created_at"],
        "timeline": []
    }

    # Add node execution timeline
    for node in state["nodes"]:
        audit_trail["timeline"].append({
            "node_name": node["node_name"],
            "node_type": node["node_type"],
            "status": node["status"],
            "start_time": node["start_time"],
            "end_time": node["end_time"],
            "duration_seconds": node["duration_seconds"],
            "input": node["input_data"],
            "output": node["output_data"],
            "error": node["error_message"],
            "tokens_used": node["total_tokens"]
        })

    # Add checkpoint info if paused
    if state["checkpoint_state"]:
        audit_trail["checkpoint"] = state["checkpoint_state"]

    # Write to file
    with open(output_file, 'w') as f:
        json.dump(audit_trail, f, indent=2)

    print(f"Audit trail exported to: {output_file}")
    print(f"Nodes: {len(audit_trail['timeline'])}")
    print(f"Status: {audit_trail['status']}")


# Example 6: Paginated listing
def list_all_paused_paginated(graph_name: str, page_size: int = 20):
    """
    List all paused executions with pagination.

    Args:
        graph_name: Workflow name
        page_size: Items per page
    """
    manager = PausedExecutionManager()
    skip = 0
    all_executions = []

    while True:
        result = manager.list_paused_by_graph(graph_name, skip=skip, limit=page_size)
        executions = result["executions"]
        pagination = result["pagination"]

        all_executions.extend(executions)
        print(f"Fetched {len(executions)} executions (total so far: {len(all_executions)})")

        if not pagination["has_more"]:
            break

        skip = pagination["next_skip"]

    print(f"\nTotal paused executions for {graph_name}: {len(all_executions)}")
    return all_executions


# Run examples
if __name__ == "__main__":
    # Example 1: Dashboard
    print("=== Approval Dashboard ===")
    build_approval_dashboard()

    # Example 2: Process queue
    print("\n=== Processing Approval Queue ===")
    process_approval_queue("customer-approval-workflow", auto_approve_threshold=100.0)

    # Example 4: Cancel stale
    print("\n=== Cancelling Stale Executions ===")
    cancel_stale_executions(days_threshold=7)

    # Example 6: Pagination
    print("\n=== Paginated Listing ===")
    list_all_paused_paginated("customer-approval-workflow", page_size=10)
```

### Integration with WebSocket for Resume

```python
import asyncio
import websockets
import json

async def resume_paused_execution(execution_id: str, user_input: Dict[str, Any]):
    """
    Resume a paused execution via WebSocket API.

    This demonstrates integration between Execution API (for inspection)
    and WebSocket API (for resumption).

    Args:
        execution_id: The paused execution to resume
        user_input: User's decision/input for the checkpoint
    """
    # 1. Get checkpoint data via REST API
    manager = PausedExecutionManager()
    checkpoint_data = manager.get_checkpoint_data(execution_id)

    thread_id = checkpoint_data["thread_id"]
    graph_name = checkpoint_data["graph_name"]

    print(f"Resuming execution: {execution_id}")
    print(f"Thread ID: {thread_id}")
    print(f"Graph: {graph_name}")

    # 2. Connect to WebSocket for execution
    uri = f"ws://localhost:8000/ws/graph/{graph_name}/execute"

    async with websockets.connect(uri) as websocket:
        # 3. Send resume message
        resume_message = {
            "type": "resume",
            "thread_id": thread_id,
            "user_input": user_input
        }

        await websocket.send(json.dumps(resume_message))
        print("Resume message sent")

        # 4. Listen for execution updates
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "node_update":
                print(f"Node: {data['node_name']} - Status: {data['status']}")
            elif msg_type == "execution_complete":
                print(f"Execution completed: {data}")
                break
            elif msg_type == "execution_paused":
                print(f"Execution paused again at: {data['checkpoint_node']}")
                break
            elif msg_type == "error":
                print(f"Error: {data['message']}")
                break


# Example usage
if __name__ == "__main__":
    # Resume with approval
    asyncio.run(resume_paused_execution(
        execution_id="exec-abc-123-def-456",
        user_input={
            "approved": True,
            "approver": "manager@company.com",
            "notes": "Approved - customer has good history",
            "timestamp": datetime.utcnow().isoformat()
        }
    ))
```

## Performance Considerations

### Endpoint Performance

**Fast Endpoints (< 100ms):**

- `POST /api/executions/{execution_id}/cancel` - Single database transaction
- `GET /api/executions/{execution_id}/checkpoint-data` - Minimal data fetch

**Medium Endpoints (100ms - 500ms):**

- `GET /api/executions/paused/{graph_name}` - Paginated query with joins
- `GET /api/executions/{execution_id}/state` - Multiple database queries

**Potentially Slow Endpoints (> 500ms):**

- `GET /api/executions/paused` - No pagination, can return large datasets
- `GET /api/executions/{execution_id}/state` - For executions with > 100 nodes

### Optimisation Tips

**1. Use Pagination:**

```python
# Instead of fetching all paused executions
result = get("/api/executions/paused")  # Can be slow with many executions

# Use paginated endpoint
result = get("/api/executions/paused/customer-workflow?limit=20")  # Faster
```

**2. Limit Response Size:**

```python
# For quick checks, use checkpoint-data instead of full state
# Checkpoint data: ~2KB, State: ~50KB
checkpoint = get(f"/api/executions/{execution_id}/checkpoint-data")  # Fast

# Only fetch full state when needed for debugging/auditing
state = get(f"/api/executions/{execution_id}/state")  # Slower
```

**3. Cache Results Client-Side:**

```python
# Cache paused execution lists
execution_cache = {}
cache_ttl = 30  # seconds

def get_paused_executions_cached(graph_name: str) -> Dict[str, Any]:
    now = time.time()
    cache_key = f"paused:{graph_name}"

    if cache_key in execution_cache:
        cached_data, cached_time = execution_cache[cache_key]
        if now - cached_time < cache_ttl:
            return cached_data

    # Fetch fresh data
    data = requests.get(f"/api/executions/paused/{graph_name}").json()
    execution_cache[cache_key] = (data, now)
    return data
```

**4. Batch Cancellations:**

```python
# Efficient bulk cancellation
import concurrent.futures

def cancel_multiple(execution_ids: List[str]):
    """Cancel multiple executions in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(requests.post, f"/api/executions/{eid}/cancel")
            for eid in execution_ids
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    return results
```

**5. Index Database Columns:**

```sql
-- Ensure database indexes exist for fast queries
CREATE INDEX idx_executions_status_graph
ON graph_executions(status, graph_name);

CREATE INDEX idx_executions_created_at
ON graph_executions(created_at DESC);

CREATE INDEX idx_node_executions_exec_id_order
ON node_executions(execution_id, execution_order);
```

**6. Limit Data in Responses:**
When building UIs, only request necessary fields:

- For listing: Use summary data (from `/paused` endpoints)
- For detail view: Use `/checkpoint-data` for approval context
- For debugging: Use `/state` for complete history

**7. Poll Efficiently:**

```python
# Adaptive polling - reduce frequency over time
def poll_execution_state(execution_id: str):
    poll_intervals = [2, 5, 10, 30, 60]  # seconds
    attempt = 0

    while True:
        state = get(f"/api/executions/{execution_id}/state")
        if state["execution"]["status"] != "running":
            return state

        interval = poll_intervals[min(attempt, len(poll_intervals) - 1)]
        time.sleep(interval)
        attempt += 1
```

### Database Query Optimisation

**Efficient Queries:**

- Use pagination (`LIMIT` and `OFFSET`)
- Filter early (`WHERE status = 'paused'`)
- Order efficiently (`ORDER BY created_at DESC`)
- Join only when needed (checkpoint node details)

**Query Execution Plan:**

```sql
-- Fast: Uses index on status and graph_name
SELECT * FROM graph_executions
WHERE status = 'paused' AND graph_name = 'customer-workflow'
ORDER BY created_at DESC
LIMIT 20 OFFSET 0;

-- Slower: No index, large result set
SELECT * FROM graph_executions
WHERE status = 'paused';  -- All graphs, no limit
```

### Performance Metrics

**Typical Response Times:**

- `/paused/{graph_name}` (20 items): 80-150ms
- `/paused` (50 total executions): 200-400ms
- `/paused` (500 total executions): 800-1500ms
- `/{execution_id}/state` (10 nodes): 100-200ms
- `/{execution_id}/state` (100 nodes): 400-800ms
- `/{execution_id}/checkpoint-data`: 50-100ms
- `/{execution_id}/cancel`: 20-50ms

**Response Size:**

- Paused execution summary: ~1-2KB per execution
- Full execution state: 5-50KB depending on node count
- Checkpoint data: 1-5KB

## Related Documentation

- [Graph API](../graph/graph.md) - Workflow creation and execution endpoints
- [WebSocket API](../websocket/websocket.md) - Real-time execution monitoring and resumption
- [HTTP Execution API](../http_execution/http_execution.md) - Streaming execution endpoint
- [Architecture Overview](../../../docs/architecture/00-overview.md) - System architecture
- [Checkpoint System](../architecture/checkpoints.md) - How checkpoints work
- [Data Flow Patterns](../../../docs/architecture/02-data-flow.md) - Understanding workflow state

## Summary

The Execution API module provides focused functionality for managing paused workflow executions in AgenticStudio. It
complements the Graph API's execution endpoints by offering specialised tools for human-in-the-loop workflows and
approval processes.

### Key Features

- **Comprehensive Querying** - List paused executions by workflow or across all workflows with pagination support
- **Detailed Inspection** - Access complete execution state including node-level history, timing data, and token usage
- **Checkpoint Management** - Retrieve checkpoint data needed for resuming paused workflows
- **Execution Control** - Cancel paused executions with proper cleanup of checkpoint nodes
- **Progress Tracking** - Monitor workflow completion percentage and execution timeline
- **Audit Trail** - Complete execution history for compliance and debugging

### Primary Use Cases

**Human-in-the-Loop Workflows:**

- Approval gates requiring manager review
- Quality control checkpoints
- Manual verification steps
- Compliance reviews

**Workflow Management:**

- Build task queue dashboards
- Monitor pending work items
- Track SLA compliance
- Generate workload reports

**Debugging and Auditing:**

- Investigate why workflows paused
- Review AI agent decision-making
- Analyse execution performance
- Export audit trails for compliance

**Operational Tasks:**

- Cancel stale or invalid executions
- Clean up abandoned workflows
- Batch process approval queues
- Implement timeout policies

### Integration Points

This module works in concert with:

- **Graph API** - For creating and executing workflows
- **WebSocket API** - For resuming paused executions and real-time updates
- **HTTP Execution API** - For streaming execution with checkpoint support
- **PausedExecutionService** - Service layer providing business logic
- **LangGraph Checkpoint Store** - Persistent storage for execution state

The Execution API is essential for building production-grade AI workflows that require human oversight, approval gates,
or complex multi-step processes with pause-and-resume capabilities.
