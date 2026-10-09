# OAuth2-Proxy Trust Model: Why We Trust the Email Header

## The Problem We Encountered

When deploying with oauth2-proxy + Azure AD, we encountered this error:

```
Token validation error: Signature verification failed
```

### Root Cause: Token Audience Mismatch

The access token from Azure AD had:

```json
{
  "aud": "https://graph.microsoft.com",  // Token is for Graph API
  "appid": "5c307c9c-4ad6-47e1-ac27-97389e84e504"
}
```

**The token was issued for Microsoft Graph API, not for our backend application.**

This happens because oauth2-proxy requests a token for the Graph API (to get user profile info) rather than requesting a
token specifically for our backend's client ID.

## The Solution: Trust the Proxy

Instead of validating the JWT token ourselves, we **trust that oauth2-proxy already validated the user**.

### Why This is Secure

1. **OAuth2-Proxy validates the user session**
    - Checks Microsoft's authentication
    - Validates the OAuth2 flow
    - Maintains secure session cookies

2. **Nginx enforces the auth check**

   ```nginx
   location /api/ {
       auth_request /oauth2/auth;  # BLOCKS if auth fails
       error_page 401 = @oauth2_signin;

       # Only forwards requests if oauth2-proxy returns 200
       proxy_pass http://backend;
   }
   ```

3. **Headers are set by nginx, not the client**
    - Client cannot forge `X-Auth-Request-Email`
    - nginx sets these headers based on oauth2-proxy's response
    - Client headers are NOT passed through

### Trust Chain

```
User → OAuth2-Proxy (validates Microsoft auth)
           ↓ (returns 200 + headers)
       nginx (validates response, sets headers)
           ↓ (forwards only if 200)
       Backend (trusts the email header)
```

**The backend never receives a request unless oauth2-proxy approved it.**

## Implementation

### Backend Code (auth.py)

```python
if AUTH_MODE == "oauth_proxy" and request is not None:
    # Trust the email header set by oauth2-proxy/nginx
    email = request.headers.get("X-Auth-Request-Email")
    if not email:
        raise HTTPException(status_code=401, detail="Missing email from oauth2-proxy")

    # Build claims from headers
    claims = {
        "email": email,
        "auth_source": "oauth_proxy",
        "sub": email,
    }

    # Optionally extract additional info from token (without validation)
    if token:
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
        claims["name"] = unverified_claims.get("name")
        claims["given_name"] = unverified_claims.get("given_name")
        # ... etc

    return claims
```

### What We Extract Without Validation

From the Graph API token, we can still extract useful information **without cryptographic validation**:

- `name`: "Daniel Warner"
- `given_name`: "Daniel"
- `family_name`: "Warner"
- `oid`: Object ID (Azure user ID)
- `tid`: Tenant ID
- `upn`: User Principal Name

These are used for **user experience** (display name) and **database synchronization**, not for authorization decisions.

## Alternative Approach: Request Backend-Specific Token

If you **must** validate the JWT yourself, you need to configure oauth2-proxy to request a token for your backend's
client ID:

### Option 2: Backend Token Validation (More Complex)

1. **Create a separate App Registration** for the backend API
2. **Expose an API scope** in that registration
3. **Configure oauth2-proxy** to request that scope:

```bash
OAUTH2_PROXY_SCOPE="openid profile email api://your-backend-client-id/access_as_user"
```

1. **The token audience will match** your backend client ID
2. **Backend can validate** the JWT signature

**However, this is more complex and provides minimal additional security** when oauth2-proxy already validated the user.

## Security Considerations

### ✅ This Approach is Secure When

1. **nginx is the only entry point** - Backend is not directly accessible
2. **OAuth2-proxy is properly configured** - With secure cookie secrets, HTTPS, etc.
3. **Headers are not passed from client** - nginx sets headers from auth response only

### ❌ Do NOT use this approach if

1. Backend is directly accessible (bypassing nginx)
2. You don't trust the infrastructure (shared hosting, untrusted proxy)
3. You need fine-grained token scopes for different APIs

### Defense in Depth

Additional security measures in place:

1. **nginx rate limiting** - Prevents brute force attacks
2. **Cookie security** - HttpOnly, Secure, SameSite
3. **HTTPS enforcement** - All traffic encrypted
4. **Azure AD security** - MFA, Conditional Access policies
5. **Database-level checks** - User existence verification

## Comparison of Approaches

| Aspect             | Trust Email Header                | Validate JWT Token              |
|--------------------|-----------------------------------|---------------------------------|
| **Security**       | High (if nginx is the only entry) | Slightly higher                 |
| **Complexity**     | Low                               | High                            |
| **Token audience** | Any (Graph API token works)       | Must match backend              |
| **Setup**          | Simple oauth2-proxy config        | Complex Azure AD + scope config |
| **Performance**    | Fast (no crypto validation)       | Slower (RSA signature check)    |
| **Maintenance**    | Easy                              | Complex (JWKS rotation, etc.)   |

## Monitoring & Logging

With the trust model, we log:

```python
logger.debug(
    "Auth via oauth_proxy - email=%s, has_token=%s, extracted_claims=%s",
    email,
    bool(token),
    list(claims.keys())
)
```

### Red Flags to Monitor

1. **Requests without X-Auth-Request-Email** - Indicates misconfiguration
2. **Sudden changes in user emails** - Possible session hijacking
3. **High failure rate at oauth2-proxy** - Possible attack

## Conclusion

**Trusting the email header from oauth2-proxy is secure and simpler** than validating JWTs yourself, as long as:

1. OAuth2-proxy properly validates Microsoft authentication
2. nginx enforces the auth_request check
3. Backend is not directly accessible

This is the **recommended approach** for oauth2-proxy deployments, as it:

- ✅ Reduces complexity
- ✅ Avoids token audience issues
- ✅ Maintains security through the proxy layer
- ✅ Performs better (no crypto operations)
- ✅ Easier to maintain

The JWT token can still be decoded (without validation) to extract user profile information for display purposes.
