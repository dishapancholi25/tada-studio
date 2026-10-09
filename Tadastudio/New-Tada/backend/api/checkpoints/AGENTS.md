# Checkpoints API Module

## Overview

The Checkpoints API module provides REST API endpoints for managing workflow checkpoints in LangGraph-based executions.
It enables retrieval of checkpoint history, resumption from specific checkpoints, and monitoring of the checkpoint
system status.

**Location:** [backend/api/checkpoints/](../../backend/api/checkpoints/)

**Base Path:** `/api/checkpoints`

**Primary Responsibilities:**

- Retrieve checkpoint history for workflow threads
- Resume workflow execution from specific checkpoints
- Provide new input when resuming paused workflows
- Monitor checkpoint system status and capabilities
- Validate execution engine checkpoint support

## Architecture

### Module Structure

```
backend/api/checkpoints/
├── __init__.py           # Module exports (router)
├── routes.py             # API endpoint definitions (223 lines)
├── models.py             # Pydantic request/response models (100 lines)
└── dependencies.py       # FastAPI dependency functions (63 lines)
```

**File Descriptions:**

- ****init**.py**: Exports the checkpoint router for inclusion in the main FastAPI application
- **routes.py**: Defines all checkpoint-related HTTP endpoints with business logic
- **models.py**: Pydantic models for request validation and response serialization
- **dependencies.py**: FastAPI dependency injection functions for engine validation

### Design Pattern

The Checkpoints API follows a **simplified direct-integration architecture** (unlike the more complex handler-based
pattern used in the Graph API):

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
Dependency Validation (dependencies.py)
    ↓
Execution Engine (direct method calls)
    ↓
