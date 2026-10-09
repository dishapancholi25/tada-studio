"""Langfuse observability bootstrap (native Langfuse SDK).

Initializes the Langfuse SDK client, which configures OpenTelemetry export to
Langfuse automatically (endpoint, auth, batching, background flushing).
LangChain / LLM / embedding calls are captured automatically via the
OpenInference LangChain instrumentor, which feeds spans into the OpenTelemetry
provider the Langfuse SDK sets up — so no execution code needs to change.

Everything is best-effort and non-fatal: missing packages, bad config, or an
unreachable Langfuse server are logged and swallowed so the application keeps
running without observability.
"""

from __future__ import annotations

from importlib import import_module

from backend.services.config import get_logger


logger = get_logger(__name__)

_initialized: bool = False
_client = None  # cached Langfuse client singleton
_export_enabled: bool = False


def get_langfuse_client():
    """Return the initialized Langfuse client, or ``None`` if not set up."""
    return _client


def set_langfuse_export_enabled(enabled: bool) -> None:
    """Enable or disable Langfuse span export without tearing down the client."""
    global _export_enabled
    _export_enabled = enabled


def _should_export_langfuse_span(span) -> bool:
    """Runtime export gate used by the Langfuse SDK span processor.

    Behaviour:
      1. If Langfuse export is turned off, block everything.
      2. If the span was explicitly enriched by the NodeMetadataSpanProcessor
         (``tada.node.enriched=True``), always allow it. The Langfuse SDK's
         default filter is LLM-focused and returns False for these app spans,
         which would otherwise drop them.
      3. Otherwise defer to the Langfuse SDK's default filter, and only
         block when it says False. If the filter cannot be loaded or fails,
         allow the span rather than silently dropping observability.
    """
    if not _export_enabled:
        return False

    span_attrs = getattr(span, "attributes", None) or {}
    # Attribute-based admission: only spans TADA explicitly stamped via the
    # NodeMetadataSpanProcessor (tada.node.enriched=True) are admitted here —
    # NOT every CHAIN span and NOT kind-based.
    is_enriched_span = bool(span_attrs.get("tada.node.enriched"))

    if not is_enriched_span:
        try:
            try:
                span_filter = import_module("langfuse.span_filter")
            except ModuleNotFoundError:
                span_filter = import_module("langfuse._client.span_filter")

            if span_filter.is_default_export_span(span) is False:
                return False
        except Exception as exc:
            logger.debug("Langfuse span export gate failed open: %s", exc)
            return True

    # Admitted by enrichment or the SDK default filter.
    return True


def _instrument_langchain() -> None:
    """Auto-capture LangChain/LLM/embedding spans via OpenInference (idempotent)."""
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        instrumentor = LangChainInstrumentor()
        if not getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
            instrumentor.instrument()
            logger.debug("LangChain instrumentor enabled")
    except Exception as exc:
        logger.debug("Could not enable LangChain instrumentor (non-fatal): %s", exc)


def _instrument_openai() -> None:
    """Auto-capture raw OpenAI/Azure OpenAI spans via OpenInference (idempotent).

    This captures embedding calls (``embed_query``/``embed_documents``) that the
    LangChain instrumentor misses, since LangChain's Embeddings base class does
    not fire callback events.  Azure embeddings ultimately call the OpenAI SDK,
    so instrumenting that layer covers them.
    """
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor

        instrumentor = OpenAIInstrumentor()
        if not getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
            instrumentor.instrument()
            logger.debug("OpenAI instrumentor enabled")
    except Exception as exc:
        logger.debug("Could not enable OpenAI instrumentor (non-fatal): %s", exc)


def _uninstrument_langchain() -> None:
    """Remove LangChain OpenInference hooks when currently instrumented."""
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        instrumentor = LangChainInstrumentor()
        if getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
            instrumentor.uninstrument()
            logger.debug("LangChain instrumentor disabled")
    except Exception as exc:
        logger.debug("Could not disable LangChain instrumentor (non-fatal): %s", exc)


def _uninstrument_openai() -> None:
    """Remove OpenAI OpenInference hooks when currently instrumented."""
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor

        instrumentor = OpenAIInstrumentor()
        if getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
            instrumentor.uninstrument()
            logger.debug("OpenAI instrumentor disabled")
    except Exception as exc:
        logger.debug("Could not disable OpenAI instrumentor (non-fatal): %s", exc)


