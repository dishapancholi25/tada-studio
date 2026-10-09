# HTTP Execution API Module

## Overview

The HTTP Execution API module provides REST endpoints for triggering workflow executions via HTTP requests. This enables
external systems, webhooks, and third-party integrations to execute AgenticStudio workflows programmatically without
requiring UI access.

**Location:** [backend/api/http_execution/](../../backend/api/http_execution/)

**Base Path:** `/api/http-execution`

**Primary Responsibilities:**

- HTTP-triggered workflow execution (JSON and form data)
- Real-time execution streaming via Server-Sent Events (SSE)
- Checkpoint pause/resume for human-in-the-loop workflows
- Legacy authentication token management
- File upload processing for FILE_READ nodes
- Execution status tracking and history
- WebSocket broadcasting to connected UI clients

## Architecture

### Module Structure

```
backend/api/http_execution/
├── __init__.py                # Module exports (router, execution_tokens)
├── routes.py                  # API endpoint definitions (473 lines)
├── models.py                  # Pydantic request/response models (168 lines)
├── exceptions.py              # Custom exception types (183 lines)
├── handlers/                  # Business logic handlers
│   ├── __init__.py
│   ├── execution.py           # Core execution logic (511 lines)
│   ├── sse.py                 # Server-Sent Events streaming (385 lines)
│   ├── checkpoint.py          # Checkpoint pause/resume (418 lines)
│   └── file_upload.py         # File upload processing
├── services/                  # Service layer
│   ├── __init__.py
│   ├── authentication.py      # Security and auth checks (330 lines)
│   ├── token_manager.py       # Legacy token management (213 lines)
│   └── execution_tracker.py   # Execution state tracking
└── utils/                     # Utility functions
    ├── __init__.py
    ├── constants.py           # Configuration constants
    ├── output.py              # Output extraction (197 lines)
    └── request.py             # Request metadata extraction
```

### Design Pattern

The HTTP Execution API follows a **layered handler-service architecture** optimised for external integrations:

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
Security Checks (authentication.py)
    ├── Workflow publishing validation
    ├── Token authentication
    └── Rate limiting enforcement
    ↓
