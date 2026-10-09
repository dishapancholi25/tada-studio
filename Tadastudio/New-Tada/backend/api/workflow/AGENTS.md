# Workflow Publishing API Module

## Overview

The Workflow Publishing API module provides functionality for publishing AgenticStudio workflows as public HTTP endpoints.
It enables users to expose their workflows as REST APIs with configurable authentication, rate limiting, CORS policies,
and webhook callbacks.

**Location:** [backend/api/workflow/](../../backend/api/workflow/)

**Base Path:** `/api/publish`

**Primary Responsibilities:**

- Publishing workflows as HTTP endpoints with custom URLs
- Managing authentication tokens for published workflows
- Configuring CORS policies and rate limiting
- Tracking access statistics and usage
- Managing publication lifecycle (publish, update, unpublish)
- Webhook integration for execution completion callbacks

## Architecture

### Module Structure

```
backend/api/workflow/
├── __init__.py           # Module initialisation
└── publishing.py         # Publication endpoints (485 lines)

backend/services/workflow/publishing/
├── __init__.py          # Service exports
├── service.py           # WorkflowPublishingService (483 lines)
├── helpers.py           # Graph validation and loading helpers
├── legacy.py            # Legacy token cleanup utilities
└── responses.py         # Response formatting utilities

backend/models/workflow/
└── publication.py       # WorkflowPublicationConfig dataclass
```

**Key Files:**

- **publishing.py** - All API routes for workflow publication management
- **service.py** - Database service layer for published workflows and auth tokens
- **publication.py** - Configuration model for publication settings

### Design Pattern

The Workflow Publishing API follows a **service-oriented architecture**:

```
HTTP Request
    ↓
Route Handler (publishing.py)
    ↓
WorkflowPublishingService (service.py)
    ↓
Database (PublishedWorkflow, WorkflowAuthToken, WorkflowAccessLog)
    ↓
In-Memory Graph Updates (backwards compatibility)
```

**Request Flow:**

1. Route handler validates request and extracts user info
2. Service layer performs database operations
3. Graph configuration updated in-memory for legacy support
4. Response built with endpoint URLs and tokens

**Benefits:**

- Clean separation between HTTP handling and business logic
- Database persistence for publication state
- Backwards compatibility with in-memory graph storage
- Reusable service layer for token validation

## Authentication & Authorisation

### Authentication

Most endpoints require authentication via **OAuth2-Proxy**. The token retrieval endpoint is public for convenience.

**User Extraction Pattern:**

```python
from ..auth.dependencies import get_current_user

@publish_router.post("/workflow/{graph_name}")
async def publish_workflow(
    graph_name: str,
    request: PublishWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    # Extract user identifier (email or sub claim)
    user_identifier = current_user.get("email") or current_user.get("sub")
```

**Headers Injected by OAuth2-Proxy:**

- `X-Forwarded-User` - Username or email
- `X-Forwarded-Email` - User email
- `X-Forwarded-Preferred-Username` - Display name

### Authorisation

**User-Scoped Publishing:**

- Users can only publish workflows they created
- Workflow ownership verified via database lookup
- Published workflows remain accessible to users with workflow membership
- Authentication tokens are scoped to specific workflows

**Implementation Example:**

```python
# Verify user owns the workflow before publishing
workflow = db.query(Workflow).filter(
    Workflow.name == graph_name,
    Workflow.created_by_user_id == user_id
).first()

if not workflow:
    raise ValueError("Workflow not found or you don't have permission to publish it")
```

## API Endpoints

### Publication Management

#### `POST /api/publish/workflow/{graph_name}`

Publish a workflow as a public HTTP endpoint with configurable authentication and access controls.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Name of the workflow to publish (URL-encoded)

**Request Body:**

```json
{
  "custom_slug": "customer-onboarding",
  "description": "Customer onboarding workflow with validation and CRM integration",
  "require_authentication": true,
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
  },
  "allowed_origins": [
    "https://myapp.example.com",
    "https://admin.example.com"
  ],
  "webhook_url": "https://myapp.example.com/webhooks/workflow-complete",
  "input_schema": {
    "type": "object",
    "properties": {
      "customer_email": {"type": "string", "format": "email"},
      "company_name": {"type": "string"},
      "plan_tier": {"type": "string", "enum": ["starter", "professional", "enterprise"]}
    },
    "required": ["customer_email", "company_name"]
  }
}
```

