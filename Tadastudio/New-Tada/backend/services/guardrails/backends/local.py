"""Local scanner backend — runs LLM Guard scanners in-process.

Wraps the existing lazy-loaded scanner singletons behind the
``ScannerBackend`` protocol.  No behavioral change from the original
code — this is a reorganisation to allow swapping in an API backend.

Vault instances are stored in a module-level dict keyed by UUID string
with TTL-based cleanup so the engine can pass a ``vault_id`` string
instead of an opaque Vault object.
"""

import asyncio
import inspect
import logging
import re
import time
import uuid
from typing import Any, Dict, Optional

from backend.services.guardrail_provisioning import (
    ensure_corporate_ca_bundle,
    ensure_spacy_en_core_web_lg,
)
from backend.services.guardrails.backends.protocol import ScannerResult, ScanResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scanner construction: cached, off-loop, serialized
# ---------------------------------------------------------------------------
# Building an LLM Guard scanner (the lazy ``import`` plus torch model
# materialization) is slow on a cold call and must not run concurrently: two
# simultaneous builds can see a partially-initialized module ("cannot import
# name ... from partially initialized module") or make torch raise "Cannot copy
# out of meta tensor", and a failed build makes the guardrail fail OPEN.
# ``_load_scanner`` is the single place a cached scanner is built: it returns the
# cached instance immediately (fast path, on the loop) and, on a miss, builds it
# on a worker thread -- so a cold model load never freezes the event loop --
# under one asyncio lock, so only one build runs at a time. ``_build_off_loop``
# does the same minus caching, for the per-request vault-bound scanners.
_scanner_cache: Dict[Any, Any] = {}
_build_lock = asyncio.Lock()


async def _load_scanner(
    loop: asyncio.AbstractEventLoop, key: Any, factory: Any, *args: Any
) -> Any:
    """Return the cached scanner for ``key``, building it once if needed.

    The build runs in the default executor (off the event loop) so a cold model
    load doesn't block other requests, and the single ``_build_lock`` serialises
    concurrent cold builds. Warm calls hit the cache and return without touching
    the lock or the executor.
    """
    scanner = _scanner_cache.get(key)
    if scanner is not None:
        return scanner
    async with _build_lock:
        scanner = _scanner_cache.get(key)
        if scanner is None:
            ensure_corporate_ca_bundle()
            scanner = await loop.run_in_executor(None, factory, *args)
            _scanner_cache[key] = scanner
        return scanner


async def _build_off_loop(
    loop: asyncio.AbstractEventLoop, factory: Any, *args: Any
) -> Any:
    """Build an uncached scanner off the loop, serialised by ``_build_lock``.

    Used for the vault-bound scanners (anonymize with a request vault,
    deanonymize) whose per-request vault makes them unsafe to cache.
    """
    async with _build_lock:
        ensure_corporate_ca_bundle()
        return await loop.run_in_executor(None, factory, *args)


# ---------------------------------------------------------------------------
# Vault store (in-memory, keyed by string id, TTL-based cleanup)
# ---------------------------------------------------------------------------

_VAULT_TTL_SECONDS = 3600  # 1 hour
_vaults: Dict[str, tuple] = {}  # vault_id -> (Vault, created_at)


def _create_vault() -> tuple[str, Any]:
    """Create a new LLM Guard Vault and store it, returning (vault_id, vault)."""
    from llm_guard.vault import Vault

    vault = Vault()
    vault_id = str(uuid.uuid4())
    _vaults[vault_id] = (vault, time.monotonic())
    return vault_id, vault


def _get_vault(vault_id: str) -> Optional[Any]:
    """Retrieve a Vault by id, or None if expired/missing."""
    entry = _vaults.get(vault_id)
    if entry is None:
        return None
    vault, created_at = entry
    if time.monotonic() - created_at > _VAULT_TTL_SECONDS:
        _vaults.pop(vault_id, None)
        return None
    return vault


def _delete_vault(vault_id: str) -> None:
    _vaults.pop(vault_id, None)


