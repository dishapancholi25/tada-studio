# Proposed Solution — Azure Blob Storage Access Control (Managed Identity + RBAC)

## Objective

Move Blob access from the shared storage account key to Azure identity with RBAC, so QA/UAT/PROD don't use the account key.

**Why:** today one storage account key (inside the connection string) authenticates every blob operation in the backend. It gives full, unscoped access to the whole storage account, and in QA/UAT/PROD it is stored in plain text in an AKS ConfigMap. Access is by a shared secret rather than a named identity, so it cannot be attributed or scoped in Azure, and the download SAS URLs are signed with the same key, so they cannot be invalidated early without rotating it. Moving to a managed identity with RBAC removes the shared key, limits what the backend can do to what it needs, and makes Azure access attributable to a named, auditable backend identity.

## Proposed Solution — Flow

### 1. Pod starts and authenticates to Azure 

- The backend pod uses **AKS Workload Identity**: a federated credential binds a user-assigned **Managed Identity** to the backend's Kubernetes `ServiceAccount`, and the pod is labelled to use it.
- `_get_blob_service_client()` builds `BlobServiceClient(account_url, credential=WorkloadIdentityCredential())` when running in managed-identity mode. An explicit credential is used instead of `DefaultAzureCredential`, which tries several credential sources in turn and could silently pick up a different one; the explicit credential fails clearly if Workload Identity is not available. `azure-identity` is already a dependency and managed identity is already used elsewhere in this codebase (LLM provider, embeddings, Document Intelligence, OCR, MCP service).
- The application receives only the storage account URL (non-secret configuration). **No account key or connection string** is present in the QA/UAT/PROD deployment.
- **`_is_blob_enabled()` must be updated.** Today it returns true only when `AZURE_BLOB_CONNECTION_STRING` is set (`service.py`), and every blob path checks it first. Without this change, removing the connection string would make uploads silently write to the pod's local disk instead of Blob (`service.py`) — lost on restart and different on each replica — and downloads of existing blobs would fail. Blob must be treated as enabled based on the auth mode, and in QA/UAT/PROD the application must fail if Blob is not configured rather than fall back to local disk.

### 2. Azure RBAC decides what the identity can do 

- **`Storage Blob Data Contributor`** — allows the backend to upload, read and delete blobs. It can be assigned at one of two scopes:

  | | Container scope| Storage-account scope |
  |---|---|---|
  | How it works | The role applies only to the document container. The identity can read, write and delete blobs in that container and nothing else in the account. | The role applies to every container in the storage account. |
  | Container creation | The container must already exist, because a role can only be assigned on an existing container. It is pre-created at provisioning time and the per-upload `create_container()` call is skipped in managed-identity mode, which also removes the existing per-upload create-and-catch-exception overhead. | The identity can create containers, so the existing `create_container()` call keeps working and no pre-creation is needed, including today's per-upload create-and-catch-exception overhead, which stays as it is. |
  | Blast radius | Limited to one container. | Every container in the account, including any that are added later. |
  | User Delegation Key | Needs an additional role: `Storage Blob Delegator` at storage-account scope or higher. | No additional role needed. |
  | Trade-off | Least privilege, but needs the platform team to create the container up front and assign two roles. | Simpler to set up (one role), but broader than the application needs. |

- **`Storage Blob Delegator`** — allows the backend to generate a User Delegation Key for User Delegation SAS. Whether it is needed depends on the scope chosen above:
  - **Storage-account scope:** `Storage Blob Data Contributor` already includes the permission to generate a User Delegation Key, so **no additional role is needed**.
  - **Container scope:** `Storage Blob Delegator` must be assigned at the storage-account, resource-group, or subscription scope because generating a User Delegation Key is a storage-account-level operation.
- RBAC controls only what the backend identity can do against Blob Storage. It does not replace the application's user or group authorization.

### 3. Uploading a document 

- **With container-scoped RBAC :** the container is **pre-created at provisioning time**, so in managed-identity mode the per-upload `create_container()` call in `_ensure_blob_container_exists()` is skipped and the identity needs no container-creation rights. This also removes an existing inefficiency: today, `create_container()` runs on every upload and always throws `ResourceExistsError` after the first one, adding a needless request and exception on every upload regardless of RBAC. Dev/local (connection-string mode) can keep creating the container as it does today.
- **With storage-account-scoped RBAC:** the identity is allowed to create containers, so `create_container()` can stay as it is, including the per-upload create-and-catch-exception overhead that exists today.
- The file is then written with `upload_blob(...)` (as the managed identity in QA/UAT/PROD).

