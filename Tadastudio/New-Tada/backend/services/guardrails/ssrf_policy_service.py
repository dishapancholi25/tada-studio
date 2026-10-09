"""Admin-managed per-tool SSRF allow-list policies.

Provides CRUD operations plus a short TTL cache over the ``tool_security_policies``
table, and a helper to obtain the *effective* allow-list entries for a given
tool/service.

Initial seeding source (first access only, when no DB row exists yet for a
``tool_id``): the ``<TOOL_ID>_ALLOWED_IPS`` environment variable (comma
separated entries, same format as the admin API - see
``backend.services.guardrails.ssrf.parse_endpoint_entry``). If that env var
is unset or blank, the seed is an empty list, i.e. fail-closed - nothing is
allowed until an admin adds entries. That seed is immediately persisted as a
real DB row, so the database is always the single source of truth going
forward and every subsequent add/remove/update goes through the existing
CRUD functions below.
"""

import logging
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

from backend.services.guardrails.ssrf import parse_endpoint_entry

logger = logging.getLogger(__name__)

# Canonical tool identifier for the HTTP Request tool.
HTTP_REQUEST_TOOL_ID = "HTTP_REQUEST"

# In-memory per-tool cache of effective entries: tool_id -> (fetched_at, entries)
_CACHE_TTL_SECONDS = 60
_cache: Dict[str, Tuple[float, List[str]]] = {}
_cache_lock = threading.Lock()


def _env_seed_entries(tool_id: str) -> List[str]:
    """Return the allow-list entries seeded from ``<TOOL_ID>_ALLOWED_IPS``.

    Args:
        tool_id: Canonical tool identifier (e.g. ``"HTTP_REQUEST"``).

    Returns:
        Parsed, non-empty entries from the env var, or ``[]`` if the env var
        is unset/blank.
    """
    raw = os.getenv(f"{tool_id}_ALLOWED_IPS", "")
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def validate_allow_entries(entries: List[str]) -> List[str]:
    """Validate and normalise a list of allow-list entries.

    Args:
        entries: List of allow-list entries, e.g. ``"10.0.0.1"``,
            ``"10.0.0.1:5005"``, ``"10.0.0.1/get"``, ``"10.0.0.1:5005/get"``,
            a domain, or a full URL.

    Returns:
        The normalised (stripped) list of valid entries.

    Raises:
        ValueError: If any entry is empty or cannot be parsed into a host.
    """
    normalised: List[str] = []
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError(f"Invalid allow-list entry: {entry!r}")
        candidate = entry.strip()
        if parse_endpoint_entry(candidate) is None:
            raise ValueError(f"Invalid allow-list entry '{candidate}': could not parse a hostname")
        normalised.append(candidate)
    return normalised


def invalidate_cache(tool_id: Optional[str] = None) -> None:
    """Invalidate the effective-ranges cache for one tool or all tools."""
    with _cache_lock:
        if tool_id is None:
            _cache.clear()
        else:
            _cache.pop(tool_id, None)


def _get_or_seed_policy_ranges(tool_id: str) -> List[str]:
    """Return the DB-stored entries for ``tool_id``, seeding from the
    ``<TOOL_ID>_ALLOWED_IPS`` env var (persisted immediately) if no row
    exists yet.

    An empty list stored in the DB (as opposed to no row at all) is a valid,
    deliberate admin choice and is returned as-is without re-seeding.
    """
    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        policy = (
            db.query(ToolSecurityPolicy)
            .filter(ToolSecurityPolicy.tool_id == tool_id)
            .first()
        )
        if policy is not None:
            if not policy.enabled:
                return []
            return list(policy.allowed_ip_ranges or [])

        # No row yet: seed from env (or blank) and persist so the DB becomes
        # the single source of truth for every subsequent read/write.
        seed = _env_seed_entries(tool_id)
        policy = ToolSecurityPolicy(tool_id=tool_id, allowed_ip_ranges=seed, enabled=True)
        db.add(policy)
        db.flush()
        logger.info(
            "[SSRF-POLICY] Seeded new policy for %s from env (%d entries) and saved to DB",
            tool_id,
            len(seed),
        )
        return list(seed)


def get_effective_blocked_ranges(tool_id: str = HTTP_REQUEST_TOOL_ID) -> List[str]:
    """Return the effective allow-list entries for ``tool_id``.

    On first access for a ``tool_id`` with no DB row yet, this seeds the
    policy from the ``<TOOL_ID>_ALLOWED_IPS`` env var (blank/unset -> ``[]``,
    i.e. fail-closed) and persists it immediately, so the database becomes
    the single source of truth from then on. Admins can freely add/remove
    entries afterwards through the existing CRUD API. Cached per ``tool_id``
    for a short TTL.

    Args:
        tool_id: Canonical tool identifier (defaults to ``HTTP_REQUEST``).

    Returns:
        List of allow-list entries currently in effect for ``tool_id``.
    """
    now = time.time()
    with _cache_lock:
        cached = _cache.get(tool_id)
        if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

    try:
        effective = _get_or_seed_policy_ranges(tool_id)
    except Exception as exc:  # noqa: BLE001 - fail closed, never silently allow-all
        logger.warning(
            "[SSRF-POLICY] Failed to load/seed policy for %s, failing closed: %s",
            tool_id,
            exc,
        )
        effective = []

    with _cache_lock:
        _cache[tool_id] = (now, effective)
    return effective


