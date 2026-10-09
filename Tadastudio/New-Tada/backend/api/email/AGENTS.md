# Email API Module

## Overview

The Email API module provides REST endpoints for email-based workflow checkpoint management in AgenticStudio. It enables
workflows to pause execution and wait for email responses, creating interactive workflows that can communicate with
external stakeholders via email.

**Location:** [backend/api/email/](../../backend/api/email/)

**Base Path:** `/api/email`

**Primary Responsibilities:**

- Creating temporary email inboxes for receiving checkpoint responses
- Sending emails from checkpoint nodes during workflow execution
- Handling webhook callbacks when emails are received
- Resuming paused workflows with email response data
- Managing webhook registrations for real-time email notifications
- Monitoring email checkpoint status across workflow executions

## Architecture

### Module Structure

```text
backend/api/email/
├── __init__.py              # Module exports (router)
├── routes.py                # API endpoint definitions (335 lines)
├── models.py                # Pydantic request/response models (121 lines)
├── dependencies.py          # FastAPI dependencies (database session)
└── handlers/                # Business logic handlers
    ├── __init__.py          # Handler exports
    ├── webhook.py           # Webhook callback processing (187 lines)
    ├── resumption.py        # Workflow resumption logic (200 lines)
    └── extraction.py        # Email content extraction (116 lines)
```

**File Purposes:**

- **routes.py** - FastAPI route definitions with minimal logic, delegates to handlers
- **models.py** - Request/response Pydantic models for type safety and validation
- **dependencies.py** - Dependency injection for database sessions
- **handlers/webhook.py** - Processes incoming email webhooks from providers (Mailgun)
- **handlers/resumption.py** - Handles resuming paused workflows with email data
- **handlers/extraction.py** - Extracts execution IDs and content from email payloads

### Design Pattern

The Email API follows a **handler-based architecture** with clear separation of concerns:

```
HTTP Request (Email Webhook)
    ↓
Route Handler (routes.py)
    ↓
EmailWebhookHandler (handlers/webhook.py)
    ↓  ↙                    ↘
EmailExtractionHandler    WorkflowResumptionHandler
(Extract content)         (Resume workflow)
    ↓                          ↓
Email Service              Execution Engine
Database                   WebSocket Notifier
```

**Request Flow:**

1. **Webhook Receipt** - Email provider (Mailgun) calls `/api/email/webhooks/callback`
2. **Data Extraction** - EmailExtractionHandler parses webhook payload
3. **Execution Lookup** - Find paused workflow execution and checkpoint node
4. **Content Extraction** - Extract relevant content based on checkpoint config
5. **Database Update** - Mark checkpoint as completed with email response data
6. **Workflow Resume** - WorkflowResumptionHandler resumes workflow execution
7. **Notification** - Send WebSocket notification to connected clients

**Benefits:**

- Thin route handlers focus on HTTP protocol concerns
- Complex webhook logic isolated in specialised handlers
- Services are reusable across different API modules
- Easy to test handlers independently with mocked dependencies
- Background task execution prevents blocking webhook response

## Authentication & Authorisation

### Authentication

The Email API endpoints have **mixed authentication requirements**:

**Authenticated Endpoints:**

- `/api/email/inbox/create` - Requires user authentication
- `/api/email/inbox/{inbox_id}` (DELETE) - Requires user authentication
- `/api/email/send` - Requires user authentication
- `/api/email/webhooks/register` - Requires user authentication
- `/api/email/webhooks/{webhook_id}` (DELETE) - Requires user authentication
- `/api/email/inbox/{inbox_id}/emails` - Requires user authentication
- `/api/email/checkpoint/{execution_id}/status` - Requires user authentication

**Unauthenticated Endpoints:**

- `/api/email/webhooks/callback` - **No authentication** (called by external email providers)

**Authentication Pattern:**

Authentication is handled at the application level via OAuth2-Proxy. The email API routes do not explicitly define
authentication dependencies, relying on global middleware.

```python
# Authentication is applied globally, not per-route
# Routes inherit authentication from app-level middleware
@router.post("/inbox/create")
async def create_email_inbox(request: CreateInboxRequest):
    # User context available via OAuth2-Proxy headers
    pass
```

### Authorisation

**Webhook Security:**

The webhook callback endpoint (`/api/email/webhooks/callback`) is intentionally unauthenticated to allow email providers
to call it. Security is ensured through:

1. **Execution ID Validation** - Must match existing paused workflow
2. **Status Checks** - Only resumes workflows in "paused" status
3. **Database Constraints** - Validates checkpoint node exists and is awaiting email
4. **Graceful Failures** - Returns success for invalid webhooks to prevent retries

**Data Access:**

Workflow executions are user-scoped through the GraphExecution model's user relationship, ensuring users can only
interact with their own workflow checkpoints.

## API Endpoints

### Inbox Management

#### `POST /api/email/inbox/create`

Create a temporary email inbox for receiving checkpoint responses during workflow execution.

**Authentication:** Required

**Request Body:**

```json
{
  "expires_in_minutes": 60,
  "metadata": {
    "workflow_name": "customer_approval",
    "execution_id": "exec_abc123def456"
  }
}
```

**Field Constraints:**

- `expires_in_minutes`: Integer between 1 and 1440 (24 hours)
- `metadata`: Optional key-value pairs for tracking

**Response:**

```json
{
  "inbox_id": "inbox_7f3e9a1b2c4d",
  "email_address": "workflow-exec_abc123def456@mail.agenticstudio.ai",
  "expires_at": "2025-10-21T14:30:00Z",
  "metadata": {
    "workflow_name": "customer_approval",
    "execution_id": "exec_abc123def456"
  }
}
```

**Use Cases:**

