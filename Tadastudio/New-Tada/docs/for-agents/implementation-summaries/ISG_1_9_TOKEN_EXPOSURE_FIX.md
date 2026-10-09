# ISG Finding 1.9 – Access Token Exposed to Client-Side JavaScript via Response Headers

## Status: Implemented

## Finding Summary

ISG identified that authenticated API responses from Tada Studio contained the
`X-Auth-Request-Access-Token` header carrying a live Microsoft Entra ID access
token. Because these are same-origin responses, any JavaScript running inside
the application origin (including XSS payloads) could read the token via
`response.headers.get('X-Auth-Request-Access-Token')`.

## Root Cause

oauth2-proxy is deployed in **reverse proxy mode** with these flags:

```
OAUTH2_PROXY_SET_XAUTHREQUEST=true
OAUTH2_PROXY_PASS_ACCESS_TOKEN=true
```

In reverse proxy mode, `set_xauthrequest` causes oauth2-proxy to add
`X-Auth-Request-*` headers to **both** the upstream request (to the backend)
**and** the downstream response (to the browser). The `pass_access_token` flag
additionally includes the raw Entra access token in
`X-Auth-Request-Access-Token`.

Neither the K8s Ingress nor the backend stripped these from outgoing responses.

## Architecture (Production)

```
Browser
  → K8s nginx Ingress Controller (TLS termination)
    → oauth-proxy-svc:4180 (reverse proxy mode)
      → backend-svc:80 (FastAPI) for /api/*
      → frontend-svc:80 (Next.js) for /*

Exception (PAT auth, bypasses oauth2-proxy):
  → /api/http-execution/trigger* → backend-svc directly
```

## Remediation (4 Layers – Defense in Depth)

### Layer 1: K8s Ingress – `proxy_hide_header` (PRIMARY)

Added `nginx.ingress.kubernetes.io/configuration-snippet` annotation to the
Ingress manifest (`k8s/ingress-uat.yaml`) that strips all sensitive proxy
headers from responses at the Ingress controller level:

```yaml
nginx.ingress.kubernetes.io/configuration-snippet: |
  proxy_hide_header X-Auth-Request-Access-Token;
  proxy_hide_header X-Auth-Request-Email;
  proxy_hide_header X-Auth-Request-User;
  proxy_hide_header X-Auth-Request-Username;
  proxy_hide_header X-Auth-Request-Groups;
  proxy_hide_header X-Forwarded-Access-Token;
```

### Layer 2: oauth2-proxy – Disable `pass_access_token`

Changed `pass_access_token` from `true` to `false` in `oauth2-proxy.cfg`.
The backend still receives the token via the `Authorization` header
(`pass_authorization_header=true` remains), which is the preferred extraction
path in `token_extractor.py`.

### Layer 3: Backend Middleware – `SensitiveHeaderStripMiddleware`

New middleware at `backend/api/security/auth_header_guard.py` strips any
`X-Auth-Request-*` headers from **all** outgoing responses as a safety net.
Registered in `backend/app.py`.

### Layer 4: Backend – nginx-check endpoint cleanup

Removed `X-Auth-Request-Access-Token`, `X-Forwarded-Access-Token`, and
`Authorization` from the headers forwarded by the `/api/auth/nginx-check`
endpoint (`backend/api/auth/routes.py`). This endpoint only needs to return
`User`, `Email`, and `Groups` for the auth subrequest.

## Files Changed

| File | Change |
|------|--------|
| `k8s/ingress-uat.yaml` | **NEW** – Ingress manifest with `proxy_hide_header` |
| `backend/api/security/auth_header_guard.py` | **NEW** – Response header stripping middleware |
| `backend/api/security/__init__.py` | Export `SensitiveHeaderStripMiddleware` |
| `backend/app.py` | Register `SensitiveHeaderStripMiddleware` |
| `backend/api/auth/routes.py` | Remove token headers from nginx-check forwarding |
| `oauth2-proxy.cfg` | `pass_access_token = false` |
| `nginx.conf` | Add `proxy_hide_header` directives (local dev) |

## Relationship to #6422

Finding 1.9 is a **separate vulnerability** from #6422 (header spoofing), but
overlaps in code surface:

- **#6422** prevents inbound header forgery (client → backend)
- **1.9** prevents outbound token leakage (backend → client)

Both touch `routes.py` (nginx-check) and infrastructure configs. Coordinate
merge order to avoid conflicts.

## Verification

### Browser DevTools

1. Login → DevTools → Network → call `/api/auth/me`
2. Response headers must NOT contain `X-Auth-Request-Access-Token`

### JavaScript Console

```javascript
fetch('/api/auth/me').then(r =>
  console.log(r.headers.get('X-Auth-Request-Access-Token'))
);
// Must print: null
```

### Burp Suite

1. Intercept authenticated request to any `/api/*` endpoint
2. Inspect response headers — no `X-Auth-Request-*` present
