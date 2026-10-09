# Model Deployments API Module

## Overview

The Model Deployments API module provides comprehensive management of LLM (Large Language Model) deployments in
AgenticStudio. It enables configuration, testing, and management of multiple LLM providers including OpenAI, Anthropic, and
Azure OpenAI with secure credential storage and runtime configuration enrichment.

**Location:** [backend/api/model_deployments/](../../backend/api/model_deployments/)

**Base Path:** `/api/model-deployments`

**Primary Responsibilities:**

- CRUD operations for LLM deployment configurations
- Secure credential encryption and storage
- Default deployment management per provider
- LLM connection testing before production use
- Runtime configuration enrichment for workflow execution
- Multi-provider support (OpenAI, Anthropic, Azure OpenAI)
- Managed identity support for Azure deployments

## Architecture

### Module Structure

```
backend/api/model_deployments/
├── __init__.py          # Module exports (router)
├── routes.py            # REST API endpoints (258 lines)
├── schemas.py           # Pydantic request/response models (104 lines)
└── dependencies.py      # FastAPI dependency injection (34 lines)
```

**File Purposes:**

- ****init**.py** - Exports the FastAPI router for integration with main app
- **routes.py** - Defines 7 REST endpoints for deployment management
- **schemas.py** - Pydantic models for request validation and response serialisation
- **dependencies.py** - Singleton dependency injection for service instances

### Design Pattern

The Model Deployments API follows a **simplified service-oriented architecture**:

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
FastAPI Dependencies (dependencies.py)
    ↓
