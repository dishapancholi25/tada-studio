# Guardrails Implementation Summary

## What Was Built

A guardrails system that enforces safety policies on AI workflow executions. Runs as middleware interceptors at six points in the execution pipeline, with LLM Guard ML scanners as the primary detection engine and LLM-as-judge as a fallback.

## Core Files

### Configuration

| File | Purpose |
|------|---------|
| `backend/models/workflow/configs/guardrails.py` | Config dataclasses: `GuardrailsConfig`, `PatternRule`, `PatternEntry`, `ToolCallPolicy`, `TokenBudget`, `BehavioralGuardrails`, `OutputScanners`, `ProviderContentFilter`, `CustomFilter` |

### Engine & Orchestration

| File | Purpose |
|------|---------|
| `backend/services/guardrails/__init__.py` | Package entry, singleton `get_guardrails_engine()` |
| `backend/services/guardrails/engine.py` | `GuardrailsEngine` orchestrator with `check_input`, `check_output`, `check_tool_call`, `check_token_budget`, `resolve_unified` |
| `backend/services/guardrails/checkpoint.py` | `GuardrailCheckpoint` (unified entry point: route -> evaluate -> report -> enforce) + `GuardrailContext` (execution metadata bundle) |
| `backend/services/guardrails/models.py` | `GuardrailResult` and `Violation` dataclasses (includes `vault_id`/`vault_secret` for PII round-trips) |
| `backend/services/guardrails/ssrf.py` | SSRF protection: URL scheme validation, DNS resolution, IP range checking |
| `backend/services/guardrails/pattern_rules.py` | PatternRule regex matching with block/redact/warn actions |
| `backend/services/guardrails/policy_service.py` | Shared policy CRUD |
| `backend/services/guardrails/resolver.py` | `LayeredPolicyResolver` (6-layer merge with TTL cache) |
| `backend/services/guardrails/violation_persistence.py` | Violation DB persistence (called internally by `GuardrailCheckpoint`) |

### Evaluators

| File | Purpose |
|------|---------|
| `backend/services/guardrails/evaluators/input.py` | `InputGuardrailEvaluator` — pattern rules + behavioral + custom ingress |
| `backend/services/guardrails/evaluators/output.py` | `OutputGuardrailEvaluator` — pattern rules + length + LLM Guard output scanners + deanonymize |
| `backend/services/guardrails/evaluators/tool_call.py` | `ToolCallGuardrailEvaluator` — HTTP/SQL/file validation |
| `backend/services/guardrails/evaluators/token_budget.py` | `TokenBudgetEvaluator` — cumulative usage tracking |
| `backend/services/guardrails/evaluators/behavioral.py` | `BehavioralGuardrailEvaluator` — thin orchestrator routing to scanners or judge |
| `backend/services/guardrails/evaluators/input_scanners.py` | LLM Guard input scanner utilities with two-phase execution |
| `backend/services/guardrails/evaluators/llm_judge.py` | LLM-as-judge fallback for adversarial detection |

### Scanner Backends

| File | Purpose |
|------|---------|
| `backend/services/guardrails/backends/__init__.py` | Factory: `get_scanner_backend()` (selects local/api/hybrid) |
| `backend/services/guardrails/backends/protocol.py` | `ScannerBackend` protocol, `ScannerResult`, `ScanResult` |
| `backend/services/guardrails/backends/local.py` | `LocalScannerBackend` — in-process LLM Guard scanners |
| `backend/services/guardrails/backends/api.py` | `ApiScannerBackend` — HTTP client to llm-guard service |
| `backend/services/guardrails/backends/hybrid.py` | `HybridScannerBackend` — lightweight local + heavy remote |

### Custom Filters

| File | Purpose |
|------|---------|
| `backend/services/guardrails/filters/evaluator.py` | `CustomFilterEvaluator` |
| `backend/services/guardrails/filters/templates.py` | Filter template definitions |
| `backend/services/guardrails/filters/executors/python_sandbox.py` | Python sandbox executor (supports Presidio, Detoxify) |
| `backend/services/guardrails/filters/executors/llm_judge.py` | LLM judge filter executor |
| `backend/services/guardrails/filters/executors/declarative.py` | Declarative template executor |

### Shared Policy System (DB Models)

| File | Purpose |
|------|---------|
| `backend/models/guardrails/guardrail_policy.py` | `GuardrailPolicy` model |
| `backend/models/guardrails/guardrail_assignment.py` | `GuardrailAssignment` model |
| `backend/models/guardrails/violation_event.py` | `GuardrailViolationEvent` model |
| `backend/models/guardrails/policy_version.py` | `GuardrailPolicyVersion` model |
| `backend/models/guardrails/violation_feedback.py` | `GuardrailViolationFeedback` model |

### API Routes

