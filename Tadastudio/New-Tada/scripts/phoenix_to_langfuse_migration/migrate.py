"""End-to-end Phoenix -> Langfuse trace migration.

Single script that performs the full migration in three stages:

    1. EXPORT  - pull every span from every Phoenix project into a temporary
                 pickle file (fast, typed, no extra dependencies).
    2. MIGRATE - replay those spans into Langfuse via its OpenTelemetry
                 ingestion endpoint, preserving original trace/span ids,
                 parent links, timestamps and every attribute.
    3. VERIFY  - confirm that every Phoenix trace id now exists in Langfuse.

All configuration comes from environment variables (see README.md).

Run:
    python scripts/phoenix_to_langfuse_migration/migrate.py
"""

from __future__ import annotations

import ast
import base64
import json
import os
import sys
import tempfile
import time

import httpx
import pandas as pd
from phoenix.client import Client

# ---------------------------------------------------------------------------
# CONFIGURATION (all via environment variables)
# ---------------------------------------------------------------------------

# --- Phoenix (source) ---
_raw_phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT", "").strip()
# The app may set PHOENIX_ENDPOINT to the OTel collector path (.../v1/traces);
# strip it so we get the bare base url the Phoenix client / GraphQL API need.
PHOENIX_BASE_URL = _raw_phoenix_endpoint.removesuffix("/v1/traces").rstrip("/")
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "").strip()

# --- Langfuse (destination) ---
LANGFUSE_HOST = os.getenv("MIGRATION_LANGFUSE_HOST", "").strip().rstrip("/")
LANGFUSE_PUBLIC_KEY = os.getenv("MIGRATION_LANGFUSE_PUBLIC_KEY", "").strip()
LANGFUSE_SECRET_KEY = os.getenv("MIGRATION_LANGFUSE_SECRET_KEY", "").strip()

# --- Behaviour ---
BATCH_SIZE = int(os.getenv("MIGRATION_BATCH_SIZE", "200"))
BATCH_DELAY_SECONDS = float(os.getenv("MIGRATION_BATCH_DELAY_SECONDS", "0.2"))

# Langfuse ingests OTLP spans asynchronously, so verification polls with backoff.
VERIFY_MAX_RETRIES = int(os.getenv("MIGRATION_VERIFY_MAX_RETRIES", "10"))
VERIFY_RETRY_DELAY_SECONDS = float(
    os.getenv("MIGRATION_VERIFY_RETRY_DELAY_SECONDS", "20")
)

OTLP_URL = f"{LANGFUSE_HOST}/api/public/otel/v1/traces"
_LF_AUTH = base64.b64encode(
    f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
).decode()
_LF_HEADERS = {
    "Authorization": f"Basic {_LF_AUTH}",
    "Content-Type": "application/json",
}