def _cleanup_expired_vaults() -> None:
    now = time.monotonic()
    expired = [vid for vid, (_, t) in _vaults.items() if now - t > _VAULT_TTL_SECONDS]
    for vid in expired:
        _vaults.pop(vid, None)


# ---------------------------------------------------------------------------
# Input scanner singletons (lazy-loaded)
# ---------------------------------------------------------------------------

_scanner_secrets = None
_scanner_anonymize_no_vault = None
_scanner_gibberish_input = None
_scanner_ban_code = None

SCANNER_THRESHOLD = 0.5


def _build_scanner(scanner_cls: Any, **kwargs: Any) -> Any:
    """Create an LLM Guard scanner with only supported constructor args."""
    supported_params = inspect.signature(scanner_cls).parameters
    filtered_kwargs = {
        key: value
        for key, value in kwargs.items()
        if value is not None and key in supported_params
    }
    return scanner_cls(**filtered_kwargs)


def _normalize_scan_result(scan_result: Any) -> tuple[Any, bool, float]:
    """Normalize old/new LLM Guard scanner result shapes."""
    if not isinstance(scan_result, tuple):
        raise TypeError(f"Unexpected scanner result type: {type(scan_result)!r}")
    # Coerce numpy scalars to native Python types. Some scanners (e.g. Relevance)
    # derive is_valid/risk_score from a numpy similarity score, yielding
    # numpy.bool_/numpy.float32, which FastAPI/Pydantic cannot serialize (500).
    if len(scan_result) == 3:
        sanitized, is_valid, risk_score = scan_result
        return sanitized, bool(is_valid), float(risk_score)
    if len(scan_result) == 2:
        sanitized, is_valid = scan_result
        return sanitized, bool(is_valid), -1.0 if is_valid else 1.0
    raise ValueError(f"Unexpected scanner result length: {len(scan_result)}")


async def _scan_with_compat(
    loop: asyncio.AbstractEventLoop,
    scanner: Any,
    *args: Any,
) -> tuple[Any, bool, float]:
    """Run an LLM Guard scanner and normalize its output."""
    scan_result = await loop.run_in_executor(None, scanner.scan, *args)
    return _normalize_scan_result(scan_result)


def _patch_jailbreak_json_reader(jailbreak_module: Any) -> None:
    """Force LLM Guard's bundled jailbreak dataset to be read as UTF-8."""
    if getattr(jailbreak_module, "_tada_utf8_reader_patched", False):
        return

    def _read_json_file_utf8(json_path: str) -> Dict[str, Any]:
        import json

        try:
            with open(json_path, "r", encoding="utf-8") as myfile:
                return json.load(myfile)
        except FileNotFoundError:
            logger.error("Could not find %s", json_path)
        except json.decoder.JSONDecodeError as json_error:
            logger.error("Could not parse %s: %s", json_path, json_error)
        return {}

    jailbreak_module.read_json_file = _read_json_file_utf8
    jailbreak_module._tada_utf8_reader_patched = True


def _patch_presidio_english_only() -> None:
    """Restrict LLM Guard's Presidio scanners (Anonymize/Sensitive) to English.

    LLM Guard 0.3.16 hardcodes ``ALL_SUPPORTED_LANGUAGES = ["en", "zh"]`` and always
    builds a Chinese spaCy engine, which pulls in ``spacy-pkuseg``. That package only
    ships a numpy 1.x binary and crashes on this project's numpy 2.x
    ("numpy.dtype size changed"), so the scanner build throws and PII fails open.
    We do not process Chinese PII, so we shrink the shared language list to
    English-only. The mutation is in place (``[:] =``) rather than a rebind because
    ``output_scanners.sensitive`` imports the very same list object.
    """
    import llm_guard.input_scanners.anonymize as anonymize_module

    if getattr(anonymize_module, "_tada_english_only_patched", False):
        return
    anonymize_module.ALL_SUPPORTED_LANGUAGES[:] = ["en"]
    anonymize_module._tada_english_only_patched = True


