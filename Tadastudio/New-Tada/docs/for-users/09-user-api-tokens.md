# User API Tokens (Personal Access Tokens)

## Overview

User API Tokens (also known as Personal Access Tokens or PATs) are user-scoped authentication tokens that allow you to
authenticate HTTP execution requests with your own credentials. These tokens inherit your workflow permissions and
provide a more flexible and secure alternative to workflow-specific tokens.

## Key Features

- **User-Scoped**: Tokens inherit the user's workflow access permissions
- **Multi-Workflow**: A single token can be used across multiple workflows
- **Revocable**: Tokens can be individually revoked without affecting other integrations
- **Expirable**: Tokens can have expiration dates (1-365 days or never expire)
- **Auditable**: Track token usage, last used date, and usage count
- **Secure**: Tokens are stored hashed and only shown once during creation

## Token Format

User API tokens use the prefix `na_` (Agentic Studio) for easy identification:

```
na_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

## Creating a Token

### Via UI

1. Navigate to **Settings** → **API Tokens**
2. Click **Create New Token**
3. Fill in the token details:
    - **Name**: A descriptive name (e.g., "CI/CD Pipeline Token")
    - **Description**: Optional description of the token's purpose
    - **Scopes**: Select workflow access (currently defaults to all workflows)
    - **Expiration**: Choose expiration period or set to never expire
4. Click **Create Token**
5. **Important**: Copy the token immediately - it will never be shown again!

### Via API

**Endpoint**: `POST /api/auth/tokens`

**Authentication**: Requires OAuth2/OIDC authentication (via OAuth2Proxy)

**Request Body**:

```json
{
  "name": "My Integration Token",
  "scopes": ["workflow:*"],
  "description": "Token for CI/CD pipeline",
  "expires_in_days": 90
}
```

**Request Parameters**:

- `name` (string, required): User-friendly token name (1-100 characters)
- `scopes` (array, optional): List of scopes (default: `["workflow:*"]`)
  - `"workflow:*"` - Access to all workflows user has permission to use
  - `"workflow:my-workflow"` - Access to a specific workflow
- `description` (string, optional): Description of token purpose (max 500 characters)
- `expires_in_days` (integer, optional): Number of days until expiration (1-365, or null for no expiration)

**Response**:

```json
{
  "success": true,
  "message": "Token created successfully. Save it now - it won't be shown again!",
  "token": "na_abc123def456...",
  "token_id": "uuid-here",
  "token_name": "My Integration Token",
  "token_prefix": "na_abc123de",
  "created_at": "2025-10-22T10:30:00Z",
  "expires_at": "2026-01-20T10:30:00Z",
  "scopes": ["workflow:*"]
}
```

**Important**: The `token` field contains the full plaintext token and is only returned once. Make sure to save it
securely immediately.

## Using a Token

User API tokens can be used to authenticate HTTP execution requests by including them as a query parameter:

```bash
curl -X POST "https://your-api.com/api/http-execution/trigger/my-workflow?token=na_abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process this data",
    "async_mode": false
  }'
```

### Token Validation Flow

1. System checks if token starts with `na_` prefix
2. Token is validated against the `user_api_tokens` table
3. Token expiration and active status are checked
4. User's workflow permissions are verified via `WorkflowMembership`
5. If all checks pass, the workflow execution proceeds

### Token Priority

The HTTP authentication system supports three token types (in priority order):

1. **User API Tokens** (`na_*`) - Highest priority, user-scoped
2. **Workflow Auth Tokens** - Workflow-scoped tokens from publishing
3. **Legacy Tokens** - In-memory tokens for backward compatibility

If a request includes a User API Token, it will be validated first.

## Managing Tokens

### List All Tokens

**Endpoint**: `GET /api/auth/tokens`

**Authentication**: Requires OAuth2/OIDC authentication

**Response**:

```json
{
  "success": true,
  "tokens": [
    {
      "id": "uuid-here",
      "name": "My Integration Token",
      "prefix": "na_abc123de",
      "description": "Token for CI/CD pipeline",
      "scopes": ["workflow:*"],
      "is_active": true,
      "created_at": "2025-10-22T10:30:00Z",
      "expires_at": "2026-01-20T10:30:00Z",
      "last_used_at": "2025-10-22T15:45:00Z",
      "last_used_ip": "192.168.1.100",
      "usage_count": 42
    }
  ],
  "total_count": 1
}
```

**Note**: The plaintext token is never returned after creation. Only the token prefix is shown for identification.

### Get Token Details

**Endpoint**: `GET /api/auth/tokens/{token_id}`

**Authentication**: Requires OAuth2/OIDC authentication

**Response**: Returns the same structure as a single token in the list response

### Revoke a Token

**Endpoint**: `DELETE /api/auth/tokens/{token_id}`

**Authentication**: Requires OAuth2/OIDC authentication

**Response**:

```json
{
  "success": true,
  "message": "Token revoked successfully",
  "token_id": "uuid-here"
}
```

**Important**: Revoked tokens cannot be reactivated. You must create a new token.

### Update Token Scopes

**Endpoint**: `PUT /api/auth/tokens/{token_id}/scopes`

**Authentication**: Requires OAuth2/OIDC authentication

**Request Body**:

```json
{
  "scopes": ["workflow:specific-workflow"]
}
```

**Response**: Returns the updated token details

## Security Best Practices

### Token Storage

- **Never commit tokens to version control**
- Store tokens in secure secret management systems (e.g., AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
- Use environment variables for tokens in CI/CD pipelines
- Rotate tokens periodically (recommended: every 90 days)

### Token Scoping

- **Principle of Least Privilege**: Only grant access to workflows that the integration needs
- Use workflow-specific scopes (`workflow:my-workflow`) instead of wildcard scopes (`workflow:*`) when possible
- Create separate tokens for different integrations to enable granular revocation

### Token Lifecycle

- Set appropriate expiration dates based on use case:
  - **CI/CD pipelines**: 90-365 days with rotation
  - **Temporary integrations**: 7-30 days
  - **Long-term automation**: 365 days with monitoring
- Regularly audit token usage via the UI
- Revoke unused or compromised tokens immediately

### Monitoring

- Monitor `last_used_at` and `usage_count` fields to detect suspicious activity
- Review `last_used_ip` for unexpected locations
- Set up alerts for tokens that haven't been used in 30+ days

## Use Cases

### CI/CD Integration

```yaml
# GitHub Actions example
name: Trigger Workflow
on: [push]
jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger workflow execution
        env:
          API_TOKEN: ${{ secrets.AGENTIC_STUDIO_TOKEN }}
        run: |
          curl -X POST "https://your-api.com/api/http-execution/trigger/my-workflow?token=$API_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"data": "from-ci-cd"}'
