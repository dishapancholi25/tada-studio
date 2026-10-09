#!/usr/bin/env python3
"""Pre-download ALL local-mode LLM Guard models into the guardrail models folder.

Run this ONCE, with network access, so local guardrail mode never has to
download a model on the first request (no cold-start latency, no per-request
fetch, and it can then run fully offline).

Why this exists
---------------
``pip install llm-guard`` installs only the Python *code*. The model weights
live on HuggingFace Hub and are downloaded lazily the first time each scanner
is constructed. This script constructs every scanner local mode can use, which
triggers those downloads up front, into the SAME models folder the running
app reads from.

Model location (mirrors backend/services/guardrails/filters/executors/python_sandbox.py):
    GUARDRAIL_MODELS_DIR  (default: the repo-local models/guardrail folder,
                          mirroring the container's /app/models/guardrail;
                          git-ignored)
        -> HF_HOME, TRANSFORMERS_CACHE, TORCH_HOME, XDG_CACHE_HOME

Usage
-----
    python backend/scripts/download_all_models.py

After it finishes you can run the app fully offline by exporting:
    HF_HUB_OFFLINE=1   TRANSFORMERS_OFFLINE=1
(keep GUARDRAIL_MODELS_DIR pointing at the same directory).
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Callable

# Make the `backend` package importable when this file is run as a plain script
# (both the Docker bake and local runs do `python backend/scripts/download_all_models.py`,
# which puts backend/scripts -- not the repo root -- on sys.path).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.guardrail_provisioning import (  # noqa: E402
    ensure_corporate_ca_bundle,
    ensure_spacy_en_core_web_lg,
    resolve_models_dir,
)

# ---------------------------------------------------------------------------
# 1. Point every ML model dir at the SAME folder the app uses -- BEFORE importing
#    torch / transformers / llm_guard (those read these env vars at import time).
#    The location is resolved by the shared provisioning module so the app, this
#    script, and python_sandbox.py all agree on ONE folder.
# ---------------------------------------------------------------------------
_CACHE_DIR = resolve_models_dir()
os.environ["GUARDRAIL_MODELS_DIR"] = _CACHE_DIR
os.environ["HF_HOME"] = _CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = os.path.join(_CACHE_DIR, "transformers")
os.environ["TORCH_HOME"] = os.path.join(_CACHE_DIR, "torch")
os.environ["XDG_CACHE_HOME"] = _CACHE_DIR
# We MUST be online to download; make sure a stray offline flag doesn't block us.
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)
os.makedirs(_CACHE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 3. English-only Presidio patch.
#    Mirrors local._patch_presidio_english_only(). Without it, Anonymize /
#    Sensitive build a Chinese spaCy engine (spacy-pkuseg) whose numpy-1.x
#    binary crashes on numpy 2.x, so the download never completes.
# ---------------------------------------------------------------------------
def _patch_presidio_english_only() -> None:
    import llm_guard.input_scanners.anonymize as anonymize_module

    if getattr(anonymize_module, "_tada_english_only_patched", False):
        return
    anonymize_module.ALL_SUPPORTED_LANGUAGES[:] = ["en"]
    anonymize_module._tada_english_only_patched = True


# ---------------------------------------------------------------------------
# 4. Warm-up tasks. Constructing each scanner downloads its default model(s);
#    a single .scan() forces any deferred tokenizer / secondary download.
#    Scanners with NO model (secrets, token_limit, deanonymize) are skipped.
# ---------------------------------------------------------------------------
def _spacy_en_core_web_lg() -> None:
    ensure_spacy_en_core_web_lg()


def _prompt_injection() -> None:  # also covers "jailbreak" (same model)
    from llm_guard.input_scanners import PromptInjection

    PromptInjection(threshold=0.5).scan("test")


def _toxicity_input() -> None:
    from llm_guard.input_scanners import Toxicity

    Toxicity(threshold=0.5).scan("test")


def _anonymize() -> None:
    _patch_presidio_english_only()
    from llm_guard.input_scanners import Anonymize
    from llm_guard.vault import Vault

    Anonymize(Vault()).scan("contact me at john@example.com")


def _gibberish_input() -> None:
    from llm_guard.input_scanners import Gibberish

    Gibberish().scan("hello world")


def _ban_code_input() -> None:
    from llm_guard.input_scanners import BanCode

    BanCode().scan("hello world")


def _ban_topics_input() -> None:
    from llm_guard.input_scanners import BanTopics

    BanTopics(topics=["politics"]).scan("hello world")


def _language_input() -> None:
    from llm_guard.input_scanners import Language

    Language(valid_languages=["en"]).scan("hello world")


def _toxicity_output() -> None:
    from llm_guard.output_scanners import Toxicity

    Toxicity(threshold=0.7).scan("", "test")


def _no_refusal_output() -> None:
    from llm_guard.output_scanners import NoRefusal

    NoRefusal().scan("", "test")


def _sensitive_output() -> None:
    _patch_presidio_english_only()
    from llm_guard.output_scanners import Sensitive

    Sensitive().scan("", "contact me at john@example.com")


def _relevance_output() -> None:
    from llm_guard.output_scanners import Relevance

    Relevance().scan("hello", "hello world")


def _gibberish_output() -> None:
    from llm_guard.output_scanners import Gibberish

    Gibberish().scan("", "hello world")


def _bias_output() -> None:
    from llm_guard.output_scanners import Bias

    Bias().scan("", "hello world")


def _factual_consistency_output() -> None:
    from llm_guard.output_scanners import FactualConsistency

    FactualConsistency().scan("hello", "hello world")


def _ban_topics_output() -> None:
    from llm_guard.output_scanners import BanTopics

    BanTopics(topics=["politics"]).scan("", "hello world")


def _language_output() -> None:
    from llm_guard.output_scanners import Language

    Language(valid_languages=["en"]).scan("", "hello world")


def _ban_competitors_output() -> None:
    from llm_guard.output_scanners import BanCompetitors

    BanCompetitors(competitors=["Acme Corp"]).scan("", "hello world")


TASKS: list[tuple[str, Callable[[], None]]] = [
    ("spaCy en_core_web_lg (PII)", _spacy_en_core_web_lg),
    ("input: prompt_injection / jailbreak", _prompt_injection),
    ("input: toxicity", _toxicity_input),
    ("input: anonymize (PII NER)", _anonymize),
    ("input: gibberish", _gibberish_input),
    ("input: ban_code", _ban_code_input),
    ("input: ban_topics", _ban_topics_input),
    ("input: language", _language_input),
    ("output: toxicity", _toxicity_output),
    ("output: no_refusal", _no_refusal_output),
    ("output: sensitive (PII)", _sensitive_output),
    ("output: relevance", _relevance_output),
    ("output: gibberish", _gibberish_output),
    ("output: bias", _bias_output),
    ("output: factual_consistency", _factual_consistency_output),
    ("output: ban_topics", _ban_topics_output),
    ("output: language", _language_output),
    ("output: ban_competitors", _ban_competitors_output),
]


def _cache_size_mb() -> float:
    total = 0
    for root, _dirs, files in os.walk(_CACHE_DIR):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return round(total / (1024 * 1024), 1)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("=" * 74)
    print("DOWNLOAD ALL LOCAL-MODE GUARDRAIL MODELS")
    print("=" * 74)
    print(f"Models dir : {_CACHE_DIR}")
    print(f"HF_HOME    : {os.environ['HF_HOME']}")

    ensure_corporate_ca_bundle(_CACHE_DIR)

    results: list[tuple[str, bool]] = []
    started = time.time()

    for label, func in TASKS:
        print(f"\n>>> {label} ...", flush=True)
        t0 = time.time()
        try:
            func()
            print(f"    OK ({time.time() - t0:.1f}s)")
            results.append((label, True))
        except Exception as exc:  # keep going; report at the end
            print(f"    FAILED ({time.time() - t0:.1f}s): {exc}")
            results.append((label, False))

    passed = sum(1 for _, ok in results if ok)
    print("\n" + "=" * 74)
    print(f"Done: {passed}/{len(results)} models ready in {time.time() - started:.1f}s")
    print(f"Models size: {_cache_size_mb()} MB at {_CACHE_DIR}")
    if passed < len(results):
        print("\nFailed:")
        for label, ok in results:
            if not ok:
                print(f"  - {label}")
        print(
            "\nIf failures are TLS/SSL related, the corporate proxy CA may be "
            "missing. Re-run after confirming the CA bundle was written above."
        )
        return 1
    print("\nAll models cached. Run the app offline with HF_HUB_OFFLINE=1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
