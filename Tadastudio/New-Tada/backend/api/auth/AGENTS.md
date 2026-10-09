# Authentication API Module

## Overview

The Authentication API module provides OAuth2 proxy authentication for AgenticStudio, enabling secure user authentication
and profile retrieval through Microsoft Entra ID (Azure AD). This module serves as the foundation for user identity
management across the entire application.

**Location:** [backend/api/auth/](../../backend/api/auth/)

**Base Path:** `/api/auth`

**Primary Responsibilities:**

- User authentication via OAuth2 proxy
- JWT token validation and verification
- User profile retrieval from claims and database
- Automatic user synchronisation to database
- Reusable authentication dependency for all API modules

## Architecture

### Module Structure

```
backend/api/auth/
├── __init__.py           # Module exports (router, get_current_user)
├── routes.py             # API endpoint: GET /api/auth/me
├── models.py             # Pydantic models (UserProfileResponse)
└── dependencies.py       # FastAPI dependencies (get_current_user)

Related Services:
backend/services/auth/
├── __init__.py           # Service layer exports
├── config.py             # Authentication configuration (AuthConfig)
├── exceptions.py         # Custom authentication exceptions
├── jwt_utils.py          # JWT token decoding utilities
├── token_extractor.py    # Token extraction from requests
├── user_sync.py          # User database synchronisation
└── providers/
    ├── __init__.py
    └── oauth2_proxy.py   # OAuth2ProxyAuth implementation
```

**Key Files:**

