# Model Deployment Service

## Overview

The model deployment service provides comprehensive management for LLM model deployments in the AgenticStudio backend. It
handles CRUD operations for persisted model configurations, runtime configuration enrichment, credential
encryption/decryption, and validation of deployment settings. This service acts as a central registry for LLM provider
configurations, enabling reusable, secure model deployments across workflows.

**Location:** [backend/services/model_deployment/](../../backend/services/model_deployment/)

**Primary Responsibilities:**

- Persist and manage LLM deployment configurations in the database
- Encrypt and decrypt sensitive credential information
- Enrich runtime LLM configurations with deployment-specific settings
- Validate deployment configurations and ensure data integrity
- Serialize and format deployment data for API responses
- Support both credential-based and managed identity authentication (Azure)

**Key Use Cases:**

- Create reusable model deployment configurations for OpenAI, Anthropic, Azure, etc.
- Securely store API keys and credentials using encryption
- Dynamically inject deployment settings into workflow LLM configurations at runtime
- Test model deployment connections before saving
- Manage default deployments per model type (LLM vs embedding)
- Support Azure Managed Identity for credential-less authentication

---

## Architecture

### Module Structure

```
backend/services/model_deployment/
├── __init__.py              # Public API exports
├── service.py               # Main ModelDeploymentService with CRUD operations
├── enrichment.py            # ConfigEnricher for runtime config enrichment
├── encryption.py            # CredentialEncryption for credential security
├── exceptions.py            # Custom exception hierarchy
├── validators.py            # Input validation and normalisation
└── serializers.py           # Data serialisation and credential masking
```

**File Purposes:**

- **[\_\_init\_\_.py](../../backend/services/model_deployment/__init__.py)** - Defines public API surface with `__all__`
  exports
- **[service.py](../../backend/services/model_deployment/service.py)** - Main service class implementing CRUD operations
  and coordinating sub-components
- **[enrichment.py](../../backend/services/model_deployment/enrichment.py)** - Handles runtime enrichment of LLM configs
  with deployment data
- **[encryption.py](../../backend/services/model_deployment/encryption.py)** - Encrypts/decrypts credentials using
  backend encryption utilities
- **[exceptions.py](../../backend/services/model_deployment/exceptions.py)** - Custom exception types for
  deployment-specific errors
- **[validators.py](../../backend/services/model_deployment/validators.py)** - Validation functions for payloads,
  settings, credentials
- **[serializers.py](../../backend/services/model_deployment/serializers.py)** - Converts database models to
  dictionaries with credential masking

### Design Patterns

**Clean Architecture / Separation of Concerns:**
The module follows clean architecture principles with clear separation between:

- **Persistence layer** (service.py) - Database CRUD operations
- **Domain logic** (validators.py, enrichment.py) - Business rules and validations
- **Security layer** (encryption.py) - Credential encryption/decryption
- **Presentation layer** (serializers.py) - Data formatting and masking

**Dependency Injection:**
The `ModelDeploymentService` accepts optional `CredentialEncryption` and `ConfigEnricher` dependencies, defaulting to
standard implementations. This enables testing with mock implementations.

**Composition over Inheritance:**
The service composes `CredentialEncryption` and `ConfigEnricher` rather than inheriting functionality, promoting
flexibility and testability.

**Component Relationships:**

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                 │
│         (backend/api/model_deployments/routes.py)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              ModelDeploymentService                          │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ ConfigEnricher   │  │ CredentialEncrypt│                │
│  │  (enrichment)    │  │   (encryption)   │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │   Validators     │  │   Serializers    │                │
│  │  (validation)    │  │  (formatting)    │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│          Database (ModelDeployment table)                    │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.database` - Database session management and Base model
- `backend.models.ModelDeployment` - Database model for deployment records
- `backend.models.workflow.configs.llm.LLMConfig` - Runtime LLM configuration model
- `backend.encryption_utils.default_encryptor` - Encryption/decryption utilities

**External Dependencies:**

- `sqlalchemy` - ORM for database operations
- Standard library: `logging`, `copy`, `typing`

**Database Dependencies:**

- **Table:** `model_deployments`
- **Schema:** UUID primary key, name (unique), provider, model_name, model_type, settings (JSON),
  encrypted_credentials (JSON), is_default, is_active, timestamps

**Environment Variables:**

- No direct environment variables; encryption key is managed by `backend.encryption_utils`

---

## Public API

### Exported Classes

- `ModelDeploymentService` - Main service for CRUD operations and runtime enrichment
- `ConfigEnricher` - Enriches LLM configurations with deployment data
- `CredentialEncryption` - Handles credential encryption and decryption

### Exported Exceptions

```
Exception
└── ModelDeploymentError
    ├── DeploymentNotFoundError
    ├── DuplicateDeploymentNameError
    ├── InvalidCredentialError
    ├── InvalidSettingsError
    └── EncryptionError
```

### Exception Details

- `ModelDeploymentError` - Base exception for all deployment-related errors
- `DeploymentNotFoundError` - Raised when a deployment ID is not found or inactive
- `DuplicateDeploymentNameError` - Raised when attempting to create/update with duplicate name
- `InvalidCredentialError` - Raised when credential validation fails
- `InvalidSettingsError` - Raised when settings validation fails
- `EncryptionError` - Raised when encryption/decryption operations fail

---

## Core Classes

### `ModelDeploymentService`

Main service class encapsulating persistence and runtime enrichment for model deployments.

**Purpose:** Provides a complete interface for managing LLM deployment configurations, including CRUD operations,
credential security, and runtime configuration enrichment.

**Responsibilities:**

- Create, read, update, and delete model deployment records
- Validate deployment configurations and ensure uniqueness constraints
- Encrypt credentials before persisting to database
- Enrich LLM configurations at runtime with deployment settings
- Manage default deployment flags per provider
- Serialize deployment data for API responses

**Initialisation:**

```python
def __init__(
    self,
    credential_encryption: CredentialEncryption | None = None,
    config_enricher: ConfigEnricher | None = None,
) -> None:
    """Initialise model deployment service.

    Args:
        credential_encryption: Encryption handler (uses default if None)
        config_enricher: Config enricher (uses default if None)
    """
```

**Example:**

```python
from backend.services.model_deployment import ModelDeploymentService

# Basic initialisation with defaults
service = ModelDeploymentService()

# Custom initialisation with injected dependencies
from backend.services.model_deployment import CredentialEncryption, ConfigEnricher

