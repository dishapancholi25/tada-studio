"""SSRF (Server-Side Request Forgery) protection for HTTP tool calls.

Validates URLs against an admin-managed allow-list of exact endpoints
(IP or hostname, optionally scoped to a specific port and/or path) to
prevent agents from accessing internal network services, cloud metadata
endpoints, and any other resource that was never explicitly approved.

Allow-list entries support the following forms:
    - ``10.0.0.1``          -> any port, any path on that IP
    - ``10.0.0.1:5005``     -> any path, only port 5005
    - ``10.0.0.1/get``      -> only path ``/get``, any port
    - ``10.0.0.1:5005/get`` -> only path ``/get`` on port 5005
    - ``www.google.com``    -> hostname match, any port/path
There is no CIDR/range support and no DNS resolution: matching is a direct
string comparison against the host the caller supplied, so an empty
allow-list blocks everything (fail-closed).
"""

import logging
from fnmatch import fnmatch
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from backend.models.workflow.configs.guardrails import ToolCallPolicy
from backend.services.guardrails.models import GuardrailResult, Violation

logger = logging.getLogger(__name__)

# Default allow-list: empty means nothing is allowed until an admin (or the
# per-tool `<TOOL_ID>_ALLOWED_IPS` env var) configures entries. Fail-closed.
DEFAULT_ALLOWED_ENDPOINTS: List[str] = []

# Schemes that should never be allowed
BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "dict", "ldap", "telnet"}


def validate_url(url: str, policy: Optional[ToolCallPolicy] = None) -> GuardrailResult:
    """Validate a URL against SSRF protections.

    Checks:
    1. Scheme is HTTP/HTTPS only
    2. Hostname does not resolve to a blocked IP range
    3. URL matches allowed patterns (if configured)
    4. URL does not match blocked patterns

    Args:
        url: The URL to validate
        policy: Optional tool call policy with URL restrictions

    Returns:
        GuardrailResult indicating whether the URL is safe
    """
    violations: List[Violation] = []

    if not url or not isinstance(url, str):
        return GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="tool_call",
                    rule_name="ssrf_invalid_url",
                    severity="block",
                    message="Invalid or empty URL",
                )
            ],
            action_taken="blocked",
        )

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="tool_call",
                    rule_name="ssrf_parse_error",
                    severity="block",
                    message=f"Failed to parse URL: {url}",
                )
            ],
            action_taken="blocked",
        )

    # Check scheme
    scheme = (parsed.scheme or "").lower()
    if scheme in BLOCKED_SCHEMES:
        violations.append(
            Violation(
                category="tool_call",
                rule_name="ssrf_blocked_scheme",
                severity="block",
                message=f"URL scheme '{scheme}' is not allowed",
                details={"url": url, "scheme": scheme},
            )
        )
        return GuardrailResult(
            passed=False, violations=violations, action_taken="blocked"
        )

    if scheme not in ("http", "https"):
        violations.append(
            Violation(
                category="tool_call",
                rule_name="ssrf_invalid_scheme",
                severity="block",
                message=f"Only HTTP/HTTPS schemes are allowed, got '{scheme}'",
                details={"url": url, "scheme": scheme},
            )
        )
        return GuardrailResult(
            passed=False, violations=violations, action_taken="blocked"
        )

    hostname = parsed.hostname
    if not hostname:
        return GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="tool_call",
                    rule_name="ssrf_no_hostname",
                    severity="block",
                    message="URL has no hostname",
                    details={"url": url},
                )
            ],
            action_taken="blocked",
        )

    # Check blocked URL patterns
    if policy and policy.blocked_url_patterns:
        for pattern in policy.blocked_url_patterns:
            if fnmatch(url, pattern) or fnmatch(hostname, pattern):
                violations.append(
                    Violation(
                        category="tool_call",
                        rule_name="ssrf_blocked_pattern",
                        severity="block",
                        message=f"URL matches blocked pattern: {pattern}",
                        details={"url": url, "pattern": pattern},
                    )
                )
                return GuardrailResult(
                    passed=False, violations=violations, action_taken="blocked"
                )

    # Check allowed URL patterns (if configured, URL must match at least one)
    if policy and policy.allowed_url_patterns:
        matched = any(
            fnmatch(url, pattern) or fnmatch(hostname, pattern)
            for pattern in policy.allowed_url_patterns
        )
        if not matched:
            violations.append(
                Violation(
                    category="tool_call",
                    rule_name="ssrf_not_allowed",
                    severity="block",
                    message="URL does not match any allowed pattern",
                    details={
                        "url": url,
                        "allowed_patterns": policy.allowed_url_patterns,
                    },
                )
            )
            return GuardrailResult(
                passed=False, violations=violations, action_taken="blocked"
            )

    # Check the endpoint against the admin-managed allow-list. Entries are
    # read from `policy.blocked_ip_ranges` — the field name is kept as-is
    # for API/DB compatibility, but it now holds allow-list entries rather
    # than blocked CIDR ranges.
    allow_entries = (
        policy.blocked_ip_ranges if policy else None
    ) or DEFAULT_ALLOWED_ENDPOINTS
    req_port = parsed.port or (443 if scheme == "https" else 80)
    req_path = parsed.path or "/"

    if not _is_endpoint_allowed(hostname, req_port, req_path, allow_entries):
        return GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="tool_call",
                    rule_name="ssrf_not_in_allowlist",
                    severity="block",
                    message=f"Endpoint '{hostname}:{req_port}{req_path}' is not in the allow-list",
                    details={
                        "url": url,
                        "hostname": hostname,
                        "port": req_port,
                        "path": req_path,
                    },
                )
            ],
            action_taken="blocked",
        )

    return GuardrailResult(passed=True)