**Field Descriptions:**

- `custom_slug` (optional) - Custom URL path for the endpoint. If omitted, uses graph_name
- `description` (optional) - Human-readable description for documentation
- `require_authentication` (default: true) - Whether to require auth token for access
- `rate_limit` (optional) - Rate limiting configuration object
- `allowed_origins` (optional) - CORS allowed origins list
- `webhook_url` (optional) - URL to POST execution completion events
- `input_schema` (optional) - JSON Schema for input validation

**Response:**

```json
{
  "success": true,
  "message": "Workflow 'customer-onboarding-v2' published successfully",
  "graph_name": "customer-onboarding-v2",
  "endpoint_url": "https://api.agenticstudio.example.com/api/execute/published/customer-onboarding",
  "authentication_token": "vF3kL9mN2pQ8rT5wX7yZ0aB4cD6eF1gH3iJ5kL7mN9oP2qR4sT6uV8wX0yZ2aB4c",
  "publication_config": {
    "is_published": true,
    "custom_slug": "customer-onboarding",
    "description": "Customer onboarding workflow with validation and CRM integration",
    "require_authentication": true,
    "published_at": "2025-10-21T14:32:18.742Z",
    "access_count": 0,
    "rate_limit": {
      "requests_per_minute": 60,
      "requests_per_hour": 1000
    },
    "allowed_origins": [
      "https://myapp.example.com",
      "https://admin.example.com"
    ],
    "webhook_url": "https://myapp.example.com/webhooks/workflow-complete"
  }
}
```

**Use Cases:**

- Publishing a completed workflow for production use
- Creating API endpoints for external integrations
- Exposing workflows to mobile or web applications
- Setting up webhook notifications for async processing

**Behaviour:**

- Creates database record in `published_workflows` table
- Generates secure authentication token if required
- Updates in-memory graph configuration for backwards compatibility
- Validates workflow structure before publishing
- Checks for custom slug conflicts across all published workflows
- Updates existing publication if already published

**Validation:**

- Graph must exist and be owned by the user
- Custom slug must be unique if provided
- Workflow must be valid for execution
- Rate limit values must be positive integers
- Webhook URL must be valid HTTP/HTTPS URL
- Input schema must be valid JSON Schema

**Errors:**

- `400 Bad Request` - Custom slug conflict or invalid workflow
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Workflow doesn't exist
- `500 Internal Server Error` - Database or filesystem error

---

#### `GET /api/publish/workflow/{graph_name}`

Retrieve publication information and configuration for a workflow.

**Authentication:** None (public endpoint)

**Path Parameters:**

- `graph_name` - Name of the workflow (URL-encoded)

**Response:**

```json
{
  "graph_name": "customer-onboarding-v2",
  "is_published": true,
  "endpoint_url": "https://api.agenticstudio.example.com/api/execute/published/customer-onboarding",
  "custom_slug": "customer-onboarding",
  "description": "Customer onboarding workflow with validation and CRM integration",
  "require_authentication": true,
  "published_at": "2025-10-21T14:32:18.742Z",
  "last_accessed": "2025-10-21T16:45:22.113Z",
  "access_count": 247,
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
  },
  "allowed_origins": [
    "https://myapp.example.com",
    "https://admin.example.com"
  ],
  "webhook_url": "https://myapp.example.com/webhooks/workflow-complete"
}
```

**Use Cases:**

- Checking if a workflow is published before executing
- Retrieving endpoint URL for client configuration
- Viewing access statistics and usage metrics
- Verifying publication settings

**Behaviour:**

- Reads from in-memory graph configuration
- Returns default config if workflow exists but isn't published
- Constructs endpoint URL based on slug or graph name

**Errors:**

- `404 Not Found` - Workflow doesn't exist
- `500 Internal Server Error` - Graph loading error

---

#### `DELETE /api/publish/workflow/{graph_name}`