# Threshold-aware caches for adversarial scanners.
# Keyed by threshold float so different policies can use different
# sensitivity levels without re-loading the model every request.
_prompt_injection_cache: Dict[float, Any] = {}
_jailbreak_cache: Dict[float, Any] = {}


def _get_prompt_injection_scanner(threshold: float = SCANNER_THRESHOLD):
    if threshold not in _prompt_injection_cache:
        from llm_guard.input_scanners import PromptInjection

        _prompt_injection_cache[threshold] = _build_scanner(
            PromptInjection, threshold=threshold
        )
    return _prompt_injection_cache[threshold]


def _get_jailbreak_scanner(threshold: float = SCANNER_THRESHOLD):
    # LLM Guard 0.3.16 removed the standalone Jailbreak input scanner; jailbreak
    # detection is now handled by the PromptInjection scanner. Delegate to it so
    # existing "jailbreak" policies keep working without loading a second model.
    return _get_prompt_injection_scanner(threshold)


_toxicity_input_cache: Dict[float, Any] = {}


def _get_toxicity_input_scanner(threshold: float = 0.5):
    if threshold not in _toxicity_input_cache:
        from llm_guard.input_scanners import Toxicity

        _toxicity_input_cache[threshold] = _build_scanner(
            Toxicity, threshold=threshold
        )
    return _toxicity_input_cache[threshold]


def _get_secrets_scanner():
    global _scanner_secrets
    if _scanner_secrets is None:
        from llm_guard.input_scanners import Secrets
        from llm_guard.input_scanners.secrets import REDACT_PARTIAL

        _scanner_secrets = Secrets(redact_mode=REDACT_PARTIAL)
    return _scanner_secrets


def _get_anonymize_scanner(vault, use_faker: bool = False):
    global _scanner_anonymize_no_vault
    _patch_presidio_english_only()
    if vault is not None:
        from llm_guard.input_scanners import Anonymize

        return _build_scanner(Anonymize, vault=vault, use_faker=use_faker)
    if _scanner_anonymize_no_vault is None:
        from llm_guard.input_scanners import Anonymize

        _vault_id, vault = _create_vault()
        _scanner_anonymize_no_vault = _build_scanner(Anonymize, vault=vault)
    return _scanner_anonymize_no_vault


def _get_gibberish_input_scanner():
    global _scanner_gibberish_input
    if _scanner_gibberish_input is None:
        from llm_guard.input_scanners import Gibberish

        _scanner_gibberish_input = Gibberish()
    return _scanner_gibberish_input


def _get_ban_code_scanner():
    global _scanner_ban_code
    if _scanner_ban_code is None:
        from llm_guard.input_scanners import BanCode

        _scanner_ban_code = BanCode()
    return _scanner_ban_code


# ---------------------------------------------------------------------------
# Output scanner singletons (lazy-loaded)
# ---------------------------------------------------------------------------

_scanner_no_refusal = None
_scanner_sensitive = None
_scanner_relevance = None
_scanner_gibberish_output = None
_scanner_bias = None
_scanner_factual_consistency = None


_toxicity_output_cache: Dict[float, Any] = {}


def _get_toxicity_output_scanner(threshold: float = 0.7):
    if threshold not in _toxicity_output_cache:
        from llm_guard.output_scanners import Toxicity

        _toxicity_output_cache[threshold] = _build_scanner(
            Toxicity, threshold=threshold
        )
    return _toxicity_output_cache[threshold]


def _get_no_refusal_scanner():
    global _scanner_no_refusal
    if _scanner_no_refusal is None:
        from llm_guard.output_scanners import NoRefusal

        _scanner_no_refusal = NoRefusal()
    return _scanner_no_refusal


def _get_sensitive_scanner():
    global _scanner_sensitive
    _patch_presidio_english_only()
    if _scanner_sensitive is None:
        from llm_guard.output_scanners import Sensitive

        _scanner_sensitive = Sensitive()
    return _scanner_sensitive


