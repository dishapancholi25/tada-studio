# Azure Blob Storage — RBAC and Retention

**Context:** Vishal clarified the actual ask was RBAC specifically for Azure Blob Storage, plus retention — not the broader application-wide admin/feature RBAC covered in `proposed-azure-rbac-solution.md`. This document covers both pieces, with blockers and dependencies called out explicitly before committing to any delivery date.

---

## 1. How Access Control ("RBAC") Actually Works Today on Azure Blob

**There is no Azure RBAC — no role assignments, no Managed Identity. Access is enforced entirely in application code, then a time-limited SAS token is issued.** Step by step, verified in `service.py` and `api/documents/router.py`:

1. **Single shared credential** — `_get_blob_service_client()` (~line 124) builds one `BlobServiceClient` from `AZURE_BLOB_CONNECTION_STRING` (account key). Every request from the backend uses this same identity — confirmed the only place a blob client is constructed anywhere in the codebase. The storage account itself has no concept of "which app user" is asking.
2. **App-layer authorization happens first**, before any blob operation:
   - Upload: `router.py` (~line 188) checks `collection.user_id != user_id` (owner-only).
   - Delete/reprocess: same ownership check ("Only the collection owner can...").
   - Download/search: `document_service.check_collection_access(doc_info.collection_id, user_id)` (~line 565) — allows the owner **or** users the collection was shared with via `GroupService().get_user_groups()`.
3. **Only after that check passes**, the backend calls `generate_blob_sas()` (~line 337) to mint a **read-only** SAS token, expiring after `ttl_minutes` (~line 335). This SAS URL — not a direct Azure credential — is what's actually handed to the client as the download link. It's the only thing that talks to Azure with scoped, time-boxed permission (read-only, single blob).
4. **Storage naming has no per-user isolation** — blobs live at a flat path `documents/{file_id}{extension}` (`_build_blob_name`) in one shared container, so there's no container/prefix-level boundary an Azure RBAC role could even be scoped to today, even if one were introduced.
5. **Deletion** — `get_blob_client(...).delete_blob(...)` (~line 228), triggered only from `delete_document()`/`delete_collection()`, both owner-only manual actions.

**Net:** authorization is decided by the app's own database (`collection.user_id`, group membership) — Azure's only role in access control today is the SAS token's read-only, time-limited scope. There is no identity- or role-based decision made by Azure itself anywhere in this flow.

## 2. Retention Period

**There isn't one.**

- No TTL/expiry exists for the blob **content** itself — only the **SAS download link** expires (`AZURE_BLOB_SAS_TTL_MINUTES`, default 60 minutes). After that window, a *new* SAS link would need to be generated, but the underlying blob is completely untouched and still fully present in storage.
- No Azure Storage lifecycle management rules (auto-tier-to-cool/archive, auto-delete-after-N-days) are configured anywhere in code or docs.
- The blob is deleted **only** when a user explicitly triggers `delete_document()`/`delete_collection()` — both owner-only, manual actions. Nothing deletes a document automatically, ever.
- No scheduled/cron purge job exists for documents. **Worth a precise correction here:** guardrail violations *do* have a retention function — `guardrails/retention.py`, a 1-year rolling purge (`DELETE FROM guardrail_violations WHERE created_at < NOW() - INTERVAL '1 year'`). But verified: this function is defined and **never called anywhere else in the backend** — no scheduler, cron, or background task actually invokes it. It's not proof that retention infrastructure exists and works; it's a dormant example of the same unsolved problem, not a working precedent to build on.

**Net:** documents persist indefinitely in Blob Storage until a user manually deletes them. The only "expiring" thing in the whole flow is the 60-minute SAS download URL, which is unrelated to data retention — it governs link lifespan, not document lifespan.

---

## 3. Blockers and Dependencies Before Committing to a Delivery Date

### Good news first — some groundwork already exists

`azure-identity` is already a project dependency (`pyproject.toml`, `"azure-identity>=1.25.1"`), and `DefaultAzureCredential`/`ManagedIdentityCredential` are already used for other Azure services — confirmed in the LLM provider, embeddings, Document Intelligence, OCR, and the MCP-server managed identity service. The credential pattern itself isn't being invented from scratch for blob storage — it just needs to be extended to the one place that doesn't use it yet.

### Blockers

