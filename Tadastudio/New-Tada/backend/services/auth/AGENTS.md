# Authentication Service

## Overview

The Authentication Service provides OAuth2 proxy authentication and user API token management for the AgenticStudio backend.
It handles JWT token validation, user synchronization to the database, and Personal Access Token (PAT) management for
programmatic access to workflows.

**Location:** [backend/services/auth/](../../backend/services/auth/)

**Primary Responsibilities:**

- OAuth2 proxy authentication with Azure AD/OIDC integration
- JWT token extraction and validation
- User database synchronization from authentication claims
- Personal Access Token (PAT) creation and management
- Token-based workflow access control
- Authentication configuration management

**Key Use Cases:**

- Validating authenticated users behind oauth2-proxy
- Syncing user profiles to the database from JWT claims
- Generating API tokens for HTTP workflow execution
- Managing authentication modes (basic vs OAuth proxy)
- Extracting user information from various token formats

## Architecture

### Module Structure

```
backend/services/auth/
├── __init__.py                  # Module exports and public API
├── config.py                    # Authentication configuration (AuthConfig)
├── exceptions.py                # Custom authentication exceptions
├── jwt_utils.py                 # JWT token decoding utilities
├── token_extractor.py           # Token extraction from requests
├── user_sync.py                 # User database synchronization
├── user_api_token_service.py   # Personal Access Token management
└── providers/                   # Authentication provider implementations
    ├── __init__.py              # Provider exports
    └── oauth2_proxy.py          # OAuth2ProxyAuth provider
```

**File Purposes:**

- **config.py** - Centralises authentication configuration from environment variables, supporting multiple auth modes (
  basic, oauth_proxy)
- **exceptions.py** - Defines HTTP exception hierarchy for authentication errors with appropriate status codes
- **jwt_utils.py** - Provides unverified JWT decoding for claim extraction when tokens are already validated by
  oauth2-proxy
- **token_extractor.py** - Extracts authentication tokens from multiple sources (headers, credentials, OAuth proxy
  headers)
- **user_sync.py** - Persists and updates user records in the database from authentication claims
- **user_api_token_service.py** - Manages user-generated API tokens (Personal Access Tokens) for programmatic access
- **providers/oauth2_proxy.py** - Implements OAuth2 proxy authentication with Azure AD JWT validation

### Design Patterns

**1. Provider Pattern**

The service uses a provider pattern for authentication strategies:

```
Authentication Request
        ↓
  get_oauth_proxy_auth()
        ↓
   OAuth2ProxyAuth (singleton)
        ↓
   verify_and_sync()
        ↓
  JWT Validation + User Sync
```

**2. Singleton Pattern**

Authentication providers are singleton instances:

- `AuthConfig` - Global configuration instance
- `OAuth2ProxyAuth` - Single provider instance per application lifecycle

**3. Strategy Pattern**

Token extraction uses multiple strategies in priority order:

1. HTTPAuthorizationCredentials object
2. Authorization header (Bearer token)
3. X-Auth-Request-Access-Token header (OAuth proxy)

**4. Dependency Injection Pattern**

FastAPI dependencies inject authenticated user claims:

```python
from backend.api.auth.dependencies import get_current_user

@router.get("/protected")
async def endpoint(claims = Depends(get_current_user)):
    # claims contains validated user information
    pass
```

### Dependencies

**Internal Dependencies:**

- `backend.models.auth.user` - User database model
- `backend.services.database` - Database session management
- `backend.services.config` - Logging configuration

**External Dependencies:**

- `PyJWT` - JWT token encoding/decoding and validation
- `bcrypt` - Password and token hash generation/verification
- `fastapi` - HTTPException and request handling
- `sqlalchemy` - Database ORM for user persistence

**Database Dependencies:**

- `users` table - User profile storage
- `user_api_tokens` table - Personal Access Token storage
- `workflows` table - Workflow ownership verification
- `workflow_memberships` table - Workflow access control

**Environment Variables:**

- `AUTH_MODE` - Authentication mode ("basic" or "oauth_proxy")
- `OAUTH_PROXY_DISABLE_JWT_VALIDATION` - Disable JWT signature validation
- `JWT_SECRET` - Secret key for JWT signing (basic mode)
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_EXPIRATION_HOURS` - Token expiration time
- `AZURE_TENANT_ID` - Azure AD tenant ID
- `AZURE_CLIENT_ID` - Azure AD client/application ID
- `AZURE_ALLOWED_AUDIENCES` - Comma-separated allowed JWT audiences
- `AZURE_AUTHORITY` - Azure AD authority URL
- `AZURE_JWKS_URL` - Override JWKS URL for custom identity providers

## Public API

### Exported Classes

- `AuthConfig` - Authentication configuration container
- `OAuth2ProxyAuth` - OAuth2 proxy authentication provider
- `UserAPITokenService` - Personal Access Token management service

### Exported Functions

- `get_auth_config()` - Get global authentication configuration
- `get_oauth_proxy_auth()` - Get OAuth2 proxy auth singleton instance
- `extract_token_from_request()` - Extract token from request using multiple strategies
- `log_auth_headers()` - Log authentication headers for debugging
- `sync_user_from_claims()` - Persist user from authentication claims
- `enrich_claims()` - Enrich claims with email, name, and auth source

### Exceptions

```
HTTPException
├── AuthenticationError (401)
│   ├── InvalidTokenError (401)
│   ├── MissingTokenError (401)
│   ├── InvalidCredentialsError (401)
│   └── MissingEmailClaimError (401)
├── OAuth2ConfigurationError (500)
├── RequestContextUnavailableError (500)
└── DisabledFeatureError (405)

Exception
└── UserSyncError (internal, non-HTTP)
```

## Core Classes

### `AuthConfig`

Configuration container for all authentication settings.

**Purpose:** Centralise authentication configuration from environment variables and provide helper methods for auth mode
detection.

**Responsibilities:**

- Load and validate environment variables
- Determine authentication mode (basic vs OAuth proxy)
- Configure Azure AD settings and JWKS URL
- Build allowed audience sets
- Validate OAuth configuration requirements

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise authentication configuration from environment variables."""
```

**Key Methods:**

#### `is_oauth_proxy_mode()`

```python
def is_oauth_proxy_mode(self) -> bool:
    """Check if running in OAuth2 proxy mode.

    Returns:
        True if auth mode is "oauth_proxy", False otherwise
    """
```

**Returns:**

- `bool` - True if AUTH_MODE environment variable is "oauth_proxy"

**Example:**

```python
from backend.services.auth import get_auth_config

config = get_auth_config()
if config.is_oauth_proxy_mode():
    print("Using OAuth2 proxy authentication")
else:
    print("Using basic authentication")
```

**Use Cases:**

- Conditional authentication logic in API endpoints
- Feature flags for auth-mode-specific functionality
- Configuration validation during application startup

#### `is_basic_mode()`

```python
def is_basic_mode(self) -> bool:
    """Check if running in basic authentication mode.

    Returns:
        True if auth mode is "basic", False otherwise
    """
```

**Returns:**

- `bool` - True if AUTH_MODE environment variable is "basic"

**Example:**

```python
config = get_auth_config()
if config.is_basic_mode():
    # Use username/password authentication
    pass
```

#### `validate_oauth_config()`

```python
def validate_oauth_config(self) -> None:
    """Validate OAuth2 proxy configuration.

    Raises:
        ValueError: If OAuth proxy mode enabled but required config missing
    """
```

**Raises:**

- `ValueError` - When OAuth proxy mode is enabled but AZURE_TENANT_ID or AZURE_JWKS_URL is not set and JWT validation is
  enabled

**Example:**

```python
config = get_auth_config()
try:
    config.validate_oauth_config()
    print("OAuth configuration valid")
except ValueError as e:
    logger.error(f"Invalid OAuth config: {e}")
```

**Behaviour:**

- Only validates when `is_oauth_proxy_mode()` returns True
- Skips validation if `oauth_proxy_disable_jwt_validation` is True
- Checks that JWKS URL is configured for JWT signature verification

**Class Attributes:**

- `auth_mode: str` - Current authentication mode ("basic" or "oauth_proxy")
- `oauth_proxy_disable_jwt_validation: bool` - Whether to skip JWT signature validation
- `jwt_secret: str` - Secret key for JWT signing (basic mode)
- `jwt_algorithm: str` - JWT algorithm (default: "HS256")
- `jwt_expiration_hours: int` - JWT expiration time in hours (default: 24)
- `azure_tenant_id: Optional[str]` - Azure AD tenant ID
- `azure_client_id: Optional[str]` - Azure AD client/application ID
- `allowed_audiences: Set[str]` - Set of allowed JWT audiences
- `azure_authority: str` - Azure AD authority URL
- `expected_issuer: Optional[str]` - Expected JWT issuer
- `azure_jwks_url: Optional[str]` - JWKS URL for token validation

