"""Scope registry for PAT (Personal Access Token) access control.

This module defines the canonical catalogue of valid permission scopes.
Scope strings are validated against this registry at token creation and
update time. No DB round-trip is required — the registry lives in memory.
"""

import re
from typing import FrozenSet, List


# ---------------------------------------------------------------------------
# Regex pattern for named-resource scopes, e.g. "workflow:my-flow:execute"
# <name> must be non-empty, no colons, no asterisks.
# ---------------------------------------------------------------------------
NAMED_RESOURCE_PATTERN = re.compile(
    r"^(workflow|document|datasource|execution|memory|evaluation):[^:*]+:(read|write|execute)$"
)


# ---------------------------------------------------------------------------
# Static catalogue — all valid wildcard / super-scopes
# ---------------------------------------------------------------------------
VALID_SCOPES: FrozenSet[str] = frozenset(
    [
        # Workflow
        "workflow:*:read",
        "workflow:*:execute",
        "workflow:*:write",
        # Document
        "document:*:read",
        "document:*:write",
        # Datasource
        "datasource:*:read",
        "datasource:*:write",
        # Execution
        "execution:*:read",
        "execution:*:write",
        # Memory
        "memory:*:read",
        "memory:*:write",
        # Evaluation
        "evaluation:*:read",
        "evaluation:*:write",
        # Admin API scopes (read/write across all resources)
        "api:*:read",
        "api:*:write",
        # Super-scope (admin-only, implies everything)
        "api:*",
    ]
)

# Scopes that only admins can assign to tokens they create
ADMIN_ONLY_SCOPES: FrozenSet[str] = frozenset(
    [
        "api:*",
        "api:*:read",
        "api:*:write",
        "workflow:*:write",
        "document:*:read",
        "document:*:write",
        "datasource:*:read",
        "datasource:*:write",
        "execution:*:read",
        "execution:*:write",
        "memory:*:read",
        "memory:*:write",
        "evaluation:*:read",
        "evaluation:*:write",
    ]
)

# Scopes a non-admin user can self-assign (wildcard variants)
USER_CEILING_SCOPES: FrozenSet[str] = frozenset(
    [
        "workflow:*:read",
        "workflow:*:execute",
        # Named-resource variants are validated dynamically (see is_admin_only_scope)
    ]
)

# ---------------------------------------------------------------------------
# Scope metadata for the /available-scopes endpoint
# ---------------------------------------------------------------------------
_SCOPE_DEFINITIONS = [
    {
        "scope": "workflow:*:execute",
        "label": "Workflow — Execute All",
        "description": "Trigger executions on all accessible workflows",
        "resource": "workflow",
        "action": "execute",
        "admin_only": False,
    },
    {
        "scope": "workflow:*:read",
        "label": "Workflow — Read All",
        "description": "Read workflow definitions and view execution history for all accessible workflows",
        "resource": "workflow",
        "action": "read",
        "admin_only": False,
    },
    {
        "scope": "workflow:*:write",
        "label": "Workflow — Write All",
        "description": "Create, edit, and delete workflow definitions",
        "resource": "workflow",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "document:*:read",
        "label": "Documents — Read",
        "description": "Read documents and search document collections",
        "resource": "document",
        "action": "read",
        "admin_only": True,
    },
    {
        "scope": "document:*:write",
        "label": "Documents — Write",
        "description": "Upload, update, and delete documents",
        "resource": "document",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "datasource:*:read",
        "label": "Data Sources — Read",
        "description": "Read data source configurations",
        "resource": "datasource",
        "action": "read",
        "admin_only": True,
    },
    {
        "scope": "datasource:*:write",
        "label": "Data Sources — Write",
        "description": "Create, update, and delete data source configurations",
        "resource": "datasource",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "execution:*:read",
        "label": "Execution — Read",
        "description": "Read execution history, trace data, and checkpoint state",
        "resource": "execution",
        "action": "read",
        "admin_only": True,
    },
    {
        "scope": "execution:*:write",
        "label": "Execution — Write",
        "description": "Pause, resume, cancel, and stop workflow executions",
        "resource": "execution",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "memory:*:read",
        "label": "Memory — Read",
        "description": "Read conversation memory",
        "resource": "memory",
        "action": "read",
        "admin_only": True,
    },
    {
        "scope": "memory:*:write",
        "label": "Memory — Write",
        "description": "Create and delete conversation memory",
        "resource": "memory",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "evaluation:*:read",
        "label": "Evaluation — Read",
        "description": "Read evaluation datasets, runs, and results",
        "resource": "evaluation",
        "action": "read",
        "admin_only": True,
    },
    {
        "scope": "evaluation:*:write",
        "label": "Evaluation — Write",
        "description": "Create, modify, and delete evaluation datasets and runs",
        "resource": "evaluation",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "api:*:read",
        "label": "API — Read All",
        "description": "Read access to all API endpoints across all resources (admin-only)",
        "resource": "api",
        "action": "read",
        "admin_only": True,
    },
    {
        "scope": "api:*:write",
        "label": "API — Write All",
        "description": "Write and execute access to all API endpoints across all resources (admin-only)",
        "resource": "api",
        "action": "write",
        "admin_only": True,
    },
    {
        "scope": "api:*",
        "label": "Full API Access",
        "description": "Full access to all platform API actions (admin-only)",
        "resource": "api",
        "action": "*",
        "admin_only": True,
    },
]