def list_policies() -> List[dict]:
    """Return all stored tool security policies as dictionaries."""
    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        return [p.to_dict() for p in db.query(ToolSecurityPolicy).all()]


def get_policy(tool_id: str) -> Optional[dict]:
    """Return a single tool security policy, or ``None`` if it does not exist."""
    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        policy = (
            db.query(ToolSecurityPolicy)
            .filter(ToolSecurityPolicy.tool_id == tool_id)
            .first()
        )
        return policy.to_dict() if policy else None


def upsert_policy(
    tool_id: str, allowed_ip_ranges: List[str], enabled: bool = True
) -> dict:
    """Create or update the policy for ``tool_id``.

    Args:
        tool_id: Canonical tool identifier.
        allowed_ip_ranges: Allow-list entries to save (validated first).
        enabled: Whether the policy is active.

    Returns:
        The stored policy as a dictionary.

    Raises:
        ValueError: If any entry is invalid.
    """
    entries = validate_allow_entries(allowed_ip_ranges)

    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        policy = (
            db.query(ToolSecurityPolicy)
            .filter(ToolSecurityPolicy.tool_id == tool_id)
            .first()
        )
        if policy:
            policy.allowed_ip_ranges = entries
            policy.enabled = enabled
        else:
            policy = ToolSecurityPolicy(
                tool_id=tool_id, allowed_ip_ranges=entries, enabled=enabled
            )
            db.add(policy)
        db.flush()
        result = policy.to_dict()

    invalidate_cache(tool_id)
    return result


def add_ip(tool_id: str, ip_or_cidr: str) -> dict:
    """Add a single allow-list entry to the policy for ``tool_id``.

    Creates the policy (seeded from the ``<TOOL_ID>_ALLOWED_IPS`` env var, or
    blank if unset) if it does not exist yet. No-op if the entry is already
    present.

    Raises:
        ValueError: If ``ip_or_cidr`` cannot be parsed into a hostname.
    """
    (normalised,) = validate_allow_entries([ip_or_cidr])

    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        policy = (
            db.query(ToolSecurityPolicy)
            .filter(ToolSecurityPolicy.tool_id == tool_id)
            .first()
        )
        if policy:
            entries = list(policy.allowed_ip_ranges or [])
            if normalised not in entries:
                entries.append(normalised)
                policy.allowed_ip_ranges = entries
        else:
            entries = _env_seed_entries(tool_id)
            if normalised not in entries:
                entries.append(normalised)
            policy = ToolSecurityPolicy(
                tool_id=tool_id, allowed_ip_ranges=entries, enabled=True
            )
            db.add(policy)
        db.flush()
        result = policy.to_dict()

    invalidate_cache(tool_id)
    return result


def remove_ip(tool_id: str, ip_or_cidr: str) -> dict:
    """Remove a single allow-list entry from the policy for ``tool_id``.

    Creates the policy (seeded from the ``<TOOL_ID>_ALLOWED_IPS`` env var, or
    blank if unset) if it does not exist yet, so a seeded entry can be
    explicitly removed on first use.

    Raises:
        ValueError: If ``ip_or_cidr`` cannot be parsed into a hostname.
    """
    (normalised,) = validate_allow_entries([ip_or_cidr])

    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        policy = (
            db.query(ToolSecurityPolicy)
            .filter(ToolSecurityPolicy.tool_id == tool_id)
            .first()
        )
        if policy:
            entries = [r for r in (policy.allowed_ip_ranges or []) if r != normalised]
            policy.allowed_ip_ranges = entries
        else:
            entries = [r for r in _env_seed_entries(tool_id) if r != normalised]
            policy = ToolSecurityPolicy(
                tool_id=tool_id, allowed_ip_ranges=entries, enabled=True
            )
            db.add(policy)
        db.flush()
        result = policy.to_dict()

    invalidate_cache(tool_id)
    return result


def bulk_upsert(policies: Dict[str, List[str]]) -> List[dict]:
    """Create or update multiple policies from a ``{tool_id: [entries]}`` map.

    All entries are validated before any write. Each affected policy is enabled.

    Raises:
        ValueError: If any entry is invalid.
    """
    validated = {tid: validate_allow_entries(entries) for tid, entries in policies.items()}

    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    results: List[dict] = []
    with get_db() as db:
        for tool_id, entries in validated.items():
            policy = (
                db.query(ToolSecurityPolicy)
                .filter(ToolSecurityPolicy.tool_id == tool_id)
                .first()
            )
            if policy:
                policy.allowed_ip_ranges = entries
                policy.enabled = True
            else:
                policy = ToolSecurityPolicy(
                    tool_id=tool_id, allowed_ip_ranges=entries, enabled=True
                )
                db.add(policy)
            db.flush()
            results.append(policy.to_dict())

    invalidate_cache()
    return results


def delete_policy(tool_id: str) -> bool:
    """Delete the policy for ``tool_id``.

    Returns:
        ``True`` if a policy was deleted, ``False`` if none existed.
    """
    from backend.models.configuration.tool_security_policy import ToolSecurityPolicy
    from backend.services.database import get_db

    with get_db() as db:
        policy = (
            db.query(ToolSecurityPolicy)
            .filter(ToolSecurityPolicy.tool_id == tool_id)
            .first()
        )
        if not policy:
            return False
        db.delete(policy)

    invalidate_cache(tool_id)
    return True
