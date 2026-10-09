"""Per-workflow Phoenix project routing and span metadata.

Wraps workflow execution in OpenInference context managers so that:
  1. Spans are routed to a Phoenix project named after the workflow.
  2. Every span carries rich metadata (execution_id, workflow_id, user, trigger).
  3. The execution is tagged for easy filtering in the Phoenix UI.

All operations are best-effort — import failures or context-manager errors
are logged and never propagate to the caller.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.services.config import get_logger

logger = get_logger(__name__)


def sanitize_project_name(name: str) -> str:
    """Turn an arbitrary workflow name into a valid Phoenix project name.

    Phoenix project names should be URL-safe.  We lowercase, replace
    whitespace/special chars with hyphens, collapse runs, and strip edges.
    """
    sanitized = re.sub(r"[^a-z0-9\-]", "-", name.lower())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    return sanitized or "default"


@dataclass
class PhoenixContext:
    """Context yielded by :func:`phoenix_workflow_context`.

    Attributes:
        project_name: Sanitized Phoenix project name.
        trace_id: OTel trace ID (hex string) captured during execution,
            or ``None`` if OTel is not available.
        span_id: OTel span ID (hex string), or ``None``.
    """

    project_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


@contextmanager
def phoenix_workflow_context(
    *,
    graph_name: str,
    execution_id: str,
    db_execution_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    evaluation_run_id: Optional[str] = None,
):
    """Context manager that routes spans to a per-workflow Phoenix project
    and attaches execution metadata to every span created within.

    Yields a :class:`PhoenixContext` with the project name.  The caller
    should use :func:`phoenix_root_span` around the actual streaming
    execution to capture the OTel trace ID for deep-linking.

    Usage::

        with phoenix_workflow_context(
            graph_name="my-workflow",
            execution_id="abc-123",
            workflow_id="wf-456",
        ) as ctx:
            with phoenix_root_span(ctx, graph_name="my-workflow", execution_id="abc-123"):
                await compiled_app.astream(...)
            # ctx.trace_id is now available

    The context manager is a no-op (yields immediately) when Phoenix is
    disabled or when the ``openinference.instrumentation`` package is not
    installed.
    """
    from backend.services.phoenix.config import get_phoenix_config

    config = get_phoenix_config()
    if not config.enabled:
        yield PhoenixContext(project_name=sanitize_project_name(graph_name))
        return

    project_name = sanitize_project_name(graph_name)

    metadata: Dict[str, Any] = {
        "agentic_studio.execution_id": execution_id,
        "agentic_studio.graph_name": graph_name,
    }
    if db_execution_id:
        metadata["agentic_studio.db_execution_id"] = str(db_execution_id)
    if workflow_id:
        metadata["agentic_studio.workflow_id"] = workflow_id
    if user_id:
        metadata["agentic_studio.user_id"] = user_id
    if trigger_type:
        metadata["agentic_studio.trigger_type"] = trigger_type
    if evaluation_run_id:
        metadata["agentic_studio.evaluation_run_id"] = evaluation_run_id

    tags = ["agentic-studio", f"workflow:{project_name}"]
    if trigger_type:
        tags.append(f"trigger:{trigger_type}")

    # Build a stack of OpenInference context managers.
    # We use individual context managers (using_metadata, using_session, etc.)
    # and merge metadata with any existing context to avoid clobbering metadata
    # set by outer callers (best-effort).
    _contexts: list = []
    try:
        from openinference.instrumentation import (
            using_metadata,
            using_session,
            using_tags,
            using_user,
        )

        from backend.services.phoenix.project_routing import using_project

        # Merge with any existing metadata in the current OTel context
        # so that outer callers (e.g. the evaluation orchestrator) can set
        # additional metadata that propagates through to all spans.
        try:
            import json

            from openinference.semconv.trace import SpanAttributes
            from opentelemetry.context import get_current, get_value

            existing_raw = get_value(SpanAttributes.METADATA, get_current())
            if existing_raw and isinstance(existing_raw, str):
                existing_metadata = json.loads(existing_raw)
                if isinstance(existing_metadata, dict):
                    # Our keys go in first, existing keys override (they're more specific)
                    metadata = {**metadata, **existing_metadata}
        except Exception:
            pass  # best-effort merge

        _contexts.append(using_project(project_name))
        _contexts.append(using_session(execution_id))
        if user_id:
            _contexts.append(using_user(user_id))
        _contexts.append(using_metadata(metadata))
        _contexts.append(using_tags(tags))
    except ImportError:
        logger.debug(
            "openinference.instrumentation not installed, Phoenix context disabled"
        )
    except Exception as exc:
        logger.warning("Failed to build Phoenix context managers (non-fatal): %s", exc)

    # Enter all contexts
    entered: list = []
    for ctx in _contexts:
        try:
            ctx.__enter__()
            entered.append(ctx)
        except Exception as exc:
            logger.warning("Failed to enter Phoenix context (non-fatal): %s", exc)

    try:
        yield PhoenixContext(project_name=project_name)
    finally:
        # Exit in reverse order
        for ctx in reversed(entered):
            try:
                ctx.__exit__(None, None, None)
            except Exception as exc:
                logger.warning("Failed to exit Phoenix context (non-fatal): %s", exc)


@contextmanager
def phoenix_root_span(
    phoenix_ctx: PhoenixContext,
    *,
    graph_name: str,
    execution_id: str,
    input_value: str | None = None,
):
    """Create an OTel root span that scopes the workflow's streaming execution.

    Must be called inside :func:`phoenix_workflow_context` so the span
    inherits the correct project routing and metadata.  After the context
    manager exits the captured ``trace_id`` and ``span_id`` are written
    back to *phoenix_ctx* for the caller to use.

    Usage::

        with phoenix_root_span(ctx, graph_name="my-wf", execution_id="abc"):
            await compiled_app.astream(...)
        # ctx.trace_id is now set
    """
    from backend.services.phoenix.config import get_phoenix_config

    if not get_phoenix_config().enabled:
        yield
        return

    root_span = None
    ctx_token = None
    try:
        from opentelemetry import context as otel_context
        from opentelemetry import trace

        tracer = trace.get_tracer("agentic-studio")
        span_attrs: Dict[str, Any] = {
            "agentic_studio.execution_id": execution_id,
            "agentic_studio.graph_name": graph_name,
        }
        try:
            from openinference.semconv.trace import SpanAttributes

            span_attrs[SpanAttributes.OPENINFERENCE_SPAN_KIND] = "CHAIN"
            # Pin the original user input on the root span so every observability
            # backend sharing this span (Phoenix, Langfuse) shows the raw user
            # query as the trace input — not a later reframed/expanded version.
            if input_value:
                span_attrs[SpanAttributes.INPUT_VALUE] = input_value
        except ImportError:
            # OpenInference semantic conventions are optional; fall back without the extra span kind attribute.
            logger.debug(
                "openinference.semconv.trace not available; proceeding without OPENINFERENCE_SPAN_KIND attribute"
            )

        root_span = tracer.start_span(name=graph_name, attributes=span_attrs)
        ctx_token = otel_context.attach(trace.set_span_in_context(root_span))
        span_context = root_span.get_span_context()
        if span_context and span_context.trace_id:
            phoenix_ctx.trace_id = format(span_context.trace_id, "032x")
            phoenix_ctx.span_id = format(span_context.span_id, "016x")
    except Exception as exc:
        logger.debug("Failed to create root OTel span (non-fatal): %s", exc)

    try:
        yield
    finally:
        if root_span is not None:
            try:
                root_span.end()
            except Exception as exc:
                logger.debug("Failed to end root OTel span (non-fatal): %s", exc)
        if ctx_token is not None:
            try:
                from opentelemetry import context as otel_context

                otel_context.detach(ctx_token)
            except Exception as exc:
                logger.debug("Failed to detach OTel context token (non-fatal): %s", exc)
