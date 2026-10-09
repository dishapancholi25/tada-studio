# Local Email/Password Authentication Feature

> **Status:** Not yet implemented. This document captures a fully-designed feature
> that was prototyped on `main` and then reverted so it can be reimplemented on a
> dedicated branch. All file contents and diffs are preserved below.

---

## Architecture

The core challenge: nginx's `auth_request` only understands oauth2-proxy sessions.
A local auth user would be rejected by nginx before their request ever reaches FastAPI.

**Solution:** Replace `auth_request /oauth2/auth` with `auth_request /api/auth/nginx-check`,
a new FastAPI endpoint that:

1. Checks for `_local_auth` cookie -> validates local JWT -> returns 200 with headers if valid
2. If absent/invalid -> calls `http://127.0.0.1:4180/oauth2/auth` via httpx -> forwards that response

```
User -> nginx
  +-- auth_request /api/auth/nginx-check (internal)
       +-- _local_auth cookie?  -> validate JWT -> 200 + X-Auth-Request-Email
       +-- no local cookie      -> forward to oauth2-proxy -> 200 or 401
  +-- 401 -> redirect /login?rd=<original_uri>  (instead of /oauth2/start)
  +-- 200 -> proxy to backend/frontend with X-Auth-Request-* headers
```

Backend's `get_current_user` still works unchanged via the `X-Auth-Request-Email` header path.

**Toggle:** `ENABLE_LOCAL_AUTH` env var (default: `false`). When false, the app behaves
identically to the original Entra-only setup. The `/login` page auto-redirects to
`/oauth2/start` if the feature is disabled.

**Dependencies needed:** None new -- `bcrypt`, `httpx`, and `pyjwt` are already in `pyproject.toml`.

---

## Endpoints

### Public (no auth required)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/auth/nginx-check` | Unified session check for nginx `auth_request` |
| GET | `/api/auth/local/status` | Returns `{enabled: bool}` for frontend |
| POST | `/api/auth/local/login` | `{email, password}` -> set `_local_auth` cookie |
| POST | `/api/auth/local/logout` | Clear `_local_auth` cookie |

### Admin-only (requires `require_admin`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/local/users` | Create local user `{email, password}` |
| GET | `/api/auth/local/users` | List local users (no passwords) |
| DELETE | `/api/auth/local/users/{user_id}` | Deactivate user |
| PUT | `/api/auth/local/users/{user_id}/reset-password` | `{new_password}` |

---

## Files Overview

| File | Status | Purpose |
|------|--------|---------|
| `backend/models/auth/local_user.py` | **New** | SQLAlchemy model |
| `backend/services/auth/local_auth.py` | **New** | Auth service (bcrypt, JWT, CRUD) |
| `frontend/src/app/login/page.tsx` | **New** | Dual-option login page |
| `frontend/src/components/settings/tabs/LocalUsersTab.tsx` | **New** | Admin UI |
| `backend/api/auth/routes.py` | Modified | Add all local auth endpoints |
| `backend/api/auth/dependencies.py` | Modified | Local cookie check in `get_current_user` |
| `backend/models/auth/__init__.py` | Modified | Export `LocalUser` |
| `nginx.conf` | Modified | auth_request swap, public locations, redirect |
| `oauth2-proxy.cfg` | Modified | skip_auth_routes |
| `frontend/src/contexts/AuthContext.tsx` | Modified | `local_password` logout, `/login` redirects |
| `frontend/src/app/settings/page.tsx` | Modified | LocalUsersTab integration |

---

## New File Contents

### backend/models/auth/local_user.py

```python
"""Local user authentication model for non-Entra users."""

from sqlalchemy import Boolean, Column, String

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class LocalUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A locally-managed user account with email/password credentials.

    Used for external users who don't have a Microsoft Entra account.
    Passwords are stored as bcrypt hashes.

    Attributes:
        id: UUID primary key.
        email: Unique email address (used as login identifier).
        hashed_password: bcrypt hash of the user's password.
        is_active: Whether the account is enabled.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "local_users"

    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
```

### backend/services/auth/local_auth.py