- Creating a unique email address for each workflow execution's checkpoint
- Establishing a temporary inbox before pausing workflow for email response
- Setting up email-based approval flows in automated workflows

**Behaviour:**

- Creates inbox via configured email provider (Mailgun or MailSlurp)
- Generates unique email address incorporating execution context
- Sets automatic expiry to clean up temporary inboxes
- Returns immediately with inbox details

**Validation:**

- Expires time must be within allowed range (1-1440 minutes)
- Metadata must be valid JSON object if provided

**Errors:**

- `500 Internal Server Error` - Email provider unavailable or inbox creation failed

---

#### `DELETE /api/email/inbox/{inbox_id}`

Delete a temporary email inbox, typically after workflow completion or timeout.

**Authentication:** Required

**Path Parameters:**

- `inbox_id` - The unique identifier of the inbox to delete (e.g., "inbox_7f3e9a1b2c4d")

**Response:**

```json
{
  "success": true
}
```

**Use Cases:**

- Cleaning up inboxes after workflow completes successfully
- Removing inboxes when checkpoint times out
- Manual cleanup during workflow cancellation

**Behaviour:**

- Deletes inbox from email provider
- Returns success even if inbox doesn't exist (idempotent)
- Does not affect completed workflow executions

**Errors:**

- `500 Internal Server Error` - Email provider communication failure

---

#### `GET /api/email/inbox/{inbox_id}/emails`

Retrieve emails from an inbox for debugging, monitoring, or manual inspection.

**Authentication:** Required

**Path Parameters:**

- `inbox_id` - The inbox identifier

**Query Parameters:**

- `limit` - Maximum number of emails to retrieve (default: 10, max: 100)

**Response:**

```json
{
  "emails": [
    {
      "id": "msg_9k3j2h1g",
      "from": "stakeholder@company.com",
      "to": ["workflow-exec_abc123def456@mail.agenticstudio.ai"],
      "subject": "Re: Approval Required [REF:exec_abc123def456]",
      "body": "Approved. Please proceed with the deployment.",
      "received_at": "2025-10-21T13:45:23Z"
    },
    {
      "id": "msg_8j2i1h0g",
      "from": "manager@company.com",
      "to": ["workflow-exec_abc123def456@mail.agenticstudio.ai"],
      "subject": "Re: Budget Approval [REF:exec_abc123def456]",
      "body": "Budget looks good. Approved for $50,000.",
      "received_at": "2025-10-21T12:30:15Z"
    }
  ]
}
```

**Use Cases:**

- Debugging email reception issues
- Monitoring email checkpoint activity
- Auditing email responses for compliance
- Manual inspection of email content before processing

**Behaviour:**

- Queries email provider's storage for inbox messages
- Returns most recent emails first
- Does not mark emails as read or modify inbox state

**Performance:**

- Fast for recent emails (< 1 second)
- May be slower for inboxes with many emails

**Errors:**

- `404 Not Found` - Inbox does not exist or has expired
- `500 Internal Server Error` - Email provider communication failure

---

### Email Operations

#### `POST /api/email/send`

Send an email from a checkpoint node during workflow execution.

**Authentication:** Required

**Request Body:**

```json
{
  "recipient": "stakeholder@company.com",
  "subject": "Approval Required: Budget Review [REF:exec_abc123def456]",
  "body": "Please review and approve the attached budget proposal. Reply to this email with your decision.",
  "html_body": "<html><body><h2>Budget Approval Request</h2><p>Please review and approve the attached budget proposal.</p><p>Reply to this email with your decision.</p></body></html>",
  "reply_to": "workflow-exec_abc123def456@mail.agenticstudio.ai",
  "inbox_id": "inbox_7f3e9a1b2c4d"
}
```

**Field Details:**

- `recipient` - Email address to send to (required)
- `subject` - Email subject line (required)
- `body` - Plain text email body (required)
- `html_body` - Optional HTML version of email body
- `reply_to` - Optional reply-to address (typically the workflow inbox)
- `inbox_id` - Optional inbox to send from (for MailSlurp provider)

**Response:**

```json
{
  "success": true,
  "result": {
    "id": "msg_send_9k3j2h1g",
    "status": "sent",
    "provider": "mailgun"
  }
}
```

**Use Cases:**

- Sending approval requests from workflow checkpoints
- Notifying stakeholders of workflow state requiring input
- Creating interactive workflows that pause for external feedback
- Implementing email-based human-in-the-loop processes

**Behaviour:**

- Sends email via configured provider (Mailgun or MailSlurp)
- If `inbox_id` provided and provider supports it, sends from that specific inbox
- Otherwise, sends from default address: `noreply@agenticstudio.ai`
- Blocks until email provider confirms send

**Validation:**

- Email addresses validated by provider
- Subject and body cannot be empty

**Errors:**

- `500 Internal Server Error` - Email provider unavailable or send failed
- Provider-specific errors (rate limits, invalid addresses, etc.)

---

### Webhook Management

#### `POST /api/email/webhooks/callback`

Webhook callback endpoint called by email providers when an email is received. This is the core endpoint that enables
email-based workflow resumption.

**Authentication:** None (called by external providers)

**Request Body (Form Data):**

Mailgun sends webhook data as form-encoded data:

```
recipient=workflow-exec_abc123def456@mail.agenticstudio.ai
sender=stakeholder@company.com
from=John Doe <stakeholder@company.com>
subject=Re: Approval Required [REF:exec_abc123def456]
body-plain=Approved. Please proceed with the deployment.
stripped-text=Approved. Please proceed with the deployment.
message-headers=[[\"Content-Type\", \"text/plain\"]]
```

**Response:**

```json
{
  "status": "success",
  "message": "Email received and workflow will resume"
}
```

**Use Cases:**

- Receiving email responses to workflow checkpoint emails
- Automatically resuming paused workflows when stakeholder replies
- Real-time processing of email-based approvals/rejections
- Handling email responses for interactive workflows