def is_valid_scope(scope: str) -> bool:
    """Return True if scope is in the static registry or matches the named-resource pattern."""
    if scope in VALID_SCOPES:
        return True
    return bool(NAMED_RESOURCE_PATTERN.match(scope))


def is_admin_only_scope(scope: str) -> bool:
    """Return True if scope can only be granted by an admin.

    Rules:
    - ``api:*``, ``api:*:read``, ``api:*:write`` are always admin-only.
    - Any non-workflow resource scope is admin-only (document, datasource,
      execution, memory, evaluation).
    - ``workflow:*:write`` is admin-only.
    - ``workflow:<name>:write`` is admin-only.
    - All other valid scopes (workflow:*:read, workflow:*:execute,
      workflow:<name>:read, workflow:<name>:execute) are user-grantable.
    """
    if scope in ("api:*", "api:*:read", "api:*:write"):
        return True
    parts = scope.split(":")
    if not parts:
        return True
    resource = parts[0]
    if resource != "workflow":
        return True
    # workflow:*:write
    if scope == "workflow:*:write":
        return True
    # workflow:<name>:write
    if len(parts) == 3 and parts[2] == "write":
        return True
    return False


def validate_scopes(scopes: List[str]) -> List[str]:
    """Validate a list of scope strings against the registry.

    Args:
        scopes: List of scope strings to validate

    Returns:
        The same list if all scopes are valid

    Raises:
        ValueError: If any scope string is not in the catalogue
    """
    invalid = [s for s in scopes if not is_valid_scope(s)]
    if invalid:
        raise ValueError(
            f"Unknown scopes: {invalid}. "
            "Scopes must be from the scope registry (e.g. workflow:*:execute)."
        )
    return scopes


def get_all_scope_definitions() -> List[dict]:
    """Return the full list of scope definition dicts."""
    return list(_SCOPE_DEFINITIONS)


def get_user_available_scope_definitions(is_admin: bool, restrict_to_workflow: bool) -> List[dict]:
    """Return scope definitions visible to the given user role.

    Args:
        is_admin: Whether the user holds admin privileges
        restrict_to_workflow: Whether the admin restriction toggle is ON

    Returns:
        Filtered list of scope definition dicts
    """
    if is_admin:
        return list(_SCOPE_DEFINITIONS)
    if restrict_to_workflow:
        return [s for s in _SCOPE_DEFINITIONS if s["resource"] == "workflow"]
    return [s for s in _SCOPE_DEFINITIONS if not s["admin_only"]]