def _get_relevance_scanner():
    global _scanner_relevance
    if _scanner_relevance is None:
        from llm_guard.output_scanners import Relevance

        _scanner_relevance = Relevance()
    return _scanner_relevance


def _get_gibberish_output_scanner():
    global _scanner_gibberish_output
    if _scanner_gibberish_output is None:
        from llm_guard.output_scanners import Gibberish

        _scanner_gibberish_output = Gibberish()
    return _scanner_gibberish_output


def _get_bias_scanner():
    global _scanner_bias
    if _scanner_bias is None:
        from llm_guard.output_scanners import Bias

        _scanner_bias = Bias()
    return _scanner_bias


def _get_factual_consistency_scanner():
    global _scanner_factual_consistency
    if _scanner_factual_consistency is None:
        from llm_guard.output_scanners import FactualConsistency

        _scanner_factual_consistency = FactualConsistency()
    return _scanner_factual_consistency


# ---------------------------------------------------------------------------
# Input scanner dispatch
# ---------------------------------------------------------------------------

# Maps scanner key → (getter_fn, scan_signature) for input scanners.
# "single" means scanner.scan(content), "vault" means it needs the vault.
_INPUT_SCANNER_REGISTRY: Dict[str, tuple] = {
    "gibberish": (_get_gibberish_input_scanner, "single"),
    "secrets": (_get_secrets_scanner, "single"),
}

# Dynamic input scanners (instantiated per-request with config params)
_DYNAMIC_INPUT_SCANNERS = {
    "prompt_injection",
    "jailbreak",
    "toxicity",
    "ban_topics",
    "language",
    "token_limit",
    "anonymize",
}


# Signals that the text plausibly contains source code. The ban_code model
# (vishnun/codenlbert-sm) over-fires on identifier-like or random strings
# (e.g. "someLongToken") and even on plain prose, so we gate it: run the model
# only when at least one of these appears. Real code virtually always contains
# brackets/operators/indentation, so detection is unaffected; matching too
# eagerly is harmless because the model then runs and decides.
_CODE_SIGNAL_RE = re.compile(
    r"[{}()\[\];=<>]"                          # brackets, parens, semicolon, =, < >
    r"|=>|->|::|==|!=|<=|>=|&&|\|\||\+\+|--"    # multi-char operators
    r"|</|/>|#!|#include|#define"               # tags / shebang / preprocessor
    r"|\n[ \t]+\S"                              # an indented continuation line
)


def _looks_like_code(text: str) -> bool:
    """Heuristic gate for the ban_code scanner: does the text plausibly contain
    source code? Errs toward True (i.e. toward running the model)."""
    return bool(_CODE_SIGNAL_RE.search(text))