**Behaviour:**

1. **Parse Webhook** - Extract email data from Mailgun form payload
2. **Extract Execution ID** - Parse from recipient address (e.g., `workflow-{execution_id}@...`) or subject line
   `[REF:execution_id]`
3. **Find Execution** - Query database for paused GraphExecution matching execution_id
4. **Find Checkpoint** - Locate paused CHECKPOINT node for this execution
5. **Extract Content** - Parse email body based on checkpoint's email_config (full_body, pattern, etc.)
6. **Update Database** - Mark checkpoint as completed, store email response data
7. **Schedule Resume** - Create background task to resume workflow
8. **Return Success** - Respond to webhook immediately (non-blocking)

**Background Resumption Flow:**

The workflow resume happens asynchronously:

```python
# Background task flow:
1. Get execution details from database
2. Update execution status to "running"
3. Get latest checkpoint ID from execution engine
4. Resume workflow with extracted email content as input
5. Send WebSocket notification to connected clients
```

**Email Extraction Modes:**

Configured in checkpoint node's `email_config`:

- `full_body` - Use entire email body as input
- `stripped_text` - Use stripped text (removes quoted replies, signatures)
- `pattern` - Extract using regex pattern from `extraction_pattern` config

**Validation:**

- Execution ID must be present in recipient or subject
- Execution must exist and be in "paused" status
- Checkpoint node must exist and be in "paused" status

**Errors:**

The endpoint is designed to **always return success** to prevent webhook retries:

```json
{
  "status": "error",
  "message": "No execution ID found"
}
```

Even on errors, returns 200 OK. This prevents email providers from repeatedly calling webhook for invalid/expired
executions.

**Security Considerations:**

- No authentication required (webhooks come from external providers)
- Validates execution exists before processing
- Only processes paused executions (prevents replay attacks)
- Graceful failure for invalid webhooks

---

#### `POST /api/email/webhooks/register`

Register a webhook with the email provider to receive notifications when emails arrive at a specific inbox.

**Authentication:** Required

**Request Body:**

```json
{
  "inbox_id": "inbox_7f3e9a1b2c4d",
  "execution_id": "exec_abc123def456",
  "checkpoint_id": "checkpoint_node_approval",
  "webhook_base_url": "https://agenticstudio.mycompany.com"
}
```

**Field Details:**

