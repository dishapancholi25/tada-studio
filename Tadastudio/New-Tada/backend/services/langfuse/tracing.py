"""Langfuse trace helpers.

LLM/embedding spans are captured automatically by the Langfuse SDK + the
OpenInference LangChain instrumentor.  This module translates a captured OTel
``trace_id`` into a Langfuse UI deep-link.
"""

from __future__ import annotations

from typing import Optional

from backend.services.config import get_logger

logger = get_logger(__name__)


def build_langfuse_trace_ref(trace_id: Optional[str]) -> Optional[dict]:
    """Return a trace reference dict for a captured ``trace_id``, or ``None``.

    Best-effort and non-fatal: returns ``None`` when Langfuse is disabled, not
    configured, or anything goes wrong.
    """
    if not trace_id:
        return None
    try:
        from backend.services.langfuse.config import get_langfuse_config
        from backend.services.langfuse.instrumentation import get_langfuse_client

        config = get_langfuse_config()
        if not config.enabled:
            return None

        client = get_langfuse_client()
        if client is None:
            return None

        # Use the SDK method so the URL includes the correct /project/{slug}/traces/ path.
        # Manual construction (f"{host}/trace/{id}") produces a broken URL missing the project segment.
        url = client.get_trace_url(trace_id=trace_id)
        if not url:
            return None
        return {
            # "trace_id": trace_id,
            "url": url,
            # "project_name": config.project_name,
        }
    except Exception as exc:
        logger.debug("Failed to build Langfuse trace ref (non-fatal): %s", exc)
        return None
    



def get_langfuse_session_url(execution_id: str) -> str:
    """
    Builds Langfuse session URL using env variables and execution/session ID.

    Required env variables:
      - LANGFUSE_UI_HOST
      - LANGFUSE_PROJECT_ID

    Args:
        execution_id: Execution ID / Session ID generated during runtime.

    Returns:
        Langfuse session URL.
    """
    
    import os
    host = os.getenv("LANGFUSE_UI_HOST")
    project_id = os.getenv("LANGFUSE_PROJECT_ID")


    
    if not host:
        raise ValueError("Missing environment variable: LANGFUSE_UI_HOST")

    if not project_id:
        raise ValueError("Missing environment variable: LANGFUSE_PROJECT_ID")

    if not execution_id:
        raise ValueError("execution_id cannot be empty")

    host = host.rstrip("/")

    return f"{host}/project/{project_id}/sessions/{execution_id}"