def _require_config() -> None:
    """Fail fast if any required configuration is missing."""
    missing = []
    if not PHOENIX_BASE_URL:
        missing.append("PHOENIX_ENDPOINT")
    if not LANGFUSE_HOST:
        missing.append("MIGRATION_LANGFUSE_HOST")
    if not LANGFUSE_PUBLIC_KEY:
        missing.append("MIGRATION_LANGFUSE_PUBLIC_KEY")
    if not LANGFUSE_SECRET_KEY:
        missing.append("MIGRATION_LANGFUSE_SECRET_KEY")
    if missing:
        print(f"ERROR: missing required env vars: {', '.join(missing)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# STAGE 1 - EXPORT (Phoenix -> temp pickle)
# ---------------------------------------------------------------------------

def _phoenix_client() -> Client:
    if PHOENIX_API_KEY:
        return Client(base_url=PHOENIX_BASE_URL, api_key=PHOENIX_API_KEY)
    return Client(base_url=PHOENIX_BASE_URL)


def _list_projects() -> list[str]:
    """Return all Phoenix project names via the GraphQL API."""
    headers = {}
    if PHOENIX_API_KEY:
        headers["Authorization"] = f"Bearer {PHOENIX_API_KEY}"
    try:
        resp = httpx.post(
            f"{PHOENIX_BASE_URL}/graphql",
            json={"query": "{ projects { edges { node { name } } } }"},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        projects = [
            e["node"]["name"]
            for e in resp.json()["data"]["projects"]["edges"]
        ]
        print(f"  found {len(projects)} project(s): {projects}")
        return projects
    except Exception as exc:
        print(f"  could not list projects ({exc}); using 'default'.")
        return ["default"]


def export_to_pickle(path: str) -> int:
    """Export every span from every project to a pickle file. Returns span count."""
    print(f"[1/3] Exporting Phoenix spans from {PHOENIX_BASE_URL} ...")
    client = _phoenix_client()
    frames = []
    for project in _list_projects():
        try:
            df = client.spans.get_spans_dataframe(project_identifier=project)
        except Exception as exc:
            print(f"    [error] {project}: {exc}")
            continue
        if df is None or df.empty:
            print(f"    [skip]  {project}: no spans")
            continue
        df = df.reset_index(drop=True)
        df.insert(0, "project_name", project)
        frames.append(df)
        print(f"    [ok]    {project}: {len(df)} spans")

    if not frames:
        print("  No spans found in any project. Nothing to migrate.")
        return 0

    out = pd.concat(frames, ignore_index=True)
    out.to_pickle(path)
    print(f"  wrote {len(out)} spans -> {path}")
    return len(out)


# ---------------------------------------------------------------------------
# STAGE 2 - MIGRATE (pickle -> Langfuse via OTLP)
# ---------------------------------------------------------------------------

def _val(row, col):
    """Return a clean value or None for NaN/missing columns."""
    if col not in row:
        return None
    v = row[col]
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v


def _parse(v):
    """Parse a python/JSON literal string; fall back to the raw value."""
    if not isinstance(v, str):
        return v
    for parser in (ast.literal_eval, json.loads):
        try:
            return parser(v)
        except Exception:
            continue
    return v


def _messages(v):
    """Remap Phoenix message dicts (message.role/content) -> role/content."""
    parsed = _parse(v)
    if isinstance(parsed, list):
        out = []
        for m in parsed:
            if isinstance(m, dict):
                out.append({
                    "role": m.get("message.role", m.get("role")),
                    "content": m.get("message.content", m.get("content")),
                })
            else:
                out.append(m)
        return out
    return parsed


def _nanos(v):
    """Parse a timestamp into unix nanoseconds."""
    if v is None:
        return None
    ts = pd.to_datetime(v, utc=True, errors="coerce")
    if pd.isna(ts):
        return None
    return int(ts.value)


def _hex_to_b64(hex_str, size):
    """Convert a hex id to base64 bytes as required by OTLP/JSON."""
    b = bytes.fromhex(hex_str)
    if len(b) != size:
        b = b.rjust(size, b"\x00")[:size]
    return base64.b64encode(b).decode()


def _attr(key, value):
    """Build one OTLP KeyValue with the right typed value."""
    if isinstance(value, bool):
        val = {"boolValue": value}
    elif isinstance(value, int):
        val = {"intValue": str(value)}
    elif isinstance(value, float):
        val = {"doubleValue": value}
    elif isinstance(value, str):
        val = {"stringValue": value}
    else:
        val = {"stringValue": json.dumps(value, default=str)}
    return {"key": key, "value": val}


def _as_text(v):
    """Serialise dict/list values to JSON, leave scalars as-is."""
    if isinstance(v, (dict, list)):
        return json.dumps(v, default=str, ensure_ascii=False)
    return v


def _build_span(s, root):
    """Build one OTLP span dict from a Phoenix span row."""
    kind = _val(s, "attributes.openinference.span.kind") or _val(s, "span_kind")
    is_llm = kind == "LLM"

    attrs = [_attr("langfuse.observation.type",
                   "generation" if is_llm else "span")]

    if is_llm:
        model = _val(s, "attributes.llm.model_name")
        if model:
            attrs.append(_attr("langfuse.observation.model.name", model))
        inp = _messages(_val(s, "attributes.llm.input_messages")) or _parse(
            _val(s, "attributes.input.value")
        )
        usage = {
            "input": _val(s, "attributes.llm.token_count.prompt"),
            "output": _val(s, "attributes.llm.token_count.completion"),
            "total": _val(s, "attributes.llm.token_count.total"),
        }
        usage = {k: int(v) for k, v in usage.items() if v is not None}
        if usage:
            attrs.append(_attr("langfuse.observation.usage_details",
                               json.dumps(usage)))
    else:
        inp = _parse(_val(s, "attributes.input.value"))

    out = _parse(_val(s, "attributes.output.value"))
    if inp is not None:
        attrs.append(_attr("langfuse.observation.input", _as_text(inp)))
    if out is not None:
        attrs.append(_attr("langfuse.observation.output", _as_text(out)))

    level = "ERROR" if _val(s, "status_code") == "ERROR" else "DEFAULT"
    attrs.append(_attr("langfuse.observation.level", level))
    if _val(s, "status_message"):
        attrs.append(_attr("langfuse.observation.status_message",
                           str(_val(s, "status_message"))))

    # Trace-level fields (only on the root span)
    if s is root:
        attrs.append(_attr("langfuse.trace.name", str(_val(root, "name"))))
        if inp is not None:
            attrs.append(_attr("langfuse.trace.input", _as_text(inp)))
        if out is not None:
            attrs.append(_attr("langfuse.trace.output", _as_text(out)))
        if _val(root, "attributes.session.id"):
            attrs.append(_attr("langfuse.session.id",
                               str(_val(root, "attributes.session.id"))))
        if _val(root, "attributes.user.id"):
            attrs.append(_attr("langfuse.user.id",
                               str(_val(root, "attributes.user.id"))))

    # Catch-all: dump EVERY attributes.* column into metadata
    for col in s:
        if not col.startswith("attributes."):
            continue
        cv = _val(s, col)
        if cv is None:
            continue
        key = "langfuse.observation.metadata." + col[len("attributes."):]
        attrs.append(_attr(key, _as_text(_parse(cv)) if isinstance(cv, str)
                           else cv))

    status_code = {"OK": 1, "ERROR": 2}.get(_val(s, "status_code"), 0)
    span = {
        "traceId": _hex_to_b64(str(_val(s, "context.trace_id")), 16),
        "spanId": _hex_to_b64(str(_val(s, "context.span_id")), 8),
        "name": str(_val(s, "name")),
        "kind": 1,
        "startTimeUnixNano": str(_nanos(_val(s, "start_time")) or 0),
        "endTimeUnixNano": str(_nanos(_val(s, "end_time")) or 0),
        "attributes": attrs,
        "status": {"code": status_code},
    }
    parent = _val(s, "parent_id")
    if parent:
        span["parentSpanId"] = _hex_to_b64(str(parent), 8)
    return span


def _send(spans):
    payload = {
        "resourceSpans": [{
            "resource": {"attributes": [
                _attr("service.name", "phoenix-migration")
            ]},
            "scopeSpans": [{
                "scope": {"name": "phoenix-migration"},
                "spans": spans,
            }],
        }]
    }
    resp = httpx.post(OTLP_URL, headers=_LF_HEADERS, json=payload, timeout=60)
    resp.raise_for_status()


def migrate_from_pickle(path: str) -> int:
    """Read the pickle export and ingest all spans into Langfuse."""
    print(f"[2/3] Migrating spans into Langfuse at {LANGFUSE_HOST} ...")
    df = pd.read_pickle(path)

    all_spans, traces = [], 0
    for _trace_id, group in df.groupby("context.trace_id"):
        rows = group.sort_values("start_time").to_dict("records")
        root = next((r for r in rows if _val(r, "parent_id") is None), rows[0])
        for r in rows:
            all_spans.append(_build_span(r, root))
        traces += 1

    sent = 0
    for i in range(0, len(all_spans), BATCH_SIZE):
        batch = all_spans[i:i + BATCH_SIZE]
        _send(batch)
        sent += len(batch)
        print(f"    sent {sent}/{len(all_spans)} spans")
        if BATCH_DELAY_SECONDS and i + BATCH_SIZE < len(all_spans):
            time.sleep(BATCH_DELAY_SECONDS)

    print(f"  migrated {traces} traces, {sent} spans.")
    return traces


# ---------------------------------------------------------------------------
# STAGE 3 - VERIFY (Phoenix trace ids present in Langfuse)
# ---------------------------------------------------------------------------

def _normalise_id(tid):
    """Convert a base64 trace id to hex; leave hex ids unchanged."""
    try:
        return base64.b64decode(tid, validate=True).hex()
    except Exception:
        return tid


def _langfuse_trace_ids() -> set[str]:
    ids = set()
    page = 1
    while True:
        resp = httpx.get(
            f"{LANGFUSE_HOST}/api/public/traces",
            headers={"Authorization": f"Basic {_LF_AUTH}"},
            params={"page": page, "limit": 100},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        if not items:
            break
        ids.update(_normalise_id(str(t["id"])) for t in items)
        total_pages = data.get("meta", {}).get("totalPages", page)
        if page >= total_pages:
            break
        page += 1
    return ids


def verify(path: str) -> bool:
    """Confirm every Phoenix trace id exists in Langfuse. Returns True on match.

    Langfuse ingests OTLP spans asynchronously through a queue, so freshly
    migrated traces are not queryable immediately. Poll with a short backoff
    until all traces appear (or the retry budget is exhausted).
    """
    print("[3/3] Verifying migration ...")
    df = pd.read_pickle(path)
    phoenix_ids = set(df["context.trace_id"].astype(str))

    langfuse_ids: set[str] = set()
    missing = phoenix_ids
    for attempt in range(1, VERIFY_MAX_RETRIES + 1):
        langfuse_ids = _langfuse_trace_ids()
        missing = phoenix_ids - langfuse_ids
        if not missing:
            break
        if attempt < VERIFY_MAX_RETRIES:
            print(
                f"  attempt {attempt}: {len(missing)} traces not visible yet, "
                f"waiting {VERIFY_RETRY_DELAY_SECONDS}s for ingestion ..."
            )
            time.sleep(VERIFY_RETRY_DELAY_SECONDS)

    print(f"  Phoenix : {len(phoenix_ids)} traces, {len(df)} spans")
    print(f"  Langfuse: {len(langfuse_ids)} traces")

    if not missing:
        print("  OK: every Phoenix trace is present in Langfuse.")
        return True
    print(f"  MISSING {len(missing)} traces not found in Langfuse:")
    for t in sorted(missing):
        print(f"    - {t}")
    return False


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    _require_config()

    # Temp pickle file, auto-deleted at the end.
    fd, pickle_path = tempfile.mkstemp(suffix=".pkl", prefix="phoenix_")
    os.close(fd)

    try:
        span_count = export_to_pickle(pickle_path)
        if span_count == 0:
            sys.exit(0)

        migrate_from_pickle(pickle_path)
        ok = verify(pickle_path)
        sys.exit(0 if ok else 2)
    finally:
        try:
            os.remove(pickle_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