- `inbox_id` - The inbox to monitor for incoming emails (required)
- `execution_id` - Workflow execution ID for tracking (required)
- `checkpoint_id` - Checkpoint node ID that's waiting for email (required)
- `webhook_base_url` - Optional base URL (defaults to EMAIL_WEBHOOK_BASE_URL env var or <http://localhost:8000>)

**Response:**

```json
{
  "webhook_id": "webhook_4h8j9k2m",
  "inbox_id": "inbox_7f3e9a1b2c4d",
  "webhook_url": "https://agenticstudio.mycompany.com/api/email/webhooks/callback",
  "event_types": ["NEW_EMAIL"]
}
```

**Use Cases:**

- Setting up real-time email notifications for checkpoint inboxes
- Enabling immediate workflow resumption when email received
- Configuring webhook after creating inbox and before sending checkpoint email

**Behaviour:**

- Constructs webhook URL by appending `/api/email/webhooks/callback` to base URL
- Registers webhook with email provider (Mailgun or MailSlurp)
- Configures webhook to trigger on NEW_EMAIL events
- Returns webhook details for tracking

**Typical Workflow:**

1. Create inbox → Get inbox_id
2. Register webhook for that inbox
3. Send email from checkpoint
4. Wait for webhook callback when reply received
5. Workflow resumes automatically

**Validation:**

- Inbox must exist
- Webhook base URL must be valid and publicly accessible

**Errors:**

- `500 Internal Server Error` - Email provider unavailable or registration failed
- Provider may reject invalid webhook URLs (not HTTPS, unreachable, etc.)

---

#### `DELETE /api/email/webhooks/{webhook_id}`

Unregister a webhook from the email provider.

**Authentication:** Required

**Path Parameters:**

- `webhook_id` - The webhook identifier returned from registration

**Response:**

```json
{
  "success": true
}
```

**Use Cases:**

- Cleaning up webhooks after workflow completion
- Removing webhooks when checkpoint times out
- Manual webhook cleanup during workflow cancellation

**Behaviour:**

- Removes webhook registration from email provider
- Returns success even if webhook doesn't exist (idempotent)
- Does not affect active workflow executions

**Errors:**

- `500 Internal Server Error` - Email provider communication failure

---

### Status Monitoring

#### `GET /api/email/checkpoint/{execution_id}/status`

Get the status of email checkpoints for a specific workflow execution.

**Authentication:** Required

**Path Parameters:**

- `execution_id` - The workflow execution ID (websocket_execution_id)

**Response:**

```json
{
  "execution_id": "exec_abc123def456",
  "has_email_checkpoints": true,
  "email_checkpoints": [
    {
      "node_id": "checkpoint_approval",
      "node_name": "Manager Approval",
      "status": "completed",
      "inbox_id": "inbox_7f3e9a1b2c4d",
      "reply_to_address": "workflow-exec_abc123def456@mail.agenticstudio.ai",
      "email_sent": true,
      "email_received": true,
      "start_time": "2025-10-21T13:00:00Z",
      "end_time": "2025-10-21T13:45:23Z"
    },
    {
      "node_id": "checkpoint_budget_approval",
      "node_name": "Finance Approval",
      "status": "paused",
      "inbox_id": "inbox_8g4f0b3e5a6c",
      "reply_to_address": "workflow-exec_abc123def456@mail.agenticstudio.ai",
      "email_sent": true,
      "email_received": false,
      "start_time": "2025-10-21T13:45:30Z",
      "end_time": null
    }
  ]
}
```

**Use Cases:**

- Monitoring progress of multi-checkpoint workflows
- Displaying checkpoint status in UI dashboards
- Debugging workflow pauses and resumptions
- Tracking email delivery and response times

**Behaviour:**

- Queries GraphExecution table for execution by websocket_execution_id
- Finds all NodeExecution records with type "CHECKPOINT" and await_mode "email"
- Extracts metadata including inbox details and email status
- Returns empty list if no email checkpoints exist

**Response Fields:**

- `has_email_checkpoints` - Boolean indicating if any email checkpoints exist
- `email_checkpoints` - Array of checkpoint details:
  - `node_id` - Unique identifier of checkpoint node
  - `node_name` - Display name of checkpoint
  - `status` - Node status: "paused", "completed", "failed"
  - `inbox_id` - Associated inbox identifier
  - `reply_to_address` - Email address for receiving responses
  - `email_sent` - Boolean from node metadata
  - `email_received` - True if status is "completed"
  - `start_time` - When checkpoint started (ISO 8601)
  - `end_time` - When checkpoint completed (ISO 8601, null if ongoing)

**Validation:**

- Execution must exist in database

**Errors:**

- `404 Not Found` - Execution does not exist
- `500 Internal Server Error` - Database query failure

---

## Error Handling

### Error Response Format

All errors follow a consistent structure:

```json
{
  "detail": "Execution not found"
}
```

For more complex errors:

```json
{
  "detail": {
    "error": "EmailProviderError",
    "message": "Failed to create inbox: Mailgun API unavailable",
    "provider": "mailgun"
  }
}
```

### Common Error Codes

#### 400 Bad Request

- Invalid request body format
- Missing required fields
- Field validation failures (e.g., expires_in_minutes out of range)

**Example Scenario:**

```json
{
  "detail": [
    {
      "loc": ["body", "expires_in_minutes"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

#### 404 Not Found

- Execution ID not found in database
- Inbox does not exist or has expired
- Checkpoint node not found for execution

**When This Occurs:**

- Requesting status for non-existent execution
- Deleting already-deleted inbox
- Accessing expired temporary inbox

#### 500 Internal Server Error

- Email provider (Mailgun/MailSlurp) unavailable
- Database connection failure
- Workflow resumption errors
- Webhook processing failures

**Common Causes:**

- Email provider API outage
- Network connectivity issues
- Database deadlocks or timeouts
- Invalid provider credentials in environment variables

### Error Handling Example

**Client-Side Error Handling:**

```python
import httpx

async def create_checkpoint_inbox(expires_minutes: int = 60):
    """Create inbox with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.agenticstudio.com/api/email/inbox/create",
                json={"expires_in_minutes": expires_minutes},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                print(f"Invalid request: {e.response.json()}")
            elif e.response.status_code == 500:
                print("Email service unavailable, retrying...")
                # Implement retry logic
            raise

        except httpx.TimeoutException:
            print("Request timed out")
            raise
```

**Webhook Error Handling:**

Webhooks intentionally return success even on errors to prevent retries:

```python
# In webhook handler
try:
    process_webhook(email_data)
except ExecutionNotFoundError:
    # Return success to prevent webhook retry
    return {"status": "success", "message": "Execution not found, ignoring"}
except Exception as e:
    logger.error(f"Webhook processing failed: {e}")
    # Still return success to provider
    return {"status": "success", "message": "Processed with errors"}
```

---

## Integration with Services Layer

### Dependency Flow

```
API Route (routes.py)
    ↓
Handler (handlers/*.py)
    ↓  ↙                        ↓                    ↘
EmailManager           Database Session      ExecutionEngine
(services/email)       (SessionLocal)        (dependency_injection)
    ↓                          ↓                     ↓
Email Provider         PostgreSQL            LangGraph Runtime
(Mailgun/MailSlurp)    (GraphExecution,      (Workflow State)
                       NodeExecution)
```

### Example Integration

**Complete Workflow Checkpoint Flow:**

```python
# 1. Create inbox (Route → EmailManager)
@router.post("/inbox/create")
async def create_email_inbox(request: CreateInboxRequest):
    # Get email manager singleton
    email_manager = get_email_manager()

    # Create inbox via service
    inbox = await email_manager.create_inbox(request.expires_in_minutes)

    return CreateInboxResponse(
        inbox_id=inbox.inbox_id,
        email_address=inbox.email_address,
        expires_at=inbox.expires_at.isoformat() if inbox.expires_at else None,
        metadata=request.metadata
    )
```

```python
# 2. Send email (Route → EmailManager)
@router.post("/send")
async def send_checkpoint_email(request: SendEmailRequest):
    email_manager = get_email_manager()

    # Service layer handles provider abstraction
    result = await email_manager.send_email(
        from_address="noreply@agenticstudio.ai",
        to_address=request.recipient,
        subject=request.subject,
        body=request.body,
        html_body=request.html_body,
        reply_to=request.reply_to
    )

    return SendEmailResponse(success=True, result=result)
```

```python
# 3. Webhook callback (Route → Handler → Services)
@router.post("/webhooks/callback")
async def email_webhook_callback(request: Request, db: Session = Depends(get_db)):
    # Parse webhook payload
    form_data = await request.form()
    payload = {key: value for key, value in form_data.items()}

    # Delegate to handler
    result = await EmailWebhookHandler.handle_mailgun_webhook(payload, db)

    return WebhookCallbackResponse(**result)
```

**Handler Delegation:**

```python
# handlers/webhook.py
class EmailWebhookHandler:
    @staticmethod
    async def handle_mailgun_webhook(form_data: Dict, db: Session):
        # Extract email data
        email_data = EmailExtractionHandler.parse_mailgun_webhook(form_data)

        # Extract execution ID
        execution_id = EmailExtractionHandler.extract_execution_id(email_data)

        # Get execution from database
        execution, checkpoint = _get_execution_and_checkpoint(db, execution_id)

        # Extract content
        extracted_content = EmailExtractionHandler.extract_content(
            email_data,
            checkpoint.node_metadata.get("email_config", {})
        )

        # Update database
        _update_checkpoint_node(checkpoint, email_data, extracted_content, db)

        # Resume workflow (async background task)
        await _schedule_workflow_resume(
            execution_id,
            checkpoint.node_id,
            extracted_content,
            execution.id
        )

        return {"status": "success", "message": "Email received and workflow will resume"}
```

**Workflow Resumption:**

```python
# handlers/resumption.py
class WorkflowResumptionHandler:
    @staticmethod
    async def resume_workflow(execution_id, checkpoint_id, input_data, db_execution_id):
        db = SessionLocal()
        try:
            # Get execution engine
            execution_engine = get_execution_engine()

            # Get checkpoint ID for resume
            checkpoint_id_for_resume = await _get_checkpoint_id(thread_id)

            # Resume workflow with email content
            result = await execution_engine.resume_from_checkpoint(
                graph_name=execution.graph_name,
                thread_id=execution.thread_id,
                checkpoint_id=checkpoint_id_for_resume,
                new_input={"answer": input_data}
            )

            # Send WebSocket notification
            from backend.services.websocket import notifier
            await notifier.on_execution_complete(execution_id, result)

            return result
        finally:
            db.close()
```

### Services Used

#### EmailManager

**Location:** [backend/services/email/manager.py](../../services/email/manager.py)

**Purpose:** High-level interface for email operations

**Key Methods:**

- `create_inbox(expires_in_minutes)` - Create temporary email inbox
- `delete_inbox(inbox_id)` - Delete inbox
- `send_email(from_address, to_address, subject, body, ...)` - Send email
- `get_emails(inbox_id, limit)` - Retrieve inbox emails
- `register_webhook(inbox_id, webhook_url, event_types)` - Register webhook
- `unregister_webhook(webhook_id)` - Remove webhook

**Provider Abstraction:**

EmailManager abstracts two providers:

- **Mailgun** - Production email provider (webhook-based)
- **MailSlurp** - Testing provider (polling-based)

Configuration via environment variables:

```bash
EMAIL_PROVIDER=mailgun  # or mailslurp
MAILGUN_API_KEY=key_xxx
MAILGUN_DOMAIN=mail.agenticstudio.ai
```

#### Database Session

**Location:** [backend/services/database](../../backend/services/database/)

**Purpose:** SQLAlchemy session for database access

**Models Used:**

- `GraphExecution` - Workflow execution records
- `NodeExecution` - Individual node execution records (including checkpoints)

**Key Queries:**

```python
# Find paused execution
execution = db.query(GraphExecution).filter(
    GraphExecution.websocket_execution_id == execution_id,
    GraphExecution.status == "paused"
).first()

# Find paused checkpoint node
checkpoint = db.query(NodeExecution).filter(
    NodeExecution.graph_execution_id == execution.id,
    NodeExecution.node_type == "CHECKPOINT",
    NodeExecution.status == "paused"
).first()
```

#### ExecutionEngine

**Location:** [backend/services/dependency_injection](../../backend/services/dependency_injection/)

**Purpose:** Manages LangGraph workflow execution

**Key Methods:**

- `resume_from_checkpoint(graph_name, thread_id, checkpoint_id, new_input)` - Resume paused workflow
- `get_checkpoints(thread_id)` - Get checkpoint history

**Integration:**

```python
execution_engine = get_execution_engine()
result = await execution_engine.resume_from_checkpoint(
    graph_name="customer_approval_workflow",
    thread_id="thread_abc123",
    checkpoint_id="checkpoint_latest",
    new_input={"answer": "Approved"}
)
```

#### WebSocket Notifier

**Location:** [backend/services/websocket](../../backend/services/websocket/)

**Purpose:** Send real-time notifications to connected clients

**Usage:**

```python
from backend.services.websocket import notifier
await notifier.on_execution_complete(execution_id, result)
```

Sends notification to frontend when workflow resumes and completes after email response.

---

## Usage Examples

### Complete Email Checkpoint Workflow Example

**Scenario:** Create a workflow that pauses for manager approval via email, then resumes automatically when manager
replies.

#### Step 1: Create Inbox

```python
import httpx

async def setup_email_checkpoint():
    """Set up email checkpoint for workflow."""

    async with httpx.AsyncClient() as client:
        # Create temporary inbox
        response = await client.post(
            "https://api.agenticstudio.com/api/email/inbox/create",
            json={
                "expires_in_minutes": 120,  # 2 hours
                "metadata": {
                    "workflow": "budget_approval",
                    "requester": "john.doe@company.com"
                }
            },
            headers={"Authorization": f"Bearer {api_token}"}
        )
        response.raise_for_status()
        inbox_data = response.json()

        print(f"Created inbox: {inbox_data['email_address']}")
        print(f"Inbox ID: {inbox_data['inbox_id']}")

        return inbox_data
```

**Response:**

```json
{
  "inbox_id": "inbox_9h3k2j1f",
  "email_address": "workflow-exec_budget_2025@mail.agenticstudio.ai",
  "expires_at": "2025-10-21T16:00:00Z",
  "metadata": {
    "workflow": "budget_approval",
    "requester": "john.doe@company.com"
  }
}
```

#### Step 2: Register Webhook

```python
async def register_inbox_webhook(inbox_id: str, execution_id: str):
    """Register webhook for email notifications."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.agenticstudio.com/api/email/webhooks/register",
            json={
                "inbox_id": inbox_id,
                "execution_id": execution_id,
                "checkpoint_id": "checkpoint_manager_approval",
                "webhook_base_url": "https://agenticstudio.mycompany.com"
            },
            headers={"Authorization": f"Bearer {api_token}"}
        )
        response.raise_for_status()
        webhook_data = response.json()

        print(f"Registered webhook: {webhook_data['webhook_url']}")
        return webhook_data
