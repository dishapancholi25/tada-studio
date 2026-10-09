# Email Service Documentation

## Overview

The Email service provides comprehensive email capabilities for workflows in the AgenticStudio backend, including sending
emails, managing temporary inboxes, handling webhook notifications, and polling for email responses.

**Location:** [backend/services/email/](../../backend/services/email/)

**Primary Responsibilities:**

- Send emails through multiple providers (Mailgun, MailSlurp)
- Create and manage temporary email inboxes for receiving responses
- Register and handle webhooks for real-time email notifications
- Poll email inboxes when webhooks aren't available
- Extract structured content from email responses
- Track workflow-related emails with execution context
- Resume workflows from email responses

**Key Use Cases:**

- Sending notification emails from workflows
- Awaiting email responses in workflow checkpoints
- Extracting data from email replies
- Integrating external email-based approvals
- Handling asynchronous workflow interactions

---

## Architecture

### Module Structure

```
backend/services/email/
├── __init__.py              # Public API exports and package documentation
├── manager.py               # EmailManager - high-level interface
├── exceptions.py            # Custom exception hierarchy
├── schemas.py               # Pydantic data models
├── config.py                # Configuration constants and environment variables
├── utils.py                 # Utility functions (validation, extraction, formatting)
├── providers/               # Email provider implementations
│   ├── __init__.py         # Provider exports
│   ├── base.py             # Abstract base class and protocol
│   ├── factory.py          # Provider factory for dynamic creation
│   ├── mailgun.py          # Mailgun provider implementation
│   └── mailslurp.py        # MailSlurp provider implementation
└── polling/                 # Email polling for non-webhook scenarios
    ├── __init__.py         # Polling exports
    ├── service.py          # EmailPollingService for async polling
    └── processor.py        # EmailResponseProcessor for workflow resumption
```

**File Purposes:**

- **manager.py** - Provides `EmailManager`, the main high-level interface for all email operations. Acts as a facade
  over provider implementations.