def reset_openinference_instrumentation() -> None:
    """Clear OpenInference LangChain/OpenAI hooks before provider switching."""
    _uninstrument_langchain()
    _uninstrument_openai()

def initialize_langfuse_instrumentation(config=None) -> None:
    """Initialize Langfuse tracing (idempotent, non-fatal).

    Creates the Langfuse SDK client (which sets up OpenTelemetry export) and
    enables LangChain auto-instrumentation.  Safe to call when Langfuse is
    disabled — it simply returns early.
    """
    global _initialized, _client
    if config is None:
        from backend.services.langfuse.config import get_langfuse_config

        config = get_langfuse_config()
    set_langfuse_export_enabled(config.is_configured)
    if _initialized:
        return

    if not config.is_configured:
        missing = [
            name
            for name, value in (
                ("enabled", config.enabled),
                ("host", config.host),
                ("public_key", config.public_key),
                ("secret_key", config.secret_key),
            )
            if not value
        ]
        logger.info(
            "Langfuse instrumentation skipped (missing/disabled: %s)",
            ", ".join(missing) or "unknown",
        )
        return

    try:
        try:
            from langfuse import Langfuse
        except ImportError:
            logger.warning(
                "langfuse package not installed, skipping Langfuse instrumentation"
            )
            return

        # Creating the client configures OpenTelemetry export to Langfuse
        # (endpoint, auth, batching, background flushing) automatically.
        import requests.adapters
        import urllib3
        import httpx
        import os
        Client_ID=(config.client_id or os.getenv("LANGFUSE_CLIENT_ID", "")).strip()
      
        HEADERS={"ClientId": Client_ID} if Client_ID else {}

        

     
        #Interim Solution for Bypassing SSL Verification for Langfuse SDK Client.
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        _orig_send = requests.adapters.HTTPAdapter.send

        def _send(self, request, *args, verify=True, **kwargs):
            if Client_ID and config.host in (request.url or ""):
                request.headers.setdefault("ClientId", Client_ID)
            return _orig_send(self, request, *args, verify=False, **kwargs)

        requests.adapters.HTTPAdapter.send = _send

        _client= Langfuse(
        public_key=config.public_key,
        secret_key=config.secret_key,
        base_url=config.host,
        should_export_span=_should_export_langfuse_span,
        httpx_client=httpx.Client(verify=False, timeout=30.0, headers=HEADERS),
        additional_headers=HEADERS if HEADERS else None)

        # Auto-capture LangChain/LLM/embedding spans.
        _instrument_langchain()
        _instrument_openai()

        # Register the node-metadata enrichment processor on the Langfuse-
        # configured (global) TracerProvider so per-node auto CHAIN spans get
        # human-readable names + node.* attributes even when Phoenix is off.
        try:
            from opentelemetry import trace as trace_api
            from backend.services.langfuse.node_enrichment import (
                get_node_metadata_span_processor,
            )

            tracer_provider = trace_api.get_tracer_provider()
            if hasattr(tracer_provider, "add_span_processor"):
                node_processor = get_node_metadata_span_processor()
                if node_processor is not None:
                    tracer_provider.add_span_processor(node_processor)
                    logger.debug("NodeMetadataSpanProcessor registered")
            else:
                logger.debug(
                    "Active TracerProvider has no add_span_processor; "
                    "node metadata enrichment disabled"
                )
        except Exception as proc_exc:
            logger.debug(
                "Could not register node metadata processor (non-fatal): %s",
                proc_exc,
            )

        _initialized = True
        logger.info(
            "Langfuse instrumentation initialized (host=%s)",
            config.host,
        )
    except Exception as e:
        logger.warning("Langfuse instrumentation setup failed (non-fatal): %s", e)


def shutdown_langfuse() -> None:
    """Flush and shut down the Langfuse client (non-fatal)."""
    global _client, _initialized
    if _client is None:
        _initialized = False
        return
    try:
        _client.flush()
        _client.shutdown()
    except Exception as exc:
        logger.debug("Langfuse shutdown error (non-fatal): %s", exc)
    finally:
        _client = None
        _initialized = False
        set_langfuse_export_enabled(False)