```

**Response:**

```json
{
  "webhook_id": "webhook_7j2k3m4n",
  "inbox_id": "inbox_9h3k2j1f",
  "webhook_url": "https://agenticstudio.mycompany.com/api/email/webhooks/callback",
  "event_types": ["NEW_EMAIL"]
}
```

#### Step 3: Send Checkpoint Email

```python
async def send_approval_request(inbox_address: str, manager_email: str):
    """Send approval request email."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.agenticstudio.com/api/email/send",
            json={
                "recipient": manager_email,
                "subject": "Budget Approval Required [REF:exec_budget_2025]",
                "body": """Hello,

Please review and approve the Q4 budget proposal for $150,000.

Details:
- Marketing: $60,000
- Engineering: $50,000
- Operations: $40,000

Reply to this email with:
- 'APPROVED' to approve the budget
- 'REJECTED' to reject and request revision

Thank you,
AgenticStudio Automation""",
                "html_body": """<html><body>
<h2>Budget Approval Request</h2>
<p>Please review and approve the Q4 budget proposal for <strong>$150,000</strong>.</p>
<h3>Details:</h3>
<ul>
  <li>Marketing: $60,000</li>
  <li>Engineering: $50,000</li>
  <li>Operations: $40,000</li>
</ul>
<p>Reply to this email with:</p>
<ul>
  <li><strong>APPROVED</strong> to approve the budget</li>
  <li><strong>REJECTED</strong> to reject and request revision</li>