Unpublish a workflow, removing it from public access and revoking authentication tokens.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Name of the workflow to unpublish (URL-encoded)

**Response:**

```json
{
  "success": true,
  "message": "Workflow 'customer-onboarding-v2' unpublished successfully"
}
```

**Use Cases:**

- Removing workflow from production
- Temporarily disabling access during maintenance
- Decommissioning deprecated workflows
- Revoking access after security incident

**Behaviour:**

- Marks workflow as unpublished in database
- Deactivates all authentication tokens
- Updates in-memory graph configuration
- Cleans up legacy token files
- Does not delete the workflow itself

**Errors:**

- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Published workflow not found
- `500 Internal Server Error` - Database or filesystem error

---

#### `PUT /api/publish/workflow/{graph_name}`

Update publication settings for an already-published workflow.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Name of the workflow to update (URL-encoded)

**Request Body:**

```json
{
  "custom_slug": "customer-onboarding-v2",
  "description": "Updated customer onboarding workflow with enhanced validation",
  "require_authentication": true,
  "rate_limit": {
    "requests_per_minute": 100,
    "requests_per_hour": 5000
  },
  "allowed_origins": [
    "https://myapp.example.com",
    "https://admin.example.com",
    "https://partner.example.com"
  ],
  "webhook_url": "https://myapp.example.com/api/v2/webhooks/workflow-events"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Workflow 'customer-onboarding-v2' publication settings updated successfully",
  "graph_name": "customer-onboarding-v2",
  "endpoint_url": "https://api.agenticstudio.example.com/api/execute/published/customer-onboarding-v2",
  "authentication_token": "vF3kL9mN2pQ8rT5wX7yZ0aB4cD6eF1gH3iJ5kL7mN9oP2qR4sT6uV8wX0yZ2aB4c",
  "publication_config": {
    "is_published": true,
    "custom_slug": "customer-onboarding-v2",
    "description": "Updated customer onboarding workflow with enhanced validation",
    "require_authentication": true,
    "published_at": "2025-10-21T14:32:18.742Z",
    "last_accessed": "2025-10-21T16:45:22.113Z",
    "access_count": 247,
    "rate_limit": {
      "requests_per_minute": 100,
      "requests_per_hour": 5000
    },
    "allowed_origins": [
      "https://myapp.example.com",
      "https://admin.example.com",
      "https://partner.example.com"
    ],
    "webhook_url": "https://myapp.example.com/api/v2/webhooks/workflow-events"
  }
}
```

**Use Cases:**

- Updating rate limits based on usage patterns
- Adding new allowed CORS origins
- Changing webhook URL for new integrations
- Modifying workflow description for documentation
- Enabling/disabling authentication requirements

**Behaviour:**

- Updates configuration in database and in-memory graph
- Returns existing token if authentication still required
- Generates new token if authentication newly enabled
- Removes token if authentication disabled
- Updates graph timestamps

**Validation:**

- Workflow must already be published
- Same validation as publish endpoint

**Errors:**

- `400 Bad Request` - Invalid configuration
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Workflow not published
- `500 Internal Server Error` - Failed to save configuration

---

#### `GET /api/publish/workflows`

List all published workflows accessible to the authenticated user.

**Authentication:** Required

**Response:**

```json
{
  "success": true,
  "published_workflows": [
    {
      "graph_name": "customer-onboarding-v2",
      "is_published": true,
      "endpoint_url": "https://api.agenticstudio.example.com/api/execute/published/customer-onboarding",
      "custom_slug": "customer-onboarding",
      "description": "Customer onboarding workflow with validation and CRM integration",
      "require_authentication": true,
      "published_at": "2025-10-21T14:32:18.742Z",
      "last_accessed": "2025-10-21T16:45:22.113Z",
      "access_count": 247,
      "rate_limit": {
        "requests_per_minute": 60,
        "requests_per_hour": 1000
      },
      "allowed_origins": [
        "https://myapp.example.com"
      ],
      "webhook_url": "https://myapp.example.com/webhooks/workflow-complete"
    },
    {
      "graph_name": "data-processing-pipeline",
      "is_published": true,
      "endpoint_url": "https://api.agenticstudio.example.com/api/execute/published/data-pipeline",
      "custom_slug": "data-pipeline",
      "description": "Automated data processing and enrichment pipeline",
      "require_authentication": false,
      "published_at": "2025-10-15T09:15:42.331Z",
      "last_accessed": "2025-10-21T17:12:05.884Z",
      "access_count": 1523,
      "rate_limit": null,
      "allowed_origins": ["*"],
      "webhook_url": null
    }
  ],
  "total_count": 2
}
```

