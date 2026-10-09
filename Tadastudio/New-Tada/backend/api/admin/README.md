# Admin API - RBAC Feature Access Control

## Overview

The Admin API provides endpoints for managing Role-Based Access Control (RBAC) feature access settings. Admins can control which features require admin privileges and which are accessible to all authenticated users.

## Architecture

### Components

1. **Routes** (`backend/api/admin/routes.py`)
   - REST API endpoints for feature access management
   - CSRF protection on all state-changing operations
   - Rate limiting to prevent abuse
   - Input validation against feature name whitelist

2. **RBAC Service** (`backend/services/auth/rbac.py`)
   - Admin detection logic
   - Feature access checking with TTL-based caching
   - Cache management utilities

3. **Database Model** (`backend/models/configuration/feature_access.py`)
   - Stores feature access control settings
   - Tracks which features are admin-only

4. **Frontend Context** (`frontend/src/contexts/FeatureAccessContext.tsx`)
   - React context for global feature access state
   - Fail-closed error handling for security

## API Endpoints

### GET `/api/admin/feature-access`

List all feature access settings.

**Authentication:** Required (any authenticated user)
**Returns:** All feature access settings with metadata

**Example Response:**

```json
{
  "success": true,
  "features": [
    {
      "id": "uuid",
      "feature_name": "settings.database",
      "display_name": "Database Settings",
      "admin_only": true,
      "description": "Configure database connections and data sources"
    }
  ]
}
```

### GET `/api/admin/feature-access/{feature_name}`

Get specific feature access setting.

**Authentication:** Admin only
**Validation:** Feature name must match whitelist
**Note:** Rate limiting is handled at the application level via middleware

**Example:**

```bash
GET /api/admin/feature-access/settings.database
```

### PUT `/api/admin/feature-access/{feature_name}`

Update feature access setting.

**Authentication:** Admin only
**CSRF Protection:** Required
**Validation:** Feature name must match whitelist
**Note:** Rate limiting is handled at the application level via middleware

**Request Body:**

```json
{
  "admin_only": true
}
```

**Example:**

```bash
curl -X PUT /api/admin/feature-access/settings.database \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: <csrf-token>" \
  -H "Content-Type: application/json" \
  -d '{"admin_only": true}'
```

### POST `/api/admin/feature-access/reset`

Reset all feature access settings to defaults.

**Authentication:** Admin only
**CSRF Protection:** Required
**Note:** Rate limiting is handled at the application level via middleware

**Resets Settings Features Only:**

- Database Settings: Admin Only
- LLM Providers: Admin Only
- External Services: Admin Only
- External Tools: All Users
- Appearance: All Users
- API Tokens: All Users

**Note:** This does not reset navigation features. Navigation features default to accessible by all users and are not modified by this operation.

## Security Features

### 1. CSRF Protection

All state-changing endpoints (PUT, POST) require a CSRF token via the `X-CSRF-Token` header. This prevents cross-site request forgery attacks.

**Implementation:** Uses custom header requirement, which forces browsers to send preflight OPTIONS requests, preventing CSRF.

### 2. Input Validation

Feature names are validated against a whitelist to prevent:

- SQL injection attempts
- Arbitrary feature creation
- Directory traversal attacks

**Valid Features:**

- Settings: `settings.database`, `settings.llm_providers`, `settings.external_services`, `settings.external_tools`, `settings.appearance`, `settings.api_tokens`
- Navigation: `nav.workflow`, `nav.library`, `nav.publish`, `nav.datasources`, `nav.executions`, `nav.manage`

### 3. Rate Limiting

Rate limiting is handled at the application level via the SlowAPI middleware configured in `backend/app.py`. The app-wide rate limiter protects all admin endpoints from abuse.

### 4. Audit Logging

All permission changes are logged with:

- Admin user email
- Feature name
- Old and new values
- Timestamp

**Log Format:**

```
[AUDIT] Feature access changed by admin@example.com: settings.database admin_only=False -> True
```

