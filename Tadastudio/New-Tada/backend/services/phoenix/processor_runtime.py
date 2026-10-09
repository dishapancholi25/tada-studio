"""Runtime management for the Phoenix OpenTelemetry span processor."""

from __future__ import annotations

from typing import Any

from backend.services.config import get_logger

logger = get_logger(__name__)

_phoenix_processor: Any = None


def set_phoenix_processor(processor: Any) -> None:
    """Store the Phoenix processor created by phoenix.otel.register()."""
    global _phoenix_processor
    _phoenix_processor = processor


def _processor_contains(root: Any, target: Any) -> bool:
    """Return True when target is already present in a processor tree."""
    if root is None or target is None:
        return False
    if root is target:
        return True
    for child in getattr(root, "_span_processors", []):
        if _processor_contains(child, target):
            return True
    return False


def _exporter_is_shutdown(exporter: Any) -> bool:
    """Best-effort check for shutdown flags on exporter wrappers/delegates."""
    if exporter is None:
        return False
    if getattr(exporter, "_shutdown", False):
        return True
    return _exporter_is_shutdown(getattr(exporter, "_delegate", None))


def _processor_is_shutdown(processor: Any) -> bool:
    """Best-effort check for a shutdown BatchSpanProcessor tree."""
    if processor is None:
        return False

    batch_processor = getattr(processor, "_batch_processor", None)
    if batch_processor is not None and getattr(batch_processor, "_shutdown", False):
        return True

    if _exporter_is_shutdown(getattr(processor, "span_exporter", None)):
        return True

    for child in getattr(processor, "_span_processors", []):
        if _processor_is_shutdown(child):
            return True

    return False


def ensure_phoenix_processor_attached() -> bool:
    """Reattach the remembered Phoenix processor to the current OTel provider.

    Returns False when no reusable processor exists, allowing the caller to
    create a fresh Phoenix provider/processor.
    """
    global _phoenix_processor

    if _phoenix_processor is None:
        return False
    if _processor_is_shutdown(_phoenix_processor):
        _phoenix_processor = None
        return False

    try:
        from opentelemetry import trace as trace_api

        tracer_provider = trace_api.get_tracer_provider()
        if not hasattr(tracer_provider, "add_span_processor"):
            return False

        active_processor = getattr(tracer_provider, "_active_span_processor", None)
        if not _processor_contains(active_processor, _phoenix_processor):
            tracer_provider.add_span_processor(_phoenix_processor)
            logger.info("Phoenix OTLP processor reattached to current TracerProvider")

        return True
    except Exception as exc:
        logger.debug("Could not reattach Phoenix processor (non-fatal): %s", exc)
        return False