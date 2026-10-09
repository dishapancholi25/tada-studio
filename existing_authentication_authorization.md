# Existing Authentication & Authorization Architecture — Tada Studio

**Purpose:** Baseline documentation of the current identity and access-control implementation, prepared for evaluating where Azure RBAC could be introduced.

**Scope:** Backend (`Tadastudio/New-Tada/backend`). All file references have been verified against the current codebase.

---

## 1. Summary

Tada Studio separates identity from permissions, and the two are implemented very differently:

- **Authentication** (confirming *who* a user is) is already built on **Azure AD / Microsoft Entra ID**, via an OAuth2-Proxy sitting in front of the application.
- **Authorization** (deciding *what* an authenticated user is allowed to do) is **entirely custom-built** — a combination of database tables, environment variables, and in-app comparison logic. It reads some identity data from Azure AD (group membership, in one case), but no permission decision is delegated to Azure's own access-control systems (Azure RBAC / Entra App Roles / Directory Roles).

This gap — Azure-based authentication, but fully homegrown authorization — is the relevant starting point for scoping an Azure RBAC initiative.

---

## 2. Authentication

Authentication is handled by **OAuth2-Proxy**, which performs the OIDC login flow against Azure AD and forwards identity to the backend in one of two ways:

| Path | Mechanism | Used when |
|---|---|---|
| **Header-based** | Proxy validates the user and forwards trusted headers (`X-Auth-Request-Email`, `X-Auth-Request-Groups`) | Standard browser traffic through the proxy |
| **Token-based** | Backend validates a JWT bearer token directly and extracts claims (`email`, `groups`, `roles`, `oid`, `tid`) | API/service calls, or when proxy headers aren't present |

A third path exists for **Personal Access Tokens** (`na_`-prefixed strings), authenticated separately from the OAuth flow, used for programmatic API access outside a browser session.

There is also a **development-only bypass** (`SKIP_AUTH`), which substitutes a fixed mock identity — intended strictly for local development, not present in any deployed environment.

**Key file:** `backend/api/auth/dependencies.py` (`get_current_user`)

---

## 3. Authorization

Authorization is not a single system — it is **six largely independent mechanisms**, each governing a different kind of access decision. A request may pass through several of these depending on what it's trying to do.

### 3.1 User Role

Every user record carries one role, stored as a plain column on the `users` table:

```
PENDING | USER | ADMIN | SYSTEM
```

`SYSTEM` is notable: it is auto-assigned (not manually set) whenever the login claims are detected as belonging to an Azure AD **service principal** (a machine/application identity) rather than a human user — including retroactive promotion of existing accounts if this detection logic is added after the fact.

**Key files:** `backend/models/auth/role.py` (enum), `backend/models/auth/user.py` (table)

### 3.2 Admin Determination

"Is this user an admin?" is answered by checking **four independent sources**, in order, with the first match winning:

1. **Database role** — `users.role == "ADMIN"`
2. **`ADMIN_USERS` environment variable** — a plain-text email allowlist
3. **`ADMIN_GROUP` environment variable** — compared against the `groups`/`roles` claim from the Azure AD JWT
4. **A database-managed "Administrators" group** — a separate membership table, checked with caching

Only source 3 involves Azure AD data at all, and even then the comparison is performed entirely in application code — Azure is not making the decision.

**Key file:** `backend/services/auth/rbac.py` (`is_user_admin`)

### 3.3 Feature-Level Access Control

A `feature_access` table lists individual application features (e.g. `settings.database`, `settings.llm_providers`) with a single `admin_only` boolean per feature. A route-level decorator (`@feature_access_required("...")`) enforces this per endpoint.

Logic: admins always pass; for non-admins, the feature's `admin_only` flag decides access; a feature not yet present in the table **defaults to accessible by all users** rather than defaulting closed.

**Key files:** `backend/models/configuration/feature_access.py`, `backend/api/auth/rbac_middleware.py`, `check_feature_access()` in `rbac.py`

### 3.4 Workflow-Level Sharing

Individual workflows can be shared with specific users at one of three levels — **Owner, Editor, Viewer** — tracked in a dedicated join table (`workflow_memberships`), one row per (workflow, user) pair.

Access resolution checks, in order: admin status → direct ownership (a separate concept from membership) → an explicit membership row. This is the only one of the six mechanisms that is **per-object** (scoped to an individual workflow) rather than account-wide.

**Key files:** `backend/models/workflows/membership.py`, `verify_workflow_access()` in `backend/services/graph/storage/access_control.py`

### 3.5 Group-Based Resource Visibility

Certain resources (e.g. datasource/database connections) carry a `visible_to_groups` field. A resource is visible to a user if: they own it, the field contains the special value `__all__` (shared with everyone), or the field overlaps with the groups the user belongs to. Only the owner can change a resource's visibility.

Unlike mechanism 3.2, the "groups" here are **not** Azure AD groups — they are manually created, in-app groups (`Group` / `GroupMembership` database tables), managed entirely within Tada Studio and explicitly separate from Azure AD group membership. This mechanism touches no Azure AD data at all.

**Key files:** `backend/services/datasource/service.py` (`get_connection_for_user`), `backend/services/groups/service.py` (`get_user_groups`)

### 3.6 API Token Scopes

Personal Access Tokens carry an explicit scope list (e.g. `workflow:*:read`) constraining what that specific token can do. This scoping system applies **only** to PAT-authenticated requests — normal interactive sessions are not subject to it.

---

## 4. Summary Table

| # | Mechanism | Governs | Enforced via | Touches Azure AD data? |
|---|---|---|---|---|
| 1 | User Role | Baseline account status | DB column | No |
| 2 | Admin Determination | Full admin access | DB + env vars + JWT group claim (4-way fallback) | Partially (source 3 only) |
| 3 | Feature-Level Access | Specific settings/pages | DB table + route decorator | No |
| 4 | Workflow Sharing | Individual workflow access | DB join table (Owner/Editor/Viewer) | No |
| 5 | Group-Based Visibility | Resource visibility (e.g. connections) | In-app group membership vs. stored group list | No |
| 6 | PAT Scopes | Programmatic API access | Token-embedded scope list | No |

---

## 5. Observations Relevant to Azure RBAC Scoping

- **Authentication already depends on Azure AD** — no changes needed there for an RBAC initiative.
- **No authorization decision currently uses Azure RBAC or Entra App/Directory Roles.** The only mechanism that touches Azure AD data at all is mechanism 2 (source 3, the `ADMIN_GROUP` claim check), and even there it's limited to reading group membership and comparing it manually in code — the equivalent of Azure's own role-assignment and policy evaluation is not in use anywhere. Mechanism 5's "groups" are a separate, in-app concept and involve no Azure AD data.
- Mechanisms 2 and 3 (account-wide admin/feature access) are the most natural candidates for delegating to **Entra App Roles**, since they are coarse, account-level permissions — closer to what Azure RBAC is designed to express.
- Mechanisms 4 and 6 (per-workflow sharing, per-token scopes) are fine-grained, application-domain permissions and are a poor fit for Azure RBAC, which governs Azure resources rather than arbitrary in-app objects.
- Separately, the application's own access to Azure resources (OpenAI, Blob Storage) currently relies on static API keys rather than Managed Identity / Workload Identity with real Azure RBAC role assignments — a distinct gap from user-facing authorization, but part of the same overall "not using Azure RBAC yet" picture.