</ul>
<p>Thank you,<br>AgenticStudio Automation</p>
</body></html>""",
                "reply_to": inbox_address
            },
            headers={"Authorization": f"Bearer {api_token}"}
        )
        response.raise_for_status()
        send_result = response.json()

        print(f"Email sent successfully: {send_result['success']}")
        return send_result
```

**Response:**

```json
{
  "success": true,
  "result": {
    "id": "<20251021140030.1.A1B2C3D4E5F6@mail.agenticstudio.ai>",
    "message": "Queued. Thank you."
  }
}
```

#### Step 4: Monitor Checkpoint Status

```python
async def monitor_checkpoint_status(execution_id: str):
    """Monitor email checkpoint status."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.agenticstudio.com/api/email/checkpoint/{execution_id}/status",
            headers={"Authorization": f"Bearer {api_token}"}
        )
        response.raise_for_status()
        status = response.json()

        for checkpoint in status['email_checkpoints']:
            print(f"Checkpoint: {checkpoint['node_name']}")
            print(f"  Status: {checkpoint['status']}")
            print(f"  Email sent: {checkpoint['email_sent']}")
            print(f"  Email received: {checkpoint['email_received']}")

            if checkpoint['status'] == 'paused':
                print(f"  Waiting for response at: {checkpoint['reply_to_address']}")
            elif checkpoint['status'] == 'completed':
                elapsed = (
                    datetime.fromisoformat(checkpoint['end_time']) -
                    datetime.fromisoformat(checkpoint['start_time'])
                ).total_seconds()
                print(f"  Response received after {elapsed:.0f} seconds")

        return status
```

**Response (while waiting):**

```json
{
  "execution_id": "exec_budget_2025",
  "has_email_checkpoints": true,
  "email_checkpoints": [
    {
      "node_id": "checkpoint_manager_approval",
      "node_name": "Manager Approval",
      "status": "paused",
      "inbox_id": "inbox_9h3k2j1f",
      "reply_to_address": "workflow-exec_budget_2025@mail.agenticstudio.ai",
      "email_sent": true,
      "email_received": false,
      "start_time": "2025-10-21T14:00:00Z",
      "end_time": null
    }
  ]
}
```

**Response (after manager replies):**

```json
{
  "execution_id": "exec_budget_2025",
  "has_email_checkpoints": true,
  "email_checkpoints": [
    {
      "node_id": "checkpoint_manager_approval",
      "node_name": "Manager Approval",
      "status": "completed",
      "inbox_id": "inbox_9h3k2j1f",
      "reply_to_address": "workflow-exec_budget_2025@mail.agenticstudio.ai",
      "email_sent": true,
      "email_received": true,
      "start_time": "2025-10-21T14:00:00Z",
      "end_time": "2025-10-21T14:15:32Z"
    }
  ]
}
```

#### Step 5: Automatic Webhook Processing

When manager replies, Mailgun automatically calls the webhook:

```
POST https://agenticstudio.mycompany.com/api/email/webhooks/callback
Content-Type: application/x-www-form-urlencoded

recipient=workflow-exec_budget_2025@mail.agenticstudio.ai&
sender=manager@company.com&
from=Sarah Manager <manager@company.com>&
subject=Re: Budget Approval Required [REF:exec_budget_2025]&
body-plain=APPROVED&
stripped-text=APPROVED
```

**Webhook Processing (Automatic):**

1. EmailWebhookHandler parses webhook data
2. Extracts execution ID from recipient address
3. Finds paused execution in database
4. Extracts "APPROVED" from email body
5. Updates checkpoint node status to "completed"
6. Schedules background task to resume workflow
7. WorkflowResumptionHandler resumes workflow with input: `{"answer": "APPROVED"}`
8. WebSocket notifier sends completion event to UI

#### Step 6: Cleanup (Optional)

```python
async def cleanup_email_resources(inbox_id: str, webhook_id: str):
    """Clean up inbox and webhook after workflow completes."""

    async with httpx.AsyncClient() as client:
        # Delete webhook
        webhook_response = await client.delete(
            f"https://api.agenticstudio.com/api/email/webhooks/{webhook_id}",
            headers={"Authorization": f"Bearer {api_token}"}
        )
        print(f"Webhook deleted: {webhook_response.json()['success']}")

        # Delete inbox
        inbox_response = await client.delete(
            f"https://api.agenticstudio.com/api/email/inbox/{inbox_id}",
            headers={"Authorization": f"Bearer {api_token}"}
        )
        print(f"Inbox deleted: {inbox_response.json()['success']}")