- **routes.py** (100 lines) - Single endpoint for user profile retrieval
- **dependencies.py** (176 lines) - Core authentication logic, exported to all modules
- **models.py** (33 lines) - Response schema for /me endpoint
- **services/auth/** - Complete authentication service layer

### Design Pattern

The Authentication API follows a **dependency injection pattern** where the authentication logic is encapsulated in a
reusable FastAPI dependency:

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Request with Token                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  get_current_user dependency       │
        │  (backend/api/auth/dependencies.py)│
        └────────────────┬───────────────────┘
                         │
        ┌────────────────┴───────────────────┐
        │                                    │
        ▼                                    ▼
┌──────────────────┐              ┌──────────────────┐
│  Header-Based    │              │  Token-Based     │
│  Authentication  │              │  Authentication  │
│  (Preferred)     │              │  (Fallback)      │
└────────┬─────────┘              └────────┬─────────┘
         │                                 │
         │  X-Auth-Request-Email present?  │
         │  Yes → Trust oauth2-proxy       │
         │  No  → Validate JWT token   ←───┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Extract Claims & Enrich from Token     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Sync User to Database                  │
│  (backend/services/auth/user_sync.py)   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Return Claims Dictionary               │
│  {email, name, sub, given_name, ...}    │
└─────────────────────────────────────────┘
```

**Benefits:**

- Single authentication dependency used across all API modules
- Centralised authentication logic (change once, affect everywhere)
- Automatic user synchronisation to database
- Flexible authentication: header-based (trusted proxy) or token-based (full validation)
- Easy to test and mock in unit tests

### Authentication Flow

AgenticStudio uses **oauth2-proxy** as a reverse proxy that handles OAuth2/OIDC authentication before requests reach the
FastAPI application. This architecture provides:

1. **Security**: Authentication handled by dedicated proxy
2. **Flexibility**: Support for multiple identity providers
3. **Performance**: Reduced authentication overhead in application
4. **Scalability**: Proxy can cache and reuse sessions

**Deployment Architecture:**

```
┌──────────┐      ┌───────────────┐      ┌────────────────┐
│  Client  │─────>│ oauth2-proxy  │─────>│  FastAPI App   │
│ (Browser)│<─────│  (Azure AD)   │<─────│  (AgenticStudio)   │
└──────────┘      └───────────────┘      └────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Azure AD /  │
                  │  Entra ID    │
                  └──────────────┘
```

**Authentication Modes:**

1. **Header-Based Authentication** (Preferred)
    - oauth2-proxy validates user and forwards headers
    - Headers injected: `X-Auth-Request-Email`, `X-Forwarded-User`, etc.
    - FastAPI trusts the proxy (requests only arrive if authenticated)
    - User claims built from headers + optional token
    - **Fastest**: No JWT validation overhead

2. **Token-Based Authentication** (Fallback)
    - Client sends `Authorization: Bearer <token>` header
    - FastAPI performs full JWT validation (signature, expiration, audience, issuer)
    - Uses Azure AD JWKS endpoint for public key retrieval
    - User claims extracted from validated token
    - **Most Secure**: Full cryptographic verification

## Authentication & Authorisation

### Authentication

All endpoints (except health checks) require authentication via the `get_current_user` dependency.

#### Using the Authentication Dependency

```python
from typing import Any, Dict
from fastapi import APIRouter, Depends
from backend.api.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/protected-resource")
async def protected_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Protected endpoint requiring authentication.

    Args:
        current_user: User claims dictionary from get_current_user

    Returns:
        Protected resource data scoped to current user
    """
    user_email = current_user["email"]
    user_id = current_user.get("sub")
    user_name = current_user.get("name", "Unknown")

    return {
        "message": f"Hello, {user_name}!",
        "email": user_email,
        "user_id": user_id
    }
```

#### User Claims Structure

The `get_current_user` dependency returns a dictionary containing user claims:

```python
{
    "email": "john.doe@example.com",      # User email (always present)
    "sub": "abc123...",                   # Subject identifier (user ID)
    "name": "John Doe",                   # Full name
    "given_name": "John",                 # First name
    "family_name": "Doe",                 # Last name
    "oid": "def456...",                   # Azure AD object ID
    "tid": "ghi789...",                   # Azure AD tenant ID
    "auth_source": "oauth_proxy",         # Authentication source
    # ... additional Azure AD claims
}
```

#### Required Headers

**For Header-Based Authentication:**

```
X-Auth-Request-Email: user@example.com
X-Forwarded-User: user@example.com
X-Forwarded-Preferred-Username: John Doe
Authorization: Bearer <token>  (optional, used for claim enrichment)
```

**For Token-Based Authentication:**

```
Authorization: Bearer <jwt_token>
```

#### Configuration

Authentication behaviour is controlled via environment variables:

```bash
# Authentication mode
AUTH_MODE=oauth_proxy  # or "basic" (default: "basic")

# OAuth2 Proxy JWT validation
OAUTH_PROXY_DISABLE_JWT_VALIDATION=false  # Set to "true" to disable signature validation

# Azure AD configuration (required for JWT validation)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_ALLOWED_AUDIENCES=api://your-api-id,your-client-id
AZURE_AUTHORITY=https://login.microsoftonline.com

# Optional: Custom JWKS URL (for non-Azure identity providers)
AZURE_JWKS_URL=https://your-identity-provider.com/.well-known/jwks.json
```

### Authorisation

**User-Scoped Data:**
All API operations in AgenticStudio are scoped to the authenticated user:

- Users can only access their own workflows, documents, and executions
- Shared resources are explicitly granted via sharing mechanisms
- Database queries automatically filter by user ID

### Personal Access Tokens (PATs)

In addition to OAuth2-based user authentication for the main application, AgenticStudio supports **Personal Access Tokens
** (PATs) for HTTP execution endpoints. These tokens allow users to authenticate external systems and webhooks without
requiring OAuth2 flow.

**PAT vs OAuth2 Authentication:**

| Feature               | OAuth2 (User Auth)               | Personal Access Tokens        |
|-----------------------|----------------------------------|-------------------------------|
| Use Case              | Web UI access                    | External API access, webhooks |
| Authentication Method | Bearer token with JWT validation | Token-based (prefix: `na_`)   |
| Scope                 | Full user access                 | Workflow execution only       |
| Management            | Automatic via oauth2-proxy       | User-managed via Settings UI  |
| Expiration            | Session-based                    | Optional (can be permanent)   |
| Multi-Tenant          | Per Azure AD tenant              | Per user, cross-tenant        |

**PAT Usage Example:**

```bash
# Execute published workflow with PAT
curl -X POST "https://app.agenticstudio.com/api/http-execution/trigger/9d04ad87-4762-4ab4-b35f-85a1b002d8e3?token=na_OxQQzj7KuqIUNWUka93AUSyGBwNnXHtTw1m6v1_7yYo" \
  -H "Content-Type: application/json" \
  -d '{"message": "Process this request"}'
```

**PAT Security Features:**

- Prefix-based identification (`na_` prefix)
- Bcrypt-hashed storage in database
- Scope-based access control (`workflow:*` or `workflow:specific-name`)
- Per-token usage tracking and audit logs
- Optional expiration dates
- Revocable at any time via UI

See [HTTP Execution API](../http_execution/http_execution.md) for details on using PATs with published workflows.

**Implementation Pattern:**

```python
from backend.api.auth.dependencies import get_current_user
from backend.services.database import get_db
from backend.models.workflow import Workflow

@router.get("/workflows")
async def list_user_workflows(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List workflows for the authenticated user only."""
    user_id = current_user["sub"]

    with get_db() as db:
        # Automatically filter by user_id
        workflows = db.query(Workflow).filter(
            Workflow.user_id == user_id
        ).all()

    return {"workflows": workflows}
```

**Security Considerations:**

1. **Email as User Identifier**: The `email` claim is used as the primary user identifier
2. **Automatic User Sync**: User records are automatically created/updated on each authentication
3. **No Role-Based Access Control (RBAC)**: Currently, all authenticated users have equal permissions
4. **Tenant Isolation**: Azure AD tenant ID tracked but not enforced (future enhancement)

## API Endpoints

The auth module provides a single endpoint for retrieving the authenticated user's profile.

---

### `GET /api/auth/me`

Get the authenticated user's profile information from both JWT claims and the database.

**Authentication:** Required (via `get_current_user` dependency)

**Headers:**

- `Authorization: Bearer <token>` - JWT access token
- `X-Auth-Request-Email: user@example.com` - Email from oauth2-proxy (header-based auth)

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
{
  "claims": {
    "email": "john.doe@example.com",
    "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "John Doe",
    "given_name": "John",
    "family_name": "Doe",
    "oid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "tid": "tenant-id-1234",
    "auth_source": "oauth_proxy",
    "iat": 1698765432,
    "exp": 1698851832,
    "iss": "https://login.microsoftonline.com/tenant-id-1234/v2.0",
    "aud": "api://agenticstudio-api"
  },
  "user": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "john.doe@example.com",
    "username": null,
    "first_name": "John",
    "last_name": "Doe",
    "name": "John Doe",
    "created_at": "2025-09-15T14:23:45.123456Z",
    "updated_at": "2025-10-20T08:15:30.654321Z"
  }
}
```

**Response Fields:**

| Field                | Type           | Description                                         |
|----------------------|----------------|-----------------------------------------------------|
| `claims`             | object         | Raw JWT claims from authentication token            |
| `claims.email`       | string         | User email address (primary identifier)             |
| `claims.sub`         | string         | Subject identifier (Azure AD user ID)               |
| `claims.name`        | string         | Full display name                                   |
| `claims.given_name`  | string         | First name                                          |
| `claims.family_name` | string         | Last name                                           |
| `claims.oid`         | string         | Azure AD object ID                                  |
| `claims.tid`         | string         | Azure AD tenant ID                                  |
| `claims.auth_source` | string         | Authentication source (`oauth_proxy` or `azure_ad`) |
| `user`               | object \| null | User profile from database (null if not synced)     |
| `user.id`            | string         | User ID (matches `claims.sub`)                      |
| `user.email`         | string         | Email from database                                 |
| `user.first_name`    | string         | First name from database                            |
| `user.last_name`     | string         | Last name from database                             |
| `user.name`          | string         | Full name from database                             |
| `user.created_at`    | string         | ISO 8601 timestamp of user creation                 |
| `user.updated_at`    | string         | ISO 8601 timestamp of last update                   |

**Use Cases:**

1. **User Profile Display**: Fetch user information for profile page
2. **Authentication Verification**: Verify that the user is authenticated
3. **User Identification**: Get user ID and email for API calls
4. **Token Validation**: Confirm that the access token is valid
5. **Session Management**: Check if user session is still active

**Behaviour:**

1. **Token Validation**: The endpoint validates the JWT token (if token-based auth) or trusts oauth2-proxy headers (if
   header-based auth)
2. **Claims Extraction**: User claims are extracted from the token and/or headers
3. **Database Lookup**: The system queries the database for the user record by email
4. **User Synchronisation**: If user doesn't exist in database, a new record is created automatically
5. **Response Construction**: Returns both raw claims and database user profile

**Validation:**

- **Email Required**: Token must contain an `email` claim
- **Token Expiration**: Token must not be expired (checked during JWT validation)
- **Signature Verification**: Token signature validated against Azure AD JWKS (unless disabled)
- **Audience Validation**: Token audience must match configured allowed audiences
- **Issuer Validation**: Token issuer must match Azure AD tenant issuer

**Side Effects:**

- **User Creation**: New users are automatically created in the database on first authentication
- **User Update**: Existing user records are updated with latest claims (name, email, tenant info)
- **Last Login Tracking**: The `last_login_at` timestamp is updated on every authentication
- **Claims Storage**: Latest JWT claims are stored in the `last_claims` JSON field

**Errors:**

| Status Code | Error                            | Description                                   |
|-------------|----------------------------------|-----------------------------------------------|
| 401         | `MissingTokenError`              | No authorization token provided               |
| 401         | `MissingEmailClaimError`         | Token missing required email claim            |
| 401         | `InvalidTokenError`              | Token signature invalid or expired            |
| 500         | `OAuth2ConfigurationError`       | OAuth2 authentication not configured properly |
| 500         | `RequestContextUnavailableError` | Request context unavailable (internal error)  |

**Example Request (cURL):**

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Accept: application/json"
```

**Example Request (Python):**

```python
import requests

# Using token from environment or login flow
access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

response = requests.get(
    "http://localhost:8000/api/auth/me",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
)

if response.status_code == 200:
    profile = response.json()
    print(f"Logged in as: {profile['claims']['name']}")
    print(f"Email: {profile['claims']['email']}")
    print(f"User ID: {profile['user']['id']}")
else:
    print(f"Authentication failed: {response.status_code}")
    print(response.json())
```

**Example Request (JavaScript):**

```javascript
async function getUserProfile(accessToken) {
  const response = await fetch('http://localhost:8000/api/auth/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': 'application/json'
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Authentication failed: ${error.detail}`);
  }

  const profile = await response.json();
  console.log(`Logged in as: ${profile.claims.name}`);
  console.log(`Email: ${profile.claims.email}`);

  return profile;
}

// Usage
try {
  const profile = await getUserProfile(accessToken);
  // Update UI with user profile
  updateUserProfileUI(profile);
} catch (error) {
  console.error('Failed to fetch user profile:', error);
  // Redirect to login
  redirectToLogin();
}
```

**Performance Notes:**

- **Fast**: Typically responds in < 50ms
- **Database Query**: Single SELECT query by email (indexed)
- **Caching**: Consider caching user profile in frontend for duration of session
- **Rate Limiting**: No rate limiting currently applied (future enhancement)

## Error Handling

### Error Response Format

All authentication errors follow the FastAPI HTTPException format:

```json
{
  "detail": "Human-readable error message"
}
```

**Example Error Response:**

```json
{
  "detail": "Missing bearer token"
}
```

### Common Error Codes

#### 401 Unauthorised

Authentication failures return HTTP 401 with specific error messages:

**MissingTokenError:**

```json
{
  "detail": "Missing bearer token"
}
```

**When it occurs:**

- No `Authorization` header provided
- No `X-Auth-Request-Email` header from oauth2-proxy
- Token is empty or malformed

**MissingEmailClaimError:**

```json
{
  "detail": "Token missing email claim"
}
```

**When it occurs:**

- JWT token validated successfully but contains no email field
- Token missing `email`, `preferred_username`, `upn`, or `unique_name` claims

**InvalidTokenError:**

```json
{
  "detail": "Invalid or expired token"
}
```

**When it occurs:**

- Token signature verification failed
- Token has expired (past `exp` claim)
- Token issuer doesn't match expected issuer
- Token audience doesn't match allowed audiences
- Token is malformed or corrupted

**InvalidCredentialsError:**

```json
{
  "detail": "Invalid email or password"
}
```

**When it occurs:**

- Basic authentication mode (username/password) authentication fails
- User not found or password incorrect (not used in OAuth proxy mode)

**AuthenticationError (Generic):**

```json
{
  "detail": "Authentication failed"
}
```

**When it occurs:**

- Generic authentication failure
- Catch-all for unexpected authentication issues

#### 405 Method Not Allowed

**DisabledFeatureError:**

```json
{
  "detail": "This feature is disabled for current deployment"
}
```

**When it occurs:**

- Attempting to use password login when in OAuth proxy mode
- Attempting to use registration endpoint when in OAuth proxy mode
- Feature not available in current authentication mode

#### 500 Internal Server Error

**OAuth2ConfigurationError:**

```json
{
  "detail": "OAuth authentication is not configured"
}
```

**When it occurs:**

- `AUTH_MODE=oauth_proxy` but `AZURE_TENANT_ID` not set
- JWT validation enabled but JWKS URL not configured
- Missing required Azure AD configuration

**RequestContextUnavailableError:**

```json
{
  "detail": "Request context unavailable"
}
```

**When it occurs:**

- FastAPI Request object unavailable (internal error)
- Should not occur in normal operation
- Indicates potential framework or testing issue

### Error Handling Example

**Python Error Handling:**

```python
import requests
from requests.exceptions import HTTPError

def get_user_profile(access_token: str):
    """Fetch user profile with comprehensive error handling."""
    try:
        response = requests.get(
            "http://localhost:8000/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except HTTPError as e:
        if e.response.status_code == 401:
            error_detail = e.response.json().get("detail", "Authentication failed")

            if "Missing bearer token" in error_detail:
                print("Error: No authentication token provided")
                # Redirect to login
                return None

            elif "expired token" in error_detail:
                print("Error: Token has expired, refreshing...")
                # Attempt token refresh
                new_token = refresh_access_token()
                return get_user_profile(new_token)

            elif "missing email claim" in error_detail:
                print("Error: Invalid token (missing email)")
                # Token is invalid, clear and re-authenticate
                clear_token()
                return None

            else:
                print(f"Authentication error: {error_detail}")
                return None

        elif e.response.status_code == 500:
            print("Server error: OAuth2 may not be configured correctly")
            return None

        else:
            print(f"Unexpected error: {e.response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print("Error: Request timeout")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
profile = get_user_profile(access_token)
if profile:
    print(f"Welcome, {profile['claims']['name']}!")
else:
    print("Please log in again")
```

**JavaScript Error Handling:**

```javascript
async function getUserProfile(accessToken) {
  try {
    const response = await fetch('http://localhost:8000/api/auth/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      const error = await response.json();

      switch (response.status) {
        case 401:
          if (error.detail.includes('expired')) {
            console.log('Token expired, attempting refresh...');
            const newToken = await refreshAccessToken();
            return getUserProfile(newToken);
          } else if (error.detail.includes('Missing bearer token')) {
            console.error('No token provided, redirecting to login...');
            window.location.href = '/login';
            return null;
          } else {
            console.error('Authentication failed:', error.detail);
            window.location.href = '/login';
            return null;
          }

        case 500:
          console.error('Server configuration error:', error.detail);
          showErrorMessage('Authentication service unavailable');
          return null;

        default:
          console.error(`Unexpected error (${response.status}):`, error.detail);
          return null;
      }
    }

    return await response.json();

  } catch (error) {
    console.error('Network error:', error);
    showErrorMessage('Unable to connect to server');
    return null;
  }
}
```

### Logging

Authentication errors are logged with appropriate severity levels:

```python
# In backend/api/auth/dependencies.py
logger.warning(f"[AUTH-ME] Token missing email claim")  # Warning for client errors
logger.error(f"[AUTH-OAUTH] JWT validation failed: {exc}")  # Error for validation issues
logger.debug(f"[AUTH] OAuth proxy authentication successful: {email}")  # Debug for success
```

**Log Levels:**

- **DEBUG**: Successful authentication, claim extraction
- **INFO**: User creation, configuration loading
- **WARNING**: Token validation issues, missing claims, database sync failures
- **ERROR**: JWT validation errors, configuration errors

## Integration with Services Layer

### Dependency Flow

The auth module integrates tightly with the services layer for authentication logic:

```
┌───────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Route: GET /api/auth/me                             │    │
│  │ (backend/api/auth/routes.py)                        │    │
│  └────────────────────┬────────────────────────────────┘    │
│                       │ Depends(get_current_user)           │
│                       ▼                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Dependency: get_current_user                        │    │
│  │ (backend/api/auth/dependencies.py)                  │    │
│  └────────────────────┬────────────────────────────────┘    │
└───────────────────────┼────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                   Services Layer                              │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ OAuth2ProxyAuth.verify_and_sync()                    │   │
│  │ (backend/services/auth/providers/oauth2_proxy.py)    │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                          │
│                   ├─► JWT Decoding (jwt_utils.py)           │
│                   │                                          │
│                   ├─► Token Extraction (token_extractor.py) │
│                   │                                          │
│                   └─► User Sync (user_sync.py)              │
│                       └─► Database (database.py)            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Example Integration

Here's how the graph API module uses the auth dependency:

**In backend/api/graph/routes.py:**

```python
from typing import Any, Dict
from fastapi import APIRouter, Depends
from backend.api.auth.dependencies import get_current_user
from backend.api.graph.handlers import graph_crud

router = APIRouter(prefix="/api/graph", tags=["graph"])

@router.get("/list")
async def list_graphs(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all workflows for the authenticated user.

    This endpoint uses the auth module's get_current_user dependency
    to authenticate the request and extract user information.

    Args:
        current_user: User claims dictionary from authentication

    Returns:
        List of workflows owned by the user
    """
    # current_user contains:
    # {
    #   "email": "user@example.com",
    #   "sub": "user-id-123",
    #   "name": "John Doe",
    #   ...
    # }

    return await graph_crud.handle_list_graphs(current_user)
```

**In backend/api/graph/handlers/graph_crud.py:**

```python
from typing import Any, Dict, List
from backend.services.graph.storage import GraphStorageService

async def handle_list_graphs(current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle listing workflows for the authenticated user.

    Args:
        current_user: User claims from get_current_user dependency

    Returns:
        List of workflow dictionaries
    """
    # Extract user ID from claims
    user_id = current_user["sub"]
    user_email = current_user["email"]

    # Use GraphStorageService to fetch user-scoped workflows
    storage = GraphStorageService()
    workflows = storage.list_graphs_by_user(user_id)

    return {
        "success": True,
        "user": user_email,
        "workflows": workflows,
        "count": len(workflows)
    }
```

### Complete Authentication Flow Example

Here's an end-to-end example showing the complete authentication and authorisation flow:

```python
# 1. Client makes authenticated request
# ----------------------------------
import requests

access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

response = requests.get(
    "http://localhost:8000/api/graph/list",
    headers={"Authorization": f"Bearer {access_token}"}
)


# 2. FastAPI route receives request
# ----------------------------------
# In backend/api/graph/routes.py

from fastapi import APIRouter, Depends
from backend.api.auth.dependencies import get_current_user

@router.get("/list")
async def list_graphs(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    # FastAPI calls get_current_user dependency first
    # This validates the token and returns user claims
    return await graph_crud.handle_list_graphs(current_user)


# 3. get_current_user dependency validates authentication
# --------------------------------------------------------
# In backend/api/auth/dependencies.py

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request: Request = None,
) -> Dict[str, Any]:
    # Extract email from oauth2-proxy headers (if present)
    email = extract_email_from_oauth_proxy_headers(request)

    if email:
        # Header-based authentication (trusted proxy)
        return _authenticate_oauth_proxy_with_headers(request)

    # Fallback to token-based authentication
    token = extract_token_from_request(request, credentials)
    if not token:
        raise MissingTokenError()

    return _authenticate_oauth_proxy_with_token(token, request)


# 4. OAuth2ProxyAuth validates token and syncs user
# --------------------------------------------------
# In backend/services/auth/providers/oauth2_proxy.py

class OAuth2ProxyAuth:
    def verify_and_sync(self, token: str, request: Request) -> Dict[str, Any]:
        # Decode and validate JWT token
        claims = self._decode_token(token)

        # Enrich claims with additional information
        email = extract_email_from_oauth_proxy_headers(request)
        claims = enrich_claims(claims, header_email=email)

        # Sync user to database
        sync_user_from_claims(claims)

        return claims


# 5. User sync service updates database
# --------------------------------------
# In backend/services/auth/user_sync.py

def sync_user_from_claims(claims: Dict[str, Any]) -> None:
    user_id = claims.get("sub")
    email = claims.get("email")

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            # Create new user
            user = User(id=user_id, email=email)
            db.add(user)

        # Update user attributes
        user.email = email
        user.name = claims.get("name")
        user.last_login_at = datetime.now(timezone.utc)
        user.last_claims = claims


# 6. Handler processes the authenticated request
# -----------------------------------------------
# In backend/api/graph/handlers/graph_crud.py

async def handle_list_graphs(current_user: Dict[str, Any]):
    user_id = current_user["sub"]

    # Fetch user-scoped workflows from database
    storage = GraphStorageService()
    workflows = storage.list_graphs_by_user(user_id)

    return {
        "success": True,
        "workflows": workflows
    }


# 7. Response returned to client
# -------------------------------
# {
#   "success": true,
#   "workflows": [
#     {"id": "workflow-1", "name": "My Workflow", ...},
#     {"id": "workflow-2", "name": "Another Workflow", ...}
#   ]
# }
```

### Services Used

The auth module depends on these services:

#### OAuth2ProxyAuth Provider

**Location:** [backend/services/auth/providers/oauth2_proxy.py](../../services/auth/providers/oauth2_proxy.py)

**Purpose:** Validate JWT tokens forwarded by oauth2-proxy and persist users to database

**Key Methods:**

- `verify_and_sync(token, request)` - Main authentication method
- `_decode_token(token)` - Decode and validate JWT signature, audience, issuer

**Usage:**

```python
from backend.services.auth import get_oauth_proxy_auth

oauth_auth = get_oauth_proxy_auth()
claims = oauth_auth.verify_and_sync(token, request)
```

#### User Sync Service

**Location:** [backend/services/auth/user_sync.py](../../services/auth/user_sync.py)

**Purpose:** Synchronise authenticated users to the database

**Key Functions:**

- `sync_user_from_claims(claims)` - Create or update user in database
- `enrich_claims(claims, header_email)` - Enrich claims with email and name
- `extract_email_from_claims(claims)` - Extract email from multiple claim fields

**Usage:**

```python
from backend.services.auth.user_sync import sync_user_from_claims

claims = {"sub": "user123", "email": "user@example.com", "name": "John Doe"}
sync_user_from_claims(claims)  # Creates or updates user in database
```

#### JWT Utilities

**Location:** [backend/services/auth/jwt_utils.py](../../services/auth/jwt_utils.py)

**Purpose:** JWT token decoding without validation (for claim extraction)

**Key Functions:**

- `decode_token_without_verification(token)` - Decode JWT without signature verification

**Usage:**

```python
from backend.services.auth.jwt_utils import decode_token_without_verification

# Decode token to extract claims (validation already done by oauth2-proxy)
unverified_claims = decode_token_without_verification(token)
```

#### Token Extractor

**Location:** [backend/services/auth/token_extractor.py](../../services/auth/token_extractor.py)

**Purpose:** Extract authentication tokens from HTTP requests

**Key Functions:**

- `extract_token_from_request(request, credentials)` - Extract JWT from Authorization header
- `extract_email_from_oauth_proxy_headers(request)` - Extract email from X-Auth-Request-Email
- `log_auth_headers(request)` - Log authentication headers for debugging

**Usage:**

```python
from backend.services.auth.token_extractor import (
    extract_token_from_request,
    extract_email_from_oauth_proxy_headers
)

# Extract token from Authorization: Bearer header
token = extract_token_from_request(request, credentials)

# Extract email from oauth2-proxy header
email = extract_email_from_oauth_proxy_headers(request)
```

#### Database Service

**Location:** [backend/services/database.py](../../backend/services/database.py)

**Purpose:** Database connection and session management

**Usage:**

```python
from backend.services.database import get_db
from backend.models.auth.user import User

# Use context manager for automatic session cleanup
with get_db() as db:
    user = db.query(User).filter(User.email == email).first()
```

## Configuration

### Environment Variables

The auth module's behaviour is controlled by environment variables:

#### Core Configuration

```bash
# Authentication Mode
# Options: "basic" (username/password) or "oauth_proxy" (OAuth2 proxy)
# Default: "basic"
AUTH_MODE=oauth_proxy

# Disable JWT signature validation (trust oauth2-proxy completely)
# Options: "true", "false"
# Default: "false"
# WARNING: Only disable in development or when oauth2-proxy is fully trusted
OAUTH_PROXY_DISABLE_JWT_VALIDATION=false
```

#### Azure AD Configuration

Required when `AUTH_MODE=oauth_proxy` and `OAUTH_PROXY_DISABLE_JWT_VALIDATION=false`:

```bash
# Azure AD Tenant ID (required for JWT validation)
AZURE_TENANT_ID=12345678-1234-1234-1234-123456789012

# Azure AD Client ID (application ID)
AZURE_CLIENT_ID=abcdef12-3456-7890-abcd-ef1234567890

# Comma-separated list of allowed JWT audiences
# Typically includes the client ID and/or API identifier
AZURE_ALLOWED_AUDIENCES=api://agenticstudio-api,abcdef12-3456-7890-abcd-ef1234567890

# Azure AD authority URL (default: https://login.microsoftonline.com)
# Only change if using Azure Government or other Azure clouds
AZURE_AUTHORITY=https://login.microsoftonline.com
```

#### Advanced Configuration

```bash
# Custom JWKS URL (for non-Azure identity providers)
# If set, overrides the calculated Azure AD JWKS URL
AZURE_JWKS_URL=https://your-identity-provider.com/.well-known/jwks.json

# JWT Secret (for basic auth mode only, not used in OAuth proxy mode)
JWT_SECRET=your-secret-key-change-in-production

# JWT Algorithm (for basic auth mode only)
JWT_ALGORITHM=HS256

# JWT Expiration (for basic auth mode only, in hours)
JWT_EXPIRATION_HOURS=24
```

### Configuration Modes

#### OAuth Proxy Mode (Recommended)

**When to use:**

- Production deployments
- Azure AD / Entra ID authentication
- When using oauth2-proxy reverse proxy
- Multi-tenant applications

**Configuration:**

```bash
AUTH_MODE=oauth_proxy
OAUTH_PROXY_DISABLE_JWT_VALIDATION=false
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_ALLOWED_AUDIENCES=api://your-api-id
```

**Benefits:**

- Most secure (oauth2-proxy + JWT validation)
- Supports multiple identity providers
- Session management handled by proxy
- Token refresh handled by proxy

#### OAuth Proxy Mode (Validation Disabled)

**When to use:**

- Development environments
- When oauth2-proxy is fully trusted
- Performance-critical scenarios (avoids JWKS fetches)

**Configuration:**

```bash
AUTH_MODE=oauth_proxy
OAUTH_PROXY_DISABLE_JWT_VALIDATION=true
```

**Benefits:**

- Faster authentication (no JWT validation overhead)
- Simpler configuration (no Azure AD setup needed)

**Risks:**

- Relies entirely on oauth2-proxy security
- No cryptographic verification of tokens
- Vulnerable if oauth2-proxy is misconfigured or bypassed

#### Basic Mode

**When to use:**

- Development only
- Testing without OAuth setup
- Legacy compatibility

**Configuration:**

```bash
AUTH_MODE=basic
JWT_SECRET=your-secret-key
```

**Note:** Basic mode requires username/password authentication endpoints (not included in this module).

## Usage Examples

### Complete User Authentication Example

This example demonstrates a complete authentication flow from login to API access:

```python
"""
Complete authentication flow example for AgenticStudio.

This example shows:
1. Obtaining an access token from Azure AD
2. Using the token to authenticate with AgenticStudio
3. Fetching the user profile
4. Making authenticated API calls
"""

import requests
from typing import Optional, Dict, Any

class AgenticStudioClient:
    """Client for interacting with AgenticStudio API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.user_profile: Optional[Dict[str, Any]] = None

    def set_token(self, access_token: str):
        """Set the access token for authentication."""
        self.access_token = access_token

    def _headers(self) -> Dict[str, str]:
        """Get headers with authorization token."""
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def authenticate(self) -> bool:
        """
        Authenticate with AgenticStudio and fetch user profile.

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.access_token:
            print("Error: No access token set")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/auth/me",
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()

            self.user_profile = response.json()
            print(f"✓ Authenticated as {self.user_profile['claims']['name']}")
            print(f"  Email: {self.user_profile['claims']['email']}")
            print(f"  User ID: {self.user_profile['user']['id']}")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error = e.response.json()
                print(f"✗ Authentication failed: {error.get('detail', 'Unknown error')}")
            else:
                print(f"✗ HTTP error {e.response.status_code}")
            return False

        except Exception as e:
            print(f"✗ Error: {e}")
            return False

    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Get the current user profile (from cache or API)."""
        if not self.user_profile:
            self.authenticate()
        return self.user_profile

    def list_workflows(self) -> Optional[list]:
        """Fetch user's workflows (example authenticated API call)."""
        if not self.access_token:
            print("Error: Not authenticated")
            return None

        try:
            response = requests.get(
                f"{self.base_url}/api/graph/list",
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            workflows = data.get("workflows", [])
            print(f"✓ Found {len(workflows)} workflows")
            return workflows

        except requests.exceptions.HTTPError as e:
            print(f"✗ Failed to fetch workflows: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # 1. Obtain access token from Azure AD (simplified)
    # In production, use MSAL library for proper OAuth flow
    access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

    # 2. Create client and authenticate
    client = AgenticStudioClient(base_url="http://localhost:8000")
    client.set_token(access_token)

    if client.authenticate():
        # 3. Use authenticated client for API calls
        profile = client.get_user_profile()
        print(f"\nUser Profile:")
        print(f"  Name: {profile['claims']['name']}")
        print(f"  Email: {profile['claims']['email']}")
        print(f"  Account Created: {profile['user']['created_at']}")

        # 4. Make other authenticated API calls
        workflows = client.list_workflows()
        if workflows:
            for workflow in workflows:
                print(f"  - {workflow['name']}")
    else:
        print("Failed to authenticate")
```

### JavaScript/TypeScript Example

```typescript
/**
 * AgenticStudio authentication client for browser applications.
 *
 * This example uses the MSAL.js library for Azure AD authentication.
 */

