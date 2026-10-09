"""Configuration for Langfuse observability.

Reads settings from the DB ``system_settings`` table first (so the settings UI
can toggle Langfuse at runtime) and falls back to environment variables.

The values map onto the credentials the Langfuse SDK expects
(``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, ``LANGFUSE_BASE_URL``).
"""

from __future__ import annotations

import dataclasses
import os
from typing import Optional

from backend.services.config import get_logger

logger = get_logger(__name__)


@dataclasses.dataclass
class LangfuseConfig:
    """Typed configuration for Langfuse observability."""

    enabled: bool
    public_key: Optional[str]
    secret_key: Optional[str]
    host: str
    client_id: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        """True only when enabled and the minimum credentials/host exist.

        Both keys and a host are required for the Langfuse SDK to authenticate;
        without them Langfuse must stay inert so the pipeline is unaffected.
        """
        return bool(self.enabled and self.host and self.public_key and self.secret_key)

    def trace_url(self, trace_id: str) -> str:
        """Build a browser-facing deep-link to a trace in the Langfuse UI."""
        base = (self.host or "").rstrip("/")
        if not base or not trace_id:
            return ""
        return f"{base}/trace/{trace_id}"


def _get_setting(key: str, default: str = "") -> str:
    """Read a setting from the DB ``system_settings`` table, falling back to env.

    Mirrors the Phoenix pattern so runtime toggles take effect without a
    restart.  Any DB error (e.g. during startup) silently falls back to env.
    """
    try:
        from backend.services.database import get_db
        from sqlalchemy import text

        with get_db() as db:
            row = db.execute(
                text("SELECT value FROM system_settings WHERE key = :key"),
                {"key": key},
            ).fetchone()
            if row is not None and str(row[0]).strip():  # type: ignore[index]
                return str(row[0])  # type: ignore[index]
    except Exception:
        pass  # DB not available yet (startup) or table missing — fall back
    return os.getenv(key, default)


def get_langfuse_config() -> LangfuseConfig:
    """Read Langfuse configuration from DB settings, falling back to env vars."""
    enabled = _get_setting("LANGFUSE_ENABLED", "false").lower() == "true"

    # ``LANGFUSE_BASE_URL`` is what the Langfuse UI/SDK use; fall back to the
    # legacy ``LANGFUSE_HOST`` for backwards compatibility.
    host = (
        _get_setting("LANGFUSE_BASE_URL", "") or _get_setting("LANGFUSE_HOST", "")
    ).rstrip("/")

    config = LangfuseConfig(
        enabled=enabled,
        public_key=_get_setting("LANGFUSE_PUBLIC_KEY", "") or None,
        secret_key=_get_setting("LANGFUSE_SECRET_KEY", "") or None,
        host=host,
        client_id=_get_setting("LANGFUSE_CLIENT_ID", "") or None,
    )
    if enabled:
        logger.debug("Langfuse observability enabled, host=%s", config.host)
    return config


def get_langfuse_env_config() -> LangfuseConfig:
    """Read Langfuse configuration from environment variables only."""
    enabled = os.getenv("LANGFUSE_ENABLED", "false").strip("'\"").lower() == "true"
    host = (
        os.getenv("LANGFUSE_BASE_URL", "") or os.getenv("LANGFUSE_HOST", "")
    ).rstrip("/")

    return LangfuseConfig(
        enabled=enabled,
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "") or None,
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", "") or None,
        host=host,
        client_id=os.getenv("LANGFUSE_CLIENT_ID", "") or None,
    )