| File | Purpose |
|------|---------|
| `backend/api/guardrails/routes.py` | Policy CRUD, assignments, templates, resolve |
| `backend/api/guardrails/violations/routes.py` | Violation listing and summary |
| `backend/api/guardrails/feedback/routes.py` | Violation feedback (positive/negative) |
| `backend/api/guardrails/sandbox/routes.py` | Policy test sandbox |
| `backend/api/guardrails/versions/routes.py` | Policy version history and rollback |
| `backend/api/guardrails/metrics/routes.py` | Per-policy metrics |
| `backend/api/guardrails/compliance/routes.py` | Admin compliance dashboard |

## Pipeline Integration Points

All guardrail checks use `GuardrailCheckpoint` as a unified entry point. The checkpoint handles
evaluation routing, violation persistence (DB + WebSocket), and enforcement (raise on enforce,
log on audit). Config is resolved via `GuardrailsEngine.resolve_unified()`.

| File | Change |
|------|--------|
| `backend/models/workflow/configs/agent.py` | `guardrails_config: Optional[GuardrailsConfig]` field |
| `backend/services/workflow/state/schemas.py` | `guardrails_state` and `workflow_id` in `WorkflowState` |
| `backend/services/guardrails/checkpoint.py` | `GuardrailCheckpoint` + `GuardrailContext` — unified check, report, enforce |
| `backend/services/execution/async_agent/executor.py` | Input guardrails + provider content filter via `GuardrailCheckpoint` |
| `backend/services/execution/async_agent/message_builder.py` | System prompt protection in `_build_system_prompt()` |
| `backend/services/execution/async_agent/tool_executor.py` | Tool call/ingress/egress/injection guardrails via `GuardrailCheckpoint` |
| `backend/services/nodes/executors/agent.py` | Output guardrails via `GuardrailCheckpoint` + token budget tracking |
| `backend/services/streaming/event_emitter.py` | `emit_guardrail_violation()` for WebSocket events (called by checkpoint internally) |

## Pipeline Insertion Points

1. **Input** — `executor.py:execute_agent()` — `checkpoint.check(..., "input", ctx)`
2. **System prompt** — `message_builder.py:_build_system_prompt()` after variable replacement (preventive, no checkpoint)
3. **Tool call** — `tool_executor.py:_execute_single_tool()` — four checkpoint types: `tool_call`, `tool_ingress`, `tool_egress`, `tool_injection`
4. **Provider content filter** — `executor.py:execute_agent()` — `GuardrailCheckpoint.report_prebuilt_violations()`
5. **Token budget** — `agent.py:execute()` after state update (direct engine call for tracking)
6. **Output** — `agent.py:execute()` — `checkpoint.check(..., "output", ctx)`

## Key Defaults

- SSRF blocks: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `0.0.0.0/8`
- SQL: only `SELECT` allowed by default
- Max tool calls: 50 per execution
- Max file size: 10 MB
- Max input length: 50,000 chars
- Max output length: 100,000 chars
- Max LLM calls: 20 per execution
- Budget warning threshold: 80%
- Prompt injection threshold: 0.75
- Jailbreak threshold: 0.75
- Toxicity threshold: 0.5

## Behavioral Scanner Actions

Scanner fields use action enums instead of booleans:

| Action | Behavior |
|--------|----------|
| `"off"` | Scanner disabled |
| `"block"` | Fail execution on detection |
| `"warn"` | Log but continue |
| `"anonymize"` | PII only — replace with placeholders, restore in output |

## Two-Phase Input Scanning

Input scanners execute in two phases:

1. **Sanitization** (Phase 1): PII anonymization and secret redaction run first
2. **Detection** (Phase 2): Adversarial and content scanners run on sanitized text

This prevents false positives from PII patterns confusing the prompt-injection classifier.

## Frontend UI

| File | Purpose |
|------|---------|
| `frontend/src/types/guardrails.ts` | TypeScript types + defaults mirroring backend dataclasses |
| `frontend/src/types/guardrail-items.ts` | `GuardrailItem` discriminated union + per-type config interfaces |
| `frontend/src/lib/guardrail-item-mapper.ts` | Bidirectional mapper (`configToItems` / `itemsToConfig`) |
| `frontend/src/components/core/guardrails/GuardrailBuilder.tsx` | Full policy editor with guard cards, catalog, sandbox |
| `frontend/src/components/core/guardrails/GuardrailCard.tsx` | Individual guard configuration (toggle, threshold, scope) |
| `frontend/src/components/core/guardrails/GuardrailCatalogModal.tsx` | Browse and add guards from the catalog |
| `frontend/src/components/core/guardrails/catalog.ts` | Guard definitions: 7 categories + 3 quick-start bundles |
| `frontend/src/lib/guardrails-api.ts` | API client |
| `frontend/src/types/guardrail-policies.ts` | Shared policy TypeScript types |

**Location in UI:** Guardrail builder is embedded in the Guardrail Policies page and the agent node properties panel.