### 4. A user requests a document — list, download or view 

- The application validates user and collection access with its existing checks (`check_collection_access()`, `visible_to_groups`, owner/admin). This does not change with the Managed Identity / RBAC work.
- Two paths that currently skip this check are covered separately under *Application Authorization Gaps* below.

### 5. SAS is issued 

- `resolve_document_download_url()` obtains a User Delegation Key with `get_user_delegation_key()` and calls `generate_blob_sas(..., user_delegation_key=...)` instead of `account_key=...`. Permission stays read-only, single blob, TTL from `AZURE_BLOB_SAS_TTL_MINUTES`.
- The delegation key is cached and refreshed before it expires, rather than requested for every document. A SAS cannot outlive the key that signed it, so the key must be refreshed at least one SAS TTL (60 minutes by default) before it expires.
- **Fail closed:** if a SAS cannot be issued, return an error. The current behaviour of returning a plain, unsigned blob URL is removed. This is required for the migration: today the choice to sign depends on an `AccountKey` being present, so switching to Managed Identity without this change would make every document URL unsigned.

### 6. Client downloads directly from Blob Storage

- The user receives the SAS URL and downloads straight from Blob Storage, as today. The backend does not proxy the file.

### What this gives

- No account key in the environment.
- The SAS is tied to the Entra identity that requested the User Delegation Key, providing identity-based traceability, and Azure Storage requests made using the SAS can also be logged.
- Access can be cut off by revoking the delegation keys or the role assignment, without rotating a shared account key.
- Note: the identity Azure sees is the backend's managed identity, not the end user. Per-user attribution (who downloaded which document) continues to come from application logs.

## Key Trade-offs and Limitations

**1. User Delegation SAS adds Azure-side dependencies and a new moving part.**
- `get_user_delegation_key()` only works when the storage account allows Azure AD authentication. Some locked-down accounts disable this — to be confirmed for this account (see *To Confirm*).
- RBAC role assignments (`Storage Blob Data Contributor`, `Storage Blob Delegator`) can take up to ~30 minutes to propagate in Azure. Expect transient 403 errors right after any role change or the first cut-over — this is expected propagation delay, not a broken setup.
- A User Delegation Key is valid for at most 7 days and must be cached and refreshed by the application (see step 5). Today's static account key never expires, so this refresh logic is a genuinely new moving part, not a like-for-like swap.

**2. Workload Identity is an infrastructure dependency, not a code change.**
- The federated credential, ServiceAccount annotation, and testing in QA/UAT before PROD all sit outside this repository, and depend on whoever owns the AKS clusters and the Entra app registrations (see *To Confirm*).
- Until Workload Identity is live in a given environment, that environment must keep using the connection string. So during the transition, the account-key and User Delegation SAS code paths exist side by side — more moving parts than today's single static-key path, not fewer, until every environment has cut over.

**3. Azure RBAC does not add per-user access control.**
- The role is granted to the backend's own identity, not to individual end users. Azure RBAC only ever answers "can the backend talk to storage at all" — it has no concept of this application's users, groups or collections.
- All per-user and per-collection authorization continues to live entirely in the application's own checks (`check_collection_access()`, `visible_to_groups`, owner/admin), exactly as today (see flow step 4). This proposal does not add a second, independent enforcement layer at the Azure resource level — Azure still cannot answer "is this user allowed to read this blob."
- In short: this proposal closes a credential-hygiene and auditability gap (no shared key, access traceable to an identity). It does not reduce reliance on, or duplicate, the existing application-level authorization model.

## Environment Strategy

| Environment | Blob authentication | Notes |
|---|---|---|
| Dev / local | Connection string (`.env`, Docker Compose, or `docker run --env-file`) | Use a storage account separate from QA/UAT/PROD, or Azurite locally. Account-key SAS remains on this path only. |
| QA, UAT, PROD (AKS) | Managed Identity via Workload Identity, User Delegation SAS | No key or connection string in the deployment. |

- A **new explicit setting** selects the mode. It does not exist in the code today; the name is a proposal (for example `BLOB_AUTH_MODE=managed_identity | connection_string`).
- In QA/UAT/PROD, if the managed identity is unavailable the application **fails with an error** and never falls back to a connection string. A silent fallback would put the account key back in production without anyone noticing.

