# OAuth2-Proxy Azure Deployment Guide

## Overview

This guide explains how to deploy and configure oauth2-proxy with Azure AD (Microsoft Entra ID) authentication for the
Agentic Studio application on Azure Web Apps.

## Architecture

```
Internet → Azure Web App (Port 80)
    ├─ nginx (main container) - Reverse proxy
    │   └─ Routes to oauth2-proxy for auth checks
    ├─ oauth2-proxy (sidecar) - Authentication layer
    │   └─ Validates Azure AD tokens
    ├─ backend (sidecar) - FastAPI application
    └─ frontend (sidecar) - Next.js application
```

## Problem: Missing Access Token

### Symptom

Backend logs show:

```
Auth debug - mode=oauth_proxy, authorization_header=missing, proxy_token_present=False, cookies=True
```

### Root Cause

OAuth2-proxy **does not** forward the Azure AD access token to the backend by default. It only:

1. Validates the user's session cookie
2. Returns 200/401 to nginx based on session validity

### Solution

Configure oauth2-proxy with specific flags to pass the access token.

## Prerequisites

### 1. Azure AD App Registration

Create an App Registration in Azure Portal:

1. Go to **Azure Active Directory** → **App Registrations** → **New Registration**
2. Set the redirect URI: `https://yourdomain.azurewebsites.net/oauth2/callback`
3. Under **Certificates & secrets**, create a new client secret
4. Under **API permissions**, add:
    - `openid` (required)
    - `profile` (required)
    - `email` (required)
    - `User.Read` (optional, for user info)
5. Note down:
    - **Application (client) ID**
    - **Directory (tenant) ID**
    - **Client secret value**

### 2. Azure Container Registry

Push the oauth2-proxy image to your Azure Container Registry:

```bash
# Pull official image
docker pull quay.io/oauth2-proxy/oauth2-proxy:latest

# Tag for your registry
docker tag quay.io/oauth2-proxy/oauth2-proxy:latest \
  exposeaicrdevaue02.azurecr.io/oauth2-proxy:latest

# Push to registry
az acr login --name exposeaicrdevaue02
docker push exposeaicrdevaue02.azurecr.io/oauth2-proxy:latest
```

## Configuration

### Environment Variables for oauth2-proxy Container

Set these in your Azure Web App configuration:

```bash
# Required OAuth2-Proxy Settings
OAUTH2_PROXY_PROVIDER=oidc
OAUTH2_PROXY_CLIENT_ID=<your-azure-client-id>
OAUTH2_PROXY_CLIENT_SECRET=<your-azure-client-secret>
OAUTH2_PROXY_OIDC_ISSUER_URL=https://login.microsoftonline.com/<tenant-id>/v2.0
OAUTH2_PROXY_REDIRECT_URL=https://yourdomain.azurewebsites.net/oauth2/callback

# Cookie Configuration
OAUTH2_PROXY_COOKIE_SECRET=<32-byte-random-string>  # Generate with: openssl rand -base64 32
OAUTH2_PROXY_COOKIE_SECURE=true
OAUTH2_PROXY_COOKIE_HTTPONLY=true
OAUTH2_PROXY_COOKIE_SAMESITE=lax
OAUTH2_PROXY_COOKIE_EXPIRE=168h  # 7 days
OAUTH2_PROXY_COOKIE_REFRESH=1h

# CRITICAL: Token Forwarding (this is what fixes the issue!)
OAUTH2_PROXY_SET_XAUTHREQUEST=true
OAUTH2_PROXY_PASS_ACCESS_TOKEN=true
OAUTH2_PROXY_PASS_AUTHORIZATION_HEADER=true
OAUTH2_PROXY_PASS_USER_HEADERS=true

# Scopes
OAUTH2_PROXY_SCOPE=openid profile email

# Allowed Domains
OAUTH2_PROXY_EMAIL_DOMAINS=*  # Or restrict to your domain: yourcompany.com

# Reverse Proxy Settings
OAUTH2_PROXY_REVERSE_PROXY=true
OAUTH2_PROXY_REAL_CLIENT_IP_HEADER=X-Real-IP

# Logging (for debugging)
OAUTH2_PROXY_LOG_LEVEL=info  # Use 'debug' for troubleshooting

# HTTP Address
OAUTH2_PROXY_HTTP_ADDRESS=0.0.0.0:4180

# Upstream (required but unused in auth_request mode)
OAUTH2_PROXY_UPSTREAMS=http://127.0.0.1:8000
```