async def _run_input_scanner(
    scanner_name: str,
    content: str,
    config: Dict[str, Any],
    vault: Optional[Any],
    loop: asyncio.AbstractEventLoop,
) -> Optional[ScannerResult]:
    """Run a single input scanner and return its result."""
    try:
        # Static singleton scanners
        if scanner_name in _INPUT_SCANNER_REGISTRY:
            getter, _ = _INPUT_SCANNER_REGISTRY[scanner_name]
            scanner = await _load_scanner(loop, ("in", scanner_name), getter)
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=sanitized if sanitized != content else None,
                metadata=metadata,
            )

        # ban_code runs a small code-vs-text classifier that over-fires on
        # identifier-like/random strings and plain prose. Gate it: if the text
        # has no code structure at all, treat it as clean without calling the
        # model. Real code has code signals, so detection is unaffected.
        if scanner_name == "ban_code":
            if not _looks_like_code(content):
                return ScannerResult(
                    scanner_name=scanner_name, is_valid=True, risk_score=-1.0
                )
            scanner = await _load_scanner(
                loop, ("in", "ban_code"), _get_ban_code_scanner
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=sanitized if sanitized != content else None,
                metadata=metadata,
            )

        # Threshold-aware adversarial scanners
        if scanner_name == "prompt_injection":
            threshold = config.get("threshold", SCANNER_THRESHOLD)
            scanner = await _load_scanner(
                loop,
                ("prompt_injection", threshold),
                _get_prompt_injection_scanner,
                threshold,
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=sanitized if sanitized != content else None,
                metadata=metadata,
            )

        if scanner_name == "jailbreak":
            threshold = config.get("threshold", SCANNER_THRESHOLD)
            scanner = await _load_scanner(
                loop,
                ("prompt_injection", threshold),
                _get_jailbreak_scanner,
                threshold,
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=sanitized if sanitized != content else None,
                metadata=metadata,
            )

        if scanner_name == "toxicity":
            threshold = config.get("threshold", 0.5)
            scanner = await _load_scanner(
                loop,
                ("toxicity_in", threshold),
                _get_toxicity_input_scanner,
                threshold,
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=sanitized if sanitized != content else None,
                metadata=metadata,
            )

        # Dynamic / parameterised scanners
        if scanner_name == "ban_topics":
            from llm_guard.input_scanners import BanTopics

            topics = config.get("topics", [])
            if not topics:
                return None
            scanner = await _load_scanner(
                loop,
                ("ban_topics_in", tuple(topics)),
                lambda: BanTopics(topics=topics),
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {
                    "topics_checked": topics,
                    "threshold": getattr(scanner, "_threshold", None),
                }
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        if scanner_name == "language":
            from llm_guard.input_scanners import Language

            valid_languages = config.get("valid_languages", [])
            if not valid_languages:
                return None
            scanner = await _load_scanner(
                loop,
                ("language_in", tuple(valid_languages)),
                lambda: Language(valid_languages=valid_languages),
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"valid_languages": valid_languages}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        if scanner_name == "token_limit":
            from llm_guard.input_scanners import TokenLimit

            limit = config.get("limit")
            if limit is None:
                return None
            scanner = await _load_scanner(
                loop, ("token_limit", limit), lambda: TokenLimit(limit=limit)
            )
            sanitized, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, content
            )
            metadata = None
            if not is_valid:
                metadata = {"limit": limit}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=None,
                metadata=metadata,
            )

        if scanner_name == "anonymize":
            import re as _re

            action = (
                config.get("action", "anonymize")
                if isinstance(config, dict)
                else "anonymize"
            )
            if action == "anonymize":
                use_faker = (
                    config.get("use_faker", False)
                    if isinstance(config, dict)
                    else False
                )
                scanner = await _build_off_loop(
                    loop, _get_anonymize_scanner, vault, use_faker
                )
                sanitized, is_valid, risk_score = await _scan_with_compat(
                    loop, scanner, content
                )
                metadata = None
                if not is_valid and sanitized:
                    placeholders = _re.findall(
                        r"\[REDACTED_([A-Z_]+?)_\d+\]", sanitized
                    )
                    if placeholders:
                        metadata = {
                            "entity_types": sorted(set(placeholders)),
                            "entity_count": len(placeholders),
                        }
                return ScannerResult(
                    scanner_name=scanner_name,
                    is_valid=is_valid,
                    risk_score=risk_score,
                    sanitized=sanitized,
                    metadata=metadata,
                )
            else:
                # Detect-only: build a throwaway anonymize scanner (on the loop,
                # like every other scanner) with a temporary vault, run only the
                # scan off-loop, and derive entity types from the redaction
                # placeholders. The vault is discarded -- detection needs no map.
                vault_id, temp_vault = _create_vault()
                try:
                    scanner = await _build_off_loop(
                        loop, _get_anonymize_scanner, temp_vault
                    )
                    sanitized, is_valid, risk_score = await _scan_with_compat(
                        loop, scanner, content
                    )
                finally:
                    _delete_vault(vault_id)
                metadata = None
                if not is_valid:
                    placeholders = re.findall(
                        r"\[REDACTED_([A-Z_]+?)_\d+\]", sanitized
                    )
                    if placeholders:
                        metadata = {
                            "entity_types": sorted(set(placeholders)),
                            "entity_count": len(placeholders),
                        }
                return ScannerResult(
                    scanner_name=scanner_name,
                    is_valid=is_valid,
                    risk_score=risk_score,
                    sanitized=None,
                    metadata=metadata,
                )

        logger.warning("[GUARDRAILS] Unknown input scanner: %s", scanner_name)
        return None

    except Exception as e:
        logger.warning("[GUARDRAILS] Input scanner %s failed: %s", scanner_name, e)
        return None