def parse_endpoint_entry(
    entry: str,
) -> Optional[Tuple[str, Optional[int], Optional[str]]]:
    """Parse an allow-list entry into ``(host, port, path)``.

    Accepts a bare IP/hostname, ``host:port``, ``host/path``,
    ``host:port/path``, or a full URL. ``port``/``path`` are ``None`` when
    not specified in the entry, meaning "any port"/"any path" for that host.

    Args:
        entry: The raw allow-list entry string.

    Returns:
        ``(host, port, path)`` tuple (host lower-cased), or ``None`` if the
        entry is empty or cannot be parsed (e.g. no hostname).
    """
    if not entry or not isinstance(entry, str):
        return None
    candidate = entry.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    try:
        parsed = urlparse(candidate)
    except Exception:
        return None
    host = parsed.hostname
    if not host:
        return None
    path = parsed.path or None
    if path == "/":
        path = None
    return (host.lower(), parsed.port, path)


def _is_endpoint_allowed(
    hostname: str, port: int, path: str, allow_entries: List[str]
) -> bool:
    """Check whether ``hostname:port/path`` matches any allow-list entry.

    Matching is an exact comparison per field:
        - host must match exactly (case-insensitive)
        - port matches only if the entry specifies one; otherwise any port
          is allowed for that host
        - path matches only if the entry specifies one; otherwise any path
          is allowed for that host(:port)

    Args:
        hostname: Hostname/IP from the request URL
        port: Effective port from the request URL (scheme default applied)
        path: Effective path from the request URL (``/`` default applied)
        allow_entries: Raw allow-list entries to check against

    Returns:
        True if the endpoint is allowed by at least one entry.
    """
    hostname_lower = hostname.lower()
    for raw_entry in allow_entries:
        parsed_entry = parse_endpoint_entry(raw_entry)
        if not parsed_entry:
            continue
        entry_host, entry_port, entry_path = parsed_entry
        if entry_host != hostname_lower:
            continue
        if entry_port is not None and entry_port != port:
            continue
        if entry_path is not None and entry_path != path:
            continue
        return True
    return False