## Caching Strategy

### TTL-Based Cache

The RBAC system uses a Time-To-Live (TTL) based cache to balance performance and consistency.

**How It Works:**

1. Feature access settings are cached in-memory with a timestamp
2. On each read, the cache entry age is checked
3. If age > TTL (default: 5 minutes), the entry is removed and database is re-queried
4. Each worker process maintains its own cache

**Configuration:**

```bash
# .env file
FEATURE_ACCESS_CACHE_TTL_SECONDS=300  # 5 minutes (default)
```

**Cache Consistency Across Workers:**

In multi-worker deployments (e.g., Gunicorn with multiple workers), each worker maintains its own cache. This means:

- ✅ **Maximum staleness:** Permission changes propagate to all workers within the TTL duration
- ✅ **No shared state required:** Works without Redis or external cache
- ✅ **Automatic expiration:** Stale data is automatically refreshed
- ⚠️ **Eventual consistency:** Different workers may have different cached values for up to TTL duration

**Trade-offs:**

| TTL Value | Performance | Consistency | Use Case |
|-----------|-------------|-------------|----------|
| 30s | Good | Excellent | Development, frequent permission changes |
| 300s (5m) | Excellent | Good | Production (default), balanced |
| 1800s (30m) | Excellent | Fair | Permissions rarely change, high traffic |

**Manual Cache Invalidation:**

When an admin updates permissions via the API, `clear_feature_access_cache()` is called to immediately clear the cache on that worker. Other workers will pick up the change within the TTL window.

**Future Improvements:**

For stricter consistency requirements, consider:

- Redis-based shared cache
- Database triggers to update cache version
- Pub/Sub messaging for cache invalidation across workers

## Decorator Functions

The `backend/api/auth/rbac_middleware.py` module provides decorator functions for RBAC enforcement.

### Available Decorators

#### `@admin_required`

Enforces admin-only access to route handlers.

**Status:** Defined but currently unused
**Reason:** The codebase uses FastAPI's dependency injection pattern (`Depends(require_admin)`) instead

**Usage Example:**

```python
@router.get("/admin-endpoint")
@admin_required
async def admin_only_route(current_user: Dict = Depends(get_current_user)):
    return {"message": "Admin access granted"}
```

#### `@feature_access_required(feature)`

Decorator factory for feature-level access control.

**Status:** Defined but currently unused
**Reason:** The codebase uses FastAPI's dependency injection pattern (`Depends(require_feature_access("feature"))`) instead

**Usage Example:**

```python
@router.get("/settings/database")
@feature_access_required("settings.database")
async def database_settings(current_user: Dict = Depends(get_current_user)):
    return {"message": "Database settings access granted"}
```

### Why Dependency Injection is Preferred

The codebase uses `Depends()` instead of decorators because:

1. **Better IDE Support:** Type hints work better with dependencies
2. **Cleaner Signatures:** Clear parameter listing in function signature
3. **FastAPI Standard:** Follows FastAPI's recommended patterns
4. **Testability:** Easier to mock and test
5. **Composability:** Can combine multiple dependencies easily

### Decorator Function Maintenance

The decorator functions are kept in the codebase for:

- **Documentation:** Show alternative implementation patterns
- **Future Use:** Available if needed for specific use cases
- **Backwards Compatibility:** In case existing code uses them

**Recommendation:** If you need RBAC enforcement, use the dependency injection pattern:

```python
from backend.api.auth.dependencies import require_admin, require_feature_access

@router.get("/admin-only")
def admin_endpoint(current_user: Dict[str, Any] = Depends(require_admin)):
    return {"message": "Admin only"}

@router.get("/feature-protected")
def feature_endpoint(
    current_user: Dict[str, Any] = Depends(require_feature_access("settings.database"))
):
    return {"message": "Feature protected"}
```

## Environment Variables