# ---------------------------------------------------------------------------
# Output scanner dispatch
# ---------------------------------------------------------------------------

_OUTPUT_SCANNER_REGISTRY: Dict[str, tuple] = {
    "no_refusal": (_get_no_refusal_scanner, "prompt_content"),
    "sensitive": (_get_sensitive_scanner, "prompt_content"),
    "relevance": (_get_relevance_scanner, "prompt_content"),
    "gibberish": (_get_gibberish_output_scanner, "prompt_content"),
    "bias": (_get_bias_scanner, "prompt_content"),
    "factual_consistency": (_get_factual_consistency_scanner, "prompt_content"),
}

_DYNAMIC_OUTPUT_SCANNERS = {
    "toxicity",
    "ban_topics",
    "language",
    "ban_competitors",
    "deanonymize",
}


async def _run_output_scanner(
    scanner_name: str,
    prompt: str,
    content: str,
    config: Dict[str, Any],
    vault: Optional[Any],
    loop: asyncio.AbstractEventLoop,
) -> Optional[ScannerResult]:
    """Run a single output scanner and return its result."""
    try:
        # Static singleton scanners — all take (prompt, content)
        if scanner_name in _OUTPUT_SCANNER_REGISTRY:
            getter, _ = _OUTPUT_SCANNER_REGISTRY[scanner_name]
            scanner = await _load_scanner(loop, ("out", scanner_name), getter)
            _, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, prompt, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        # Threshold-aware output scanners
        if scanner_name == "toxicity":
            threshold = config.get("threshold", 0.7)
            scanner = await _load_scanner(
                loop,
                ("toxicity_out", threshold),
                _get_toxicity_output_scanner,
                threshold,
            )
            _, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, prompt, content
            )
            metadata = None
            if not is_valid:
                metadata = {"threshold": getattr(scanner, "_threshold", None)}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        # Dynamic / parameterised scanners
        if scanner_name == "ban_topics":
            from llm_guard.output_scanners import BanTopics

            topics = config.get("topics", [])
            if not topics:
                return None
            scanner = await _load_scanner(
                loop,
                ("ban_topics_out", tuple(topics)),
                lambda: BanTopics(topics=topics),
            )
            _, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, prompt, content
            )
            metadata = None
            if not is_valid:
                metadata = {
                    "topics_checked": topics,
                    "threshold": getattr(scanner, "_threshold", None),
                }
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        if scanner_name == "language":
            from llm_guard.output_scanners import Language

            valid_languages = config.get("valid_languages", [])
            if not valid_languages:
                return None
            scanner = await _load_scanner(
                loop,
                ("language_out", tuple(valid_languages)),
                lambda: Language(valid_languages=valid_languages),
            )
            _, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, prompt, content
            )
            metadata = None
            if not is_valid:
                metadata = {"valid_languages": valid_languages}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        if scanner_name == "ban_competitors":
            from llm_guard.output_scanners import BanCompetitors

            competitors = config.get("competitors", [])
            if not competitors:
                return None
            scanner = await _load_scanner(
                loop,
                ("ban_competitors", tuple(competitors)),
                lambda: BanCompetitors(competitors=competitors),
            )
            _, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, "", content
            )
            metadata = None
            if not is_valid:
                metadata = {"competitors_checked": competitors}
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                metadata=metadata,
            )

        if scanner_name == "deanonymize":
            if vault is None:
                return None
            from llm_guard.output_scanners import Deanonymize

            scanner = await _build_off_loop(
                loop, lambda: Deanonymize(vault=vault)
            )
            restored, is_valid, risk_score = await _scan_with_compat(
                loop, scanner, "", content
            )
            return ScannerResult(
                scanner_name=scanner_name,
                is_valid=is_valid,
                risk_score=risk_score,
                sanitized=restored,
            )

        logger.warning("[GUARDRAILS] Unknown output scanner: %s", scanner_name)
        return None

    except Exception as e:
        logger.warning("[GUARDRAILS] Output scanner %s failed: %s", scanner_name, e)
        return None


