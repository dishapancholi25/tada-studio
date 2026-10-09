# Existing Implementation — Azure Blob Storage Access Control

**Scope:** Current state of the user-facing document APIs (upload, list, download, view). Azure RBAC role assignments and Managed Identity are not used anywhere in this path — access is account-key/SAS-based and enforced by the application, never by Azure.

---

## Existing Flow

### 1. Authentication to Azure Storage

`service.py:118-138` — `_get_blob_service_client()` builds a `BlobServiceClient.from_connection_string(os.getenv("AZURE_BLOB_CONNECTION_STRING"))`. This single connection string (`AccountName` + `AccountKey`) is used to authenticate every blob operation the backend performs.

This credential is delivered differently per environment:

- **Dev:** via Docker. The pipeline downloads a secure `.env` file and starts the container with `docker run --env-file`, passing the connection string in directly at container start.
- **QA, UAT, and PROD:** via Kubernetes deployment on AKS. The application is deployed with `kubectl apply -f deployment.yaml`, and the connection string is supplied through an AKS ConfigMap, populated per environment, which the application reads its configuration from. The ConfigMap stores the raw connection string (including the account key) in plain text.

### 2. Listing documents

When a user lists documents, `_build_collections_with_documents_response()` calls `resolve_document_download_url()` for every document returned. This function (`service.py`) extracts the `AccountKey` from the connection string and calls `generate_blob_sas()` to mint a read-only, single-blob SAS token (TTL from `AZURE_BLOB_SAS_TTL_MINUTES`, default 60 minutes) for each document shown — not only when a download is explicitly requested.

If `AccountName`/`AccountKey` cannot be parsed from the connection string, the function instead logs a warning and returns the plain blob URL with no SAS token attached (`service.py`).

### 3. Downloading or viewing a document

Before returning a URL for `download` or `view`, the application calls `check_collection_access()` to authorize the request against the document's `collection_id`.

If the database record for the document is missing but a matching blob still exists in storage, both endpoints instead fall back to serving the file via a generated URL **without calling `check_collection_access()` at all** — because with no database row, there is no `collection_id` to check against. This is logged as `[AUDIT] Orphan-blob ... (authorization skipped)`. This path is reached when the database and storage fall out of sync — e.g. partial or failed deletes, restores, or data migrations.

### 4. Uploading a document

`_upload_to_blob()` (`service.py:165`) handles every upload, using the same key-authenticated client as every other blob operation:

1. It first calls `_ensure_blob_container_exists()` (`service.py`), which attempts `create_container()` (`service.py`) on **every upload** and ignores the error if the container already exists. No `public_access` argument is passed, which defaults to private in the Azure SDK.
2. It then writes the file with `upload_blob(..., overwrite=True)` (`service.py`).

---

## Gaps

| Area | Current Behaviour | Impact | Where Azure Blob Access Can Improve |
|---|---|---|---|
| Authentication to Azure Storage | A single shared connection string (`AccountName` + `AccountKey`) authenticates every blob operation, including container creation on every upload. | The account key gives full control of the whole storage account, well beyond what the application needs. Azure sees every request as "the application", not a specific identity. | Adopt Azure RBAC + Managed Identity (`DefaultAzureCredential`) instead of account-key auth; this is already used elsewhere in this codebase (LLM provider, embeddings, Document Intelligence, OCR, MCP service). Grant `Storage Blob Data Contributor` scoped to the document container only (the service uploads, so Reader is not enough). Pre-create the container at provisioning time and remove the per-upload `create_container()` call, so the identity needs no container-creation rights. |
| SAS tokens on listing | Account-key-signed SAS minted for every document on every listing call, not only on download. | Every listing produces working 60-minute download URLs that can end up in browser history, proxy/gateway logs and monitoring. An account-key SAS can only be invalidated early by rotating the account key, which breaks every other use of that key. | Move to user-delegation SAS: it can be invalidated by revoking the user-delegation keys (no account-key rotation), is tied to an Entra identity for auditing, and has a maximum lifetime of 7 days. It is still not revocable per token, so also generate SAS only on explicit download to limit how many live URLs exist. |
| Orphaned-blob fallback | File served via generated URL without `check_collection_access()` when the database record is missing. | A user whose access has been revoked can still download a document if its database row is deleted while the blob remains. | Route the fallback through an access check even without a database record, or hold it until the database/storage drift is reconciled. |
| Unparseable account key | Returns a plain, unsigned blob URL. | Today this only happens if the connection string is misconfigured. **But the choice to sign is based on whether an `AccountKey` is present, so moving to Managed Identity without changing this function removes the key and every document URL becomes unsigned.** Downloads break if the container is private, and are exposed if it is public. | As part of the Managed Identity migration, change `resolve_document_download_url()` to issue user-delegation SAS (`get_user_delegation_key()`), and fail closed (return an error) instead of returning an unsigned URL. |
