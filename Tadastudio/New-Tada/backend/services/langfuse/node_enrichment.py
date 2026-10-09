"""Node-metadata enrichment for OpenInference auto-instrumentation spans.

OpenInference's LangChain instrumentor emits one CHAIN span per LangGraph
node, but names it by the opaque node ``uniq_id`` and carries none of TADA's
human-readable metadata.  This module restores that metadata *onto the native
auto span* using the same concurrency-safe ``ContextVar`` + ``SpanProcessor``
pattern proven in :mod:`backend.services.phoenix.project_routing`.

Flow::

    from backend.services.langfuse.node_enrichment import (
        set_current_node_metadata, reset_current_node_metadata,
    )

    token = set_current_node_metadata({node_uniq_id: {...}, ...})
    try:
        await app.astream(...)   # per-node spans get enriched at on_start
    finally:
        reset_current_node_metadata(token)

The ``NodeMetadataSpanProcessor`` must be registered on the active
``TracerProvider`` at startup — see :func:`get_node_metadata_span_processor`,
which is wired from the Langfuse bootstrap so it runs even when Phoenix is off.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Dict, Optional

from backend.services.config import get_logger

logger = get_logger(__name__)

# Max length for the truncated exception message stamped as ``exception.message``.
_EXC_MSG_MAXLEN = 500

# Reserved key in the node-metadata mapping that carries workflow-root metadata
# (graph name / execution id) used to stamp the Langfuse trace name on the root
# auto span.  Never collides with a node ``uniq_id``.
_ROOT_META_KEY = "__workflow_root__"

# Maps a guardrail ``Violation.category`` to the coarse block direction stamped
# as ``block.category``.  Unmapped categories (e.g. ``behavioral``,
# ``token_budget``, ``custom_filter``) fall back to their raw label so the
# attribute is never empty and never misleading.
_BLOCK_CATEGORY_MAP = {
    "input": "ingress",
    "output": "egress",
    "tool_call": "tool_input",
    "tool_input": "tool_input",
    "tool_ingress": "tool_input",
    "tool_injection": "tool_input",
    "tool_output": "tool_output",
    "tool_egress": "tool_output",
}


def map_block_category(raw_category: Optional[str]) -> Optional[str]:
    """Map a raw ``Violation.category`` to ``ingress``/``egress``/``tool_input``/
    ``tool_output``, falling back to the raw label when unmapped."""
    if not raw_category:
        return None
    return _BLOCK_CATEGORY_MAP.get(raw_category, raw_category)


def _extract_exception_from_span(span):
    """Return ``(exception_type, exception_message)`` from a span's recorded
    exception event, falling back to the status description for the message.

    ``on_end`` receives a ``ReadableSpan`` whose ``events`` include the
    ``exception`` event recorded by ``record_exception`` (verified on
    opentelemetry-sdk 1.41.1: attributes ``exception.type`` / ``exception.message``).
    """
    exc_type = None
    exc_message = None
    for event in getattr(span, "events", None) or ():
        if getattr(event, "name", None) == "exception":
            ev_attrs = getattr(event, "attributes", None) or {}
            exc_type = ev_attrs.get("exception.type") or exc_type
            exc_message = ev_attrs.get("exception.message") or exc_message
    if exc_message is None:
        status = getattr(span, "status", None)
        if status is not None:
            exc_message = getattr(status, "description", None)
    return exc_type, exc_message


# Task-local mapping of ``node_uniq_id -> metadata dict``.  Populated at
# execution start (before ``app.astream``) and read by the SpanProcessor's
# ``on_start`` for every span created during streaming.
_node_metadata: ContextVar[Optional[Dict[str, Dict[str, Any]]]] = ContextVar(
    "tada_node_metadata", default=None
)


def set_current_node_metadata(mapping: Dict[str, Dict[str, Any]]) -> Token:
    """Set the task-local node-metadata mapping; returns a reset token."""
    return _node_metadata.set(mapping)


def reset_current_node_metadata(token: Token) -> None:
    """Reset the task-local node-metadata mapping (non-fatal)."""
    try:
        _node_metadata.reset(token)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("reset_current_node_metadata failed (non-fatal): %s", exc)


# Executor-deposited node outcomes keyed by ``(execution_id, node_id)``.
# Written during node execution (tool invocations, guardrail blocks) via
# :func:`record_node_outcome` and merged onto the enriched span at ``on_end``,
# then popped.  A plain module-level dict (rather than a ``ContextVar``) is used
# because the deposit and the span ``on_end`` may run in different async tasks;
# keying by ``(execution_id, node_id)`` keeps entries isolated per node.
_node_outcomes: Dict[tuple, Dict[str, Any]] = {}


def record_node_outcome(
    execution_id: Optional[str], node_id: Optional[str], **fields: Any
) -> None:
    """Deposit outcome attributes for a node's enriched span.

    Merged onto the OpenInference per-node span at ``on_end`` (e.g.
    ``tools.invoked`` / ``tools.count`` from the agent executor, or
    ``node.status="blocked"`` + ``block.*`` from a guardrail block).  ``None``
    values are ignored so optional fields never stamp empty attributes.
    """
    if not node_id:
        return
    try:
        bucket = _node_outcomes.setdefault((execution_id, node_id), {})
        bucket.update({k: v for k, v in fields.items() if v is not None})
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("record_node_outcome failed (non-fatal): %s", exc)


def get_node_metadata_span_processor():
    """Create and return the ``NodeMetadataSpanProcessor``.

    Call once during OTel bootstrap and add to the active ``TracerProvider``::

        tp = trace_api.get_tracer_provider()
        tp.add_span_processor(get_node_metadata_span_processor())
    """
    try:
        from opentelemetry.sdk.trace import SpanProcessor

        class NodeMetadataSpanProcessor(SpanProcessor):
            """Enriches per-node auto CHAIN spans with TADA node metadata.

            At ``on_start`` it looks up the span name (the node ``uniq_id``) in
            the task-local mapping and, when found, rewrites the span name to
            the human-readable node name and stamps ``node.*`` attributes plus
            an explicit ``tada.node.enriched`` marker used by the Langfuse
            export gate to admit the span.
            """

            def on_start(self, span, parent_context=None) -> None:
                try:
                    mapping = _node_metadata.get()
                    if not mapping:
                        return

                    # Root-span enrichment: stamp the Langfuse trace name so the
                    # UI shows the workflow name instead of "LangGraph".  The
                    # OpenInference LangGraph pregel root span is parentless
                    # (verified: parent is None); nested subgraph roots share the
                    # "LangGraph" name but keep a parent, so we stamp the trace
                    # name on them too (same value) but only rename the true root.
                    root_meta = mapping.get(_ROOT_META_KEY)
                    if root_meta is not None:
                        parent = getattr(span, "parent", None)
                        if parent is None or span.name == "LangGraph":
                            graph_name = root_meta.get("graph_name")
                            if graph_name:
                                span.set_attribute("langfuse.trace.name", graph_name)
                                span.set_attribute("workflow.name", graph_name)
                                if parent is None:
                                    span.update_name(graph_name)
                            exec_id = root_meta.get("execution_id")
                            if exec_id:
                                span.set_attribute("workflow.execution_id", exec_id)
                            # Admit the root span through the export gate, but
                            # WITHOUT node.id so on_end skips per-node stamping.
                            span.set_attribute("tada.node.enriched", True)
                            return

                    info = mapping.get(span.name)
                    if not info:
                        return

                    human = info.get("name")
                    if human:
                        span.update_name(human)
                        span.set_attribute("node.name", human)

                    # Explicit marker the export gate keys on (attribute-based
                    # admission — never name/kind-based).
                    span.set_attribute("tada.node.enriched", True)
                    span.set_attribute("node.id", info.get("id", span.name))

                    node_type = info.get("type")
                    if node_type is not None:
                        span.set_attribute("node.type", node_type)

                    exec_id = info.get("execution_id")
                    if exec_id:
                        span.set_attribute("workflow.execution_id", exec_id)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Node span enrichment failed (non-fatal): %s", exc)

            def on_end(self, span) -> None:
                # Duration, status and error are only knowable at span end.
                # ``on_end`` receives a ``ReadableSpan`` (no ``set_attribute``),
                # but its ``_attributes`` container is the SAME object as the
                # live span (verified on opentelemetry-sdk 1.41.1), so mutating
                # it here is visible to the deferred Langfuse batch exporter.
                # Gated on our own ``tada.node.enriched`` marker so only
                # enriched node spans are touched.
                try:
                    attrs = getattr(span, "attributes", None) or {}
                    if not attrs.get("tada.node.enriched"):
                        return

                    live_attrs = getattr(span, "_attributes", None)
                    if live_attrs is None:
                        return

                    # The workflow-root span is enriched (for the gate + trace
                    # name) but carries no ``node.id``; skip per-node stamping
                    # so we never mislabel the root as a node.
                    if not live_attrs.get("node.id"):
                        return

                    start = getattr(span, "start_time", None)
                    end = getattr(span, "end_time", None)
                    if start is not None and end is not None:
                        # Duration in milliseconds.
                        live_attrs["node.duration_ms"] = (end - start) / 1_000_000

                    from opentelemetry.trace import StatusCode

                    status = getattr(span, "status", None)
                    is_error = bool(
                        status is not None
                        and status.status_code == StatusCode.ERROR
                    )

                    # Executor-deposited outcome (tools.*, block.*, and a
                    # possible node.status="blocked") for this node.
                    node_id = live_attrs.get("node.id")
                    exec_id = live_attrs.get("workflow.execution_id")
                    outcome = _node_outcomes.pop((exec_id, node_id), None) or {}
                    deposited_status = outcome.get("node.status")

                    # node.status precedence: a deposited status (e.g. "blocked")
                    # wins; otherwise derive ok / error from the span status.
                    if deposited_status:
                        live_attrs["node.status"] = deposited_status
                    elif "node.status" not in live_attrs:
                        live_attrs["node.status"] = "error" if is_error else "ok"

                    # node.error / exception.message are the genuine-error path
                    # only — skipped for a blocked node and on success.
                    if is_error and live_attrs.get("node.status") == "error":
                        exc_type, exc_message = _extract_exception_from_span(span)
                        if exc_type:
                            live_attrs["node.error"] = exc_type
                        if exc_message:
                            live_attrs["exception.message"] = (
                                exc_message[:_EXC_MSG_MAXLEN]
                            )

                    # Merge remaining deposited attributes (tools.*, block.*).
                    for key, value in outcome.items():
                        if key == "node.status":
                            continue
                        live_attrs[key] = value
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug(
                        "Node span end-enrichment failed (non-fatal): %s", exc
                    )

            def shutdown(self) -> None:
                pass

            def force_flush(self, timeout_millis: int = 30000) -> bool:
                return True

        return NodeMetadataSpanProcessor()
    except ImportError as exc:
        logger.debug(
            "OTel SDK not available, node metadata processor disabled: %s", exc
        )
        return None
