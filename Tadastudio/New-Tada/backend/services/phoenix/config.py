from __future__ import annotations

import dataclasses
import os
import time
from typing import Any, Dict, Optional, Tuple

from backend.services.config import get_logger

logger = get_logger(__name__)

# Cache: project_name -> (project_id, timestamp)
_project_id_cache: Dict[str, Tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclasses.dataclass
class PhoenixConfig:
    """Typed configuration for Arize Phoenix observability."""

    enabled: bool
    endpoint: str
    project_name: str
    api_key: Optional[str]
    ui_url: str
    eval_penalty_enabled: bool = False
    eval_model_deployment_id: Optional[str] = None
    eval_faithfulness_enabled: bool = True
    eval_tool_selection_enabled: bool = True
    eval_llm_judge_enabled: bool = False

    @property
    def api_base_url(self) -> str:
        """Resolve the base URL for server-side Phoenix API calls.

        Prefers ``endpoint`` (internal/reachable from backend) over ``ui_url``
        (which may be an external browser-only URL).
        """
        if self.endpoint:
            return self.endpoint.removesuffix("/v1/traces").rstrip("/")
        if self.ui_url:
            return self.ui_url
        return ""

    @property
    def client_base_url(self) -> str:
        """Resolve the base URL for browser-facing Phoenix UI links.

        Returns ``ui_url`` when set, otherwise derives from ``endpoint``
        by stripping the ``/v1/traces`` collector suffix.
        """
        if self.ui_url:
            return self.ui_url
        if self.endpoint:
            return self.endpoint.removesuffix("/v1/traces").rstrip("/")
        return ""


def _get_setting(key: str, default: str = "") -> str:
    """Read a Phoenix setting from the DB system_settings table, falling back to env var.

    The settings UI persists values to the DB; env vars serve as the
    initial/default source.  This mirrors the pattern used by
    ``ConfigService._get_db_setting`` so that runtime toggles (e.g.
    disabling Phoenix in the UI) take effect without a restart.
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


def get_phoenix_config() -> PhoenixConfig:
    """Read Phoenix configuration from DB settings, falling back to env vars."""
    enabled = _get_setting("PHOENIX_ENABLED", "false").lower() == "true"
    config = PhoenixConfig(
        enabled=enabled,
        endpoint=_get_setting("PHOENIX_ENDPOINT", ""),
        project_name=_get_setting("PHOENIX_PROJECT_NAME", "agentic-studio"),
        api_key=_get_setting("PHOENIX_API_KEY", "") or None,
        ui_url=_get_setting("PHOENIX_UI_URL", ""),
        eval_penalty_enabled=_get_setting(
            "PHOENIX_EVAL_PENALTY_ENABLED", "false"
        ).lower()
        == "true",
        eval_model_deployment_id=_get_setting("PHOENIX_EVAL_MODEL_DEPLOYMENT_ID", "")
        or None,
        eval_faithfulness_enabled=_get_setting(
            "PHOENIX_EVAL_FAITHFULNESS_ENABLED", "true"
        ).lower()
        != "false",
        eval_tool_selection_enabled=_get_setting(
            "PHOENIX_EVAL_TOOL_SELECTION_ENABLED", "true"
        ).lower()
        != "false",
        eval_llm_judge_enabled=_get_setting(
            "PHOENIX_EVAL_LLM_JUDGE_ENABLED", "false"
        ).lower()
        == "true",
    )
    if enabled:
        logger.debug("Phoenix observability enabled, endpoint=%s", config.endpoint)
    return config


def get_phoenix_env_config() -> PhoenixConfig:
    """Read Phoenix configuration from environment variables only."""
    enabled = os.getenv("PHOENIX_ENABLED", "false").strip("'\"").lower() == "true"
    return PhoenixConfig(
        enabled=enabled,
        endpoint=os.getenv("PHOENIX_ENDPOINT", ""),
        project_name=os.getenv("PHOENIX_PROJECT_NAME", "agentic-studio"),
        api_key=os.getenv("PHOENIX_API_KEY", "") or None,
        ui_url=os.getenv("PHOENIX_UI_URL", ""),
        eval_penalty_enabled=os.getenv("PHOENIX_EVAL_PENALTY_ENABLED", "false")
        .strip("'\"")
        .lower()
        == "true",
        eval_model_deployment_id=os.getenv("PHOENIX_EVAL_MODEL_DEPLOYMENT_ID", "")
        or None,
        eval_faithfulness_enabled=os.getenv("PHOENIX_EVAL_FAITHFULNESS_ENABLED", "true")
        .strip("'\"")
        .lower()
        != "false",
        eval_tool_selection_enabled=os.getenv(
            "PHOENIX_EVAL_TOOL_SELECTION_ENABLED", "true"
        )
        .strip("'\"")
        .lower()
        != "false",
        eval_llm_judge_enabled=os.getenv("PHOENIX_EVAL_LLM_JUDGE_ENABLED", "false")
        .strip("'\"")
        .lower()
        == "true",
    )


def resolve_phoenix_config(override: Optional[Dict[str, Any]] = None) -> PhoenixConfig:
    """Merge an optional per-run override dict onto the global Phoenix config.

    Per-key, the override value wins when it is non-empty/non-None.
    ``enabled`` is ``True`` when *either* global or override enables it.
    It is only ``False`` when both global and override are effectively disabled.
    """
    base = get_phoenix_config()
    if not override:
        return base

    def _pick(key: str, default: Any = "") -> Any:
        """Return override value if truthy, else base value."""
        val = override.get(key)
        if val is not None and val != "":
            return val
        return getattr(base, key, default)

    # enabled logic: explicit per-run override wins; fall back to global.
    override_enabled = override.get("enabled")
    if override_enabled is not None:
        merged_enabled = bool(override_enabled)
    else:
        # override missing/None → inherit from global
        merged_enabled = base.enabled

    override_penalty = override.get("eval_penalty_enabled")
    if override_penalty is not None:
        merged_penalty = bool(override_penalty)
    else:
        merged_penalty = base.eval_penalty_enabled

    def _pick_bool(key: str, default: bool) -> bool:
        val = override.get(key)
        return bool(val) if val is not None else getattr(base, key, default)

    return PhoenixConfig(
        enabled=merged_enabled,
        endpoint=_pick("endpoint", ""),
        project_name=_pick("project_name", base.project_name),
        api_key=_pick("api_key", base.api_key),
        ui_url=_pick("ui_url", ""),
        eval_penalty_enabled=merged_penalty,
        eval_model_deployment_id=_pick(
            "eval_model_deployment_id", base.eval_model_deployment_id
        ),
        eval_faithfulness_enabled=_pick_bool("eval_faithfulness_enabled", True),
        eval_tool_selection_enabled=_pick_bool("eval_tool_selection_enabled", True),
        eval_llm_judge_enabled=_pick_bool("eval_llm_judge_enabled", False),
    )


def _client_headers(config: PhoenixConfig) -> Optional[Dict[str, str]]:
    """Build authentication headers for Phoenix API Client calls."""
    if config.api_key:
        return {"authorization": f"Bearer {config.api_key}"}
    return None


def resolve_project_id(
    project_name: str, config: Optional[PhoenixConfig] = None
) -> Optional[str]:
    """Resolve a Phoenix project name to its internal ID (best-effort, cached).

    Phoenix URLs use project IDs (e.g. ``UHJvamVjdDoy``), not names.
    This queries the Phoenix API to find the ID for a given project name,
    caching the result for 5 minutes.

    Returns ``None`` if Phoenix is unavailable or the project doesn't exist.
    """
    now = time.time()
    cached = _project_id_cache.get(project_name)
    if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    cfg = config or get_phoenix_config()
    api_base = cfg.api_base_url
    if not cfg.enabled or not api_base:
        return None

    try:
        from phoenix.client import Client

        client = Client(base_url=api_base, headers=_client_headers(cfg))
        project = client.projects.get(project_name=project_name)
        project_id = (
            project.get("id")
            if isinstance(project, dict)
            else getattr(project, "id", None)
        )
        if project_id:
            _project_id_cache[project_name] = (project_id, now)
            return project_id
    except Exception as exc:
        logger.debug(
            "Could not resolve Phoenix project ID for '%s': %s", project_name, exc
        )

    return None


def _project_path(project_name: str, config: PhoenixConfig) -> str:
    """Return the URL path segment for a project: ID if resolvable, else name."""
    project_id = resolve_project_id(project_name, config)
    return project_id if project_id else project_name


def build_phoenix_trace_ref_by_session(
    session_id: str,
    config: Optional[PhoenixConfig] = None,
) -> Optional[Dict[str, Any]]:
    """Build a Phoenix trace reference for a workflow execution by session id.

    Every workflow span is stamped with ``session.id == execution_id`` (see
    ``phoenix_workflow_context``).  This enumerates Phoenix projects and finds
    the project + trace that actually contain the spans — which may be the
    workflow-named project (normal case) or the ``default`` project when another
    SDK (e.g. Langfuse) owns the OTel provider and relocates the spans.

    Mirrors the standalone ``test_phoenix_trace_by_session.py`` script so the
    backend produces the same deep-link.  Best-effort and non-fatal.

    Returns a ref dict ``{"project", "trace_id", "path"}`` (where ``project`` is
    Phoenix's encoded project ID and ``path`` is a relative UI path), or
    ``None`` if Phoenix is unavailable or the spans are not yet ingested.
    """
    cfg = config or get_phoenix_config()
    api_base = cfg.api_base_url
    if not cfg.enabled or not api_base or not session_id:
        return None

    try:
        from phoenix.client import Client

        client = Client(base_url=api_base, headers=_client_headers(cfg))

        try:
            projects = list(client.projects.list() or [])
        except Exception as exc:
            logger.debug("Could not list Phoenix projects: %s", exc)
            return None

        for proj in projects:
            proj_name = (
                proj.get("name")
                if isinstance(proj, dict)
                else getattr(proj, "name", None)
            )
            proj_id = (
                proj.get("id")
                if isinstance(proj, dict)
                else getattr(proj, "id", None)
            )
            if not proj_name:
                continue

            # Query spans for this session, filtering server-side; fall back to
            # pulling recent spans and filtering in Python.
            try:
                df = client.spans.get_spans_dataframe(
                    project_identifier=str(proj_name),
                    filter_condition=(
                        f"attributes['session.id'] == '{session_id}'"
                    ),
                    limit=50,
                )
            except Exception:
                try:
                    df = client.spans.get_spans_dataframe(
                        project_identifier=str(proj_name), limit=500
                    )
                except Exception:
                    continue

            if df is None or len(df) == 0:
                continue

            # Locate the session column (varies by Phoenix version).
            session_col = None
            for cand in (
                "attributes.session.id",
                "session.id",
                "attributes.session_id",
            ):
                if cand in df.columns:
                    session_col = cand
                    break

            if session_col is not None:
                hit = df[df[session_col] == session_id]
            else:
                hit = df.iloc[0:0]
                for col in df.columns:
                    if "session" in col.lower():
                        sub = df[df[col].astype(str) == session_id]
                        if len(sub) > 0:
                            hit = sub
                            break

            if len(hit) == 0:
                continue

            # Grab the trace id from the matching rows.
            trace_col = None
            for cand in ("context.trace_id", "trace_id"):
                if cand in hit.columns:
                    trace_col = cand
                    break
            if not trace_col:
                continue
            trace_id = str(hit.iloc[0][trace_col])

            path_seg = str(proj_id) if proj_id else str(proj_name)
            rel_path = f"/projects/{path_seg}/traces/{trace_id}"
            ui_base = cfg.client_base_url.rstrip("/")
            return {
                "project": path_seg,
                "trace_id": trace_id,
                "path": rel_path,
                "url": f"{ui_base}{rel_path}" if ui_base else None,
            }
    except Exception as exc:
        logger.debug(
            "Could not build Phoenix trace ref for session '%s': %s",
            session_id,
            exc,
        )

    return None


def build_project_path(
    project_name: str, config: Optional[PhoenixConfig] = None
) -> str:
    """Build a Phoenix UI relative path for a project.

    Returns a path like ``/projects/<id>`` (or ``/projects/<name>`` when the
    ID cannot be resolved).  The caller or frontend prepends the Phoenix UI
    base URL so that stored references survive URL changes.
    """
    cfg = config or get_phoenix_config()
    return f"/projects/{_project_path(project_name, cfg)}"


def build_trace_path(
    project_name: str,
    trace_id: str,
    config: Optional[PhoenixConfig] = None,
) -> str:
    """Build a Phoenix UI relative path to a specific trace.

    Returns a path like ``/projects/<id>/traces/<trace_id>``.
    """
    cfg = config or get_phoenix_config()
    return f"/projects/{_project_path(project_name, cfg)}/traces/{trace_id}"


def build_project_url(
    project_name: str, config: Optional[PhoenixConfig] = None
) -> Optional[str]:
    """Build a full Phoenix UI URL for a project.

    Used for on-the-fly URL construction (e.g. config API responses).
    For persistent storage, use :func:`build_project_path` instead.
    """
    cfg = config or get_phoenix_config()
    if not cfg.client_base_url:
        return None
    return f"{cfg.client_base_url}{build_project_path(project_name, cfg)}"


def build_trace_url(
    project_name: str,
    trace_id: str,
    config: Optional[PhoenixConfig] = None,
) -> Optional[str]:
    """Build a full Phoenix UI deep-link to a specific trace.

    Used for on-the-fly URL construction (e.g. config API responses).
    For persistent storage, use :func:`build_trace_path` instead.
    """
    cfg = config or get_phoenix_config()
    if not cfg.client_base_url:
        return None
    return f"{cfg.client_base_url}{build_trace_path(project_name, trace_id, cfg)}"