1. **No workload identity wired into the AKS deployment.** Checked `backend/k8s/deployment.yaml` directly — confirmed no `serviceAccountName`, no `azure.workload.identity/use` label, no federated credential setup at all. Without this, `DefaultAzureCredential` running inside the cluster has no Azure identity to actually use. This is an **infra/platform-team dependency**, not something app code alone can fix, and needs doing for both UAT and PROD.
2. **Blob storage still uses account-key auth, not Managed Identity.** Switching to `BlobServiceClient(account_url, credential=DefaultAzureCredential())` needs a new storage-account-URL setting and removal of the connection-string path — a real behavior change needing testing across local dev (no managed identity available there, so a fallback like `az login` or a service principal is needed locally), UAT, and PROD separately.
3. **No per-user/tenant data isolation in the container.** All documents sit in one flat container (`documents/{file_id}{extension}`). Azure RBAC role assignments are normally scoped to a container or prefix — today there's nothing to scope them *to*. A data-layout change (per-user or per-tenant prefixes/containers) is a prerequisite if the actual goal is "user X's role only grants access to user X's documents" — without it, RBAC only ever narrows down to "can this app touch this container at all," which is no more granular than the app-level check that already exists today.
4. **Role assignment ownership sits outside this repo entirely.** Granting the AKS Managed Identity a role (`Storage Blob Data Contributor`/`Reader`) on the storage account happens in Azure itself (Portal, Terraform, or Bicep) — not in this codebase. Checked for any infrastructure-as-code under `k8s` or pipeline configs in this repo — found none, so it's not yet clear who owns that step or where it would be tracked.
5. **No retention requirement has been defined.** There's no product or compliance decision anywhere saying "delete documents after N days." This blocks writing any purge logic at all, since there's no target duration to build against — unlike, for comparison, the app's own `memory_retention_days` setting or the guardrails 1-year rule, both of which do have a defined number.
6. **No scheduler/cron infrastructure confirmed for a purge job.** Checked directly — the guardrails retention function is never called anywhere in the backend, and there's no CronJob, Celery, or APScheduler configuration found in the k8s folder either. If retention is pursued, this means standing up a new scheduled-job mechanism from nothing — separate infrastructure work on its own, not a small addition to existing code.
7. **The SAS token flow needs to coexist with or be reasoned about alongside any RBAC change**, not assumed to be automatically replaced by it. The read-only SAS URL is currently the only per-download control that exists. SAS tokens can still be generated from a client authenticated via Managed Identity, but that needs explicit design and testing — not assumed to be a no-op change.

### Dependencies to line up before starting

- **Azure infra/platform team** — AKS workload identity + federated credential setup, and the storage account role assignment itself.
- **Product/compliance owner** — sign-off on retention duration, and whether any document types need legal-hold or immutability specifically.
- **A data-layout decision** — whether per-user/tenant prefixing is actually required, if RBAC granularity below "whole container" is the goal.
- **Confirmation of a job scheduler** — either locate an existing one we haven't found, or plan for standing up a new one.

### Recommendation

Scope this as **two separate, sequential efforts**, not one combined delivery — Managed Identity migration for blob authentication (moderate effort, the pattern already exists elsewhere in the codebase) and the retention policy (blocked purely on a product/compliance decision plus scheduler infrastructure). Their blockers and owners don't overlap, so bundling them into one delivery would tie a mostly-technical piece of work to a decision that isn't in engineering's control.

---

## 4. Alignment with Platform-Wide RBAC

Vishal's direction: the focus here is Blob Storage specifically, but the design should stay aligned with the platform's overall RBAC direction (covered separately in `proposed-azure-rbac-solution.md`) — not built as a disconnected, parallel effort.

**These are two different mechanisms, answering two different questions, and that distinction matters for how "alignment" actually works:**
- **Platform RBAC** decides *which user* is allowed to do what inside Tada Studio — via Entra App Roles, checked in application code (`is_user_admin()`, `check_feature_access()`).
- **Blob Storage RBAC** decides what *the app itself* is allowed to do when talking to Azure Storage — via Managed Identity + ARM role assignments, a machine identity, not a user one.

**Where they're independent — no alignment needed to proceed:** Managed Identity for the app's own connection to Blob Storage (Blocker #1 and #2 in section 3) doesn't depend on platform RBAC maturity at all, since it has nothing to do with user identity. This piece can move on its own timeline.

**Where they genuinely intersect — this is the real alignment point:** per-user/tenant data isolation at the storage layer (Blocker #3) is where the two meet. Today, "which user can access which document" is decided entirely by our own database — nothing to do with Azure. If per-user isolation is ever built at the storage layer itself, that decision should be driven by whatever identity/role model platform RBAC settles on, not a second, separately-invented user-authorization mechanism specific to Blob Storage. Building storage-level isolation ahead of and disconnected from platform RBAC is exactly the rework risk the team already flagged in the meeting (Part 21, section 4 of the meeting notes) — this is the same concern restated at the design level, not a new one.

**Practical alignment steps:**
1. Keep a consistent role-naming convention across both efforts (e.g., the same `TadaStudio.*` prefix already proposed for platform RBAC), so this reads as one coordinated security strategy rather than two unrelated ones.
2. Sequence per-user isolation *after* platform RBAC's user/role model is settled, not in parallel with it.
3. Treat Managed Identity (app-to-Azure) as safe to progress independently, since it doesn't touch user identity at all.

---

## 5. What Azure Offers for Retention, Once a Requirement Is Known

- **Lifecycle management policies** — Azure-enforced rules that transition or delete blobs after a defined age, configured declaratively (no app-side scheduler needed for this specific option, unlike the DB-row purge pattern guardrails attempted).
- **Immutable storage (time-based retention / legal hold)** — blobs become undeletable/unmodifiable until a set date, enforceable even against an account admin — the relevant option if any document types have a legal minimum retention period.
- **Soft delete** — a recoverable window after deletion, protecting against accidental/malicious loss.

---

## 6. Bottom Line

Neither RBAC nor retention has existing capability to build on for Blob Storage specifically — both are net-new work touching infrastructure (Managed Identity/workload identity federation), data layout (per-user isolation, needed for genuine RBAC rather than just securing the app's own access), and a product/compliance decision (retention duration) that hasn't been made yet. This should be flagged clearly before committing to a delivery date — none of these three dependencies can be shortcut by engineering effort alone.
