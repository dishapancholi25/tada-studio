"""API scanner backend — calls a remote llm-guard-service over HTTP.

Implements the ``ScannerBackend`` protocol by making async HTTP calls to a
dedicated scanner service.  All heavy ML models live in that service; this
client is lightweight with no torch/transformers dependency.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

import httpx

from backend.services.guardrails.backends.protocol import ScannerResult, ScanResult

logger = logging.getLogger(__name__)

_REDACTED_RE = re.compile(r"\[REDACTED_([A-Z_]+?)_\d+\]")

_LLM_GUARD_API_URL = os.environ.get("LLM_GUARD_API_URL", "http://llm-guard:8001")
_LLM_GUARD_API_TIMEOUT = float(os.environ.get("LLM_GUARD_API_TIMEOUT", "30"))
_LLM_GUARD_API_KEY = os.environ.get("LLM_GUARD_API_KEY", "")


class ApiScannerBackend:
    """Calls the llm-guard-service for all scanner invocations."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self._base_url = (base_url or _LLM_GUARD_API_URL).rstrip("/")
        self._timeout = timeout or _LLM_GUARD_API_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[object] = None  # track which event loop owns the client

    async def _get_client(self) -> httpx.AsyncClient:
        import asyncio

        current_loop = asyncio.get_running_loop()

        # Recreate the client if it was created on a different (now-closed)
        # event loop — workflow executors can run in fresh loops.
        if self._client is not None and not self._client.is_closed:
            if self._loop is current_loop:
                return self._client
            # Stale client from a previous loop — discard it
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

        headers = {}
        if _LLM_GUARD_API_KEY:
            headers["Authorization"] = f"Bearer {_LLM_GUARD_API_KEY}"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            headers=headers,
        )
        self._loop = current_loop
        return self._client

    async def scan_input(
        self,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        # Detect non-anonymize PII action so we can force the remote service
        # to run the full anonymize scanner (needed to get sanitized text with
        # [REDACTED_*] placeholders for entity extraction).
        anonymize_cfg = scanners.get("anonymize", {})
        pii_action = (
            anonymize_cfg.get("action", "anonymize")
            if isinstance(anonymize_cfg, dict)
            else "anonymize"
        )
        strip_sanitization = False
        request_scanners = scanners
        if "anonymize" in scanners and pii_action != "anonymize":
            strip_sanitization = True
            request_scanners = {
                k: (
                    {**v, "action": "anonymize"}
                    if k == "anonymize" and isinstance(v, dict)
                    else v
                )
                for k, v in scanners.items()
            }

        payload: Dict[str, Any] = {
            "content": content,
            "scanners": request_scanners,
        }
        if vault_id:
            payload["vault_id"] = vault_id
        if vault_secret:
            payload["vault_secret"] = vault_secret

        try:
            client = await self._get_client()
            response = await client.post("/scan/input", json=payload)
            response.raise_for_status()
            result = self._parse_response(response.json())

            # Backfill entity metadata for the anonymize scanner when the
            # remote service omits it.  Older llm-guard-svc versions don't
            # return a metadata field; we derive it from the [REDACTED_*]
            # placeholders in the sanitized text instead.  For non-anonymize
            # actions (warn/block) we also strip the sanitized text since the
            # caller only wants detection, not transformation.
            if "anonymize" in scanners:
                patched: list[ScannerResult] = []
                for r in result.results:
                    if r.scanner_name == "anonymize":
                        metadata = r.metadata
                        if metadata is None and r.sanitized:
                            placeholders = _REDACTED_RE.findall(r.sanitized)
                            if placeholders:
                                metadata = {
                                    "entity_types": sorted(set(placeholders)),
                                    "entity_count": len(placeholders),
                                }
                        patched.append(
                            ScannerResult(
                                scanner_name=r.scanner_name,
                                is_valid=r.is_valid,
                                risk_score=r.risk_score,
                                sanitized=None if strip_sanitization else r.sanitized,
                                metadata=metadata,
                            )
                        )
                    else:
                        patched.append(r)
                result = ScanResult(
                    results=patched,
                    vault_id=None if strip_sanitization else result.vault_id,
                    vault_secret=None if strip_sanitization else result.vault_secret,
                    sanitized_content=None
                    if strip_sanitization
                    else result.sanitized_content,
                )
            return result
        except Exception as e:
            logger.error("[GUARDRAILS-API] scan_input request failed: %s", e)
            return ScanResult()

    async def scan_output(
        self,
        prompt: str,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "content": content,
            "scanners": scanners,
        }
        if vault_id:
            payload["vault_id"] = vault_id
        if vault_secret:
            payload["vault_secret"] = vault_secret

        try:
            client = await self._get_client()
            response = await client.post("/scan/output", json=payload)
            response.raise_for_status()
            return self._parse_response(response.json())
        except Exception as e:
            logger.error("[GUARDRAILS-API] scan_output request failed: %s", e)
            return ScanResult()

    @staticmethod
    def _parse_response(data: Dict[str, Any]) -> ScanResult:
        """Parse the JSON response from the llm-guard-service."""
        results = [
            ScannerResult(
                scanner_name=r["scanner"],
                is_valid=r["is_valid"],
                risk_score=r["risk_score"],
                sanitized=r.get("sanitized"),
                metadata=r.get("metadata"),
            )
            for r in data.get("results", [])
        ]
        return ScanResult(
            results=results,
            vault_id=data.get("vault_id"),
            vault_secret=data.get("vault_secret"),
            sanitized_content=data.get("sanitized_content"),
        )

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
