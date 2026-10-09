"""Global feature flags for capabilities that are not yet generally available.

Flags are resolved once at import time so a single environment variable gates
every entry point to a capability: API routes, node executors, checkpoint
handlers and agent tools alike. This module deliberately has no imports beyond
the standard library so it is safe to import from ``backend.app`` before the
heavier service packages are loaded.
"""

import os


def _env_flag(name: str, default: str = "false") -> bool:
    """Read a boolean environment variable."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# Email capability: EMAIL_SEND nodes, email agent tools, email checkpoints and
# the /api/email routes. Shipped disabled while the feature is completed.
EMAIL_FEATURE_ENABLED: bool = _env_flag("EMAIL_FEATURE_ENABLED")

EMAIL_COMING_SOON_MESSAGE = (
    "Email is coming soon and is currently unavailable. "
    "Set EMAIL_FEATURE_ENABLED=true to enable it."
)
