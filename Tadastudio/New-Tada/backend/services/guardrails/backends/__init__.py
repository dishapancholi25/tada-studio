"""Scanner backend factory.

Reads ``LLM_GUARD_MODE`` env var to select the active scanner backend:

- ``local``  (default) — in-process LLM Guard scanners (~3.5 GB models)
- ``api``    — all scanners via remote llm-guard-service
- ``hybrid`` — heavy ML scanners remote, lightweight (TokenLimit, Secrets) local
"""

import logging
import os
from typing import Union

from backend.services.guardrails.backends.api import ApiScannerBackend
from backend.services.guardrails.backends.hybrid import HybridScannerBackend
from backend.services.guardrails.backends.local import LocalScannerBackend
from backend.services.guardrails.backends.protocol import (
    ScannerBackend,
    ScannerResult,
    ScanResult,
)

logger = logging.getLogger(__name__)

_backend_instance: Union[
    LocalScannerBackend, ApiScannerBackend, HybridScannerBackend, None
] = None


def get_scanner_backend() -> Union[
    LocalScannerBackend, ApiScannerBackend, HybridScannerBackend
]:
    """Return the singleton scanner backend based on ``LLM_GUARD_MODE``."""
    global _backend_instance
    if _backend_instance is not None:
        return _backend_instance

    mode = os.environ.get("LLM_GUARD_MODE", "local").lower()

    if mode == "api":
        logger.info("[GUARDRAILS] Using API scanner backend (remote llm-guard-service)")
        _backend_instance = ApiScannerBackend()
    elif mode == "hybrid":
        logger.info("[GUARDRAILS] Using hybrid scanner backend (local + remote)")
        _backend_instance = HybridScannerBackend()
    else:
        if mode != "local":
            logger.warning(
                "[GUARDRAILS] Unknown LLM_GUARD_MODE=%s, falling back to local", mode
            )
        logger.info("[GUARDRAILS] Using local scanner backend (in-process)")
        _backend_instance = LocalScannerBackend()

    return _backend_instance


__all__ = [
    "get_scanner_backend",
    "ScannerBackend",
    "ScannerResult",
    "ScanResult",
    "LocalScannerBackend",
    "ApiScannerBackend",
    "HybridScannerBackend",
]