**Use Cases:**

- Dashboard display of all published workflows
- Inventory management for production endpoints
- Monitoring access patterns across workflows
- Identifying unused or heavily-used workflows

**Behaviour:**

- Queries database for workflows user created
- Includes workflows user has membership access to
- Returns complete publication configuration for each
- Sorted by publication date (most recent first)

**Errors:**

- `401 Unauthorized` - Missing or invalid authentication
- `500 Internal Server Error` - Database query error

---

### Token Management

#### `GET /api/publish/workflow/{graph_name}/token`

Retrieve the authentication token for a published workflow.

**Authentication:** None (public endpoint for convenience)

**Path Parameters:**

- `graph_name` - Name of the workflow (URL-encoded)

**Response:**

```json
{
  "success": true,
  "graph_name": "customer-onboarding-v2",
  "token": "vF3kL9mN2pQ8rT5wX7yZ0aB4cD6eF1gH3iJ5kL7mN9oP2qR4sT6uV8wX0yZ2aB4c",
  "created_at": "2025-10-21T14:32:18.742Z"
}
```

**Use Cases:**

- Retrieving token for client configuration
- Sharing access credentials with external systems
- Testing published endpoints
- Troubleshooting authentication issues

**Behaviour:**

- Looks up active authentication token from database
- Returns error if workflow doesn't require authentication
- Token is URL-safe base64 encoded (32 bytes = 43 characters)

**Errors:**

- `400 Bad Request` - Workflow doesn't require authentication
- `404 Not Found` - Published workflow or token not found
- `500 Internal Server Error` - Database error

---

#### `POST /api/publish/workflow/{graph_name}/token/regenerate`

Regenerate the authentication token for a published workflow, invalidating the previous token.

**Authentication:** None (public endpoint)

**Path Parameters:**

- `graph_name` - Name of the workflow (URL-encoded)

**Response:**

```json
{
  "success": true,
  "message": "Token regenerated for workflow 'customer-onboarding-v2'",
  "graph_name": "customer-onboarding-v2",
  "token": "aB2cD4eF6gH8iJ0kL1mN3oP5qR7sT9uV1wX3yZ5aB7cD9eF1gH3iJ5kL7mN9oP1q",
  "created_at": "2025-10-21T18:24:37.552Z"
}
```

**Use Cases:**

- Rotating credentials for security compliance
- Revoking access after token leak or compromise
- Periodic token rotation policies
- Resetting access after team member departure

**Behaviour:**

- Deactivates all existing tokens for the workflow
- Generates new secure token using `secrets.token_urlsafe(32)`
- Creates database record for new token
- Previous tokens immediately stop working

**Security Note:**
This endpoint is public for operational convenience. In production, consider adding authentication or implementing a
separate admin API for token management.

**Errors:**

- `400 Bad Request` - Workflow doesn't require authentication
- `404 Not Found` - Published workflow not found
- `500 Internal Server Error` - Failed to generate token

---

## Error Handling

### Error Response Format

All endpoints return consistent error responses:

```json
{
  "detail": "Workflow 'nonexistent-workflow' not found"
}
```

For 500 errors with exception details:

```json
{
  "detail": "Internal server error: Database connection timeout"
}
```

### Common Error Codes

**400 Bad Request:**

- Custom slug conflicts with existing workflow
- Invalid rate limit configuration
- Workflow doesn't require authentication (when requesting token)
- Invalid JSON schema in input_schema field

**401 Unauthorized:**

- Missing authentication headers
- Invalid or expired JWT token
- Token missing user identifier (email or sub claim)

**404 Not Found:**

- Workflow doesn't exist
- Published workflow not found
- User doesn't own the workflow
- Authentication token not found

