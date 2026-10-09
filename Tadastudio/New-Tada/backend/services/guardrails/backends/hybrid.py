"""Hybrid scanner backend — lightweight scanners local, heavy ones via API.

Splits the scanner dict: TokenLimit and Secrets run in-process (no ML models,
microsecond latency); everything else is forwarded to the remote
llm-guard-service via ``ApiScannerBackend``.
"""

import logging
from typing import Any, Dict, Optional

from backend.services.guardrails.backends.api import ApiScannerBackend
from backend.services.guardrails.backends.local import LocalScannerBackend
from backend.services.guardrails.backends.protocol import ScanResult

logger = logging.getLogger(__name__)

# Scanners that stay local — no ML models, pure heuristic / token counting.
_LOCAL_SCANNERS = {"token_limit", "secrets"}


class HybridScannerBackend:
    """Routes lightweight scanners locally, heavy ML scanners to the API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self._local = LocalScannerBackend()
        self._api = ApiScannerBackend(base_url=base_url, timeout=timeout)

    @staticmethod
    def _split(
        scanners: Dict[str, Dict[str, Any]],
    ) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Split scanners into (local, remote) dicts."""
        local = {k: v for k, v in scanners.items() if k in _LOCAL_SCANNERS}
        remote = {k: v for k, v in scanners.items() if k not in _LOCAL_SCANNERS}
        return local, remote

    async def scan_input(
        self,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        local_scanners, remote_scanners = self._split(scanners)

        # Run local scanners (always, even if empty — returns empty ScanResult)
        local_result = (
            await self._local.scan_input(content, local_scanners, vault_id, vault_secret)
            if local_scanners
            else ScanResult()
        )

        # Run remote scanners
        remote_result = (
            await self._api.scan_input(content, remote_scanners, vault_id, vault_secret)
            if remote_scanners
            else ScanResult()
        )

        return self._merge(local_result, remote_result)

    async def scan_output(
        self,
        prompt: str,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        local_scanners, remote_scanners = self._split(scanners)

        local_result = (
            await self._local.scan_output(prompt, content, local_scanners, vault_id, vault_secret)
            if local_scanners
            else ScanResult()
        )
        remote_result = (
            await self._api.scan_output(prompt, content, remote_scanners, vault_id, vault_secret)
            if remote_scanners
            else ScanResult()
        )

        return self._merge(local_result, remote_result)

    @staticmethod
    def _merge(local: ScanResult, remote: ScanResult) -> ScanResult:
        """Merge local and remote results, preferring remote for vault and sanitized content."""
        return ScanResult(
            results=local.results + remote.results,
            vault_id=remote.vault_id or local.vault_id,
            vault_secret=remote.vault_secret or local.vault_secret,
            sanitized_content=remote.sanitized_content or local.sanitized_content,
        )

    async def close(self):
        await self._api.close()