# ---------------------------------------------------------------------------
# LocalScannerBackend
# ---------------------------------------------------------------------------


class LocalScannerBackend:
    """Runs LLM Guard scanners in-process (current behaviour)."""

    async def scan_input(
        self,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        loop = asyncio.get_running_loop()

        # Periodic vault cleanup
        _cleanup_expired_vaults()

        # Resolve or create vault only when anonymize action requires it
        vault = None
        new_vault_id: Optional[str] = vault_id
        anonymize_cfg = scanners.get("anonymize", {})
        pii_action = (
            anonymize_cfg.get("action", "anonymize")
            if isinstance(anonymize_cfg, dict)
            else "anonymize"
        )
        needs_vault = "anonymize" in scanners and pii_action == "anonymize"
        if needs_vault:
            if vault_id:
                vault = _get_vault(vault_id)
            if vault is None:
                new_vault_id, vault = _create_vault()

        results: list[ScannerResult] = []
        sanitized_content: Optional[str] = None

        for scanner_name, config in scanners.items():
            result = await _run_input_scanner(
                scanner_name, content, config, vault, loop
            )
            if result is not None:
                results.append(result)
                # Track content-modifying scanners (anonymize, secrets)
                if result.sanitized is not None:
                    sanitized_content = result.sanitized

        return ScanResult(
            results=results,
            vault_id=new_vault_id if needs_vault else None,
            sanitized_content=sanitized_content,
        )

    async def scan_output(
        self,
        prompt: str,
        content: str,
        scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> ScanResult:
        loop = asyncio.get_running_loop()

        vault = _get_vault(vault_id) if vault_id else None

        results: list[ScannerResult] = []
        sanitized_content: Optional[str] = None

        for scanner_name, config in scanners.items():
            result = await _run_output_scanner(
                scanner_name, prompt, content, config, vault, loop
            )
            if result is not None:
                results.append(result)
                if result.sanitized is not None:
                    sanitized_content = result.sanitized

        # Clean up vault after deanonymize
        if "deanonymize" in scanners and vault_id:
            _delete_vault(vault_id)

        return ScanResult(
            results=results,
            vault_id=None,
            sanitized_content=sanitized_content,
        )


# ---------------------------------------------------------------------------
# Preloading (for startup warm-up)
# ---------------------------------------------------------------------------


def _preload_ban_topics_model():
    from llm_guard.input_scanners import BanTopics

    return _build_scanner(BanTopics, topics=["politics"])


def _preload_language_model():
    from llm_guard.input_scanners import Language

    return _build_scanner(Language, valid_languages=["en"])


def _preload_ban_competitors_model():
    from llm_guard.output_scanners import BanCompetitors

    return _build_scanner(BanCompetitors, competitors=["Acme Corp"])


async def _warm_all_scanners(loop: asyncio.AbstractEventLoop) -> None:
    """Download + warm every local-mode scanner model so no request pays a cold
    download. Getter-backed scanners are cached (warm start); the config-driven
    ones (ban_topics/language/ban_competitors) are built with throwaway defaults
    purely to pull their model to disk."""
    # 13th model: spaCy en_core_web_lg (the PII scanners need it) -- download if missing.
    try:
        await loop.run_in_executor(None, ensure_spacy_en_core_web_lg)
    except Exception as exc:
        logger.warning("[GUARDRAILS] spaCy en_core_web_lg preload failed: %s", exc)
    await asyncio.sleep(0)

    warm_specs = [
        (("prompt_injection", SCANNER_THRESHOLD), _get_prompt_injection_scanner, (SCANNER_THRESHOLD,)),
        (("toxicity_in", 0.5), _get_toxicity_input_scanner, (0.5,)),
        (("anonymize_no_vault",), _get_anonymize_scanner, (None,)),
        (("in", "gibberish"), _get_gibberish_input_scanner, ()),
        (("in", "ban_code"), _get_ban_code_scanner, ()),
        (("toxicity_out", 0.7), _get_toxicity_output_scanner, (0.7,)),
        (("out", "no_refusal"), _get_no_refusal_scanner, ()),
        (("out", "sensitive"), _get_sensitive_scanner, ()),
        (("out", "relevance"), _get_relevance_scanner, ()),
        (("out", "gibberish"), _get_gibberish_output_scanner, ()),
        (("out", "bias"), _get_bias_scanner, ()),
        (("out", "factual_consistency"), _get_factual_consistency_scanner, ()),
    ]
    for key, factory, args in warm_specs:
        try:
            await _load_scanner(loop, key, factory, *args)
            logger.info("[GUARDRAILS] pre-loaded scanner %s", key)
        except Exception as exc:
            logger.warning("[GUARDRAILS] pre-load failed for %s: %s", key, exc)
        await asyncio.sleep(0)

    for factory in (
        _preload_ban_topics_model,
        _preload_language_model,
        _preload_ban_competitors_model,
    ):
        try:
            await _build_off_loop(loop, factory)
            logger.info("[GUARDRAILS] pre-downloaded model via %s", factory.__name__)
        except Exception as exc:
            logger.warning(
                "[GUARDRAILS] pre-download failed for %s: %s", factory.__name__, exc
            )
        await asyncio.sleep(0)


async def preload_models(categories: Optional[list[str]] = None):
    """Pre-load scanner models into memory at application startup.

    Warms each scanner through ``_load_scanner`` so it shares the cache and the
    single build lock with request-triggered builds -- no fail-open race between
    the startup warm-up and early requests. Schedule it with
    ``asyncio.create_task(preload_models(...))``.

    Pass ``["all"]`` to download + warm every scanner (so the app self-provisions
    all models and nothing downloads at request time).
    """
    if categories is None:
        categories = ["prompt_injection", "jailbreak", "toxicity", "anonymize"]

    loop = asyncio.get_running_loop()
    # Trust the corporate proxy CA before any HuggingFace download so the app can
    # fetch models on its own (no separate download script needed).
    ensure_corporate_ca_bundle()

    if "all" in categories:
        await _warm_all_scanners(loop)
        return

    _PRELOAD_MAP = {
        "prompt_injection": (
            ("prompt_injection", SCANNER_THRESHOLD),
            _get_prompt_injection_scanner,
            (SCANNER_THRESHOLD,),
        ),
        "jailbreak": (
            ("prompt_injection", SCANNER_THRESHOLD),
            _get_jailbreak_scanner,
            (SCANNER_THRESHOLD,),
        ),
        "toxicity": (("toxicity_in", 0.5), _get_toxicity_input_scanner, (0.5,)),
        "anonymize": (("anonymize_no_vault",), _get_anonymize_scanner, (None,)),
    }

    for category in categories:
        spec = _PRELOAD_MAP.get(category)
        if spec is None:
            logger.warning(
                "[GUARDRAILS] Unknown category for preload: %s", category
            )
            continue
        key, factory, args = spec
        try:
            await _load_scanner(loop, key, factory, *args)
            logger.info("[GUARDRAILS] Pre-loaded LLM Guard scanner for %s", category)
        except Exception as e:
            logger.warning(
                "[GUARDRAILS] Failed to pre-load scanner for %s: %s", category, e
            )
        await asyncio.sleep(0)