**500 Internal Server Error:**

- Database connection failures
- Graph loading errors
- Filesystem errors when saving configuration
- Token generation failures

### Error Handling Example

```python
import requests

def publish_workflow(graph_name, config, auth_token):
    """Publish a workflow with proper error handling."""
    try:
        response = requests.post(
            f"https://api.agenticstudio.example.com/api/publish/workflow/{graph_name}",
            json=config,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        response.raise_for_status()

        result = response.json()
        print(f"✓ Published: {result['endpoint_url']}")
        if result.get('authentication_token'):
            print(f"✓ Auth Token: {result['authentication_token']}")
        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print(f"✗ Invalid configuration: {e.response.json()['detail']}")
        elif e.response.status_code == 401:
            print(f"✗ Authentication failed: {e.response.json()['detail']}")
        elif e.response.status_code == 404:
            print(f"✗ Workflow not found: {e.response.json()['detail']}")
        else:
            print(f"✗ Server error: {e.response.json()['detail']}")
        raise

    except requests.exceptions.RequestException as e:
        print(f"✗ Network error: {str(e)}")
        raise
```

## Integration with Services Layer

### Dependency Flow

```
Routes (publishing.py)
    ↓
WorkflowPublishingService (service.py)
    ↓
Database Models
    ├── PublishedWorkflow (publication records)
    ├── WorkflowAuthToken (authentication tokens)
    ├── WorkflowAccessLog (access tracking)
    ├── Workflow (workflow ownership)
    └── WorkflowMembership (access permissions)
    ↓
In-Memory Graph Storage (backwards compatibility)
```

### Example Integration

**Route Handler:**

```python
# In publishing.py
@publish_router.post("/workflow/{graph_name}")
async def publish_workflow(
    graph_name: str,
    request: PublishWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> PublishWorkflowResponse:
    user_identifier = get_user_identifier(current_user)

    # Validate graph before publishing
    graph = load_and_validate_unpublished_graph(graph_name)
    validate_graph_for_publishing(graph)

    # Delegate to service layer
    published_workflow = WorkflowPublishingService.publish_workflow(
        graph_name=graph_name,
        user_identifier=user_identifier,
        custom_slug=request.custom_slug,
        description=request.description,
        require_authentication=request.require_authentication,
        rate_limit=request.rate_limit,
        allowed_origins=request.allowed_origins,
        webhook_url=request.webhook_url,
        input_schema=request.input_schema,
    )

    # Get auth token if required
    auth_token = None
    if request.require_authentication:
        auth_token = WorkflowPublishingService.get_auth_token(graph_name)

    # Update in-memory graph for backwards compatibility
    ensure_publication_config(graph)
    sync_graph_config_from_request(graph, request)
    update_graph_timestamps(graph)
    save_graph_with_warning(graph)

    return PublishWorkflowResponse(...)
```

**Service Layer:**

```python
# In service.py
@staticmethod
def publish_workflow(
    graph_name: str,
    user_identifier: str,
    custom_slug: Optional[str] = None,
    ...
) -> PublishedWorkflow:
    with get_db() as db:
        # Verify ownership
        user_id = resolve_user_id(user_identifier, db)
        workflow = db.query(Workflow).filter(
            Workflow.name == graph_name,
            Workflow.created_by_user_id == user_id
        ).first()

        if not workflow:
            raise ValueError("Workflow not found or permission denied")

        # Check for existing publication
        existing = db.query(PublishedWorkflow).filter(
            PublishedWorkflow.graph_name == graph_name
        ).first()

        if existing:
            # Update existing
            existing.custom_slug = custom_slug
            existing.description = description
            ...
        else:
            # Create new publication
            published_workflow = PublishedWorkflow(...)
            db.add(published_workflow)

        # Ensure auth token exists if required
        if require_authentication:
            WorkflowPublishingService._ensure_auth_token(db, published_workflow)

        return published_workflow
```

### Services Used

**WorkflowPublishingService** (`backend/services/workflow/publishing/service.py`)

- Database persistence for published workflows
- Authentication token generation and validation
- Access logging and statistics tracking
- User permission verification

