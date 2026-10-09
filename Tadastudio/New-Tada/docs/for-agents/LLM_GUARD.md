# Local Model Behavioral Guardrails

## Overview

Local behavioral guardrails use [LLM Guard](https://llm-guard.com/) by ProtectAI to detect prompt injection and jailbreak
attempts without external API calls. LLM Guard replaces the previous custom HuggingFace pipeline infrastructure — the same
underlying model (`protectai/deberta-v3-base-prompt-injection-v2`) is still used, now managed by LLM Guard internally.

**Benefits:**

- Single maintained library with a consistent scanner API
- No custom download scripts — LLM Guard handles model lifecycle
- Full scanner set is now active — input and output scanning across toxicity, PII, secrets, and refusal detection
- Same detection quality, faster integration

---

## Quick Start

### Enable Local Models

```python
from backend.models.workflow.configs.guardrails import (
    BehavioralGuardrails,
    OutputScanners,
    GuardrailsConfig,
)

# Input scanners
behavioral = BehavioralGuardrails(
    detect_prompt_injection=True,
    detect_jailbreak_attempts=True,
    detect_gibberish=True,
    ban_code=False,
    ban_topics=[],
    allowed_languages=["en"],
    max_input_tokens=4096,
    detect_toxicity=True,
    anonymize_pii=True,
    detect_secrets=True,
)

# Output scanners
output = OutputScanners(
    detect_toxicity=True,
    detect_refusal=True,
    detect_sensitive_data=True,
    ban_topics=[],
    allowed_languages=["en"],
    check_relevance=True,
    detect_gibberish=True,
    ban_competitors=["CompetitorA", "CompetitorB"],
    detect_bias=False,
    check_factual_consistency=False,
)

# Combined config
config = GuardrailsConfig(
    enabled=True,
    enforcement_mode="enforce",
    behavioral=behavioral,
    output_scanners=output,
)
```

### Use in Code

```python
from backend.services.guardrails.evaluators.behavioral import BehavioralGuardrailEvaluator

evaluator = BehavioralGuardrailEvaluator()
result = await evaluator.evaluate(user_input, config)

if not result.passed:
    for violation in result.violations:
        print(f"Detected: {violation.rule_name}")
        print(f"Method: {violation.details['detection_method']}")  # "llm_guard"
        print(f"Confidence: {violation.details['confidence']}")
```

---

## Scanner Mapping

### Input Scanners

| # | Detection Type | LLM Guard Scanner | Direction | Config Flag | Notes |
|---|---|---|---|---|---|
| 1 | Prompt Injection | `PromptInjection` (FULL) | Input | `detect_prompt_injection=True` | Scores entire input as one unit |
| 2 | Jailbreak | `PromptInjection` (SENTENCE) | Input | `detect_jailbreak_attempts=True` | Scores per-sentence, returns max risk |
| 3 | Gibberish | `Gibberish` | Input | `detect_gibberish=True` | Perplexity-based; catches encoding attacks and garbled input |
| 4 | Code Detection | `BanCode` | Input | `ban_code=True` | Blocks code in prompts |
| 5 | Topic Ban | `BanTopics` | Input | `ban_topics=["topic1", "topic2"]` | Zero-shot classifier |
| 6 | Language | `Language` | Input | `allowed_languages=["en", "fr"]` | ISO 639-1 allowlist |
| 7 | Token Limit | `TokenLimit` | Input | `max_input_tokens=4096` | Token-count gate (more accurate than character limit) |
| 8 | Toxicity | `Toxicity` (SENTENCE) | Input | `detect_toxicity=True` | `unitary/unbiased-toxic-roberta` |
| 9 | PII Anonymization | `Anonymize` | Input | `anonymize_pii=True` | Vault-based round-trip |
| 10 | Secrets | `Secrets` (REDACT_PARTIAL) | Input | `detect_secrets=True` | `detect-secrets` library |

### Output Scanners (all run on raw LLM output before Deanonymize)

| # | Detection Type | LLM Guard Scanner | Direction | Config Flag | Notes |
|---|---|---|---|---|---|
| 11 | Toxicity (output) | `Toxicity` (SENTENCE) | Output | `output_scanners.detect_toxicity=True` | Same model as input |
| 12 | No-Refusal | `NoRefusal` | Output | `output_scanners.detect_refusal=True` | Flags unhelpful LLM refusals |
| 13 | Sensitive Data | `Sensitive` | Output | `output_scanners.detect_sensitive_data=True` | Detects PII leaking in responses |
| 14 | Topic Ban (output) | `BanTopics` | Output | `output_scanners.ban_topics=["topic1"]` | Zero-shot classifier on output |
| 15 | Language (output) | `Language` | Output | `output_scanners.allowed_languages=["en"]` | ISO 639-1 allowlist on output |
| 16 | Relevance | `Relevance` | Output | `output_scanners.check_relevance=True` | Semantic similarity to input prompt; requires `prompt` to be passed |
| 17 | Gibberish (output) | `Gibberish` | Output | `output_scanners.detect_gibberish=True` | Detects nonsensical LLM responses |
| 18 | Competitor Ban | `BanCompetitors` | Output | `output_scanners.ban_competitors=["CompetitorA"]` | String + classifier |
| 19 | Bias | `Bias` | Output | `output_scanners.detect_bias=True` | Gender, racial, political bias |
| 20 | Factual Consistency | `FactualConsistency` | Output | `output_scanners.check_factual_consistency=True` | Checks output vs input prompt; skipped if no prompt |
| 21 | Deanonymize | `Deanonymize` | Output | Automatic when `anonymize_pii=True` and vault present | Restores PII placeholders from Vault; runs last |

---

## Service Authentication (LLM_GUARD_API_KEY)

When running in `api` or `hybrid` mode, the backend and `llm-guard` service share a bearer token via the
`LLM_GUARD_API_KEY` environment variable. If set, the service rejects any request to `/scan/input` or `/scan/output`
that lacks a matching `Authorization: Bearer <key>` header (returns HTTP 401). The `/health` endpoint is exempt so
healthchecks work without credentials.

If the variable is empty or unset, authentication is disabled — fully backward compatible.

**Files involved:**

- [`synechron/llm-guard`](https://github.com/synechron/llm-guard) `app.py` — middleware reads `LLM_GUARD_API_KEY`, validates the header
- `backend/services/guardrails/backends/api.py` — `ApiScannerBackend._get_client()` sets the `Authorization` header on the `httpx.AsyncClient`
- `docker-compose.yml` / `docker-compose.dev.yml` — pass `LLM_GUARD_API_KEY` to both services

---

## HF_TOKEN

The HuggingFace token is **optional but recommended**. Authenticated requests get higher HuggingFace rate limits, reducing 429 errors on busy CI/CD build agents. All LLM Guard models are public — no token is required for access.

The token is only used during Docker build (as a build `ARG`) and is not present in the runtime image.

---

## Anonymize / Deanonymize — Vault-Based PII Round-Trip

When `anonymize_pii=True`, the guardrails engine performs a full PII round-trip:

1. **Input phase** — `engine.check_input()` creates a new `Vault()` instance per request. The `Anonymize` scanner
   replaces detected PII (names, emails, phone numbers, credit cards, IP addresses, dates) with placeholder tokens
   like `[REDACTED_PERSON_1]`. The Vault maps each placeholder back to the original value.
2. **Storage** — The Vault is stored in `guardrails_state["llm_guard_vault"]` and passed through to `check_output()`.
3. **Output phase** — The `Deanonymize` scanner restores original values in the LLM response using the Vault mapping. It always runs last in the output scanner chain.

**Important details:**

- The Vault is **in-memory only** — it is not persisted between requests.
- Anonymize severity is `warn` (not `block`) — PII is transformed, not blocked.
- If no Vault is present in the guardrails state, `Deanonymize` is skipped.

---

## Scanner Execution Order

### Input

`PromptInjection (FULL)` → `PromptInjection (SENTENCE)` → `Gibberish` → `BanCode` → `BanTopics` → `Language` → `TokenLimit` → `Toxicity` → `Anonymize` → `Secrets`

All input scanners run inside `_classify_with_llm_guard_input_scanners`. When no scanner flags are set but `detect_prompt_injection` or `detect_jailbreak_attempts` are enabled, the LLM-as-judge fallback path is used instead. See `backend/services/guardrails/evaluators/behavioral.py`.

### Output

`Toxicity` → `NoRefusal` → `Sensitive` → `BanTopics` → `Language` → `Relevance` → `Gibberish` → `BanCompetitors` → `Bias` → `FactualConsistency` → `Deanonymize` (always last)

**Notes:**

- `Relevance` is silently skipped if no `prompt` is available (the condition guard in `_run_llm_guard_output_scanners` simply does not enter the scanner block).
- `FactualConsistency` logs a warning (`"FactualConsistency scanner skipped: no prompt/context available"`) when no `prompt` is available. See `backend/services/guardrails/evaluators/output.py`.
- Output scanners activate when at least one `output_scanners` flag is enabled.

---

## Severity Reference

| Scanner | Severity | Effect |
|---|---|---|
| PromptInjection (both) | `block` | Blocks in enforce mode |
| Gibberish (input) | `block` | Blocks in enforce mode |
| BanCode | `block` | Blocks in enforce mode |
| BanTopics (input) | `block` | Blocks in enforce mode |
| Language (input) | `block` | Blocks in enforce mode |
| TokenLimit | `block` | Blocks in enforce mode |
| Toxicity (input) | `block` | Blocks in enforce mode |
| Anonymize | `warn` | Transforms content, does not block |
| Secrets | `block` | Blocks in enforce mode |
| Toxicity (output) | `block` | Blocks in enforce mode |
| NoRefusal | `warn` | Logged, does not block |
| Sensitive Data | `warn` | Logged, does not block |
| BanTopics (output) | `block` | Blocks in enforce mode |
| Language (output) | `block` | Blocks in enforce mode |
| Relevance | `warn` | Logged, does not block |
| Gibberish (output) | `block` | Blocks in enforce mode |
| BanCompetitors | `warn` | Logged, does not block |
| Bias | `warn` | Logged, does not block |
| FactualConsistency | `warn` | Logged, does not block |

---

## Testing

```bash
pytest backend/tests/services/test_local_model_guardrails.py -v
```

Same test file path, same assertions — no changes to test expectations.

---

## Troubleshooting

### Model Download on First Run Outside Docker

LLM Guard downloads models from HuggingFace on first instantiation. In Docker, models are pre-cached in the builder stage. Outside Docker, first use requires internet access.

### Memory Usage

| Model | Size | Used by |
|---|---|---|
| `protectai/deberta-v3-base-prompt-injection-v2` | ~500 MB | PromptInjection (FULL + SENTENCE share weights) |
| `unitary/unbiased-toxic-roberta` | ~500 MB | Toxicity (input + output) |
| `dslim/bert-base-NER` + spaCy `en_core_web_trf` | ~400 MB | Anonymize / Deanonymize NER |
| `sentence-transformers/all-MiniLM-L6-v2` | ~90 MB | Relevance, FactualConsistency |
| `valurank/distilroberta-bias` | ~250 MB | Bias |
| **Total warm cache** | **~3.5 GB** | |

### Rate Limit Errors During Build

Set `HF_TOKEN` in `.env` to authenticate and raise rate limits.

### False Positives

The scanners use `is_valid=False` as the threat gate. If false positives are an issue, consider disabling individual scanner flags rather than adjusting thresholds.

---

## Related Documentation

- **Guardrails Architecture:** `docs/architecture/07-guardrails-and-policies.md`
- **User Guide:** `docs/for-users/11-guardrails.md`
- **Guardrails Implementation:** `docs/for-agents/implementation-summaries/GUARDRAILS_IMPLEMENTATION.md`
