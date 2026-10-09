# API Authentication

This document describes which API endpoints can be accessed with each authentication method.

## Authentication Methods

The API accepts `Authorization: Bearer <token>` with 4 token types:

| Token Type | Prefix | Example | Use Case |
|------------|--------|---------|----------|
| **Workflow Token** | `wf_` | `wf_abc123...` | Per-workflow HTTP triggers |
| **Personal Access Token** | `na_` | `na_abc123...` | API automation, CI/CD |
| **Backend JWT** | *(none)* | HS256, `iss=agenticstudio` | Frontend sessions, MCP |
| **Azure AD JWT** | *(none)* | RS256 via JWKS | OAuth2 proxy flow |

## Endpoints by Auth Requirement

### Public (No Auth)

- `GET /` — API info
- `GET /health`, `/health/liveness`, `/health/readiness` — Health probes
- `GET /api/graph/health`

### HTTP Execution API — Conditional Auth

These accept all 3 token types (`wf_`, `na_`, JWT), but auth is only required if the published workflow has `require_authentication=True`. Public workflows need no token at all.

| Endpoint | Auth |
|----------|------|
| `POST /api/http-execution/trigger/{id}` | Conditional |
| `POST /api/http-execution/trigger-form/{id}` | Conditional |
| `POST /api/http-execution/trigger-sse/{id}` | Conditional |
| `POST /api/http-execution/resume/{name}` | Conditional |
| `GET /api/http-execution/execution/{id}` | Requires PAT |
| `GET /api/http-execution/workflows` | Optional PAT |

### HTTP Execution API — JWT Required

| Endpoint | Auth |
|----------|------|
| `GET /api/http-execution/latest-execution/{name}` | `require_active_user` (JWT/OAuth) |
| `GET /api/http-execution/info/{name}` | `require_active_user` (JWT/OAuth) |

### All Other API Routes — JWT/OAuth Required

These require a full user session (OAuth2 proxy headers or JWT). Workflow tokens (`wf_`) and PATs (`na_`) will not work.

| Router Prefix | Purpose |
|---------------|---------|
| `/api/graph` | Workflow CRUD, execution |
| `/api/datasources` | Data source management |
| `/api/files` | File uploads |
| `/api/email` | Email config |
| `/api/checkpoints` | Execution checkpoints |
| `/api/library` | Workflow library |
| `/api/monitoring` | System monitoring |
| `/api/memory` | Conversation memory |
| `/api/trace` | LangSmith tracing |
| `/api/model-deployments` | LLM model config |
| `/api/user/settings` | User preferences |
| `/api/execution-history` | Execution logs |
| `/api/wiki` | Wiki/docs |

### Admin-Only Endpoints

| Router Prefix | Auth |
|---------------|------|
| `/api/admin/*` | `require_admin` (JWT + admin role) |
| Feature-gated settings | `require_feature_access("settings.xxx")` |

## Token Scope Summary

- **`wf_` tokens** — Only work on HTTP execution trigger endpoints for the specific workflow they belong to.
- **`na_` tokens** — Work on HTTP execution endpoints (triggers, polling, listing), scoped to specific workflows.
- **JWT (backend-signed or Azure AD)** — Work everywhere; required for all management and UI-facing endpoints.
- **OAuth2 proxy headers** — Primary auth for browser sessions; equivalent to JWT for route access.

## Token Storage and Validation

| Token Type | Storage | Validation |
|------------|---------|------------|
| Personal Access Token (`na_`) | Bcrypt hash in `user_api_tokens` table | Hash comparison + scope check |
| Workflow Trigger Token (`wf_`) | Plain text in `workflows.http_trigger_token` | HMAC constant-time compare |
| Backend JWT | Not stored | HS256 signature verification |
| Azure AD JWT | Not stored | RS256 JWKS verification |

## Key Implementation Files

| Component | File |
|-----------|------|
| Main auth dependencies | `backend/api/auth/dependencies.py` |
| Token extraction | `backend/services/auth/token_extractor.py` |
| PAT service | `backend/services/auth/user_api_token_service.py` |
| HTTP execution auth | `backend/api/http_execution/services/authentication.py` |
| RBAC utilities | `backend/services/auth/rbac.py` |
| OAuth2 proxy provider | `backend/services/auth/providers/oauth2_proxy.py` |
| JWT utilities | `backend/services/auth/jwt_utils.py` |