- **exceptions.py** - Defines domain-specific exceptions for better error handling and debugging.
- **schemas.py** - Type-safe data models using Pydantic and dataclasses for email operations.
- **config.py** - Centralized configuration with environment variable defaults.
- **utils.py** - Shared utilities for email validation, content extraction, and formatting.
- **providers/** - Modular provider architecture supporting multiple email services.
- **polling/** - Alternative to webhooks for retrieving email responses through periodic polling.

### Design Patterns

**1. Factory Pattern (Provider Creation)**

The service uses a Factory pattern to dynamically create email providers based on configuration:

```python
# EmailServiceFactory in providers/factory.py
class EmailServiceFactory:
    _providers: Dict[str, Type[EmailServiceProvider]] = {
        "mailgun": MailgunProvider,
        "mailslurp": MailSlurpProvider,
    }

    @classmethod
    def create_provider(cls, provider_name: str = None) -> EmailServiceProvider:
        # Creates provider based on name or environment variable
        ...
```

**2. Abstract Base Class + Protocol (Provider Interface)**

Providers implement both an abstract base class and a Protocol for flexibility:

```python
# Abstract base class for inheritance
class EmailServiceProvider(ABC):
    @abstractmethod
    async def send_email(self, ...): ...


# Protocol for duck typing
class EmailProviderProtocol(Protocol):
    async def send_email(self, ...): ...
```

**3. Singleton Pattern (Service Instances)**

Both the email manager and polling service use singleton patterns:

```python
_email_manager: Optional[EmailManager] = None


def get_email_manager() -> EmailManager:
    global _email_manager
    if _email_manager is None:
        _email_manager = EmailManager()
    return _email_manager
```

**4. Facade Pattern (Manager Interface)**

`EmailManager` provides a simplified facade over complex provider operations:

```python
class EmailManager:
    def __init__(self, provider: EmailServiceProvider = None):
        self._provider = provider or EmailServiceFactory.create_provider()

    async def send_email(self, ...):
        return await self._provider.send_email(...)
```

**5. Strategy Pattern (Extraction Modes)**

Content extraction uses different strategies based on configuration:

```python
extract_mode in ["full_body", "stripped_text", "regex", "json"]
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  ┌──────────────────┐      ┌─────────────────────────────┐  │
│  │  Email Routes    │      │  Email Node Executor        │  │
│  │  (REST API)      │      │  (Workflow Nodes)           │  │
│  └────────┬─────────┘      └─────────┬───────────────────┘  │
└───────────┼────────────────────────────┼──────────────────────┘
            │                            │
            ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   EmailManager                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • send_email()                                       │   │
│  │  • create_inbox()                                     │   │
│  │  • register_webhook()                                 │   │
│  │  • get_emails()                                       │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Mailgun    │  │  MailSlurp   │  │   Custom     │
│   Provider   │  │   Provider   │  │   Provider   │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Email Polling  │
        │    Service      │
        │  ┌───────────┐  │
        │  │ Processor │  │
        │  └───────────┘  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   Database +    │
        │   WebSocket     │
        └─────────────────┘
```

### Dependencies

**Internal Dependencies:**

- [backend.services.database](database.md) - Database session management and models
- [backend.services.websocket](websocket.md) - Real-time notifications
- [backend.models](../models/) - Database ORM models (`GraphExecution`, `NodeExecution`)

**External Dependencies:**

- `aiohttp` - Async HTTP client for provider API calls
- `pydantic` - Data validation and schema definitions
- `asyncio` - Async task management for polling

**Database Dependencies:**

- Uses `SessionLocal` from database service
- Queries `GraphExecution` and `NodeExecution` models
- Updates checkpoint node status and output data

**Environment Variables:**

- `EMAIL_PROVIDER` - Email provider to use (default: "mailgun")
- `MAILGUN_API_KEY` - Mailgun API key (required for Mailgun)
- `MAILGUN_DOMAIN` - Mailgun domain (default: "sandbox.mailgun.org")
- `MAILSLURP_API_KEY` - MailSlurp API key (required for MailSlurp)
- `EMAIL_WEBHOOK_BASE_URL` - Base URL for webhook callbacks (default: "<http://localhost:8000>")

---

## Public API

### Exported Classes

- `EmailManager` - High-level interface for all email operations
- `EmailServiceProvider` - Abstract base class for provider implementations
- `EmailProviderProtocol` - Protocol defining provider interface
- `MailgunProvider` - Mailgun email provider implementation
- `MailSlurpProvider` - MailSlurp email provider implementation
- `EmailServiceFactory` - Factory for creating provider instances
- `EmailPollingService` - Service for polling email inboxes
- `EmailResponseProcessor` - Processor for handling email responses

### Exported Functions

- `get_email_manager()` - Get EmailManager singleton instance
- `reset_email_manager()` - Reset EmailManager singleton (for testing)
- `get_email_service()` - Get provider (backwards compatibility)
- `initialize_email_service()` - Initialize with specific provider (backwards compatibility)
- `get_email_polling_service()` - Get EmailPollingService singleton
- `extract_email_content()` - Extract content from email body
- `extract_workflow_id_from_email()` - Extract workflow/execution ID from email
- `validate_email_address()` - Validate email address format
- `format_email_address()` - Format email with display name
- `sanitize_subject()` - Sanitize email subject line

### Constants and Configuration

**Provider Constants:**

- `DEFAULT_EMAIL_PROVIDER` - Default provider name ("mailgun")
- `SUPPORTED_PROVIDERS` - List of supported providers (["mailgun", "mailslurp"])

**API Configuration:**

- `MAILGUN_BASE_URL` - Mailgun API base URL ("<https://api.mailgun.net/v3>")
- `MAILSLURP_BASE_URL` - MailSlurp API base URL ("<https://api.mailslurp.com>")

**Default Values:**

- `DEFAULT_FROM_NAME` - Default sender name ("AgenticStudio")
- `DEFAULT_FROM_DOMAIN` - Default from domain ("<noreply@agenticstudio.ai>")
- `DEFAULT_INBOX_EXPIRY_MINUTES` - Default inbox lifetime (60 minutes)
- `DEFAULT_POLLING_INTERVAL_SECONDS` - Default polling interval (30 seconds)
- `DEFAULT_POLLING_TIMEOUT_MINUTES` - Default polling timeout (60 minutes)

**Extraction Modes:**

- `EXTRACT_MODE_FULL_BODY` - Return full email body ("full_body")
- `EXTRACT_MODE_STRIPPED_TEXT` - Return text without quotes/signatures ("stripped_text")
- `EXTRACT_MODE_REGEX` - Extract using regex pattern ("regex")
- `EXTRACT_MODE_JSON` - Parse and return JSON from email ("json")

### Data Models

**Dataclasses (from schemas.py):**

- `EmailInbox` - Email inbox information
- `EmailMessage` - Email message data
- `EmailWebhook` - Webhook registration details

**Pydantic Models (from schemas.py):**

- `EmailSendRequest` - Request for sending email
- `WorkflowEmailRequest` - Workflow-tracked email request
- `EmailExtractionConfig` - Content extraction configuration
- `WebhookPayload` - Generic webhook payload
- `EmailPollingConfig` - Polling configuration
- `EmailProviderConfig` - Provider configuration

### Exceptions

```
Exception
└── EmailError (base for all email errors)
    ├── EmailProviderError (provider-specific errors)
    ├── EmailConfigurationError (configuration errors)
    ├── EmailSendError (sending failures)
    ├── EmailRetrievalError (retrieval failures)
    ├── EmailExtractionError (content extraction failures)
    ├── EmailInboxError (inbox operation errors)
    │   ├── InboxCreationError
    │   ├── InboxDeletionError
    │   └── InboxNotFoundError
    ├── WebhookError (webhook operation errors)
    │   ├── WebhookRegistrationError
    │   ├── WebhookUnregistrationError
    │   └── WebhookValidationError
    ├── EmailPollingError (polling errors)
    │   └── EmailPollingTimeoutError
    └── WorkflowResumptionError (workflow resume failures)
```

---

## Core Classes

### `EmailManager`

High-level manager for email service operations. Provides a unified interface for sending emails, managing inboxes, and
handling webhooks across different email providers.

**Purpose:** Simplifies email operations by providing a provider-agnostic interface. Acts as the primary entry point for
all email functionality.

**Responsibilities:**

- Delegate operations to the configured email provider
- Provide consistent interface across different providers
- Handle provider-specific quirks and differences
- Support workflow-tracked email sending
- Manage webhook registration and validation

**Initialisation:**

```python
def __init__(
        self,
        provider: EmailServiceProvider = None,
) -> None:
    """
    Args:
        provider: EmailServiceProvider instance (defaults to factory-created provider)
    """
```

**Key Methods:**

#### `create_inbox()`

Create a temporary email inbox for receiving responses.

```python
async def create_inbox(
        self,
        expires_in_minutes: int = 60,
) -> EmailInbox:
    """Create a temporary inbox for receiving emails."""
```

**Parameters:**

- `expires_in_minutes` (int) - How long the inbox should remain active (default: 60)

**Returns:**

- `EmailInbox` - Inbox details including ID, email address, and expiration

**Raises:**

- `InboxCreationError` - If inbox creation fails

**Example:**

```python
from backend.services.email import get_email_manager

manager = get_email_manager()
inbox = await manager.create_inbox(expires_in_minutes=120)
print(f"Inbox created: {inbox.email_address}")
print(f"Expires at: {inbox.expires_at}")
```

**Behaviour:**

- Creates a unique email address for receiving responses
- Sets expiration time based on `expires_in_minutes`
- Returns inbox metadata including provider-specific details
- With Mailgun, uses catch-all routing instead of actual inboxes
- With MailSlurp, creates actual temporary inbox

**Use Cases:**

- Creating inboxes for workflow checkpoint responses
- Temporary email addresses for one-time interactions
- Testing email-based integrations

#### `delete_inbox()`

Delete an email inbox when no longer needed.

```python
async def delete_inbox(
        self,
        inbox_id: str,
) -> bool:
    """Delete an email inbox."""
```

**Parameters:**

- `inbox_id` (str) - The inbox ID to delete

**Returns:**

- `bool` - True if successful

**Raises:**

- `InboxDeletionError` - If deletion fails

**Example:**

```python
manager = get_email_manager()
success = await manager.delete_inbox(inbox_id="abc123")
if success:
    print("Inbox deleted successfully")
```

**Behaviour:**

- Removes inbox from provider
- Cleans up any tracking data
- With Mailgun, removes workflow mappings
- With MailSlurp, deletes the actual inbox

**Use Cases:**

- Cleaning up after workflow completion
- Preventing inbox expiration errors
- Resource management in long-running workflows

#### `send_email()`

Send an email through the configured provider.

```python
async def send_email(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email."""
```

**Parameters:**

- `from_address` (str) - Sender email address
- `to_address` (str) - Recipient email address
- `subject` (str) - Email subject
- `body` (str) - Plain text email body
- `html_body` (Optional[str]) - HTML email body (default: None)
- `reply_to` (Optional[str]) - Reply-to email address (default: None)

**Returns:**

- `Dict[str, Any]` - Send result with message ID and status

**Raises:**

- `EmailSendError` - If sending fails

**Example:**

```python
from backend.services.email import get_email_manager

manager = get_email_manager()

result = await manager.send_email(
    from_address="noreply@agenticstudio.ai",
    to_address="user@example.com",
    subject="Workflow Notification",
    body="Your workflow has completed successfully.",
    html_body="<h1>Workflow Notification</h1><p>Your workflow has completed successfully.</p>",
    reply_to="support@agenticstudio.ai",
)

print(f"Email sent: {result.get('id')}")
```

**Behaviour:**

- Validates email addresses (basic format check)
- Sends both plain text and HTML versions if HTML body provided
- Uses provider's send API
- Returns provider-specific response including message ID
- Logs send operation for debugging

**Use Cases:**

- Sending notification emails from workflows
- Delivering workflow results to users
- Sending approval requests
- External system notifications

#### `send_workflow_email()`

Send a workflow-tracked email with execution context.

```python
async def send_workflow_email(
        self,
        workflow_id: str,
        execution_id: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a workflow-tracked email."""
```

**Parameters:**

- `workflow_id` (str) - Workflow ID
- `execution_id` (str) - Execution ID
- `to_address` (str) - Recipient email address
- `subject` (str) - Email subject
- `body` (str) - Email body
- `html_body` (Optional[str]) - HTML body (default: None)

**Returns:**

- `Dict[str, Any]` - Send result with workflow tracking info

**Raises:**

- `EmailSendError` - If sending fails

**Example:**

```python
manager = get_email_manager()

result = await manager.send_workflow_email(
    workflow_id="workflow-123",
    execution_id="exec-456",
    to_address="approver@example.com",
    subject="Approval Required",
    body="Please approve or reject this request by replying to this email.",
    html_body="<h2>Approval Required</h2><p>Please reply with APPROVE or REJECT.</p>",
)

print(f"Reply-to address: {result.get('reply_to')}")
print(f"Tracking execution: {result.get('execution_id')}")
```

**Behaviour:**

- Creates unique reply-to address with execution ID
- Adds reference ID to subject line `[REF:exec123]`
- Maps reply-to address to execution ID for response tracking
- Falls back to regular send if provider doesn't support workflow tracking
- Logs workflow context for debugging

**Use Cases:**

- Sending emails that require responses
- Workflow checkpoint email prompts
- Approval workflows with email responses
- Multi-step workflows with email interaction

#### `register_webhook()`

Register a webhook for email notifications.

```python
async def register_webhook(
        self,
        inbox_id: str,
        webhook_url: str,
        event_types: List[str] = None,
) -> EmailWebhook:
    """Register a webhook for inbox events."""
```

**Parameters:**

- `inbox_id` (str) - Inbox ID to monitor (* for catch-all)
- `webhook_url` (str) - URL for webhook notifications
- `event_types` (List[str]) - Event types to monitor (default: ["inbound"])

**Returns:**

- `EmailWebhook` - Webhook registration details

**Raises:**

- `WebhookRegistrationError` - If registration fails

**Example:**

```python
manager = get_email_manager()

webhook = await manager.register_webhook(
    inbox_id="inbox-123",
    webhook_url="https://api.example.com/webhooks/email",
    event_types=["inbound", "opened"],
)

print(f"Webhook registered: {webhook.webhook_id}")
print(f"Monitoring events: {webhook.event_types}")
```

**Behaviour:**

- Creates webhook with provider
- Returns webhook ID for later unregistration
- With Mailgun, creates routing rules
- With MailSlurp, registers webhook endpoint
- Validates webhook URL accessibility

**Use Cases:**

- Real-time email notifications
- Immediate workflow resumption on email receipt
- Tracking email opens and clicks
- Event-driven email processing

#### `unregister_webhook()`

Unregister a previously registered webhook.

```python
async def unregister_webhook(
        self,
        webhook_id: str,
) -> bool:
    """Unregister a webhook."""
```

**Parameters:**

- `webhook_id` (str) - Webhook ID to unregister

**Returns:**

- `bool` - True if successful

**Raises:**

- `WebhookUnregistrationError` - If unregistration fails

**Example:**

```python
manager = get_email_manager()
success = await manager.unregister_webhook(webhook_id="webhook-123")
```

**Use Cases:**

- Cleaning up after workflow completion
- Disabling email notifications
- Webhook rotation and updates

#### `get_emails()`

Retrieve emails from an inbox.

```python
async def get_emails(
        self,
        inbox_id: str,
        limit: int = 10,
) -> List[EmailMessage]:
    """Get emails from an inbox."""
```

**Parameters:**

- `inbox_id` (str) - Inbox ID
- `limit` (int) - Maximum number of emails to retrieve (default: 10)

**Returns:**

- `List[EmailMessage]` - List of email messages

**Raises:**

- `EmailRetrievalError` - If retrieval fails

**Example:**

```python
manager = get_email_manager()

emails = await manager.get_emails(inbox_id="inbox-123", limit=5)

for email in emails:
    print(f"From: {email.from_address}")
    print(f"Subject: {email.subject}")
    print(f"Body: {email.body}")
```

**Behaviour:**

- Fetches most recent emails first
- Returns up to `limit` emails
- Includes attachments if available
- Provider-specific: Mailgun requires message storage enabled

**Use Cases:**

- Manual email checking
- Polling for responses
- Email history retrieval
- Debugging email delivery

#### `validate_webhook_signature()`

Validate webhook signature for security.

```python
def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str = None,
) -> bool:
    """Validate webhook signature."""
```

**Parameters:**

- `payload` (bytes) - Webhook payload
- `signature` (str) - Signature to validate
- `secret` (str) - Optional secret key (default: None)

**Returns:**

- `bool` - True if signature is valid

**Example:**

```python
manager = get_email_manager()

# In webhook handler
is_valid = manager.validate_webhook_signature(
    payload=request.body,
    signature=request.headers.get("X-Signature"),
    secret="webhook-secret",
)

if not is_valid:
    raise HTTPException(status_code=401, detail="Invalid signature")
```

**Use Cases:**

- Securing webhook endpoints
- Preventing webhook spoofing
- Validating provider requests

**Properties:**

- `provider: EmailServiceProvider` - Get the current email provider instance

---

### `EmailServiceFactory`

Factory for creating email service provider instances. Supports dynamic provider registration and configuration.

**Purpose:** Centralize provider creation logic and enable runtime provider selection.

**Responsibilities:**

- Create provider instances based on configuration
- Register custom providers
- Validate provider availability
- Handle provider initialization errors

**Class Methods:**

#### `create_provider()`

Create an email service provider instance.

```python
@classmethod
def create_provider(
        cls,
        provider_name: str = None,
) -> EmailServiceProvider:
    """
    Create provider instance.

    Args:
        provider_name: Provider name (mailgun, mailslurp) or None for default

    Returns:
        EmailServiceProvider instance

    Raises:
        EmailConfigurationError: If provider is unknown or unavailable
    """
```

**Example:**

```python
from backend.services.email import EmailServiceFactory

# Create default provider (from env or default)
provider = EmailServiceFactory.create_provider()

# Create specific provider
mailgun = EmailServiceFactory.create_provider("mailgun")
mailslurp = EmailServiceFactory.create_provider("mailslurp")
```

**Behaviour:**

- Reads `EMAIL_PROVIDER` environment variable if `provider_name` is None
- Falls back to `DEFAULT_EMAIL_PROVIDER` if env var not set
- Validates provider is in `SUPPORTED_PROVIDERS` list
- Instantiates provider class
- Handles initialization errors gracefully

**Use Cases:**

- Initializing EmailManager with specific provider
- Testing with different providers
- Runtime provider switching
- Custom provider selection per workflow

#### `register_provider()`

Register a custom email service provider.

```python
@classmethod
def register_provider(
        cls,
        name: str,
        provider_class: Type[EmailServiceProvider],
):
    """
    Register a new provider.

    Args:
        name: Provider name
        provider_class: Provider class (must inherit from EmailServiceProvider)

    Raises:
        EmailConfigurationError: If provider doesn't inherit from base class
    """
```

**Example:**

```python
from backend.services.email import EmailServiceFactory, EmailServiceProvider


class CustomEmailProvider(EmailServiceProvider):
    async def send_email(self, ...):
        # Custom implementation
        pass

    # ... implement other abstract methods


# Register custom provider
EmailServiceFactory.register_provider("custom", CustomEmailProvider)

# Use custom provider
provider = EmailServiceFactory.create_provider("custom")
```

**Use Cases:**

- Adding support for new email providers
- Custom email integrations
- Testing with mock providers
- Extending email functionality

#### `get_available_providers()`

Get list of available provider names.

```python
@classmethod
def get_available_providers(cls) -> list:
    """Get list of available provider names."""
```

**Example:**

```python
providers = EmailServiceFactory.get_available_providers()
print(f"Available providers: {', '.join(providers)}")
# Output: Available providers: mailgun, mailslurp
```

---

### `EmailServiceProvider`

Abstract base class defining the interface for email service providers.

**Purpose:** Define the contract that all email providers must implement.

**Responsibilities:**

- Specify required methods for email operations
- Ensure consistent interface across providers
- Enable polymorphic provider usage

**Abstract Methods:**

All providers must implement these methods:

- `create_inbox(expires_in_minutes: int) -> EmailInbox`
- `delete_inbox(inbox_id: str) -> bool`
- `send_email(from_address, to_address, subject, body, html_body, reply_to) -> Dict`
- `register_webhook(inbox_id, webhook_url, event_types) -> EmailWebhook`
- `unregister_webhook(webhook_id: str) -> bool`
- `get_emails(inbox_id: str, limit: int) -> List[EmailMessage]`
- `validate_webhook_signature(payload, signature, secret) -> bool`

**Example Implementation:**

See [`MailgunProvider`](#mailgunprovider) or [`MailSlurpProvider`](#mailslurpprovider) for complete implementations.

---

### `MailgunProvider`

Mailgun implementation of email service provider. Supports sending and receiving emails with webhook support using
Mailgun API.

**Purpose:** Integrate Mailgun as an email provider for AgenticStudio workflows.

**Responsibilities:**

- Send emails via Mailgun API
- Create virtual inboxes using catch-all routing
- Register webhooks as Mailgun routes
- Retrieve stored messages
- Validate Mailgun webhook signatures

**Initialisation:**

```python
def __init__(
        self,
        api_key: str = None,
        domain: str = None,
) -> None:
    """
    Args:
        api_key: Mailgun API key (defaults to MAILGUN_API_KEY env var)
        domain: Mailgun domain (defaults to MAILGUN_DOMAIN env var or sandbox)

    Raises:
        EmailConfigurationError: If API key is missing
    """
```

**Example:**

```python
from backend.services.email import MailgunProvider

# Using environment variables
provider = MailgunProvider()

# Explicit configuration
provider = MailgunProvider(
    api_key="key-abc123",
    domain="mg.example.com",
)
```

**Key Methods:**

#### `send_email_with_workflow_id()`

Send an email with workflow tracking (Mailgun-specific feature).

```python
async def send_email_with_workflow_id(
        self,
        workflow_id: str,
        execution_id: str,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
) -> Dict[str, Any]:
    """Send workflow-tracked email."""
```

**Parameters:**

- `workflow_id` (str) - Workflow ID
- `execution_id` (str) - Execution ID
- `to_address` (str) - Recipient email
- `subject` (str) - Email subject
- `body` (str) - Email body
- `html_body` (Optional[str]) - HTML body

**Returns:**

- `Dict[str, Any]` - Send result with workflow tracking info including reply-to address

**Raises:**

- `EmailSendError` - If sending fails

**Example:**

```python
provider = MailgunProvider()

result = await provider.send_email_with_workflow_id(
    workflow_id="wf-123",
    execution_id="exec-456",
    to_address="user@example.com",
    subject="Please confirm",
    body="Reply to this email to confirm.",
)

print(f"Reply to: {result['reply_to']}")
# Output: Reply to: workflow-exec-456@mg.example.com
```

**Behaviour:**

- Creates unique `reply_to` address: `workflow-{execution_id}@{domain}`
- Adds reference to subject: `{subject} [REF:{execution_id[:8]}]`
- Stores workflow mapping for response routing
- Returns enhanced result with tracking metadata

**Use Cases:**

- Workflow checkpoint emails requiring responses
- Email-based approvals with execution tracking
- Multi-step workflows with email interaction

**Special Notes:**

- **Inbox Creation:** Mailgun doesn't create actual inboxes. Instead, it uses catch-all routing with patterns like
  `workflow-*@domain`.
- **Message Storage:** Retrieving emails requires Mailgun message storage to be enabled in your account.
- **Webhook Security:** Uses HMAC-SHA256 signature validation with timestamp and token.

---

### `MailSlurpProvider`

Documentation to follow.

---

### `EmailPollingService`

Service to poll for email responses when webhooks aren't available. Provides an alternative to webhooks for checkpoint
resumption.

**Purpose:** Enable email-based workflow resumption without requiring webhook infrastructure.

**Responsibilities:**

- Poll inboxes at regular intervals
- Detect new emails and process them
- Handle polling timeouts
- Manage multiple concurrent polling tasks
- Clean up polling resources

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialize email polling service."""
```

**Key Methods:**

#### `start_polling()`

Start polling for email responses.

```python
async def start_polling(
        self,
        execution_id: str,
        checkpoint_id: str,
        inbox_id: str,
        db_execution_id: int,
        interval_seconds: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        timeout_minutes: int = DEFAULT_POLLING_TIMEOUT_MINUTES,
):
    """
    Start polling for email responses.

    Args:
        execution_id: Workflow execution ID
        checkpoint_id: Checkpoint node ID
        inbox_id: Email inbox ID
        db_execution_id: Database execution ID
        interval_seconds: Polling interval (default: 30)
        timeout_minutes: Timeout duration (default: 60)
    """
```

**Parameters:**

- `execution_id` (str) - Workflow execution ID
- `checkpoint_id` (str) - Checkpoint node ID
- `inbox_id` (str) - Email inbox ID to poll
- `db_execution_id` (int) - Database execution ID
- `interval_seconds` (int) - Seconds between polls (default: 30, range: 10-300)
- `timeout_minutes` (int) - Minutes before timeout (default: 60, max: 1440)

**Example:**

```python
from backend.services.email import get_email_polling_service

polling_service = get_email_polling_service()

await polling_service.start_polling(
    execution_id="exec-123",
    checkpoint_id="checkpoint-456",
    inbox_id="inbox-789",
    db_execution_id=42,
    interval_seconds=30,
    timeout_minutes=120,
)

print("Polling started for workflow execution")
```

**Behaviour:**

- Creates background asyncio task for polling
- Cancels any existing polling for the same execution_id
- Polls inbox every `interval_seconds`
- Processes new emails through `EmailResponseProcessor`
- Stops polling after successful email processing
- Triggers timeout handler if no email received within `timeout_minutes`
- Automatically cleans up resources on completion or cancellation

**Use Cases:**

- Workflow checkpoints without webhook support
- Environments where webhooks are blocked (firewalls, local dev)
- Backup mechanism when webhooks fail
- Testing and development scenarios

#### `stop_polling()`

Stop polling for a specific execution.

```python
def stop_polling(
        self,
        execution_id: str,
):
    """
    Stop polling for execution.

    Args:
        execution_id: Workflow execution ID
    """
```

**Example:**

```python
polling_service = get_email_polling_service()
polling_service.stop_polling(execution_id="exec-123")
```

**Use Cases:**

- Manual workflow cancellation
- Received email through webhook (fallback mechanism)
- Cleanup on workflow errors

#### `stop_all_polling()`

Stop all active polling tasks.

```python
def stop_all_polling(self):
    """Stop all polling tasks."""
```

**Example:**

```python
polling_service = get_email_polling_service()
polling_service.stop_all_polling()
```

**Use Cases:**

- Application shutdown
- Resetting polling state
- Emergency stop of all email polling

#### `get_active_polls()`

Get currently active polling configurations.

```python
def get_active_polls(self) -> Dict[str, EmailPollingConfig]:
    """
    Get active polling configurations.

    Returns:
        Dict of execution_id -> EmailPollingConfig
    """
```

**Example:**

```python
polling_service = get_email_polling_service()
active = polling_service.get_active_polls()

for exec_id, config in active.items():
    print(f"Polling {exec_id}: inbox={config.inbox_id}, interval={config.interval_seconds}s")
```

**Use Cases:**

- Monitoring active polls
- Debugging polling issues
- Admin dashboards

#### `is_polling()`

Check if polling is active for an execution.

```python
def is_polling(
        self,
        execution_id: str,
) -> bool:
    """
    Check if polling is active.

    Args:
        execution_id: Workflow execution ID

    Returns:
        True if polling is active
    """
```

**Example:**

```python
if polling_service.is_polling("exec-123"):
    print("Already polling this execution")
else:
    await polling_service.start_polling(...)
```

**Use Cases:**

- Preventing duplicate polling
- Conditional polling start
- Status checks

---

### `EmailResponseProcessor`

Processes email responses for workflow resumption. Handles email content extraction and checkpoint node updates.

**Purpose:** Process received emails and update workflow state for resumption.

**Responsibilities:**

- Extract content from emails based on configuration
- Update checkpoint node with email data
- Send WebSocket notifications
- Handle polling timeouts
- Resume workflow execution

**Static Methods:**

#### `process_email_response()`

Process received email and update workflow state.

```python
@staticmethod
async def process_email_response(
        execution_id: str,
        checkpoint_id: str,
        db_execution_id: int,
        email: EmailMessage,
        extraction_config: dict = None,
) -> bool:
    """
    Process email response.

    Args:
        execution_id: Workflow execution ID
        checkpoint_id: Checkpoint node ID
        db_execution_id: Database execution ID
        email: EmailMessage to process
        extraction_config: Configuration for content extraction

    Returns:
        True if processing successful

    Raises:
        EmailExtractionError: If content extraction fails
    """
```

**Parameters:**

- `execution_id` (str) - Workflow execution ID
- `checkpoint_id` (str) - Checkpoint node ID
- `db_execution_id` (int) - Database execution ID
- `email` (EmailMessage) - Email to process
- `extraction_config` (dict) - Optional extraction configuration

**Returns:**

- `bool` - True if processing successful, False otherwise

**Example:**

```python
from backend.services.email import EmailResponseProcessor
from backend.services.email.schemas import EmailMessage
from datetime import datetime

email = EmailMessage(
    id="msg-123",
    from_address="user@example.com",
    to_addresses=["workflow-exec456@domain.com"],
    subject="Re: Approval Request",
    body="APPROVED - looks good to me!",
    received_at=datetime.utcnow(),
)

success = await EmailResponseProcessor.process_email_response(
    execution_id="exec-456",
    checkpoint_id="checkpoint-789",
    db_execution_id=42,
    email=email,
    extraction_config={
        "extract_mode": "regex",
        "extraction_pattern": r"(APPROVED|REJECTED)",
    },
)

if success:
    print("Workflow resumed with email response")
```

**Behaviour:**

- Queries database for paused checkpoint node
- Extracts content using configured extraction mode
- Updates checkpoint node output_data with:
  - `from` - Sender address
  - `subject` - Email subject
  - `body` - Full email body
  - `extracted_content` - Processed content
  - `received_at` - Receipt timestamp
- Marks checkpoint node as "completed"
- Sends WebSocket notification of type "checkpoint_resumed"
- Commits database changes

**Use Cases:**

- Processing approval/rejection emails
- Extracting structured data from email responses
- Resuming workflows from email interactions
- Email-based human-in-the-loop workflows

#### `handle_polling_timeout()`

Handle polling timeout when no email received.

```python
@staticmethod
async def handle_polling_timeout(
        execution_id: str,
        db_execution_id: int,
        timeout_minutes: int,
):
    """
    Handle polling timeout.

    Args:
        execution_id: Workflow execution ID
        db_execution_id: Database execution ID
        timeout_minutes: Timeout duration
    """
```

**Example:**

```python
await EmailResponseProcessor.handle_polling_timeout(
    execution_id="exec-123",
    db_execution_id=42,
    timeout_minutes=60,
)
```

**Behaviour:**

- Checks if execution is still in "paused" state
- Sends WebSocket notification of type "checkpoint_timeout"
- Does not automatically fail the workflow
- Allows manual resumption or intervention

**Use Cases:**

- Notifying users of email timeout
- Triggering escalation workflows
- Logging timeout events

---

## Functions

### `get_email_manager()`

Get the email manager instance (singleton pattern).

**Signature:**

```python
def get_email_manager(
        provider: EmailServiceProvider = None,
) -> EmailManager:
    """
    Get EmailManager singleton.

    Args:
        provider: Optional provider to use (only for first initialisation)

    Returns:
        EmailManager instance
    """
```

**Parameters:**

- `provider` (EmailServiceProvider) - Optional provider (only used on first call, default: None)

**Returns:**

- `EmailManager` - Singleton EmailManager instance

**Example:**

```python
from backend.services.email import get_email_manager

# Get default manager
manager = get_email_manager()

# First initialization with custom provider (only affects first call)
from backend.services.email import MailgunProvider

custom_provider = MailgunProvider(api_key="custom-key")
manager = get_email_manager(provider=custom_provider)

# Subsequent calls return the same instance
manager2 = get_email_manager()  # Returns same instance as above
assert manager is manager2  # True
```

**Use Cases:**

- Standard email operations across application
- Ensuring single provider configuration
- Dependency injection patterns

---

### `reset_email_manager()`

Reset the email manager singleton (useful for testing).

**Signature:**

```python
def reset_email_manager():
    """Reset the email manager singleton."""
```

**Example:**

```python
from backend.services.email import reset_email_manager, get_email_manager

# Reset singleton
reset_email_manager()

# Next call creates new instance
manager = get_email_manager()
```

**Use Cases:**

- Unit testing with different configurations
- Integration test cleanup
- Switching providers during runtime (test scenarios)

---

### `extract_email_content()`

Extract content from email based on configuration.

**Signature:**

```python
def extract_email_content(
        email_body: str,
        extract_mode: str = EXTRACT_MODE_FULL_BODY,
        extraction_pattern: Optional[str] = None,
        stripped_text: Optional[str] = None,
) -> Any:
    """
    Extract content from email.

    Args:
        email_body: The raw email body text
        extract_mode: How to extract content (full_body, stripped_text, regex, json)
        extraction_pattern: Regex pattern for extraction (if mode=regex)
        stripped_text: Pre-stripped text (without signatures/quotes)

    Returns:
        Extracted content (str or dict for JSON mode)

    Raises:
        EmailExtractionError: If extraction fails
    """
```

**Parameters:**

- `email_body` (str) - Raw email body text
- `extract_mode` (str) - Extraction mode: "full_body", "stripped_text", "regex", or "json" (default: "full_body")
- `extraction_pattern` (Optional[str]) - Regex pattern for regex mode (default: None)
- `stripped_text` (Optional[str]) - Pre-stripped text without signatures (default: None)

**Returns:**

- `Any` - Extracted content (str or dict for JSON mode)

**Raises:**

- `EmailExtractionError` - If extraction fails

**Example:**

```python
from backend.services.email import extract_email_content

# Full body extraction
body = "Please approve this request. Thanks!"
content = extract_email_content(body, extract_mode="full_body")
# Returns: "Please approve this request. Thanks!"

# Regex extraction
body = "Status: APPROVED - looks good"
content = extract_email_content(
    body,
    extract_mode="regex",
    extraction_pattern=r"Status:\s*(\w+)",
)
# Returns: "APPROVED"

# JSON extraction
body = "Here's the data: {\"status\": \"approved\", \"amount\": 1000}"
content = extract_email_content(body, extract_mode="json")
# Returns: {"status": "approved", "amount": 1000}

# Stripped text (without quotes and signatures)
stripped = "This is my actual response"
content = extract_email_content(
    "Full email body with quotes...",
    extract_mode="stripped_text",
    stripped_text=stripped,
)
# Returns: "This is my actual response"
```

**Use Cases:**

- Extracting approval/rejection decisions
- Parsing structured data from emails
- Cleaning email responses
- JSON API responses via email

---

### `extract_workflow_id_from_email()`

Extract workflow/execution ID from email data using multiple methods.

**Signature:**

```python
def extract_workflow_id_from_email(
        email_data: Dict[str, Any],
) -> Optional[str]:
    """
    Extract workflow/execution ID from email.

    Tries multiple methods:
    1. Recipient address (workflow-{id}@domain)
    2. Subject line reference ([REF:{id}])
    3. Custom headers (X-Workflow-ID)

    Args:
        email_data: Email data dictionary

    Returns:
        Extracted execution ID or None
    """
```

**Parameters:**

- `email_data` (Dict[str, Any]) - Email data dictionary with keys like "recipient", "subject", "message-headers"

**Returns:**

- `Optional[str]` - Extracted execution ID or None if not found

**Example:**

```python
from backend.services.email import extract_workflow_id_from_email

# Method 1: From recipient address
email_data = {
    "recipient": "workflow-exec-123@domain.com",
    "subject": "Reply",
    "body": "Approved",
}
exec_id = extract_workflow_id_from_email(email_data)
# Returns: "exec-123"

# Method 2: From subject line
email_data = {
    "recipient": "user@domain.com",
    "subject": "Re: Approval Request [REF:exec-456]",
    "body": "Approved",
}
exec_id = extract_workflow_id_from_email(email_data)
# Returns: "exec-456"

# Method 3: From custom header
email_data = {
    "recipient": "user@domain.com",
    "subject": "Reply",
    "message-headers": [
        ["From", "sender@example.com"],
        ["X-Workflow-ID", "exec-789"],
    ],
    "body": "Approved",
}
exec_id = extract_workflow_id_from_email(email_data)
# Returns: "exec-789"
```

**Use Cases:**

- Routing email responses to correct workflow
- Webhook handlers identifying execution
- Email polling response matching
- Debugging email tracking

---

### `validate_email_address()`

Validate email address format.

**Signature:**

```python
def validate_email_address(
        email: str,
) -> bool:
    """
    Validate email address.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
```

**Parameters:**

- `email` (str) - Email address to validate

**Returns:**

- `bool` - True if valid format, False otherwise

**Example:**

```python
from backend.services.email import validate_email_address

# Valid emails
assert validate_email_address("user@example.com") is True
assert validate_email_address("user.name+tag@example.co.uk") is True

# Invalid emails
assert validate_email_address("invalid") is False
assert validate_email_address("@example.com") is False
assert validate_email_address("user@") is False
assert validate_email_address(None) is False
```

**Use Cases:**

- Form validation
- API request validation
- Email send pre-checks
- User input sanitization

---

### `format_email_address()`

Format email address with display name.

**Signature:**

```python
def format_email_address(
        name: str,
        email: str,
) -> str:
    """
    Format email address with name.

    Args:
        name: Display name
        email: Email address

    Returns:
        Formatted address like "Name <email@domain.com>"
    """
```

**Parameters:**

- `name` (str) - Display name
- `email` (str) - Email address

**Returns:**

- `str` - Formatted email address

**Example:**

```python
from backend.services.email import format_email_address

formatted = format_email_address("John Doe", "john@example.com")
# Returns: "John Doe <john@example.com>"

formatted = format_email_address("", "john@example.com")
# Returns: "john@example.com"

formatted = format_email_address("Support Team", "support@agenticstudio.ai")
# Returns: "Support Team <support@agenticstudio.ai>"
```

**Use Cases:**

- Formatting from addresses with friendly names
- Email display in UI
- Creating professional-looking emails

---

### `sanitize_subject()`

Sanitize email subject line by removing control characters and truncating.

**Signature:**

```python
def sanitize_subject(
        subject: str,
        max_length: int = 200,
) -> str:
    """
    Sanitize email subject line.

    Args:
        subject: Original subject
        max_length: Maximum length (default: 200)

    Returns:
        Sanitised subject
    """
```

**Parameters:**

- `subject` (str) - Original subject line
- `max_length` (int) - Maximum length (default: 200)

**Returns:**

- `str` - Sanitised subject line

**Example:**

```python
from backend.services.email import sanitize_subject

# Remove control characters
subject = "Hello\x00World\x1f"
clean = sanitize_subject(subject)
# Returns: "HelloWorld"

# Truncate long subjects
long_subject = "A" * 300
clean = sanitize_subject(long_subject, max_length=200)
# Returns: "A" * 197 + "..."

# Normal subject
clean = sanitize_subject("Order Confirmation")
# Returns: "Order Confirmation"
```

**Use Cases:**

- Preventing email header injection
- Ensuring subject line compatibility
- Database field length constraints
- Security sanitization

---

## Configuration

### Configuration Classes

#### `EmailProviderConfig`

Base configuration for email providers.

```python
class EmailProviderConfig(BaseModel):
    """Base configuration for email providers."""

    provider_name: str = Field(..., description="Email provider name (mailgun, mailslurp)")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    domain: Optional[str] = Field(None, description="Domain for email operations")
```

**Fields:**

- `provider_name` (str) - Provider name: "mailgun" or "mailslurp" (required)
- `api_key` (Optional[str]) - API key for the provider (default: None, uses env var)
- `domain` (Optional[str]) - Domain for email operations (default: None, uses env var or sandbox)

**Example:**

```python
from backend.services.email.schemas import EmailProviderConfig

config = EmailProviderConfig(
    provider_name="mailgun",
    api_key="key-abc123",
    domain="mg.example.com",
)
```

#### `EmailPollingConfig`

Configuration for email polling operations.

```python
class EmailPollingConfig(BaseModel):
    """Configuration for email polling operations."""

    execution_id: str
    checkpoint_id: str
    inbox_id: str
    db_execution_id: int
    interval_seconds: int = Field(default=30, ge=10, le=300)
    timeout_minutes: int = Field(default=60, ge=1, le=1440)
```

**Fields:**

- `execution_id` (str) - Workflow execution ID (required)
- `checkpoint_id` (str) - Checkpoint node ID (required)
- `inbox_id` (str) - Email inbox ID to poll (required)
- `db_execution_id` (int) - Database execution ID (required)
- `interval_seconds` (int) - Polling interval in seconds (default: 30, range: 10-300)
- `timeout_minutes` (int) - Timeout in minutes (default: 60, max: 1440 = 24 hours)

#### `EmailExtractionConfig`

Configuration for extracting content from email responses.

```python
class EmailExtractionConfig(BaseModel):
    """Configuration for extracting content from email responses."""

    extract_mode: str = Field(
        default="full_body",
        description="Extraction mode: full_body, regex, json, or stripped_text",
    )
    extraction_pattern: Optional[str] = Field(
        None,
        description="Regex pattern for extraction (if mode=regex)",
    )
```

**Fields:**

- `extract_mode` (str) - Extraction mode (default: "full_body")
  - `"full_body"` - Return entire email body
  - `"stripped_text"` - Return text without quotes/signatures
  - `"regex"` - Extract using regex pattern
  - `"json"` - Parse JSON from email body
- `extraction_pattern` (Optional[str]) - Regex pattern for regex mode (default: None)

**Example:**

```python
from backend.services.email.schemas import EmailExtractionConfig

# Full body extraction
config = EmailExtractionConfig(extract_mode="full_body")

# Regex extraction for approval status
config = EmailExtractionConfig(
    extract_mode="regex",
    extraction_pattern=r"Status:\s*(APPROVED|REJECTED)",
)

# JSON extraction
config = EmailExtractionConfig(extract_mode="json")
```

### Environment Variables

**Required for Mailgun:**

- `MAILGUN_API_KEY` - Mailgun API key (required: yes)

**Optional for Mailgun:**

- `MAILGUN_DOMAIN` - Mailgun domain (default: "sandbox.mailgun.org")
- `MAILGUN_SANDBOX_DOMAIN` - Sandbox domain override (default: generated from API key hash)

**Required for MailSlurp:**

- `MAILSLURP_API_KEY` - MailSlurp API key (required: yes)

**General Configuration:**

- `EMAIL_PROVIDER` - Email provider to use (default: "mailgun", options: "mailgun", "mailslurp")
- `EMAIL_WEBHOOK_BASE_URL` - Base URL for webhook callbacks (default: "<http://localhost:8000>")

### Initialisation Patterns

#### Basic Initialisation

```python
from backend.services.email import get_email_manager

# Get manager with default provider (from env or "mailgun")
manager = get_email_manager()

# Use manager
inbox = await manager.create_inbox(expires_in_minutes=60)
```

#### Advanced Initialisation

```python
from backend.services.email import EmailManager, MailgunProvider

# Create custom provider
provider = MailgunProvider(
    api_key="key-abc123",
    domain="mg.example.com",
)

# Create manager with custom provider
manager = EmailManager(provider=provider)

# Use manager
result = await manager.send_email(
    from_address="noreply@example.com",
    to_address="user@example.com",
    subject="Hello",
    body="This is a test email",
)
```

#### Factory-Based Initialisation

```python
from backend.services.email import EmailServiceFactory, EmailManager

# Create provider using factory
provider = EmailServiceFactory.create_provider("mailgun")

# Create manager
manager = EmailManager(provider=provider)
```

#### Dependency Injection (FastAPI)

```python
from fastapi import Depends
from backend.services.email import get_email_manager, EmailManager


def get_email_service() -> EmailManager:
    """Dependency for email manager."""
    return get_email_manager()


@router.post("/send")
async def send_email(
        request: EmailRequest,
        email_manager: EmailManager = Depends(get_email_service),
):
    """Send email endpoint."""
    result = await email_manager.send_email(
        from_address=request.from_address,
        to_address=request.to_address,
        subject=request.subject,
        body=request.body,
    )
    return {"message_id": result.get("id")}
```

---

## Error Handling

### Exception Hierarchy

```
Exception
└── EmailError (base for all email errors)
    ├── EmailConfigurationError (configuration problems)
    ├── EmailProviderError (provider-specific errors)
    ├── EmailSendError (sending failures)
    ├── EmailRetrievalError (retrieval failures)
    ├── EmailExtractionError (content extraction failures)
    ├── EmailInboxError (inbox operation errors)
    │   ├── InboxCreationError (failed to create inbox)
    │   ├── InboxDeletionError (failed to delete inbox)
    │   └── InboxNotFoundError (inbox not found)
    ├── WebhookError (webhook operation errors)
    │   ├── WebhookRegistrationError (failed to register webhook)
    │   ├── WebhookUnregistrationError (failed to unregister webhook)
    │   └── WebhookValidationError (signature validation failed)
    ├── EmailPollingError (polling errors)
    │   └── EmailPollingTimeoutError (polling timeout)
    └── WorkflowResumptionError (workflow resume failures)
```

### Exception Details

#### `EmailError`

Base exception for all email-related errors.

**Inherits from:** `Exception`

**When raised:**

- Never raised directly, use specific subclasses
- Catch this to handle all email service errors

**Example:**

```python
from backend.services.email import get_email_manager, EmailError

try:
    manager = get_email_manager()
    result = await manager.send_email(...)
except EmailError as e:
    logger.error(f"Email operation failed: {e}")
    # Handle any email-related error
```

#### `EmailConfigurationError`

Email service configuration error.

**Inherits from:** `EmailError`

**When raised:**

- Missing API keys or credentials
- Invalid provider name
- Provider class registration errors
- Missing required configuration

**Example:**

```python
from backend.services.email import EmailServiceFactory, EmailConfigurationError

try:
    # Missing API key will raise this
    provider = EmailServiceFactory.create_provider("mailgun")
except EmailConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    # Provide user guidance on setting up API keys
```

#### `EmailSendError`

Errors related to sending emails.

**Inherits from:** `EmailError`

**When raised:**

- SMTP/API errors during send
- Invalid recipient addresses
- Rate limiting or quota exceeded
- Network errors during send

**Example:**

```python
from backend.services.email import get_email_manager, EmailSendError

try:
    manager = get_email_manager()
    result = await manager.send_email(
        from_address="invalid",
        to_address="user@example.com",
        subject="Test",
        body="Test body",
    )
except EmailSendError as e:
    logger.error(f"Failed to send email: {e}")
    # Retry or notify user
```

#### `InboxCreationError`

Failed to create email inbox.

**Inherits from:** `EmailInboxError` → `EmailError`

**When raised:**

- Provider API errors during inbox creation
- Quota limits reached
- Invalid inbox parameters

**Example:**

```python
from backend.services.email import get_email_manager, InboxCreationError

try:
    manager = get_email_manager()
    inbox = await manager.create_inbox(expires_in_minutes=60)
except InboxCreationError as e:
    logger.error(f"Failed to create inbox: {e}")
    # Fall back to alternative mechanism
```

#### `WebhookRegistrationError`

Failed to register webhook.

**Inherits from:** `WebhookError` → `EmailError`

**When raised:**

- Provider API errors during webhook registration
- Invalid webhook URL
- Webhook URL not accessible
- Maximum webhook limit reached

**Example:**

```python
from backend.services.email import get_email_manager, WebhookRegistrationError

try:
    manager = get_email_manager()
    webhook = await manager.register_webhook(
        inbox_id="inbox-123",
        webhook_url="https://api.example.com/webhook/email",
    )
except WebhookRegistrationError as e:
    logger.warning(f"Webhook registration failed: {e}")
    # Fall back to polling
    from backend.services.email import get_email_polling_service

    polling = get_email_polling_service()
    await polling.start_polling(...)
```

#### `EmailPollingTimeoutError`

Email polling timed out waiting for response.

**Inherits from:** `EmailPollingError` → `EmailError`

**When raised:**

- No email received within timeout period
- Polling service timeout handler

**Example:**

```python
from backend.services.email import EmailPollingTimeoutError

try:
    # This is typically caught internally by polling service
    # but can be raised explicitly
    raise EmailPollingTimeoutError("No email received within 60 minutes")
except EmailPollingTimeoutError as e:
    logger.warning(f"Polling timeout: {e}")
    # Notify user or escalate
```

#### `EmailExtractionError`

Failed to extract content from email.

**Inherits from:** `EmailError`

**When raised:**

- Regex pattern doesn't match
- Invalid JSON in email body
- Extraction mode errors

**Example:**

```python
from backend.services.email import extract_email_content, EmailExtractionError

try:
    content = extract_email_content(
        email_body="No JSON here",
        extract_mode="json",
    )
except EmailExtractionError as e:
    logger.warning(f"Content extraction failed: {e}")
    # Fall back to full body
    content = email_body
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.email import (
    get_email_manager,
    EmailError,
    EmailSendError,
    EmailConfigurationError,
    InboxCreationError,
)
import logging

logger = logging.getLogger(__name__)


async def send_workflow_notification(
        to_address: str,
        subject: str,
        body: str,
):
    """
    Send workflow notification with comprehensive error handling.

    Returns:
        Dict with success status and message_id or error
    """
    try:
        manager = get_email_manager()

        # Send email
        result = await manager.send_email(
            from_address="noreply@agenticstudio.ai",
            to_address=to_address,
            subject=subject,
            body=body,
        )

        logger.info(f"Email sent successfully: {result.get('id')}")
        return {"success": True, "message_id": result.get("id")}

    except EmailConfigurationError as e:
        # Configuration errors - likely setup issue
        logger.error(f"Email configuration error: {e}")
        return {
            "success": False,
            "error": "Email service not configured",
            "details": str(e),
        }

    except EmailSendError as e:
        # Send errors - may be transient, could retry
        logger.error(f"Failed to send email: {e}")
        return {
            "success": False,
            "error": "Failed to send email",
            "details": str(e),
            "retryable": True,
        }

    except EmailError as e:
        # Other email errors
        logger.error(f"Email service error: {e}")
        return {
            "success": False,
            "error": "Email service error",
            "details": str(e),
        }

    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error sending email: {e}")
        return {
            "success": False,
            "error": "Unexpected error",
            "details": str(e),
        }
```

**Fallback Pattern (Webhook → Polling):**

```python
from backend.services.email import (
    get_email_manager,
    get_email_polling_service,
    WebhookRegistrationError,
)


async def setup_email_response_handling(
        inbox_id: str,
        execution_id: str,
        checkpoint_id: str,
        db_execution_id: int,
        webhook_url: str,
):
    """
    Setup email response handling with webhook fallback to polling.
    """
    manager = get_email_manager()

    try:
        # Try webhook first
        webhook = await manager.register_webhook(
            inbox_id=inbox_id,
            webhook_url=webhook_url,
        )
        logger.info(f"Webhook registered: {webhook.webhook_id}")
        return {"method": "webhook", "webhook_id": webhook.webhook_id}

    except WebhookRegistrationError as e:
        # Fall back to polling
        logger.warning(f"Webhook registration failed, using polling: {e}")

        polling_service = get_email_polling_service()
        await polling_service.start_polling(
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            inbox_id=inbox_id,
            db_execution_id=db_execution_id,
            interval_seconds=30,
            timeout_minutes=60,
        )

        return {"method": "polling", "interval": 30, "timeout": 60}
```

---

## Integration Patterns

### Integration with API Layer

The email service integrates with FastAPI routes for REST API access:

**Example from [backend/api/email/routes.py](../../../backend/api/email/routes.py):**

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.services.email import get_email_manager, EmailError
from pydantic import BaseModel

router = APIRouter(prefix="/api/email", tags=["email"])


class SendEmailRequest(BaseModel):
    to_address: str
    subject: str
    body: str
    html_body: str = None


class SendEmailResponse(BaseModel):
    success: bool
    message_id: str = None
    error: str = None


@router.post("/send", response_model=SendEmailResponse)
async def send_email_endpoint(request: SendEmailRequest) -> SendEmailResponse:
    """
    Send an email via the email service.

    Args:
        request: Email send request

    Returns:
        Send result with message ID
    """
    try:
        manager = get_email_manager()

        result = await manager.send_email(
            from_address="noreply@agenticstudio.ai",
            to_address=request.to_address,
            subject=request.subject,
            body=request.body,
            html_body=request.html_body,
        )

        return SendEmailResponse(
            success=True,
            message_id=result.get("id"),
        )

    except EmailError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}",
        )


@router.post("/inbox/create")
async def create_inbox_endpoint(expires_in_minutes: int = 60):
    """Create a temporary email inbox."""
    try:
        manager = get_email_manager()
        inbox = await manager.create_inbox(expires_in_minutes=expires_in_minutes)

        return {
            "inbox_id": inbox.inbox_id,
            "email_address": inbox.email_address,
            "expires_at": inbox.expires_at.isoformat(),
        }

    except EmailError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create inbox: {str(e)}",
        )
```

### Integration with Workflow Nodes

Email service integrates with workflow node executors:

**Example from [backend/services/nodes/executors/email.py](../../../backend/services/nodes/executors/email.py):**

```python
from backend.services.email import get_email_manager, EmailSendError
from backend.services.workflow.state import WorkflowState


class EmailNodeExecutor:
    """Executor for EMAIL_SEND nodes."""

    async def execute(
            self,
            node_data: dict,
            state: WorkflowState,
            execution_id: str,
    ) -> dict:
        """
        Execute email send node.

        Args:
            node_data: Node configuration
            state: Workflow state
            execution_id: Execution ID

        Returns:
            Execution result
        """
        # Extract email parameters from node config or state
        to_address = self._resolve_field(node_data.get("to"), state)
        subject = self._resolve_field(node_data.get("subject"), state)
        body = self._resolve_field(node_data.get("body"), state)
        html_body = self._resolve_field(node_data.get("html_body"), state)

        try:
            manager = get_email_manager()

            # Send email
            result = await manager.send_email(
                from_address="noreply@agenticstudio.ai",
                to_address=to_address,
                subject=subject,
                body=body,
                html_body=html_body,
            )

            return {
                "success": True,
                "message_id": result.get("id"),
                "to": to_address,
                "subject": subject,
            }

        except EmailSendError as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _resolve_field(self, field_config: dict, state: WorkflowState) -> str:
        """Resolve field from state or direct value."""
        if not field_config:
            return ""

        if field_config.get("type") == "direct":
            return field_config.get("value", "")

        if field_config.get("type") == "from_state":
            path = field_config.get("path", "")
            return state.get(path, "")

        return ""
```

### Integration with Checkpoint Service

Email service integrates with checkpoint handling:

**Example from checkpoint flow:**

```python
from backend.services.email import (
    get_email_manager,
    get_email_polling_service,
)
from backend.services.execution.checkpoint import CheckpointHandler


async def handle_email_checkpoint(
        execution_id: str,
        checkpoint_id: str,
        db_execution_id: int,
        email_config: dict,
):
    """
    Handle email checkpoint - send email and await response.

    Args:
        execution_id: Workflow execution ID
        checkpoint_id: Checkpoint node ID
        db_execution_id: Database execution ID
        email_config: Email configuration from node
    """
    manager = get_email_manager()

    # Create inbox for response
    inbox = await manager.create_inbox(expires_in_minutes=120)

    # Send email with reply-to address
    result = await manager.send_workflow_email(
        workflow_id=email_config["workflow_id"],
        execution_id=execution_id,
        to_address=email_config["to_address"],
        subject=email_config["subject"],
        body=email_config["body"],
        html_body=email_config.get("html_body"),
    )

    # Start polling for response (fallback if webhook fails)
    polling_service = get_email_polling_service()
    await polling_service.start_polling(
        execution_id=execution_id,
        checkpoint_id=checkpoint_id,
        inbox_id=inbox.inbox_id,
        db_execution_id=db_execution_id,
        interval_seconds=30,
        timeout_minutes=120,
    )

    logger.info(
        f"Email checkpoint setup complete: "
        f"inbox={inbox.email_address}, reply_to={result['reply_to']}"
    )
```

### Dependency Flow

```
┌─────────────────────────────────────────────┐
│          Application Layer                   │
│  ┌─────────────┐        ┌────────────────┐  │
│  │  API Routes │        │ Node Executors │  │
│  └──────┬──────┘        └────────┬───────┘  │
└─────────┼───────────────────────┼──────────┘
          │                       │
          │    ┌──────────────────┘
          │    │
          ▼    ▼
┌──────────────────────────┐
│   Email Service          │
│   (EmailManager)         │
└─────────┬────────────────┘
          │
          ├─────────────┬──────────────┐
          │             │              │
          ▼             ▼              ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Database  │  │  WebSocket │  │  Provider  │
│  Service   │  │  Service   │  │   APIs     │
└────────────┘  └────────────┘  └────────────┘
```

**Services this module depends on:**

- [Database Service](database.md) - Session management, model queries
- [WebSocket Service](websocket.md) - Real-time notifications

**Services that depend on this module:**

- Email API Routes - REST endpoints for email operations
- Email Node Executor - Workflow node for sending emails
- Checkpoint Service - Email-based checkpoint handling
- Notification systems - General email notifications

### Common Integration Patterns

#### Pattern 1: Send Notification Email

```python
from backend.services.email import get_email_manager, EmailSendError


async def send_notification(user_email: str, notification: dict):
    """Send notification email to user."""
    manager = get_email_manager()

    try:
        result = await manager.send_email(
            from_address="notifications@agenticstudio.ai",
            to_address=user_email,
            subject=notification["subject"],
            body=notification["body"],
            html_body=notification.get("html_body"),
        )

        logger.info(f"Notification sent to {user_email}: {result.get('id')}")
        return True

    except EmailSendError as e:
        logger.error(f"Failed to send notification: {e}")
        return False
```

#### Pattern 2: Workflow Email with Response

```python
from backend.services.email import (
    get_email_manager,
    get_email_polling_service,
)


async def workflow_email_checkpoint(
        execution_id: str,
        checkpoint_id: str,
        db_execution_id: int,
        workflow_id: str,
        recipient: str,
):
    """Send email and await response in workflow."""
    manager = get_email_manager()

    # Create inbox
    inbox = await manager.create_inbox(expires_in_minutes=240)

    # Send tracked email
    result = await manager.send_workflow_email(
        workflow_id=workflow_id,
        execution_id=execution_id,
        to_address=recipient,
        subject="Approval Required",
        body="Please reply to this email with APPROVE or REJECT",
    )

    # Start polling for response
    polling = get_email_polling_service()
    await polling.start_polling(
        execution_id=execution_id,
        checkpoint_id=checkpoint_id,
        inbox_id=inbox.inbox_id,
        db_execution_id=db_execution_id,
        interval_seconds=60,
        timeout_minutes=240,
    )

    return {
        "inbox_address": inbox.email_address,
        "reply_to": result["reply_to"],
        "message_id": result["id"],
    }
```

#### Pattern 3: Batch Email Sending

```python
from backend.services.email import get_email_manager
import asyncio


async def send_batch_emails(recipients: list, template: dict):
    """Send emails to multiple recipients."""
    manager = get_email_manager()

    async def send_one(recipient):
        try:
            result = await manager.send_email(
                from_address=template["from"],
                to_address=recipient,
                subject=template["subject"],
                body=template["body"],
                html_body=template.get("html_body"),
            )
            return {"recipient": recipient, "success": True, "message_id": result.get("id")}
        except Exception as e:
            return {"recipient": recipient, "success": False, "error": str(e)}

    # Send concurrently with rate limiting
    results = []
    for i in range(0, len(recipients), 10):  # Batch of 10
        batch = recipients[i:i + 10]
        batch_results = await asyncio.gather(*[send_one(r) for r in batch])
        results.extend(batch_results)
        await asyncio.sleep(1)  # Rate limit: 1 second between batches

    return results
```

---

## Usage Examples

### Example 1: Basic Email Sending

Complete end-to-end example of basic email sending:

```python
from backend.services.email import get_email_manager, EmailSendError
import asyncio


async def send_welcome_email():
    """Send a welcome email to a new user."""

    # Step 1: Get email manager
    manager = get_email_manager()

    # Step 2: Prepare email content
    to_address = "newuser@example.com"
    subject = "Welcome to AgenticStudio!"
    body = """
    Hello!

    Welcome to AgenticStudio. We're excited to have you on board.

    Get started by creating your first workflow at:
    https://app.agenticstudio.ai/workflows/new

    Best regards,
    The AgenticStudio Team
    """

    html_body = """
    <html>
      <body>
        <h1>Welcome to AgenticStudio!</h1>
        <p>We're excited to have you on board.</p>
        <p>
          <a href="https://app.agenticstudio.ai/workflows/new">
            Create your first workflow
          </a>
        </p>
        <p>Best regards,<br/>The AgenticStudio Team</p>
      </body>
    </html>
    """

    # Step 3: Send email
    try:
        result = await manager.send_email(
            from_address="welcome@agenticstudio.ai",
            to_address=to_address,
            subject=subject,
            body=body,
            html_body=html_body,
        )

        # Step 4: Process result
        print(f"Email sent successfully!")
        print(f"Message ID: {result.get('id')}")
        print(f"To: {to_address}")

        return {"success": True, "message_id": result.get("id")}

    except EmailSendError as e:
        print(f"Failed to send email: {e}")
        return {"success": False, "error": str(e)}


# Run the example
if __name__ == "__main__":
    result = asyncio.run(send_welcome_email())
    print(f"Result: {result}")
```

### Example 2: Email Checkpoint with Response

Complete example showing email checkpoint workflow:

```python
from backend.services.email import (
    get_email_manager,
    get_email_polling_service,
    extract_email_content,
    EmailError,
)
import asyncio


async def approval_workflow_example():
    """
    Example workflow that sends approval email and awaits response.
    """

    # Workflow context
    workflow_id = "approval-workflow-123"
    execution_id = "exec-456"
    db_execution_id = 789
    checkpoint_id = "approval-checkpoint"

    manager = get_email_manager()
    polling_service = get_email_polling_service()

    try:
        # Step 1: Create temporary inbox for responses
        print("Creating inbox for responses...")
        inbox = await manager.create_inbox(expires_in_minutes=120)
        print(f"Inbox created: {inbox.email_address}")
        print(f"Expires at: {inbox.expires_at}")

        # Step 2: Send approval request email
        print("\nSending approval request email...")
        result = await manager.send_workflow_email(
            workflow_id=workflow_id,
            execution_id=execution_id,
            to_address="approver@example.com",
            subject="Approval Required: Purchase Order #12345",
            body="""
            Dear Approver,

            A new purchase order requires your approval:

            Purchase Order: #12345
            Amount: $5,000.00
            Vendor: Example Corp

            Please reply to this email with one of:
            - APPROVE
            - REJECT

            This request will expire in 2 hours.

            Best regards,
            AgenticStudio Workflow System
            """,
            html_body="""
            <html>
              <body>
                <h2>Approval Required</h2>
                <p>A new purchase order requires your approval:</p>
                <ul>
                  <li><strong>Purchase Order:</strong> #12345</li>
                  <li><strong>Amount:</strong> $5,000.00</li>
                  <li><strong>Vendor:</strong> Example Corp</li>
                </ul>
                <p>Please reply to this email with <strong>APPROVE</strong> or <strong>REJECT</strong>.</p>
                <p><em>This request will expire in 2 hours.</em></p>
              </body>
            </html>
            """,
        )

        print(f"Email sent: {result.get('id')}")
        print(f"Reply-to address: {result.get('reply_to')}")

        # Step 3: Start polling for response
        print("\nStarting email polling for response...")
        await polling_service.start_polling(
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            inbox_id=inbox.inbox_id,
            db_execution_id=db_execution_id,
            interval_seconds=30,
            timeout_minutes=120,
        )

        print("Polling started. Waiting for email response...")
        print(f"Checking inbox every 30 seconds for up to 120 minutes")

        # Step 4: Wait for polling to complete (in real workflow, this is async)
        # In production, the workflow would pause here and resume when email arrives

        return {
            "success": True,
            "inbox_id": inbox.inbox_id,
            "inbox_address": inbox.email_address,
            "message_id": result.get("id"),
            "reply_to": result.get("reply_to"),
        }

    except EmailError as e:
        print(f"Error in approval workflow: {e}")
        return {"success": False, "error": str(e)}


# Run the example
if __name__ == "__main__":
    result = asyncio.run(approval_workflow_example())
    print(f"\nWorkflow setup complete: {result}")
```

### Example 3: Custom Content Extraction

Show realistic email content extraction:

```python
from backend.services.email import (
    extract_email_content,
    EmailExtractionError,
    EXTRACT_MODE_FULL_BODY,
    EXTRACT_MODE_REGEX,
    EXTRACT_MODE_JSON,
)


def content_extraction_examples():
    """Demonstrate various content extraction modes."""

    # Example 1: Full body extraction
    print("=== Example 1: Full Body Extraction ===")
    email_body = """
    Hi there,

    I approve this request. Please proceed.

    Thanks,
    John
    """

    content = extract_email_content(email_body, extract_mode=EXTRACT_MODE_FULL_BODY)
    print(f"Full body: {content}")

    # Example 2: Regex extraction for approval status
    print("\n=== Example 2: Regex Extraction ===")
    email_body = """
    Subject: Re: Approval Required

    Status: APPROVED

    Comments: Looks good to me. Please proceed with the purchase.
    """

    try:
        # Extract just the status
        status = extract_email_content(
            email_body,
            extract_mode=EXTRACT_MODE_REGEX,
            extraction_pattern=r"Status:\s*(\w+)",
        )
        print(f"Extracted status: {status}")  # Output: APPROVED

    except EmailExtractionError as e:
        print(f"Extraction failed: {e}")

    # Example 3: JSON extraction
    print("\n=== Example 3: JSON Extraction ===")
    email_body = """
    Here's the data you requested:

    {
      "approved": true,
      "amount": 5000.00,
      "approver": "john@example.com",
      "comments": "Approved with conditions"
    }

    Let me know if you need anything else.
    """

    try:
        data = extract_email_content(email_body, extract_mode=EXTRACT_MODE_JSON)
        print(f"Extracted JSON: {data}")
        print(f"Approved: {data['approved']}")
        print(f"Amount: ${data['amount']}")

    except EmailExtractionError as e:
        print(f"JSON extraction failed: {e}")

    # Example 4: Multiple patterns
    print("\n=== Example 4: Multiple Field Extraction ===")
    email_body = """
    Approval Details:
    Decision: APPROVED
    Amount: $5,000.00
    Approver: john@example.com
    Date: 2025-01-15
    """

    # Extract decision
    decision = extract_email_content(
        email_body,
        extract_mode=EXTRACT_MODE_REGEX,
        extraction_pattern=r"Decision:\s*(\w+)",
    )

    # Extract amount
    amount = extract_email_content(
        email_body,
        extract_mode=EXTRACT_MODE_REGEX,
        extraction_pattern=r"Amount:\s*\$?([\d,]+\.?\d*)",
    )

    # Extract approver
    approver = extract_email_content(
        email_body,
        extract_mode=EXTRACT_MODE_REGEX,
        extraction_pattern=r"Approver:\s*([\w.]+@[\w.]+)",
    )

    print(f"Decision: {decision}")
    print(f"Amount: ${amount}")
    print(f"Approver: {approver}")


# Run examples
if __name__ == "__main__":
    content_extraction_examples()
```

### Example 4: Testing Email Service

Show how to use the service in tests:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.email import (
    EmailManager,
    EmailServiceProvider,
    EmailSendError,
    reset_email_manager,
)
from backend.services.email.schemas import EmailInbox
from datetime import datetime, timedelta


class MockEmailProvider(EmailServiceProvider):
    """Mock email provider for testing."""

    def __init__(self):
        self.sent_emails = []
        self.created_inboxes = []

    async def create_inbox(self, expires_in_minutes: int = 60):
        inbox = EmailInbox(
            inbox_id="test-inbox-123",
            email_address="test@example.com",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
        )
        self.created_inboxes.append(inbox)
        return inbox

    async def delete_inbox(self, inbox_id: str) -> bool:
        return True

    async def send_email(self, from_address, to_address, subject, body, html_body=None, reply_to=None):
        email_data = {
            "from": from_address,
            "to": to_address,
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "reply_to": reply_to,
        }
        self.sent_emails.append(email_data)
        return {"id": "msg-123", "status": "sent"}

    async def register_webhook(self, inbox_id, webhook_url, event_types=None):
        pass

    async def unregister_webhook(self, webhook_id):
        return True

    async def get_emails(self, inbox_id, limit=10):
        return []

    def validate_webhook_signature(self, payload, signature, secret=None):
        return True


@pytest.fixture
def mock_provider():
    """Fixture for mock email provider."""
    return MockEmailProvider()


@pytest.fixture
def email_manager(mock_provider):
    """Fixture for email manager with mock provider."""
    reset_email_manager()  # Reset singleton
    return EmailManager(provider=mock_provider)


@pytest.mark.asyncio
async def test_send_email_basic(email_manager, mock_provider):
    """Test basic email sending."""
    result = await email_manager.send_email(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test Email",
        body="This is a test email",
    )

    assert result["id"] == "msg-123"
    assert result["status"] == "sent"
    assert len(mock_provider.sent_emails) == 1

    sent = mock_provider.sent_emails[0]
    assert sent["to"] == "recipient@example.com"
    assert sent["subject"] == "Test Email"


@pytest.mark.asyncio
async def test_create_inbox(email_manager, mock_provider):
    """Test inbox creation."""
    inbox = await email_manager.create_inbox(expires_in_minutes=120)

    assert inbox.inbox_id == "test-inbox-123"
    assert inbox.email_address == "test@example.com"
    assert len(mock_provider.created_inboxes) == 1


@pytest.mark.asyncio
async def test_send_email_error_handling(email_manager, mock_provider):
    """Test email sending error handling."""
    # Mock provider to raise error
    mock_provider.send_email = AsyncMock(side_effect=EmailSendError("Network error"))

    with pytest.raises(EmailSendError) as exc_info:
        await email_manager.send_email(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            subject="Test",
            body="Test",
        )

    assert "Network error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_workflow_email(email_manager, mock_provider):
    """Test workflow-tracked email."""
    result = await email_manager.send_workflow_email(
        workflow_id="wf-123",
        execution_id="exec-456",
        to_address="user@example.com",
        subject="Approval Required",
        body="Please approve",
    )

    assert "execution_id" in result
    assert result["execution_id"] == "exec-456"
    assert len(mock_provider.sent_emails) == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Performance Considerations

### Performance Characteristics

**Email Sending:**

- **Complexity:** O(1) per email
- **I/O Bound:** Network latency to provider API (100-500ms typical)
- **Throughput:** Limited by provider rate limits (Mailgun: ~100-1000 emails/hour depending on plan)

**Inbox Creation:**

- **Complexity:** O(1)
- **I/O Bound:** Provider API call (50-200ms)
- **Memory:** Minimal, only stores metadata

**Email Polling:**

- **Complexity:** O(n) where n is number of active polls
- **I/O Bound:** Periodic API calls every interval_seconds
- **Resource Usage:** One asyncio task per active poll

**Content Extraction:**

- **Complexity:**
  - Full body: O(1)
  - Regex: O(n) where n is body length
  - JSON: O(n) for parsing
- **CPU Bound:** Regex and JSON parsing
- **Memory:** O(n) for email body

### Optimisation Tips

#### Tip 1: Batch Email Sending

**Problem:**

```python
# Inefficient: Sequential sending
for recipient in recipients:
    await manager.send_email(
        from_address="noreply@example.com",
        to_address=recipient,
        subject="Notification",
        body="Message",
    )
# Takes: N * send_time (e.g., 100 emails * 200ms = 20 seconds)
```

**Solution:**

```python
# Efficient: Concurrent sending with rate limiting
import asyncio


async def send_batch(recipients, template, batch_size=10):
    """Send emails in concurrent batches."""
    manager = get_email_manager()
    results = []

    for i in range(0, len(recipients), batch_size):
        batch = recipients[i:i + batch_size]

        # Send batch concurrently
        batch_results = await asyncio.gather(*[
            manager.send_email(
                from_address=template["from"],
                to_address=recipient,
                subject=template["subject"],
                body=template["body"],
            )
            for recipient in batch
        ], return_exceptions=True)

        results.extend(batch_results)

        # Rate limit: Wait between batches
        if i + batch_size < len(recipients):
            await asyncio.sleep(1)

    return results


# Usage
recipients = ["user1@example.com", "user2@example.com", ...]
results = await send_batch(recipients, template, batch_size=10)
# Takes: (N / batch_size) * (send_time + 1s) (e.g., 10 batches * 1.2s = 12 seconds)
```

#### Tip 2: Caching Provider Instance

**Problem:**

```python
# Inefficient: Creating new manager/provider each time
async def send_notification(to: str, message: str):
    manager = EmailManager()  # New instance every call
    await manager.send_email(...)
```

**Solution:**

```python
# Efficient: Use singleton pattern
from backend.services.email import get_email_manager


async def send_notification(to: str, message: str):
    manager = get_email_manager()  # Reuses singleton instance
    await manager.send_email(...)
```

#### Tip 3: Webhook vs Polling

**When to use each:**

```python
# Webhook (preferred): Real-time, low resource usage
if webhook_available and not_local_development:
    webhook = await manager.register_webhook(
        inbox_id=inbox.inbox_id,
        webhook_url="https://api.example.com/webhook/email",
    )
    # No polling overhead, instant response

# Polling (fallback): Works everywhere, but uses more resources
else:
    await polling_service.start_polling(
        execution_id=execution_id,
        inbox_id=inbox.inbox_id,
        interval_seconds=60,  # Longer interval = less load
        timeout_minutes=120,
    )
```

**Optimisation:**

- Use webhooks when possible (instant, no overhead)
- For polling, use longer intervals if response time isn't critical
- Stop polling immediately when response received

### Async/Await Support

The email service is fully async throughout:

```python
from backend.services.email import get_email_manager
import asyncio


async def async_email_example():
    """Example using async/await."""
    manager = get_email_manager()

    # All operations are async
    inbox = await manager.create_inbox(expires_in_minutes=60)

    result = await manager.send_email(
        from_address="noreply@example.com",
        to_address="user@example.com",
        subject="Async Email",
        body="This is sent asynchronously",
    )

    emails = await manager.get_emails(inbox_id=inbox.inbox_id, limit=10)

    await manager.delete_inbox(inbox_id=inbox.inbox_id)

    return result


# Run in async context
result = asyncio.run(async_email_example())
```

**Benefits:**

- Non-blocking I/O for network calls
- Concurrent email operations
- Efficient resource usage
- Compatible with FastAPI and async frameworks

### Connection Pooling

HTTP connections are managed by `aiohttp` with connection pooling:

```python
# In MailgunProvider (example)
async with aiohttp.ClientSession() as session:
    # Session handles connection pooling automatically
    async with session.post(url, auth=self.auth, data=data) as response:
        return await response.json()
```

**Optimisation for high-volume sending:**

```python
from backend.services.email import MailgunProvider
import aiohttp


class OptimizedMailgunProvider(MailgunProvider):
    """Optimized Mailgun provider with persistent session."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = None

    async def get_session(self):
        """Get or create persistent session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=100)  # Connection pool
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def send_email(self, ...):
        """Send email using persistent session."""
        session = await self.get_session()
        # Use session for request...

    async def close(self):
        """Close session on shutdown."""
        if self._session:
            await self._session.close()
```

### Batch Operations

**Email retrieval batching:**

```python
# Retrieve multiple inboxes efficiently
async def get_all_inbox_emails(inbox_ids: list) -> dict:
    """Get emails from multiple inboxes concurrently."""
    manager = get_email_manager()

    results = await asyncio.gather(*[
        manager.get_emails(inbox_id=inbox_id, limit=10)
        for inbox_id in inbox_ids
    ])

    return {
        inbox_id: emails
        for inbox_id, emails in zip(inbox_ids, results)
    }
```

---

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.email import (
    EmailManager,
    EmailServiceProvider,
    get_email_manager,
    reset_email_manager,
)
from backend.services.email.schemas import EmailInbox
from datetime import datetime, timedelta


@pytest.fixture
def mock_provider():
    """Mock email provider for testing."""
    provider = AsyncMock(spec=EmailServiceProvider)

    # Mock create_inbox
    provider.create_inbox.return_value = EmailInbox(
        inbox_id="test-inbox",
        email_address="test@example.com",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )

    # Mock send_email
    provider.send_email.return_value = {
        "id": "msg-123",
        "status": "sent",
    }

    return provider


@pytest.fixture
def email_manager(mock_provider):
    """Email manager with mocked provider."""
    reset_email_manager()
    return EmailManager(provider=mock_provider)


@pytest.mark.asyncio
async def test_create_inbox(email_manager, mock_provider):
    """Test inbox creation."""
    inbox = await email_manager.create_inbox(expires_in_minutes=60)

    assert inbox.inbox_id == "test-inbox"
    assert inbox.email_address == "test@example.com"
    mock_provider.create_inbox.assert_called_once_with(60)


@pytest.mark.asyncio
async def test_send_email(email_manager, mock_provider):
    """Test email sending."""
    result = await email_manager.send_email(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test",
        body="Test body",
    )

    assert result["id"] == "msg-123"
    assert result["status"] == "sent"
    mock_provider.send_email.assert_called_once()


@pytest.mark.asyncio
async def test_workflow_email(email_manager, mock_provider):
    """Test workflow-tracked email."""
    # Mock provider's workflow method
    provider.send_email_with_workflow_id = AsyncMock(return_value={
        "id": "msg-456",
        "workflow_id": "wf-123",
        "execution_id": "exec-456",
        "reply_to": "workflow-exec-456@example.com",
    })

    result = await email_manager.send_workflow_email(
        workflow_id="wf-123",
        execution_id="exec-456",
        to_address="user@example.com",
        subject="Approval",
        body="Please approve",
    )

    assert result["execution_id"] == "exec-456"
    assert "reply_to" in result
```

### Mocking Dependencies

```python
@pytest.mark.asyncio
@patch('backend.services.email.manager.EmailServiceFactory')
async def test_manager_with_factory_mock(mock_factory):
    """Test manager with mocked factory."""
    # Setup mock
    mock_provider = AsyncMock(spec=EmailServiceProvider)
    mock_factory.create_provider.return_value = mock_provider

    # Create manager
    reset_email_manager()
    manager = get_email_manager()

    # Verify factory was called
    mock_factory.create_provider.assert_called_once()


@pytest.mark.asyncio
@patch('backend.services.email.polling.processor.SessionLocal')
async def test_email_processor_with_db_mock(mock_session_local):
    """Test email processor with mocked database."""
    from backend.services.email import EmailResponseProcessor
    from backend.services.email.schemas import EmailMessage

    # Mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Mock checkpoint node
    mock_checkpoint = MagicMock()
    mock_checkpoint.status = "paused"
    mock_checkpoint.node_metadata = {}
    mock_db.query.return_value.filter.return_value.first.return_value = mock_checkpoint

    # Test email processing
    email = EmailMessage(
        id="msg-123",
        from_address="user@example.com",
        to_addresses=["workflow@example.com"],
        subject="Approval",
        body="APPROVED",
    )

    success = await EmailResponseProcessor.process_email_response(
        execution_id="exec-123",
        checkpoint_id="checkpoint-456",
        db_execution_id=789,
        email=email,
    )

    assert success is True
    mock_db.commit.assert_called_once()
```

### Integration Testing

```python
import pytest
from backend.services.email import (
    get_email_manager,
    MailgunProvider,
    reset_email_manager,
)
import os


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("MAILGUN_API_KEY"),
    reason="MAILGUN_API_KEY not set",
)
@pytest.mark.asyncio
async def test_mailgun_integration():
    """Integration test with real Mailgun API."""
    # Use real Mailgun provider
    reset_email_manager()
    provider = MailgunProvider(
        api_key=os.getenv("MAILGUN_API_KEY"),
        domain=os.getenv("MAILGUN_DOMAIN", "sandbox.mailgun.org"),
    )
    manager = EmailManager(provider=provider)

    # Test inbox creation
    inbox = await manager.create_inbox(expires_in_minutes=30)
    assert inbox.inbox_id is not None
    assert "@" in inbox.email_address

    # Test email sending
    result = await manager.send_email(
        from_address=f"test@{provider.domain}",
        to_address=inbox.email_address,
        subject="Integration Test",
        body="This is an integration test email",
    )
    assert "id" in result

    # Cleanup
    await manager.delete_inbox(inbox_id=inbox.inbox_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_polling_integration():
    """Integration test for email polling."""
    from backend.services.email import get_email_polling_service

    polling = get_email_polling_service()

    # Start polling
    await polling.start_polling(
        execution_id="test-exec",
        checkpoint_id="test-checkpoint",
        inbox_id="test-inbox",
        db_execution_id=1,
        interval_seconds=10,
        timeout_minutes=1,
    )

    # Verify polling is active
    assert polling.is_polling("test-exec")

    # Stop polling
    polling.stop_polling("test-exec")
    assert not polling.is_polling("test-exec")
```

---

## Best Practices

### Do's

✅ **Use the singleton pattern for EmailManager**

```python
from backend.services.email import get_email_manager

# Good: Use singleton
manager = get_email_manager()
```

**Why:** Ensures consistent configuration and reuses provider connections.

---

✅ **Handle errors gracefully with specific exception types**

```python
from backend.services.email import (
    get_email_manager,
    EmailSendError,
    EmailConfigurationError,
)

try:
    manager = get_email_manager()
    result = await manager.send_email(...)
except EmailConfigurationError as e:
    logger.error(f"Email not configured: {e}")
    # Notify admin to configure email service
except EmailSendError as e:
    logger.warning(f"Email send failed: {e}")
    # Retry or fallback to alternative notification
```

**Why:** Enables appropriate error handling and recovery strategies.

---

✅ **Use workflow-tracked emails for checkpoint responses**

```python
# Good: Workflow-tracked email with unique reply-to
result = await manager.send_workflow_email(
    workflow_id=workflow_id,
    execution_id=execution_id,
    to_address=recipient,
    subject="Approval Required",
    body="Please reply with APPROVE or REJECT",
)

# Reply-to address is unique: workflow-exec456@domain.com
# Enables automatic response routing
```

**Why:** Enables automatic workflow resumption from email responses.

---

✅ **Provide both plain text and HTML email bodies**

```python
# Good: Both formats
await manager.send_email(
    from_address="noreply@example.com",
    to_address="user@example.com",
    subject="Welcome",
    body="Welcome to AgenticStudio!\n\nGet started: https://app.agenticstudio.ai",
    html_body="""
        <h1>Welcome to AgenticStudio!</h1>
        <p><a href="https://app.agenticstudio.ai">Get started</a></p>
    """,
)
```

**Why:** Ensures compatibility with all email clients and better user experience.

---

✅ **Clean up inboxes after use**

```python
# Good: Cleanup in finally block
inbox = None
try:
    inbox = await manager.create_inbox(expires_in_minutes=60)
    # Use inbox...
finally:
    if inbox:
        await manager.delete_inbox(inbox_id=inbox.inbox_id)
```

**Why:** Prevents inbox quota issues and resource leaks.

---

✅ **Use appropriate extraction modes for content**

```python
# Good: Use regex for structured data
approval_status = extract_email_content(
    email.body,
    extract_mode="regex",
    extraction_pattern=r"Decision:\s*(APPROVED|REJECTED)",
)

# Good: Use JSON for API-style responses
data = extract_email_content(
    email.body,
    extract_mode="json",
)
```

**Why:** Extracts only needed data, reducing noise and improving reliability.

### Don'ts

❌ **Don't create new EmailManager instances repeatedly**

```python
# Bad: Creating new instances
async def send_notification(to: str, message: str):
    manager = EmailManager()  # Creates new provider each time
    await manager.send_email(...)


# Good: Use singleton
from backend.services.email import get_email_manager


async def send_notification(to: str, message: str):
    manager = get_email_manager()  # Reuses singleton
    await manager.send_email(...)
```

**Why:** Creates unnecessary provider instances and loses connection pooling benefits.

---

❌ **Don't ignore email sending errors**

```python
# Bad: Silent failure
try:
    await manager.send_email(...)
except:
    pass  # Email not sent, no one knows

# Good: Log and handle errors
from backend.services.email import EmailSendError

try:
    result = await manager.send_email(...)
    logger.info(f"Email sent: {result.get('id')}")
except EmailSendError as e:
    logger.error(f"Email send failed: {e}")
    # Notify admin, retry, or use fallback notification method
```

**Why:** Email failures should be visible for debugging and user notifications.

---

❌ **Don't use full_body extraction for structured responses**

```python
# Bad: Full body when you need specific data
email_response = extract_email_content(
    email.body,
    extract_mode="full_body",
)
# Returns entire email including signatures, quotes, etc.
# Then parse manually...

# Good: Use regex or JSON extraction
approval = extract_email_content(
    email.body,
    extract_mode="regex",
    extraction_pattern=r"(APPROVE|REJECT)",
)
```

**Why:** Regex/JSON extraction is more reliable and reduces parsing errors.

---

❌ **Don't hardcode API keys in code**

```python
# Bad: Hardcoded credentials
provider = MailgunProvider(
    api_key="key-abc123def456",  # Security risk!
    domain="mg.example.com",
)

# Good: Use environment variables
provider = MailgunProvider()  # Reads from env vars
# Or explicitly:
provider = MailgunProvider(
    api_key=os.getenv("MAILGUN_API_KEY"),
    domain=os.getenv("MAILGUN_DOMAIN"),
)
```

**Why:** Hardcoded credentials are security risks and can't be changed per environment.

---

❌ **Don't poll with very short intervals**

```python
# Bad: Polling too frequently
await polling_service.start_polling(
    execution_id=execution_id,
    inbox_id=inbox_id,
    interval_seconds=5,  # Too frequent!
    ...
)

# Good: Use reasonable intervals or webhooks
# Webhooks (preferred):
webhook = await manager.register_webhook(...)

# Polling (fallback):
await polling_service.start_polling(
    execution_id=execution_id,
    inbox_id=inbox_id,
    interval_seconds=30,  # Reasonable interval
    ...
)
```

**Why:** Short polling intervals waste resources and may hit rate limits. Use webhooks when possible.

---

❌ **Don't send emails in loops without rate limiting**

```python
# Bad: No rate limiting
for user in users:
    await manager.send_email(
        to_address=user.email,
        subject="Notification",
        body="...",
    )
# May hit rate limits!

# Good: Batch with rate limiting
import asyncio

for i in range(0, len(users), 10):
    batch = users[i:i + 10]
    await asyncio.gather(*[
        manager.send_email(
            to_address=user.email,
            subject="Notification",
            body="...",
        )
        for user in batch
    ])
    await asyncio.sleep(1)  # Rate limit between batches
```

**Why:** Prevents rate limiting and provider throttling.

---

## Related Documentation

### Related Services

- [Database Service](database.md) - Database session management and ORM models
- [WebSocket Service](websocket.md) - Real-time notifications for email events
- [Checkpoint Service](checkpoint.md) - Workflow checkpoint handling
- [Workflow Service](workflow.md) - Workflow execution and state management

### Related API Modules

- [Email API](../../../backend/api/email/email.md) - REST endpoints for email operations
- [Checkpoint API](../../../backend/api/checkpoints/checkpoints.md) - Checkpoint management endpoints

### Architecture Documentation

- [Service Layer Architecture](../architecture/services.md) - Overall service layer design
- [Workflow Execution](../architecture/execution.md) - How workflows execute with checkpoints

### External Documentation

- [Mailgun API Documentation](https://documentation.mailgun.com/en/latest/) - Mailgun provider API reference
- [MailSlurp Documentation](https://docs.mailslurp.com/) - MailSlurp provider API reference
- [aiohttp Documentation](https://docs.aiohttp.org/) - Async HTTP client library

---

## Summary

The Email service provides comprehensive email capabilities for AgenticStudio workflows, enabling both outbound email
sending and inbound email response handling. It supports multiple email providers through a flexible architecture, with
Mailgun and MailSlurp implementations included.

The service is built around a modular provider system using the Factory pattern, allowing easy addition of new email
providers. The high-level `EmailManager` provides a simple, unified interface for all email operations, while the
underlying providers handle provider-specific implementations.

For workflow checkpoints, the service offers two mechanisms for receiving email responses: webhooks (preferred for
real-time responses with minimal overhead) and polling (fallback for environments where webhooks aren't available). The
`EmailPollingService` manages background polling tasks, while `EmailResponseProcessor` handles email content extraction
and workflow resumption.

**Key Features:**

- Multiple provider support (Mailgun, MailSlurp) with extensible provider system
- Async/await throughout for non-blocking I/O
- Temporary inbox creation for receiving responses
- Workflow-tracked emails with execution context
- Flexible content extraction (full body, regex, JSON, stripped text)
- Webhook and polling support for email responses
- Comprehensive error handling with specific exception types
- Type-safe operations with Pydantic schemas
- Singleton pattern for consistent configuration

**Primary Use Cases:**

- Sending notification emails from workflows
- Email-based workflow checkpoints awaiting user responses
- Approval workflows with email interaction
- Extracting structured data from email replies
- Human-in-the-loop workflows requiring email communication

**When to Use This Service:**

- Workflows need to send email notifications
- Workflows require email responses for continuation (checkpoints)
- Approval processes involve email-based decisions
- External systems communicate via email
- User interactions need email-based confirmations

The service integrates seamlessly with the AgenticStudio workflow execution system, database layer, and WebSocket
notifications to provide a complete email-based workflow interaction system.
