"""Phoenix OTel auto-instrumentation bootstrap.

Instruments LLM libraries via ``phoenix.otel.register()`` at startup when
Phoenix is enabled.  A gated exporter wraps only Phoenix's exporter so that
the settings UI toggle (``PHOENIX_ENABLED``) can suppress Phoenix span export
at runtime without requiring a process restart.
"""

from __future__ import annotations

from backend.services.config import get_logger
from backend.services.phoenix.processor_runtime import (
    ensure_phoenix_processor_attached,
    set_phoenix_processor,
)

logger = get_logger(__name__)

_initialized: bool = False


_SENTINEL = object()


def _build_gated_exporter(delegate):
    """Wrap a Phoenix exporter and suppress only its export call when disabled."""
    try:
        from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
    except ImportError:
        return delegate

    if getattr(delegate, "_is_phoenix_gated_exporter", False):
        return delegate

    class GatedSpanExporter(SpanExporter):
        """Exports spans only when Phoenix is enabled at runtime.

        Also keeps the OTLP exporter's auth headers in sync with the
        current ``PHOENIX_API_KEY`` setting so that key changes in the
        UI take effect without a backend restart.
        """

        _is_phoenix_gated_exporter = True

        def __init__(self, delegate):
            self._delegate = delegate
            self._session = getattr(delegate, "_session", None)
            self._last_api_key = _SENTINEL  # force first sync

        def _sync_auth_header(self, api_key: str | None) -> None:
            """Update the exporter's session Authorization header if the key changed."""
            if self._session is None or api_key == self._last_api_key:
                return
            self._last_api_key = api_key
            if api_key:
                self._session.headers["authorization"] = f"Bearer {api_key}"
            else:
                self._session.headers.pop("authorization", None)
            logger.debug("Phoenix exporter auth header updated")

        def export(self, spans):
            try:
                from backend.services.phoenix.config import get_phoenix_config

                cfg = get_phoenix_config()
                if not cfg.enabled:
                    return SpanExportResult.SUCCESS
                self._sync_auth_header(cfg.api_key)
            except Exception:
                pass  # config read failed; allow through
            return self._delegate.export(spans)

        def shutdown(self) -> None:
            self._delegate.shutdown()

        def force_flush(self, timeout_millis: int = 30000) -> bool:
            return self._delegate.force_flush(timeout_millis)

    return GatedSpanExporter(delegate)


def _set_processor_exporter(processor, exporter) -> bool:
    """Replace the exporter on SimpleSpanProcessor or BatchSpanProcessor."""
    batch_processor = getattr(processor, "_batch_processor", None)
    if batch_processor is not None and hasattr(batch_processor, "_exporter"):
        batch_processor._exporter = exporter
        return True
    if hasattr(processor, "span_exporter"):
        try:
            processor.span_exporter = exporter
            return True
        except AttributeError:
            return False
    return False


def _wrap_processor_exporters(processor) -> bool:
    """Wrap exporters found in a processor tree with the Phoenix export gate."""
    wrapped = False
    exporter = getattr(processor, "span_exporter", None)
    if exporter is not None:
        gated_exporter = _build_gated_exporter(exporter)
        if gated_exporter is not exporter:
            wrapped = _set_processor_exporter(processor, gated_exporter)

    for child in getattr(processor, "_span_processors", []):
        wrapped = _wrap_processor_exporters(child) or wrapped

    return wrapped


def initialize_phoenix_instrumentation(config=None) -> None:
    """Register Phoenix OpenTelemetry instrumentation (idempotent, non-fatal).

    Uses a gated Phoenix exporter so that spans are only exported while
    Phoenix is enabled in the settings UI.  Disabling Phoenix at runtime
    stops new Phoenix spans from being sent without requiring a restart.
    """
    global _initialized
    if _initialized and ensure_phoenix_processor_attached():
        return

    if config is None:
        from backend.services.phoenix.config import get_phoenix_config

        config = get_phoenix_config()
    if not config.enabled or not config.endpoint:
        logger.info("Phoenix instrumentation skipped (disabled or no endpoint)")
        return

    try:
        try:
            import phoenix.otel
        except ImportError:
            logger.debug("phoenix.otel not installed, skipping instrumentation")
            return

        # Register Phoenix but tell it NOT to override the global TracerProvider
        # (which may already be set by Langfuse or another SDK).  We extract
        # Phoenix's OTLP processor and attach it to the existing global provider.
        phoenix_provider = phoenix.otel.register(
            project_name=config.project_name,
            endpoint=config.endpoint,
            auto_instrument=True,
            api_key=config.api_key or None,
            set_global_tracer_provider=False,
        )

        # Get the global provider (set by Langfuse, or Phoenix if nothing ran before).
        from opentelemetry import trace as trace_api
        tracer_provider = trace_api.get_tracer_provider()

        phoenix_inner = getattr(phoenix_provider, "_active_span_processor", None)
        set_phoenix_processor(phoenix_inner)

        # If the global provider is the default no-op proxy, fall back to using
        # Phoenix's provider directly and set it as global.
        if not hasattr(tracer_provider, "add_span_processor"):
            if phoenix_inner is not None and _wrap_processor_exporters(phoenix_inner):
                logger.debug("Phoenix OTLP exporter gate installed")
            trace_api.set_tracer_provider(phoenix_provider)
            tracer_provider = phoenix_provider
            logger.debug("Phoenix provider set as global TracerProvider")
        else:
            # Attach Phoenix's OTLP processor(s) to the existing global provider.
            if phoenix_inner is not None:
                if _wrap_processor_exporters(phoenix_inner):
                    logger.debug("Phoenix OTLP exporter gate installed")
                tracer_provider.add_span_processor(phoenix_inner)
                logger.debug("Phoenix OTLP processor attached to existing TracerProvider")

        # Register the concurrency-safe project routing processor so that
        # using_project() can override the Phoenix project per-task.
        try:
            from backend.services.phoenix.project_routing import get_span_processor

            processor = get_span_processor()
            if processor is not None:
                tracer_provider.add_span_processor(
                    processor, replace_default_processor=False
                )
                logger.debug("ProjectRoutingSpanProcessor registered")
        except Exception as proc_exc:
            logger.debug(
                "Could not register project routing processor (non-fatal): %s", proc_exc
            )

        _initialized = True
        logger.info(
            "Phoenix OTel instrumentation registered (project=%s, endpoint=%s)",
            config.project_name,
            config.endpoint,
        )
    except Exception as e:
        logger.warning("Phoenix instrumentation setup failed (non-fatal): %s", e)
