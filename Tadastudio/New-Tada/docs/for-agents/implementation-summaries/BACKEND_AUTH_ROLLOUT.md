# Backend Authentication Rollout Plan

## Current State

- Microsoft Entra ID provides SSO via the frontend MSAL integration.
- Backend token verification only occurs when individual routes call `get_current_user`; most routes skip this
  dependency so requests succeed without a bearer token.
- User persistence is implemented in `backend/auth.py::_sync_user`, but the function only runs during token
  verification, so user rows are never created unless a protected route is hit.
- Workflow access control is partially modeled in the database (`users`, `workflows`, `workflow_memberships`) but not
  consistently enforced at the API layer.

## Target State

- Every state-changing backend request requires a valid bearer token; read-only endpoints are audited to determine
  whether they should be public.
- User synchronization happens automatically during authentication, ensuring the `users` table reflects active Entra
  accounts.
- Workflow CRUD operations respect membership rules defined in the data model.
- Frontend API helpers automatically attach tokens so individual components stay simple.

## Implementation Snapshot

- Backend authentication now supports two modes behind the `AUTH_MODE` environment variable (`basic` or `oauth_proxy`).
  The default remains `basic` for local development.
- When `AUTH_MODE=oauth_proxy`, FastAPI trusts requests coming through nginx/oauth2-proxy, validates Azure-issued JWT
  access tokens via JWKS, and persists Entra principals in the `users` table on every request. Legacy password endpoints
  are automatically disabled.
- A feature flag `OAUTH_PROXY_DISABLE_JWT_VALIDATION` exists for break-glass troubleshooting, but production
  environments should keep signature validation enabled.
- The Next.js runtime configuration exposes `authMode` via `/api/config`, and the React `AuthContext` now adapts
  automatically: in proxy mode it relies on the oauth2-proxy session (no stored tokens), while `basic` mode keeps the
  existing credential flow for contributors.
- Frontend runtime builds should set `RUNTIME_AUTH_MODE=oauth_proxy` alongside the existing `RUNTIME_API_URL` when
  deploying behind the proxy, and surface `NEXT_PUBLIC_AUTH_MODE=oauth_proxy` (leaving legacy MSAL helpers gated off
  unless the build explicitly opts into `basic`).

## Implementation Phases

1. **Audit & Classification**
    - Categorise all FastAPI routes (public vs. protected).
    - Identify endpoints that need dedicated scopes or elevated roles (e.g., admin-only configuration APIs).
2. **Incremental Protection**
    - Introduce a shared dependency wrapper (e.g., `require_user`) that returns both claims and the hydrated `User` ORM
      object.
    - Apply the dependency to high-impact routes first (workflow CRUD, configuration, execution) and add feature flags
      for staged rollout.
    - Capture unauthorized access attempts with structured logging for monitoring.
3. **Frontend Alignment**
    - Centralise fetch logic so all `api.*` methods automatically call `acquireToken` and attach the bearer token.
    - Add a post-login sync (`/api/auth/me`) that hydrates the UI with backend-backed user metadata and kicks off
      membership provisioning.
    - Establish error handling for 401/403 responses (auto-reauth, friendly messaging).
4. **Testing & Observability**
    - Expand unit/integration tests to cover authenticated access patterns and membership checks.
    - Add synthetic monitoring or smoke tests that validate token handshake in staging.
    - Instrument metrics/dashboards for authentication failures, latency, and sync errors.
5. **Hardening & Cleanup**
    - Remove legacy `username` query parameters that bypass auth.
    - Backfill membership data for existing workflows and migrate any anonymous records.
    - Document operational playbooks (token expiry settings, rotating MSAL config, incident response).

## Key Considerations

- **Token Verification Strategy**: Decide between per-route dependencies vs. a global middleware. Dependencies keep
  FastAPI docs accurate and allow fine-grained control.
- **Background Jobs & WebSockets**: Ensure non-HTTP entry points (e.g., background tasks, WebSocket connections)
  propagate and validate user context.
- **Multi-Tenancy Boundaries**: Confirm whether graph names must be unique globally or per tenant; adjust uniqueness
  constraints accordingly.
- **Local Development**: Provide a development IdP or token stub to avoid blocking workflows for contributors without
  Entra access.
- **Rollout Safety**: Ship behind a feature flag to allow quick disablement if unexpected authorization failures occur
  in production.

## Open Questions

- Do any third-party integrations require anonymous/public access that must remain unauthenticated?
- What is the long-term plan for role-based access beyond the current OWNER/EDITOR/VIEWER enum?
- Should API tokens or service principals be supported alongside interactive Entra login?

Keeping this plan separate lets us iterate on the implementation while tracking long-term hardening steps.