---

### `OAuth2ProxyAuth`

OAuth2 proxy authentication provider for validating tokens forwarded by oauth2-proxy.

**Purpose:** Validate access tokens from oauth2-proxy, verify JWT signatures against Azure AD JWKS, and synchronise
authenticated users to the database.

**Responsibilities:**

- Decode and validate JWT tokens using JWKS
- Verify token signature, audience, issuer, and expiration
- Support configurable JWT validation (can be disabled)
- Enrich claims with additional information
- Synchronise user to database
- Handle Azure AD and generic OIDC tokens

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise OAuth2 proxy authentication.

    Raises:
        ValueError: If JWT validation enabled but JWKS URL not configured
    """
```

**Example:**

```python
from backend.services.auth.providers import OAuth2ProxyAuth

auth = OAuth2ProxyAuth()
# JWKS client initialised if JWT validation enabled
```

**Key Methods:**

#### `verify_and_sync()`

```python
def verify_and_sync(
    self,
    token: str,
    request: Request,
) -> Dict[str, Any]:
    """Validate the token, hydrate claims, and persist the user.

    This is the main entry point for OAuth2 proxy authentication.
    """
```

**Parameters:**

- `token` (str) - JWT access token from oauth2-proxy
- `request` (Request) - FastAPI Request object

**Returns:**

- `Dict[str, Any]` - Complete user claims dictionary containing:
  - `sub` - Subject (user ID)
  - `email` - User email address
  - `name` - Full name
  - `given_name` - First name
  - `family_name` - Last name
  - `oid` - Object ID (Azure AD)
  - `tid` - Tenant ID (Azure AD)
  - `auth_source` - Authentication source ("azure_ad")
  - `aud` - Audience
  - `iss` - Issuer

**Raises:**

- `InvalidTokenError` - If token validation fails

**Example:**

```python
from fastapi import Request
from backend.services.auth.providers import get_oauth_proxy_auth

auth = get_oauth_proxy_auth()
token = request.headers.get("X-Auth-Request-Access-Token")

try:
    claims = auth.verify_and_sync(token, request)
    print(f"Authenticated user: {claims['email']}")
    print(f"User ID: {claims['sub']}")
except InvalidTokenError as e:
    print(f"Authentication failed: {e}")
```

**Behaviour:**

- Decodes and validates JWT token (or skips validation if disabled)
- Extracts email from X-Auth-Request-Email header as fallback
- Enriches claims with header information
- Syncs user to database (creates new user if doesn't exist)
- Updates last login timestamp
- Returns enriched claims dictionary

**Use Cases:**

- Primary authentication method for oauth2-proxy deployments
- User profile extraction from JWT tokens
- Automatic user provisioning from OAuth providers
- Session tracking and last login updates

---

### `UserAPITokenService`

Service for managing user-generated API tokens (Personal Access Tokens) for programmatic workflow access.

**Purpose:** Provide CRUD operations for Personal Access Tokens that allow users to authenticate HTTP workflow execution
requests without OAuth.

**Responsibilities:**

- Generate cryptographically secure API tokens
- Hash tokens using bcrypt for secure storage
- Validate tokens and check workflow access permissions
- Manage token lifecycle (create, list, revoke)
- Track token usage statistics
- Enforce token expiration and scope-based access control

**Initialisation:**

This is a static service class - no instance creation needed.

**Example:**

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

# All methods are static
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Production API Token"
)
```

**Key Methods:**

#### `create_token()`

```python
@staticmethod
def create_token(
    user_id: str,
    token_name: str,
    scopes: List[str] = None,
    description: str = None,
    expires_in_days: int = None,
) -> Tuple[UserAPIToken, str]:
    """Create a new user API token."""
```

**Parameters:**

- `user_id` (str) - User email who owns this token
- `token_name` (str) - User-friendly name for the token
- `scopes` (List[str]) - List of scopes (default: ["workflow:*"])
  - Format: `"workflow:*"` for all workflows
  - Format: `"workflow:{workflow_id}"` for specific workflow
- `description` (str) - Optional description of token purpose
- `expires_in_days` (int) - Days until expiration (None for no expiration)

**Returns:**

- `Tuple[UserAPIToken, str]` - (token object, plaintext token string)
  - The plaintext token is only returned once and should be displayed to the user
  - Token format: `"na_{random_43_chars}"`

**Example:**

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

# Create token with all workflows access
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Production Integration",
    scopes=["workflow:*"],
    description="Token for production CI/CD pipeline",
    expires_in_days=90
)

# IMPORTANT: Show plaintext token to user (only shown once)
print(f"Your API token: {plaintext}")
print(f"Token ID: {token_obj.id}")
print(f"Expires: {token_obj.expires_at}")

# Create token for specific workflow
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Customer Support Bot Token",
    scopes=["workflow:support-workflow-uuid"],
    expires_in_days=365
)
```

**Behaviour:**

- Generates cryptographically secure token using `secrets.token_urlsafe()`
- Hashes token with bcrypt before storage (plaintext never stored)
- Creates token prefix for display (first 11 characters)
- Saves token record to database
- Returns both database object and plaintext token

**Use Cases:**

- Creating API tokens for CI/CD pipelines
- Generating tokens for third-party integrations
- Providing programmatic access to published workflows
- Testing workflow APIs without OAuth

#### `validate_token()`

```python
@staticmethod
def validate_token(
    plaintext_token: str,
    workflow_name: str = None,
) -> Optional[Tuple[UserAPIToken, str]]:
    """Validate a token and check workflow access."""
```

**Parameters:**

- `plaintext_token` (str) - The plaintext token to validate
- `workflow_name` (str) - Optional workflow ID/name to check access for

**Returns:**

- `Optional[Tuple[UserAPIToken, str]]` - (token object, user_id) if valid, None otherwise

**Raises:**

- No exceptions raised; returns None on validation failure

**Example:**

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

# Validate token for any workflow
result = UserAPITokenService.validate_token("na_abc123...")
if result:
    token_obj, user_id = result
    print(f"Valid token for user: {user_id}")
    print(f"Token name: {token_obj.token_name}")
    print(f"Scopes: {token_obj.scopes}")
else:
    print("Invalid or expired token")

# Validate token for specific workflow
result = UserAPITokenService.validate_token(
    "na_abc123...",
    workflow_name="support-workflow-uuid"
)
if result:
    token_obj, user_id = result
    print(f"Token has access to workflow")
else:
    print("Token invalid or lacks workflow access")
```

**Behaviour:**

- Checks token format (must start with "na_")
- Extracts token prefix for fast lookup
- Queries database for active tokens with matching prefix
- Verifies token hash using bcrypt
- Checks token expiration
- Validates workflow access based on scopes
- Verifies user ownership/membership of workflow
- Updates usage statistics (last_used_at, usage_count)
- Returns token object and user ID if all checks pass

**Use Cases:**

- Authenticating HTTP workflow execution requests
- Validating API tokens in middleware
- Enforcing workflow-level access control
- Tracking token usage for security auditing

#### `list_user_tokens()`

```python
@staticmethod
def list_user_tokens(user_id: str) -> List[UserAPIToken]:
    """List all tokens for a user."""
```

**Parameters:**

- `user_id` (str) - User email to list tokens for

**Returns:**

- `List[UserAPIToken]` - List of token objects (sorted by created_at descending)

**Example:**

```python
tokens = UserAPITokenService.list_user_tokens("user@example.com")

for token in tokens:
    print(f"Name: {token.token_name}")
    print(f"Prefix: {token.token_prefix}")
    print(f"Created: {token.created_at}")
    print(f"Active: {token.is_active}")
    print(f"Scopes: {token.scopes}")
    print(f"Usage: {token.usage_count} times")
    print(f"Last used: {token.last_used_at}")
    print("---")
```

**Use Cases:**

- Displaying user's API tokens in settings UI
- Token management dashboards
- Auditing user access patterns

#### `revoke_token()`

```python
@staticmethod
def revoke_token(token_id: str, user_id: str = None) -> bool:
    """Revoke (deactivate) a token."""
```

**Parameters:**

- `token_id` (str) - Token UUID to revoke
- `user_id` (str) - Optional user ID to verify ownership

**Returns:**

- `bool` - True if token revoked, False if not found

**Example:**

```python
# Revoke token with ownership check
success = UserAPITokenService.revoke_token(
    token_id="token-uuid-here",
    user_id="user@example.com"
)

if success:
    print("Token revoked successfully")
else:
    print("Token not found or access denied")
```

**Behaviour:**

- Sets `is_active = False` on token
- Updates `updated_at` timestamp
- Logs revocation for audit trail
- Does not delete token (preserves history)

**Use Cases:**

- User-initiated token revocation from settings
- Automatic revocation on security events
- Token rotation workflows
- Emergency access removal

#### `update_token_scopes()`

```python
@staticmethod
def update_token_scopes(
    token_id: str,
    user_id: str,
    scopes: List[str],
) -> Optional[UserAPIToken]:
    """Update token scopes."""
```

**Parameters:**

- `token_id` (str) - Token UUID
- `user_id` (str) - User ID to verify ownership
- `scopes` (List[str]) - New list of scopes

**Returns:**

- `Optional[UserAPIToken]` - Updated token object or None if not found

**Example:**

```python
# Update token to specific workflow access
updated = UserAPITokenService.update_token_scopes(
    token_id="token-uuid",
    user_id="user@example.com",
    scopes=["workflow:workflow-1", "workflow:workflow-2"]
)

if updated:
    print(f"Updated scopes: {updated.scopes}")
```

**Use Cases:**

- Restricting token access to specific workflows
- Expanding token permissions
- Security hardening by limiting scope

**Class Attributes:**

- `TOKEN_PREFIX: str` - Token prefix ("na" for Agentic Studio)
- `TOKEN_LENGTH: int` - Token length in bytes (32 = 43 chars base64)

---

## Functions

### `get_auth_config()`

Get the global authentication configuration instance.

**Signature:**

```python
def get_auth_config() -> AuthConfig:
    """Get the global authentication configuration instance.

    Returns:
        AuthConfig: The global auth configuration
    """
```

**Parameters:**

- None

**Returns:**

- `AuthConfig` - Singleton authentication configuration instance

**Example:**

```python
from backend.services.auth import get_auth_config

config = get_auth_config()
print(f"Auth mode: {config.auth_mode}")
print(f"Azure tenant: {config.azure_tenant_id}")

if config.is_oauth_proxy_mode():
    print("OAuth proxy enabled")
```

**Use Cases:**

- Accessing auth configuration from anywhere in the application
- Conditional logic based on auth mode
- Configuration validation during startup

---

### `get_oauth_proxy_auth()`

Get or create the global OAuth2ProxyAuth singleton instance.

**Signature:**

```python
def get_oauth_proxy_auth() -> Optional[OAuth2ProxyAuth]:
    """Get or create the global OAuth2ProxyAuth instance.

    Returns:
        Optional[OAuth2ProxyAuth]: Auth instance if in oauth_proxy mode, None otherwise
    """
```

**Parameters:**

- None

**Returns:**

- `Optional[OAuth2ProxyAuth]` - OAuth2ProxyAuth instance if AUTH_MODE is "oauth_proxy", None if in basic mode

**Example:**

```python
from backend.services.auth.providers import get_oauth_proxy_auth

auth = get_oauth_proxy_auth()

if auth:
    # OAuth proxy mode is enabled
    claims = auth.verify_and_sync(token, request)
else:
    # Basic auth mode or OAuth not configured
    print("OAuth proxy not available")
```

**Use Cases:**

- Dependency injection in API endpoints
- Conditional authentication flows
- Testing OAuth authentication logic

---

### `extract_token_from_request()`

Extract authentication token from request using multiple strategies.

**Signature:**

```python
def extract_token_from_request(
    request: Optional[Request],
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """Extract authentication token from request.

    Tries multiple sources in order:
    1. HTTPAuthorizationCredentials object
    2. Authorization header (Bearer token)
    3. X-Auth-Request-Access-Token header (OAuth proxy)
    """
```

**Parameters:**

- `request` (Optional[Request]) - FastAPI Request object
- `credentials` (Optional[HTTPAuthorizationCredentials]) - Security dependency credentials

**Returns:**

- `Optional[str]` - First token found, or None if no token present

**Example:**

```python
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.auth import extract_token_from_request

security = HTTPBearer(auto_error=False)

async def my_endpoint(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = extract_token_from_request(request, credentials)

    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    # Use token for authentication
    print(f"Token: {token[:20]}...")
```

**Behaviour:**

- Checks credentials object first (fastest)
- Falls back to Authorization header parsing
- Checks OAuth proxy header only in oauth_proxy mode
- Returns None if no token found (doesn't raise exceptions)

**Use Cases:**

- Extracting tokens in authentication middleware
- Supporting multiple token formats
- OAuth proxy header forwarding

---

### `log_auth_headers()`

Log authentication-related headers for debugging.

**Signature:**

```python
def log_auth_headers(request: Request) -> None:
    """Log authentication-related headers for debugging.

    Only logs at DEBUG level.
    """
```

**Parameters:**

- `request` (Request) - FastAPI Request object

**Returns:**

- None

**Example:**

```python
from backend.services.auth import log_auth_headers

async def endpoint(request: Request):
    # Debug authentication issues
    log_auth_headers(request)
    # Logs: auth mode, headers present, cookies, etc.
```

**Use Cases:**

- Troubleshooting authentication failures
- Debugging OAuth proxy configuration
- Development and testing

---

### `sync_user_from_claims()`

Persist or update authenticated user in the database from claims.

**Signature:**

```python
def sync_user_from_claims(claims: Dict[str, Any]) -> None:
    """Persist or update authenticated user in database.

    Creates new user if doesn't exist, updates existing user info.
    """
```

**Parameters:**

- `claims` (Dict[str, Any]) - Authentication claims dictionary containing:
  - `sub` (required) - User ID
  - `email` (optional) - Email address
  - `name` (optional) - Full name
  - `given_name` (optional) - First name
  - `family_name` (optional) - Last name
  - `tid` (optional) - Tenant ID
  - `oid` (optional) - Object ID

**Returns:**

- None

**Raises:**

- No exceptions raised; errors logged as warnings

**Example:**

```python
from backend.services.auth import sync_user_from_claims

claims = {
    "sub": "user-123",
    "email": "john.doe@example.com",
    "name": "John Doe",
    "given_name": "John",
    "family_name": "Doe",
    "tid": "tenant-123",
    "oid": "object-123"
}

# Sync user to database
sync_user_from_claims(claims)

# User created or updated in database
# - Creates new user if sub not found
# - Updates email, name, tenant_id, object_id
# - Updates last_login_at timestamp
# - Stores claims in last_claims field
```

**Behaviour:**

- Creates new user if `sub` (user ID) not in database
- Updates existing user with latest claim values
- Preserves existing values if claims don't contain fields
- Updates `last_login_at` to current UTC time
- Stores complete claims dictionary in `last_claims` field
- Does not raise exceptions (logs warnings on failure)
- Uses context manager for automatic database session cleanup

**Use Cases:**

- Automatic user provisioning from OAuth
- Syncing user profile updates from identity provider
- Tracking last login timestamps
- Storing identity provider metadata

---

### `enrich_claims()`

Enrich authentication claims with additional fields.

**Signature:**

```python
def enrich_claims(
    claims: Dict[str, Any],
    header_email: str = None,
    auth_source: str = "azure_ad",
) -> Dict[str, Any]:
    """Enrich claims with email, name, and auth source.

    Applies all enrichment operations and returns modified claims.
    """
```

**Parameters:**

- `claims` (Dict[str, Any]) - Authentication claims dictionary (modified in-place)
- `header_email` (str) - Optional email from X-Auth-Request-Email header
- `auth_source` (str) - Authentication source identifier (default: "azure_ad")

**Returns:**

- `Dict[str, Any]` - Enriched claims dictionary (same object as input)

**Example:**

```python
from backend.services.auth import enrich_claims

claims = {
    "sub": "user-123",
    "given_name": "John",
    "family_name": "Doe"
}

# Enrich claims
enriched = enrich_claims(
    claims,
    header_email="john.doe@example.com",
    auth_source="azure_ad"
)

print(enriched)
# {
#     "sub": "user-123",
#     "given_name": "John",
#     "family_name": "Doe",
#     "email": "john.doe@example.com",  # Added from header
#     "name": "John Doe",                # Constructed from given/family
#     "auth_source": "azure_ad"          # Added
# }
```

**Behaviour:**

- Adds email from multiple sources (claims, headers)
- Constructs full name from given_name + family_name
- Adds auth_source field
- Modifies claims dictionary in-place
- Preserves existing claim values

**Use Cases:**

- Normalising claims from different OAuth providers
- Ensuring required fields exist
- Tracking authentication source for auditing

---

## Configuration

### Environment Variables

#### Core Authentication

- `AUTH_MODE` - Authentication mode
  - Values: `"basic"` or `"oauth_proxy"`
  - Default: `"basic"`
  - Required: No
  - Description: Determines authentication strategy

#### OAuth2 Proxy Settings

- `OAUTH_PROXY_DISABLE_JWT_VALIDATION` - Disable JWT signature validation
  - Values: `"true"`, `"false"`, `"1"`, `"yes"`
  - Default: `"false"`
  - Required: No
  - Description: Skip JWT signature verification (oauth2-proxy trusted)

#### Basic Auth JWT Settings

- `JWT_SECRET` - Secret key for JWT signing
  - Default: `"your-secret-key-change-in-production"`
  - Required: Yes (in production with basic auth)
  - Description: Secret for signing/verifying JWT tokens

- `JWT_ALGORITHM` - JWT signing algorithm
  - Default: `"HS256"`
  - Required: No
  - Description: Algorithm for JWT signatures

- `JWT_EXPIRATION_HOURS` - Token expiration time
  - Default: `24`
  - Required: No
  - Description: Hours until JWT expiration

#### Azure AD / OIDC Settings

- `AZURE_TENANT_ID` - Azure AD tenant ID
  - Default: None
  - Required: Yes (for OAuth proxy with JWT validation)
  - Description: Azure tenant identifier
  - Example: `"12345678-1234-1234-1234-123456789012"`

- `AZURE_CLIENT_ID` - Azure AD client/application ID
  - Default: None
  - Required: No (but recommended)
  - Description: Application registration client ID
  - Example: `"87654321-4321-4321-4321-210987654321"`

- `AZURE_ALLOWED_AUDIENCES` - Allowed JWT audiences
  - Default: None
  - Required: No
  - Description: Comma-separated list of valid audiences
  - Example: `"api://myapp,https://myapp.example.com"`

- `AZURE_AUTHORITY` - Azure AD authority URL
  - Default: `"https://login.microsoftonline.com"`
  - Required: No
  - Description: Identity provider authority

- `AZURE_JWKS_URL` - JWKS endpoint URL
  - Default: Constructed from tenant ID if not provided
  - Required: Yes (if AZURE_TENANT_ID not set)
  - Description: Override for custom identity providers
  - Example: `"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"`

### Initialisation Patterns

#### Basic Initialisation (Get Configuration)

```python
from backend.services.auth import get_auth_config

# Get global configuration
config = get_auth_config()

# Check authentication mode
if config.is_oauth_proxy_mode():
    print("Using OAuth proxy")
elif config.is_basic_mode():
    print("Using basic auth")
```

#### OAuth2 Proxy Authentication

```python
from backend.services.auth.providers import get_oauth_proxy_auth
from fastapi import Request

# Get OAuth provider (returns None if not in oauth_proxy mode)
auth = get_oauth_proxy_auth()

if auth:
    # Validate token
    token = request.headers.get("X-Auth-Request-Access-Token")
    claims = auth.verify_and_sync(token, request)
    print(f"User: {claims['email']}")
```

#### User API Token Service

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

# Create token (static method, no instance needed)
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="API Integration",
    scopes=["workflow:*"],
    expires_in_days=90
)

# Store plaintext securely (only shown once)
print(f"Token: {plaintext}")
```

#### FastAPI Dependency Injection

```python
from fastapi import Depends, FastAPI
from backend.api.auth.dependencies import get_current_user

app = FastAPI()

@app.get("/protected")
async def protected_endpoint(claims = Depends(get_current_user)):
    """Endpoint requiring authentication."""
    return {
        "email": claims["email"],
        "user_id": claims["sub"]
    }
```

## Error Handling

### Exception Hierarchy

```
Exception
│
├── HTTPException (FastAPI)
│   │
│   ├── AuthenticationError (401 Unauthorized)
│   │   ├── InvalidTokenError (401)
│   │   ├── MissingTokenError (401)
│   │   ├── InvalidCredentialsError (401)
│   │   └── MissingEmailClaimError (401)
│   │
│   ├── OAuth2ConfigurationError (500 Internal Server Error)
│   ├── RequestContextUnavailableError (500 Internal Server Error)
│   └── DisabledFeatureError (405 Method Not Allowed)
│
└── UserSyncError (internal, non-HTTP)
```

### Exception Details

#### `AuthenticationError`

Base exception for all authentication failures.

**Inherits from:** `HTTPException`

**HTTP Status:** 401 Unauthorized

**When raised:**

- Generic authentication failures
- Base class for specific auth errors

**Example:**

```python
from backend.services.auth import AuthenticationError

try:
    # Authenticate user
    pass
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e.detail}")
    # Returns 401 with error detail
```

---

#### `InvalidTokenError`

Token is invalid, expired, or signature verification failed.

**Inherits from:** `AuthenticationError`

**HTTP Status:** 401 Unauthorized

**When raised:**

- JWT signature verification fails
- Token has expired
- Token format is invalid
- Required claims missing

**Example:**

```python
from backend.services.auth import InvalidTokenError
from backend.services.auth.providers import get_oauth_proxy_auth

auth = get_oauth_proxy_auth()

try:
    claims = auth.verify_and_sync(token, request)
except InvalidTokenError as e:
    # Token validation failed
    return {"error": "Please re-authenticate"}
```

---

#### `MissingTokenError`

Authentication token not provided in request.

**Inherits from:** `AuthenticationError`

**HTTP Status:** 401 Unauthorized

**When raised:**

- No Authorization header present
- Bearer token format incorrect
- OAuth proxy headers missing

**Example:**

```python
from backend.services.auth import MissingTokenError, extract_token_from_request

token = extract_token_from_request(request, credentials)

if not token:
    raise MissingTokenError("Authorization required")
```

---

#### `InvalidCredentialsError`

User credentials (username/password) are incorrect.

**Inherits from:** `AuthenticationError`

**HTTP Status:** 401 Unauthorized

**When raised:**

- Username not found
- Password doesn't match hash
- Basic auth login fails

**Example:**

```python
from backend.services.auth import InvalidCredentialsError

if not user or not verify_password(password, user.password_hash):
    raise InvalidCredentialsError()
```

---

#### `MissingEmailClaimError`

JWT token missing required email claim.

**Inherits from:** `AuthenticationError`

**HTTP Status:** 401 Unauthorized

**When raised:**

- JWT doesn't contain email field
- No email in alternative claim fields
- OAuth proxy email header missing

**Example:**

```python
from backend.services.auth import MissingEmailClaimError

if not claims.get("email"):
    raise MissingEmailClaimError("Email claim required")
```

---

#### `OAuth2ConfigurationError`

OAuth2 authentication is not properly configured.

**Inherits from:** `HTTPException`

**HTTP Status:** 500 Internal Server Error

**When raised:**

- OAuth proxy mode enabled but JWKS URL missing
- Required Azure AD configuration missing
- JWT validation enabled but tenant ID not set

**Example:**

```python
from backend.services.auth import OAuth2ConfigurationError, get_auth_config

config = get_auth_config()

try:
    config.validate_oauth_config()
except ValueError:
    raise OAuth2ConfigurationError(
        "AZURE_TENANT_ID required for OAuth proxy mode"
    )
```

---

#### `RequestContextUnavailableError`

HTTP request context not available but required.

**Inherits from:** `HTTPException`

**HTTP Status:** 500 Internal Server Error

**When raised:**

- Authentication requires Request object but it's None
- Called outside of HTTP request context
- Testing scenarios without mock request

**Example:**

```python
from backend.services.auth import RequestContextUnavailableError

if request is None:
    raise RequestContextUnavailableError(
        "Authentication requires request context"
    )
```

---

#### `DisabledFeatureError`

Feature is disabled for current authentication mode.

**Inherits from:** `HTTPException`

**HTTP Status:** 405 Method Not Allowed

**When raised:**

- Password login attempted in OAuth mode
- User registration disabled
- Feature not available in current deployment

**Example:**

```python
from backend.services.auth import DisabledFeatureError, get_auth_config

config = get_auth_config()

if config.is_oauth_proxy_mode():
    # Password login not available in OAuth mode
    raise DisabledFeatureError("Password login disabled in OAuth mode")
```

---

#### `UserSyncError`

User database synchronisation failed (internal exception).

**Inherits from:** `Exception`

**HTTP Status:** None (internal exception, not raised to HTTP layer)

**When raised:**

- Database connection fails during user sync
- User model validation fails
- Required claim missing (sub)

**Example:**

```python
from backend.services.auth.exceptions import UserSyncError

try:
    from backend.services.auth import sync_user_from_claims
    sync_user_from_claims(claims)
except UserSyncError as e:
    logger.warning(f"Failed to sync user: {e}")
    # Don't fail authentication, just log warning
```

**Note:** This exception is caught internally and logged as a warning. User sync failures do not prevent authentication
from succeeding.

---

### Error Handling Patterns

**Recommended Authentication Error Handling:**

```python
from fastapi import Depends, HTTPException
from backend.api.auth.dependencies import get_current_user
from backend.services.auth import (
    AuthenticationError,
    InvalidTokenError,
    MissingTokenError,
    OAuth2ConfigurationError
)

@router.get("/protected")
async def protected_endpoint(claims = Depends(get_current_user)):
    """Protected endpoint with proper error handling.

    The get_current_user dependency automatically raises appropriate
    HTTP exceptions that FastAPI converts to error responses.
    """
    try:
        # Use authenticated claims
        user_id = claims["sub"]
        email = claims["email"]

        return {
            "success": True,
            "user_id": user_id,
            "email": email
        }

    except AuthenticationError as e:
        # FastAPI automatically converts to HTTP response
        # 401 Unauthorized with error detail
        raise
```

**OAuth Provider Error Handling:**

```python
from backend.services.auth.providers import get_oauth_proxy_auth
from backend.services.auth import InvalidTokenError, OAuth2ConfigurationError

auth = get_oauth_proxy_auth()

if not auth:
    # OAuth not configured
    raise OAuth2ConfigurationError("OAuth proxy not configured")

try:
    claims = auth.verify_and_sync(token, request)
    logger.info(f"Authenticated user: {claims['email']}")

except InvalidTokenError as e:
    # Token validation failed
    logger.warning(f"Invalid token: {e.detail}")
    return {"error": "Authentication failed", "detail": str(e)}
```

**User API Token Validation:**

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

# Validate API token
result = UserAPITokenService.validate_token(
    plaintext_token,
    workflow_name="my-workflow-uuid"
)

if not result:
    # Token invalid, expired, or lacks workflow access
    raise HTTPException(
        status_code=401,
        detail="Invalid API token or insufficient permissions"
    )

token_obj, user_id = result

# Token valid, proceed with request
logger.info(f"API token '{token_obj.token_name}' validated for {user_id}")
```

**User Sync Error Handling:**

```python
from backend.services.auth import sync_user_from_claims
from backend.services.auth.exceptions import UserSyncError

try:
    sync_user_from_claims(claims)
except Exception as e:
    # User sync failures are logged but don't prevent authentication
    logger.warning(f"User sync failed: {e}")
    # Continue with authentication anyway
```

## Integration Patterns

### Integration with API Layer

The auth service integrates with the API layer through FastAPI dependencies.

**Example from backend/api/auth/routes.py:**

```python
from fastapi import APIRouter, Depends
from backend.api.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/me")
async def get_authenticated_user(
    claims: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get authenticated user profile.

    The get_current_user dependency:
    - Extracts token from request
    - Validates token via OAuth2ProxyAuth
    - Syncs user to database
    - Returns user claims
    """
    email = claims.get("email")
    user_id = claims.get("sub")

    # Look up user in database
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()

        return {
            "claims": claims,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at
            } if user else None
        }