**GraphStorageService** (via helper functions)

- Loading workflow graphs from filesystem
- Validating graph structure for publishing
- Saving updated graph configurations
- User identifier resolution

**Helper Modules:**

- **helpers.py** - Graph validation, loading, and timestamp management
- **responses.py** - URL building and response formatting
- **legacy.py** - Legacy token file cleanup

## Usage Examples

### Complete Workflow Publishing Example

**Python Client:**

```python
import requests
from typing import Dict, Any, Optional

class AgenticStudioPublishingClient:
    """Client for AgenticStudio workflow publishing API."""

    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    def publish_workflow(
        self,
        graph_name: str,
        custom_slug: Optional[str] = None,
        description: str = "",
        require_auth: bool = True,
        allowed_origins: list = None,
        rate_limit: Dict[str, int] = None,
        webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish a workflow as a public endpoint."""
        config = {
            "custom_slug": custom_slug,
            "description": description,
            "require_authentication": require_auth,
            "allowed_origins": allowed_origins or [],
            "rate_limit": rate_limit,
            "webhook_url": webhook_url,
        }

        response = requests.post(
            f"{self.base_url}/api/publish/workflow/{graph_name}",
            json=config,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_publication_info(self, graph_name: str) -> Dict[str, Any]:
        """Get publication information for a workflow."""
        response = requests.get(
            f"{self.base_url}/api/publish/workflow/{graph_name}"
        )
        response.raise_for_status()
        return response.json()

    def update_publication(
        self,
        graph_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update publication settings."""
        response = requests.put(
            f"{self.base_url}/api/publish/workflow/{graph_name}",
            json=config,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def unpublish_workflow(self, graph_name: str) -> Dict[str, Any]:
        """Unpublish a workflow."""
        response = requests.delete(
            f"{self.base_url}/api/publish/workflow/{graph_name}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def list_published_workflows(self) -> Dict[str, Any]:
        """List all published workflows."""
        response = requests.get(
            f"{self.base_url}/api/publish/workflows",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_auth_token(self, graph_name: str) -> str:
        """Get authentication token for a published workflow."""
        response = requests.get(
            f"{self.base_url}/api/publish/workflow/{graph_name}/token"
        )
        response.raise_for_status()
        return response.json()["token"]

    def regenerate_token(self, graph_name: str) -> str:
        """Regenerate authentication token."""
        response = requests.post(
            f"{self.base_url}/api/publish/workflow/{graph_name}/token/regenerate"
        )
        response.raise_for_status()
        return response.json()["token"]


# Example usage
def main():
    client = AgenticStudioPublishingClient(
        base_url="https://api.agenticstudio.example.com",
        auth_token="your-jwt-token-here"
    )

    # 1. Publish a workflow
    print("Publishing workflow...")
    result = client.publish_workflow(
        graph_name="customer-onboarding-v2",
        custom_slug="customer-onboarding",
        description="Automated customer onboarding with validation",
        require_auth=True,
        allowed_origins=["https://myapp.example.com"],
        rate_limit={
            "requests_per_minute": 60,
            "requests_per_hour": 1000
        },
        webhook_url="https://myapp.example.com/webhooks/workflow-complete"
    )

    print(f"✓ Published at: {result['endpoint_url']}")
    print(f"✓ Auth token: {result['authentication_token']}")

    # 2. Get publication info
    print("\nFetching publication info...")
    info = client.get_publication_info("customer-onboarding-v2")
    print(f"✓ Access count: {info['access_count']}")
    print(f"✓ Last accessed: {info['last_accessed']}")

    # 3. List all published workflows
    print("\nListing published workflows...")
    workflows = client.list_published_workflows()
    print(f"✓ Total published workflows: {workflows['total_count']}")
    for wf in workflows['published_workflows']:
        print(f"  - {wf['graph_name']}: {wf['endpoint_url']}")

    # 4. Update publication settings
    print("\nUpdating rate limits...")
    client.update_publication(
        graph_name="customer-onboarding-v2",
        config={
            "custom_slug": "customer-onboarding",
            "description": "Automated customer onboarding with validation",
            "require_authentication": True,
            "allowed_origins": ["https://myapp.example.com"],
            "rate_limit": {
                "requests_per_minute": 120,  # Increased
                "requests_per_hour": 5000    # Increased
            }
        }
    )
    print("✓ Rate limits updated")

    # 5. Regenerate token (security rotation)
    print("\nRegenerating authentication token...")
    new_token = client.regenerate_token("customer-onboarding-v2")
    print(f"✓ New token: {new_token}")

    # 6. Unpublish when done
    print("\nUnpublishing workflow...")
    client.unpublish_workflow("customer-onboarding-v2")
    print("✓ Workflow unpublished")


if __name__ == "__main__":
    main()
```

