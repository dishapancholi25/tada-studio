"""Post-write PII redaction for memory content.

This module implements the write-side redaction hook that protects sensitive
personal data *before* a memory row is persisted, so plaintext PII never
reaches the database or the logs.

Approach (detect + encrypt hybrid):
    1. Irreversibly mask secrets (passwords / API keys) using the same
       ``detect-secrets`` plugin set as the app's guardrails Secrets scanner.
       Detected spans are replaced in-place with a fixed, unrecoverable marker.
       These are never recoverable.
    2. Detect reversible PII spans with an in-process Presidio ``AnalyzerEngine``
       (English-only). Detection runs locally and never depends on the remote
       guardrails service.
    3. Reversibly encrypt each detected span with a dedicated Fernet key
       (``MEMORY_ENCRYPTION_KEY``) and replace it in-text with a self-delimiting
       token so the value can later be decrypted by authorised readers.

This module contains no read-side, decryption, or admin logic. It only leaves
recoverable spans encrypted in a durable, versioned form.

Token format:
    ⟦PII:{ENTITY_TYPE}:{key_version}:{ciphertext}⟧

where ``{key_version}:{ciphertext}`` is exactly the versioned output of the
memory Fernet encryptor (e.g. ``v1:gAAAAA...``).
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
from typing import Any, List, Optional, Tuple

from backend.encryption_utils import CredentialEncryption

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PII buckets
# ---------------------------------------------------------------------------
# Dedicated, fixed list owned by the memory module. Deliberately NOT reused from
# InputScanners.pii_entity_types so guardrail policy changes never alter what
# memory redaction protects. PERSON is intentionally excluded to avoid
# over-encryption / search noise.
MEMORY_PII_ENTITY_TYPES: List[str] = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "IBAN_CODE",
    "UK_NHS",
    "ES_NIF",
    "IT_FISCAL_CODE",
]

# Detection language and confidence threshold. English-only mirrors the
# guardrails constraint in services/guardrails/backends/local.py. The threshold
# is 0.4 (not Presidio's 0.5 default) because this feature errs toward recall on
# a small, curated high-value entity list: Presidio's PhoneRecognizer emits a
# fixed 0.4 score for a context-free phone number, so a 0.5 cutoff would silently
# drop every phone number that lacks an adjacent context word. 0.4 keeps those
# while the very-weak sub-0.4 patterns (e.g. bare 9-digit SSN) still stay out.
MEMORY_PII_LANGUAGE = "en"
MEMORY_PII_SCORE_THRESHOLD = 0.4

# ---------------------------------------------------------------------------
# Token format
# ---------------------------------------------------------------------------
_TOKEN_OPEN = "\u27e6"  # ⟦  LEFT WHITE SQUARE BRACKET
_TOKEN_CLOSE = "\u27e7"  # ⟧  RIGHT WHITE SQUARE BRACKET

# Locates redaction tokens. The ciphertext group is the versioned Fernet output
# (``v{n}:<base64>``). Used here only to detect already-redacted content for
# idempotency — this module never decrypts.
TOKEN_PATTERN = re.compile(
    _TOKEN_OPEN + r"PII:([A-Z_]+):(v\d+:[A-Za-z0-9+/=_\-]+)" + _TOKEN_CLOSE
)


def _format_token(entity_type: str, versioned_ciphertext: str) -> str:
    """Build the in-text token for an encrypted reversible span."""
    return f"{_TOKEN_OPEN}PII:{entity_type}:{versioned_ciphertext}{_TOKEN_CLOSE}"


# ---------------------------------------------------------------------------
# Dedicated memory encryptor (MEMORY_ENCRYPTION_KEY) — lazy singleton
# ---------------------------------------------------------------------------
_memory_encryptor: Optional[CredentialEncryption] = None
_encryptor_lock = threading.Lock()


def get_memory_encryptor() -> CredentialEncryption:
    """Return the process-wide encryptor bound to ``MEMORY_ENCRYPTION_KEY``.

    Uses a dedicated key (not ``CREDENTIAL_ENCRYPTION_KEY``) so memory
    readability is isolated from credential-key rotation. Fails closed if the
    key is missing in a non-test environment.
    """
    global _memory_encryptor
    if _memory_encryptor is None:
        with _encryptor_lock:
            if _memory_encryptor is None:
                _memory_encryptor = CredentialEncryption(
                    key_env_var="MEMORY_ENCRYPTION_KEY"
                )
    return _memory_encryptor


# ---------------------------------------------------------------------------
# In-process Presidio analyzer — lazy singleton (English-only)
# ---------------------------------------------------------------------------
_analyzer: Optional[Any] = None
_analyzer_lock = threading.Lock()


def _get_analyzer() -> Any:
    """Build and cache the in-process Presidio ``AnalyzerEngine`` (English-only).

    Construction loads the spaCy ``en_core_web_lg`` model and is expensive
    (~seconds), so it is built once and cached.
    """
    global _analyzer
    if _analyzer is None:
        with _analyzer_lock:
            if _analyzer is None:
                from backend.services.guardrail_provisioning import (
                    ensure_spacy_en_core_web_lg,
                )

                ensure_spacy_en_core_web_lg()

                from presidio_analyzer import AnalyzerEngine
                from presidio_analyzer.nlp_engine import NlpEngineProvider

                nlp_engine = NlpEngineProvider(
                    nlp_configuration={
                        "nlp_engine_name": "spacy",
                        "models": [
                            {"lang_code": "en", "model_name": "en_core_web_lg"}
                        ],
                    }
                ).create_engine()

                _analyzer = AnalyzerEngine(
                    nlp_engine=nlp_engine,
                    supported_languages=["en"],
                )
    return _analyzer


# ---------------------------------------------------------------------------
# Secret detection + masking (deterministic, span-based, irreversible)
# ---------------------------------------------------------------------------
# Fixed, unrecoverable marker substituted for any detected secret span.
_SECRET_MASK = "\u27e6SECRET\u27e7"  # ⟦SECRET⟧

_detect_secrets_config: Optional[dict] = None
_detect_secrets_lock = threading.Lock()


def _get_detect_secrets_config() -> dict:
    """Return the ``detect-secrets`` plugin configuration to scan memory with.

    Reuses LLM Guard's curated plugin set so detection here matches the app's
    guardrails Secrets scanner exactly, without depending on LLM Guard's
    offset-unsafe text reconstruction (which can corrupt or leak on overlapping
    matches). We only borrow the detector configuration, not its redaction.
    """
    global _detect_secrets_config
    if _detect_secrets_config is None:
        with _detect_secrets_lock:
            if _detect_secrets_config is None:
                from llm_guard.input_scanners.secrets import (
                    _default_detect_secrets_config,
                )

                _detect_secrets_config = _default_detect_secrets_config
    return _detect_secrets_config


def _detect_secret_values(content: str) -> List[Tuple[str, str]]:
    """Return ``(secret_value, secret_type)`` pairs detected in ``content``.

    Mirrors LLM Guard's scan mechanics (a temp file scanned by detect-secrets)
    but returns raw values so the caller can mask every occurrence itself.
    """
    from detect_secrets.core.secrets_collection import SecretsCollection
    from detect_secrets.settings import transient_settings

    collection = SecretsCollection()
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.write(content.encode("utf-8"))
        tmp.close()
        with transient_settings(_get_detect_secrets_config()):
            collection.scan_file(tmp.name)
        found: List[Tuple[str, str]] = []
        for file in collection.files:
            for secret in collection[file]:
                if secret.secret_value:
                    found.append((secret.secret_value, secret.type))
        return found
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


class MemoryRedactor:
    """Redacts PII from memory content before persistence.

    ``redact`` is synchronous and CPU-bound; callers on the async write path
    should offload it to a worker thread.
    """

    def redact(self, content: str) -> str:
        """Return a redacted copy of ``content`` safe to persist.

        Secrets are irreversibly masked; the reversible PII entity types in
        ``MEMORY_PII_ENTITY_TYPES`` are Fernet-encrypted and replaced with
        in-text tokens. Non-PII text is left untouched.
        """
        if not content or not content.strip():
            return content

        # 1) Irreversibly mask secrets first (highest-risk material).
        masked = self._mask_secrets(content)

        # 2) Detect reversible PII spans in the secret-masked text.
        spans = self._detect_pii(masked)
        if not spans:
            return masked

        # 3) Encrypt spans and replace right-to-left so offsets stay valid.
        return self._encrypt_spans(masked, spans)

    # -- step 1 -------------------------------------------------------------
    def _mask_secrets(self, content: str) -> str:
        try:
            found = _detect_secret_values(content)
        except Exception:
            # Fail closed: if secret detection cannot run, do not persist the
            # content. Re-raise (without the reason) so the caller aborts.
            logger.error(
                "[MEMORY-REDACT] Secret detection failed; aborting write",
                exc_info=True,
            )
            raise

        if not found:
            return content

        # Locate every occurrence of every detected secret value, then mask
        # right-to-left so replacements never shift later offsets. This avoids
        # the offset-unsafe reconstruction that can corrupt or leak on
        # overlapping matches.
        spans: List[Tuple[int, int]] = []
        counts: dict[str, int] = {}
        for value, secret_type in found:
            counts[secret_type] = counts.get(secret_type, 0) + 1
            start = 0
            while True:
                idx = content.find(value, start)
                if idx < 0:
                    break
                spans.append((idx, idx + len(value)))
                start = idx + len(value)

        if not spans:
            return content

        # Merge overlapping/adjacent spans so each region is masked once.
        spans.sort()
        merged: List[Tuple[int, int]] = []
        for s, e in spans:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))

        out = content
        for s, e in sorted(merged, reverse=True):
            out = out[:s] + _SECRET_MASK + out[e:]

        # Fail closed: never persist a detected secret value.
        for value, _ in found:
            if value in out:
                logger.error(
                    "[MEMORY-REDACT] Secret survived masking; aborting write"
                )
                raise RuntimeError("Secret masking failed to remove a detected secret")

        logger.info("[MEMORY-REDACT] Masked secrets: %s", counts)
        return out

    # -- step 2 -------------------------------------------------------------
    def _detect_pii(self, content: str) -> List[Any]:
        analyzer = _get_analyzer()
        results = analyzer.analyze(
            text=content,
            language=MEMORY_PII_LANGUAGE,
            entities=MEMORY_PII_ENTITY_TYPES,
            score_threshold=MEMORY_PII_SCORE_THRESHOLD,
        )
        # Skip spans that fall inside an already-existing token (idempotency).
        existing = [(m.start(), m.end()) for m in TOKEN_PATTERN.finditer(content)]

        def _inside_token(start: int, end: int) -> bool:
            return any(ts <= start and end <= te for ts, te in existing)

        return [r for r in results if not _inside_token(r.start, r.end)]

    # -- step 3 -------------------------------------------------------------
    def _encrypt_spans(self, content: str, spans: List[Any]) -> str:
        encryptor = get_memory_encryptor()
        # Sort by start descending so replacements don't shift later offsets.
        ordered = sorted(spans, key=lambda r: r.start, reverse=True)
        counts: dict[str, int] = {}
        out = content
        for span in ordered:
            plaintext = out[span.start : span.end]
            versioned_ciphertext = encryptor.encrypt(plaintext)
            token = _format_token(span.entity_type, versioned_ciphertext)
            out = out[: span.start] + token + out[span.end :]
            counts[span.entity_type] = counts.get(span.entity_type, 0) + 1
        # Log entity types and counts only — never the raw spans or plaintext.
        logger.info("[MEMORY-REDACT] Encrypted PII spans: %s", counts)
        return out


_redactor: Optional[MemoryRedactor] = None
_redactor_lock = threading.Lock()


def get_memory_redactor() -> MemoryRedactor:
    """Return the process-wide ``MemoryRedactor`` singleton."""
    global _redactor
    if _redactor is None:
        with _redactor_lock:
            if _redactor is None:
                _redactor = MemoryRedactor()
    return _redactor


def redact_memory_content(content: str) -> str:
    """Convenience wrapper around the singleton redactor."""
    return get_memory_redactor().redact(content)
