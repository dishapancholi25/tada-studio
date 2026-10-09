# Proposed Azure RBAC Solution — Tada Studio

**Context:** Follow-on to `existing_authentication_authorization.md` (the as-is research). This document covers the proposed solution — where Azure RBAC would actually plug into the codebase, in what phases, and what could go wrong.

---

## 1. What Already Exists (Brief Recap)

Full detail is in `existing_authentication_authorization.md`. In short: authentication already runs on Azure AD, but authorization is entirely custom-built across 6 mechanisms. The one relevant here is **Mechanism 2 — Admin Determination**, a 4-way fallback in `is_user_admin()` (`backend/services/auth/rbac.py`), checked in this order:

1. `User.role == "ADMIN"` in the database
2. Email in the `ADMIN_USERS` env var
3. `ADMIN_GROUP` env var matched against the user's Azure AD **group** claim
4. Membership in a database-managed `Administrators` group

None of these use Azure RBAC or Entra App Roles. Only #3 touches Azure AD data at all, and even that's a manual comparison in app code, not a delegated Azure decision.

---

## 2. Where Azure RBAC Actually Comes In

Azure RBAC's *decision* — who has what role — is made entirely inside Azure AD (Entra ID app registration → App Roles → assigned to users/groups). That decision reaches this app only through the **JWT token's `roles` claim** at login. The codebase's job is to receive that claim correctly and act on it. Three code locations are involved:

### 2.1 `backend/api/auth/dependencies.py` (header-based auth path, ~lines 149-157)
Currently:
```python
groups = (
    unverified_claims.get("groups")
    or unverified_claims.get("roles")
    or unverified_claims.get("wids")
    or []
)
claims["groups"] = groups if isinstance(groups, list) else [groups] if groups else []
```
This collapses `roles`/`wids`/`groups` into one field, destroying the distinction between an Azure AD Group and an Entra App Role. **Fix:** add a separate field, e.g. `claims["app_roles"] = unverified_claims.get("roles") or []`, without touching the existing `groups` logic.

### 2.2 `backend/services/auth/providers/oauth2_proxy.py` (`verify_and_sync()`, token-based auth path)
**Verified gap, independent of this proposal:** this path builds claims via `dict(payload)` + `enrich_claims()` (in `user_sync.py`), and `enrich_claims()` only touches email/name/auth_source — it never looks at `groups`, `roles`, or `wids` at all. So today, a user authenticating via this path who has a `roles`-only claim (no `groups`) would not be recognized by the existing `ADMIN_GROUP` check either, independent of anything we're proposing. The same `app_roles` extraction needs to be added here too, or the two auth paths will behave inconsistently.

### 2.3 `backend/services/auth/rbac.py`, `is_user_admin()` (line ~142)
This is the actual decision point. Add a new check reading `claims["app_roles"]` for a specific role value (e.g., `"TadaStudio.Admin"`).

### 2.4 `backend/services/auth/rbac.py`, `check_feature_access()` — later, optional
Could be extended the same way, using per-feature App Roles (e.g., `"TadaStudio.Settings.Database"`) instead of the current `feature_access` DB table. Not designed in detail yet — flagged as a possible Phase 2+ extension, not part of the initial plan.

**Why this is worth doing — the operational split it creates:** today, the only way to give a regular user access to one specific admin-only feature (e.g., settings) is to make them a full admin, or have someone manually edit a database row/env var to carve out an exception. Once this extension exists, granting that one specific permission becomes a one-time Azure AD admin action — assigning a named role to that person in the Entra portal — with no code change, no database edit, and no deployment needed. This creates a clean split going forward:
- **Developers (one-time setup):** define the specific roles needed (e.g., "can view settings") and update the code to recognize them.
- **Azure AD admins (ongoing, day-to-day):** decide who gets which role, and grant or revoke it whenever needed, entirely inside Azure's own admin tools — properly audited, without touching the app at all.

**Concrete examples of where this could apply, beyond the "settings" example above:**

- **Config Viewer vs. Config Admin (system configuration):** today, looking at system configuration and changing it are protected by the exact same single gate — full admin or nothing. Splitting this into two roles would let someone (e.g., support/ops staff) view configuration for troubleshooting, without also being able to change it.
- **Group Manager (user group administration):** there is currently no tier here at all — creating or managing user groups requires full admin, with nothing in between. A dedicated role would let someone manage groups without inheriting every other admin capability.
- **User Approver (new user approval):** approving a newly-registered user today also requires full admin. A dedicated role would let a team lead or manager approve their own team's new users without needing full admin rights.