```python
"""Local email/password authentication service.

Manages locally-created user accounts for external users who don't have
a Microsoft Entra identity. Passwords are stored as bcrypt hashes and
sessions are issued as HS256 JWTs stored in an HttpOnly cookie.
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import bcrypt
import jwt as pyjwt

from backend.models.auth.local_user import LocalUser
from backend.services.auth.config import get_auth_config
from backend.services.database import get_db

logger = logging.getLogger(__name__)

# Feature flag -- set ENABLE_LOCAL_AUTH=true to activate email/password auth.
# Defaults to false so the app behaves identically to the original Entra-only setup.
LOCAL_AUTH_ENABLED: bool = os.getenv("ENABLE_LOCAL_AUTH", "false").lower() in {"1", "true", "yes"}

_LOCAL_AUTH_AUDIENCE = "local-auth"
_LOCAL_AUTH_ISSUER = "agenticstudio"
_LOCAL_JWT_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def create_local_user(email: str, password: str) -> LocalUser:
    """Create a new local user account.

    Raises:
        ValueError: If a user with that email already exists.
    """
    email = email.strip().lower()
    with get_db() as db:
        existing = db.query(LocalUser).filter(LocalUser.email == email).first()
        if existing:
            raise ValueError(f"A local user with email '{email}' already exists.")
        user = LocalUser(email=email, hashed_password=_hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"[LOCAL-AUTH] Created local user: {email}")
        return user


def get_local_users() -> list[LocalUser]:
    """Return all local user records (active and inactive)."""
    with get_db() as db:
        return db.query(LocalUser).order_by(LocalUser.created_at).all()


def get_local_user_by_id(user_id: str) -> Optional[LocalUser]:
    """Fetch a local user by primary key."""
    with get_db() as db:
        return db.query(LocalUser).filter(LocalUser.id == user_id).first()


def deactivate_local_user(user_id: str) -> bool:
    """Deactivate (soft-disable) a local user. Returns True if found."""
    with get_db() as db:
        user = db.query(LocalUser).filter(LocalUser.id == user_id).first()
        if not user:
            return False
        user.is_active = False
        db.commit()
        logger.info(f"[LOCAL-AUTH] Deactivated local user id={user_id}")
        return True


def reset_local_user_password(user_id: str, new_password: str) -> bool:
    """Update the password for a local user. Returns True if found."""
    with get_db() as db:
        user = db.query(LocalUser).filter(LocalUser.id == user_id).first()
        if not user:
            return False
        user.hashed_password = _hash_password(new_password)
        db.commit()
        logger.info(f"[LOCAL-AUTH] Password reset for local user id={user_id}")
        return True


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def verify_local_user(email: str, password: str) -> Optional[LocalUser]:
    """Verify email/password credentials.

    Returns the LocalUser on success, None on failure (wrong credentials
    or inactive account).
    """
    email = email.strip().lower()
    with get_db() as db:
        user = (
            db.query(LocalUser)
            .filter(LocalUser.email == email, LocalUser.is_active == True)  # noqa: E712
            .first()
        )
        if user and _check_password(password, user.hashed_password):
            return user
    return None


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_local_jwt(email: str) -> str:
    """Issue a signed JWT for a local user session (7-day expiry)."""
    config = get_auth_config()
    now = int(time.time())
    payload = {
        "sub": email,
        "email": email,
        "auth_source": "local_password",
        "iss": _LOCAL_AUTH_ISSUER,
        "aud": _LOCAL_AUTH_AUDIENCE,
        "iat": now,
        "exp": now + _LOCAL_JWT_EXPIRY_SECONDS,
    }
    return pyjwt.encode(payload, config.jwt_secret, algorithm="HS256")


def validate_local_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Validate a local auth JWT. Returns claims dict or None."""
    config = get_auth_config()
    try:
        claims = pyjwt.decode(
            token,
            config.jwt_secret,
            algorithms=["HS256"],
            audience=_LOCAL_AUTH_AUDIENCE,
            issuer=_LOCAL_AUTH_ISSUER,
        )
        return claims
    except pyjwt.ExpiredSignatureError:
        logger.debug("[LOCAL-AUTH] JWT expired")
    except pyjwt.InvalidTokenError as exc:
        logger.debug(f"[LOCAL-AUTH] Invalid JWT: {exc}")
    return None
```