### Backend Environment Variables

Set these for your backend container:

```bash
# Authentication Mode
AUTH_MODE=oauth_proxy

# Azure AD Configuration (for JWT validation)
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-azure-client-id>

# Optional (recommended): shared secret for trusted proxy identity headers.
# - If NOT set: header-based auth works exactly as before (backward-compatible).
#   This is safe to deploy without any other changes.
# - If SET: the backend only trusts X-Auth-Request-Email/Groups/User/Username
#   when the request also carries the matching secret in the header below.
#   Requests without it fall back to JWT token validation instead of being
#   trusted on headers alone.
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
AUTH_PROXY_SHARED_SECRET=<high-entropy-random-secret>
AUTH_PROXY_SHARED_SECRET_HEADER=X-Auth-Proxy-Secret

# Optional: Allow disabling JWT validation for debugging
# OAUTH_PROXY_DISABLE_JWT_VALIDATION=false  # Keep false in production!

# Enable debug endpoint (staging only!)
# ENABLE_AUTH_DEBUG=true  # Only for troubleshooting, disable in production
```

### Nginx Trusted Header Forwarding (Standalone nginx sidecar deployments)

Configure nginx to forward the same secret on all authenticated API routes:

```nginx
location /api/ {
    # ... existing auth_request config ...
    proxy_set_header X-Auth-Proxy-Secret "<same-secret-as-AUTH_PROXY_SHARED_SECRET>";
}
```

Without this, once `AUTH_PROXY_SHARED_SECRET` is configured on the backend, header-based
identity (`X-Auth-Request-Email`, `X-Auth-Request-Groups`) from requests lacking the
matching secret header is rejected and falls back to JWT token validation.

### Kubernetes (Ingress + oauth2-proxy) Deployment — UAT/DEV Architecture

UAT and DEV do **not** use the nginx sidecar model above. Traffic flows:

```
Client → Ingress (nginx ingress controller) → oauth2-proxy pod (4180) → backend-svc (8000)
```

oauth2-proxy is what forwards `X-Auth-Request-Email` / `X-Auth-Request-Groups` to the
backend, so the shared secret must be **injected by oauth2-proxy itself**, not by the
ingress. oauth2-proxy supports this via the `injectRequestHeaders` alpha config
(oauth2-proxy >= 7.4). Ready-to-apply artifacts are provided in `backend/k8s/`:

- `backend/k8s/oauth2-proxy-alpha-config.yaml` — oauth2-proxy alpha config that injects
  `X-Auth-Proxy-Secret` plus the identity headers. See the file header for the ConfigMap
  + volume mount + `--alpha-config` flag wiring.
- `backend/k8s/networkpolicy-backend.yaml` — restricts `backend-svc:8000` ingress to only
  the `oauth-proxy` and `frontend-app` pods (defense-in-depth, also covers the WebSocket
  auth path which has no shared-secret check).

Then set the matching env var on the backend deployment/ConfigMap:

```bash
kubectl set env deployment/backend-app -n tadastudio-uat \
  AUTH_PROXY_SHARED_SECRET=<same-secret-as-oauth2-proxy> \
  AUTH_PROXY_SHARED_SECRET_HEADER=X-Auth-Proxy-Secret
```

**Rollout order matters:** deploy/verify the oauth2-proxy header injection first, confirm
`X-Auth-Proxy-Secret` is reaching the backend (e.g. via `ENABLE_AUTH_DEBUG` or logs), and
only then set `AUTH_PROXY_SHARED_SECRET` on the backend. If the backend enforces the
secret before oauth2-proxy is injecting it, all header-based auth will fall back to JWT
token validation — which can fail if `OAUTH_PROXY_DISABLE_JWT_VALIDATION`/JWKS aren't
correctly configured, effectively locking out all users until fixed.

**Defense-in-depth:** independent of the shared secret, apply
`backend/k8s/networkpolicy-backend.yaml` to restrict which pods can reach
`backend-svc:8000` directly — this also protects the WebSocket auth path
(`/api/collab`, `/api/notifications/ws`), which does not use the shared-secret
header check.


## Deployment Steps

### 1. Update Docker Compose for Azure

Your Azure Web App should use a Docker Compose configuration with 4 containers:

```yaml
version: '3.8'

services:
  nginx:
    image: exposeaicrdevaue02.azurecr.io/nginx:latest
    ports:
      - "80:80"
    depends_on:
      - oauth2-proxy
      - backend
      - frontend

  oauth2-proxy:
    image: exposeaicrdevaue02.azurecr.io/oauth2-proxy:latest
    command:
      - --config=/oauth2-proxy.cfg
    environment:
      - OAUTH2_PROXY_CLIENT_ID=${AZURE_CLIENT_ID}
      - OAUTH2_PROXY_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - OAUTH2_PROXY_OIDC_ISSUER_URL=https://login.microsoftonline.com/${AZURE_TENANT_ID}/v2.0
      - OAUTH2_PROXY_REDIRECT_URL=${OAUTH2_REDIRECT_URL}
      - OAUTH2_PROXY_COOKIE_SECRET=${OAUTH2_COOKIE_SECRET}
      - OAUTH2_PROXY_SET_XAUTHREQUEST=true
      - OAUTH2_PROXY_PASS_ACCESS_TOKEN=true
      - OAUTH2_PROXY_PASS_AUTHORIZATION_HEADER=true
      - OAUTH2_PROXY_PASS_USER_HEADERS=true
      - OAUTH2_PROXY_SCOPE=openid profile email
      - OAUTH2_PROXY_EMAIL_DOMAINS=*
      - OAUTH2_PROXY_HTTP_ADDRESS=0.0.0.0:4180
      - OAUTH2_PROXY_UPSTREAMS=http://127.0.0.1:8000
      - OAUTH2_PROXY_REVERSE_PROXY=true
      - OAUTH2_PROXY_COOKIE_SECURE=true
      - OAUTH2_PROXY_LOG_LEVEL=info

  backend:
    image: exposeaicrdevaue02.azurecr.io/agentic-studio:latest
    environment:
      - AUTH_MODE=oauth_proxy
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      # ... other backend env vars

  frontend:
    image: exposeaicrdevaue02.azurecr.io/agentic-studio-fe:latest
    environment:
      - RUNTIME_AUTH_MODE=oauth_proxy
      # ... other frontend env vars
```

### 2. Deploy to Azure

```bash
# Set environment variables in Azure Portal or via CLI
az webapp config appsettings set \
  --resource-group <your-resource-group> \
  --name <your-webapp-name> \
  --settings \
    AZURE_CLIENT_ID="<client-id>" \
    AZURE_CLIENT_SECRET="<client-secret>" \
    AZURE_TENANT_ID="<tenant-id>" \
    OAUTH2_REDIRECT_URL="https://<your-domain>/oauth2/callback" \
    OAUTH2_COOKIE_SECRET="<random-32-byte-string>"

# Deploy via Azure Portal or Azure DevOps
```

### 3. Verify Deployment

After deployment, test the authentication flow:

#### A. Check OAuth2-Proxy Health

```bash
curl https://yourdomain.azurewebsites.net/oauth2/ping
# Should return: "OK"
```

#### B. Test Login Flow

1. Navigate to `https://yourdomain.azurewebsites.net`
2. Should redirect to Microsoft login
3. After login, should redirect back to your app

#### C. Enable Debug Endpoint (Staging Only!)

> ⚠️ **Security warning:** The debug endpoint exposes authentication headers including access tokens. Only enable it temporarily on non-production environments and disable it immediately after use.

```bash
# Set this environment variable temporarily
ENABLE_AUTH_DEBUG=true

# Then call the debug endpoint
curl https://yourdomain.azurewebsites.net/api/auth/debug/headers \
  -H "Cookie: <your-session-cookie>"

# Expected output:
{
  "auth_mode": "oauth_proxy",
  "oauth_proxy_headers": {
    "x-auth-request-user": "user@domain.com",
    "x-auth-request-email": "user@domain.com",
    "x-auth-request-access-token": "eyJ0eXAi..."
  },
  "has_authorization_header": true,
  "has_proxy_token": true,
  "has_proxy_user": true,
  "has_proxy_email": true
}
```

#### D. Check Backend Logs

Look for the enhanced debug output:

```
Auth debug - mode=oauth_proxy, authorization_header=present, proxy_token_present=True, cookies=True, all_auth_headers={...}
```

## Troubleshooting

### Issue 1: Still Getting `proxy_token_present=False`

**Cause**: OAuth2-proxy not configured with token forwarding flags

**Solution**: Ensure these flags are set:

```bash
OAUTH2_PROXY_SET_XAUTHREQUEST=true
OAUTH2_PROXY_PASS_ACCESS_TOKEN=true
```

### Issue 2: `authorization_header=missing` but `proxy_token_present=True`

**Cause**: nginx not mapping the token to Authorization header

**Solution**: Check `nginx.conf` (project root) has the correct map directive:

```nginx
map $upstream_http_x_auth_request_access_token $authz_header {
    default "";
    "~.+"   "Bearer $upstream_http_x_auth_request_access_token";
}
```

### Issue 3: JWT Validation Errors

**Cause**: Azure AD token audience/issuer mismatch

**Solution**:

1. Check `AZURE_TENANT_ID` matches your Azure AD tenant
2. Verify `AZURE_CLIENT_ID` matches the App Registration
3. Temporarily disable validation for debugging:

   ```bash
   OAUTH2_PROXY_DISABLE_JWT_VALIDATION=true
   ```

4. Check backend logs for specific JWT error messages

### Issue 4: Infinite Redirect Loop

**Cause**: Cookie not being set (usually HTTPS/domain mismatch)

**Solution**:

1. Ensure `OAUTH2_PROXY_COOKIE_SECURE=true` only on HTTPS
2. Check redirect URL matches exactly (including trailing slashes)
3. Verify cookie domain settings

### Issue 5: 401 Unauthorized After Login

**Cause**: Session cookie not being passed to auth subrequest

**Solution**: Ensure nginx `/oauth2/auth` location passes cookies:

```nginx
location = /oauth2/auth {
    proxy_set_header Cookie $http_cookie;
    # ... other settings
}
```

## Security Considerations

### Production Checklist

- [ ] Set `OAUTH2_PROXY_COOKIE_SECRET` to a cryptographically random 32-byte value
- [ ] Restrict `OAUTH2_PROXY_EMAIL_DOMAINS` to your organization
- [ ] Keep `OAUTH2_PROXY_DISABLE_JWT_VALIDATION=false` (never disable in production)
- [ ] Use `OAUTH2_PROXY_COOKIE_SECURE=true` (HTTPS only)
- [ ] Set `ENABLE_AUTH_DEBUG=false` (disable debug endpoint)
- [ ] Rotate Azure AD client secrets periodically
- [ ] Monitor authentication failures in Application Insights
- [ ] Set appropriate cookie expiry (`OAUTH2_PROXY_COOKIE_EXPIRE`)
- [ ] Enable cookie refresh (`OAUTH2_PROXY_COOKIE_REFRESH`)
- [ ] Review skip_auth_routes to ensure no sensitive paths are bypassed

### Additional Hardening

1. **Rate Limiting**: Already configured in nginx (`limit_req_zone`)
2. **CORS**: Configure if frontend is on different domain
3. **Azure Front Door**: Consider adding for DDoS protection
4. **Application Insights**: Monitor authentication metrics
5. **Conditional Access**: Configure in Azure AD for MFA/location policies

## Reference Links

- [oauth2-proxy Documentation](https://oauth2-proxy.github.io/oauth2-proxy/)
- [Azure AD OpenID Connect](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-protocols-oidc)
- [nginx auth_request Module](http://nginx.org/en/docs/http/ngx_http_auth_request_module.html)

## Quick Reference: Key Environment Variables

| Variable                         | Container    | Purpose                     | Example             |
|----------------------------------|--------------|-----------------------------|---------------------|
| `OAUTH2_PROXY_SET_XAUTHREQUEST`  | oauth2-proxy | **Enable token forwarding** | `true`              |
| `OAUTH2_PROXY_PASS_ACCESS_TOKEN` | oauth2-proxy | **Pass access token**       | `true`              |
| `AUTH_MODE`                      | backend      | Enable OAuth proxy mode     | `oauth_proxy`       |
| `AZURE_TENANT_ID`                | backend      | JWT validation              | `00000000-0000-...` |
| `ENABLE_AUTH_DEBUG`              | backend      | Debug endpoint              | `false` (prod)      |

## Support

For issues related to:

- **OAuth2-Proxy**: Check logs with `OAUTH2_PROXY_LOG_LEVEL=debug`
- **Backend Auth**: Check logs and use `/api/auth/debug/headers` (staging only)
- **nginx**: Check `/var/log/nginx/error.log` and `/var/log/nginx/access.log`
