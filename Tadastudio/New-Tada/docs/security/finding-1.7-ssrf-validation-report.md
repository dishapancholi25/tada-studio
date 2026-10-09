# Finding 1.7 – Server-Side Request Forgery via HTTP Request Workflow Node

## Validation Report

**Ticket:** #6427  
**Branch:** `feature/6427-ssrf-http-request-workflow-node`  
**Validated By:** Abid Dasurkar  
**Date:** 2026-07-20  

---

## Scenario 1 – Internal Backend Access via Loopback

**PoC:**
```
GET http://127.0.0.1:8000/api/auth/me
```

**Observed Result:**
```
SSRF protection blocked request: IP address 127.0.0.1 is in a blocked range.
```

**Status:** ✅ PASS

---

## Scenario 2 – SSRF + Authentication Bypass Chain

**PoC:**
```
GET http://127.0.0.1:8000/api/auth/me
Headers:
  X-Auth-Request-Email: victim@mashreq.com
  X-Auth-Request-Groups: admins
```

**Observed Result:**  
Request never reaches the target because `127.0.0.1` is blocked at the SSRF validation layer.

**Status:** ✅ PASS

> The SSRF → Authentication Bypass chain documented by ISG is no longer executable.

---

## Scenario 3 – Azure Metadata Service (IMDS)

**PoC:**
```
GET http://169.254.169.254/metadata/identity/oauth2/token
Headers:
  Metadata: true
```

**Observed Result:**
```
SSRF protection blocked request: IP address 169.254.169.254 is in a blocked range.
```

**Status:** ✅ PASS

> No metadata or managed identity information returned.

---

## Scenario 4 – Public Internet Request Validation

**PoC:**
```
GET https://postman-echo.com/get
GET http://httpbin.org/get
```

**Observed Result:**  
Not blocked by SSRF protection. Errors received were:
- `SSL certificate verification failed` (corporate proxy/TLS interception)
- `503 Service Temporarily Unavailable` (httpbin.org down)

Both indicate requests were **allowed to leave the application** — SSRF controls did not interfere.

**Status:** ✅ PASS

> Public destinations are not being blocked by SSRF controls.

---

## Scenario 5 – Dangerous Header Injection

Validated via automated backend tests.

### Headers Verified Stripped

| Header | Stripped? |
|--------|-----------|
| `X-Auth-Request-Email` | ✅ Removed |
| `X-Auth-Request-Groups` | ✅ Removed |
| `X-Auth-Request-User` | ✅ Removed |
| `Metadata` | ✅ Removed |
| `Authorization` | ✅ Removed (unless structured auth config allows it) |
| `Cookie` | ✅ Removed |

### Tests

| Test Name | Result |
|-----------|--------|
| `test_x_auth_request_headers_stripped` | ✅ PASSED |
| `test_metadata_header_stripped` | ✅ PASSED |
| `test_authorization_header_stripped_unless_allowed` | ✅ PASSED |
| `test_cookie_header_stripped` | ✅ PASSED |
| `test_header_stripping_case_insensitive` | ✅ PASSED |

**Status:** ✅ PASS

> Dangerous headers are stripped before outbound transmission.

---

## Scenario 6 – Redirect Revalidation

Validated via automated backend tests.

### Tests

| Test Name | Result |
|-----------|--------|
| `test_redirect_to_internal_is_blocked` | ✅ PASSED |
| `test_too_many_redirects_raises` | ✅ PASSED |

### Verified Flow

```
safe.example.com
      ↓ 302
169.254.169.254 (IMDS)
      ↓
BLOCKED: "SSRF protection blocked redirect"
```

**Status:** ✅ PASS

> Redirect targets are revalidated before execution.

---

## Additional Protection Verified

### Blocked CIDR Ranges (Database-Managed)

| Range | Purpose |
|-------|---------|
| `10.0.0.0/8` | RFC1918 private |
| `172.16.0.0/12` | RFC1918 private |
| `192.168.0.0/16` | RFC1918 private |
| `127.0.0.0/8` | Loopback |
| `169.254.0.0/16` | Link-local / IMDS |
| `0.0.0.0/8` | Zero network |
| `::1/128` | IPv6 loopback |
| `fc00::/7` | IPv6 unique local |
| `fe80::/10` | IPv6 link-local |

### Admin UI