```

**Example from backend/api/graph/routes.py:**

```python
from fastapi import APIRouter, Depends
from backend.api.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/graph")

@router.get("/list")
async def list_graphs(
    claims: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """List user's workflows.

    User ID from claims scopes query to user's workflows.
    """
    user_id = claims["sub"]

    # Get workflows for this user
    workflows = storage_service.get_user_workflows(user_id)

    return {
        "success": True,
        "graphs": workflows
    }
```

### Integration with Other Services

The auth service is a foundational service used by most other services.

**Database Service Integration:**

```python
from backend.services.auth import sync_user_from_claims
from backend.services.database import get_db
from backend.models.auth.user import User

# Auth service syncs users to database
claims = {"sub": "user-123", "email": "user@example.com"}
sync_user_from_claims(claims)

# Other services query user records
with get_db() as db:
    user = db.query(User).filter(User.id == "user-123").first()
    print(f"User: {user.email}")
```

**Workflow Publishing Integration:**

```python
from backend.services.auth.user_api_token_service import UserAPITokenService
from backend.services.workflow.publishing import publish_workflow

# Create API token for workflow access
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Published Workflow Token",
    scopes=["workflow:my-workflow-uuid"],
    expires_in_days=365
)

# Publish workflow with token authentication
publish_workflow(
    workflow_id="my-workflow-uuid",
    auth_token=plaintext
)
```

**HTTP Execution Authentication:**

```python
from fastapi import Request, HTTPException
from backend.services.auth.user_api_token_service import UserAPITokenService