**JavaScript/TypeScript Client:**

```typescript
interface PublicationConfig {
  custom_slug?: string;
  description?: string;
  require_authentication?: boolean;
  rate_limit?: {
    requests_per_minute?: number;
    requests_per_hour?: number;
  };
  allowed_origins?: string[];
  webhook_url?: string;
  input_schema?: Record<string, any>;
}

class AgenticStudioPublishingClient {
  constructor(
    private baseUrl: string,
    private authToken: string
  ) {}

  async publishWorkflow(
    graphName: string,
    config: PublicationConfig
  ): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/publish/workflow/${encodeURIComponent(graphName)}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Publishing failed: ${error.detail}`);
    }

    return response.json();
  }

  async getPublicationInfo(graphName: string): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/publish/workflow/${encodeURIComponent(graphName)}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get info: ${error.detail}`);
    }

    return response.json();
  }

  async listPublishedWorkflows(): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/publish/workflows`,
      {
        headers: {
          'Authorization': `Bearer ${this.authToken}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to list workflows: ${error.detail}`);
    }

    return response.json();
  }

  async getAuthToken(graphName: string): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/api/publish/workflow/${encodeURIComponent(graphName)}/token`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get token: ${error.detail}`);
    }

    const data = await response.json();
    return data.token;
  }

  async regenerateToken(graphName: string): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/api/publish/workflow/${encodeURIComponent(graphName)}/token/regenerate`,
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to regenerate token: ${error.detail}`);
    }

    const data = await response.json();
    return data.token;
  }
}

// Example usage
async function main() {
  const client = new AgenticStudioPublishingClient(
    'https://api.agenticstudio.example.com',
    'your-jwt-token-here'
  );

  try {
    // Publish workflow
    const result = await client.publishWorkflow(
      'customer-onboarding-v2',
      {
        custom_slug: 'customer-onboarding',
        description: 'Automated customer onboarding',
        require_authentication: true,
        allowed_origins: ['https://myapp.example.com'],
        rate_limit: {
          requests_per_minute: 60,
          requests_per_hour: 1000,
        },
      }
    );

    console.log('Published:', result.endpoint_url);
    console.log('Token:', result.authentication_token);

    // List published workflows
    const workflows = await client.listPublishedWorkflows();
    console.log(`Total workflows: ${workflows.total_count}`);

  } catch (error) {
    console.error('Error:', error.message);
  }
}
```

## Performance Considerations

### Endpoint Performance

**Fast (< 100ms):**

- `GET /api/publish/workflow/{graph_name}` - Reads from in-memory graph
- `GET /api/publish/workflow/{graph_name}/token` - Single database lookup

**Medium (100ms - 500ms):**

- `GET /api/publish/workflows` - Database query with joins
- `POST /api/publish/workflow/{graph_name}/token/regenerate` - Database write

**Slow (> 500ms):**

- `POST /api/publish/workflow/{graph_name}` - Graph validation + DB write + file I/O
- `PUT /api/publish/workflow/{graph_name}` - Graph loading + DB write + file I/O
- `DELETE /api/publish/workflow/{graph_name}` - DB write + file I/O + token cleanup

### Optimisation Tips

**1. Batch Publication Queries**

❌ **Bad:** Multiple sequential requests

```python
for workflow in workflow_names:
    info = get_publication_info(workflow)
    process(info)
```

✅ **Good:** Single batch request

```python
# Get all at once
all_workflows = list_published_workflows()
workflow_map = {wf['graph_name']: wf for wf in all_workflows['published_workflows']}