```

### Complete Workflow Code

```python
import asyncio
import httpx
from datetime import datetime

API_BASE = "https://api.agenticstudio.com"
API_TOKEN = "your_api_token_here"

async def run_email_checkpoint_workflow():
    """Complete email checkpoint workflow example."""

    execution_id = "exec_budget_2025"
    manager_email = "manager@company.com"

    async with httpx.AsyncClient() as client:
        # 1. Create inbox
        print("Creating inbox...")
        inbox_resp = await client.post(
            f"{API_BASE}/api/email/inbox/create",
            json={"expires_in_minutes": 120},
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        inbox_resp.raise_for_status()
        inbox = inbox_resp.json()
        print(f"✓ Inbox created: {inbox['email_address']}")

        # 2. Register webhook
        print("\nRegistering webhook...")
        webhook_resp = await client.post(
            f"{API_BASE}/api/email/webhooks/register",
            json={
                "inbox_id": inbox['inbox_id'],
                "execution_id": execution_id,
                "checkpoint_id": "checkpoint_manager_approval"
            },
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        webhook_resp.raise_for_status()
        webhook = webhook_resp.json()
        print(f"✓ Webhook registered: {webhook['webhook_url']}")

        # 3. Send approval email
        print("\nSending approval request...")
        email_resp = await client.post(
            f"{API_BASE}/api/email/send",
            json={
                "recipient": manager_email,
                "subject": f"Budget Approval Required [REF:{execution_id}]",
                "body": "Please approve the Q4 budget. Reply APPROVED or REJECTED.",
                "reply_to": inbox['email_address']
            },
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        email_resp.raise_for_status()
        print("✓ Approval email sent")

        # 4. Monitor status
        print("\nMonitoring checkpoint status...")
        while True:
            status_resp = await client.get(
                f"{API_BASE}/api/email/checkpoint/{execution_id}/status",
                headers={"Authorization": f"Bearer {API_TOKEN}"}
            )
            status_resp.raise_for_status()
            status = status_resp.json()

            checkpoint = status['email_checkpoints'][0]
            if checkpoint['status'] == 'completed':
                print("✓ Email response received!")
                print(f"  Completed at: {checkpoint['end_time']}")
                break
            else:
                print(f"  Waiting for response... (status: {checkpoint['status']})")
                await asyncio.sleep(10)  # Check every 10 seconds

        # 5. Cleanup
        print("\nCleaning up...")
        await client.delete(
            f"{API_BASE}/api/email/webhooks/{webhook['webhook_id']}",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        await client.delete(
            f"{API_BASE}/api/email/inbox/{inbox['inbox_id']}",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        print("✓ Cleanup complete")

# Run the workflow
asyncio.run(run_email_checkpoint_workflow())
```

---

## Performance Considerations

### Endpoint Performance

#### Fast Endpoints (< 500ms)

- `POST /api/email/webhooks/callback` - Returns immediately, processes in background
- `GET /api/email/checkpoint/{execution_id}/status` - Simple database query
- `DELETE /api/email/inbox/{inbox_id}` - Quick provider API call
- `DELETE /api/email/webhooks/{webhook_id}` - Quick provider API call

#### Medium Endpoints (500ms - 2s)

- `POST /api/email/inbox/create` - Creates inbox via provider API
- `POST /api/email/send` - Sends email via provider (blocks until sent)
- `POST /api/email/webhooks/register` - Registers webhook with provider

#### Slower Endpoints (2s+)

- `GET /api/email/inbox/{inbox_id}/emails` - Depends on inbox size and provider

### Optimisation Tips

#### 1. Webhook Callback Performance

**Good Pattern - Non-blocking Response:**

```python
@router.post("/webhooks/callback")
async def email_webhook_callback(request: Request, db: Session = Depends(get_db)):
    # Parse webhook
    form_data = await request.form()
    payload = {key: value for key, value in form_data.items()}

    # Process webhook
    result = await EmailWebhookHandler.handle_mailgun_webhook(payload, db)

    # Return immediately (workflow resume happens in background)
    return WebhookCallbackResponse(**result)
```

**Why It's Fast:**

- Webhook response returns in < 100ms
- Workflow resumption happens in background asyncio task
- Email provider doesn't wait for workflow to complete
- Prevents webhook timeout errors

**Bad Pattern - Blocking Response:**

```python
# DON'T DO THIS
@router.post("/webhooks/callback")
async def email_webhook_callback(request: Request, db: Session = Depends(get_db)):
    # Process webhook
    execution_id = extract_execution_id(request)

    # BAD: Wait for workflow to complete before responding
    result = await resume_workflow(execution_id)  # Could take minutes!

    return {"status": "success", "result": result}
    # Webhook will timeout after 30 seconds
```

#### 2. Polling vs Webhooks

**Webhooks (Recommended):**

- Instant notification when email received
- No polling overhead
- Resource efficient
- Use for production deployments

**Polling (Testing Only):**

- Checks inbox every N seconds
- Higher latency (5-30 seconds)
- More provider API calls
- Use for local development or providers without webhooks

```python
# Configure via environment
EMAIL_PROVIDER=mailgun       # Webhook-based (fast)
EMAIL_PROVIDER=mailslurp     # Supports both webhook and polling
```

#### 3. Inbox Lifecycle Management

**Good Pattern - Automatic Cleanup:**

```python
# Create inbox with appropriate expiry
inbox = await client.post("/api/email/inbox/create", json={
    "expires_in_minutes": 60  # Auto-delete after 1 hour
})

# Provider automatically cleans up expired inboxes
# No manual cleanup needed for short-lived workflows
```

**Good Pattern - Manual Cleanup for Long Workflows:**

```python
try:
    # Create inbox
    inbox = await create_inbox(expires_in_minutes=1440)  # 24 hours

    # Run workflow
    await run_workflow()

finally:
    # Always clean up, even on errors
    await delete_inbox(inbox['inbox_id'])
    await delete_webhook(webhook['webhook_id'])
```

#### 4. Email Send Optimisation

**Good Pattern - HTML + Plain Text:**

```python
# Send both formats for best compatibility
await client.post("/api/email/send", json={
    "recipient": "user@example.com",
    "subject": "Action Required",
    "body": "Plain text version for email clients without HTML support",
    "html_body": "<html><body><h1>Action Required</h1><p>Formatted content</p></body></html>"
})
```

**Bad Pattern - Large Attachments:**

```python
# DON'T embed large files in email body
# Email API doesn't support attachments
# Use file upload API and send links instead

await client.post("/api/email/send", json={
    "body": f"Please review the document at: {document_url}"
    # NOT: Including base64 encoded attachment
})
```

#### 5. Database Query Optimisation

**Good Pattern - Indexed Queries:**

```python
# Status endpoint uses indexed columns
# Fast lookup by websocket_execution_id (indexed)
execution = db.query(GraphExecution).filter(
    GraphExecution.websocket_execution_id == execution_id
).first()

# Fast lookup by graph_execution_id and node_type (both indexed)
checkpoints = db.query(NodeExecution).filter(
    NodeExecution.graph_execution_id == execution.id,
    NodeExecution.node_type == "CHECKPOINT"
).all()
```

**Performance Metrics:**

- Single execution lookup: < 10ms
- Checkpoint node queries: < 50ms
- Total status endpoint: < 100ms

#### 6. Concurrent Execution

**Good Pattern - Parallel Setup:**

```python
import asyncio

async def setup_checkpoint_fast():
    """Set up inbox and webhook in parallel."""

    # Create inbox
    inbox_task = create_inbox()

    # Wait for inbox
    inbox = await inbox_task

    # Now register webhook (depends on inbox_id)
    webhook = await register_webhook(inbox['inbox_id'])

    # Send email in parallel with any other setup
    await asyncio.gather(
        send_email(inbox['email_address']),
        update_workflow_metadata(inbox['inbox_id'])
    )
```

---

## Related Documentation

### Architecture Documentation

- [Checkpoint Architecture](../architecture/checkpoints.md) - Design and implementation of checkpoint system
- [Email Service Architecture](../../services/email.md) - Email service layer documentation
- [Workflow Execution](../architecture/workflow-execution.md) - How workflows execute and pause

### API Documentation

- [Graph API](../graph/graph.md) - Workflow management and execution
- [Execution API](../execution/execution.md) - Direct workflow execution endpoints
- [WebSocket API](../websocket/websocket.md) - Real-time workflow notifications

### Service Documentation

- [Email Service](../../services/email.md) - Comprehensive email service documentation
- [Email Providers](../services/email-providers.md) - Mailgun and MailSlurp integration
- [Email Polling](../services/email-polling.md) - Polling service for non-webhook scenarios

### Integration Guides

- [Creating Email Checkpoints](../guides/email-checkpoints.md) - Step-by-step guide
- [Webhook Configuration](../guides/webhook-setup.md) - Setting up webhooks in production
- [Email Template Best Practices](../guides/email-templates.md) - Writing effective checkpoint emails

---

## Summary

The Email API module provides a comprehensive solution for email-based workflow checkpoints in AgenticStudio. It enables
workflows to pause execution and wait for email responses, creating powerful interactive automation patterns.

**Key Features:**

- **Temporary Inbox Management** - Create disposable email addresses for each workflow execution
- **Email Sending** - Send checkpoint notification emails to stakeholders
- **Webhook Integration** - Real-time processing of email responses via provider webhooks
- **Automatic Resumption** - Workflows resume automatically when email responses are received
- **Content Extraction** - Flexible email parsing with multiple extraction modes (full body, stripped text, regex
  patterns)
- **Status Monitoring** - Track email checkpoint progress across workflow executions
- **Provider Abstraction** - Support for multiple email providers (Mailgun, MailSlurp) via unified interface
- **Background Processing** - Non-blocking webhook handling with async workflow resumption
- **Robust Error Handling** - Graceful degradation and retry prevention for invalid webhooks

**Primary Use Cases:**

1. **Approval Workflows** - Pause workflow for manager/stakeholder approval via email
2. **Human-in-the-Loop** - Integrate human feedback into automated processes
3. **External Communication** - Communicate with users who don't have system access
4. **Asynchronous Input** - Collect information from stakeholders at their convenience
5. **Multi-step Approvals** - Chain multiple email checkpoints for complex approval chains
6. **Notification + Response** - Send notifications and wait for specific responses
7. **Data Collection** - Gather structured data via email forms or templated responses

**Architecture Highlights:**

- Clean handler-based separation of concerns
- Background task execution for non-blocking webhooks
- Provider abstraction for flexibility and testing
- Database-driven workflow state management
- Integration with LangGraph execution engine
- Real-time WebSocket notifications for UI updates

The Email API seamlessly integrates with AgenticStudio's workflow execution system, providing a reliable foundation for
building interactive, email-driven automation workflows.