**An honest scope note on these three:** they don't all currently live in the same part of the code. Settings access already goes through the feature-access system this section is extending. Group management and user approval, however, are currently just informal, one-off checks written directly into their own business logic, with no shared feature-access system behind them at all. That means delivering all three isn't just "extend one function" — it's touching a few different places in the code, each in its own way. Still recommended as a Phase 2+ idea, not part of the initial rollout.

### 2.5 Azure AD / Entra ID app registration (outside the codebase)
Someone with admin access to Tada Studio's app registration must **define** the App Role(s) and **assign** them to users/groups. Until this exists, `app_roles` will simply be an empty list for everyone — the code changes above do nothing on their own without this.

---

## 3. Blast Radius If This Changes

`is_user_admin()` gates roughly **61 endpoints** via `require_admin`/`@admin_required` (concentrated in `admin/routes.py` — 23 endpoints — plus monitoring, config API, model deployments, guardrails/compliance, auth, library, tutorial, collaboration), and `check_feature_access()` gates another **~12 endpoints** via `require_feature_access` (mainly MCP server settings, plus evaluations). Any change to the admin-determination logic affects all of these at once, not a single isolated feature.

---

## 4. Two-Phase Approach

### Phase 1 — Add (low risk)
Azure Role becomes a **5th** path in `is_user_admin()`, alongside the existing 4 — not a replacement. Nobody's current access changes. This is what's designed above (sections 2.1–2.3).

**Purpose:** validate that App Roles actually flow through correctly end-to-end before touching anything that currently works.