**Why Dev/local keeps the connection string**

The objective is to remove shared storage-account credentials from QA/UAT/PROD, not to eliminate connection strings everywhere. Dev keeps the simpler approach because:
- **The key protects little.** Dev uses a storage account separate from QA/UAT/PROD with no production data, so a leaked Dev key exposes test files only.
- **Workload Identity is AKS-only.** Shared Dev is deployed with `docker run` on a host and local work uses Docker Compose, so there is no Kubernetes pod to attach a federated identity to.
- **Local development stays simple.** Developers can work without an Azure login or role assignments on the storage account, or use Azurite (a local storage emulator).
- **One approach to maintain**, instead of an identity-based setup for environments where the risk is low.

This should be revisited if Dev holds real or copied production data, or shares a storage account with UAT/PROD. In that case the Dev key would be equivalent to a production key.

## Suggestions (optional)

- **Generate SAS only on explicit download** instead of for every document on a listing call. This reduces the number of live download URLs, but changes what the list API returns, so the frontend must be checked first.
- **Log each SAS issuance** (user, document, blob, TTL), alongside the existing orphan-blob audit lines.
- **Prefix blob names by collection** (`documents/<collection_id>/...`) to allow per-collection lifecycle or scoping later. Requires migrating existing blobs.
- **Separate read and write identities.** One identity for the write path and one for the read path, for tighter least privilege.
- **Interim measure if the platform work (managed identity, federated credential, role assignments) is delayed:** move the connection string from the ConfigMap into a Kubernetes Secret (Key Vault-backed).
- Once all AKS environments use managed identity and Dev uses a separate account, **disable shared-key access** on the AKS environments' storage account.

## To Confirm Before Implementation

**Blocks the plan if unfavorable — confirm first:**
- Whether the storage account allows Azure AD (Entra ID) authentication. If this is disabled, `get_user_delegation_key()` cannot work at all, and User Delegation SAS — the core of this proposal — cannot be implemented as designed.
- Whether Workload Identity (OIDC issuer and the Workload Identity feature) is enabled on the AKS clusters. Without it, the pod cannot get a Managed Identity at all, so step 1 of the flow cannot happen. The UAT cluster (`SHAREDSERVICES-01-AKS-UAT`) is shared, so enabling it is a platform-level decision and the most likely item to take time.

**Affects how carefully we roll out, not whether the plan works:**
- Whether the storage account and container are shared with other applications. The plan still works either way, but if shared, rotating the account key or disabling shared-key access would affect other consumers and needs coordination, and container-scoped RBAC matters more.

**Background — informational, doesn't change whether this proposal succeeds:**
- Whether the storage container is private in live QA/UAT/PROD (this belongs to Finding 4 in `existing_blob_accesscontrol.md`, not to this proposal).
- Whether any RBAC role assignments already exist on the storage account.
- Who can read the ConfigMap that holds the connection string (stops mattering once the key is retired).
- That Dev/local use a storage account separate from QA/UAT/PROD (only affects the Dev risk-acceptance reasoning above, not QA/UAT/PROD).

**Separate issue — needed to fix the Application Authorization Gap below, not to implement Managed Identity/RBAC:**
- The intended callers of the `http-execution` presigned-URL endpoint, and how it is routed in PROD (UAT ingress shows it behind oauth2-proxy), to decide how to protect it.

## Application Authorization Gaps (separate from RBAC)

These are not solved by Managed Identity or Azure RBAC. RBAC controls what the backend identity can do against Blob Storage; it does not decide which user may see which document. Both are application code changes.

**1. Orphan-document fallback** (`download` and `view`, `router.py`)
- Currently serves the file without `check_collection_access()` when the database row is missing. Change to one of: require a database row (return 404), or restrict the fallback to admins. Decision needed from the owners of this code, since the fallback is deliberate today.

**2. `GET /api/http-execution/presigned-url/{document_id}`** (`http_execution/routes.py`)
- Currently validates only that the token is a valid PAT, workflow token or JWT, and returns a SAS URL for any `document_id`. Add a collection-level access check equivalent to the one on `/api/pat/documents/*`, or restrict the endpoint to the callers it was built for (external services such as TADA Chat).
- Exposure depends on routing: in `k8s/ingress-uat.yaml` only `/api/http-execution/trigger*` bypasses oauth2-proxy, so this route appears to sit behind oauth2-proxy on UAT. PROD and any other ingress are to be confirmed.