async def authenticate_http_execution(request: Request, workflow_id: str):
    """Authenticate HTTP workflow execution request."""

    # Extract Bearer token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API token")

    token = auth_header.split(" ", 1)[1]

    # Validate token and check workflow access
    result = UserAPITokenService.validate_token(token, workflow_id)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid token")

    token_obj, user_id = result

    # Execute workflow as authenticated user
    return {"user_id": user_id, "workflow_id": workflow_id}
```

### Dependency Flow

**Services that depend on Auth Service:**

- All API modules (`backend/api/*`) - User authentication
- Workflow Publishing (`backend/services/workflow/publishing`) - API token generation
- HTTP Execution (`backend/api/http_execution`) - Token-based auth
- Graph CRUD (`backend/services/graph`) - User-scoped data access
- Execution Service (`backend/services/execution`) - User context

**Services that Auth Service depends on:**

- Database Service (`backend/services/database`) - User persistence
- Config Service (`backend/services/config`) - Logging
- Models (`backend/models.auth.user`) - User model definition

**Data Flow:**

```
HTTP Request
    ↓
FastAPI Dependency (get_current_user)
    ↓
extract_token_from_request()
    ↓
OAuth2ProxyAuth.verify_and_sync()
    ↓
JWT Validation (PyJWT + JWKS)
    ↓
enrich_claims()
    ↓
sync_user_from_claims()
    ↓
Database (User table)
    ↓
Return Claims to API Endpoint
```

### Common Integration Patterns

#### Pattern 1: Protected API Endpoint

```python
from fastapi import Depends, APIRouter
from backend.api.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/workflows")
async def create_workflow(
    data: WorkflowCreate,
    claims = Depends(get_current_user)
):
    """Create workflow for authenticated user."""
    user_id = claims["sub"]

    workflow = Workflow(
        name=data.name,
        created_by_user_id=user_id
    )

    db.add(workflow)
    db.commit()

    return {"id": workflow.id}
```

#### Pattern 2: User API Token Authentication

```python
from fastapi import Request, HTTPException
from backend.services.auth.user_api_token_service import UserAPITokenService

async def authenticate_with_token(request: Request, workflow_id: str):
    """Authenticate using Personal Access Token."""

    # Extract token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer na_"):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = auth.replace("Bearer ", "")

    # Validate
    result = UserAPITokenService.validate_token(token, workflow_id)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    token_obj, user_id = result
    return user_id
```

#### Pattern 3: Conditional Authentication Mode

```python
from backend.services.auth import get_auth_config
from backend.api.auth.dependencies import get_current_user

config = get_auth_config()

if config.is_oauth_proxy_mode():
    # OAuth proxy handles authentication
    @router.get("/login")
    async def login():
        return {"message": "Use OAuth proxy login"}

elif config.is_basic_mode():
    # Traditional username/password
    @router.post("/login")
    async def login(credentials: LoginRequest):
        # Validate username/password
        user = authenticate_user(credentials.username, credentials.password)
        token = create_access_token(user.id)
        return {"access_token": token}
```

#### Pattern 4: User Provisioning from OAuth

```python
from backend.services.auth import sync_user_from_claims

# After OAuth authentication
claims = {
    "sub": "azure-ad-user-id",
    "email": "john.doe@example.com",
    "name": "John Doe",
    "given_name": "John",
    "family_name": "Doe",
    "tid": "tenant-id",
    "oid": "object-id"
}

# Automatically create or update user
sync_user_from_claims(claims)

# User now exists in database
with get_db() as db:
    user = db.query(User).filter(User.id == "azure-ad-user-id").first()
    print(f"User created: {user.email}")
```

## Usage Examples

### Example 1: Basic OAuth Proxy Authentication

Complete example of authenticating a request in OAuth proxy mode:

```python
from fastapi import FastAPI, Depends, Request
from backend.api.auth.dependencies import get_current_user
from backend.services.auth import get_auth_config

app = FastAPI()

# Check authentication mode
config = get_auth_config()
print(f"Auth mode: {config.auth_mode}")

@app.get("/profile")
async def get_profile(
    request: Request,
    claims = Depends(get_current_user)
):
    """Get user profile (requires OAuth proxy authentication)."""

    # Extract user information from claims
    user_id = claims["sub"]
    email = claims["email"]
    name = claims.get("name", "")

    # Log authentication
    print(f"Authenticated user: {email}")

    # Return profile
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "auth_source": claims.get("auth_source"),
        "tenant_id": claims.get("tid")
    }
```

### Example 2: Creating and Using API Tokens

Complete example of creating and validating Personal Access Tokens:

```python
from fastapi import FastAPI, HTTPException, Depends, Header
from backend.services.auth.user_api_token_service import UserAPITokenService
from backend.api.auth.dependencies import get_current_user

app = FastAPI()

@app.post("/api/tokens")
async def create_api_token(
    token_name: str,
    workflow_id: str,
    expires_days: int = 90,
    claims = Depends(get_current_user)
):
    """Create a Personal Access Token for workflow access."""

    user_id = claims["sub"]

    # Create token with specific workflow scope
    token_obj, plaintext = UserAPITokenService.create_token(
        user_id=user_id,
        token_name=token_name,
        scopes=[f"workflow:{workflow_id}"],
        description=f"Token for workflow {workflow_id}",
        expires_in_days=expires_days
    )

    # IMPORTANT: plaintext token only shown once
    return {
        "success": True,
        "token_id": token_obj.id,
        "token": plaintext,  # Save this!
        "token_prefix": token_obj.token_prefix,
        "expires_at": token_obj.expires_at.isoformat(),
        "scopes": token_obj.scopes,
        "warning": "Save this token now - it won't be shown again"
    }


@app.get("/api/tokens")
async def list_tokens(claims = Depends(get_current_user)):
    """List user's API tokens."""

    user_id = claims["sub"]
    tokens = UserAPITokenService.list_user_tokens(user_id)

    return {
        "success": True,
        "tokens": [
            {
                "id": t.id,
                "name": t.token_name,
                "prefix": t.token_prefix,
                "scopes": t.scopes,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                "usage_count": t.usage_count
            }
            for t in tokens
        ]
    }


@app.delete("/api/tokens/{token_id}")
async def revoke_token(
    token_id: str,
    claims = Depends(get_current_user)
):
    """Revoke an API token."""

    user_id = claims["sub"]
    success = UserAPITokenService.revoke_token(token_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Token not found")

    return {"success": True, "message": "Token revoked"}


@app.post("/workflows/{workflow_id}/execute")
async def execute_workflow_with_token(
    workflow_id: str,
    authorization: str = Header(None)
):
    """Execute workflow using API token authentication."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing Bearer token in Authorization header"
        )

    token = authorization.replace("Bearer ", "")

    # Validate token and check workflow access
    result = UserAPITokenService.validate_token(token, workflow_id)

    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid token or insufficient permissions"
        )

    token_obj, user_id = result

    # Execute workflow as authenticated user
    return {
        "success": True,
        "message": f"Workflow {workflow_id} executed",
        "user_id": user_id,
        "token_name": token_obj.token_name
    }
```

### Example 3: Complete Authentication Flow

End-to-end example showing OAuth proxy authentication with user sync:

```python
from fastapi import FastAPI, Request, Depends, HTTPException
from backend.services.auth import (
    get_auth_config,
    get_oauth_proxy_auth,
    extract_token_from_request,
    sync_user_from_claims,
    enrich_claims,
    InvalidTokenError,
    OAuth2ConfigurationError
)
from backend.services.database import get_db
from backend.models.auth.user import User

app = FastAPI()

# Initialise authentication
config = get_auth_config()

if config.is_oauth_proxy_mode():
    print("OAuth proxy mode enabled")

    # Validate configuration
    try:
        config.validate_oauth_config()
        print("OAuth configuration valid")
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise

    # Get OAuth provider
    oauth_auth = get_oauth_proxy_auth()
    print(f"JWKS URL: {config.azure_jwks_url}")


@app.get("/auth/verify")
async def verify_authentication(request: Request):
    """Verify OAuth proxy authentication and sync user."""

    # Step 1: Extract token from request
    token = extract_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="No authentication token found"
        )

    # Step 2: Get OAuth provider
    oauth_auth = get_oauth_proxy_auth()

    if not oauth_auth:
        raise OAuth2ConfigurationError(
            "OAuth proxy not configured"
        )

    try:
        # Step 3: Validate token and get claims
        claims = oauth_auth.verify_and_sync(token, request)

        # Step 4: User automatically synced to database
        # Look up user record
        with get_db() as db:
            user = db.query(User).filter(
                User.id == claims["sub"]
            ).first()

        # Step 5: Return authentication details
        return {
            "authenticated": True,
            "user": {
                "id": claims["sub"],
                "email": claims["email"],
                "name": claims.get("name"),
                "auth_source": claims.get("auth_source")
            },
            "database_user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "last_login_at": user.last_login_at.isoformat() if user else None,
                "created_at": user.created_at.isoformat() if user else None
            } if user else None,
            "claims": claims
        }

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {e.detail}"
        )


@app.get("/workflows")
async def list_user_workflows(claims = Depends(get_current_user)):
    """List workflows for authenticated user."""

    user_id = claims["sub"]

    with get_db() as db:
        workflows = db.query(Workflow).filter(
            Workflow.created_by_user_id == user_id
        ).all()

        return {
            "success": True,
            "user_id": user_id,
            "workflows": [
                {
                    "id": w.id,
                    "name": w.name,
                    "created_at": w.created_at.isoformat()
                }
                for w in workflows
            ]
        }
```

### Example 4: Testing Authentication

Example showing how to test authentication in unit tests:

```python
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from backend.services.auth import (
    get_oauth_proxy_auth,
    sync_user_from_claims,
    UserAPITokenService
)

def test_oauth_proxy_authentication():
    """Test OAuth2 proxy authentication."""

    # Mock request with OAuth proxy headers
    mock_request = Mock()
    mock_request.headers = {
        "X-Auth-Request-Access-Token": "mock-jwt-token",
        "X-Auth-Request-Email": "test@example.com"
    }

    # Mock JWT validation
    with patch('backend.services.auth.providers.oauth2_proxy.jwt.decode') as mock_decode:
        mock_decode.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "name": "Test User"
        }

        auth = get_oauth_proxy_auth()

        if auth and not auth.config.oauth_proxy_disable_jwt_validation:
            # Test token validation
            claims = auth.verify_and_sync("mock-jwt-token", mock_request)

            assert claims["email"] == "test@example.com"
            assert claims["sub"] == "user-123"


def test_user_sync():
    """Test user database synchronisation."""

    claims = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User"
    }

    # Sync user (creates or updates)
    sync_user_from_claims(claims)

    # Verify user exists
    with get_db() as db:
        user = db.query(User).filter(User.id == "test-user-id").first()
        assert user is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"


def test_api_token_lifecycle():
    """Test API token creation, validation, and revocation."""

    # Create token
    token_obj, plaintext = UserAPITokenService.create_token(
        user_id="test@example.com",
        token_name="Test Token",
        scopes=["workflow:*"],
        expires_in_days=30
    )

    assert plaintext.startswith("na_")
    assert token_obj.token_name == "Test Token"

    # Validate token
    result = UserAPITokenService.validate_token(plaintext)
    assert result is not None

    validated_token, user_id = result
    assert user_id == "test@example.com"

    # Revoke token
    success = UserAPITokenService.revoke_token(
        token_obj.id,
        user_id="test@example.com"
    )
    assert success is True

    # Validate again (should fail)
    result = UserAPITokenService.validate_token(plaintext)
    assert result is None


@pytest.fixture
def authenticated_client():
    """Test client with authentication."""

    from backend.main import app

    client = TestClient(app)

    # Mock authentication dependency
    def override_get_current_user():
        return {
            "sub": "test-user",
            "email": "test@example.com",
            "name": "Test User"
        }

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield client

    app.dependency_overrides.clear()


def test_protected_endpoint(authenticated_client):
    """Test accessing protected endpoint."""

    response = authenticated_client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["claims"]["email"] == "test@example.com"
```

## Performance Considerations

### Performance Characteristics

**JWT Token Validation:**

- Complexity: O(1) for token decoding
- JWKS key lookup: O(1) with caching (PyJWKClient caches keys)
- Network: One JWKS fetch per application startup (cached)
- CPU-bound: RSA signature verification (~1-2ms per token)

**User Synchronisation:**

- Complexity: O(1) database lookup by user ID (indexed)
- I/O-bound: Database insert/update (~5-10ms)
- Optimisation: Sync is non-blocking, failures logged but don't block auth

**API Token Validation:**

- Complexity: O(1) for prefix lookup (indexed)
- Bcrypt verification: CPU-bound (~50-100ms per token)
- Optimisation: Prefix filtering reduces candidates before bcrypt check
- Database: Single query with index on token_prefix

**Memory Usage:**

- AuthConfig: ~1KB per instance (singleton)
- OAuth2ProxyAuth: ~5KB + JWKS cache (~10-50KB)
- PyJWKClient: Caches signing keys (~10KB per tenant)

### Optimisation Tips

#### Tip 1: Token Prefix Optimisation

**Problem:**

```python
# Inefficient: Check all tokens with bcrypt
for token in all_tokens:
    if UserAPITokenService.verify_token(plaintext, token.token_hash):
        return token
```

**Solution:**

```python
# Efficient: Filter by prefix first (indexed column)
token_prefix = plaintext[:11]

candidates = db.query(UserAPIToken).filter(
    UserAPIToken.token_prefix == token_prefix,
    UserAPIToken.is_active == True
).all()

# Only verify bcrypt on matching prefixes
for candidate in candidates:
    if UserAPITokenService.verify_token(plaintext, candidate.token_hash):
        return candidate
```

**Result:** Reduces bcrypt operations from N (all tokens) to 1-2 (tokens with matching prefix).

---

#### Tip 2: JWKS Caching

The PyJWKClient automatically caches JWKS keys, but you can optimise further:

```python
from jwt import PyJWKClient

# Default caching (built-in)
jwks_client = PyJWKClient(jwks_url)

# Keys are cached after first fetch
# Subsequent validations use cached keys
# Cache refreshes when keys expire or rotate
```

**Optimisation:**

- JWKS keys cached in memory (no repeated network calls)
- Key rotation handled automatically
- No manual cache management needed

---

#### Tip 3: User Sync Non-Blocking

User sync failures don't block authentication:

```python
from backend.services.auth import sync_user_from_claims

# Sync wrapped in try-except internally
sync_user_from_claims(claims)

# Even if database fails, authentication succeeds
# Failure logged as warning, not error
```

**Behaviour:**

- Database failures logged but don't raise exceptions
- Authentication proceeds even if user sync fails
- Ensures high availability during DB issues

---

#### Tip 4: Database Connection Pooling

Use connection pooling for user sync:

```python
from backend.services.database import get_db

# Context manager uses connection pool
with get_db() as db:
    user = db.query(User).filter(User.id == user_id).first()
    # Connection returned to pool automatically
```

**Benefits:**

- Reuses database connections
- Reduces connection overhead
- Automatic cleanup with context manager

### Async/Await Support

The auth service supports async operations through FastAPI dependencies:

```python
from fastapi import Depends
from backend.api.auth.dependencies import get_current_user

@router.get("/async-endpoint")
async def async_endpoint(claims = Depends(get_current_user)):
    """Async endpoint with authentication.

    get_current_user is an async function that can be awaited.
    """
    user_id = claims["sub"]

    # Perform async operations
    data = await fetch_data_async(user_id)

    return {"data": data}
```

**Note:** While the dependency is async, JWT validation itself is CPU-bound and synchronous. Database operations use
synchronous SQLAlchemy.

### Connection Pooling

Database connection pooling is handled by the database service:

```python
from backend.services.database import get_db

# get_db() provides pooled connection
with get_db() as db:
    # Use connection
    user = db.query(User).filter(User.id == user_id).first()
    # Connection automatically returned to pool
```

### Batch Operations

User API token service supports batch token listing:

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

# List all user tokens in single query
tokens = UserAPITokenService.list_user_tokens("user@example.com")

# More efficient than:
# for token_id in token_ids:
#     token = UserAPITokenService.get_token_by_id(token_id)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.auth import (
    AuthConfig,
    OAuth2ProxyAuth,
    extract_token_from_request
)

@pytest.fixture
def auth_config():
    """Mock authentication configuration."""
    with patch.dict('os.environ', {
        'AUTH_MODE': 'oauth_proxy',
        'AZURE_TENANT_ID': 'test-tenant',
        'AZURE_CLIENT_ID': 'test-client',
        'OAUTH_PROXY_DISABLE_JWT_VALIDATION': 'false'
    }):
        config = AuthConfig()
        yield config


def test_auth_config_oauth_mode(auth_config):
    """Test authentication configuration in OAuth mode."""
    assert auth_config.is_oauth_proxy_mode() is True
    assert auth_config.is_basic_mode() is False
    assert auth_config.azure_tenant_id == 'test-tenant'


def test_token_extraction():
    """Test token extraction from request."""
    # Mock request with Authorization header
    mock_request = Mock()
    mock_request.headers = {
        "Authorization": "Bearer test-token-123"
    }

    token = extract_token_from_request(mock_request)

    assert token == "test-token-123"


def test_oauth_proxy_header_extraction():
    """Test OAuth proxy header extraction."""
    from backend.services.auth.token_extractor import extract_token_from_oauth_proxy_header

    mock_request = Mock()
    mock_request.headers = {
        "X-Auth-Request-Access-Token": "oauth-proxy-token"
    }

    token = extract_token_from_oauth_proxy_header(mock_request)

    assert token == "oauth-proxy-token"
```

### Mocking Dependencies

```python
from unittest.mock import patch, Mock
import pytest

@patch('backend.services.auth.providers.oauth2_proxy.jwt.decode')
def test_oauth_authentication(mock_jwt_decode):
    """Test OAuth authentication with mocked JWT."""

    # Mock JWT decode response
    mock_jwt_decode.return_value = {
        "sub": "user-123",
        "email": "test@example.com",
        "name": "Test User",
        "aud": "test-client-id",
        "iss": "https://login.microsoftonline.com/tenant/v2.0"
    }

    # Mock request
    mock_request = Mock()
    mock_request.headers = {
        "X-Auth-Request-Email": "test@example.com"
    }

    # Test authentication
    from backend.services.auth.providers import OAuth2ProxyAuth

    # Need to disable JWT validation for test
    with patch.dict('os.environ', {
        'AUTH_MODE': 'oauth_proxy',
        'OAUTH_PROXY_DISABLE_JWT_VALIDATION': 'true'
    }):
        auth = OAuth2ProxyAuth()
        claims = auth.verify_and_sync("mock-token", mock_request)

        assert claims["email"] == "test@example.com"
        assert claims["sub"] == "user-123"


@patch('backend.services.auth.user_sync.get_db')
def test_user_sync_mock(mock_get_db):
    """Test user synchronisation with mocked database."""
    from backend.services.auth import sync_user_from_claims

    # Mock database session
    mock_db = Mock()
    mock_get_db.return_value.__enter__.return_value = mock_db

    # Mock user query
    mock_db.query.return_value.filter.return_value.first.return_value = None

    claims = {
        "sub": "test-user",
        "email": "test@example.com",
        "name": "Test User"
    }

    # Sync user
    sync_user_from_claims(claims)

    # Verify database was called
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
```

### Integration Testing

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.database import get_db
from backend.models.auth.user import User

@pytest.mark.integration
def test_authentication_integration():
    """Integration test for full authentication flow."""

    client = TestClient(app)

    # Test with mock OAuth headers
    headers = {
        "Authorization": "Bearer test-token",
        "X-Auth-Request-Email": "integration@example.com",
        "X-Auth-Request-Access-Token": "test-token"
    }

    # Make authenticated request
    response = client.get("/api/auth/me", headers=headers)

    # Verify authentication (may fail if OAuth validation enabled)
    # In test environment, use OAUTH_PROXY_DISABLE_JWT_VALIDATION=true

    if response.status_code == 200:
        data = response.json()
        assert "claims" in data
        assert data["claims"]["email"] == "integration@example.com"


@pytest.mark.integration
def test_api_token_integration():
    """Integration test for API token flow."""

    from backend.services.auth.user_api_token_service import UserAPITokenService

    # Create token
    token_obj, plaintext = UserAPITokenService.create_token(
        user_id="integration@example.com",
        token_name="Integration Test Token",
        scopes=["workflow:*"]
    )

    # Validate token
    result = UserAPITokenService.validate_token(plaintext)

    assert result is not None
    validated_token, user_id = result
    assert user_id == "integration@example.com"

    # List tokens
    tokens = UserAPITokenService.list_user_tokens("integration@example.com")
    assert len(tokens) >= 1
    assert any(t.token_name == "Integration Test Token" for t in tokens)

    # Revoke token
    success = UserAPITokenService.revoke_token(token_obj.id, user_id)
    assert success is True

    # Validate again (should fail)
    result = UserAPITokenService.validate_token(plaintext)
    assert result is None
```

## Best Practices

### Do's

✅ **Always use get_current_user dependency for protected endpoints**

```python
from fastapi import Depends
from backend.api.auth.dependencies import get_current_user

@router.get("/protected")
async def protected_endpoint(claims = Depends(get_current_user)):
    """Properly protected endpoint."""
    user_id = claims["sub"]
    return {"user_id": user_id}
```

Why: Centralised authentication logic, automatic error handling, consistent user extraction.

---

✅ **Use token prefixes for API token display**

```python
from backend.services.auth.user_api_token_service import UserAPITokenService

token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Production Token"
)

# Show user the prefix for identification
print(f"Token: {plaintext}")
print(f"Prefix: {token_obj.token_prefix}")  # "na_abc123de"

# User can identify tokens by prefix in UI
```

Why: Helps users identify tokens without exposing full token, easier revocation.

---

✅ **Set token expiration for security**

```python
# Good: Expiring token
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="CI/CD Token",
    expires_in_days=90  # 90 day expiration
)

# Good: Short-lived test token
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Test Token",
    expires_in_days=7
)
```

Why: Reduces risk of compromised tokens, enforces token rotation.

---

✅ **Use specific scopes for least privilege**

```python
# Good: Specific workflow access
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Support Workflow Token",
    scopes=["workflow:support-workflow-uuid"]  # Specific scope
)

# Acceptable: All workflows for admin integrations
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="admin@example.com",
    token_name="Admin Integration",
    scopes=["workflow:*"]  # All workflows
)
```

Why: Minimises damage from compromised tokens, follows principle of least privilege.

---

✅ **Handle authentication errors gracefully**

```python
from backend.services.auth import InvalidTokenError, MissingTokenError

try:
    claims = auth.verify_and_sync(token, request)
except MissingTokenError:
    return {"error": "Please log in to continue"}
except InvalidTokenError:
    return {"error": "Session expired, please re-authenticate"}
```

Why: Better user experience, clear error messages, proper HTTP status codes.

### Don'ts

❌ **Don't skip authentication on sensitive endpoints**

```python
# Bad: No authentication
@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Anyone can delete workflows!"""
    delete_workflow(workflow_id)
    return {"success": True}

# Good: Requires authentication
@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    claims = Depends(get_current_user)
):
    """Only authenticated users can delete."""
    user_id = claims["sub"]
    verify_ownership(workflow_id, user_id)
    delete_workflow(workflow_id)
    return {"success": True}
```

Why: Security vulnerability, allows unauthorised access.

---

❌ **Don't store plaintext API tokens**

```python
# Bad: Storing plaintext token
token_obj, plaintext = UserAPITokenService.create_token(...)

db_record = APITokenBackup(
    user_id="user@example.com",
    token_plaintext=plaintext  # DON'T DO THIS!
)
db.add(db_record)

# Good: Only hash stored (automatic in UserAPITokenService)
token_obj, plaintext = UserAPITokenService.create_token(...)
# token_obj.token_hash is bcrypt hash
# plaintext returned once, never stored
```

Why: Major security risk if database is compromised, violates security best practices.

---

❌ **Don't disable JWT validation in production**

```python
# Bad: Production configuration
AUTH_MODE=oauth_proxy
OAUTH_PROXY_DISABLE_JWT_VALIDATION=true  # NEVER in production!

# Good: Production configuration
AUTH_MODE=oauth_proxy
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
# JWT validation enabled (default)
```

Why: Trusts unvalidated tokens, vulnerable to token forgery attacks.

---

❌ **Don't create tokens without expiration for long-term use**

```python
# Bad: No expiration
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Integration Token",
    expires_in_days=None  # Never expires!
)

# Good: Reasonable expiration
token_obj, plaintext = UserAPITokenService.create_token(
    user_id="user@example.com",
    token_name="Integration Token",
    expires_in_days=365  # 1 year, forces rotation
)
```

Why: Increases security risk, makes compromised tokens valid forever.

---

❌ **Don't reuse plaintext tokens after initial display**

```python
# Bad: Trying to retrieve plaintext later
token_obj = UserAPITokenService.get_token_by_id(token_id)
plaintext = token_obj.token_plaintext  # Doesn't exist!

# Good: Show plaintext immediately after creation
token_obj, plaintext = UserAPITokenService.create_token(...)

# Show to user NOW (only chance)
return {
    "token": plaintext,
    "message": "Save this token - it won't be shown again"
}

# Later: Can only show prefix
token_obj = UserAPITokenService.get_token_by_id(token_id)
print(f"Token prefix: {token_obj.token_prefix}")
```

Why: Plaintext is never stored, only bcrypt hash available after creation.

## Related Documentation

### Related Services

- [Database Service](database.md) - User persistence and session management
- [Graph Service](graph.md) - Workflow ownership and access control
- [Execution Service](execution.md) - Execution context and user scoping
- [Workflow Publishing Service](workflow.md) - API token generation for published workflows

### Related API Modules

- [Auth API](../../../backend/api/auth/auth.md) - Authentication endpoints and user profile
- [Graph API](../../../backend/api/graph/graph.md) - Workflow CRUD with user scoping
- [HTTP Execution API](../../../backend/api/http_execution/http_execution.md) - Token-based workflow execution
- [User API Tokens API](../api/user_api_tokens.md) - Token management endpoints

### Architecture Documentation

- [Authentication Architecture](../architecture/authentication.md) - OAuth2 proxy integration
- [Security Architecture](../architecture/security.md) - Security model and threat mitigations

### External Documentation

- [PyJWT Documentation](https://pyjwt.readthedocs.io/) - JWT encoding/decoding library
- [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) - Reverse proxy for OAuth authentication
- [Azure AD OAuth](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow) - Azure
  Active Directory OAuth flow
- [bcrypt](https://github.com/pyca/bcrypt/) - Password and token hashing

## Summary

The Authentication Service is a foundational component of AgenticStudio that provides OAuth2 proxy authentication, user
database synchronisation, and Personal Access Token management. It integrates with Azure AD and generic OIDC providers,
validating JWT tokens and enriching user claims from multiple sources.

The service follows a provider-based architecture with singleton instances for configuration and authentication
providers. It supports multiple authentication modes (basic and OAuth proxy) and provides comprehensive error handling
with appropriate HTTP status codes.

User synchronisation happens automatically during authentication, creating or updating user records from JWT claims
without blocking authentication on database failures. Personal Access Tokens provide programmatic access to published
workflows with bcrypt-hashed storage and scope-based access control.

**Key Features:**

- OAuth2 proxy authentication with Azure AD/OIDC support
- Automatic user provisioning and profile synchronisation
- Personal Access Token (PAT) management for programmatic access
- JWT token validation with JWKS signature verification
- Multi-source token extraction (headers, credentials, OAuth proxy)
- Scope-based workflow access control
- Comprehensive exception hierarchy with HTTP status mapping
- FastAPI dependency injection for protected endpoints
- Token prefix optimisation for fast validation

**Primary Use Cases:**

- Authenticating users behind oauth2-proxy reverse proxy
- Validating JWT tokens from Azure AD or custom OIDC providers
- Syncing user profiles to database from identity providers
- Generating API tokens for CI/CD pipelines and integrations
- Enforcing user-scoped access to workflows and resources
- Tracking user sessions and last login timestamps
- Managing token lifecycle (creation, validation, revocation)

**When to Use This Service:**

- Implementing authentication for API endpoints
- Validating user identity from OAuth providers
- Creating programmatic access to workflows
- Syncing user data from identity providers
- Building user management interfaces
- Integrating third-party services with token-based auth
- Testing authentication flows in development
