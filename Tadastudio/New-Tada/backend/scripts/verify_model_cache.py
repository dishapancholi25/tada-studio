#!/usr/bin/env python3
"""Verify all models are pre-downloaded and cached.

This script tests that all models (spaCy and LLM Guard scanners) are
available in the cache without requiring downloads.

Used during Docker build verification and CI/CD checks.
"""

import os
import sys
import time


def check_model_cached(model_name: str, check_func) -> tuple[bool, float]:
    """Check if a model is cached by running its load function.

    Args:
        model_name: Human-readable model name
        check_func: Function that loads/uses the model

    Returns:
        Tuple of (success: bool, load_time: float)
    """
    print(f"\n📦 Checking {model_name}...", end=" ", flush=True)
    start = time.time()

    try:
        check_func()
        elapsed = time.time() - start
        print(f"✅ OK ({elapsed:.2f}s)")
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ FAILED ({elapsed:.2f}s)")
        print(f"   Error: {e}")
        return False, elapsed


def main():
    """Check all models are cached."""
    print("=" * 70)
    print("MODEL CACHE VERIFICATION")
    print("=" * 70)

    # Show cache locations
    print("\n📂 Cache directories:")
    print(f"   HF_HOME: {os.getenv('HF_HOME', 'not set')}")
    print(f"   TRANSFORMERS_CACHE: {os.getenv('TRANSFORMERS_CACHE', 'not set')}")
    print(f"   TORCH_HOME: {os.getenv('TORCH_HOME', 'not set')}")

    results = []
    total_time = 0

    # Check spaCy
    def check_spacy():
        import spacy
        nlp = spacy.load("en_core_web_lg")
        nlp("Test sentence")

    success, elapsed = check_model_cached("spaCy en_core_web_lg", check_spacy)
    results.append(("spaCy", success))
    total_time += elapsed

    # Check LLM Guard PromptInjection scanner
    def check_llm_guard_prompt_injection():
        from llm_guard.input_scanners import PromptInjection
        from llm_guard.input_scanners.prompt_injection import MatchType
        scanner = PromptInjection(threshold=0.5, match_type=MatchType.FULL)
        scanner.scan("test")

    success, elapsed = check_model_cached(
        "LLM Guard PromptInjection",
        check_llm_guard_prompt_injection
    )
    results.append(("LLM Guard PromptInjection", success))
    total_time += elapsed

    # Check LLM Guard Toxicity scanner
    def check_llm_guard_toxicity():
        from llm_guard.input_scanners import Toxicity
        scanner = Toxicity()
        scanner.scan("test")

    success, elapsed = check_model_cached(
        "LLM Guard Toxicity",
        check_llm_guard_toxicity
    )
    results.append(("LLM Guard Toxicity", success))
    total_time += elapsed

    # Check LLM Guard Anonymize scanner
    def check_llm_guard_anonymize():
        from llm_guard.input_scanners import Anonymize
        from llm_guard.vault import Vault
        vault = Vault()
        scanner = Anonymize(vault)
        scanner.scan("test@example.com")

    success, elapsed = check_model_cached(
        "LLM Guard Anonymize",
        check_llm_guard_anonymize
    )
    results.append(("LLM Guard Anonymize", success))
    total_time += elapsed

    # Check LLM Guard Output Toxicity scanner
    def check_llm_guard_output_toxicity():
        from llm_guard.output_scanners import Toxicity
        from llm_guard.output_scanners.toxicity import MatchType
        scanner = Toxicity(match_type=MatchType.SENTENCE)
        scanner.scan("", "test")

    success, elapsed = check_model_cached(
        "LLM Guard Output Toxicity",
        check_llm_guard_output_toxicity
    )
    results.append(("LLM Guard Output Toxicity", success))
    total_time += elapsed

    # Check LLM Guard NoRefusal scanner
    def check_llm_guard_no_refusal():
        from llm_guard.output_scanners import NoRefusal
        scanner = NoRefusal()
        scanner.scan("", "test")

    success, elapsed = check_model_cached(
        "LLM Guard NoRefusal",
        check_llm_guard_no_refusal
    )
    results.append(("LLM Guard NoRefusal", success))
    total_time += elapsed

    # Check LLM Guard Gibberish scanner (input)
    def check_llm_guard_gibberish():
        from llm_guard.input_scanners import Gibberish
        scanner = Gibberish()
        scanner.scan("hello world")

    success, elapsed = check_model_cached(
        "LLM Guard Gibberish (input)",
        check_llm_guard_gibberish
    )
    results.append(("LLM Guard Gibberish (input)", success))
    total_time += elapsed

    # Check LLM Guard BanCode scanner (input)
    def check_llm_guard_ban_code():
        from llm_guard.input_scanners import BanCode
        scanner = BanCode()
        scanner.scan("hello world")

    success, elapsed = check_model_cached(
        "LLM Guard BanCode (input)",
        check_llm_guard_ban_code
    )
    results.append(("LLM Guard BanCode (input)", success))
    total_time += elapsed

    # Check LLM Guard BanTopics scanner (input)
    def check_llm_guard_ban_topics():
        from llm_guard.input_scanners import BanTopics
        scanner = BanTopics(topics=["test"])
        scanner.scan("hello world")

    success, elapsed = check_model_cached(
        "LLM Guard BanTopics (input)",
        check_llm_guard_ban_topics
    )
    results.append(("LLM Guard BanTopics (input)", success))
    total_time += elapsed

    # Check LLM Guard Relevance scanner (output)
    def check_llm_guard_relevance():
        from llm_guard.output_scanners import Relevance
        scanner = Relevance()
        scanner.scan("hello", "hello world")

    success, elapsed = check_model_cached(
        "LLM Guard Relevance (output)",
        check_llm_guard_relevance
    )
    results.append(("LLM Guard Relevance (output)", success))
    total_time += elapsed

    # Check LLM Guard Bias scanner (output)
    def check_llm_guard_bias():
        from llm_guard.output_scanners import Bias
        scanner = Bias()
        scanner.scan("", "hello world")

    success, elapsed = check_model_cached(
        "LLM Guard Bias (output)",
        check_llm_guard_bias
    )
    results.append(("LLM Guard Bias (output)", success))
    total_time += elapsed

    # Check LLM Guard FactualConsistency scanner (output)
    def check_llm_guard_factual_consistency():
        from llm_guard.output_scanners import FactualConsistency
        scanner = FactualConsistency()
        scanner.scan("hello", "hello world")

    success, elapsed = check_model_cached(
        "LLM Guard FactualConsistency (output)",
        check_llm_guard_factual_consistency
    )
    results.append(("LLM Guard FactualConsistency (output)", success))
    total_time += elapsed

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\n✅ Passed: {passed}/{total}")
    print(f"⏱️  Total time: {total_time:.2f}s")

    if passed < total:
        print("\n❌ Some models failed to load!")
        print("\nFailed models:")
        for name, success in results:
            if not success:
                print(f"   - {name}")
        sys.exit(1)
    else:
        print("\n🎉 All models cached and ready!")

        # If all loads were fast, cache is working
        if total_time < 30:
            print("✨ Cache is working perfectly (fast load times)")
        else:
            print("⚠️  Load times seem slow - models may be downloading")

        sys.exit(0)


if __name__ == "__main__":
    main()