custom_encryption = CredentialEncryption()
custom_enricher = ConfigEnricher(custom_encryption)
service = ModelDeploymentService(
    credential_encryption=custom_encryption,
    config_enricher=custom_enricher,
)
```

---

### Key Methods

#### `list_deployments()`

List all active model deployments with optional filtering.

```python
def list_deployments(
    self,
    include_credentials: bool = False,
    model_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all active model deployments."""
```

**Parameters:**

- `include_credentials` (bool) - Whether to include decrypted credentials (default: False)
- `model_type` (Optional[str]) - Filter by model type ('llm' or 'embedding', default: None)

**Returns:**

- `List[Dict[str, Any]]` - List of serialised deployment dictionaries

**Raises:**

- `InvalidSettingsError` - If model_type is invalid

**Example:**

```python
from backend.services.model_deployment import ModelDeploymentService

service = ModelDeploymentService()

# List all active LLM deployments
llm_deployments = service.list_deployments(model_type="llm")

# List all deployments with credentials (admin use)
all_deployments = service.list_deployments(include_credentials=True)

for deployment in llm_deployments:
    print(f"Deployment: {deployment['name']} ({deployment['provider']})")
```

**Behaviour:**

- Queries database for active deployments only (`is_active=True`)
- Applies model_type filter if provided
- Orders results by name ascending
- Credentials are masked by default, shown only if `include_credentials=True`
- Returns empty list if no deployments found

**Use Cases:**

- Display available model deployments in UI dropdowns
- Admin dashboard showing all configured models
- Filtering LLM vs embedding deployments for different workflow node types

---

#### `get_deployment()`

Retrieve a single model deployment by ID.

```python
def get_deployment(
    self,
    deployment_id: str,
    include_credentials: bool = False,
) -> Optional[Dict[str, Any]]:
    """Get a single model deployment by ID."""
```

**Parameters:**

- `deployment_id` (str) - Deployment ID to retrieve
- `include_credentials` (bool) - Whether to include decrypted credentials (default: False)

**Returns:**

- `Optional[Dict[str, Any]]` - Serialised deployment or None if not found

**Example:**

```python
service = ModelDeploymentService()

deployment = service.get_deployment("550e8400-e29b-41d4-a716-446655440000")
if deployment:
    print(f"Found: {deployment['name']}")
    print(f"Provider: {deployment['provider']}")
    print(f"Model: {deployment['model_name']}")
else:
    print("Deployment not found")
```

**Behaviour:**

- Returns None if deployment_id is not found
- Inactive deployments are still returned (unlike `list_deployments`)
- Credentials masked unless `include_credentials=True`

**Use Cases:**

- Fetch deployment details for editing in UI
- Retrieve deployment information for logging/audit
- Validate deployment exists before using in workflow

---

#### `create_deployment()`

Create a new model deployment with validation and encryption.

```python
def create_deployment(
    self,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new model deployment."""
```

**Parameters:**

- `payload` (Dict[str, Any]) - Deployment creation data

**Payload Structure:**

```python
{
    "name": str,                        # Required: Unique deployment name
    "provider": str,                    # Required: Provider (openai, anthropic, azure_openai, etc.)
    "model_name": str,                  # Required: Model identifier
    "model_type": str,                  # Optional: 'llm' or 'embedding' (default: 'llm')
    "display_name": str,                # Optional: Human-readable name
    "description": str,                 # Optional: Deployment description
    "credentials": Dict[str, str],      # Optional: Credential key-value pairs
    "settings": Dict[str, Any],         # Optional: Provider-specific settings
    "is_default": bool,                 # Optional: Set as default deployment (default: False)
}
```

**Returns:**

- `Dict[str, Any]` - Serialised created deployment

**Raises:**

- `DuplicateDeploymentNameError` - If name already exists
- `InvalidSettingsError` - If required fields missing or invalid
- `InvalidCredentialError` - If credential validation fails
- `EncryptionError` - If encryption fails

**Example:**

```python
from backend.services.model_deployment import ModelDeploymentService

service = ModelDeploymentService()

# Create OpenAI deployment
deployment = service.create_deployment({
    "name": "gpt-4-production",
    "provider": "openai",
    "model_name": "gpt-4-0125-preview",
    "model_type": "llm",
    "display_name": "GPT-4 Turbo (Production)",
    "description": "Production GPT-4 deployment with high rate limits",
    "credentials": {
        "api_key": "sk-..."
    },
    "settings": {
        "base_url": "https://api.openai.com/v1",
        "organization_id": "org-..."
    },
    "is_default": True,
})

print(f"Created deployment: {deployment['id']}")
```

**Behaviour:**

- Validates all required fields present and correct types
- Normalises provider to lowercase
- Validates model_type is 'llm' or 'embedding'
- Encrypts credentials before storing
- Validates either credentials OR managed identity configured (Azure)
- Raises `DefaultModelConflictError` (rather than silently switching) if `is_default=True` and another active
  deployment of the same model type is already default; only one default per model type is allowed, independent of
  provider
- Sets `is_active=True` automatically
- Returns serialised deployment without credentials

**Use Cases:**

- Configure new LLM provider for workflows
- Set up multiple API keys for different environments
- Create Azure deployment with managed identity

---

#### `update_deployment()`

Update an existing model deployment.

```python
def update_deployment(
    self,
    deployment_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Update an existing model deployment."""
```

**Parameters:**

- `deployment_id` (str) - Deployment ID to update
- `payload` (Dict[str, Any]) - Update data (only provided fields are updated)

**Returns:**

- `Optional[Dict[str, Any]]` - Serialised updated deployment or None if not found

**Raises:**

- `DuplicateDeploymentNameError` - If name change conflicts with existing deployment
- `InvalidSettingsError` - If validation fails
- `InvalidCredentialError` - If credential validation fails
- `EncryptionError` - If encryption fails

**Example:**

```python
service = ModelDeploymentService()

# Update specific fields only
updated = service.update_deployment(
    "550e8400-e29b-41d4-a716-446655440000",
    {
        "display_name": "GPT-4 Turbo (Staging)",
        "settings": {
            "base_url": "https://api.staging.example.com/v1"
        },
        "is_default": False,
    }
)

if updated:
    print(f"Updated: {updated['name']}")
else:
    print("Deployment not found")
```

**Behaviour:**

- Partial updates: only provided fields are modified
- Name uniqueness validated if name is changed
- Credentials are merged with existing (not replaced entirely)
- Setting a credential key to None or empty string removes it
- Raises `DefaultModelConflictError` (rather than silently switching) if setting `is_default=True` while another
  active deployment of the same model type is already default
- Empty payload returns current deployment unchanged

**Use Cases:**

- Rotate API keys without changing other settings
- Toggle default deployment flag
- Update model name after provider upgrade
- Deactivate deployment temporarily (`is_active=False`)

---

#### `delete_deployment()`

Delete a model deployment (soft or hard delete).

```python
def delete_deployment(
    self,
    deployment_id: str,
    hard_delete: bool = False,
) -> bool:
    """Delete a model deployment."""
```

**Parameters:**

- `deployment_id` (str) - Deployment ID to delete
- `hard_delete` (bool) - If True, permanently delete; if False, mark as inactive (default: False)

**Returns:**

- `bool` - True if deleted, False if not found

**Example:**

```python
service = ModelDeploymentService()

# Soft delete (mark as inactive)
success = service.delete_deployment("550e8400-e29b-41d4-a716-446655440000")

# Hard delete (permanent removal)
success = service.delete_deployment(
    "550e8400-e29b-41d4-a716-446655440000",
    hard_delete=True
)

if success:
    print("Deployment deleted")
else:
    print("Deployment not found")
```

**Behaviour:**

- Soft delete: Sets `is_active=False` and `is_default=False`
- Hard delete: Permanently removes record from database
- Soft delete is recommended to preserve audit trail
- Returns False if deployment_id not found

**Use Cases:**

- Temporarily disable deployment without losing configuration
- Clean up test deployments permanently
- Remove deployments after provider migration

---

#### `enrich_llm_config()`

Enrich an LLM configuration with deployment settings and credentials at runtime.

```python
def enrich_llm_config(
    self,
    llm_config: LLMConfig,
) -> LLMConfig:
    """Attach provider settings and decrypted credentials to LLM config."""
```

**Parameters:**

- `llm_config` (LLMConfig) - Base LLM configuration with `model_deployment_id`

**Returns:**

- `LLMConfig` - Enriched LLM configuration (deep copy to avoid side effects)

**Raises:**

- `DeploymentNotFoundError` - If deployment not found or inactive

**Example:**

```python
from backend.services.model_deployment import ModelDeploymentService
from backend.models.workflow.configs.llm import LLMConfig

service = ModelDeploymentService()

# Create base config referencing deployment
base_config = LLMConfig(
    provider="",  # Will be filled from deployment
    model_name="",  # Will be filled from deployment
    temperature=0.7,
    max_tokens=1000,
    model_deployment_id="550e8400-e29b-41d4-a716-446655440000",
)

# Enrich with deployment data
enriched = service.enrich_llm_config(base_config)

print(f"Provider: {enriched.provider}")
print(f"Model: {enriched.model_name}")
print(f"Has credentials: {enriched.credentials is not None}")
```

**Behaviour:**

- Returns original config unchanged if no `model_deployment_id` specified
- Fetches deployment from database
- Creates deep copy of input config to avoid side effects
- Populates `provider`, `model_name`, `display_name` from deployment
- Decrypts and attaches credentials
- Merges deployment settings with runtime config (runtime overrides deployment)
- Fills legacy fields (`deployment_name`, `api_version`, `api_base`) for backward compatibility

**Use Cases:**

- Inject deployment settings into workflow LLM node at execution time
- Resolve deployment reference to concrete configuration
- Support dynamic model switching without workflow changes

---

#### `get_default_deployment()`

Get the default model deployment for a specific model type.

```python
def get_default_deployment(
    self,
    model_type: str = "llm",
    include_credentials: bool = False,
) -> Optional[Dict[str, Any]]:
    """Get the default model deployment for a specific model type."""
```

**Parameters:**

- `model_type` (str) - Type of model ('llm' or 'embedding', default: 'llm')
- `include_credentials` (bool) - Whether to include decrypted credentials (default: False)

**Returns:**

- `Optional[Dict[str, Any]]` - Serialised default deployment or None if no default set

**Raises:**

- `InvalidSettingsError` - If model_type is invalid

**Example:**

```python
service = ModelDeploymentService()

# Get default LLM deployment
default_llm = service.get_default_deployment(model_type="llm")
if default_llm:
    print(f"Default LLM: {default_llm['name']}")

# Get default embedding deployment
default_embedding = service.get_default_deployment(model_type="embedding")
if default_embedding:
    print(f"Default Embedding: {default_embedding['name']}")
```

**Behaviour:**

- Queries for active deployment with `is_default=True` and matching `model_type`
- Returns None if no default configured
- Each model type can have its own default
- Provider-agnostic: returns default regardless of provider

**Use Cases:**

- Populate default model selection in UI
- Fallback when no deployment specified in workflow
- Quick access to primary LLM configuration

---

### `ConfigEnricher`

Handles enrichment of LLM configurations with deployment data at runtime.

**Purpose:** Separates the concern of runtime configuration enrichment from CRUD operations, enabling independent
testing and reuse.

**Responsibilities:**

- Fetch deployment data from database
- Decrypt credentials from deployment
- Merge deployment settings with runtime configuration
- Fill legacy configuration fields for backward compatibility

**Initialisation:**

```python
def __init__(
    self,
    credential_encryption: CredentialEncryption | None = None,
) -> None:
    """Initialise config enricher.

    Args:
        credential_encryption: Encryption handler (uses default if None)
    """
```

**Example:**

```python
from backend.services.model_deployment import ConfigEnricher, CredentialEncryption
from backend.services.database import get_db

encryption = CredentialEncryption()
enricher = ConfigEnricher(credential_encryption=encryption)

# Use enricher directly
with get_db() as db:
    enriched_config = enricher.enrich_llm_config(db, base_config)
```

---

#### `enrich_llm_config()`

Enrich an LLM configuration with deployment data.

```python
def enrich_llm_config(
    self,
    db: Session,
    llm_config: LLMConfig,
) -> LLMConfig:
    """Attach provider settings and decrypted credentials to LLM config."""
```

**Parameters:**

- `db` (Session) - Database session
- `llm_config` (LLMConfig) - Base LLM configuration

**Returns:**

- `LLMConfig` - Enriched LLM configuration (deep copy)

**Raises:**

- `DeploymentNotFoundError` - If deployment not found or inactive

**Behaviour:**

- Returns original if no `model_deployment_id` specified
- Creates deep copy to avoid side effects on input
- Merges settings: runtime config overrides deployment settings
- Fills legacy fields for backward compatibility

---

### `CredentialEncryption`

Handles encryption and decryption of model deployment credentials.

**Purpose:** Provides secure credential storage by encrypting all credential values before persisting to database.

**Responsibilities:**

- Encrypt credential dictionaries for storage
- Decrypt credential dictionaries for runtime use
- Merge credential updates with existing encrypted data
- Validate credential types and formats

**Initialisation:**

```python
def __init__(
    self,
    encryptor=None,
) -> None:
    """Initialise credential encryption handler.

    Args:
        encryptor: Encryption service (defaults to default_encryptor)
    """
```

**Example:**

```python
from backend.services.model_deployment import CredentialEncryption

encryption = CredentialEncryption()

# Encrypt credentials
credentials = {"api_key": "sk-...", "org_id": "org-..."}
encrypted = encryption.encrypt_credentials(credentials)

# Decrypt credentials
decrypted = encryption.decrypt_credentials(encrypted)
```

---

#### `encrypt_credentials()`

Encrypt a dictionary of credentials.

```python
def encrypt_credentials(
    self,
    credentials: Optional[Dict[str, Any]],
) -> Optional[Dict[str, str]]:
    """Encrypt credential dictionary."""
```

**Parameters:**

- `credentials` (Optional[Dict[str, Any]]) - Dictionary of credential key-value pairs

**Returns:**

- `Optional[Dict[str, str]]` - Dictionary of encrypted credentials or None if input is empty

**Raises:**

- `InvalidCredentialError` - If credential value is not a string
- `EncryptionError` - If encryption fails

**Example:**

```python
encryption = CredentialEncryption()

credentials = {
    "api_key": "sk-1234567890",
    "organization_id": "org-abcdef"
}

encrypted = encryption.encrypt_credentials(credentials)
# Result: {"api_key": "encrypted_value_1", "organization_id": "encrypted_value_2"}
```

**Behaviour:**

- Returns None if credentials is None or empty
- Skips keys with empty/None values
- Validates all values are strings
- Encrypts each credential value individually
- Returns None if no valid credentials after filtering

---

#### `decrypt_credentials()`

Decrypt a dictionary of encrypted credentials.

```python
def decrypt_credentials(
    self,
    encrypted: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """Decrypt credential dictionary."""
```

**Parameters:**

- `encrypted` (Optional[Dict[str, Any]]) - Dictionary of encrypted credential key-value pairs

**Returns:**

- `Dict[str, str]` - Dictionary of decrypted credentials (empty dict if input is None)

**Example:**

```python
encryption = CredentialEncryption()

encrypted = {"api_key": "encrypted_value"}
decrypted = encryption.decrypt_credentials(encrypted)
# Result: {"api_key": "sk-1234567890"}
```

**Behaviour:**

- Returns empty dict if input is None
- Skips keys with empty/None values
- Logs decryption errors but does not raise (robustness)
- Failed decryptions omit the key from result

---

#### `merge_credentials()`

Merge credential updates with existing credentials.

```python
def merge_credentials(
    self,
    existing_encrypted: Optional[Dict[str, Any]],
    updates: Optional[Dict[str, Any]],
) -> Optional[Dict[str, str]]:
    """Merge credential updates with existing credentials."""
```

**Parameters:**

- `existing_encrypted` (Optional[Dict[str, Any]]) - Current encrypted credentials
- `updates` (Optional[Dict[str, Any]]) - Updates to apply (None/empty string removes keys)

**Returns:**

- `Optional[Dict[str, str]]` - Updated encrypted credentials or None if result is empty

**Raises:**

- `InvalidCredentialError` - If update value is not a string
- `EncryptionError` - If encryption fails

**Example:**

```python
encryption = CredentialEncryption()

existing = {"api_key": "encrypted_old", "org_id": "encrypted_org"}

# Update api_key, remove org_id, add new_key
updates = {
    "api_key": "sk-new-key",
    "org_id": None,  # Remove this key
    "new_key": "new-value"
}

merged = encryption.merge_credentials(existing, updates)
# Result: {"api_key": "encrypted_new", "new_key": "encrypted_new_value"}
```

**Behaviour:**

- Returns existing if updates is None
- Decrypts existing credentials
- Applies updates: None or empty string removes key
- Re-encrypts merged result

**Use Cases:**

- Rotate API key without affecting other credentials
- Remove specific credentials during update
- Add new credential fields to existing deployment

---

## Configuration

### Environment Variables

The model deployment service does not directly use environment variables. However, it depends on the encryption key
configured in `backend.encryption_utils`, which may use environment variables like:

- `ENCRYPTION_KEY` - Encryption key for credential encryption (required: yes)

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.model_deployment import ModelDeploymentService

# Use default encryption and enricher
service = ModelDeploymentService()
```

**Advanced Initialisation with Dependency Injection:**

```python
from backend.services.model_deployment import (
    ModelDeploymentService,
    CredentialEncryption,
    ConfigEnricher,
)

# Custom encryption instance (e.g., for testing)
custom_encryption = CredentialEncryption(encryptor=mock_encryptor)

# Custom enricher with custom encryption
custom_enricher = ConfigEnricher(credential_encryption=custom_encryption)

# Inject dependencies
service = ModelDeploymentService(
    credential_encryption=custom_encryption,
    config_enricher=custom_enricher,
)
```

**Singleton Pattern (FastAPI Dependency):**

```python
from functools import lru_cache
from backend.services.model_deployment import ModelDeploymentService

@lru_cache(maxsize=1)
def get_model_deployment_service() -> ModelDeploymentService:
    """Get singleton model deployment service instance."""
    return ModelDeploymentService()

# Use in FastAPI route
from fastapi import Depends

@router.get("/deployments")
async def list_deployments(
    service: ModelDeploymentService = Depends(get_model_deployment_service),
):
    return service.list_deployments()
```

---

## Error Handling

### Exception Hierarchy

```
Exception
└── ModelDeploymentError
    ├── DeploymentNotFoundError
    ├── DuplicateDeploymentNameError
    ├── InvalidCredentialError
    ├── InvalidSettingsError
    └── EncryptionError
```

### Exception Details

#### `ModelDeploymentError`

Base exception for all model deployment errors.

**Inherits from:** `Exception`

**When raised:**

- Never raised directly; use specific subclasses

**Example:**

```python
from backend.services.model_deployment import ModelDeploymentError

try:
    service.create_deployment(payload)
except ModelDeploymentError as e:
    # Catch all deployment-related errors
    logger.error(f"Deployment error: {e}")
```

---

#### `DeploymentNotFoundError`

Raised when a model deployment is not found or inactive.

**Inherits from:** `ModelDeploymentError`

**Attributes:**

- `deployment_id` (str) - The deployment ID that was not found

**When raised:**

- Attempting to enrich config with non-existent deployment
- Deployment exists but is marked inactive

**Example:**

```python
from backend.services.model_deployment import DeploymentNotFoundError

try:
    enriched = service.enrich_llm_config(llm_config)
except DeploymentNotFoundError as e:
    print(f"Deployment {e.deployment_id} not found")
    # Use fallback configuration
```

---

#### `DuplicateDeploymentNameError`

Raised when attempting to create or update a deployment with a duplicate name.

**Inherits from:** `ModelDeploymentError`

**Attributes:**

- `name` (str) - The duplicate deployment name

**When raised:**

- Creating deployment with name that already exists
- Updating deployment name to conflict with another deployment

**Example:**

```python
from backend.services.model_deployment import DuplicateDeploymentNameError

try:
    service.create_deployment({"name": "gpt-4", ...})
except DuplicateDeploymentNameError as e:
    print(f"Deployment name '{e.name}' already exists")
    # Prompt user to choose different name
```

---

#### `InvalidCredentialError`

Raised when credential validation fails.

**Inherits from:** `ModelDeploymentError`

**When raised:**

- Credential value is not a string
- Required credentials missing for provider (non-Azure)
- Credential format invalid

**Example:**

```python
from backend.services.model_deployment import InvalidCredentialError

try:
    service.create_deployment({
        "name": "my-deployment",
        "provider": "openai",
        "model_name": "gpt-4",
        "credentials": {"api_key": 12345}  # Invalid: not a string
    })
except InvalidCredentialError as e:
    print(f"Credential error: {e}")
```

---

#### `InvalidSettingsError`

Raised when settings validation fails.

**Inherits from:** `ModelDeploymentError`

**When raised:**

- Required field missing (name, provider, model_name)
- Field has incorrect type
- Provider string is empty or invalid
- model_type is not 'llm' or 'embedding'
- Settings is not a dictionary

**Example:**

```python
from backend.services.model_deployment import InvalidSettingsError

try:
    service.create_deployment({
        "name": "my-deployment",
        # Missing required 'provider' field
        "model_name": "gpt-4",
    })
except InvalidSettingsError as e:
    print(f"Settings error: {e}")
```

---

#### `EncryptionError`

Raised when encryption/decryption operations fail.

**Inherits from:** `ModelDeploymentError`

**Attributes:**

- `key` (str) - The credential key being encrypted/decrypted
- `operation` (str) - The operation that failed ('encrypt' or 'decrypt')
- `original_error` (Exception) - The underlying exception

**When raised:**

- Encryption service fails to encrypt credential
- Decryption service fails to decrypt credential (during encryption.encrypt_credentials)

**Example:**

```python
from backend.services.model_deployment import EncryptionError

try:
    encrypted = encryption.encrypt_credentials(credentials)
except EncryptionError as e:
    print(f"Failed to {e.operation} credential '{e.key}': {e.original_error}")
    # Log and alert administrators
```

---

### Error Handling Patterns

**Recommended Pattern for CRUD Operations:**

```python
from backend.services.model_deployment import (
    ModelDeploymentService,
    DeploymentNotFoundError,
    DuplicateDeploymentNameError,
    InvalidCredentialError,
    InvalidSettingsError,
    EncryptionError,
    ModelDeploymentError,
)

service = ModelDeploymentService()

try:
    deployment = service.create_deployment(payload)
    print(f"Created: {deployment['id']}")

except DuplicateDeploymentNameError as e:
    # Handle duplicate name specifically
    return {"error": "duplicate_name", "message": str(e)}

except InvalidCredentialError as e:
    # Handle credential validation
    return {"error": "invalid_credentials", "message": str(e)}

except InvalidSettingsError as e:
    # Handle settings validation
    return {"error": "invalid_settings", "message": str(e)}

except EncryptionError as e:
    # Handle encryption failure (system error)
    logger.error(f"Encryption failed: {e}")
    return {"error": "system_error", "message": "Failed to secure credentials"}

except ModelDeploymentError as e:
    # Catch-all for other deployment errors
    logger.error(f"Deployment error: {e}")
    return {"error": "deployment_error", "message": str(e)}
```

**Recommended Pattern for Runtime Enrichment:**

```python
from backend.services.model_deployment import (
    ModelDeploymentService,
    DeploymentNotFoundError,
)

service = ModelDeploymentService()

try:
    enriched_config = service.enrich_llm_config(llm_config)
    llm = factory.create_llm(enriched_config)

except DeploymentNotFoundError as e:
    # Deployment not found or inactive
    logger.warning(f"Deployment not found: {e}")
    # Use fallback configuration or raise workflow error
    raise WorkflowExecutionError(f"Model deployment '{e.deployment_id}' not available")

except Exception as e:
    # Unexpected errors
    logger.error(f"Failed to enrich config: {e}")
    raise
```

---

## Integration Patterns

### Integration with API Layer

The model deployment service is typically used in FastAPI routes via dependency injection.

**Example from [backend/api/model_deployments/routes.py](../../backend/api/model_deployments/routes.py):**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.services.model_deployment import ModelDeploymentService
from .dependencies import get_model_deployment_service

router = APIRouter(prefix="/api/model-deployments", tags=["model deployments"])

@router.get("")
async def list_model_deployments(
    include_credentials: bool = Query(False),
    model_type: Optional[str] = Query(None),
    service: ModelDeploymentService = Depends(get_model_deployment_service),
):
    """List all active model deployments."""
    try:
        deployments = service.list_deployments(
            include_credentials=include_credentials,
            model_type=model_type,
        )
        return {"success": True, "data": deployments}
    except ModelDeploymentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("")
async def create_model_deployment(
    payload: ModelDeploymentCreate,
    service: ModelDeploymentService = Depends(get_model_deployment_service),
):
    """Create a new model deployment."""
    try:
        deployment = service.create_deployment(payload.model_dump())
        return {"success": True, "data": deployment}
    except ModelDeploymentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

---

### Integration with Execution Services

The model deployment service is used by execution services to enrich LLM configurations at runtime.

**Example
from [backend/services/execution/async_agent/llm_builder.py](../../backend/services/execution/async_agent/llm_builder.py):
**

```python
from backend.services.model_deployment import ModelDeploymentService
from backend.services.llm_models import LLMFactory

# Initialise services
model_service = ModelDeploymentService()
llm_factory = LLMFactory(model_service=model_service)

# Enrich config with deployment settings
enriched_config = model_service.enrich_llm_config(base_llm_config)

# Create LLM instance
llm = llm_factory.create_llm(enriched_config)
```

---

### Integration with Graph Service

The graph service uses model deployment service to validate and enrich LLM configurations in workflow nodes.

**Example from [backend/services/graph/manager.py](../../backend/services/graph/manager.py):**

```python
from backend.services.model_deployment import ModelDeploymentService
from backend.services.llm_models import LLMFactory

class GraphManager:
    def __init__(self):
        self.model_service = ModelDeploymentService()
        self.llm_factory = LLMFactory(model_service=self.model_service)

    def build_agent(self, agent_config: AgentConfig):
        # Enrich LLM config from deployment
        enriched_config = self.model_service.enrich_llm_config(
            agent_config.llm_config
        )

        # Create LLM instance for agent
        llm = self.llm_factory.create_llm(enriched_config)
        return llm
```

---

### Dependency Flow

```
API Layer (FastAPI routes)
    │
    ├─► ModelDeploymentService.list_deployments()
    ├─► ModelDeploymentService.create_deployment()
    └─► ModelDeploymentService.update_deployment()

Execution Layer (Workflow execution)
    │
    ├─► ModelDeploymentService.enrich_llm_config()
    └─► LLMFactory.create_llm() ──► Uses enriched config

Graph Layer (Graph building)
    │
    └─► ModelDeploymentService.enrich_llm_config()
```

**Services that depend on model_deployment:**

- `backend.services.graph` - GraphManager enriches agent LLM configs
- `backend.services.execution.async_agent` - Execution enriches LLM configs at runtime
- `backend.services.llm_models` - LLMFactory uses model_service for enrichment
- `backend.api.model_deployments` - API routes for CRUD operations

**Services that model_deployment depends on:**

- `backend.services.database` - Database session management
- `backend.encryption_utils` - Credential encryption/decryption

---

### Common Integration Patterns

#### Pattern 1: Dependency Injection in FastAPI

Use singleton pattern to share service instance across routes.

```python
from functools import lru_cache
from backend.services.model_deployment import ModelDeploymentService

@lru_cache(maxsize=1)
def get_model_deployment_service() -> ModelDeploymentService:
    """Get singleton service instance."""
    return ModelDeploymentService()

# Use in route
@router.get("/deployments")
async def list_deployments(
    service: ModelDeploymentService = Depends(get_model_deployment_service),
):
    return service.list_deployments()
```

---

#### Pattern 2: Runtime Config Enrichment

Enrich LLM config with deployment data before creating LLM instance.

```python
from backend.services.model_deployment import ModelDeploymentService
from backend.services.llm_models import LLMFactory
from backend.models.workflow.configs.llm import LLMConfig

# Services
model_service = ModelDeploymentService()
llm_factory = LLMFactory(model_service=model_service)

# Base config with deployment reference
base_config = LLMConfig(
    provider="",
    model_name="",
    temperature=0.7,
    model_deployment_id="550e8400-e29b-41d4-a716-446655440000",
)

# Enrich and create LLM
enriched_config = model_service.enrich_llm_config(base_config)
llm = llm_factory.create_llm(enriched_config)

# Use LLM
response = llm.invoke("What is 2+2?")
```

---

#### Pattern 3: Test Connection Before Save

Validate deployment connection before persisting to database.

```python
from backend.services.model_deployment import ModelDeploymentService
from backend.services.llm_models import LLMFactory
from backend.models.workflow.configs.llm import LLMConfig

model_service = ModelDeploymentService()
llm_factory = LLMFactory(model_service=model_service)

# Build test config
test_config = LLMConfig(
    provider=payload["provider"],
    model_name=payload["model_name"],
    credentials=payload.get("credentials", {}),
    config=payload.get("settings", {}),
)

# Test connection
try:
    test_result = llm_factory.test_llm_connection(test_config)
    if not test_result.get("success"):
        return {"error": "Connection test failed", "details": test_result}
except Exception as e:
    return {"error": "Connection test failed", "details": str(e)}

# Save if test passed
deployment = model_service.create_deployment(payload)
return {"success": True, "data": deployment}
```

---

## Usage Examples

### Example 1: Basic CRUD Operations

Complete example of creating, reading, updating, and deleting deployments.

```python
from backend.services.model_deployment import (
    ModelDeploymentService,
    DuplicateDeploymentNameError,
)

# Initialise service
service = ModelDeploymentService()

# Create deployment
try:
    deployment = service.create_deployment({
        "name": "gpt-4-production",
        "provider": "openai",
        "model_name": "gpt-4-0125-preview",
        "model_type": "llm",
        "display_name": "GPT-4 Turbo (Production)",
        "description": "Production GPT-4 deployment",
        "credentials": {
            "api_key": "sk-proj-..."
        },
        "settings": {
            "base_url": "https://api.openai.com/v1"
        },
        "is_default": True,
    })
    print(f"✓ Created deployment: {deployment['id']}")
except DuplicateDeploymentNameError as e:
    print(f"✗ Name already exists: {e.name}")

# List all deployments
deployments = service.list_deployments(model_type="llm")
print(f"✓ Found {len(deployments)} LLM deployments")
for dep in deployments:
    print(f"  - {dep['name']} ({dep['provider']})")

# Get specific deployment
deployment = service.get_deployment(deployment['id'])
print(f"✓ Retrieved: {deployment['name']}")

# Update deployment
updated = service.update_deployment(
    deployment['id'],
    {"display_name": "GPT-4 Turbo (Updated)"}
)
print(f"✓ Updated display name: {updated['display_name']}")

# Soft delete deployment
success = service.delete_deployment(deployment['id'])
print(f"✓ Deleted deployment: {success}")
```

---

### Example 2: Runtime Config Enrichment

Complete workflow showing config enrichment and LLM usage.

```python
from backend.services.model_deployment import ModelDeploymentService
from backend.services.llm_models import LLMFactory
from backend.models.workflow.configs.llm import LLMConfig

# Initialise services
model_service = ModelDeploymentService()
llm_factory = LLMFactory(model_service=model_service)

# Step 1: Create deployment (one-time setup)
deployment = model_service.create_deployment({
    "name": "anthropic-claude-3",
    "provider": "anthropic",
    "model_name": "claude-3-5-sonnet-20241022",
    "credentials": {
        "api_key": "sk-ant-..."
    },
})
deployment_id = deployment['id']
print(f"✓ Created deployment: {deployment_id}")

# Step 2: Create base LLM config (in workflow)
base_config = LLMConfig(
    provider="",  # Will be filled from deployment
    model_name="",  # Will be filled from deployment
    temperature=0.7,
    max_tokens=2000,
    model_deployment_id=deployment_id,
)

# Step 3: Enrich config at runtime
enriched_config = model_service.enrich_llm_config(base_config)
print(f"✓ Enriched config:")
print(f"  Provider: {enriched_config.provider}")
print(f"  Model: {enriched_config.model_name}")
print(f"  Has credentials: {enriched_config.credentials is not None}")

# Step 4: Create LLM and use it
llm = llm_factory.create_llm(enriched_config)
response = llm.invoke("What is the capital of France?")
print(f"✓ LLM response: {response.content}")
```

---

### Example 3: Azure Managed Identity Setup

Example showing Azure OpenAI deployment with managed identity.

```python
from backend.services.model_deployment import ModelDeploymentService

service = ModelDeploymentService()

# Create Azure deployment with managed identity
deployment = service.create_deployment({
    "name": "azure-gpt-4-managed",
    "provider": "azure_openai",
    "model_name": "gpt-4",
    "model_type": "llm",
    "display_name": "Azure GPT-4 (Managed Identity)",
    "description": "Uses DefaultAzureCredential for authentication",
    "credentials": None,  # No API key needed
    "settings": {
        "use_managed_identity": True,
        "api_base": "https://myinstance.openai.azure.com",
        "api_version": "2024-02-15-preview",
        "deployment_name": "gpt-4-deployment",
    },
})

print(f"✓ Created Azure managed identity deployment: {deployment['id']}")
print(f"  Provider: {deployment['provider']}")
print(f"  Managed Identity: {deployment['settings']['use_managed_identity']}")
```

---

### Example 4: Rotating API Keys

Example showing credential rotation without affecting other settings.

```python
from backend.services.model_deployment import ModelDeploymentService

service = ModelDeploymentService()

deployment_id = "550e8400-e29b-41d4-a716-446655440000"

# Get current deployment
deployment = service.get_deployment(deployment_id)
print(f"Current deployment: {deployment['name']}")

# Rotate API key only
updated = service.update_deployment(
    deployment_id,
    {
        "credentials": {
            "api_key": "sk-new-key-rotated-..."
        }
    }
)

print(f"✓ Rotated API key for: {updated['name']}")
print(f"  Provider unchanged: {updated['provider']}")
print(f"  Model unchanged: {updated['model_name']}")
```

---

### Example 5: Testing Usage

Show how to test the service with mocks.

```python
import pytest
from unittest.mock import Mock, MagicMock
from backend.services.model_deployment import (
    ModelDeploymentService,
    CredentialEncryption,
    DeploymentNotFoundError,
)

@pytest.fixture
def mock_encryption():
    """Mock encryption service."""
    mock = Mock(spec=CredentialEncryption)
    mock.encrypt_credentials.return_value = {"api_key": "encrypted"}
    mock.decrypt_credentials.return_value = {"api_key": "decrypted"}
    return mock

@pytest.fixture
def service(mock_encryption):
    """Service with mocked encryption."""
    return ModelDeploymentService(credential_encryption=mock_encryption)

def test_create_deployment(service, mock_encryption):
    """Test creating a deployment."""
    payload = {
        "name": "test-deployment",
        "provider": "openai",
        "model_name": "gpt-4",
        "credentials": {"api_key": "test-key"}
    }

    # Mock database operations would go here
    # For now, test that encryption is called
    mock_encryption.encrypt_credentials.assert_not_called()

    # Call would trigger encryption
    # deployment = service.create_deployment(payload)
    # mock_encryption.encrypt_credentials.assert_called_once()

def test_enrich_llm_config_not_found(service):
    """Test enrichment with non-existent deployment."""
    from backend.models.workflow.configs.llm import LLMConfig

    config = LLMConfig(
        provider="",
        model_name="",
        model_deployment_id="non-existent-id"
    )

    with pytest.raises(DeploymentNotFoundError) as exc_info:
        service.enrich_llm_config(config)

    assert "non-existent-id" in str(exc_info.value)
```

---

## Performance Considerations

### Performance Characteristics

**CRUD Operations:**

- `list_deployments()`: O(n) where n is number of deployments; database query with index on `is_active`
- `get_deployment()`: O(1) lookup by primary key (UUID index)
- `create_deployment()`: O(1) insert with uniqueness check on `name` (indexed)
- `update_deployment()`: O(1) update by primary key
- `delete_deployment()`: O(1) soft delete (flag update) or hard delete

**Encryption Operations:**

- `encrypt_credentials()`: O(m) where m is number of credential keys; linear iteration
- `decrypt_credentials()`: O(m) where m is number of credential keys; linear iteration
- Encryption/decryption overhead: ~1-5ms per credential key (depends on encryption algorithm)

**Config Enrichment:**

- `enrich_llm_config()`: O(1) database lookup + O(m) decryption + deep copy overhead
- Deep copy overhead: ~0.1-1ms for typical config size

**Memory Usage:**

- Service instance: ~1-2 KB (lightweight, stateless)
- Credential encryption: Minimal overhead, no caching
- Config enrichment: Creates deep copy of config (~5-20 KB per config)

**I/O Characteristics:**

- **I/O-bound**: Database queries and encryption operations
- **Database connections**: Uses connection pool via `get_db()` context manager
- **Encryption**: CPU-bound encryption operations (typically fast)

---

### Optimisation Tips

#### Tip 1: Batch List Operations

**Problem:**

```python
# Inefficient: Multiple individual queries
for deployment_id in deployment_ids:
    deployment = service.get_deployment(deployment_id)
    process(deployment)
```

**Solution:**

```python
# Efficient: Single query with filtering
all_deployments = service.list_deployments()
deployment_map = {d['id']: d for d in all_deployments}

for deployment_id in deployment_ids:
    deployment = deployment_map.get(deployment_id)
    if deployment:
        process(deployment)
```

---

#### Tip 2: Cache Singleton Service Instance

**Problem:**

```python
# Inefficient: Creating service instance repeatedly
def process_workflow():
    service = ModelDeploymentService()  # New instance each call
    enriched = service.enrich_llm_config(config)
```

**Solution:**

```python
# Efficient: Singleton service instance
from functools import lru_cache

@lru_cache(maxsize=1)
def get_service():
    return ModelDeploymentService()

def process_workflow():
    service = get_service()  # Reuse cached instance
    enriched = service.enrich_llm_config(config)
```

---

#### Tip 3: Avoid Unnecessary Credential Decryption

**Problem:**

```python
# Inefficient: Always include credentials
deployments = service.list_deployments(include_credentials=True)
# Send to frontend (security risk + performance overhead)
```

**Solution:**

```python
# Efficient: Only decrypt when needed
# List without credentials (masked)
deployments = service.list_deployments(include_credentials=False)

# Decrypt only when editing specific deployment
deployment = service.get_deployment(deployment_id, include_credentials=True)
```

---

#### Tip 4: Minimise Config Enrichment Calls

**Problem:**

```python
# Inefficient: Enriching same config repeatedly in loop
for message in messages:
    enriched = service.enrich_llm_config(base_config)  # Repeated enrichment
    llm = factory.create_llm(enriched)
    response = llm.invoke(message)
```

**Solution:**

```python
# Efficient: Enrich once, reuse enriched config
enriched = service.enrich_llm_config(base_config)
llm = factory.create_llm(enriched)

for message in messages:
    response = llm.invoke(message)
```

---

### Async/Await Support

The model deployment service does **not** currently support async/await operations. All methods are synchronous.

**Current Pattern (Synchronous):**

```python
from backend.services.model_deployment import ModelDeploymentService

service = ModelDeploymentService()
deployment = service.get_deployment(deployment_id)
```

**Future Async Pattern (Not Yet Supported):**

```python
# This does NOT work yet
# service = AsyncModelDeploymentService()
# deployment = await service.get_deployment(deployment_id)
```

**Workaround for Async Contexts:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=5)

async def get_deployment_async(deployment_id: str):
    loop = asyncio.get_event_loop()
    service = ModelDeploymentService()
    return await loop.run_in_executor(
        executor,
        service.get_deployment,
        deployment_id
    )

# Use in async context
deployment = await get_deployment_async(deployment_id)
```

---

### Connection Pooling

The service uses SQLAlchemy's connection pooling via `get_db()` context manager. Connection pooling is handled
automatically by the database service.

```python
from backend.services.database import get_db

# Connection pool managed automatically
with get_db() as db:
    # Database operations use pooled connection
    deployment = db.query(ModelDeployment).filter(...).first()
# Connection returned to pool automatically
```

---

### Batch Operations

The service does not currently support explicit batch operations. For bulk updates, use individual calls within a single
database transaction.

**Pattern for Bulk Updates:**

```python
from backend.services.database import get_db
from backend.models import ModelDeployment

with get_db() as db:
    # Bulk update within single transaction
    deployments = db.query(ModelDeployment).filter(
        ModelDeployment.provider == "openai"
    ).all()

    for deployment in deployments:
        deployment.settings = {**deployment.settings, "new_field": "value"}

    db.commit()  # Single commit for all updates
```

---

## Testing Patterns

### Unit Testing

**Basic Unit Test:**

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.model_deployment import (
    ModelDeploymentService,
    CredentialEncryption,
    ConfigEnricher,
)

@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()

@pytest.fixture
def mock_encryption():
    """Mock encryption service."""
    mock = Mock(spec=CredentialEncryption)
    mock.encrypt_credentials.return_value = {"api_key": "encrypted_value"}
    mock.decrypt_credentials.return_value = {"api_key": "decrypted_value"}
    mock.merge_credentials.return_value = {"api_key": "merged_value"}
    return mock

@pytest.fixture
def service(mock_encryption):
    """Service with mocked encryption."""
    return ModelDeploymentService(credential_encryption=mock_encryption)

def test_encrypt_credentials(mock_encryption):
    """Test credential encryption."""
    credentials = {"api_key": "test-key"}
    encrypted = mock_encryption.encrypt_credentials(credentials)

    assert encrypted is not None
    assert "api_key" in encrypted
    mock_encryption.encrypt_credentials.assert_called_once_with(credentials)

def test_create_deployment_calls_encryption(service, mock_encryption):
    """Test that create_deployment encrypts credentials."""
    with patch('backend.services.model_deployment.service.get_db'):
        try:
            service.create_deployment({
                "name": "test",
                "provider": "openai",
                "model_name": "gpt-4",
                "credentials": {"api_key": "test-key"}
            })
        except:
            pass  # Ignore database errors

        # Verify encryption was called
        mock_encryption.encrypt_credentials.assert_called()
```

---

### Mocking Dependencies

**Mock Database Operations:**

```python
import pytest
from unittest.mock import patch, MagicMock
from backend.services.model_deployment import ModelDeploymentService
from backend.models import ModelDeployment

@patch('backend.services.model_deployment.service.get_db')
def test_list_deployments(mock_get_db):
    """Test listing deployments with mocked database."""
    # Setup mock database session
    mock_db = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_db

    # Setup mock query results
    mock_deployment = MagicMock(spec=ModelDeployment)
    mock_deployment.id = "123"
    mock_deployment.name = "test-deployment"
    mock_deployment.provider = "openai"
    mock_deployment.model_name = "gpt-4"
    mock_deployment.is_active = True
    mock_deployment.encrypted_credentials = {}

    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        mock_deployment
    ]

    # Test
    service = ModelDeploymentService()
    deployments = service.list_deployments()

    assert len(deployments) == 1
    assert deployments[0]['name'] == "test-deployment"
```

---

**Mock Encryption Service:**

```python
import pytest
from unittest.mock import Mock
from backend.services.model_deployment import CredentialEncryption

@pytest.fixture
def mock_encryptor():
    """Mock encryptor with fixed return values."""
    mock = Mock()
    mock.encrypt.side_effect = lambda x: f"encrypted_{x}"
    mock.decrypt.side_effect = lambda x: x.replace("encrypted_", "")
    return mock

def test_credential_encryption_with_mock(mock_encryptor):
    """Test encryption with mocked encryptor."""
    encryption = CredentialEncryption(encryptor=mock_encryptor)

    credentials = {"api_key": "test-key"}
    encrypted = encryption.encrypt_credentials(credentials)

    assert encrypted == {"api_key": "encrypted_test-key"}
    mock_encryptor.encrypt.assert_called_once_with("test-key")
```

---

### Integration Testing

**Integration Test with Real Database:**

```python
import pytest
from backend.services.model_deployment import ModelDeploymentService
from backend.services.database import get_db
from backend.models import ModelDeployment

@pytest.mark.integration
def test_create_and_retrieve_deployment():
    """Integration test with real database operations."""
    service = ModelDeploymentService()

    # Create deployment
    deployment = service.create_deployment({
        "name": f"integration-test-{uuid.uuid4()}",
        "provider": "openai",
        "model_name": "gpt-4",
        "credentials": {"api_key": "test-key"}
    })

    deployment_id = deployment['id']

    try:
        # Retrieve deployment
        retrieved = service.get_deployment(deployment_id)
        assert retrieved is not None
        assert retrieved['name'] == deployment['name']
        assert retrieved['provider'] == "openai"

        # Update deployment
        updated = service.update_deployment(
            deployment_id,
            {"display_name": "Updated Name"}
        )
        assert updated['display_name'] == "Updated Name"

    finally:
        # Cleanup
        service.delete_deployment(deployment_id, hard_delete=True)
```

---

## Best Practices

### Do's

✅ **Use dependency injection for testability**

```python
# Good: Inject dependencies for testing
from backend.services.model_deployment import (
    ModelDeploymentService,
    CredentialEncryption,
)

mock_encryption = Mock(spec=CredentialEncryption)
service = ModelDeploymentService(credential_encryption=mock_encryption)
```

---

✅ **Always mask credentials in API responses**

```python
# Good: Use include_credentials=False by default
deployments = service.list_deployments(include_credentials=False)

# Only include credentials for admin operations
if user.is_admin:
    deployment = service.get_deployment(id, include_credentials=True)
```

---

✅ **Use soft delete to preserve audit trail**

```python
# Good: Soft delete preserves history
service.delete_deployment(deployment_id, hard_delete=False)

# Hard delete only for compliance (GDPR, etc.)
if user_requested_data_deletion:
    service.delete_deployment(deployment_id, hard_delete=True)
```

---

✅ **Enrich configs at runtime, not at storage**

```python
# Good: Store minimal config, enrich at runtime
workflow_config = LLMConfig(
    model_deployment_id="550e8400-e29b-41d4-a716-446655440000",
    temperature=0.7,
)

# Enrich when executing
enriched = service.enrich_llm_config(workflow_config)
```

---

✅ **Handle exceptions specifically**

```python
# Good: Handle specific exceptions
from backend.services.model_deployment import (
    DeploymentNotFoundError,
    DuplicateDeploymentNameError,
)

try:
    deployment = service.create_deployment(payload)
except DuplicateDeploymentNameError as e:
    return {"error": "Name already exists", "name": e.name}
except DeploymentNotFoundError as e:
    return {"error": "Deployment not found", "id": e.deployment_id}
```

---

### Don'ts

❌ **Don't store decrypted credentials in workflow configs**

```python
# Bad: Storing decrypted credentials
workflow_config = LLMConfig(
    provider="openai",
    model_name="gpt-4",
    credentials={"api_key": "sk-..."},  # ❌ Security risk
)

# Good: Reference deployment ID only
workflow_config = LLMConfig(
    provider="",
    model_name="",
    model_deployment_id="550e8400-...",  # ✅ Secure reference
)
```

**Explanation:** Storing decrypted credentials in workflow configs risks exposing secrets in logs, database dumps, and
API responses.

---

❌ **Don't create service instances repeatedly**

```python
# Bad: Creating service in hot path
def process_message(message):
    service = ModelDeploymentService()  # ❌ Expensive
    enriched = service.enrich_llm_config(config)

# Good: Reuse service instance
service = ModelDeploymentService()

def process_message(message):
    enriched = service.enrich_llm_config(config)  # ✅ Efficient
```

**Explanation:** Service instances are lightweight but creating them repeatedly adds unnecessary overhead. Use singleton
pattern or dependency injection.

---

❌ **Don't ignore encryption errors**

```python
# Bad: Swallowing encryption errors
try:
    deployment = service.create_deployment(payload)
except Exception:
    pass  # ❌ Silent failure

# Good: Handle and log encryption errors
try:
    deployment = service.create_deployment(payload)
except EncryptionError as e:
    logger.error(f"Encryption failed for key '{e.key}': {e.original_error}")
    raise  # ✅ Propagate critical error
```

**Explanation:** Encryption failures indicate system-level issues (missing encryption key, corrupted data). These must
be logged and handled, not silenced.

---

## Related Documentation

### Related Services

- [LLM Models Service](./llm_models.md) - LLM provider factory using model deployments
- [Execution Service](./execution.md) - Workflow execution enriching configs at runtime
- [Graph Service](./graph.md) - Graph manager validating and building agent configs
- [Database Service](./database.md) - Database session management and models

### Related API Modules

- [Model Deployments API](../agents-guide/api/model_deployments.md) - REST endpoints for CRUD operations

### Architecture Documentation

- [Design Principles](../architecture/03-design-principles.md) - Clean architecture and separation of concerns

### External Documentation

- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/) - Database ORM used by the service
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/) - Symmetric encryption (used by encryption_utils)

---

## Summary

The model deployment service provides comprehensive management for LLM model deployments in AgenticStudio. It acts as a
central registry for LLM provider configurations, handling persistence, validation, credential security, and runtime
enrichment. The service follows clean architecture principles with clear separation between persistence, domain logic,
security, and presentation layers.

The service enables workflows to reference model deployments by ID rather than storing sensitive credentials directly in
workflow configurations. At runtime, the service enriches LLM configurations with deployment-specific settings and
decrypted credentials, enabling secure and maintainable LLM integrations.

**Key Features:**

- Complete CRUD operations for model deployment configurations
- Secure credential encryption and decryption using backend encryption utilities
- Runtime configuration enrichment for workflow LLM nodes
- Validation and normalisation of deployment settings
- Support for multiple LLM providers (OpenAI, Anthropic, Azure, etc.)
- Azure Managed Identity support for credential-less authentication
- Default deployment management per model type (LLM vs embedding)

**Primary Use Cases:**

- Configure reusable LLM provider deployments across workflows
- Securely store and manage API keys and credentials
- Dynamically inject deployment settings at workflow execution time
- Test model deployment connections before saving
- Support multi-tenant or multi-environment model configurations

**When to Use This Service:**

- Creating or updating LLM provider configurations in the UI
- Enriching workflow LLM configurations before execution
- Managing API keys and credentials securely
- Supporting multiple models or providers in a single application
- Implementing Azure Managed Identity authentication for LLMs