LangGraph Checkpoint System
```

**Benefits:**

- Minimal abstraction for simple checkpoint operations
- Direct access to execution engine checkpoint methods
- Clear dependency validation via FastAPI dependencies
- Lightweight implementation suitable for focused functionality

**Difference from Graph API:**
The checkpoints module does NOT use separate handlers or services subdirectories because:

- Operations are straightforward (retrieve, resume, status)
- All logic directly delegates to the execution engine
- No complex business logic requiring separate handler layer
- Smaller scope compared to the comprehensive Graph API

## Authentication & Authorisation

### Authentication

The Checkpoints API endpoints **do not explicitly require authentication dependencies** in their route definitions. This
design choice suggests:

**Infrastructure-Level Authentication:**

- Authentication likely handled by OAuth2-Proxy at the infrastructure level
- All requests to `/api/*` endpoints pass through authentication middleware
- Headers like `X-Forwarded-User` available but not explicitly consumed

**Usage Pattern:**

```python
@router.get(
    "/threads/{thread_id}",
    response_model=List[CheckpointResponse],
    dependencies=[Depends(require_langgraph_engine)],  # Engine validation only
)
async def get_thread_checkpoints(thread_id: str):
    # No explicit current_user parameter
    # Authentication handled at infrastructure level
    ...
```

### Authorisation

**Thread-Scoped Access:**
While not explicitly enforced in the checkpoint API code, authorisation follows these principles:

- **Thread Ownership**: Checkpoints belong to workflow execution threads
- **Workflow Ownership**: Threads are created by workflow executions owned by users
- **Implicit Scoping**: Access control enforced by the execution engine and workflow ownership
- **Infrastructure Trust**: Assumes requests reaching the API have passed infrastructure-level auth

**Security Note:**
If exposing checkpoint endpoints to external users, consider adding explicit user extraction and authorisation checks to
ensure users can only access checkpoints for their own workflows.

**Recommended Enhancement:**

```python
from backend.api.auth.dependencies import get_current_user

@router.get("/threads/{thread_id}")
async def get_thread_checkpoints(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)  # Add this
):
    # Validate thread belongs to current_user
    # Then proceed with checkpoint retrieval
    ...
```

## API Endpoints

### Checkpoint Retrieval

#### `GET /api/checkpoints/threads/{thread_id}`

Retrieve all checkpoints for a specific workflow execution thread. Returns a list of checkpoint snapshots with metadata.

**Authentication:** Infrastructure-level (OAuth2-Proxy assumed)

**Path Parameters:**

- `thread_id` (string, required) - The unique thread identifier for the workflow execution

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
[
  {
    "checkpoint_id": "1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7",
    "thread_id": "workflow_123_thread_456",
    "timestamp": "2025-10-20T14:32:15.123456Z",
    "metadata": {
      "status": "paused",
      "node": "human_input_node",
      "step": 5,
      "waiting_for_input": true
    }
  },
  {
    "checkpoint_id": "1ef89c3a-1a4b-5c2d-7e81-a1b2c3d4e5f6",
    "thread_id": "workflow_123_thread_456",
    "timestamp": "2025-10-20T14:31:42.987654Z",
    "metadata": {
      "status": "running",
      "node": "data_processing_node",
      "step": 4
    }
  }
]
```

**Use Cases:**

- **Debugging**: Inspect workflow execution history to understand where a workflow paused or failed
- **Resumption Selection**: Display available checkpoints to users for manual resumption
- **Audit Trail**: Track workflow execution progression through checkpoints
- **State Inspection**: Examine metadata to understand workflow state at each checkpoint

**Behaviour:**

1. Validates that the execution engine supports checkpoint operations (via `require_langgraph_engine` dependency)
2. Calls `engine.get_checkpoints(thread_id)` to retrieve checkpoint history
3. Transforms raw checkpoint data into standardized `CheckpointResponse` models
4. Returns checkpoints in chronological order (implementation-dependent)
5. Returns empty list `[]` if no checkpoints exist for the thread

**Validation:**

- `thread_id` must be a non-empty string
- Execution engine must implement `get_checkpoints` method
- Thread ID should correspond to an actual workflow execution (not validated at API level)

**Errors:**

**501 Not Implemented** - Engine doesn't support checkpoints:

```json
{
  "detail": "Current execution engine does not support checkpoints"
}
```

**500 Internal Server Error** - Failed to retrieve checkpoints:

```json
{
  "detail": "Failed to retrieve checkpoints: Database connection error"
}
```

**Edge Cases:**

- **Non-existent thread**: Returns empty list rather than error
- **Malformed thread_id**: Passes to engine, may return empty list or error depending on engine implementation
- **Large checkpoint history**: No pagination implemented, all checkpoints returned

---

### Checkpoint Resumption

#### `POST /api/checkpoints/resume`

Resume workflow execution from a specific checkpoint, optionally providing new input data. This is used when a workflow
has paused (e.g., waiting for human input) and needs to continue execution.

**Authentication:** Infrastructure-level (OAuth2-Proxy assumed)

**Path Parameters:** None

**Query Parameters:** None

**Request Body:**

```json
{
  "graph_name": "customer_support_workflow",
  "thread_id": "workflow_123_thread_456",
  "checkpoint_id": "1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7",
  "new_input": {
    "user_response": "Yes, please proceed with the refund",
    "approval_status": "approved",
    "additional_notes": "Customer confirmed via email"
  }
}
```

**Request Body Schema:**

- `graph_name` (string, required, min_length=1) - Name of the workflow graph to resume
- `thread_id` (string, required, min_length=1) - Thread identifier for the paused execution
- `checkpoint_id` (string, required, min_length=1) - Specific checkpoint to resume from
- `new_input` (object, optional) - New input data to provide to the resumed workflow

**Response:**

```json
{
  "status": "resumed",
  "thread_id": "workflow_123_thread_456",
  "checkpoint_id": "1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7",
  "result": {
    "execution_id": "exec_789",
    "final_output": {
      "refund_processed": true,
      "refund_amount": 99.99,
      "transaction_id": "txn_abc123"
    },
    "steps_executed": 8,
    "completion_time": "2025-10-20T14:35:22.456789Z"
  }
}
```

**Use Cases:**

- **Human-in-the-Loop**: Resume workflows paused for human approval or input
- **Interactive Workflows**: Continue execution after collecting user feedback
- **Error Recovery**: Retry workflows from last successful checkpoint after fixing issues
- **Conditional Branching**: Provide different input to explore alternative execution paths
- **Testing**: Test workflow behaviour from specific states

**Behaviour:**

1. Validates request body against `ResumeExecutionRequest` schema
2. Checks execution engine supports `resume_from_checkpoint` method
3. Calls `await engine.resume_from_checkpoint()` with provided parameters
4. Execution resumes from the specified checkpoint state
5. If `new_input` provided, it's passed to the workflow's next node
6. Returns immediately with status "resumed" (execution may be async)
7. Actual execution result included in the `result` field

**Validation:**

- All string fields (`graph_name`, `thread_id`, `checkpoint_id`) must be non-empty
- `new_input` must be a valid JSON object if provided
- Checkpoint must exist and be resumable (validated by execution engine)
- Graph must exist and match the checkpoint's original graph

**Errors:**

**501 Not Implemented** - Engine doesn't support resumption:

```json
{
  "detail": "Current execution engine does not support checkpoint resumption"
}
```

**500 Internal Server Error** - Failed to resume:

```json
{
  "detail": "Failed to resume from checkpoint: Checkpoint not found or invalid"
}
```

**422 Validation Error** - Invalid request body:

```json
{
  "detail": [
    {
      "loc": ["body", "graph_name"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**Special Considerations:**

- **Asynchronous Execution**: The resume operation may complete asynchronously; the API returns immediately
- **State Consistency**: Engine ensures workflow state at checkpoint is correctly restored
- **Input Merging**: How `new_input` merges with checkpoint state depends on workflow design
- **Idempotency**: Resuming the same checkpoint multiple times may produce different results if workflow has side
  effects

**Example Workflow:**

```python
# 1. User pauses a workflow waiting for approval
# Workflow creates checkpoint: cp_waiting_approval

# 2. Later, user provides approval
response = requests.post(
    "http://localhost:8000/api/checkpoints/resume",
    json={
        "graph_name": "approval_workflow",
        "thread_id": "thread_abc123",
        "checkpoint_id": "cp_waiting_approval",
        "new_input": {
            "approved": True,
            "approver": "john.doe@company.com"
        }
    }
)

# 3. Workflow resumes and completes
result = response.json()
print(f"Resumed: {result['status']}")
print(f"Result: {result['result']['final_output']}")
```

---

### System Status

#### `GET /api/checkpoints/status`

Get the current status and configuration of the checkpoint system, including whether checkpointing is enabled and which
execution engine is in use.

**Authentication:** None (public endpoint for system monitoring)

**Path Parameters:** None

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
{
  "checkpointing_enabled": true,
  "engine_type": "execution_engine",
  "engine_supports_checkpoints": true
}
```

**Response Schema:**

- `checkpointing_enabled` (boolean) - Whether checkpointing is enabled via `ENABLE_CHECKPOINTING` environment variable
- `engine_type` (string) - Type of execution engine currently configured ("execution_engine")
- `engine_supports_checkpoints` (boolean) - Whether the engine has checkpoint capabilities (always true in current
  implementation)

**Use Cases:**

- **Health Checks**: Verify checkpoint system is available before attempting checkpoint operations
- **Configuration Validation**: Confirm checkpointing is enabled in the environment
- **Troubleshooting**: Debug checkpoint-related issues by checking system configuration
- **Monitoring**: Include in system health monitoring dashboards
- **Client Configuration**: Allow clients to adjust behaviour based on checkpoint availability

**Behaviour:**

1. Reads `ENABLE_CHECKPOINTING` environment variable (defaults to "true")
2. Retrieves execution engine type from `ExecutionConfig.get_execution_engine_type()`
3. Returns current checkpoint system status
4. No validation or engine interaction required (read-only config check)

**Configuration:**
The `checkpointing_enabled` field reflects the `ENABLE_CHECKPOINTING` environment variable:

```bash
# Enable checkpointing (default)
export ENABLE_CHECKPOINTING=true

# Disable checkpointing
export ENABLE_CHECKPOINTING=false
```

**Response Examples:**

**Checkpointing Enabled:**

```json
{
  "checkpointing_enabled": true,
  "engine_type": "execution_engine",
  "engine_supports_checkpoints": true
}
```

**Checkpointing Disabled:**

```json
{
  "checkpointing_enabled": false,
  "engine_type": "execution_engine",
  "engine_supports_checkpoints": true
}
```

**Note:**
Even if `checkpointing_enabled` is `false`, the engine may still support checkpoints technically. The
`checkpointing_enabled` flag indicates whether the system is configured to use checkpointing, not whether it's capable
of it.

**Errors:**
This endpoint typically doesn't fail, but may return:

**500 Internal Server Error** - Configuration read failure:

```json
{
  "detail": "Failed to read checkpoint configuration"
}
```

**Use in Client Code:**

```python
import requests

def check_checkpoint_availability():
    """Check if checkpoint system is available."""
    response = requests.get("http://localhost:8000/api/checkpoints/status")
    status = response.json()

    if not status["checkpointing_enabled"]:
        print("⚠️  Checkpointing is disabled in configuration")
        return False

    if not status["engine_supports_checkpoints"]:
        print(f"⚠️  Engine '{status['engine_type']}' doesn't support checkpoints")
        return False

    print("✅ Checkpoint system is available")
    return True

# Use before attempting checkpoint operations
if check_checkpoint_availability():
    # Safe to use checkpoint endpoints
    checkpoints = get_thread_checkpoints(thread_id)
```

---

## Error Handling

### Error Response Format

All checkpoint endpoints return errors in FastAPI's standard error format:

```json
{
  "detail": "Human-readable error message describing what went wrong"
}
```

For validation errors (422 Unprocessable Entity), the format includes detailed field information:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Error message",
      "type": "error_type"
    }
  ]
}
```

### Common Error Codes

#### 501 Not Implemented

**When:** Execution engine doesn't support required checkpoint operations

**Endpoints Affected:**

- `GET /api/checkpoints/threads/{thread_id}`
- `POST /api/checkpoints/resume`

**Example:**

```json
{
  "detail": "Current execution engine does not support checkpoints"
}
```

**Cause:**

- Engine missing `get_checkpoints` method (for retrieval endpoint)
- Engine missing `resume_from_checkpoint` method (for resume endpoint)
- Wrong execution engine type configured

**Resolution:**

- Ensure LangGraph execution engine is configured
- Check `EXECUTION_ENGINE` environment variable
- Verify execution engine initialization in application startup

#### 500 Internal Server Error

**When:** Unexpected error during checkpoint operations

**Endpoints Affected:** All endpoints

**Examples:**

**Checkpoint retrieval failure:**

```json
{
  "detail": "Failed to retrieve checkpoints: Database connection timeout"
}
```

**Resumption failure:**

```json
{
  "detail": "Failed to resume from checkpoint: Invalid checkpoint state"
}
```

**Causes:**

- Database connection issues
- Checkpoint storage corruption
- Invalid checkpoint data
- Execution engine internal errors
- Network failures communicating with checkpoint storage

**Resolution:**

- Check database/storage connectivity
- Verify checkpoint storage integrity
- Review execution engine logs
- Ensure checkpoint IDs are valid

#### 422 Unprocessable Entity

**When:** Request body validation fails

**Endpoints Affected:**

- `POST /api/checkpoints/resume`

**Example:**

```json
{
  "detail": [
    {
      "loc": ["body", "graph_name"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    },
    {
      "loc": ["body", "new_input"],
      "msg": "value is not a valid dict",
      "type": "type_error.dict"
    }
  ]
}
```

**Causes:**

- Empty required string fields (`graph_name`, `thread_id`, `checkpoint_id`)
- Invalid `new_input` format (must be JSON object)
- Missing required fields

**Resolution:**

- Ensure all required fields are provided
- Validate string fields are non-empty
- Ensure `new_input` is a valid JSON object (or null)

#### 404 Not Found

**Note:** The checkpoint API does **not** return 404 errors for non-existent threads or checkpoints. Instead:

- **Non-existent thread**: `GET /threads/{thread_id}` returns empty list `[]`
- **Invalid checkpoint**: `POST /resume` returns 500 error from execution engine

This design choice prioritizes simplicity over strict HTTP semantics.

### Error Handling Example

```python
import requests
from requests.exceptions import RequestException

def safe_resume_checkpoint(graph_name, thread_id, checkpoint_id, new_input=None):
    """
    Safely resume from checkpoint with comprehensive error handling.

    Args:
        graph_name: Workflow graph name
        thread_id: Thread identifier
        checkpoint_id: Checkpoint to resume from
        new_input: Optional input data

    Returns:
        dict: Resume result, or None if failed
    """
    try:
        # First check if checkpointing is available
        status_response = requests.get("http://localhost:8000/api/checkpoints/status")
        status_response.raise_for_status()
        status = status_response.json()

        if not status["checkpointing_enabled"]:
            print("Error: Checkpointing is disabled")
            return None

        if not status["engine_supports_checkpoints"]:
            print(f"Error: Engine {status['engine_type']} doesn't support checkpoints")
            return None

        # Attempt to resume
        resume_response = requests.post(
            "http://localhost:8000/api/checkpoints/resume",
            json={
                "graph_name": graph_name,
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "new_input": new_input
            }
        )

        # Handle specific error codes
        if resume_response.status_code == 422:
            errors = resume_response.json()["detail"]
            print("Validation errors:")
            for error in errors:
                field = " -> ".join(str(loc) for loc in error["loc"])
                print(f"  {field}: {error['msg']}")
            return None

        elif resume_response.status_code == 501:
            print("Error: Execution engine doesn't support checkpoint resumption")
            print("Check EXECUTION_ENGINE configuration")
            return None

        elif resume_response.status_code == 500:
            error_detail = resume_response.json()["detail"]
            print(f"Server error: {error_detail}")
            # Could implement retry logic here
            return None

        # Success
        resume_response.raise_for_status()
        result = resume_response.json()
        print(f"✅ Successfully resumed from checkpoint {checkpoint_id}")
        return result

    except RequestException as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Example usage
result = safe_resume_checkpoint(
    graph_name="customer_workflow",
    thread_id="thread_123",
    checkpoint_id="cp_456",
    new_input={"approved": True}
)

if result:
    print(f"Execution result: {result['result']}")
else:
    print("Failed to resume checkpoint")
```

---

## Integration with Services Layer

### Dependency Flow

The Checkpoints API integrates directly with the execution engine without intermediate service layers:

```
Route (routes.py)
    ↓
Dependency Validation (dependencies.py)
    ↓
Dependency Injection (get_execution_engine)
    ↓
Execution Engine Methods
    ↓
LangGraph Checkpoint System
```

**Key Components:**

1. **ExecutionConfig** (`backend.services.config.ExecutionConfig`):
    - Provides configuration for checkpointing system
    - Methods: `use_checkpointing()`, `get_execution_engine_type()`
    - Reads environment variables

2. **Dependency Injection** (`backend.services.dependency_injection.get_execution_engine`):
    - Returns singleton execution engine instance
    - Engine type determined by application configuration
    - Ensures consistent engine across all endpoints

3. **Execution Engine** (returned by `get_execution_engine()`):
    - Must implement `get_checkpoints(thread_id)` method
    - Must implement `resume_from_checkpoint()` method
    - Typically LangGraph-based engine with checkpoint support

### Example Integration

**Complete Request Flow:**

```python
# 1. Route Handler (routes.py)
@router.get(
    "/threads/{thread_id}",
    response_model=List[CheckpointResponse],
    dependencies=[Depends(require_langgraph_engine)],  # Validation dependency
)
async def get_thread_checkpoints(thread_id: str) -> List[CheckpointResponse]:
    """Route handler - thin HTTP layer."""

    # 2. Get execution engine via dependency injection
    engine = get_execution_engine()

    # 3. Validate engine has required method
    if not hasattr(engine, "get_checkpoints"):
        raise HTTPException(
            status_code=501,
            detail="Current execution engine does not support checkpoints"
        )

    # 4. Call engine method directly
    checkpoints = engine.get_checkpoints(thread_id)

    # 5. Transform to response models
    return [
        CheckpointResponse(
            checkpoint_id=cp.get("checkpoint_id", ""),
            thread_id=cp.get("thread_id", thread_id),
            timestamp=cp.get("timestamp", ""),
            metadata=cp.get("metadata"),
        )
        for cp in checkpoints
    ]
```

**Dependency Validation (dependencies.py):**

```python
def require_langgraph_engine() -> bool:
    """
    FastAPI dependency to ensure checkpoint support.

    Currently always returns True (all engines support checkpoints).
    Maintained for backward compatibility and future extensibility.
    """
    # Future: Could validate engine type here
    # engine = get_execution_engine()
    # if not isinstance(engine, LangGraphEngine):
    #     raise HTTPException(501, "LangGraph engine required")

    return True


def get_engine_with_checkpoint_support() -> Any:
    """
    Alternative dependency that returns validated engine.

    Verifies engine has checkpoint methods before returning.
    """
    engine = get_execution_engine()

    if not hasattr(engine, "get_checkpoints") or not hasattr(
        engine, "resume_from_checkpoint"
    ):
        raise HTTPException(
            status_code=501,
            detail="Current execution engine does not support checkpoints",
        )

    return engine
```

**Configuration Integration:**

```python
from backend.services.config import ExecutionConfig

# Check if checkpointing is enabled
enabled = ExecutionConfig.use_checkpointing()
# Reads: os.getenv("ENABLE_CHECKPOINTING", "true").lower() == "true"

# Get engine type
engine_type = ExecutionConfig.get_execution_engine_type()
# Returns: "execution_engine"
```

### Services Used

The Checkpoints API depends on these core services:

#### 1. ExecutionConfig Service

**Location:** `backend/services/config/execution.py`

**Purpose:** Provides execution and checkpoint configuration

**Methods Used:**

- `use_checkpointing() -> bool`: Returns whether checkpointing is enabled
- `get_execution_engine_type() -> str`: Returns execution engine type identifier

**Example:**

```python
from backend.services.config import ExecutionConfig

# Check configuration
if ExecutionConfig.use_checkpointing():
    print("Checkpointing is enabled")

engine_type = ExecutionConfig.get_execution_engine_type()
print(f"Using engine: {engine_type}")
```

#### 2. Execution Engine (Dependency Injection)

**Location:** `backend/services/dependency_injection.py`

**Purpose:** Provides singleton access to execution engine

**Methods Used:**

- `get_execution_engine() -> ExecutionEngine`: Returns engine instance

**Required Engine Methods:**

- `get_checkpoints(thread_id: str) -> List[Dict]`: Retrieve checkpoints for thread
- `async resume_from_checkpoint(graph_name, thread_id, checkpoint_id, new_input) -> Dict`: Resume execution

**Example:**

```python
from backend.services.dependency_injection import get_execution_engine

engine = get_execution_engine()

# Verify checkpoint support
if hasattr(engine, "get_checkpoints"):
    checkpoints = engine.get_checkpoints("thread_123")
    print(f"Found {len(checkpoints)} checkpoints")

# Resume from checkpoint
if hasattr(engine, "resume_from_checkpoint"):
    result = await engine.resume_from_checkpoint(
        graph_name="my_workflow",
        thread_id="thread_123",
        checkpoint_id="cp_456",
        new_input={"user_input": "proceed"}
    )
    print(f"Resume result: {result}")
```

#### 3. Logger Service

**Location:** `backend/services/config.get_logger`

**Purpose:** Provides structured logging for checkpoint operations

**Usage in Module:**

```python
from backend.services.config import get_logger

logger = get_logger("checkpoint_api")

# Log checkpoint operations
logger.info(f"[CHECKPOINT-API] Retrieving checkpoints for thread: {thread_id}")
logger.debug(f"[CHECKPOINT-API] Resume with new input: {new_input}")
logger.error(f"[CHECKPOINT-API] Failed to resume: {error}", exc_info=True)
```

### No Separate Services Layer

Unlike the Graph API module, the Checkpoints API does **not** have a `services/` subdirectory. This is intentional:

**Why No Services Layer:**

1. **Simple Operations**: Checkpoint operations are straightforward delegations to the engine
2. **No Business Logic**: No complex business rules requiring separate service classes
3. **Direct Delegation**: All operations directly call execution engine methods
4. **Minimal Abstraction**: Over-engineering would add unnecessary complexity

**When You Might Add Services:**
If checkpoint functionality expands to include:

- Complex checkpoint querying with filters
- Checkpoint metadata enrichment
- Checkpoint storage management
- Checkpoint analytics and reporting
- Multi-engine checkpoint aggregation

Then consider adding a `CheckpointService` class for business logic.

**Current Pattern (Sufficient):**

```python
# Simple, direct delegation
engine = get_execution_engine()
checkpoints = engine.get_checkpoints(thread_id)
```

**Future Pattern (If Complexity Grows):**

```python
# Business logic in service layer
checkpoint_service = CheckpointService(engine)
checkpoints = checkpoint_service.get_filtered_checkpoints(
    thread_id,
    filter_by_status="paused",
    include_metadata=True,
    sort_order="desc"
)
```

---

## Usage Examples

### Complete Checkpoint Workflow Example

This example demonstrates a complete workflow involving checkpoint retrieval, status checking, and resumption.

#### Scenario: Human-in-the-Loop Approval Workflow

```python
import requests
from typing import Dict, List, Optional
from datetime import datetime

BASE_URL = "http://localhost:8000"

class CheckpointClient:
    """Client for interacting with the Checkpoints API."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    def check_system_status(self) -> Dict:
        """Check if checkpoint system is available."""
        response = requests.get(f"{self.base_url}/api/checkpoints/status")
        response.raise_for_status()
        return response.json()

    def get_thread_checkpoints(self, thread_id: str) -> List[Dict]:
        """Get all checkpoints for a thread."""
        response = requests.get(
            f"{self.base_url}/api/checkpoints/threads/{thread_id}"
        )
        response.raise_for_status()
        return response.json()

    def resume_from_checkpoint(
        self,
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        new_input: Optional[Dict] = None
    ) -> Dict:
        """Resume execution from a checkpoint."""
        payload = {
            "graph_name": graph_name,
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
        }
        if new_input is not None:
            payload["new_input"] = new_input

        response = requests.post(
            f"{self.base_url}/api/checkpoints/resume",
            json=payload
        )
        response.raise_for_status()
        return response.json()


def workflow_with_checkpoints():
    """
    Complete workflow example: Purchase approval process.

    Workflow steps:
    1. Submit purchase request
    2. Workflow pauses at approval checkpoint
    3. Retrieve checkpoints to find paused state
    4. Manager provides approval
    5. Resume workflow from checkpoint
    6. Workflow completes purchase
    """
    client = CheckpointClient()

    # Step 1: Check system availability
    print("=" * 60)
    print("STEP 1: Checking checkpoint system status")
    print("=" * 60)

    status = client.check_system_status()
    print(f"Checkpointing enabled: {status['checkpointing_enabled']}")
    print(f"Engine type: {status['engine_type']}")
    print(f"Engine supports checkpoints: {status['engine_supports_checkpoints']}")

    if not status["checkpointing_enabled"]:
        print("\n❌ Checkpointing is disabled. Cannot proceed.")
        return

    print("\n✅ Checkpoint system is ready\n")

    # Step 2: Assume workflow was started and is now paused
    # In real scenario, workflow would be started via Graph API execution endpoint
    workflow_name = "purchase_approval_workflow"
    thread_id = "workflow_purchase_12345_thread_67890"

    print("=" * 60)
    print("STEP 2: Retrieve checkpoints for paused workflow")
    print("=" * 60)
    print(f"Thread ID: {thread_id}")

    checkpoints = client.get_thread_checkpoints(thread_id)
    print(f"\nFound {len(checkpoints)} checkpoints:\n")

    for i, checkpoint in enumerate(checkpoints, 1):
        print(f"Checkpoint {i}:")
        print(f"  ID: {checkpoint['checkpoint_id']}")
        print(f"  Timestamp: {checkpoint['timestamp']}")
        print(f"  Metadata: {checkpoint.get('metadata', {})}")
        print()

    # Step 3: Find the checkpoint waiting for approval
    paused_checkpoint = None
    for checkpoint in checkpoints:
        metadata = checkpoint.get("metadata", {})
        if metadata.get("status") == "paused" and metadata.get("waiting_for_approval"):
            paused_checkpoint = checkpoint
            break

    if not paused_checkpoint:
        print("❌ No paused checkpoint found waiting for approval")
        return

    print("=" * 60)
    print("STEP 3: Found paused checkpoint waiting for approval")
    print("=" * 60)
    print(f"Checkpoint ID: {paused_checkpoint['checkpoint_id']}")
    print(f"Waiting at node: {paused_checkpoint['metadata'].get('node')}")
    print(f"Purchase amount: ${paused_checkpoint['metadata'].get('purchase_amount')}")
    print()

    # Step 4: Manager provides approval input
    print("=" * 60)
    print("STEP 4: Manager providing approval input")
    print("=" * 60)

    approval_input = {
        "approved": True,
        "approver_email": "manager@company.com",
        "approver_name": "Sarah Johnson",
        "approval_notes": "Approved for Q4 equipment budget",
        "approval_timestamp": datetime.utcnow().isoformat() + "Z"
    }

    print(f"Approval input: {approval_input}\n")

    # Step 5: Resume workflow with approval
    print("=" * 60)
    print("STEP 5: Resuming workflow from checkpoint")
    print("=" * 60)

    try:
        result = client.resume_from_checkpoint(
            graph_name=workflow_name,
            thread_id=thread_id,
            checkpoint_id=paused_checkpoint["checkpoint_id"],
            new_input=approval_input
        )

        print(f"Status: {result['status']}")
        print(f"Thread ID: {result['thread_id']}")
        print(f"Checkpoint ID: {result['checkpoint_id']}")
        print(f"\nExecution result:")
        print(f"  Purchase processed: {result['result'].get('purchase_processed')}")
        print(f"  Order ID: {result['result'].get('order_id')}")
        print(f"  Total amount: ${result['result'].get('total_amount')}")
        print(f"  Estimated delivery: {result['result'].get('estimated_delivery')}")

        print("\n✅ Workflow resumed and completed successfully!")

    except requests.HTTPError as e:
        print(f"\n❌ Failed to resume workflow: {e}")
        print(f"Response: {e.response.json()}")
        return

    # Step 6: Verify checkpoint history includes new checkpoints
    print("\n" + "=" * 60)
    print("STEP 6: Verify updated checkpoint history")
    print("=" * 60)

    updated_checkpoints = client.get_thread_checkpoints(thread_id)
    print(f"Total checkpoints after resumption: {len(updated_checkpoints)}")
    print("\nLatest checkpoint:")
    latest = updated_checkpoints[0]
    print(f"  ID: {latest['checkpoint_id']}")
    print(f"  Timestamp: {latest['timestamp']}")
    print(f"  Status: {latest.get('metadata', {}).get('status', 'completed')}")


# Run the complete workflow example
if __name__ == "__main__":
    workflow_with_checkpoints()
```

**Expected Output:**

```
============================================================
STEP 1: Checking checkpoint system status
============================================================
Checkpointing enabled: True
Engine type: execution_engine
Engine supports checkpoints: True

✅ Checkpoint system is ready

============================================================
STEP 2: Retrieve checkpoints for paused workflow
============================================================
Thread ID: workflow_purchase_12345_thread_67890

Found 3 checkpoints:

Checkpoint 1:
  ID: 1ef89c5a-3c6d-7e4f-9g92-b3c4d5e6f7g8
  Timestamp: 2025-10-20T15:45:30.123456Z
  Metadata: {'status': 'paused', 'node': 'approval_node', 'waiting_for_approval': True, 'purchase_amount': 2499.99}

Checkpoint 2:
  ID: 1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7
  Timestamp: 2025-10-20T15:45:15.987654Z
  Metadata: {'status': 'running', 'node': 'validation_node', 'step': 2}

Checkpoint 3:
  ID: 1ef89c3a-1a4b-5c2d-7e81-a1b2c3d4e5f6
  Timestamp: 2025-10-20T15:45:01.654321Z
  Metadata: {'status': 'running', 'node': 'submission_node', 'step': 1}

============================================================
STEP 3: Found paused checkpoint waiting for approval
============================================================
Checkpoint ID: 1ef89c5a-3c6d-7e4f-9g92-b3c4d5e6f7g8
Waiting at node: approval_node
Purchase amount: $2499.99

============================================================
STEP 4: Manager providing approval input
============================================================
Approval input: {'approved': True, 'approver_email': 'manager@company.com', 'approver_name': 'Sarah Johnson', 'approval_notes': 'Approved for Q4 equipment budget', 'approval_timestamp': '2025-10-20T15:47:22.456789Z'}

============================================================
STEP 5: Resuming workflow from checkpoint
============================================================
Status: resumed
Thread ID: workflow_purchase_12345_thread_67890
Checkpoint ID: 1ef89c5a-3c6d-7e4f-9g92-b3c4d5e6f7g8

Execution result:
  Purchase processed: True
  Order ID: ORD-2025-10-20-12345
  Total amount: $2499.99
  Estimated delivery: 2025-10-27

✅ Workflow resumed and completed successfully!

============================================================
STEP 6: Verify updated checkpoint history
============================================================
Total checkpoints after resumption: 5
Latest checkpoint:
  ID: 1ef89c6a-4d7e-8f5g-0h03-c4d5e6f7g8h9
  Timestamp: 2025-10-20T15:47:25.789012Z
  Status: completed
```

### JavaScript/TypeScript Example

```typescript
interface CheckpointResponse {
  checkpoint_id: string;
  thread_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

interface ResumeRequest {
  graph_name: string;
  thread_id: string;
  checkpoint_id: string;
  new_input?: Record<string, any>;
}

interface ResumeResponse {
  status: string;
  thread_id: string;
  checkpoint_id: string;
  result: any;
}

class CheckpointAPI {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async getCheckpoints(threadId: string): Promise<CheckpointResponse[]> {
    const response = await fetch(
      `${this.baseUrl}/api/checkpoints/threads/${threadId}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get checkpoints: ${response.statusText}`);
    }

    return response.json();
  }

  async resumeCheckpoint(request: ResumeRequest): Promise<ResumeResponse> {
    const response = await fetch(`${this.baseUrl}/api/checkpoints/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Resume failed: ${error.detail}`);
    }

    return response.json();
  }

  async checkStatus(): Promise<{
    checkpointing_enabled: boolean;
    engine_type: string;
    engine_supports_checkpoints: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/api/checkpoints/status`);

    if (!response.ok) {
      throw new Error(`Status check failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// Usage example
async function handleWorkflowResumption() {
  const api = new CheckpointAPI();

  try {
    // Check system status
    const status = await api.checkStatus();
    console.log('Checkpoint system status:', status);

    if (!status.checkpointing_enabled) {
      console.error('Checkpointing is disabled');
      return;
    }

    // Get checkpoints
    const threadId = 'workflow_abc_thread_xyz';
    const checkpoints = await api.getCheckpoints(threadId);
    console.log(`Found ${checkpoints.length} checkpoints`);

    // Find paused checkpoint
    const pausedCheckpoint = checkpoints.find(
      cp => cp.metadata?.status === 'paused'
    );

    if (!pausedCheckpoint) {
      console.log('No paused checkpoints found');
      return;
    }

    console.log('Resuming from checkpoint:', pausedCheckpoint.checkpoint_id);

    // Resume with new input
    const result = await api.resumeCheckpoint({
      graph_name: 'customer_workflow',
      thread_id: threadId,
      checkpoint_id: pausedCheckpoint.checkpoint_id,
      new_input: {
        user_decision: 'approve',
        notes: 'Looks good to proceed',
      },
    });

    console.log('Resume successful:', result);
    console.log('Execution result:', result.result);

  } catch (error) {
    console.error('Error during workflow resumption:', error);
  }
}
```

### cURL Examples

**Check System Status:**

```bash
curl -X GET http://localhost:8000/api/checkpoints/status
```

**Get Thread Checkpoints:**

```bash
curl -X GET http://localhost:8000/api/checkpoints/threads/workflow_123_thread_456
```

**Resume from Checkpoint (without new input):**

```bash
curl -X POST http://localhost:8000/api/checkpoints/resume \
  -H "Content-Type: application/json" \
  -d '{
    "graph_name": "my_workflow",
    "thread_id": "workflow_123_thread_456",
    "checkpoint_id": "1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7"
  }'
```

**Resume from Checkpoint (with new input):**

```bash
curl -X POST http://localhost:8000/api/checkpoints/resume \
  -H "Content-Type: application/json" \
  -d '{
    "graph_name": "approval_workflow",
    "thread_id": "workflow_123_thread_456",
    "checkpoint_id": "1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7",
    "new_input": {
      "approved": true,
      "approver": "john.doe@company.com",
      "approval_notes": "Approved for Q4 budget"
    }
  }'
```

**Error Handling in Bash Script:**

```bash
#!/bin/bash

THREAD_ID="workflow_123_thread_456"
CHECKPOINT_ID="1ef89c4a-2b5c-6d3e-8f91-a2b3c4d5e6f7"

# Check system status first
echo "Checking checkpoint system status..."
STATUS_RESPONSE=$(curl -s http://localhost:8000/api/checkpoints/status)
CHECKPOINTING_ENABLED=$(echo "$STATUS_RESPONSE" | jq -r '.checkpointing_enabled')

if [ "$CHECKPOINTING_ENABLED" != "true" ]; then
  echo "Error: Checkpointing is disabled"
  exit 1
fi

echo "Checkpointing is enabled. Proceeding..."

# Get checkpoints
echo "Retrieving checkpoints for thread: $THREAD_ID"
CHECKPOINTS=$(curl -s http://localhost:8000/api/checkpoints/threads/$THREAD_ID)
CHECKPOINT_COUNT=$(echo "$CHECKPOINTS" | jq '. | length')

echo "Found $CHECKPOINT_COUNT checkpoints"

# Resume from checkpoint
echo "Resuming from checkpoint: $CHECKPOINT_ID"
RESUME_RESPONSE=$(curl -s -X POST http://localhost:8000/api/checkpoints/resume \
  -H "Content-Type: application/json" \
  -d "{
    \"graph_name\": \"my_workflow\",
    \"thread_id\": \"$THREAD_ID\",
    \"checkpoint_id\": \"$CHECKPOINT_ID\",
    \"new_input\": {\"user_input\": \"proceed\"}
  }")

# Check for errors
if echo "$RESUME_RESPONSE" | jq -e '.detail' > /dev/null; then
  echo "Error resuming checkpoint:"
  echo "$RESUME_RESPONSE" | jq '.detail'
  exit 1
fi

echo "Resume successful!"
echo "$RESUME_RESPONSE" | jq '.'
```

---

## Performance Considerations

### Endpoint Performance

Checkpoint endpoints have varying performance characteristics based on their operations:

#### Fast Endpoints (< 100ms typical)

**`GET /api/checkpoints/status`**

- **Why Fast:** Simple configuration read, no database queries
- **Typical Latency:** 10-50ms
- **Use Case:** Health checks, monitoring dashboards
- **Optimisation:** Already optimal, no improvements needed

#### Medium Endpoints (100ms - 1s typical)

**`GET /api/checkpoints/threads/{thread_id}`**

- **Why Medium:** Database/storage query for checkpoint history
- **Typical Latency:** 100-500ms depending on checkpoint count
- **Factors Affecting Performance:**
  - Number of checkpoints in thread history
  - Checkpoint storage backend (PostgreSQL, Redis, etc.)
  - Network latency to storage
  - Checkpoint metadata size
- **Degrades When:**
  - Thread has hundreds of checkpoints
  - Checkpoint metadata is very large
  - Storage backend is under load

**Optimisation Tips:**

```python
# Consider limiting checkpoint history in production workflows
# to prevent unbounded growth

# Option 1: Limit checkpoints in workflow configuration
workflow_config = {
    "checkpointer": {
        "max_checkpoints_per_thread": 50,  # Keep only last 50
        "cleanup_strategy": "keep_recent"
    }
}

# Option 2: Implement pagination (future enhancement)
# GET /api/checkpoints/threads/{thread_id}?limit=20&offset=0
```

#### Slow Endpoints (1s+ typical)

**`POST /api/checkpoints/resume`**

- **Why Slow:** Restores workflow state and executes workflow nodes
- **Typical Latency:** 1-10+ seconds depending on workflow complexity
- **Factors Affecting Performance:**
  - Workflow complexity (number of nodes to execute)
  - External API calls in workflow
  - LLM inference time for agent nodes
  - Data processing operations
  - Checkpoint state size to restore
- **Async Execution:** Workflow may continue executing after API returns

**Performance Profile:**

```python
# Resume operation breakdown:
# 1. Checkpoint retrieval:          100-200ms
# 2. State restoration:              200-500ms
# 3. Workflow execution:             1s - 60s+ (varies widely)
# 4. API response:                   immediate (doesn't wait for completion)

# The API returns quickly with status "resumed",
# but actual workflow execution continues asynchronously
```

**Optimisation Tips:**

```python
# 1. Use streaming endpoints for long-running workflows
# Instead of waiting for complete execution, stream progress:
# See: /api/http_execution/stream (HTTP Execution API)

# 2. Monitor execution via WebSocket
# Connect to WebSocket for real-time execution updates:
# See: /api/websocket/execute (WebSocket API)

# 3. Poll execution history for completion
# After resuming, poll execution history endpoint:
from time import sleep

def resume_and_wait(thread_id, checkpoint_id, timeout=60):
    # Resume checkpoint
    response = requests.post("/api/checkpoints/resume", json={...})

    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check execution history for completion
        history = requests.get(f"/api/execution_history?thread_id={thread_id}")
        latest_execution = history.json()[0]

        if latest_execution["status"] == "completed":
            return latest_execution["result"]
        elif latest_execution["status"] == "failed":
            raise Exception(f"Execution failed: {latest_execution['error']}")

        sleep(2)  # Poll every 2 seconds

    raise TimeoutError("Execution did not complete in time")
```

### Optimisation Tips

#### 1. Check Status Before Operations

**Bad Pattern:**

```python
# Directly attempt resume, fails if checkpointing disabled
try:
    result = resume_from_checkpoint(...)
except HTTPError as e:
    if e.response.status_code == 501:
        print("Checkpointing not supported")
```

**Good Pattern:**

```python
# Check status first (fast endpoint), avoid failed requests
status = get_checkpoint_status()
if status["checkpointing_enabled"]:
    result = resume_from_checkpoint(...)
else:
    print("Checkpointing disabled, skipping")
```

**Benefit:** Avoids unnecessary failed requests, better error messages

#### 2. Cache Checkpoint Lists

**Bad Pattern:**

```python
# Retrieve checkpoints multiple times
checkpoints = get_thread_checkpoints(thread_id)
latest = checkpoints[0]

checkpoints = get_thread_checkpoints(thread_id)  # Same query again!
oldest = checkpoints[-1]
```

**Good Pattern:**

```python
# Retrieve once, reuse
checkpoints = get_thread_checkpoints(thread_id)
latest = checkpoints[0]
oldest = checkpoints[-1]

# Cache for a few seconds if needed multiple times
from functools import lru_cache
from time import time

@lru_cache(maxsize=100)
def get_cached_checkpoints(thread_id, cache_time):
    """Cache checkpoints for 5 seconds."""
    return get_thread_checkpoints(thread_id)

# Usage: cache_time changes every 5 seconds, invalidating cache
checkpoints = get_cached_checkpoints(thread_id, int(time() / 5))
```

**Benefit:** Reduces redundant database queries

#### 3. Use Appropriate Timeout Values

**Bad Pattern:**

```python
# Default timeout too short for workflow resumption
requests.post("/api/checkpoints/resume", json={...}, timeout=5)
# May timeout before workflow completes
```

**Good Pattern:**

```python
# Resume endpoint: Use longer timeout (or no timeout)
# API returns quickly, but allow time for initial state restoration
requests.post("/api/checkpoints/resume", json={...}, timeout=30)

# Status endpoint: Short timeout is fine
requests.get("/api/checkpoints/status", timeout=5)

# Checkpoint retrieval: Medium timeout
requests.get(f"/api/checkpoints/threads/{thread_id}", timeout=15)
```

**Benefit:** Prevents premature timeouts, appropriate per endpoint

#### 4. Implement Retry Logic for Resume

**Good Pattern:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def resume_with_retry(graph_name, thread_id, checkpoint_id, new_input):
    """Resume with exponential backoff retry on transient failures."""
    response = requests.post("/api/checkpoints/resume", json={
        "graph_name": graph_name,
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id,
        "new_input": new_input
    })

    # Only retry on 500 errors (server errors), not 4xx (client errors)
    if response.status_code >= 500:
        response.raise_for_status()  # Will trigger retry

    return response.json()

# Usage
result = resume_with_retry(
    "my_workflow",
    "thread_123",
    "cp_456",
    {"input": "data"}
)
```

**Benefit:** Handles transient failures (database connection issues, temporary engine unavailability)

#### 5. Limit Checkpoint History Growth

**Configuration Recommendation:**

```python
# In workflow configuration or environment variables
CHECKPOINT_RETENTION_POLICY = {
    "max_checkpoints_per_thread": 100,  # Limit checkpoints per thread
    "max_age_days": 30,                 # Delete checkpoints older than 30 days
    "cleanup_interval_hours": 24,       # Run cleanup daily
}

# Implement cleanup job (background task)
import asyncio
from datetime import datetime, timedelta

async def cleanup_old_checkpoints():
    """Periodic cleanup of old checkpoints."""
    cutoff_date = datetime.utcnow() - timedelta(days=30)

    # Get all threads (implementation depends on your system)
    threads = get_all_thread_ids()

    for thread_id in threads:
        checkpoints = get_thread_checkpoints(thread_id)

        # Keep only recent checkpoints
        recent_checkpoints = [
            cp for cp in checkpoints
            if datetime.fromisoformat(cp["timestamp"].rstrip("Z")) > cutoff_date
        ]

        # Or keep only last N checkpoints
        recent_checkpoints = checkpoints[:100]

        # Delete old checkpoints via execution engine
        # (Assumes engine has delete_checkpoint method)
        old_checkpoint_ids = [cp["checkpoint_id"] for cp in checkpoints[100:]]
        for cp_id in old_checkpoint_ids:
            engine.delete_checkpoint(thread_id, cp_id)
```

**Benefit:** Prevents unbounded checkpoint storage growth, maintains performance

---

## Related Documentation

### Core API Modules

- **[Graph API](../graph/graph.md)** - Workflow creation and management
  - How to create workflows that use checkpoints
  - Workflow execution endpoints that create checkpoints
  - Thread management and execution contexts

- **[Execution History API](../execution_history/execution_history.md)** - Execution records and logs
  - Track execution status after resuming checkpoints
  - View execution history for threads
  - Monitor workflow completion

- **[HTTP Execution API](../http_execution/http_execution.md)** - Streaming workflow execution
  - Alternative to checkpoint resumption for real-time workflows
  - Server-sent events for execution progress
  - Comparison: streaming vs. checkpoint-based execution

- **[WebSocket API](../websocket/websocket.md)** - Real-time execution monitoring
  - Real-time updates during checkpoint-based execution
  - Alternative to polling for execution status
  - Bi-directional communication for interactive workflows

### Architecture Documentation

- **[API Architecture](../../../docs/for-agents/api/README.md)** - Overall API structure
  - How checkpoint API fits into AgenticStudio architecture
  - Authentication and authorisation patterns
  - API design principles

- **[Services Layer Documentation](../../backend/services/README.md)** - Backend services
  - ExecutionConfig service details
  - Dependency injection pattern
  - Execution engine architecture

### LangGraph Documentation

- **[LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/checkpointing/)** - Official LangGraph
  docs
  - How LangGraph implements checkpoints
  - Checkpoint storage backends
  - State persistence mechanisms

- **[LangGraph Human-in-the-Loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)** - Interruption
  patterns
  - Designing workflows with human interruption points
  - Best practices for checkpoint-based approval workflows
  - Input schemas for resumption

### Configuration Documentation

- **[Environment Variables](../../backend/config/README.md)** - Configuration reference
  - `ENABLE_CHECKPOINTING` environment variable
  - Execution engine configuration
  - Checkpoint storage configuration

---

## Summary

The Checkpoints API module provides a focused, lightweight interface for managing workflow checkpoints in
LangGraph-based executions. It enables critical human-in-the-loop and error recovery patterns through checkpoint
retrieval and resumption.

### Key Features

- **Thread Checkpoint Retrieval**: Query complete checkpoint history for any execution thread
- **Checkpoint Resumption**: Resume paused workflows from specific checkpoints with optional new input
- **System Status Monitoring**: Check checkpoint system availability and configuration
- **Direct Engine Integration**: Minimal abstraction layer for straightforward operations
- **Error Handling**: Comprehensive error responses for engine compatibility and operational failures
- **Flexible Input**: Support for providing new data when resuming paused workflows

### Primary Use Cases

1. **Human-in-the-Loop Workflows**
    - Pause workflows for human approval or decision-making
    - Resume with user-provided input after collecting feedback
    - Enable interactive multi-step processes requiring human oversight

2. **Error Recovery**
    - Resume failed workflows from last successful checkpoint
    - Retry execution after fixing configuration or data issues
    - Minimise wasted computation by avoiding full re-execution

3. **Interactive Agent Workflows**
    - Build conversational agents that pause for user input
    - Support multi-turn interactions with state preservation
    - Enable complex dialogue flows with checkpointed state

4. **Debugging and Development**
    - Inspect workflow state at specific execution points
    - Test workflow behaviour from intermediate states
    - Analyse checkpoint history to understand workflow progression

5. **Workflow Testing**
    - Test different execution paths by resuming with varied inputs
    - Validate conditional logic by exploring branches from checkpoints
    - Regression testing with checkpointed states

### Architectural Simplicity

Unlike the more complex Graph API, the Checkpoints API intentionally maintains a simple architecture without separate
handlers or services layers. This design is appropriate because:

- Operations are straightforward delegations to the execution engine
- No complex business logic requires abstraction
- Direct integration provides clarity and minimal overhead
- Small API surface area (3 endpoints) doesn't warrant additional layers

### Integration Points

The Checkpoints API is designed to work seamlessly with:

- **Graph API**: Workflows created via Graph API automatically support checkpoints
- **Execution History API**: Track execution status after resuming checkpoints
- **HTTP Execution API**: Alternative real-time execution with streaming progress
- **WebSocket API**: Real-time monitoring of checkpoint-based executions

### Performance Characteristics

- **Status Check**: Very fast (< 50ms) - configuration read only
- **Checkpoint Retrieval**: Medium speed (100-500ms) - depends on checkpoint count
- **Checkpoint Resumption**: Variable (1s - 60s+) - depends on workflow complexity

### Future Enhancements

Potential improvements to consider:

1. **Pagination**: Add pagination to checkpoint retrieval for threads with extensive history
2. **Filtering**: Support filtering checkpoints by metadata, date range, or status
3. **Authentication**: Add explicit user-scoped access control for checkpoint operations
4. **Checkpoint Deletion**: Provide endpoint for cleaning up old or unwanted checkpoints
5. **Checkpoint Metadata Search**: Enable querying checkpoints across threads by metadata
6. **Streaming Resumption**: Combine checkpoint resumption with streaming execution updates
7. **Checkpoint Comparison**: Diff checkpoint states to understand execution changes

The Checkpoints API provides the foundation for building robust, interruptible workflows in AgenticStudio, enabling
sophisticated human-in-the-loop patterns and resilient execution strategies.