```bash
# Admin Users (comma-separated email addresses)
ADMIN_USERS=admin@example.com,admin2@example.com

# Admin Group (for OAuth/JWT group-based admin detection)
ADMIN_GROUP=AdminGroup

# Feature Access Cache TTL (seconds)
FEATURE_ACCESS_CACHE_TTL_SECONDS=300
```

## Frontend Integration

### Feature Access Context

The `FeatureAccessContext` provides global state for feature access:

```typescript
import { useFeatureAccess } from '@/contexts/FeatureAccessContext';

function MyComponent() {
  const { canAccessFeature, isFeatureAdminOnly, loading, error } = useFeatureAccess();

  if (!canAccessFeature('settings.database')) {
    return null; // Hide component
  }

  return <div>Database Settings</div>;
}
```

### Error Handling Strategy

**Fail-Closed:** If feature access permissions fail to load, the frontend clears all permissions and denies access. This prevents unauthorized access if the API is unavailable.

**User Experience:**

- Loading state: Shows loading indicator while fetching permissions
- Error state: Shows error message and prompts user to refresh
- Admins: Always have access regardless of feature settings

## Testing

**Status:** Test coverage needs to be implemented.

**Required Tests:**

1. **Backend Tests** (`backend/tests/test_rbac.py`)
   - Admin detection logic
   - Feature access checking
   - Cache behavior (TTL expiration, manual clearing)
   - Input validation

2. **API Tests** (`backend/tests/api/test_admin_routes.py`)
   - CRUD operations
   - CSRF protection enforcement
   - Rate limiting
   - Admin-only access enforcement
   - Input validation edge cases

3. **Frontend Tests** (`frontend/src/contexts/__tests__/FeatureAccessContext.test.tsx`)
   - Context provider behavior
   - Error handling (fail-closed)
   - Admin bypass logic

## Database Migration Rollback

If you need to rollback the RBAC feature access migration:

### Manual Rollback SQL

```sql
-- Remove the feature_access table
DROP TABLE IF EXISTS feature_access CASCADE;

-- Remove related indexes (if they weren't dropped with CASCADE)
DROP INDEX IF EXISTS idx_feature_access_name;
DROP INDEX IF EXISTS idx_feature_access_admin_only;
```

### Post-Rollback Steps

1. Remove or comment out the migration from `backend/services/database/migrations/registry.py`
2. Restart the application to prevent re-creation of the table
3. If using version control, revert the RBAC-related commits

### Important Notes

- Migrations run automatically on startup before full app initialization
- Always backup your database before performing rollbacks
- The migration uses idempotent checks, so re-running is safe
- For production rollbacks, test in staging first

## Troubleshooting

### Issue: Permission changes not taking effect

**Cause:** Cache TTL hasn't expired yet on all workers

**Solution:**

1. Wait for TTL duration (default: 5 minutes)
2. Restart application to clear all caches
3. Reduce `FEATURE_ACCESS_CACHE_TTL_SECONDS` for faster updates

### Issue: "Invalid feature name" error

**Cause:** Feature name not in whitelist

**Solution:**

1. Check `VALID_FEATURES` in `backend/api/admin/routes.py`
2. Add feature to whitelist if legitimate
3. Verify spelling matches database entries

### Issue: CSRF validation failed

**Cause:** Missing X-CSRF-Token header

**Solution:**

1. Ensure frontend includes CSRF token in requests
2. Check `getCsrfToken()` function in frontend
3. Verify token is set in cookie/localStorage

## Best Practices

1. **Default to Admin-Only:** When adding new sensitive features, default to `admin_only=true`
2. **Test Permission Changes:** Always test in non-production environment first
3. **Monitor Audit Logs:** Regularly review `[AUDIT]` logs for unexpected permission changes
4. **Use Environment Variables:** Never hardcode admin users in code
5. **Rate Limit Awareness:** Be aware of rate limits when scripting admin operations

## References

- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [CSRF Protection Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [RBAC Design Patterns](https://en.wikipedia.org/wiki/Role-based_access_control)