Service Layer (services/model_deployment/*)
    ├── ModelDeploymentService (CRUD operations)
    ├── CredentialEncryption (secure credential handling)
    ├── ConfigEnricher (runtime config enrichment)
    └── LLMFactory (connection testing)
    ↓
Database (PostgreSQL)
```

**Architecture Benefits:**

- **Thin routes:** Focus on HTTP concerns (request/response handling)
- **Direct service access:** No intermediate handler layer (simpler than graph module)
- **Singleton services:** Performance optimisation via `@lru_cache` dependency injection
- **Separation of concerns:** Encryption, validation, and serialisation in separate modules
- **Type safety:** Pydantic models ensure request/response validation

**Comparison to Graph Module:**
Unlike the graph module which uses a handler layer pattern (Routes → Handlers → Services), the model deployments module
uses direct service injection (Routes → Services) because:

- Simpler business logic (standard CRUD operations)
- No complex orchestration required
- System-level configuration (not user-scoped)

## Authentication & Authorisation

### Authentication

**Authentication:** None Required

The Model Deployments API does not require user authentication. This is a **system-level configuration API** typically
accessed by:

- System administrators during initial setup
- Internal services for runtime LLM configuration
- Deployment automation scripts
- Configuration management tools

**Security Considerations:**
While no authentication is enforced at the API level, access should be restricted via:

- Network-level controls (firewall rules, VPC restrictions)
- API gateway authentication
- Internal service mesh authentication

**Typical Deployment Pattern:**

```
Internet → API Gateway (auth) → Load Balancer → AgenticStudio API
                                                      ↓
                                          /api/model-deployments (internal)
```

### Authorisation

**No User-Scoped Data:**
Unlike user-facing APIs (graph, documents), model deployments are **global system resources**. All deployments are
visible to all services that can access the API.

**Default Deployment Scope:**
The `is_default` flag is scoped per model type, not per provider or user:

- Each model type (`llm`, `embedding`) can have at most one default deployment, regardless of provider
- Default deployments are used when workflows don't specify a deployment ID
- Setting `is_default=true` while another deployment of the same model type is already default is **rejected**
  (`409 Conflict`, `DefaultModelConflictError`) rather than silently clearing the previous default; the caller must
  unset the existing default first

## API Endpoints

### Deployment Retrieval (3 endpoints)

#### `GET /api/model-deployments/default`

Get the default model deployment for a specific model type.

**Authentication:** None

**Query Parameters:**

- `model_type` - Model type filter: 'llm' or 'embedding' (default: 'llm')
- `include_credentials` - Include decrypted credentials in response (default: false)

**Request Example:**

```bash
GET /api/model-deployments/default?model_type=llm&include_credentials=false
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "deploy-550e8400-e29b-41d4-a716-446655440000",
    "name": "production-gpt4",
    "description": "Production GPT-4 deployment for main workflows",
    "provider": "azure_openai",
    "model_name": "gpt-4-0613",
    "model_type": "llm",
    "display_name": "GPT-4 (Azure Production)",
    "settings": {
      "api_version": "2024-02-15-preview",
      "api_base": "https://myorg-openai.openai.azure.com/",
      "deployment_name": "gpt-4-prod",
      "use_managed_identity": false
    },
    "credentials": null,
    "has_credentials": true,
    "is_default": true,
    "is_active": true,
    "created_at": "2025-10-15T10:00:00Z",
    "updated_at": "2025-10-20T14:30:00Z"
  }
}
```

**Response (No Default Set):**

```json
{
  "success": true,
  "data": null
}
```

**Use Cases:**

- Frontend displaying current default LLM to users
- Services determining which LLM to use when no deployment specified
- Configuration validation during workflow creation
- Monitoring dashboards showing active default deployments

**Behaviour:**

- Returns the deployment marked `is_default=true` for the specified model type
- Only returns active deployments (`is_active=true`)
- Returns `null` in data field if no default is set
- Credentials are masked by default unless `include_credentials=true`

**Validation:**

- `model_type` must be 'llm' or 'embedding' (case-insensitive)
- Invalid model_type returns 400 error

**Errors:**

```json
{
  "detail": "Invalid settings: model_type must be 'llm' or 'embedding'"
}
```

---

#### `GET /api/model-deployments/`

List all active model deployments with optional filtering.

**Authentication:** None

**Query Parameters:**

- `include_credentials` - Include decrypted credentials (default: false)
- `model_type` - Filter by model type: 'llm' or 'embedding' (optional)

**Request Example:**

```bash
GET /api/model-deployments/?model_type=llm&include_credentials=false
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "deploy-550e8400-e29b-41d4-a716-446655440000",
      "name": "production-gpt4",
      "description": "Production GPT-4 deployment for main workflows",
      "provider": "azure_openai",
      "model_name": "gpt-4-0613",
      "model_type": "llm",
      "display_name": "GPT-4 (Azure Production)",
      "settings": {
        "api_version": "2024-02-15-preview",
        "api_base": "https://myorg-openai.openai.azure.com/",
        "deployment_name": "gpt-4-prod",
        "use_managed_identity": false
      },
      "credentials": null,
      "has_credentials": true,
      "is_default": true,
      "is_active": true,
      "created_at": "2025-10-15T10:00:00Z",
      "updated_at": "2025-10-20T14:30:00Z"
    },
    {
      "id": "deploy-661f9511-f3ac-52e5-b827-557766551111",
      "name": "development-claude",
      "description": "Claude 3.5 Sonnet for development testing",
      "provider": "anthropic",
      "model_name": "claude-3-5-sonnet-20241022",
      "model_type": "llm",
      "display_name": "Claude 3.5 Sonnet (Development)",
      "settings": {},
      "credentials": null,
      "has_credentials": true,
      "is_default": false,
      "is_active": true,
      "created_at": "2025-10-18T09:15:00Z",
      "updated_at": "2025-10-18T09:15:00Z"
    },
    {
      "id": "deploy-772fa622-g4bd-63f6-c938-668877662222",
      "name": "embeddings-ada",
      "description": "OpenAI Ada embeddings for document search",
      "provider": "openai",
      "model_name": "text-embedding-ada-002",
      "model_type": "embedding",
      "display_name": "OpenAI Ada Embeddings",
      "settings": {},
      "credentials": null,
      "has_credentials": true,
      "is_default": true,
      "is_active": true,
      "created_at": "2025-10-16T11:20:00Z",
      "updated_at": "2025-10-16T11:20:00Z"
    }
  ]
}
```

**Use Cases:**

- Frontend dropdown for selecting LLM deployments in workflows
- Configuration UI showing all available LLM options
- Monitoring dashboards displaying deployment inventory
- Export/backup of deployment configurations

**Behaviour:**

- Only returns active deployments (`is_active=true`)
- Results sorted alphabetically by name
- Filters by `model_type` if provided
- Credentials masked by default
- Empty array if no deployments match criteria

**Performance:**

- Fast: Simple database query with optional filter
- No external API calls
- Typically < 50ms response time

---

#### `GET /api/model-deployments/{deployment_id}`

Retrieve a single model deployment by ID.

**Authentication:** None

**Path Parameters:**

- `deployment_id` - UUID of the deployment to retrieve

**Query Parameters:**

- `include_credentials` - Include decrypted credentials (default: false)

**Request Example:**

```bash
GET /api/model-deployments/deploy-550e8400-e29b-41d4-a716-446655440000?include_credentials=true
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "deploy-550e8400-e29b-41d4-a716-446655440000",
    "name": "production-gpt4",
    "description": "Production GPT-4 deployment for main workflows",
    "provider": "azure_openai",
    "model_name": "gpt-4-0613",
    "model_type": "llm",
    "display_name": "GPT-4 (Azure Production)",
    "settings": {
      "api_version": "2024-02-15-preview",
      "api_base": "https://myorg-openai.openai.azure.com/",
      "deployment_name": "gpt-4-prod",
      "use_managed_identity": false
    },
    "credentials": {
      "api_key": "sk-abc123def456..."
    },
    "has_credentials": true,
    "is_default": true,
    "is_active": true,
    "created_at": "2025-10-15T10:00:00Z",
    "updated_at": "2025-10-20T14:30:00Z"
  }
}
```

**Use Cases:**

- Viewing full deployment details for editing
- Retrieving credentials for manual testing
- Configuration auditing and review
- Debugging workflow execution issues

**Behaviour:**

- Returns deployment regardless of `is_active` status (unlike list endpoint)
- Credentials decrypted only if `include_credentials=true`
- Returns 404 if deployment not found

**Errors:**

```json
{
  "detail": "Model deployment not found"
}
```

---

### Deployment Management (3 endpoints)

#### `POST /api/model-deployments/`

Create a new model deployment.

**Authentication:** None

**Request Body:**

```json
{
  "name": "production-gpt4",
  "model_type": "llm",
  "provider": "azure_openai",
  "model_name": "gpt-4-0613",
  "display_name": "GPT-4 (Azure Production)",
  "description": "Production GPT-4 deployment for main workflows",
  "settings": {
    "api_version": "2024-02-15-preview",
    "api_base": "https://myorg-openai.openai.azure.com/",
    "deployment_name": "gpt-4-prod",
    "use_managed_identity": false
  },
  "credentials": {
    "api_key": "sk-abc123def456..."
  },
  "is_default": true
}
```

**Request Body (Azure Managed Identity):**

```json
{
  "name": "azure-gpt4-managed-identity",
  "model_type": "llm",
  "provider": "azure_openai",
  "model_name": "gpt-4-0613",
  "display_name": "GPT-4 (Managed Identity)",
  "description": "Azure deployment using managed identity",
  "settings": {
    "api_version": "2024-02-15-preview",
    "api_base": "https://myorg-openai.openai.azure.com/",
    "deployment_name": "gpt-4-prod",
    "use_managed_identity": true
  },
  "credentials": {},
  "is_default": false
}
```

**Request Body (Anthropic):**

```json
{
  "name": "development-claude",
  "model_type": "llm",
  "provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "display_name": "Claude 3.5 Sonnet",
  "description": "Claude for development testing",
  "settings": {},
  "credentials": {
    "api_key": "sk-ant-api03-..."
  },
  "is_default": false
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "deploy-550e8400-e29b-41d4-a716-446655440000",
    "name": "production-gpt4",
    "description": "Production GPT-4 deployment for main workflows",
    "provider": "azure_openai",
    "model_name": "gpt-4-0613",
    "model_type": "llm",
    "display_name": "GPT-4 (Azure Production)",
    "settings": {
      "api_version": "2024-02-15-preview",
      "api_base": "https://myorg-openai.openai.azure.com/",
      "deployment_name": "gpt-4-prod",
      "use_managed_identity": false
    },
    "credentials": null,
    "has_credentials": true,
    "is_default": true,
    "is_active": true,
    "created_at": "2025-10-21T10:00:00Z",
    "updated_at": "2025-10-21T10:00:00Z"
  }
}
```

**Use Cases:**

- Initial system setup with LLM providers
- Adding new LLM models as they become available
- Configuring multiple deployments for different environments (dev/staging/prod)
- Setting up cost-optimised vs performance-optimised models

**Behaviour:**

- Encrypts credentials before storing in database
- Auto-generates UUID for deployment ID
- If `is_default=true`, verifies no other active deployment of the same model type is already default; rejects
  with `409 Conflict` (`DefaultModelConflictError`) instead of silently clearing an existing default
- Validates unique deployment name
- Normalises provider string to lowercase
- Sets `is_active=true` automatically

**Validation:**

- `name` - Required, must be unique across all deployments
- `provider` - Required, must be 'openai', 'azure_openai', or 'anthropic'
- `model_name` - Required, cannot be empty
- `model_type` - Defaults to 'llm', must be 'llm' or 'embedding'
- `credentials` - Either credentials OR managed identity required (Azure)
- `settings` - Provider-specific validation applies

**Provider-Specific Settings:**

**Azure OpenAI:**

```json
{
  "api_version": "2024-02-15-preview",
  "api_base": "https://myorg.openai.azure.com/",
  "deployment_name": "gpt-4-prod",
  "use_managed_identity": false
}
```

**OpenAI:**

```json
{
  "organization_id": "org-abc123"  // Optional
}
```

**Anthropic:**

```json
{}  // Typically no additional settings required
```

**Errors:**

```json
{
  "detail": "Model deployment with name 'production-gpt4' already exists"
}
```

```json
{
  "detail": "Invalid credential: api_key is required for provider 'anthropic'"
}
```

```json
{
  "detail": "Invalid settings: model_type must be 'llm' or 'embedding'"
}
```

---

#### `PUT /api/model-deployments/{deployment_id}`

Update an existing model deployment. Only provided fields are updated (partial update).

**Authentication:** None

**Path Parameters:**

- `deployment_id` - UUID of the deployment to update

**Request Body (Partial Update Example):**

```json
{
  "description": "Updated description for production deployment",
  "is_default": true
}
```

**Request Body (Update Credentials):**

```json
{
  "credentials": {
    "api_key": "sk-new-key-789..."
  }
}
```

**Request Body (Disable Deployment):**

```json
{
  "is_active": false
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "deploy-550e8400-e29b-41d4-a716-446655440000",
    "name": "production-gpt4",
    "description": "Updated description for production deployment",
    "provider": "azure_openai",
    "model_name": "gpt-4-0613",
    "model_type": "llm",
    "display_name": "GPT-4 (Azure Production)",
    "settings": {
      "api_version": "2024-02-15-preview",
      "api_base": "https://myorg-openai.openai.azure.com/",
      "deployment_name": "gpt-4-prod",
      "use_managed_identity": false
    },
    "credentials": null,
    "has_credentials": true,
    "is_default": true,
    "is_active": true,
    "created_at": "2025-10-15T10:00:00Z",
    "updated_at": "2025-10-21T11:45:00Z"
  }
}
```

**Use Cases:**

- Rotating API keys without recreating deployment
- Updating deployment descriptions
- Changing default deployment
- Temporarily disabling deployments without deletion
- Updating provider settings (e.g., API version changes)

**Behaviour:**

- Only updates fields included in request body
- Empty request body returns current deployment unchanged
- Setting `is_default=true` is rejected with `409 Conflict` (`DefaultModelConflictError`) if another active
  deployment of the same model type is already default; the existing default must be unset first
- Credentials are merged (can update individual keys)
- Name changes validated for uniqueness
- Returns 404 if deployment not found

**Validation:**

- `name` - If changed, must be unique
- `provider` - If changed, validated against supported providers
- `model_type` - If changed, must be 'llm' or 'embedding'
- `credentials` - Individual credentials can be updated or cleared

**Credential Merging:**

```json
// Existing credentials
{
  "api_key": "old-key",
  "organization_id": "org-123"
}

// Update request
{
  "credentials": {
    "api_key": "new-key"
  }
}

// Result
{
  "api_key": "new-key",
  "organization_id": "org-123"  // Preserved
}
```

**Clearing Credentials:**

```json
{
  "credentials": {
    "api_key": ""  // Empty string clears the credential
  }
}
```

**Errors:**

```json
{
  "detail": "Model deployment not found"
}
```

```json
{
  "detail": "Model deployment with name 'new-name' already exists"
}
```

---

#### `DELETE /api/model-deployments/{deployment_id}`

Delete a model deployment (soft or hard delete).

**Authentication:** None

**Path Parameters:**

- `deployment_id` - UUID of the deployment to delete

**Query Parameters:**

- `hard_delete` - Permanently delete the record (default: false)

**Request Example (Soft Delete):**

```bash
DELETE /api/model-deployments/deploy-550e8400-e29b-41d4-a716-446655440000?hard_delete=false
```

**Request Example (Hard Delete):**

```bash
DELETE /api/model-deployments/deploy-550e8400-e29b-41d4-a716-446655440000?hard_delete=true
```

**Response:**

```json
{
  "success": true
}
```

**Use Cases:**

- Removing deprecated deployments
- Cleaning up test deployments
- Temporarily disabling deployments (soft delete)
- Permanent removal for compliance (hard delete)

**Behaviour:**

**Soft Delete (`hard_delete=false`):**

- Sets `is_active=false`
- Sets `is_default=false`
- Record remains in database
- Deployment no longer appears in list endpoint
- Can be re-enabled by updating `is_active=true`

**Hard Delete (`hard_delete=true`):**

- Permanently removes record from database
- Cannot be recovered
- Use with caution in production

**Validation:**

- Deployment must exist (returns 404 if not found)

**Errors:**

```json
{
  "detail": "Model deployment not found"
}
```

**Best Practices:**

- Use soft delete for production (preserves audit trail)
- Use hard delete only for test data or compliance requirements
- Check for workflows using deployment before deleting

---

### Testing (1 endpoint)

#### `POST /api/model-deployments/{deployment_id}/test`

Test a model deployment's connection by making a test LLM call.

**Authentication:** None

**Path Parameters:**

- `deployment_id` - UUID of the deployment to test

**Request Body (Optional):**

```json
{
  "overrides": {
    "temperature": 0.5,
    "max_tokens": 100,
    "config": {
      "custom_setting": "value"
    }
  }
}
```

**Request Body (Empty - Use Defaults):**

```json
{}
```

**Response (Success):**

```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Successfully connected to azure_openai",
    "provider": "azure_openai",
    "model": "gpt-4-0613",
    "response": "Hello! I'm working correctly.",
    "latency_ms": 1247,
    "tokens_used": 8
  }
}
```

**Response (Failure):**

```json
{
  "success": false,
  "data": {
    "success": false,
    "message": "Connection failed",
    "provider": "azure_openai",
    "model": "gpt-4-0613",
    "error": "AuthenticationError: Invalid API key",
    "error_type": "AuthenticationError"
  }
}
```

**Use Cases:**

- Validating credentials after deployment creation
- Testing connectivity before setting as default
- Debugging connection issues
- Verifying API key rotation success
- Testing managed identity configuration

**Behaviour:**

- Sends a simple test prompt to the LLM: "Hello, please respond to confirm you're working."
- Measures response latency
- Returns full error details on failure
- Uses provided `overrides` if specified, otherwise uses defaults
- Does not modify deployment configuration
- Timeout: 30 seconds

**Test Process:**

1. Retrieves deployment configuration from database
2. Decrypts credentials
3. Enriches LLM config with deployment settings
4. Creates LLM instance via LLMFactory
5. Sends test message
6. Returns result with timing and token usage

**Validation:**

- Deployment must exist (404 if not found)
- Deployment must be active

**Errors:**

```json
{
  "detail": "Model deployment 'deploy-xyz' not found or inactive"
}
```

**Error Types in Response:**

- `AuthenticationError` - Invalid API key or credentials
- `RateLimitError` - API rate limit exceeded
- `TimeoutError` - Request timed out (> 30s)
- `InvalidRequestError` - Invalid model name or configuration
- `APIError` - General provider API error

**Performance:**

- Depends on LLM provider latency
- Typical: 500ms - 3000ms
- Timeout: 30s

---

## Error Handling

### Error Response Format

All errors follow FastAPI's standard HTTPException format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors (422):

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Common Error Codes

#### HTTP 400 - Bad Request

**DuplicateDeploymentNameError:**

```json
{
  "detail": "Model deployment with name 'production-gpt4' already exists"
}
```

**InvalidCredentialError:**

```json
{
  "detail": "Invalid credential: api_key is required for provider 'openai'"
}
```

**InvalidSettingsError:**

```json
{
  "detail": "Invalid settings: model_type must be 'llm' or 'embedding'"
}
```

**ModelDeploymentError (Generic):**

```json
{
  "detail": "Failed to create deployment: [specific error]"
}
```

**When 400 Occurs:**

- Creating deployment with duplicate name
- Missing required credentials
- Invalid provider name
- Invalid model type
- Credential validation failure
- Settings validation failure
- Encryption/decryption errors

#### HTTP 404 - Not Found

**DeploymentNotFoundError:**

```json
{
  "detail": "Model deployment not found"
}
```

```json
{
  "detail": "Model deployment 'deploy-550e8400-invalid' not found or inactive"
}
```

**When 404 Occurs:**

- Getting non-existent deployment by ID
- Updating non-existent deployment
- Deleting non-existent deployment
- Testing non-existent or inactive deployment

#### HTTP 422 - Validation Error

**Pydantic Validation Failure:**

```json
{
  "detail": [
    {
      "loc": ["body", "provider"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "model_type"],
      "msg": "value is not a valid enumeration member; permitted: 'llm', 'embedding'",
      "type": "type_error.enum",
      "ctx": {
        "enum_values": ["llm", "embedding"]
      }
    }
  ]
}
```

**When 422 Occurs:**

- Missing required fields in request body
- Invalid data types (e.g., string instead of boolean)
- Invalid enum values
- Malformed JSON

### Error Handling Example

**Python Client with Error Handling:**

```python
import requests
from typing import Optional, Dict, Any

class ModelDeploymentClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def create_deployment(self, deployment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a deployment with comprehensive error handling."""
        try:
            response = requests.post(
                f"{self.base_url}/api/model-deployments/",
                json=deployment_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                error_detail = e.response.json().get('detail', 'Unknown error')
                if 'already exists' in error_detail:
                    print(f"Deployment name conflict: {error_detail}")
                    # Could auto-retry with modified name
                    return None
                elif 'Invalid credential' in error_detail:
                    print(f"Credential validation failed: {error_detail}")
                    return None
                else:
                    print(f"Bad request: {error_detail}")
                    return None

            elif e.response.status_code == 404:
                print(f"Resource not found: {e.response.json().get('detail')}")
                return None

            elif e.response.status_code == 422:
                validation_errors = e.response.json().get('detail', [])
                print("Validation errors:")
                for error in validation_errors:
                    field = '.'.join(str(loc) for loc in error['loc'])
                    print(f"  {field}: {error['msg']}")
                return None

            else:
                print(f"HTTP error {e.response.status_code}: {e}")
                return None

        except requests.exceptions.Timeout:
            print("Request timed out")
            return None

        except requests.exceptions.ConnectionError:
            print("Connection error - is the service running?")
            return None

        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

# Usage example
client = ModelDeploymentClient("http://localhost:8000")

deployment = {
    "name": "production-gpt4",
    "provider": "azure_openai",
    "model_name": "gpt-4-0613",
    "credentials": {"api_key": "sk-..."},
    "settings": {
        "api_base": "https://myorg.openai.azure.com/",
        "deployment_name": "gpt-4-prod"
    }
}

result = client.create_deployment(deployment)
if result:
    print(f"Created deployment: {result['data']['id']}")
else:
    print("Failed to create deployment")
```

---

## Integration with Services Layer

### Dependency Flow

```
┌─────────────────────────────────────────────────────┐
│ routes.py                                           │
│ @router.post("/")                                   │
│ async def create_model_deployment(                  │
│     payload: ModelDeploymentCreate,                 │
│     service: ModelDeploymentService = Depends(...)  │
│ )                                                   │
└─────────────────┬───────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────┐
│ dependencies.py                                     │
│ @lru_cache(maxsize=1)                              │
│ def get_model_deployment_service():                │
│     return ModelDeploymentService()                │
└─────────────────┬───────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────┐
│ services/model_deployment/service.py                │
│ class ModelDeploymentService:                       │
│   - create_deployment(payload)                      │
│   - update_deployment(id, payload)                  │
│   - delete_deployment(id, hard_delete)              │
│   - list_deployments(include_credentials, filter)   │
│   - get_deployment(id, include_credentials)         │
│   - get_default_deployment(model_type)              │
│   - enrich_llm_config(llm_config)                   │
└─────────────────┬───────────────────────────────────┘
                  │
                  ├──→ CredentialEncryption (encryption.py)
                  │    - encrypt_credentials(credentials)
                  │    - decrypt_credentials(encrypted)
                  │    - merge_credentials(existing, updates)
                  │
                  ├──→ ConfigEnricher (enrichment.py)
                  │    - enrich_llm_config(db, llm_config)
                  │
                  ├──→ Validators (validators.py)
                  │    - validate_provider_string(provider)
                  │    - validate_model_type(model_type)
                  │    - validate_unique_name(db, name)
                  │    - validate_credentials_or_managed_identity(...)
                  │
                  └──→ Serializers (serializers.py)
                       - serialize_deployment(deployment, include_creds)
                       - serialize_deployments(deployments, include_creds)
```

### Example Integration

**Complete Request Flow:**

```python
# 1. HTTP Request arrives at route handler
@router.post("/")
async def create_model_deployment(
    payload: ModelDeploymentCreate,  # ← Pydantic validates request
    service: ModelDeploymentService = Depends(get_model_deployment_service),  # ← DI injects service
):
    try:
        # 2. Delegate to service layer
        deployment = service.create_deployment(payload.model_dump())

        # 3. Return response
        return {"success": True, "data": deployment}

    except ModelDeploymentError as exc:
        # 4. Handle service exceptions
        logger.error("[MODEL-DEPLOYMENT-API] Create error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

**Service Layer Processing:**

```python
# services/model_deployment/service.py
class ModelDeploymentService:
    def create_deployment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Validate payload structure
        validate_deployment_create_payload(payload)

        # 2. Validate and normalise individual fields
        provider = validate_provider_string(payload["provider"])
        model_type = validate_model_type(payload.get("model_type", "llm"))
        settings = normalize_settings(payload.get("settings"))

        # 3. Database transaction
        with get_db() as db:
            # 4. Validate unique name
            validate_unique_name(db, payload["name"])

            # 5. Encrypt credentials
            encrypted_credentials = self.credential_encryption.encrypt_credentials(
                payload.get("credentials")
            )

            # 6. Validate credentials or managed identity
            validate_credentials_or_managed_identity(
                provider, encrypted_credentials, settings
            )

            # 7. Create database record
            deployment = ModelDeployment(
                name=payload["name"].strip(),
                provider=provider,
                model_name=payload["model_name"].strip(),
                model_type=model_type,
                settings=settings,
                encrypted_credentials=encrypted_credentials,
                is_default=bool(payload.get("is_default", False)),
                is_active=True,
            )

            # 8. Handle default flag
            if deployment.is_default:
                self._clear_default(db, deployment.provider)

            # 9. Persist to database
            db.add(deployment)
            db.commit()
            db.refresh(deployment)

            # 10. Serialise response
            return serialize_deployment(
                deployment,
                include_credentials=False,
                credential_encryption=self.credential_encryption
            )
```

### Services Used

#### ModelDeploymentService

**Location:** [backend/services/model_deployment/service.py](../../services/model_deployment/service.py)

**Purpose:** Main business logic for deployment CRUD operations

**Key Methods:**

- `create_deployment(payload)` - Create new deployment with validation and encryption
- `update_deployment(id, payload)` - Partial update with credential merging
- `delete_deployment(id, hard_delete)` - Soft or hard deletion
- `list_deployments(include_credentials, model_type)` - List with filtering
- `get_deployment(id, include_credentials)` - Single deployment retrieval
- `get_default_deployment(model_type)` - Get default for model type
- `enrich_llm_config(llm_config)` - Runtime config enrichment for execution

**Usage in Routes:**

```python
service: ModelDeploymentService = Depends(get_model_deployment_service)
deployment = service.create_deployment(payload.model_dump())
```

---

#### CredentialEncryption

**Location:** [backend/services/model_deployment/encryption.py](../../services/model_deployment/encryption.py)

**Purpose:** Secure encryption and decryption of sensitive credentials

**Key Methods:**

- `encrypt_credentials(credentials)` - Encrypt credential dictionary
- `decrypt_credentials(encrypted)` - Decrypt credential dictionary
- `merge_credentials(existing, updates)` - Merge updated credentials with existing

**Encryption Approach:**

- Uses Fernet symmetric encryption (AES-128 in CBC mode)
- Each credential value encrypted individually
- Encryption key from environment variable `ENCRYPTION_KEY`
- Keys stored as base64-encoded encrypted strings in database JSON

**Example:**

```python
# Input
credentials = {"api_key": "sk-abc123", "org_id": "org-xyz"}

# After encryption
encrypted = {
    "api_key": "gAAAAABhX1Y2Z3...",  # ← Encrypted base64 string
    "org_id": "gAAAAABhX1Y2Z4..."
}
```

---

#### ConfigEnricher

**Location:** [backend/services/model_deployment/enrichment.py](../../services/model_deployment/enrichment.py)

**Purpose:** Enrich runtime LLM configurations with deployment settings and credentials

**Key Methods:**

- `enrich_llm_config(db, llm_config)` - Add deployment settings to base config

**Usage Pattern:**

```python
# Workflow specifies deployment ID
base_config = LLMConfig(
    provider="",  # ← Will be populated from deployment
    model_name="",  # ← Will be populated from deployment
    model_deployment_id="deploy-550e8400-..."
)

# Enricher fills in missing details
enriched_config = service.enrich_llm_config(base_config)

# Result
enriched_config = LLMConfig(
    provider="azure_openai",
    model_name="gpt-4-0613",
    model_deployment_id="deploy-550e8400-...",
    config={
        "api_base": "https://myorg.openai.azure.com/",
        "api_version": "2024-02-15-preview",
        "deployment_name": "gpt-4-prod",
        "api_key": "sk-decrypted-key-..."  # ← Decrypted at runtime
    }
)
```

**Benefits:**

- Centralised credential management (not embedded in workflows)
- Runtime credential decryption (not stored in workflow definitions)
- Easy credential rotation (update deployment, no workflow changes)

---

#### LLMFactory

**Location:** [backend/services/llm_models/factory.py](../../services/llm_models/factory.py)

**Purpose:** Create LLM instances and test connections

**Key Methods:**

- `test_llm_connection(llm_config)` - Test LLM connectivity and return result

**Usage in Test Endpoint:**

```python
factory: LLMFactory = Depends(get_llm_factory)

# Build config with deployment settings
enriched = service.enrich_llm_config(base_config)

# Test connection
test_result = factory.test_llm_connection(enriched)
```

**Test Process:**

1. Creates LLM instance from enriched config
2. Sends test message: "Hello, please respond to confirm you're working."
3. Measures latency and token usage
4. Catches provider-specific errors
5. Returns structured result

---

#### Validators

**Location:** [backend/services/model_deployment/validators.py](../../services/model_deployment/validators.py)

**Purpose:** Input validation and normalisation

**Key Functions:**

- `validate_provider_string(provider)` - Validate and normalise provider name
- `validate_model_type(model_type)` - Validate model type (llm/embedding)
- `validate_unique_name(db, name, exclude_id)` - Check name uniqueness
- `validate_credentials_or_managed_identity(provider, credentials, settings)` - Ensure auth present
- `normalize_settings(settings)` - Normalise settings dictionary

**Validation Rules:**

- Provider must be in: `['openai', 'azure_openai', 'anthropic']`
- Model type must be: `'llm'` or `'embedding'`
- Name must be unique (case-sensitive)
- Either credentials OR managed identity required (Azure only)

---

#### Serializers

**Location:** [backend/services/model_deployment/serializers.py](../../services/model_deployment/serializers.py)

**Purpose:** Format database models for API responses

**Key Functions:**

- `serialize_deployment(deployment, include_credentials, encryption)` - Serialise single deployment
- `serialize_deployments(deployments, include_credentials, encryption)` - Serialise list

**Serialisation Behaviour:**

- Credentials masked by default (`credentials: null`, `has_credentials: true`)
- Credentials decrypted if `include_credentials=true`
- Timestamps formatted as ISO 8601 strings
- Settings returned as-is (no decryption needed)

---

## Usage Examples

### Complete Deployment Management Example

This example demonstrates the full lifecycle of managing an LLM deployment: creation, testing, setting as default, and
usage in workflows.

**Python Example:**

```python
import requests
from typing import Dict, Any, Optional

class ModelDeploymentManager:
    """Client for managing model deployments."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def create_azure_deployment(
        self,
        name: str,
        model_name: str,
        api_base: str,
        deployment_name: str,
        api_key: str,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create an Azure OpenAI deployment."""
        payload = {
            "name": name,
            "provider": "azure_openai",
            "model_name": model_name,
            "model_type": "llm",
            "display_name": f"{model_name} (Azure)",
            "description": description or f"Azure deployment for {model_name}",
            "settings": {
                "api_base": api_base,
                "api_version": "2024-02-15-preview",
                "deployment_name": deployment_name,
                "use_managed_identity": False
            },
            "credentials": {
                "api_key": api_key
            },
            "is_default": is_default
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/model-deployments/",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            print(f"✓ Created deployment: {result['data']['id']}")
            return result['data']

        except requests.exceptions.HTTPError as e:
            error = e.response.json().get('detail', 'Unknown error')
            print(f"✗ Failed to create deployment: {error}")
            return None

    def test_deployment(self, deployment_id: str) -> bool:
        """Test deployment connection."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/model-deployments/{deployment_id}/test",
                json={},
                timeout=60  # Longer timeout for LLM call
            )
            response.raise_for_status()
            result = response.json()

            if result['data']['success']:
                latency = result['data'].get('latency_ms', 0)
                tokens = result['data'].get('tokens_used', 0)
                print(f"✓ Test successful (latency: {latency}ms, tokens: {tokens})")
                return True
            else:
                error = result['data'].get('error', 'Unknown error')
                print(f"✗ Test failed: {error}")
                return False

        except Exception as e:
            print(f"✗ Test error: {e}")
            return False

    def set_as_default(self, deployment_id: str) -> bool:
        """Set deployment as default."""
        try:
            response = self.session.put(
                f"{self.base_url}/api/model-deployments/{deployment_id}",
                json={"is_default": True},
                timeout=30
            )
            response.raise_for_status()
            print(f"✓ Set as default deployment")
            return True

        except Exception as e:
            print(f"✗ Failed to set default: {e}")
            return False

    def list_deployments(self, model_type: str = "llm") -> list:
        """List all active deployments."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/model-deployments/",
                params={"model_type": model_type},
                timeout=30
            )
            response.raise_for_status()
            deployments = response.json()['data']
            print(f"✓ Found {len(deployments)} deployments")
            return deployments

        except Exception as e:
            print(f"✗ Failed to list deployments: {e}")
            return []

    def get_default_deployment(self, model_type: str = "llm") -> Optional[Dict[str, Any]]:
        """Get default deployment."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/model-deployments/default",
                params={"model_type": model_type},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if result['data']:
                print(f"✓ Default deployment: {result['data']['name']}")
                return result['data']
            else:
                print("⚠ No default deployment set")
                return None

        except Exception as e:
            print(f"✗ Failed to get default: {e}")
            return None

    def rotate_api_key(self, deployment_id: str, new_api_key: str) -> bool:
        """Rotate API key for existing deployment."""
        try:
            # Update credentials
            response = self.session.put(
                f"{self.base_url}/api/model-deployments/{deployment_id}",
                json={"credentials": {"api_key": new_api_key}},
                timeout=30
            )
            response.raise_for_status()
            print(f"✓ Updated API key")

            # Test with new key
            return self.test_deployment(deployment_id)

        except Exception as e:
            print(f"✗ Failed to rotate key: {e}")
            return False


# ========================================
# Example Usage
# ========================================

if __name__ == "__main__":
    manager = ModelDeploymentManager()

    # Step 1: Create deployment
    print("\n=== Creating Azure GPT-4 Deployment ===")
    deployment = manager.create_azure_deployment(
        name="production-gpt4",
        model_name="gpt-4-0613",
        api_base="https://myorg-openai.openai.azure.com/",
        deployment_name="gpt-4-prod",
        api_key="your-api-key-here",
        description="Production GPT-4 for main workflows",
        is_default=False  # Don't set as default yet
    )

    if not deployment:
        print("Failed to create deployment, exiting")
        exit(1)

    deployment_id = deployment['id']

    # Step 2: Test connection
    print("\n=== Testing Connection ===")
    if not manager.test_deployment(deployment_id):
        print("Connection test failed, not setting as default")
        exit(1)

    # Step 3: Set as default
    print("\n=== Setting as Default ===")
    manager.set_as_default(deployment_id)

    # Step 4: Verify default
    print("\n=== Verifying Default Deployment ===")
    default = manager.get_default_deployment(model_type="llm")

    # Step 5: List all deployments
    print("\n=== Listing All Deployments ===")
    deployments = manager.list_deployments(model_type="llm")
    for dep in deployments:
        status = "DEFAULT" if dep['is_default'] else ""
        print(f"  - {dep['name']} ({dep['provider']}) {status}")

    # Optional: API key rotation example
    print("\n=== API Key Rotation (Example) ===")
    # manager.rotate_api_key(deployment_id, "new-api-key-here")
```

**JavaScript/TypeScript Example:**

```typescript
interface ModelDeployment {
  id: string;
  name: string;
  provider: string;
  model_name: string;
  model_type: string;
  is_default: boolean;
  is_active: boolean;
  settings: Record<string, any>;
  credentials: Record<string, string> | null;
  has_credentials: boolean;
}

interface TestResult {
  success: boolean;
  message?: string;
  provider?: string;
  model?: string;
  response?: string;
  latency_ms?: number;
  tokens_used?: number;
  error?: string;
}

class ModelDeploymentClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}

  async createDeployment(config: {
    name: string;
    provider: string;
    model_name: string;
    api_key: string;
    settings?: Record<string, any>;
    is_default?: boolean;
  }): Promise<ModelDeployment | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/model-deployments/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: config.name,
          provider: config.provider,
          model_name: config.model_name,
          model_type: 'llm',
          display_name: `${config.model_name} (${config.provider})`,
          settings: config.settings || {},
          credentials: { api_key: config.api_key },
          is_default: config.is_default || false
        })
      });

      if (!response.ok) {
        const error = await response.json();
        console.error('Failed to create deployment:', error.detail);
        return null;
      }

      const result = await response.json();
      console.log('✓ Created deployment:', result.data.id);
      return result.data;
    } catch (error) {
      console.error('Error creating deployment:', error);
      return null;
    }
  }

  async testDeployment(deploymentId: string): Promise<boolean> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/model-deployments/${deploymentId}/test`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        }
      );

      const result = await response.json();
      const testResult: TestResult = result.data;

      if (testResult.success) {
        console.log(`✓ Test passed (${testResult.latency_ms}ms)`);
        return true;
      } else {
        console.error('✗ Test failed:', testResult.error);
        return false;
      }
    } catch (error) {
      console.error('Error testing deployment:', error);
      return false;
    }
  }

  async listDeployments(modelType: string = 'llm'): Promise<ModelDeployment[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/model-deployments/?model_type=${modelType}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('Error listing deployments:', error);
      return [];
    }
  }

  async getDefaultDeployment(modelType: string = 'llm'): Promise<ModelDeployment | null> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/model-deployments/default?model_type=${modelType}`
      );

      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('Error getting default deployment:', error);
      return null;
    }
  }
}

// Usage
async function setupProductionLLM() {
  const client = new ModelDeploymentClient();

  // Create Azure OpenAI deployment
  const deployment = await client.createDeployment({
    name: 'production-gpt4',
    provider: 'azure_openai',
    model_name: 'gpt-4-0613',
    api_key: process.env.AZURE_OPENAI_API_KEY!,
    settings: {
      api_base: 'https://myorg-openai.openai.azure.com/',
      api_version: '2024-02-15-preview',
      deployment_name: 'gpt-4-prod'
    },
    is_default: true
  });

  if (!deployment) {
    console.error('Failed to create deployment');
    return;
  }

  // Test connection
  const testPassed = await client.testDeployment(deployment.id);
  if (!testPassed) {
    console.error('Deployment test failed');
    return;
  }

  // Verify it's set as default
  const defaultDep = await client.getDefaultDeployment('llm');
  console.log('Default LLM:', defaultDep?.name);
}

setupProductionLLM();
```

---

## Performance Considerations

### Endpoint Performance

**Fast Endpoints** (< 100ms typical):

- `GET /api/model-deployments/` - Simple database query with filter
- `GET /api/model-deployments/{deployment_id}` - Single record lookup by primary key
- `GET /api/model-deployments/default` - Indexed query on `is_default` and `model_type`

**Medium Endpoints** (100ms - 500ms typical):

- `POST /api/model-deployments/` - Database insert + credential encryption
- `PUT /api/model-deployments/{deployment_id}` - Database update + credential merge/encryption
- `DELETE /api/model-deployments/{deployment_id}` - Database delete/update

**Slow Endpoints** (500ms - 3000ms typical):

- `POST /api/model-deployments/{deployment_id}/test` - External LLM API call with network latency

### Optimisation Tips

**1. Use Credential Masking by Default**

```python
# ❌ Bad: Always includes credentials (slower, security risk)
response = requests.get(
    f"{base_url}/api/model-deployments/",
    params={"include_credentials": True}  # Triggers decryption for ALL
)

# ✅ Good: Only request credentials when needed
response = requests.get(
    f"{base_url}/api/model-deployments/"
    # include_credentials defaults to False
)

# Only decrypt when actually needed (e.g., for editing)
deployment = requests.get(
    f"{base_url}/api/model-deployments/{deployment_id}",
    params={"include_credentials": True}
).json()
```

**2. Filter Early with `model_type`**

```python
# ❌ Bad: Fetch all, filter in application
all_deployments = client.list_deployments()
llm_deployments = [d for d in all_deployments if d['model_type'] == 'llm']

# ✅ Good: Filter in database
llm_deployments = client.list_deployments(model_type='llm')
```

**3. Cache Default Deployment**

```python
# ❌ Bad: Fetch default on every workflow execution
def get_llm_config():
    default = requests.get(f"{base_url}/api/model-deployments/default").json()
    return default['data']

# ✅ Good: Cache default deployment (invalidate on update)
from functools import lru_cache

@lru_cache(maxsize=1)
def get_default_deployment():
    response = requests.get(f"{base_url}/api/model-deployments/default")
    return response.json()['data']

# Clear cache when deployments change
get_default_deployment.cache_clear()
```

**4. Test Before Setting as Default**

```python
# ❌ Bad: Set as default without testing (may break workflows)
client.create_deployment(..., is_default=True)

# ✅ Good: Test first, then set as default
deployment = client.create_deployment(..., is_default=False)
if client.test_deployment(deployment['id']):
    client.set_as_default(deployment['id'])
else:
    print("Test failed, not setting as default")
```

**5. Use Soft Delete for Production**

```python
# ❌ Bad: Hard delete (slower, cannot undo)
requests.delete(
    f"{base_url}/api/model-deployments/{deployment_id}?hard_delete=true"
)

# ✅ Good: Soft delete (faster, reversible)
requests.delete(
    f"{base_url}/api/model-deployments/{deployment_id}?hard_delete=false"
)

# Can re-enable later if needed
requests.put(
    f"{base_url}/api/model-deployments/{deployment_id}",
    json={"is_active": True}
)
```

### Caching Strategies

**Service Layer Caching:**

The module uses `@lru_cache` for singleton service instances:

```python
# dependencies.py
@lru_cache(maxsize=1)
def get_model_deployment_service() -> ModelDeploymentService:
    return ModelDeploymentService()  # Created once, reused
```

**Benefits:**

- Single service instance across all requests
- Shared encryption/enrichment instances
- Reduced memory allocation

**Application-Level Caching:**

For high-traffic applications, consider caching deployment data:

```python
import redis
import json

class CachedDeploymentClient:
    def __init__(self, base_url: str, redis_client: redis.Redis):
        self.base_url = base_url
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minutes

    def get_deployment(self, deployment_id: str) -> Optional[Dict]:
        # Check cache first
        cached = self.redis.get(f"deployment:{deployment_id}")
        if cached:
            return json.loads(cached)

        # Fetch from API
        response = requests.get(f"{self.base_url}/api/model-deployments/{deployment_id}")
        if response.ok:
            data = response.json()['data']

            # Cache result
            self.redis.setex(
                f"deployment:{deployment_id}",
                self.cache_ttl,
                json.dumps(data)
            )
            return data

        return None

    def invalidate_deployment(self, deployment_id: str):
        """Call after update/delete operations."""
        self.redis.delete(f"deployment:{deployment_id}")
```

---

## Related Documentation

### Architecture Documentation

- [Design Principles](../../../docs/architecture/03-design-principles.md) - Service layer patterns and dependency injection
- [Database Schema](../architecture/database-schema.md) - ModelDeployment table structure
- [Security Architecture](../architecture/security.md) - Credential encryption and key management

### API Documentation

- [Graph API](../../../backend/api/graph/graph.md) - Workflow execution (uses model deployments)
- [Execution API](../../../backend/api/execution/execution.md) - Workflow runtime (consumes enriched configs)
- [HTTP Execution API](../../../backend/api/http_execution/http_execution.md) - Streaming execution with LLMs

### Services Documentation

- [Model Deployment Service](../../backend/services/model_deployment/) - Service layer implementation
- [LLM Factory](../../backend/services/llm_models/) - LLM instance creation and testing
- [Credential Encryption](../../services/model_deployment/encryption.py) - Security implementation

### Frontend Integration

- [Model Deployment UI](../../../frontend/src/lib/model-deployment-api.ts) - TypeScript client implementation
- [Workflow Configuration](../../frontend/src/components/workflow/) - Using deployments in workflows

---

## Summary

The Model Deployments API module provides **enterprise-grade LLM configuration management** for AgenticStudio. It abstracts
away the complexity of managing multiple LLM providers, securing credentials, and ensuring reliable connections before
production use.

**Key Features:**

- **Multi-Provider Support:** Seamlessly manage OpenAI, Anthropic, and Azure OpenAI deployments
- **Secure Credential Storage:** Industry-standard encryption (Fernet/AES) for API keys
- **Connection Testing:** Validate deployments before using in production workflows
- **Default Deployment Management:** One default per provider for simplified workflow configuration
- **Runtime Config Enrichment:** Centralised credential injection at execution time
- **Flexible Deletion:** Soft delete for operational safety, hard delete for compliance
- **Azure Managed Identity:** Support for credential-less Azure deployments
- **Model Type Separation:** Distinct management for LLMs vs embeddings

**Architecture Highlights:**

- **Simplified Service Pattern:** Direct service injection (Routes → Services)
- **Singleton Services:** Performance optimisation via dependency caching
- **Modular Design:** Separate concerns (encryption, validation, serialisation)
- **Type-Safe:** Pydantic models ensure request/response validation

**Primary Use Cases:**

- **Initial System Setup:** Configure LLM providers during AgenticStudio deployment
- **Multi-Environment Management:** Separate dev/staging/prod LLM deployments
- **Cost Optimisation:** Switch between cost-effective and high-performance models
- **Security Compliance:** Centralised credential rotation and audit trail
- **Provider Migration:** Easy switching between OpenAI, Anthropic, Azure
- **Workflow Flexibility:** Override deployment per-workflow or use global default

**Operational Benefits:**

- **Zero-Downtime Updates:** Update credentials without restarting services
- **Centralised Management:** One API for all LLM configurations
- **Test-Driven Configuration:** Validate before deploying to production
- **Audit Trail:** Timestamps track deployment changes
- **Reversible Deletions:** Soft delete allows recovery from mistakes

The Model Deployments module is foundational to AgenticStudio's LLM capabilities, ensuring secure, reliable, and flexible
integration with leading AI providers.