import { PublicClientApplication } from "@azure/msal-browser";

interface UserProfile {
  claims: {
    email: string;
    sub: string;
    name: string;
    given_name?: string;
    family_name?: string;
  };
  user: {
    id: string;
    email: string;
    name: string;
    created_at: string;
    updated_at: string;
  } | null;
}

class AgenticStudioAuth {
  private msalInstance: PublicClientApplication;
  private accessToken: string | null = null;
  private userProfile: UserProfile | null = null;
  private baseUrl: string;

  constructor(
    tenantId: string,
    clientId: string,
    baseUrl: string = "http://localhost:8000"
  ) {
    this.baseUrl = baseUrl;

    // Initialize MSAL for Azure AD authentication
    this.msalInstance = new PublicClientApplication({
      auth: {
        clientId: clientId,
        authority: `https://login.microsoftonline.com/${tenantId}`,
        redirectUri: window.location.origin,
      },
      cache: {
        cacheLocation: "localStorage",
        storeAuthStateInCookie: false,
      },
    });
  }

  /**
   * Initiate login flow with Azure AD.
   */
  async login(): Promise<boolean> {
    try {
      await this.msalInstance.initialize();

      const loginResponse = await this.msalInstance.loginPopup({
        scopes: ["api://your-api-id/access_as_user"],
      });

      this.accessToken = loginResponse.accessToken;
      console.log("✓ Logged in successfully");

      // Verify authentication with AgenticStudio
      return await this.verifyAuthentication();

    } catch (error) {
      console.error("✗ Login failed:", error);
      return false;
    }
  }

