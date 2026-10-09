"""Scanner backend protocol and shared data models.

Defines the interface that all scanner backends (local, API, hybrid) must
implement, plus the data classes they return.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ScannerResult:
    """Result from a single scanner invocation.

    Attributes:
        scanner_name: Identifier matching the scanner key (e.g. "prompt_injection").
        is_valid: True when the content passed the scanner check.
        risk_score: Confidence score in [0, 1].
        sanitized: Transformed content (redacted/anonymized), or None if unchanged.
    """

    scanner_name: str
    is_valid: bool
    risk_score: float
    sanitized: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ScanResult:
    """Aggregated result from a scan_input / scan_output call.

    Attributes:
        results: Per-scanner results.
        vault_id: Identifier for an Anonymize/Deanonymize vault session.
                  Returned on input when anonymize is used; passed back on output
                  for deanonymization.
        sanitized_content: Final sanitized text after all scanners that modify
                           content (anonymize, secrets redaction, etc.).
    """

    results: List[ScannerResult] = field(default_factory=list)
    vault_id: Optional[str] = None
    vault_secret: Optional[str] = None
    sanitized_content: Optional[str] = None


@runtime_checkable
class ScannerBackend(Protocol):
    """Protocol that all scanner backends must satisfy.

    Implementations:
        - LocalScannerBackend  (in-process LLM Guard scanners)
        - ApiScannerBackend    (HTTP calls to llm-guard-service)
        - HybridScannerBackend (lightweight scanners local, heavy ones via API)
    """

    async def scan_input(
        self,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        """Run input-phase scanners.

        Args:
            content: User input text to scan.
            scanners: Mapping of scanner_name → config overrides.
                      e.g. ``{"prompt_injection": {"threshold": 0.5},
                              "ban_topics": {"topics": ["violence"]}}``
            vault_id: Existing vault session to reuse (rare for input phase).
            vault_secret: Ownership token for the vault session.

        Returns:
            Aggregated scan result with per-scanner details and optional vault_id.
        """
        ...

    async def scan_output(
        self,
        prompt: str,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        """Run output-phase scanners.

        Args:
            prompt: Original user prompt (needed by relevance, factual consistency, etc.).
            content: LLM response text to scan.
            scanners: Mapping of scanner_name → config overrides.
            vault_id: Vault session from input phase (for deanonymize).
            vault_secret: Ownership token for the vault session.

        Returns:
            Aggregated scan result.  If deanonymize was requested the vault is
            cleaned up server-side after this call.
        """
        ...