### frontend/src/app/login/page.tsx

```tsx
"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export default function LoginPage() {
    const searchParams = useSearchParams();
    const rd = searchParams.get("rd") || "/";

    const [localAuthEnabled, setLocalAuthEnabled] = useState<boolean | null>(null);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // On mount: check whether local auth is enabled. If not, skip the login page
    // entirely and go straight to Microsoft -- preserving original Entra-only behaviour.
    useEffect(() => {
        fetch("/api/auth/local/status", { credentials: "include" })
            .then((r) => r.json())
            .then((data) => {
                if (!data.enabled) {
                    window.location.replace(
                        `/oauth2/start?rd=${encodeURIComponent(rd)}`,
                    );
                } else {
                    setLocalAuthEnabled(true);
                }
            })
            .catch(() => {
                // If the status check fails, fall back to Microsoft auth
                window.location.replace(
                    `/oauth2/start?rd=${encodeURIComponent(rd)}`,
                );
            });
    }, [rd]);

    const handleMicrosoftSignIn = () => {
        window.location.href = `/oauth2/start?rd=${encodeURIComponent(rd)}`;
    };

    const handleLocalSignIn = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);
        try {
            const res = await fetch("/api/auth/local/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ email, password }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                setError(data.detail ?? "Invalid email or password.");
                return;
            }
            window.location.href = rd;
        } catch {
            setError("Network error -- please try again.");
        } finally {
            setLoading(false);
        }
    };

    // Show nothing while we determine whether local auth is on (avoids flash)
    if (localAuthEnabled === null) {
        return (
            <div
                className="flex min-h-screen items-center justify-center"
                style={{ background: "var(--color-bg-primary)" }}
            />
        );
    }

    return (
        <div
            className="flex min-h-screen items-center justify-center p-4"
            style={{ background: "var(--color-bg-primary)" }}
        >
            <div
                className="w-full max-w-sm rounded-[24px] border-2 p-8 shadow-[0_35px_120px_rgba(0,0,0,0.65)]"
                style={{
                    borderColor: "rgba(var(--color-primary-rgb),0.30)",
                    background:
                        "linear-gradient(135deg, rgba(26,26,26,0.96), rgba(16,16,16,0.98), rgba(6,6,6,1))",
                }}
            >
                {/* Header */}
                <div className="mb-8 text-center">
                    <h1
                        className="mb-1 text-2xl font-semibold"
                        style={{ color: "var(--color-text-primary)" }}
                    >
                        Sign in
                    </h1>
                    <p
                        className="text-sm"
                        style={{ color: "var(--color-text-muted)" }}
                    >
                        Choose how you&apos;d like to continue
                    </p>
                </div>

                {/* Microsoft sign-in */}
                <button
                    type="button"
                    onClick={handleMicrosoftSignIn}
                    className="mb-6 flex w-full items-center justify-center gap-3 rounded-xl border px-4 py-3 text-sm font-medium transition-all duration-200 hover:brightness-110 active:scale-[0.98]"
                    style={{
                        borderColor: "rgba(var(--color-primary-rgb),0.40)",
                        background: "rgba(var(--color-primary-rgb),0.10)",
                        color: "var(--color-primary-light)",
                    }}
                >
                    <MicrosoftLogo />
                    Sign in with Microsoft
                </button>

                {/* Divider */}
                <div className="mb-6 flex items-center gap-3">
                    <div
                        className="h-px flex-1"
                        style={{ background: "var(--color-border)" }}
                    />
                    <span
                        className="text-xs uppercase tracking-[0.2em]"
                        style={{ color: "var(--color-text-muted)" }}
                    >
                        or
                    </span>
                    <div
                        className="h-px flex-1"
                        style={{ background: "var(--color-border)" }}
                    />
                </div>

                {/* Local sign-in form */}
                <form onSubmit={handleLocalSignIn} className="space-y-4">
                    <div>
                        <label
                            htmlFor="email"
                            className="mb-1.5 block text-xs uppercase tracking-[0.2em]"
                            style={{ color: "var(--color-text-secondary)" }}
                        >
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            autoComplete="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors focus:border-[color:var(--color-primary)]"
                            style={{
                                background: "rgba(255,255,255,0.04)",
                                borderColor: "var(--color-border)",
                                color: "var(--color-text-primary)",
                            }}
                        />
                    </div>
                    <div>
                        <label
                            htmlFor="password"
                            className="mb-1.5 block text-xs uppercase tracking-[0.2em]"
                            style={{ color: "var(--color-text-secondary)" }}
                        >
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            autoComplete="current-password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors focus:border-[color:var(--color-primary)]"
                            style={{
                                background: "rgba(255,255,255,0.04)",
                                borderColor: "var(--color-border)",
                                color: "var(--color-text-primary)",
                            }}
                        />
                    </div>

                    {error && (
                        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                            {error}
                        </p>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
                        style={{
                            background:
                                "linear-gradient(135deg, rgba(var(--color-primary-rgb),0.8), rgba(var(--color-primary-rgb),0.6))",
                            color: "var(--button-primary-text, #fff)",
                        }}
                    >
                        {loading ? "Signing in..." : "Sign in"}
                    </button>
                </form>
            </div>
        </div>
    );
}

function MicrosoftLogo() {
    return (
        <svg width="18" height="18" viewBox="0 0 21 21" aria-hidden="true">
            <rect x="1" y="1" width="9" height="9" fill="#F25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
            <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
            <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
        </svg>
    );
}
```

