"""Concurrency-safe per-workflow Phoenix project routing.

Replaces ``dangerously_using_project`` (which globally monkey-patches
``ReadableSpan.__init__``) with a ``ContextVar``-based ``SpanProcessor``
that stamps ``openinference.project.name`` on each span from the current
task-local context — safe for concurrent asyncio coroutines.

Usage::

    from backend.services.phoenix.project_routing import using_project

    with using_project("my-workflow"):
        # All spans created here (including by auto-instrumented LLM calls)
        # will be routed to the "my-workflow" Phoenix project.
        await some_llm_call()

The ``ProjectRoutingSpanProcessor`` must be registered on the
``TracerProvider`` at startup — see :func:`get_span_processor`.
"""

from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional

from backend.services.config import get_logger

logger = get_logger(__name__)

# Task-local project name override.  When set, the SpanProcessor stamps
# this value onto every span's resource, overriding the default project.
_current_project: ContextVar[Optional[str]] = ContextVar(
    "phoenix_project", default=None
)


@contextmanager
def using_project(project_name: str):
    """Context manager that routes spans to a specific Phoenix project.

    Concurrency-safe: uses a ``ContextVar`` so each asyncio task / thread
    gets its own project override without affecting other tasks.
    """
    token = _current_project.set(project_name)
    try:
        yield
    finally:
        _current_project.reset(token)


def get_current_project() -> Optional[str]:
    """Return the active Phoenix project name, or ``None`` if unset.

    Useful for capturing the project before crossing a thread or
    ``contextvars.Context()`` boundary so it can be restored with
    :func:`using_project` on the other side.
    """
    return _current_project.get()


def get_span_processor():
    """Create and return the ``ProjectRoutingSpanProcessor``.

    Call this once during OTel bootstrap and add the returned processor
    to the ``TracerProvider``::

        from backend.services.phoenix.project_routing import get_span_processor
        tracer_provider.add_span_processor(get_span_processor())
    """
    try:
        from opentelemetry.sdk.trace import SpanProcessor
        from opentelemetry.sdk.resources import Resource
        from openinference.semconv.resource import ResourceAttributes

        class ProjectRoutingSpanProcessor(SpanProcessor):
            """Stamps ``openinference.project.name`` from a ContextVar onto spans."""

            def on_start(self, span, parent_context=None) -> None:
                project = _current_project.get()
                if project is not None:
                    # Override the resource to include the project name.
                    # We merge with existing resource attributes so nothing is lost.
                    span._resource = Resource(
                        {
                            **span._resource.attributes,
                            ResourceAttributes.PROJECT_NAME: project,
                        },
                        span._resource.schema_url,
                    )

            def on_end(self, span) -> None:
                pass

            def shutdown(self) -> None:
                pass

            def force_flush(self, timeout_millis: int = 30000) -> bool:
                return True

        return ProjectRoutingSpanProcessor()
    except ImportError as exc:
        logger.debug(
            "OTel SDK not available, project routing processor disabled: %s", exc
        )
        return None
