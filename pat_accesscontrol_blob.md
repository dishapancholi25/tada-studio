# Access Control for Blob Storage under PAT Authentication

## 1. Authentication layer

`backend/api/auth/dependencies.py` — `_authenticate_pat()` validates a `na_`-prefixed token via `UserAPITokenService.validate_token_no_scope_check()`. On success it builds synthetic claims: `sub` (user_id), `active_scopes` (the token's granted scopes), and `auth_via_pat=True`.

## 2. Scope enforcement

`backend/services/auth/scope_enforcer.py` — `require_scope(...)` / `require_any_scope([...])` are FastAPI dependencies that only apply when `auth_via_pat=True` (session/OAuth users bypass them entirely). They check the token's `active_scopes` against the route's required scope (e.g. `document:*:read`, `workflow:*:execute`), with wildcard support (`api:*`, `resource:*:action`, etc.).

## 3. Document/blob routes

`backend/api/documents/router.py` — a dedicated `pat_router` is mounted at `/api/pat/documents`, bypassing oauth2-proxy at the Ingress level, so each route must declare its own scope dependency.

- Example: `GET /api/pat/documents/{document_id}/view` (`router.py`) requires `document:*:read` or `workflow:*:execute`, then delegates to the same `view_document` handler used by session auth.
- The `download` and `view` handlers additionally enforce **collection-level authorization** via `document_service.check_collection_access(doc_info.collection_id, user_id)` (`router.py`)Even with a valid scope, the PAT's user must own or have shared access to the document's collection, otherwise the request is rejected with 403.

## 4. Blob URL issuance

`backend/services/document_storage/service.py` — once authorized, `resolve_document_download_url()` generates a short-lived Azure Blob SAS token (`generate_blob_sas`, read-only permission, TTL from `AZURE_BLOB_SAS_TTL_MINUTES`, default 60 minutes) rather than exposing the storage account key or a permanent URL. The blob itself is never proxied through the backend for authorized flows, the client gets a presigned URL directly to Blob Storage.

## 5. Orphaned-blob fallback

When no database record exists for a `document_id`, both handlers skip `check_collection_access` because there is no collection to check against (`router.py` for download, `router.py` for view). The event is logged as `[AUDIT] Orphan-blob download/view ...` for traceability. This is the one case where only the PAT scope is enforced, not collection ownership or sharing.

## Summary of the access-control chain

**PAT scope check → collection-level ownership/sharing check → time-limited SAS URL**, with the orphaned-blob path being the exception where only the scope check applies.