Business Logic Handler (handlers/*.py)
    ├── execution.py - Sync/async execution
    ├── sse.py - Real-time streaming
    └── checkpoint.py - Pause/resume logic
    ↓
Services Layer
    ├── WorkflowPublishingService - Publishing & auth
    ├── ExecutionEngine - Workflow execution
    ├── ExecutionHistoryService - Result storage
    └── RateLimitingService - Rate limiting
    ↓
LangGraph Execution / Database / WebSocket
```

**Benefits:**

- Clear separation between HTTP concerns and business logic
- Centralised security checks in authentication service
- Reusable handlers for different execution modes
- Async/streaming support for real-time updates
- Integration with existing AgenticStudio services

## Authentication & Authorisation

### Authentication

HTTP Execution endpoints use **Personal Access Token (PAT) authentication** for published workflows. Unlike the Graph
API, these endpoints do NOT use OAuth2-Proxy user authentication, as they're designed for external systems and webhooks.

**Authentication Flow:**

```python
# 1. Create a Personal Access Token (PAT) via Settings UI
# Token format: na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo
# Scopes: "workflow:*" (all workflows) or "workflow:specific-name"

# 2. Publish a workflow (via UI or Publishing API)
POST /api/workflow/publish
{
  "workflow_name": "customer-support",
  "require_authentication": true,
  "rate_limit": {"requests_per_minute": 10}
}

# 3. Use PAT token to execute workflow via UUID or custom slug
POST /api/http-execution/trigger/9d04ad87-4762-4ab4-b35f-85a1b002d8e3?token=na_OxQQzj7K...
{
  "message": "Customer inquiry about pricing"
}
```

**UUID-Based Endpoints:**

Published workflows are now identified by **workflow UUID** instead of workflow name. This enables multi-tenant support
where different users can have workflows with the same name.

**Endpoint Format:**

```
/api/http-execution/trigger/{workflow_identifier}

Where workflow_identifier can be:
- Workflow UUID (e.g., "9d04ad87-4762-4ab4-b35f-85a1b002d8e3")
- Custom slug (e.g., "my-custom-endpoint") if configured
```

**Benefits of UUID-Based Endpoints:**

- **Multi-Tenant:** Different users can publish workflows with the same name
- **Unique:** Workflow UUIDs are globally unique across all users
- **Secure:** Cannot accidentally access another user's workflow
- **Scalable:** Supports unlimited users without name collisions

**Token Validation Pattern:**

```python
# In authentication.py
published_workflow = WorkflowPublishingService.get_published_workflow_by_identifier(workflow_identifier)

if published_workflow.require_authentication:
    if not token:
        raise AuthenticationRequiredException(workflow_identifier)

    # Validate Personal Access Token
    validated = UserAPITokenService.validate_token_for_workflow(token, workflow_identifier)
    if not validated:
        raise InvalidAuthenticationTokenException()
```

**Personal Access Token (PAT) Features:**

- Prefix-based identification (`na_` prefix)
- Bcrypt-hashed storage in database
- Scope-based access control (`workflow:*` or `workflow:UUID`)
- Per-token usage tracking and audit logs
- Optional expiration dates
- Revocable at any time via Settings UI

**Legacy Token System (Deprecated):**

The legacy in-memory token system is deprecated and should not be used for new workflows.
See [Token Management](#token-management-3-endpoints) section for migration guidance.

### Authorisation

**Publishing-Based Access Control:**

Workflows must be explicitly published to be executable via HTTP:

```python
# Check if workflow is published
published_workflow = WorkflowPublishingService.get_published_workflow("my-workflow")

if not published_workflow:
    raise WorkflowNotPublishedException("my-workflow")
```

This ensures only intentionally exposed workflows are accessible via HTTP, preventing accidental exposure of draft or
test workflows.

**Rate Limiting:**

Published workflows can specify rate limits to prevent abuse:

```python
# Rate limit configuration
rate_limit_config = {
    "requests_per_minute": 10,
    "requests_per_hour": 100,
    "tokens_per_minute": 50000  # For LLM token limits
}

# Rate limiting is enforced per client (IP or token)
client_identifier = rate_limiting_service.get_client_identifier(client_ip, token)

is_allowed, rate_info = rate_limiting_service.check_rate_limit(
    workflow_name="my-workflow",
    client_identifier=client_identifier,
    rate_limit_config=rate_limit_config
)

if not is_allowed:
    raise RateLimitExceededException(
        limit_type="requests",
        retry_after=60,
        reset_time=1640995200
    )
```

**Access Logging:**

All HTTP execution attempts are logged for audit and monitoring:

```python
WorkflowPublishingService.log_access(
    published_workflow=published_workflow,
    client_ip="192.168.1.100",
    user_agent="curl/7.68.0",
    token_used="abc123xyz",
    authentication_status="success",
    response_status=200,
    execution_id="exec_20251021_143052_customer-support"
)
```

## API Endpoints

### Workflow Execution (3 endpoints)

#### `POST /api/http-execution/trigger/{workflow_identifier}`

Trigger workflow execution via HTTP with JSON payload.

**Authentication:** Required if workflow requires authentication (Personal Access Token)

**Path Parameters:**

- `workflow_identifier` - Workflow UUID or custom slug of the published workflow
  - UUID example: `9d04ad87-4762-4ab4-b35f-85a1b002d8e3`
  - Custom slug example: `customer-support-v2`

**Query Parameters:**

- `token` - Personal Access Token (PAT) with `na_` prefix (required if workflow requires authentication)

**Request Body:**

```json
{
  "message": "Analyse this customer feedback: The product is great but shipping was slow",
  "async_mode": false,
  "timeout": 300
}
```

**Response (Sync Mode - async_mode=false):**

```json
{
  "success": true,
  "execution_id": "exec_20251021_143052_customer-support",
  "status": "completed",
  "output": {
    "sentiment": "positive",
    "issues": ["shipping delay"],
    "priority": "medium",
    "suggested_response": "Thank you for the feedback. We'll improve our shipping times."
  }
}
```

**Response (Async Mode - async_mode=true):**

```json
{
  "success": true,
  "execution_id": "exec_20251021_143052_customer-support",
  "status": "running",
  "status_endpoint": "/api/graph/execution/exec_20251021_143052_customer-support/status",
  "message": "Workflow 'customer-support' execution started successfully"
}
```

**Response (Checkpoint Pause):**

```json
{
  "success": true,
  "execution_id": "exec_20251021_143052_approval-workflow",
  "status": "paused",
  "checkpoint_data": {
    "status": "paused",
    "execution_id": "exec_20251021_143052_approval-workflow",
    "thread_id": "exec_20251021_143052_approval-workflow",
    "checkpoint_id": "1ef9c8f0-8f2a-6b4c-8001-e4c9c8f08f2a",
    "checkpoint_node": "Manager Approval",
    "checkpoint_input": "Budget request: $5,000 for new marketing campaign",
    "resume_endpoint": "/api/http-execution/resume/approval-workflow",
    "resume_instructions": "POST to resume_endpoint with thread_id, checkpoint_id, and user_input"
  }
}
```

**Use Cases:**

- Triggering workflows from external systems (CRM, ticketing systems)
- Processing webhook payloads from third-party services
- Scheduled workflow execution via cron jobs
- Building custom integrations with AgenticStudio

**Behaviour:**

- In sync mode (`async_mode=false`), waits up to `timeout` seconds for completion
- In async mode (`async_mode=true`), returns immediately with execution ID
- Pre-registers execution in execution engine for tracking
- Broadcasts execution start to WebSocket listeners if enabled
- Validates workflow is published and authentication if required
- Enforces rate limits based on workflow configuration
- If workflow pauses at CHECKPOINT node, returns checkpoint data

**Validation:**

- Workflow must exist and be published
- Authentication token required if workflow requires it
- Either `message` or file data must be provided
- Timeout must be positive integer

**Errors:**

- `403 Forbidden` - Workflow not published
- `401 Unauthorized` - Invalid or missing authentication token
- `404 Not Found` - Workflow not found
- `408 Request Timeout` - Execution exceeded timeout (sync mode)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Execution failed

**Example:**

```bash
# Sync execution with UUID
curl -X POST "http://localhost:8000/api/http-execution/trigger/9d04ad87-4762-4ab4-b35f-85a1b002d8e3?token=na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Customer wants refund for order #12345",
    "async_mode": false,
    "timeout": 300
  }'

# Async execution with custom slug (returns immediately)
curl -X POST "http://localhost:8000/api/http-execution/trigger/data-processing-v2?token=na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process latest sales data",
    "async_mode": true
  }'
```

---

#### `POST /api/http-execution/trigger-form/{workflow_identifier}`

Trigger workflow execution via form data with optional file upload.

**Authentication:** Required if workflow requires authentication (Personal Access Token)

**Path Parameters:**

- `workflow_identifier` - Workflow UUID or custom slug of the published workflow

**Query Parameters:**

- `token` - Personal Access Token (PAT) with `na_` prefix (required if workflow requires authentication)

**Form Data:**

- `Message` (optional) - Text message input
- `file` (optional) - File upload for FILE_READ nodes
- `async_mode` (optional, default: false) - Whether to return immediately
- `timeout` (optional, default: 300) - Timeout in seconds for sync mode

**Response:**
Same as JSON trigger endpoint above.

**Use Cases:**

- Workflows that process uploaded documents (PDF, CSV, images)
- File-based data ingestion pipelines
- Document analysis and extraction workflows
- OCR and document classification

**Behaviour:**

- Processes uploaded file into base64-encoded data structure
- File data is passed to FILE_READ nodes in the workflow
- Validates that either message OR file is provided (not both)
- Maximum file size determined by FastAPI configuration
- File metadata (name, type, size, extension) included in execution

**Validation:**

- Workflow must exist and be published
- Either `Message` OR `file` must be provided (mutually exclusive)
- File must not be empty
- File extension must be valid for FILE_READ node

**Errors:**

- `400 Bad Request` - Both message and file provided, or neither provided
- `400 Bad Request` - File processing failed
- `403 Forbidden` - Workflow not published
- `401 Unauthorized` - Invalid authentication token

**Example:**

```bash
# Upload PDF for processing (using UUID)
curl -X POST "http://localhost:8000/api/http-execution/trigger-form/7c8f3a21-45b6-4d2e-9f1a-8b3c4e5f6a7d?token=na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo" \
  -F "file=@invoice_may_2024.pdf" \
  -F "async_mode=false"

# Upload CSV with custom slug
curl -X POST "http://localhost:8000/api/http-execution/trigger-form/data-import-v2?token=na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo" \
  -F "Message=Import Q2 sales data" \
  -F "file=@sales_q2.csv"
```

**File Data Structure:**

```python
{
  "file_info": {
    "base64": "JVBERi0xLjcKCjEgMCBvYmoKPDwvVHlwZS9DYXRhbG9n...",
    "extension": ".pdf",
    "name": "invoice_may_2024.pdf",
    "type": "application/pdf",
    "size": 45678
  }
}
```

---

#### `POST /api/http-execution/trigger-sse/{workflow_identifier}`

Trigger workflow execution with real-time Server-Sent Events streaming.

**Authentication:** Required if workflow requires authentication (Personal Access Token)

**Path Parameters:**

- `workflow_identifier` - Workflow UUID or custom slug of the published workflow

**Query Parameters:**

- `token` - Personal Access Token (PAT) with `na_` prefix (required if workflow requires authentication)

**Request Body:**

```json
{
  "message": "Analyse market trends for Q4 2024"
}
```

**Response:**
Streaming response with `Content-Type: text/event-stream`

**SSE Events:**

The endpoint streams multiple event types as the workflow executes:

```
data: {"event": "acknowledged", "message": "Request received", "graph": "market-analysis"}

data: {"event": "started", "execution_id": "exec_20251021_150000_market-analysis"}

data: {"event": "node_executing", "node": "Data Collection Agent", "status": "running"}

data: {"event": "node_executing", "node": "Analysis Agent", "status": "running"}

data: {"event": "completed", "execution_id": "exec_20251021_150000_market-analysis", "output": {"trends": ["AI adoption increasing", "Cloud migration accelerating"], "confidence": 0.87}}

data: {"event": "done"}
```

**Event Types:**

- `acknowledged` - Request received and validated
- `started` - Execution started (includes execution_id)
- `node_executing` - Node is being executed (includes node name)
- `completed` - Execution completed successfully (includes output)
- `failed` - Execution failed (includes error message)
- `error` - Error occurred during streaming
- `done` - Stream complete (final event)

**Use Cases:**

- Real-time progress tracking in external UIs
- Live status dashboards
- Long-running workflow monitoring
- Streaming results to end users

**Behaviour:**

- Maintains persistent HTTP connection
- Sends events as workflow progresses
- Polls execution status every 0.5 seconds (configurable)
- Automatically broadcasts to WebSocket listeners
- Closes connection after completion or error
- Client receives immediate feedback on security failures

**Integration Example (JavaScript):**

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/http-execution/trigger-sse/market-analysis?token=abc123',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'Analyse Q4 trends' })
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.event) {
    case 'started':
      console.log('Execution started:', data.execution_id);
      break;
    case 'node_executing':
      console.log('Executing node:', data.node);
      break;
    case 'completed':
      console.log('Results:', data.output);
      eventSource.close();
      break;
    case 'failed':
      console.error('Execution failed:', data.error);
      eventSource.close();
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

**Integration Example (Python):**

```python
import requests
import json

url = 'http://localhost:8000/api/http-execution/trigger-sse/market-analysis?token=abc123'
payload = {'message': 'Analyse Q4 trends'}

with requests.post(url, json=payload, stream=True) as response:
    for line in response.iter_lines():
        if line:
            # SSE format: "data: {...}"
            if line.startswith(b'data: '):
                data = json.loads(line[6:])
                event_type = data.get('event')

                if event_type == 'started':
                    print(f"Started: {data['execution_id']}")
                elif event_type == 'node_executing':
                    print(f"Executing: {data['node']}")
                elif event_type == 'completed':
                    print(f"Results: {data['output']}")
                    break
                elif event_type == 'failed':
                    print(f"Failed: {data['error']}")
                    break
```

**Errors:**

- Errors are sent as SSE events rather than HTTP error responses
- Authentication/security errors sent as `error` event, then stream closes
- Execution failures sent as `failed` event with error details

**Example:**

```bash
# Stream execution progress with UUID (use -N to disable buffering)
curl -N -X POST "http://localhost:8000/api/http-execution/trigger-sse/3f7a9b2c-6d4e-4a8b-9c1d-5e6f7a8b9c0d?token=na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyse Q4 2024 trends"}'
```

---

### Checkpoint Management (1 endpoint)

#### `POST /api/http-execution/resume/{graph_name}`

Resume a paused HTTP execution from a checkpoint.

**Authentication:** None (checkpoint state validates the resume)

**Path Parameters:**

- `graph_name` - Name of the workflow to resume

**Request Body:**

```json
{
  "thread_id": "exec_20251021_143052_approval-workflow",
  "checkpoint_id": "1ef9c8f0-8f2a-6b4c-8001-e4c9c8f08f2a",
  "user_input": "Approved - proceed with $5,000 budget allocation",
  "async_mode": false,
  "timeout": 300
}
```

**Response (Execution Completes):**

```json
{
  "success": true,
  "execution_id": "exec_20251021_143052_approval-workflow",
  "status": "completed",
  "output": {
    "approval_status": "approved",
    "approved_amount": 5000,
    "approver": "Manager",
    "timestamp": "2025-10-21T14:35:20Z"
  }
}
```

**Response (Another Checkpoint):**

```json
{
  "success": true,
  "execution_id": "exec_20251021_143052_approval-workflow",
  "status": "paused",
  "checkpoint_data": {
    "status": "paused",
    "execution_id": "exec_20251021_143052_approval-workflow",
    "thread_id": "exec_20251021_143052_approval-workflow",
    "checkpoint_id": "2ab9d8e1-9e3b-7c5d-9012-f5d9d8e19e3b",
    "checkpoint_node": "Director Approval",
    "checkpoint_input": "Manager approved $5,000. Requires director approval for amounts over $3,000.",
    "resume_endpoint": "/api/http-execution/resume/approval-workflow",
    "resume_instructions": "POST to resume_endpoint with thread_id, checkpoint_id, and user_input"
  }
}
```

**Use Cases:**

- Human-in-the-loop workflows requiring approval
- Multi-stage review processes
- Data validation workflows with human verification
- Interactive troubleshooting workflows

**Behaviour:**

- Validates checkpoint state exists for the given thread_id
- Verifies graph_name matches stored checkpoint state
- Resumes execution from the paused checkpoint node
- Provides user input to the workflow as `{"value": user_input}`
- Can pause again at subsequent checkpoint nodes
- Deletes checkpoint state after final completion
- Updates checkpoint state if another checkpoint is hit

**Validation:**

- `thread_id` must exist in checkpoint storage
- `graph_name` must match the checkpoint's graph
- `checkpoint_id` must be valid
- `user_input` is required (can be any type: string, object, array)

**Errors:**

- `404 Not Found` - No paused execution found for thread_id
- `404 Not Found` - Graph name mismatch
- `500 Internal Server Error` - Resume failed

**Complete Checkpoint Workflow Example:**

```bash
# Step 1: Trigger workflow that has CHECKPOINT node
curl -X POST "http://localhost:8000/api/http-execution/trigger/approval-workflow?token=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Budget request for $5,000 marketing campaign",
    "async_mode": false
  }'

# Response includes checkpoint data
{
  "success": true,
  "execution_id": "exec_20251021_143052_approval-workflow",
  "status": "paused",
  "checkpoint_data": {
    "thread_id": "exec_20251021_143052_approval-workflow",
    "checkpoint_id": "1ef9c8f0-8f2a-6b4c-8001-e4c9c8f08f2a",
    "checkpoint_node": "Manager Approval",
    "checkpoint_input": "Budget request: $5,000 for new marketing campaign",
    "resume_endpoint": "/api/http-execution/resume/approval-workflow"
  }
}

# Step 2: Resume with user input
curl -X POST "http://localhost:8000/api/http-execution/resume/approval-workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "exec_20251021_143052_approval-workflow",
    "checkpoint_id": "1ef9c8f0-8f2a-6b4c-8001-e4c9c8f08f2a",
    "user_input": "Approved",
    "async_mode": false
  }'

# Response - execution completes
{
  "success": true,
  "execution_id": "exec_20251021_143052_approval-workflow",
  "status": "completed",
  "output": {
    "approval_status": "approved",
    "budget_allocated": 5000
  }
}
```

---

### Token Management (3 endpoints)

#### `POST /api/http-execution/token/{graph_name}`

Generate or retrieve a legacy authentication token for a workflow.

**Authentication:** None (requires OAuth2-Proxy user auth in production)

**Path Parameters:**

- `graph_name` - Name of the workflow

**Response:**

```json
{
  "token": "v8dJK3mP9sL2nR6tQ4wY7uX1cZ5bN0fH8gM2pS6vT4",
  "graph_name": "customer-support",
  "created_at": "2025-10-21T14:30:00.123456"
}
```

**Use Cases:**

- Generating tokens for workflows not using WorkflowPublishingService
- Legacy system integration
- Quick token generation for testing

**Behaviour:**

- Validates workflow exists (checks in memory, then loads from disk)
- Generates cryptographically secure random token (32-byte URL-safe)
- Stores token in in-memory dictionary (not persisted to database)
- If token already exists, returns existing token
- Tokens don't expire in legacy system

**Important:** This is a legacy system. New workflows should use the WorkflowPublishingService token system via the
Publishing API, which provides:

- Database persistence (tokens survive restarts)
- Token expiration and rotation
- Fine-grained rate limiting
- Access logging and audit trails

**Errors:**

- `404 Not Found` - Workflow not found
- `500 Internal Server Error` - Token generation failed

**Example:**

```bash
curl -X POST "http://localhost:8000/api/http-execution/token/customer-support"

# Response
{
  "token": "v8dJK3mP9sL2nR6tQ4wY7uX1cZ5bN0fH8gM2pS6vT4",
  "graph_name": "customer-support",
  "created_at": "2025-10-21T14:30:00.123456"
}
```

---

#### `GET /api/http-execution/token/{graph_name}`

Get existing legacy authentication token for a workflow.

**Authentication:** None (requires OAuth2-Proxy user auth in production)

**Path Parameters:**

- `graph_name` - Name of the workflow

**Response:**

```json
{
  "token": "v8dJK3mP9sL2nR6tQ4wY7uX1cZ5bN0fH8gM2pS6vT4",
  "graph_name": "customer-support",
  "created_at": "2025-10-21T14:30:00.123456"
}
```

**Use Cases:**

- Retrieving existing token after restart (if persisted externally)
- Checking if token exists before generating new one
- Displaying token in admin UI

**Errors:**

- `404 Not Found` - No token found for workflow

**Example:**

```bash
curl "http://localhost:8000/api/http-execution/token/customer-support"
```

---

#### `DELETE /api/http-execution/token/{graph_name}`

Revoke (delete) legacy authentication token for a workflow.

**Authentication:** None (requires OAuth2-Proxy user auth in production)

**Path Parameters:**

- `graph_name` - Name of the workflow

**Response:**

```json
{
  "success": true,
  "message": "Token revoked for graph 'customer-support'"
}
```

**Use Cases:**

- Rotating tokens for security
- Disabling HTTP access to a workflow
- Token compromise response

**Behaviour:**

- Removes token from in-memory storage
- All subsequent requests with the old token will fail with 401
- Workflow can still be accessed by generating a new token

**Errors:**

- `404 Not Found` - No token found for workflow

**Example:**

```bash
curl -X DELETE "http://localhost:8000/api/http-execution/token/customer-support"

# Response
{
  "success": true,
  "message": "Token revoked for graph 'customer-support'"
}
```

---

### Execution Information (2 endpoints)

#### `GET /api/http-execution/latest-execution/{graph_name}`

Get the latest HTTP-triggered execution for a workflow.

**Authentication:** None

**Path Parameters:**

- `graph_name` - Name of the workflow

**Response:**

```json
{
  "success": true,
  "has_active_execution": true,
  "execution_id": "exec_20251021_143052_customer-support",
  "status": "completed",
  "start_time": "2025-10-21T14:30:52.123456",
  "db_execution_id": 1247
}
```

**Response (No Execution):**

```json
{
  "success": true,
  "has_active_execution": false,
  "execution_id": null,
  "status": null,
  "start_time": null,
  "db_execution_id": null
}
```

**Use Cases:**

- Checking if workflow is currently running
- Monitoring latest execution status
- Debugging recent execution issues
- Building status dashboards

**Behaviour:**

- Returns the most recent HTTP-triggered execution from in-memory tracking
- Only tracks executions started via HTTP endpoints (not UI executions)
- Execution must have `source: "http"` or `source: "http-sse"`
- Does not query database, only in-memory state

**Example:**

```bash
curl "http://localhost:8000/api/http-execution/latest-execution/customer-support"
```

---

#### `GET /api/http-execution/info/{graph_name}`

Get HTTP execution information and example curl commands for a workflow.

**Authentication:** None

**Path Parameters:**

- `graph_name` - Name of the workflow

**Response:**

```json
{
  "success": true,
  "graph_name": "customer-support",
  "endpoint": "http://localhost:8000/api/http-execution/trigger/customer-support",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body_format": {
    "message": "string"
  },
  "has_token": true,
  "token": "v8dJK3mP9sL2nR6tQ4wY7uX1cZ5bN0fH8gM2pS6vT4",
  "example_curl": "curl -X POST \"http://localhost:8000/api/http-execution/trigger/customer-support?token=v8dJK3mP9sL2nR6tQ4wY7uX1cZ5bN0fH8gM2pS6vT4\" \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\"message\": \"Your message here\"}' ",
  "example_body": {
    "message": "Your message here"
  }
}
```

**Use Cases:**

- Generating documentation for workflows
- Providing integration instructions to external teams
- Quick copy-paste curl commands for testing
- Discovering endpoint URLs dynamically

**Behaviour:**

- Validates workflow exists (loads from disk if needed)
- Checks for existing legacy token
- Derives base URL from the request headers (handles proxies)
- Generates ready-to-use curl command
- URL-decodes graph name for display

**Errors:**

- `404 Not Found` - Workflow not found
- `500 Internal Server Error` - Failed to generate info

**Example:**

```bash
curl "http://localhost:8000/api/http-execution/info/customer-support"
```

## Error Handling

### Error Response Format

All error responses follow a consistent structure:

```json
{
  "detail": "Workflow 'my-workflow' is not published. Only published workflows can be executed via HTTP."
}
```

For rate limit errors, additional headers are included:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Reset: 1698768000

{
  "detail": "Rate limit exceeded for requests. Try again in 60 seconds."
}
```

### Common Error Codes

**400 Bad Request**

- `InvalidInputException` - Neither message nor file provided
- `InvalidInputException` - Both message and file provided (mutually exclusive)
- `FileProcessingException` - File upload processing failed

**401 Unauthorized**

- `AuthenticationRequiredException` - Workflow requires authentication token but none provided
- `InvalidAuthenticationTokenException` - Token is invalid, expired, or doesn't match workflow

**403 Forbidden**

- `WorkflowNotPublishedException` - Workflow is not published for HTTP execution

**404 Not Found**

- `WorkflowNotFoundException` - Workflow doesn't exist
- `CheckpointNotFoundException` - No paused execution found for thread_id
- Token not found for workflow (token endpoints)

**408 Request Timeout**

- `ExecutionTimeoutException` - Execution exceeded configured timeout in sync mode

**429 Too Many Requests**

- `RateLimitExceededException` - Client exceeded rate limit for requests or tokens

**500 Internal Server Error**

- `ExecutionFailedException` - Workflow execution failed with internal error
- `HttpExecutionException` - Generic execution error
- Unexpected server errors

### Error Handling Example

**Python Client with Error Handling:**

```python
import requests
import time

def execute_workflow_with_retry(workflow_name, message, token, max_retries=3):
    """Execute workflow with automatic retry on rate limits."""
    url = f"http://localhost:8000/api/http-execution/trigger/{workflow_name}"
    params = {"token": token} if token else {}
    payload = {"message": message, "async_mode": False, "timeout": 300}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, params=params, json=payload)

            # Success
            if response.status_code == 200:
                return response.json()

            # Rate limit - wait and retry
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited. Retrying in {retry_after}s...")
                time.sleep(retry_after)
                continue

            # Authentication error - don't retry
            elif response.status_code in [401, 403]:
                print(f"Authentication error: {response.json()['detail']}")
                return None

            # Not found - don't retry
            elif response.status_code == 404:
                print(f"Workflow not found: {response.json()['detail']}")
                return None

            # Timeout - could retry with longer timeout
            elif response.status_code == 408:
                print(f"Execution timeout: {response.json()['detail']}")
                payload["timeout"] = payload["timeout"] * 2  # Double timeout
                continue

            # Server error - retry
            elif response.status_code == 500:
                print(f"Server error: {response.json()['detail']}")
                time.sleep(5)
                continue

            # Other errors
            else:
                print(f"Error {response.status_code}: {response.json()['detail']}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None

    print("Max retries exceeded")
    return None

# Usage
result = execute_workflow_with_retry(
    workflow_name="customer-support",
    message="Help with order #12345",
    token="abc123xyz"
)

if result:
    print(f"Execution completed: {result['output']}")
```

**JavaScript Client with Error Handling:**

```javascript
async function executeWorkflow(workflowName, message, token) {
  const url = `http://localhost:8000/api/http-execution/trigger/${workflowName}${token ? '?token=' + token : ''}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        async_mode: false,
        timeout: 300
      })
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle specific error codes
      switch (response.status) {
        case 401:
        case 403:
          throw new Error(`Authentication failed: ${data.detail}`);
        case 404:
          throw new Error(`Workflow not found: ${data.detail}`);
        case 408:
          throw new Error(`Execution timeout: ${data.detail}`);
        case 429:
          const retryAfter = response.headers.get('Retry-After');
          throw new Error(`Rate limited. Retry after ${retryAfter}s`);
        case 500:
          throw new Error(`Execution failed: ${data.detail}`);
        default:
          throw new Error(`Error ${response.status}: ${data.detail}`);
      }
    }

    return data;

  } catch (error) {
    console.error('Workflow execution error:', error);
    throw error;
  }
}

// Usage with async/await
try {
  const result = await executeWorkflow(
    'customer-support',
    'Help with refund request',
    'abc123xyz'
  );
  console.log('Execution result:', result.output);
} catch (error) {
  console.error('Failed:', error.message);
}
```

## Integration with Services Layer

### Dependency Flow

```
Route Handler (routes.py)
    ↓
┌──────────────────────────────────────────────────┐
│  Security Layer (authentication.py)              │
│  ↓                                                │
│  1. validate_workflow_published()                │
│     └→ WorkflowPublishingService                 │
│  2. validate_authentication()                    │
│     └→ WorkflowPublishingService (new tokens)    │
│     └→ TokenManager (legacy tokens)              │
│  3. check_rate_limits()                          │
│     └→ RateLimitingService                       │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│  Handler Layer (handlers/*.py)                   │
│  ↓                                                │
│  HttpExecutionHandler.trigger_execution()        │
│  ├→ Load workflow (GraphManager)                 │
│  ├→ Generate execution ID                        │
│  ├→ Broadcast to WebSocket (optional)            │
│  ├→ Submit to thread pool (ExecutionManager)     │
│  └→ Poll for completion (sync mode)              │
│      └→ Extract output (output.py)               │
│          └→ ExecutionHistoryService              │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│  Service Layer                                   │
│  ↓                                                │
│  ExecutionEngine.execute()                       │
│  └→ LangGraph execution                          │
│      └→ ExecutionHistoryService (save results)   │
│          └→ Database (PostgreSQL)                │
└──────────────────────────────────────────────────┘
```

### Example Integration

**Complete Request Flow:**

```python
# routes.py - Route Handler
@router.post("/trigger/{graph_name}")
async def trigger_http_execution_json(
    graph_name: str,
    execution_request: HttpExecutionRequest,
    request: Request,
    token: Optional[str] = None,
) -> HttpExecutionResponse:
    try:
        return await http_execution_handler.trigger_execution(
            graph_name=graph_name,
            message=execution_request.message,
            token=token,
            async_mode=execution_request.async_mode,
            timeout=execution_request.timeout,
            fastapi_request=request,
        )
    except HttpExecutionException as e:
        raise _handle_http_execution_exception(e)
```

```python
# handlers/execution.py - Business Logic Handler
class HttpExecutionHandler:
    @staticmethod
    async def trigger_execution(
        graph_name: str,
        message: Optional[str] = None,
        token: Optional[str] = None,
        async_mode: bool = False,
        timeout: int = 300,
        fastapi_request: Optional[Request] = None,
    ) -> HttpExecutionResponse:
        # 1. Security checks
        published_workflow, _ = http_auth_service.perform_full_security_check(
            graph_name, token, client_ip
        )

        # 2. Load workflow
        graph = get_graph_manager().get_graph(graph_name)

        # 3. Generate execution ID
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{graph_name}"

        # 4. Pre-register execution
        get_execution_engine().active_executions[execution_id] = {
            "execution_id": execution_id,
            "status": "pending",
            "graph_name": graph_name,
            "source": "http"
        }

        # 5. Broadcast to WebSocket
        await ws_manager.broadcast_http_execution_start(
            execution_id=execution_id,
            graph_name=graph_name,
            input_data={"message": message}
        )

        # 6. Execute in thread pool
        execution_manager.submit_execution(graph, {"message": message}, execution_id)

        # 7. Wait for completion (sync mode) or return immediately (async mode)
        if async_mode:
            return HttpExecutionResponse(
                success=True,
                execution_id=execution_id,
                status="running",
                status_endpoint=f"/api/graph/execution/{execution_id}/status"
            )
        else:
            # Poll for completion
            result = await _wait_for_completion(execution_id, timeout)
            return result
```

```python
# services/authentication.py - Security Service
class HttpAuthService:
    @staticmethod
    def perform_full_security_check(
        graph_name: str,
        token: Optional[str],
        client_ip: Optional[str]
    ) -> Tuple[Any, Optional[ClientContext]]:
        # 1. Validate workflow is published
        published_workflow = WorkflowPublishingService.get_published_workflow(graph_name)
        if not published_workflow:
            raise WorkflowNotPublishedException(graph_name)

        # 2. Validate authentication
        if published_workflow.require_authentication:
            if not token:
                raise AuthenticationRequiredException(graph_name)

            validated = WorkflowPublishingService.validate_token(token, graph_name)
            if not validated:
                raise InvalidAuthenticationTokenException()

        # 3. Check rate limits
        client_id = rate_limiting_service.get_client_identifier(client_ip, token)
        is_allowed, rate_info = rate_limiting_service.check_rate_limit(
            workflow_name=graph_name,
            client_identifier=client_id,
            rate_limit_config=published_workflow.rate_limit
        )

        if not is_allowed:
            raise RateLimitExceededException(
                limit_type=rate_info["limit_type_hit"],
                retry_after=rate_info["retry_after"]
            )

        return published_workflow, client_context
```

### Services Used

**WorkflowPublishingService** (`backend/services/workflow/publishing.py`)

- Manages workflow publishing state
- Provides token generation and validation
- Logs access attempts for audit
- Stores rate limit configurations

**ExecutionEngine** (`backend/services/execution/engine.py`)

- Executes LangGraph workflows
- Manages active execution state
- Provides checkpoint pause/resume
- Tracks execution progress

**ExecutionHistoryService** (`backend/services/execution/history.py`)

- Persists execution records to database
- Stores node execution details
- Provides execution result queries
- Archives execution history

**GraphManager** (`backend/services/graph/manager.py`)

- Loads workflows from storage
- Manages in-memory graph cache
- Provides graph compilation
- Handles graph persistence

**RateLimitingService** (`backend/services/rate_limiting.py`)

- Enforces request rate limits
- Tracks client quotas (IP or token-based)
- Provides sliding window rate limiting
- Returns retry-after timings

**ExecutionManager** (`backend/api/graph/services/execution_manager.py`)

- Manages thread pool for executions
- Submits execution jobs
- Tracks execution futures
- Handles execution cancellation

**WebSocketManager** (`backend/services/websocket.py`)

- Broadcasts execution events to UI
- Manages WebSocket connections
- Provides real-time updates
- Handles connection lifecycle

**TokenManager** (`backend/api/http_execution/services/token_manager.py`)

- Legacy token storage and validation
- In-memory token management
- Backward compatibility support
- Simple CRUD operations

## Usage Examples

### Complete HTTP Execution Workflow

**Scenario:** External CRM triggers customer support workflow when ticket is created

```python
import requests
import json

# 1. Workflow is already published via UI or Publishing API
# (Assume "customer-support" workflow is published with token authentication)

# 2. Execute workflow synchronously
def handle_new_ticket(ticket_id, customer_message):
    """Trigger AgenticStudio workflow when new support ticket is created."""

    url = "http://agenticstudio.example.com/api/http-execution/trigger/customer-support"
    token = "abc123xyz456"  # Stored securely in environment variable

    payload = {
        "message": f"Ticket #{ticket_id}: {customer_message}",
        "async_mode": False,  # Wait for result
        "timeout": 300  # 5 minutes max
    }

    try:
        response = requests.post(
            url,
            params={"token": token},
            json=payload,
            timeout=305  # Slightly longer than workflow timeout
        )

        response.raise_for_status()
        result = response.json()

        if result["status"] == "completed":
            # Extract AI-generated response
            output = result["output"]

            # Update ticket in CRM
            update_ticket(
                ticket_id=ticket_id,
                category=output.get("category"),
                priority=output.get("priority"),
                suggested_response=output.get("suggested_response")
            )

            return {
                "success": True,
                "execution_id": result["execution_id"],
                "category": output.get("category"),
                "priority": output.get("priority")
            }

        elif result["status"] == "paused":
            # Workflow hit a checkpoint (human approval needed)
            checkpoint_data = result["checkpoint_data"]

            # Store checkpoint data for later resume
            store_checkpoint(
                ticket_id=ticket_id,
                thread_id=checkpoint_data["thread_id"],
                checkpoint_id=checkpoint_data["checkpoint_id"]
            )

            # Notify human reviewer
            notify_reviewer(ticket_id, checkpoint_data["checkpoint_input"])

            return {
                "success": True,
                "status": "awaiting_approval",
                "thread_id": checkpoint_data["thread_id"]
            }

    except requests.exceptions.Timeout:
        print(f"Workflow execution timeout for ticket {ticket_id}")
        return {"success": False, "error": "timeout"}

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited
            retry_after = e.response.headers.get('Retry-After', 60)
            print(f"Rate limited. Retry after {retry_after}s")
            return {"success": False, "error": "rate_limited", "retry_after": retry_after}
        else:
            print(f"HTTP error: {e.response.status_code} - {e.response.json()}")
            return {"success": False, "error": str(e)}

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"success": False, "error": str(e)}

# 3. Resume checkpoint after human approval
def handle_approval(ticket_id, approved):
    """Resume workflow after human reviews checkpoint."""

    # Retrieve stored checkpoint data
    checkpoint = get_checkpoint(ticket_id)

    url = "http://agenticstudio.example.com/api/http-execution/resume/customer-support"

    payload = {
        "thread_id": checkpoint["thread_id"],
        "checkpoint_id": checkpoint["checkpoint_id"],
        "user_input": "Approved" if approved else "Rejected",
        "async_mode": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        if result["status"] == "completed":
            # Final result after approval
            output = result["output"]

            # Update ticket with final response
            update_ticket(ticket_id, final_response=output.get("final_response"))

            return {"success": True, "output": output}

    except Exception as e:
        print(f"Resume error: {e}")
        return {"success": False, "error": str(e)}

# Example usage
ticket_result = handle_new_ticket(
    ticket_id=12345,
    customer_message="I need help with my order. It hasn't arrived yet."
)

if ticket_result["success"] and ticket_result.get("status") == "awaiting_approval":
    # Later, when human approves
    approval_result = handle_approval(ticket_id=12345, approved=True)
```

### Real-Time Streaming with SSE

**Scenario:** Live dashboard showing workflow execution progress

```javascript
// Frontend dashboard component
class WorkflowDashboard {
  constructor(workflowName, token) {
    this.workflowName = workflowName;
    this.token = token;
    this.eventSource = null;
  }

  async executeWithProgress(message, onProgress) {
    const url = `https://agenticstudio.example.com/api/http-execution/trigger-sse/${this.workflowName}?token=${this.token}`;

    // SSE doesn't support POST directly, use fetch to initiate
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    // Read SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const eventData = JSON.parse(line.substring(6));
            this.handleEvent(eventData, onProgress);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  handleEvent(eventData, onProgress) {
    const { event, execution_id, node, output, error } = eventData;

    switch (event) {
      case 'acknowledged':
        onProgress({
          status: 'acknowledged',
          message: 'Request received'
        });
        break;

      case 'started':
        onProgress({
          status: 'started',
          execution_id,
          message: 'Execution started'
        });
        break;

      case 'node_executing':
        onProgress({
          status: 'executing',
          node,
          message: `Executing: ${node}`
        });
        break;

      case 'completed':
        onProgress({
          status: 'completed',
          execution_id,
          output,
          message: 'Execution completed'
        });
        break;

      case 'failed':
        onProgress({
          status: 'failed',
          execution_id,
          error,
          message: `Execution failed: ${error}`
        });
        break;

      case 'done':
        onProgress({
          status: 'done',
          message: 'Stream closed'
        });
        break;
    }
  }
}

// Usage in React component
function WorkflowExecutor() {
  const [progress, setProgress] = useState([]);
  const [executing, setExecuting] = useState(false);

  const executeWorkflow = async (message) => {
    setExecuting(true);
    setProgress([]);

    const dashboard = new WorkflowDashboard('market-analysis', 'abc123xyz');

    try {
      await dashboard.executeWithProgress(message, (update) => {
        setProgress(prev => [...prev, {
          timestamp: new Date().toISOString(),
          ...update
        }]);

        if (update.status === 'completed') {
          console.log('Final output:', update.output);
          setExecuting(false);
        } else if (update.status === 'failed') {
          console.error('Execution failed:', update.error);
          setExecuting(false);
        }
      });
    } catch (error) {
      console.error('Stream error:', error);
      setExecuting(false);
    }
  };

  return (
    <div>
      <button
        onClick={() => executeWorkflow('Analyse Q4 2024 market trends')}
        disabled={executing}
      >
        {executing ? 'Executing...' : 'Execute Workflow'}
      </button>

      <div className="progress-log">
        {progress.map((item, idx) => (
          <div key={idx} className={`log-item ${item.status}`}>
            <span className="timestamp">{item.timestamp}</span>
            <span className="message">{item.message}</span>
            {item.node && <span className="node">{item.node}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### File Upload Processing

**Scenario:** Process uploaded invoices for data extraction

```python
import requests
from pathlib import Path

def process_invoice_file(invoice_path: str, token: str) -> dict:
    """Upload invoice and trigger extraction workflow."""

    url = "http://agenticstudio.example.com/api/http-execution/trigger-form/invoice-processor"

    # Read file
    file_path = Path(invoice_path)

    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path.name, f, 'application/pdf')
        }
        data = {
            'async_mode': 'false',
            'timeout': '300'
        }
        params = {
            'token': token
        }

        response = requests.post(
            url,
            params=params,
            files=files,
            data=data
        )

    response.raise_for_status()
    result = response.json()

    if result['status'] == 'completed':
        # Extract invoice data
        output = result['output']

        invoice_data = {
            'invoice_number': output.get('invoice_number'),
            'date': output.get('invoice_date'),
            'vendor': output.get('vendor_name'),
            'total_amount': output.get('total_amount'),
            'line_items': output.get('line_items', []),
            'execution_id': result['execution_id']
        }

        return invoice_data
    else:
        raise Exception(f"Execution failed: {result.get('message')}")

# Batch process multiple invoices
def batch_process_invoices(invoice_directory: str, token: str):
    """Process all PDF invoices in a directory."""

    results = []
    invoice_dir = Path(invoice_directory)

    for invoice_file in invoice_dir.glob('*.pdf'):
        try:
            print(f"Processing {invoice_file.name}...")
            data = process_invoice_file(str(invoice_file), token)
            results.append({
                'filename': invoice_file.name,
                'success': True,
                'data': data
            })
            print(f"✓ Extracted: Invoice #{data['invoice_number']}, ${data['total_amount']}")

        except Exception as e:
            print(f"✗ Failed to process {invoice_file.name}: {e}")
            results.append({
                'filename': invoice_file.name,
                'success': False,
                'error': str(e)
            })

    return results

# Usage
results = batch_process_invoices(
    invoice_directory='./invoices/pending',
    token='abc123xyz456'
)

# Summary
successful = sum(1 for r in results if r['success'])
failed = len(results) - successful
print(f"\nProcessed {len(results)} invoices: {successful} successful, {failed} failed")
```

### Webhook Integration

**Scenario:** GitHub webhook triggers deployment workflow

```python
from fastapi import FastAPI, Request, HTTPException
import requests
import hmac
import hashlib

app = FastAPI()

AGENTICSTUDIO_URL = "http://agenticstudio.example.com"
AGENTICSTUDIO_TOKEN = "abc123xyz456"
GITHUB_WEBHOOK_SECRET = "your-webhook-secret"

def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature:
        return False

    expected = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)

@app.post("/webhooks/github/push")
async def handle_github_push(request: Request):
    """Handle GitHub push events and trigger AgenticStudio deployment workflow."""

    # Verify webhook signature
    body = await request.body()
    signature = request.headers.get('X-Hub-Signature-256')

    if not verify_github_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse webhook payload
    payload = await request.json()

    # Extract deployment info
    repo = payload.get('repository', {}).get('full_name')
    branch = payload.get('ref', '').replace('refs/heads/', '')
    commits = payload.get('commits', [])
    pusher = payload.get('pusher', {}).get('name')

    # Only deploy on main branch
    if branch != 'main':
        return {"message": f"Ignoring push to {branch}"}

    # Prepare deployment message
    commit_messages = '\n'.join([
        f"- {c['message']} ({c['id'][:7]})"
        for c in commits[:5]  # Last 5 commits
    ])

    deployment_message = f"""
New deployment requested for {repo}
Branch: {branch}
Pusher: {pusher}
Commits:
{commit_messages}
"""

    # Trigger AgenticStudio deployment workflow
    try:
        agenticstudio_response = requests.post(
            f"{AGENTICSTUDIO_URL}/api/http-execution/trigger/github-deployment",
            params={"token": AGENTICSTUDIO_TOKEN},
            json={
                "message": deployment_message,
                "async_mode": True  # Deploy in background
            },
            timeout=10
        )

        agenticstudio_response.raise_for_status()
        result = agenticstudio_response.json()

        return {
            "message": "Deployment workflow triggered",
            "execution_id": result["execution_id"],
            "status_endpoint": result["status_endpoint"]
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger deployment: {str(e)}"
        )
```

## Performance Considerations

### Endpoint Performance

**Fast (< 1 second):**

- `POST /api/http-execution/trigger/{graph_name}` (async mode) - Returns immediately
- `GET /api/http-execution/token/{graph_name}` - In-memory lookup
- `DELETE /api/http-execution/token/{graph_name}` - In-memory deletion
- `GET /api/http-execution/latest-execution/{graph_name}` - In-memory state check
- `GET /api/http-execution/info/{graph_name}` - Quick metadata generation

**Variable (depends on workflow):**

- `POST /api/http-execution/trigger/{graph_name}` (sync mode) - Waits for workflow completion
- `POST /api/http-execution/trigger-form/{graph_name}` - File upload + workflow execution
- `POST /api/http-execution/trigger-sse/{graph_name}` - Streams until completion
- `POST /api/http-execution/resume/{graph_name}` - Resumes from checkpoint

**Slow (potentially > 1 minute):**

- Complex workflows with multiple LLM calls
- Workflows with external API dependencies
- Large file processing workflows
- Workflows with database queries

### Optimisation Tips

**Use Async Mode for Long-Running Workflows:**

```python
# Bad - Blocks for entire execution
response = requests.post(url, json={
    "message": "Process 1000 records",
    "async_mode": False,
    "timeout": 3600  # 1 hour!
})

# Good - Returns immediately, poll status separately
response = requests.post(url, json={
    "message": "Process 1000 records",
    "async_mode": True
})

execution_id = response.json()["execution_id"]
status_url = response.json()["status_endpoint"]

# Poll status separately with exponential backoff
def poll_status(status_url, max_wait=3600):
    wait_time = 1
    elapsed = 0

    while elapsed < max_wait:
        status = requests.get(status_url).json()

        if status["status"] == "completed":
            return status
        elif status["status"] == "failed":
            raise Exception(status.get("error"))

        time.sleep(wait_time)
        elapsed += wait_time
        wait_time = min(wait_time * 2, 60)  # Max 60s between polls
```

**Use SSE for Real-Time Updates:**

```python
# Bad - Sync mode with long timeout
response = requests.post(url, json={
    "message": "Generate report",
    "async_mode": False,
    "timeout": 600
})
# User waits 10 minutes with no feedback

# Good - SSE streaming with progress updates
import requests

url_sse = f"{base_url}/api/http-execution/trigger-sse/report-generator?token={token}"

with requests.post(url_sse, json={"message": "Generate report"}, stream=True) as response:
    for line in response.iter_lines():
        if line and line.startswith(b'data: '):
            event = json.loads(line[6:])

            if event['event'] == 'node_executing':
                print(f"Progress: {event['node']}")  # Show progress to user
            elif event['event'] == 'completed':
                return event['output']
```

**Batch File Processing:**

```python
# Bad - Upload files one at a time synchronously
for file in files:
    process_file(file)  # Blocks for each file

# Good - Upload files concurrently with async
import asyncio
import aiohttp

async def process_file_async(session, file, token):
    with open(file, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file', f, filename=file.name)
        data.add_field('async_mode', 'true')

        async with session.post(url, params={'token': token}, data=data) as response:
            return await response.json()

async def process_files_batch(files, token):
    async with aiohttp.ClientSession() as session:
        tasks = [process_file_async(session, file, token) for file in files]
        results = await asyncio.gather(*tasks)
        return results

# Process 100 files concurrently
results = asyncio.run(process_files_batch(files, token))
```

**Timeout Configuration:**

```python
# Bad - Fixed timeout for all workflows
timeout = 300  # All workflows get 5 minutes

# Good - Adjust timeout based on workflow complexity
workflow_timeouts = {
    "quick-classification": 30,      # Simple LLM call
    "data-enrichment": 120,          # Multiple API calls
    "report-generation": 600,        # Complex processing
    "batch-processing": 3600         # Large dataset processing
}

timeout = workflow_timeouts.get(workflow_name, 300)

response = requests.post(url, json={
    "message": message,
    "async_mode": False,
    "timeout": timeout
})
```

**Caching Strategies:**

```python
# For workflows with predictable outputs, implement client-side caching

import hashlib
from functools import lru_cache

@lru_cache(maxsize=100)
def execute_workflow_cached(workflow_name, message, token):
    """Cache workflow results for identical inputs."""
    response = requests.post(
        f"{url}/api/http-execution/trigger/{workflow_name}",
        params={"token": token},
        json={"message": message, "async_mode": False}
    )
    return response.json()

# Identical messages return cached results instantly
result1 = execute_workflow_cached("classifier", "Hello world", token)
result2 = execute_workflow_cached("classifier", "Hello world", token)  # Cached!
```

**Rate Limit Awareness:**

```python
# Bad - Hammer the API until rate limited
for item in items:
    execute_workflow(item)  # Gets rate limited quickly

# Good - Respect rate limits with pacing
import time

def execute_with_rate_limiting(items, requests_per_minute=10):
    """Execute workflows with automatic rate limit pacing."""
    delay = 60.0 / requests_per_minute
    results = []

    for item in items:
        start = time.time()

        result = execute_workflow(item)
        results.append(result)

        # Pace requests
        elapsed = time.time() - start
        if elapsed < delay:
            time.sleep(delay - elapsed)

    return results

# Process 100 items at 10 requests/minute
results = execute_with_rate_limiting(items, requests_per_minute=10)
```

## Related Documentation

### API Modules

- [Graph API](../../../backend/api/graph/graph.md) - Workflow management and execution via UI
- [Execution History API](../../../backend/api/execution_history/execution_history.md) - Execution records and logs
- [WebSocket API](../websocket/websocket.md) - Real-time execution updates
- [Publishing API](../workflow/workflow.md) - Workflow publishing and token management

### Architecture Documentation

- [Services Architecture](../architecture/services.md) - Services layer overview
- [Execution Engine](../architecture/execution_engine.md) - LangGraph execution details
- [Rate Limiting](../architecture/rate_limiting.md) - Rate limiting implementation
- [Security](../architecture/security.md) - Authentication and authorisation

### Integration Guides

- [Webhook Integration Guide](../guides/webhooks.md) - Setting up webhooks
- [External API Integration](../guides/external_apis.md) - Integrating with AgenticStudio
- [File Processing Guide](../guides/file_processing.md) - Working with file uploads

## Summary

The HTTP Execution API module provides a robust, production-ready interface for triggering AgenticStudio workflows from
external systems. It bridges the gap between AgenticStudio's powerful AI workflow capabilities and the broader software
ecosystem, enabling seamless integrations with CRMs, ticketing systems, webhooks, and custom applications.

The module's architecture emphasises security through mandatory workflow publishing, flexible authentication via tokens,
and comprehensive rate limiting. The dual execution modes (sync and async) provide flexibility for different use cases,
from quick API calls requiring immediate responses to long-running background jobs. The SSE streaming endpoint offers a
middle ground, providing real-time progress updates for workflows that take minutes to complete.

Checkpoint support enables sophisticated human-in-the-loop workflows, where AI-generated outputs can be reviewed and
approved before proceeding. This makes the module suitable for sensitive operations requiring human oversight, such as
financial approvals, content moderation, or regulatory compliance workflows.

**Key Features:**

- **Multiple Execution Modes**: Sync, async, and SSE streaming
- **Token-Based Authentication**: Secure access control with dual token systems
- **Rate Limiting**: Prevent abuse with configurable request and token limits
- **File Upload Support**: Process documents, images, and data files
- **Checkpoint Pause/Resume**: Human-in-the-loop workflows
- **WebSocket Broadcasting**: Real-time UI updates
- **Comprehensive Error Handling**: Clear error messages with proper HTTP status codes
- **Access Logging**: Complete audit trail of all execution attempts
- **Clean Architecture**: Separation of routing, security, and business logic

**Primary Use Cases:**

- Webhook-triggered workflows (GitHub, Stripe, Slack, etc.)
- CRM integrations (Salesforce, HubSpot)
- Support ticket automation (Zendesk, Intercom)
- Scheduled batch processing (via cron jobs)
- Document processing pipelines
- Real-time data analysis APIs
- Approval and review workflows
- Custom external integrations