  /**
   * Acquire access token (with automatic refresh if expired).
   */
  async getAccessToken(): Promise<string | null> {
    try {
      const accounts = this.msalInstance.getAllAccounts();
      if (accounts.length === 0) {
        console.error("No accounts found, please login");
        return null;
      }

      const silentRequest = {
        scopes: ["api://your-api-id/access_as_user"],
        account: accounts[0],
      };

      const response = await this.msalInstance.acquireTokenSilent(silentRequest);
      this.accessToken = response.accessToken;
      return this.accessToken;

    } catch (error) {
      console.error("✗ Token acquisition failed:", error);
      // Fall back to interactive login
      await this.login();
      return this.accessToken;
    }
  }

  /**
   * Verify authentication with AgenticStudio API.
   */
  async verifyAuthentication(): Promise<boolean> {
    if (!this.accessToken) {
      console.error("No access token available");
      return false;
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/auth/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${this.accessToken}`,
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        console.error("✗ Authentication verification failed:", error.detail);
        return false;
      }

      this.userProfile = await response.json();
      console.log(`✓ Authenticated as ${this.userProfile!.claims.name}`);
      return true;

    } catch (error) {
      console.error("✗ Verification error:", error);
      return false;
    }
  }

  /**
   * Get user profile (from cache or API).
   */
  async getUserProfile(): Promise<UserProfile | null> {
    if (!this.userProfile) {
      await this.verifyAuthentication();
    }
    return this.userProfile;
  }

  /**
   * Make authenticated API request.
   */
  async authenticatedRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T | null> {
    const token = await this.getAccessToken();
    if (!token) {
      throw new Error("Failed to acquire access token");
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(`API error: ${error.detail || response.statusText}`);
      }

      return await response.json();

    } catch (error) {
      console.error(`✗ Request failed for ${endpoint}:`, error);
      return null;
    }
  }

  /**
   * Logout from Azure AD and clear local state.
   */
  async logout(): Promise<void> {
    await this.msalInstance.logoutPopup();
    this.accessToken = null;
    this.userProfile = null;
    console.log("✓ Logged out successfully");
  }
}

// Example usage in a React component
export async function exampleUsage() {
  const auth = new AgenticStudioAuth(
    "your-tenant-id",
    "your-client-id",
    "http://localhost:8000"
  );

  // Login
  const success = await auth.login();
  if (!success) {
    console.error("Login failed");
    return;
  }

  // Get user profile
  const profile = await auth.getUserProfile();
  if (profile) {
    console.log("User Profile:", profile.claims.name);
    console.log("Email:", profile.claims.email);
    console.log("User ID:", profile.user?.id);
  }

  // Make authenticated API calls
  const workflows = await auth.authenticatedRequest<any>("/api/graph/list");
  if (workflows) {
    console.log("Workflows:", workflows.workflows);
  }

  // Logout
  await auth.logout();
}
```

### cURL Examples

**Basic Authentication Request:**

```bash
# Fetch user profile
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Accept: application/json"
```

**With Verbose Output:**

```bash
# See full request/response headers
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Accept: application/json" \
  -v
```

**Save Token and Reuse:**

```bash
# Save token to environment variable
export ACCESS_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# Use token in multiple requests
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  | jq .

curl -X GET "http://localhost:8000/api/graph/list" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  | jq .
```

**Extract User Email:**

```bash
# Extract specific fields with jq
curl -s -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  | jq -r '.claims.email'
```

## Performance Considerations

### Endpoint Performance

The auth module provides a fast, lightweight authentication mechanism:

**Fast (<50ms):**

- `GET /api/auth/me` - Typically 20-50ms
  - Header-based auth: ~20ms (no JWT validation)
  - Token-based auth: ~50ms (includes JWT validation + JWKS fetch)

**Performance Factors:**

1. **Header-Based vs Token-Based:**
    - Header-based: Fastest (~20ms) - trusts oauth2-proxy, minimal validation
    - Token-based: Slower (~50ms) - full JWT validation, JWKS fetch

2. **Database Query:**
    - Single SELECT by email (indexed): ~5-10ms
    - User creation (first login): ~20-30ms

3. **JWKS Fetch:**
    - First validation: ~100-200ms (fetches public keys from Azure AD)
    - Subsequent validations: ~5-10ms (keys cached by PyJWKClient)

4. **User Synchronisation:**
    - Existing user update: ~10ms
    - New user creation: ~30ms

### Optimisation Tips

#### Client-Side Caching

Cache user profile in the frontend to avoid repeated API calls:

```javascript
// ✅ GOOD: Cache user profile in session storage
async function getUserProfile() {
  // Check cache first
  const cached = sessionStorage.getItem('user_profile');
  if (cached) {
    const profile = JSON.parse(cached);
    // Verify cache age (e.g., cache for 5 minutes)
    const cacheTime = sessionStorage.getItem('user_profile_time');
    if (Date.now() - parseInt(cacheTime) < 5 * 60 * 1000) {
      return profile;
    }
  }

  // Fetch from API
  const response = await fetch('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` }
  });
  const profile = await response.json();

  // Cache result
  sessionStorage.setItem('user_profile', JSON.stringify(profile));
  sessionStorage.setItem('user_profile_time', Date.now().toString());

  return profile;
}