### Phase 2 — Migrate, then replace (higher risk, separate decision)
1. Identify everyone with current admin access via any of the 4 existing mechanisms (query `User.role = 'ADMIN'`, check `ADMIN_USERS`/`ADMIN_GROUP` env vars, check the DB `Administrators` group membership table).
2. Assign all of them the new Azure App Role in Entra ID.
3. Confirm the Azure Role path grants them access correctly (Phase 1's new 5th path).
4. Only then remove the old 4 checks from `is_user_admin()`, making Azure RBAC the sole source of truth.

**This phase is not automatic and should not be assumed as part of "just adding RBAC."** Skipping the migration step and removing old checks prematurely would lock out every current admin who wasn't manually re-assigned first.

---

## 5. Edge Cases

- **Auth-path inconsistency (already exists today, independent of this proposal):** the header-based and token-based auth paths currently handle `groups`/`roles`/`wids` differently — the header path has a fallback chain, the token path has none at all. Whether a user's role claim is recognized today already depends on which path they authenticated through. This proposal's `app_roles` field needs to be added to *both* paths, or this inconsistency continues.

- **No App Roles defined/assigned yet:** if Entra ID has no App Roles configured for this app registration, `app_roles` will be an empty list for every user, and the new check in `is_user_admin()` will simply never match — not an error, just inert.

- **Timing/propagation delay:** Azure Role assignment changes only take effect the next time a user gets a fresh token (re-login or token refresh) — unlike the existing DB-based checks (`User.role`, `Administrators` group), which take effect on the very next request. Someone newly assigned the Azure Role won't see the change until their session refreshes. Worth setting expectations on this if Phase 2 migration is compared against the old system's immediacy.

- **Partial migration risk (Phase 2 specifically):** if the audit in step 1 misses someone who has admin access via a less-obvious path (e.g., indirect DB `Administrators` group membership), they would silently lose access once the old checks are removed, with no error until they try to use an admin feature.

- **Caching consistency:** `is_user_admin()`'s existing DB group check uses a TTL cache (`_admin_group_cache`, `FEATURE_ACCESS_CACHE_TTL_SECONDS`). Any new Azure Role check should follow a consistent caching approach, or the different admin-check paths could behave inconsistently in how quickly they reflect a change.

- **Feature-level extension (section 2.4) is a much larger scope than the admin check** — it would require defining one Entra App Role per feature rather than one `"Admin"` role, which is a bigger Azure AD administration burden. Not recommended as part of the initial rollout.

---

## 6. Additional Authentication Paths Found (Not in Original Scope)

Beyond the header-based and token-based paths in section 2, the codebase has 3 more distinct authentication routes, verified in `dependencies.py`:

- **WebSocket authentication (`get_current_user_ws()`)** — has its own separate claims-building logic. Its header-fallback branch builds claims with only `email`/`name`/`sub`/`user_id`/`auth_source` — no `groups` key at all, no `roles`/`wids` extraction. Same category of gap as section 2.1/2.2 — needs the same `app_roles` fix if this path should also recognize Azure RBAC.
- **Personal Access Token (PAT) authentication (`_authenticate_pat()`)** — bypasses `is_user_admin()` entirely; sets `is_admin` directly from `user.role == "ADMIN"` and hardcodes `"groups": []`. **Structurally excluded, not a gap:** a PAT is a static, long-lived token, not obtained via a fresh Azure AD login — there is no Azure role claim to check for these requests.
- **Local username/password login (`ENABLE_LOCAL_AUTH` cookie path)** — also does not go through Azure AD. **Structurally excluded, not a gap:** same reasoning as PAT — no Azure login means no Azure role claim exists to check.

---

## 7. Where Azure RBAC Was Considered and Declined

Not everything authorization-related is a fit for Azure RBAC. These were explicitly considered and ruled out, with reasons:

| Area | Why declined |
|---|---|
| **Workflow-level sharing** (`WorkflowRole` — Owner/Editor/Viewer, Mechanism 4) | Dynamic, per-object grants created constantly by end users (every share action = a new permission relationship). Azure App Roles are static and centrally managed — not designed to be created/assigned at this scale or frequency. Stays as app-level DB authorization. |
| **Collection access via shared workflows** (separate bug found — see `existing_authentication_authorization.md` for full detail) | Same reasoning as above — fine-grained, per-object, per-user data access, not a coarse role. The actual fix is a missing `check_collection_access()` call in `execute_collection_search()`, a code fix unrelated to Azure RBAC. |
| **Group-Based Resource Visibility** (Mechanism 5 — `visible_to_groups` on datasource connections) | Uses manually-created, in-app groups (`Group`/`GroupMembership` tables) — explicitly separate from and unrelated to Azure AD groups. Not an Azure RBAC candidate at all. |
| **API Token Scopes** (Mechanism 6 — PAT scope lists) | Applies only to programmatic PAT-authenticated requests, which (per section 6) structurally cannot carry a fresh Azure role claim in the first place. Orthogonal to RBAC. |
| **PAT and local-auth authentication paths** (section 6) | Neither goes through an Azure AD login, so neither can ever carry an Azure role claim. Excluded by the mechanics of authentication itself, not a design choice. |
| **User Role baseline status** (Mechanism 1 — `PENDING`/`USER`/`ADMIN`/`SYSTEM` DB column) | This is account lifecycle status (e.g., pending approval), not a permission decision — stays as a DB-managed field regardless of RBAC adoption. |

---

## 8. A Second, Distinct Way to Implement Azure RBAC — Securing the App's Own Access to Azure Resources

Everything in sections 2–8 covers Azure RBAC as it applies to *people* — which user can do what inside Tada Studio. But the original ask was broader than user access alone: to suggest ways Azure RBAC could be implemented, period. There is a second, genuinely different area where it applies: securing **the app itself**, when it talks to other Azure services, via Managed Identity + ARM role assignments instead of stored static keys. This isn't a side note — it's a second legitimate answer to the same question, just governing machine-to-Azure access rather than user-to-app access. Verified against the actual code, this isn't one uniform gap — it's three different situations:
  - **Already supports Managed Identity, just not the default:** the main Azure OpenAI LLM provider, the embeddings service, and Azure Document Intelligence all already have a working `use_managed_identity` option, falling back to it only if no API key is configured. The capability exists — it's simply not turned on, and stored keys remain the default path. Closing this is mostly a configuration/cleanup effort, not new development.
  - **No Managed Identity option exists at all:** Blob Storage (document upload/storage) only supports a single static connection string today, with no fallback or alternative. This would need genuinely new code, not just a default flip.
  - **Not currently applicable:** Key Vault isn't used anywhere in the codebase today — secrets currently live in environment variables per existing security guidance. Granting Key Vault access via ARM RBAC isn't a current gap, since there's no Key Vault in the picture to grant access to.