- Network Security tab added under Admin Settings
- CRUD management of per-tool blocked IP ranges
- Policies can be toggled on/off, ranges added/removed dynamically
- No hardcoded values at runtime — database is the source of truth

---

## Final Validation Matrix

| Scenario | Status |
|----------|--------|
| Localhost SSRF | ✅ PASS |
| SSRF → Auth Bypass Chain | ✅ PASS |
| Azure IMDS Access | ✅ PASS |
| Public Internet Requests | ✅ PASS |
| Dangerous Header Injection | ✅ PASS |
| Redirect Revalidation | ✅ PASS |

---

## Conclusion

✅ All six validation scenarios pass.

✅ Original ISG PoCs using `127.0.0.1` and `169.254.169.254` can no longer be reproduced.

✅ Dangerous header forwarding is prevented.

✅ Redirect-based SSRF bypasses are prevented.

✅ Legitimate outbound requests remain functional.

✅ Admin-configurable network security policies (per-tool blocked IP ranges) provide operational flexibility.

**Based on the evidence gathered and automated test coverage, Finding 1.7 can be considered fully remediated and validated.**

---

## Test Evidence

### Automated Test Run (26 tests)

```
backend/tests/services/test_guardrails.py::TestSSRFRuntimeEnforcement

PASSED test_file_scheme_blocked_at_execution
PASSED test_http_scheme_passes_validation
PASSED test_blocked_range_blocked_at_execution[http://127.0.0.1:8000/api/auth/me-loopback IPv4]
PASSED test_blocked_range_blocked_at_execution[http://127.0.0.2/x-loopback subnet]
PASSED test_blocked_range_blocked_at_execution[http://10.0.0.1/internal-RFC-1918 10/8]
PASSED test_blocked_range_blocked_at_execution[http://10.255.255.1/internal-RFC-1918 10/8 edge]
PASSED test_blocked_range_blocked_at_execution[http://172.16.0.1/internal-RFC-1918 172.16/12]
PASSED test_blocked_range_blocked_at_execution[http://172.31.255.1/internal-RFC-1918 172.31/12 edge]
PASSED test_blocked_range_blocked_at_execution[http://192.168.0.1/internal-RFC-1918 192.168/16]
PASSED test_blocked_range_blocked_at_execution[http://192.168.255.254/x-RFC-1918 192.168/16 edge]
PASSED test_blocked_range_blocked_at_execution[http://169.254.169.254/latest/meta-data/-Azure/AWS IMDS]
PASSED test_blocked_range_blocked_at_execution[http://169.254.0.1/x-link-local start]
PASSED test_blocked_range_blocked_at_execution[http://0.0.0.0/-zero address]
PASSED test_ipv6_blocked_ranges_at_execution[http://[::1]/-IPv6 loopback]
PASSED test_ipv6_blocked_ranges_at_execution[http://[fc00::1]/-IPv6 ULA fc00::/7]
PASSED test_ipv6_blocked_ranges_at_execution[http://[fd00::1]/-IPv6 ULA fd00::/7]
PASSED test_ipv6_blocked_ranges_at_execution[http://[fe80::1]/-IPv6 link-local]
PASSED test_dns_failure_is_blocked_not_allowed
PASSED test_redirect_to_internal_is_blocked
PASSED test_too_many_redirects_raises
PASSED test_x_auth_request_headers_stripped
PASSED test_metadata_header_stripped
PASSED test_authorization_header_stripped_unless_allowed
PASSED test_cookie_header_stripped
PASSED test_header_stripping_case_insensitive
PASSED test_imds_url_plus_metadata_header_both_blocked

======================== 26 passed in 2.40s ========================
```

### Key Implementation Files

| File | Purpose |
|------|---------|
| `backend/services/guardrails/ssrf.py` | URL validation, DNS resolution, IP range blocking |
| `backend/services/guardrails/ssrf_policy_service.py` | Database-backed policy CRUD + caching |
| `backend/tools/http_request/handlers.py` | Header stripping, redirect revalidation, SSRF-safe send |
| `backend/api/admin/routes.py` | Admin API for managing blocked IP ranges |
| `backend/models/configuration/tool_security_policy.py` | ORM model for per-tool policies |
| `backend/services/database/migrations/schema_updates.py` | DB table creation + seeding |
| `frontend/src/components/settings/tabs/admin/NetworkSecurityTab.tsx` | Admin UI for network policies |
| `frontend/src/lib/admin-api.ts` | Frontend API client for SSRF policy management |