// ❌ BAD: Fetch user profile on every component render
function UserProfileBadge() {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    // This runs on every render - wasteful!
    fetch('/api/auth/me').then(r => r.json()).then(setProfile);
  }, []);  // Empty deps means runs on every mount

  return <div>{profile?.claims.name}</div>;
}
```

#### Token Validation Configuration

Choose the appropriate validation mode for your environment:

```bash
# ✅ GOOD: Production (full validation)
AUTH_MODE=oauth_proxy
OAUTH_PROXY_DISABLE_JWT_VALIDATION=false
AZURE_TENANT_ID=your-tenant-id

# ✅ GOOD: Development (faster, less secure)
AUTH_MODE=oauth_proxy
OAUTH_PROXY_DISABLE_JWT_VALIDATION=true

# ❌ BAD: Production with validation disabled (security risk)
# Only disable JWT validation if oauth2-proxy is fully trusted
# and cannot be bypassed (e.g., network-level security)
```

#### Database Connection Pooling

The auth module uses SQLAlchemy connection pooling automatically:

```python
# Connection pooling configured in backend/services/database.py
# Default pool size: 5 connections
# Max overflow: 10 connections
# Connection recycle: 3600 seconds

# ✅ GOOD: Use context manager (automatic connection return)
with get_db() as db:
    user = db.query(User).filter(User.email == email).first()
