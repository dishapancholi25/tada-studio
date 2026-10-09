"""Backward-compatible entry point for pre-loading LLM Guard scanner models.

Delegates to ``backends.local.preload_models`` which is the canonical
implementation since the scanner backend refactoring.
"""

from backend.services.guardrails.backends.local import preload_models  # noqa: F401 — re-export


def clear_model_cache():
    """Clear all cached scanners from memory.

    Useful for testing or memory management.
    Note: This only clears the input scanner singletons in backends/local.py.
    """
    from backend.services.guardrails.backends import local

    # Reset all module-level scanner singletons
    local._scanner_prompt_injection = None
    local._scanner_jailbreak = None
    local._scanner_toxicity_input = None
    local._scanner_secrets = None
    local._scanner_anonymize_no_vault = None
    local._scanner_gibberish_input = None
    local._scanner_ban_code = None
    local._scanner_toxicity_output = None
    local._scanner_no_refusal = None
    local._scanner_sensitive = None
    local._scanner_relevance = None
    local._scanner_gibberish_output = None
    local._scanner_bias = None
    local._scanner_factual_consistency = None

    # Clear the unified build cache used by _load_scanner (fast path).
    local._scanner_cache.clear()