```

### Scheduled Automation

```python
import requests
import os

# Token stored in environment variable
TOKEN = os.environ['AGENTIC_STUDIO_TOKEN']

response = requests.post(
    f"https://your-api.com/api/http-execution/trigger/daily-report?token={TOKEN}",
    json={"date": "2025-10-22"}
)

print(response.json())
```

### External Integration

```javascript
const axios = require('axios');

const token = process.env.AGENTIC_STUDIO_TOKEN;

async function executeWorkflow(workflowName, data) {
  const response = await axios.post(
    `https://your-api.com/api/http-execution/trigger/${workflowName}?token=${token}`,
    data
  );
  return response.data;
}
```

## Comparison: User Tokens vs Workflow Tokens

| Feature         | User API Tokens                      | Workflow Tokens                  |
|-----------------|--------------------------------------|----------------------------------|
| **Scope**       | User-scoped, multi-workflow          | Workflow-specific                |
| **Permissions** | Inherits user's workflow permissions | Full access to specific workflow |
| **Revocable**   | Yes, individually                    | Yes, but affects all users       |
| **Expiration**  | Configurable (1-365 days or never)   | Never expires                    |
| **Auditing**    | Detailed usage stats per token       | Per-workflow stats               |
| **Use Case**    | Personal integrations, CI/CD         | Shared workflow access           |
| **Rotation**    | Easy (create new, revoke old)        | Requires coordination            |

## Troubleshooting

### "Invalid authentication token" Error

**Possible causes:**

1. Token has been revoked
2. Token has expired
3. User no longer has access to the workflow
4. Token format is incorrect (should start with `na_`)

**Solution:**

- Check token status in Settings → API Tokens
- Verify workflow permissions
- Generate a new token if needed

### "Token missing user identifier" Error

**Cause**: Token validation failed to extract user information

**Solution:**

- Ensure you're using a valid User API Token (not a workflow token)
- Check that the token hasn't been corrupted

### Token Not Working After Creation

**Cause**: Token may not have been copied correctly

**Solution:**

- Tokens are only shown once during creation
- If lost, generate a new token
- Use the "Show token" feature carefully to avoid exposure

## API Reference Summary

| Method | Endpoint                       | Description                |
|--------|--------------------------------|----------------------------|
| POST   | `/api/auth/tokens`             | Create new user API token  |
| GET    | `/api/auth/tokens`             | List all user tokens       |
| GET    | `/api/auth/tokens/{id}`        | Get specific token details |
| DELETE | `/api/auth/tokens/{id}`        | Revoke a token             |
| PUT    | `/api/auth/tokens/{id}/scopes` | Update token scopes        |

## Database Schema

The User API Tokens are stored in the `user_api_tokens` table:

```sql
CREATE TABLE user_api_tokens (
    id UUID PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    token_hash VARCHAR NOT NULL,           -- Bcrypt hashed token
    token_prefix VARCHAR(12) NOT NULL,     -- First 11 chars for display
    token_name VARCHAR NOT NULL,
    description TEXT,
    scopes JSON NOT NULL DEFAULT '[]',
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    last_used_ip VARCHAR,
    usage_count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_user_id VARCHAR
);
```

**Indexes:**

- `idx_user_api_tokens_user_id` - For fast user lookup
- `idx_user_api_tokens_token_hash` - For token validation
- `idx_user_api_tokens_token_prefix` - For prefix-based lookup
- `idx_user_api_tokens_is_active` - For active token filtering
- `idx_user_api_tokens_active_valid` - Composite index for active, non-expired tokens

## Related Documentation

- [API Authentication](../for-developers/05-api-authentication.md) — Token types and endpoint access requirements