# Connection automatically returned to pool

# ❌ BAD: Manual session management (connection leak risk)
db = get_db()
user = db.query(User).filter(User.email == email).first()
# Connection not returned to pool!
```

#### Request Batching

Avoid making unnecessary authentication checks:

```python
# ✅ GOOD: Authenticate once per request
@router.get("/dashboard")
async def get_dashboard(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Authenticated once at route level
    user_id = current_user["sub"]

    # Make multiple data fetches with same user context
    workflows = await fetch_workflows(user_id)
    executions = await fetch_executions(user_id)
    documents = await fetch_documents(user_id)

    return {
        "workflows": workflows,
        "executions": executions,
        "documents": documents
    }

# ❌ BAD: Re-authenticate for each sub-operation
@router.get("/dashboard")
async def get_dashboard_bad(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Each of these fetches re-authenticates (wasteful!)
    workflows = await fetch_workflows_with_auth(request)
    executions = await fetch_executions_with_auth(request)
    documents = await fetch_documents_with_auth(request)
```

#### Header-Based Authentication

When deploying with oauth2-proxy, prefer header-based authentication:

```python
# Header-based authentication flow (fastest):
# 1. oauth2-proxy validates user session
# 2. oauth2-proxy injects X-Auth-Request-Email header
# 3. AgenticStudio trusts header and builds claims
# 4. No JWT validation overhead

# Token-based authentication flow (slower):
# 1. Client sends Authorization: Bearer header
# 2. AgenticStudio fetches JWKS from Azure AD (first time)
# 3. AgenticStudio validates JWT signature
# 4. AgenticStudio validates audience, issuer, expiration
# 5. AgenticStudio extracts claims

# To prefer header-based auth, ensure oauth2-proxy is configured
# to forward headers:
# --set-xauthrequest=true
# --pass-access-token=true
```

### Monitoring & Profiling

Use FastAPI middleware to monitor authentication performance:

```python
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class AuthPerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/auth/me":
            start_time = time.time()
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000  # ms

            # Log slow authentication requests
            if duration > 100:
                logger.warning(f"Slow auth request: {duration:.2f}ms")

            # Add performance header
            response.headers["X-Auth-Duration-Ms"] = f"{duration:.2f}"
            return response

        return await call_next(request)

app.add_middleware(AuthPerformanceMiddleware)
```

## Related Documentation

### Architecture Documentation

- [Architecture Overview](../../../docs/architecture/00-overview.md) - System architecture and components
- [Architecture Diagrams](../../../docs/architecture/01-architecture-diagram.md) - Visual architecture diagrams
- [Authentication Architecture](../architecture/authentication.md) - Detailed authentication architecture (if exists)

### API Documentation

- [Graph API](../graph/graph.md) - Workflow management API (uses `get_current_user` dependency)
- [Execution API](../execution/execution.md) - Workflow execution endpoints
- [Documents API](../documents/documents.md) - Document management endpoints
- [API Overview](../../../docs/for-agents/api/README.md) - Complete API documentation index

### Services Documentation

- [Authentication Services](../../services/auth.md) - Auth service layer implementation (if exists)
- [Database Services](../../services/database.md) - Database connection and models (if exists)

### Setup & Configuration

- [OAuth2 Proxy Setup](../setup/oauth2-proxy.md) - oauth2-proxy configuration guide (if exists)
- [Azure AD Setup](../setup/azure-ad.md) - Azure AD app registration guide (if exists)
- [Environment Variables](../setup/environment.md) - Complete environment variable reference (if exists)

### Security Documentation

- [Security Best Practices](../security/best-practices.md) - Security recommendations (if exists)
- [Token Management](../security/token-management.md) - JWT token handling guide (if exists)

## Summary

The Authentication API module provides OAuth2 proxy authentication for AgenticStudio, enabling secure and scalable user
authentication through Microsoft Entra ID (Azure AD). This module is foundational to the entire application, as all API
modules depend on its `get_current_user` dependency for authentication.

**Key Features:**

- **OAuth2 Proxy Integration**: Seamless integration with oauth2-proxy reverse proxy for production deployments
- **Dual Authentication Modes**: Header-based (fastest, trusts proxy) and token-based (most secure, full JWT validation)
- **Automatic User Synchronisation**: Users are automatically created and updated in the database on authentication
- **Reusable Dependency**: The `get_current_user` dependency is exported and used across all API modules
- **Flexible Configuration**: Support for Azure AD, custom OIDC providers, and development modes
- **Comprehensive Error Handling**: Detailed error types for all authentication failure scenarios
- **Performance Optimised**: Fast authentication (<50ms typical) with minimal overhead
- **Security-First Design**: Cryptographic JWT validation with audience, issuer, and expiration checks

**Primary Use Cases:**

1. **User Authentication**: Validate user identity and extract user information
2. **API Protection**: Protect all API endpoints with authentication requirements
3. **User Profile Retrieval**: Fetch user profile information for display
4. **Session Management**: Verify active user sessions and handle token expiration
5. **User Synchronisation**: Keep database user records in sync with identity provider

**Integration Points:**

- **All API Modules**: Every API module imports and uses `get_current_user` dependency
- **OAuth2 Proxy**: Deployed behind oauth2-proxy for production authentication
- **Azure AD / Entra ID**: Integrated with Microsoft identity platform
- **Database**: Automatic user synchronisation to PostgreSQL/SQLite
- **Frontend**: Token-based authentication from web applications

**Architecture Highlights:**

The auth module follows a **dependency injection pattern** where authentication logic is encapsulated in a reusable
FastAPI dependency (`get_current_user`). This allows:

- **Centralised Authentication**: Change authentication logic once, affect all endpoints
- **Testability**: Easy to mock authentication in tests
- **Flexibility**: Support multiple authentication modes transparently
- **Performance**: Choose between trusted header-based auth (fastest) or cryptographic token validation (most secure)

**Example Usage in Other Modules:**

```python
# Any API module can use authentication by importing the dependency
from backend.api.auth.dependencies import get_current_user
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/protected-resource")
async def protected_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """This endpoint is automatically protected by authentication."""
    user_email = current_user["email"]
    user_id = current_user["sub"]
    return {"message": f"Hello, {current_user.get('name', 'User')}!"}
```

The auth module is intentionally minimal (1 endpoint) but foundational - it provides the authentication infrastructure
that all other API modules depend upon. Its simplicity belies its importance: every authenticated request in AgenticStudio
flows through the `get_current_user` dependency defined in this module.