for workflow_name in workflow_names:
    info = workflow_map.get(workflow_name)
    if info:
        process(info)
```

**2. Cache Publication Info**

```python
import time
from functools import lru_cache

class CachedPublishingClient:
    def __init__(self, client):
        self.client = client
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def get_publication_info(self, graph_name: str):
        """Get publication info with caching."""
        cache_key = f"pub_info:{graph_name}"
        cached = self._cache.get(cache_key)

        if cached and time.time() - cached['timestamp'] < self._cache_ttl:
            return cached['data']

        # Fetch fresh data
        data = self.client.get_publication_info(graph_name)
        self._cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        return data
```

**3. Avoid Unnecessary Token Regeneration**

❌ **Bad:** Regenerating on every deployment

```python
# This invalidates existing tokens unnecessarily
new_token = regenerate_token(graph_name)
```

✅ **Good:** Only regenerate when needed

```python
# Only regenerate on security events or scheduled rotation
if should_rotate_token(last_rotation_date):
    new_token = regenerate_token(graph_name)
    notify_clients_of_token_change(new_token)
```

**4. Use Appropriate Rate Limits**

```python
# Configure based on expected load
rate_limit = {
    "requests_per_minute": 60,   # Burst capacity
    "requests_per_hour": 1000     # Sustained capacity
}

# For high-traffic endpoints
high_traffic_limit = {
    "requests_per_minute": 300,
    "requests_per_hour": 10000
}

# For internal-only endpoints
internal_limit = {
    "requests_per_minute": 1000,
    "requests_per_hour": 50000
}
```

### Caching Strategies

**Application-Level Caching:**

- Cache publication info for 5-10 minutes
- Invalidate cache on publication updates
- Use ETags for conditional requests (future enhancement)

**Database-Level Optimisation:**

- Index on `graph_name` and `custom_slug` in `published_workflows` table
- Index on `token` in `workflow_auth_tokens` table
- Denormalise access counts for faster reads

## Related Documentation

**Architecture Documentation:**

- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md) - Overall system design
- [Database Schema](../architecture/DATABASE_SCHEMA.md) - Database models and relationships

**Related API Modules:**

- [Graph API](../../../backend/api/graph/graph.md) - Workflow creation and management
- [Execution API](../../../backend/api/execution/execution.md) - Workflow execution endpoints
- [HTTP Execution API](../../../backend/api/http_execution/http_execution.md) - Published workflow execution

**Service Layer Documentation:**

- [Workflow Publishing Service](../../backend/services/workflow/publishing/) - Service implementation
- [Graph Storage Service](../../backend/services/graph/storage.py) - Graph persistence

**Security Documentation:**

- [Authentication Guide](../security/AUTHENTICATION.md) - OAuth2-Proxy setup
- [Rate Limiting](../security/RATE_LIMITING.md) - Rate limit implementation

## Summary

The Workflow Publishing API module provides a comprehensive solution for exposing AgenticStudio workflows as production HTTP
endpoints. It combines database-backed persistence with backwards-compatible in-memory graph storage to ensure
reliability and consistency.

The module handles the complete publication lifecycle from initial publishing through configuration updates to eventual
unpublishing. Authentication token management is built-in, with support for secure token generation, validation, and
rotation. The service layer enforces user-scoped access control, ensuring users can only publish and manage workflows
they own or have membership access to.

**Key Features:**

- **Flexible Publishing** - Custom URL slugs, descriptions, and input validation schemas
- **Robust Security** - Token-based authentication with automatic generation and rotation
- **Access Control** - CORS policies, rate limiting, and user-scoped permissions
- **Integration Ready** - Webhook callbacks for async execution completion events
- **Usage Tracking** - Access logs and statistics for monitoring and analytics
- **Database Persistence** - Reliable storage with backwards compatibility for legacy systems

**Primary Use Cases:**

- Exposing AI workflows as REST APIs for external integrations
- Creating public endpoints for mobile and web applications
- Building workflow marketplaces with published templates
- Implementing webhook-driven automation pipelines
- Managing production workflow deployments with proper access controls