### frontend/src/components/settings/tabs/LocalUsersTab.tsx

```tsx
"use client";

import { useEffect, useState } from "react";
import { Plus, RotateCcw, UserX } from "lucide-react";
import { useToast } from "@/contexts/ToastContext";

interface LocalUser {
    id: string;
    email: string;
    is_active: boolean;
    created_at: string | null;
}

async function apiRequest(path: string, options?: RequestInit) {
    const res = await fetch(path, {
        ...options,
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Request failed (${res.status})`);
    }
    return res.json();
}

export default function LocalUsersTab() {
    const { showToast } = useToast();
    const [users, setUsers] = useState<LocalUser[]>([]);
    const [loading, setLoading] = useState(true);

    // Create form
    const [newEmail, setNewEmail] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [creating, setCreating] = useState(false);

    // Reset password form (keyed by user id)
    const [resetUserId, setResetUserId] = useState<string | null>(null);
    const [resetPassword, setResetPassword] = useState("");
    const [resetting, setResetting] = useState(false);

    const loadUsers = async () => {
        try {
            const data = await apiRequest("/api/auth/local/users");
            setUsers(data.users ?? []);
        } catch (err) {
            showToast("error", String(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadUsers();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setCreating(true);
        try {
            await apiRequest("/api/auth/local/users", {
                method: "POST",
                body: JSON.stringify({ email: newEmail, password: newPassword }),
            });
            showToast("success", `User ${newEmail} created.`);
            setNewEmail("");
            setNewPassword("");
            await loadUsers();
        } catch (err) {
            showToast("error", String(err));
        } finally {
            setCreating(false);
        }
    };

    const handleDeactivate = async (user: LocalUser) => {
        if (!confirm(`Deactivate ${user.email}?`)) return;
        try {
            await apiRequest(`/api/auth/local/users/${user.id}`, { method: "DELETE" });
            showToast("success", `${user.email} deactivated.`);
            await loadUsers();
        } catch (err) {
            showToast("error", String(err));
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!resetUserId) return;
        setResetting(true);
        try {
            await apiRequest(`/api/auth/local/users/${resetUserId}/reset-password`, {
                method: "PUT",
                body: JSON.stringify({ new_password: resetPassword }),
            });
            showToast("success", "Password updated.");
            setResetUserId(null);
            setResetPassword("");
        } catch (err) {
            showToast("error", String(err));
        } finally {
            setResetting(false);
        }
    };

    return (
        <div className="p-6 max-w-2xl space-y-8">
            {/* ... full JSX for create form, user list, reset password inline form ... */}
            {/* See the original file for full UI implementation */}
        </div>
    );
}
```

---

## Diffs for Modified Files

### backend/api/auth/dependencies.py

Add local JWT cookie check in `get_current_user`, after the `SKIP_AUTH` / dev-mode block
and before the oauth2-proxy header check:

```python
    # Local email/password cookie check (defence-in-depth alongside nginx-check)
    # Only active when ENABLE_LOCAL_AUTH=true
    if request is not None:
        from backend.services.auth.local_auth import LOCAL_AUTH_ENABLED

        local_token = request.cookies.get("_local_auth") if LOCAL_AUTH_ENABLED else None
        if local_token:
            from backend.services.auth.local_auth import validate_local_jwt

            local_claims = validate_local_jwt(local_token)
            if local_claims:
                from backend.services.auth.rbac import get_user_groups, is_user_admin

                sync_user_from_claims(local_claims)
                local_claims["is_admin"] = is_user_admin(local_claims)
                local_claims["groups"] = get_user_groups(local_claims)
                logger.debug("[AUTH] Local cookie authentication successful")
                return local_claims
```

### backend/api/auth/routes.py

Add to imports:

```python
import os
import httpx
from fastapi import Request, Response
from pydantic import BaseModel
from .dependencies import require_admin  # add to existing import
```

Then add all endpoints after the existing `update_token_scopes` endpoint:

- `nginx_session_check` (GET `/nginx-check`)
- `local_auth_status` (GET `/local/status`)
- `local_login` (POST `/local/login`)
- `local_logout` (POST `/local/logout`)
- `create_local_user_endpoint` (POST `/local/users`)
- `list_local_users_endpoint` (GET `/local/users`)
- `deactivate_local_user_endpoint` (DELETE `/local/users/{user_id}`)
- `reset_local_user_password_endpoint` (PUT `/local/users/{user_id}/reset-password`)

(Full implementation captured in the git diff -- ~240 lines of new code appended to routes.py)

### backend/models/auth/\_\_init\_\_.py

Add import and export:

```python
from .local_user import LocalUser
# Add "LocalUser" to __all__
```

### nginx.conf

**4 `auth_request` changes:**

```nginx
# In locations: /api/, /api/ws/, /api/graph/ws/, /
auth_request /api/auth/nginx-check;  # was: /oauth2/auth
```

**Redirect change:**

```nginx
location @oauth2_signin {
    return 302 https://$host/login?rd=$request_uri;  # was: /oauth2/start?rd=...
}
```

**3 new location blocks** (added before the `/api/` block):

```nginx
# Internal: unified session check
location = /api/auth/nginx-check {
    internal;
    proxy_pass         http://backend;
    proxy_set_header   Cookie         $http_cookie;
    proxy_set_header   X-Original-URI $request_uri;
    proxy_set_header   X-Real-IP      $remote_addr;
    proxy_set_header   X-Scheme       $scheme;
    proxy_set_header   Host           $host;
}

# Public: custom login page (no auth required)
location = /login {
    proxy_pass http://frontend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffer_size 128k;
    proxy_buffers 8 256k;
    proxy_busy_buffers_size 256k;
}

# Public: local email/password auth API (no auth required)
location ~ ^/api/auth/local/ {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### oauth2-proxy.cfg

Add to `skip_auth_routes`:

```
"^/login$",                      # Custom dual-path login page
"^/api/auth/local/",             # Local email/password auth endpoints
"^/api/auth/nginx-check$",       # nginx unified session check (internal only)
```

### frontend/src/contexts/AuthContext.tsx

In the `logout` function:

1. Change oauth_proxy redirect: `"/oauth2/sign_out?rd=/login"` (was `rd=/`)
2. Add new branch before `basic_auth`:

   ```typescript
   } else if (authSource === "local_password") {
       await fetch("/api/auth/local/logout", {
           method: "POST",
           credentials: "include",
       }).catch(() => {});
       window.location.href = "/login";
   }
   ```

3. Change basic_auth and default redirects to `/login` (were `/`)

### frontend/src/app/settings/page.tsx

1. Add import: `import LocalUsersTab from "@/components/settings/tabs/LocalUsersTab";`
2. Change `adminTab` (single object) to `adminTabs` (array) including new `local-users` tab
3. Add `localAuthEnabled` state + useEffect to fetch `/api/auth/local/status`
4. Filter admin tabs: hide `local-users` when `!localAuthEnabled`
5. Add case in `renderTabContent`: `case "local-users": return <LocalUsersTab />;`
